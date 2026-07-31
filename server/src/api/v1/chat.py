# -*- coding: utf-8 -*-
"""
聊天 API 路由

提供对话和文件上传接口。

设计说明：
- **MySQL 是消息/摘要的唯一持久源**。`chat_service` 只在内存中编排 LangGraph，
  完成一轮后由本层统一把 (user, assistant, summary) 写库 + 更新 in-memory 缓存。
- 这样流式和非流式两条路径都用同一份持久化逻辑，避免双写不一致。
"""

from __future__ import annotations

import json
import re
from typing import Annotated, AsyncGenerator, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import verify_api_key
from src.core.config import settings
from src.core.logger import logger
from src.core.ratelimit import chat_rate_limiter
from src.infras.mysql import get_async_db
from src.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MediaInput,
    ProviderInfo,
    ProvidersResponse,
)
from src.services.chat_service import get_chat_service
from src.services.conversation_service import ConversationService


router = APIRouter()


# ============ 公共工具 ============

def _resolve_provider_model(provider: Optional[str]) -> Tuple[str, str, str]:
    """解析当前请求实际使用的 provider/display_name/model_name。"""
    provider_map = {
        "tongyi": ("千问", settings.ALIYUN_MODEL_NAME),
        "deepseek": ("DeepSeek", settings.DEEPSEEK_MODEL_NAME),
        "glm": ("GLM", settings.GLM_MODEL_NAME),
        "doubao": ("豆包", settings.DOUBAO_MODEL_NAME),
        "kimi": ("Kimi", settings.KIMI_MODEL_NAME),
    }

    selected = (provider or "").strip().lower()
    if selected not in provider_map:
        selected = settings.get_default_provider()

    display_name, model_name = provider_map.get(selected, ("未知", "unknown"))
    return selected, display_name, model_name


def _is_current_model_query(query: str) -> bool:
    """判断用户是否在询问当前使用的模型。"""
    q = (query or "").strip().lower()
    if not q:
        return False
    patterns = [
        r"当前.*模型",
        r"现在.*模型",
        r"用的.*模型",
        r"哪个.*模型",
        r"what.*model",
        r"which.*model",
        r"current.*model",
        r"provider",
    ]
    return any(re.search(p, q) for p in patterns)


def _to_agent_media_inputs(items: Iterable[MediaInput]) -> list:
    """把 schema 的 MediaInput 转成 agent 层使用的 MediaInput。"""
    from src.agent.media import MediaInput as AgentMediaInput, MediaType

    type_mapping = {
        "text": MediaType.TEXT,
        "voice": MediaType.VOICE,
        "audio": MediaType.AUDIO,
        "image": MediaType.IMAGE,
        "video": MediaType.VIDEO,
        "auto": MediaType.AUTO,
    }
    result = []
    for mi in items:
        result.append(
            AgentMediaInput(
                type=type_mapping.get(mi.type.lower(), MediaType.AUTO),
                filename=mi.filename,
                url=mi.url,
                bytes_base64=mi.bytes_base64,
            )
        )
    return result


def _to_langchain_history(items: Iterable[ChatMessage]) -> list:
    """把 schema 的 ChatMessage 转成 LangChain 消息列表。"""
    from langchain_core.messages import AIMessage, HumanMessage

    out = []
    for msg in items:
        if msg.role == "user":
            out.append(HumanMessage(content=msg.content))
        else:
            out.append(AIMessage(content=msg.content))
    return out


async def _persist_turn(
    session: AsyncSession,
    conversation_id: str,
    user_query: str,
    assistant_answer: str,
    summary: Optional[str],
    provider: Optional[str],
) -> None:
    """
    把一轮对话（用户 + 助手 + 摘要）写入 MySQL，并刷新 in-memory 缓存。

    - 自动确保会话存在（首次对话时自动创建）
    - 自动从首条用户消息生成标题
    - 失败仅写日志，不抛异常（持久化失败不应阻塞用户拿到响应）
    """
    if not conversation_id or not assistant_answer:
        return

    try:
        service = ConversationService(session)

        # 确保会话存在
        existing = await service.conversation_repo.get_with_messages(conversation_id)
        if existing is None:
            first_user_text = (user_query or "").strip()
            title = first_user_text[:20] + ("..." if len(first_user_text) > 20 else "")
            if not title:
                title = "新对话"
            await service.conversation_repo.create(
                conversation_id=conversation_id,
                title=title,
                model_provider=provider or "tongyi",
            )
            existing = await service.conversation_repo.get_with_messages_or_raise(
                conversation_id
            )

        # 追加两条消息
        if user_query:
            await service.message_repo.create(
                conversation_id=conversation_id,
                role="user",
                content=user_query,
            )
        await service.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_answer,
        )

        # 写摘要
        if summary:
            await service.update_conversation(conversation_id, summary=summary)

        # 刷新 in-memory 缓存（避免下次同会话进来读不到刚写入的消息）
        from src.services.chat_service import get_chat_service

        chat_svc = get_chat_service()
        from src.agent.memory import _from_langchain_messages

        # 从 DB 重新拉最新消息写入缓存
        refreshed = await service.conversation_repo.get_with_messages_or_raise(
            conversation_id
        )
        raw = [
            {"role": m.role, "content": m.content}
            for m in sorted(refreshed.messages, key=lambda m: m.created_at or 0)
        ]
        from langchain_core.messages import HumanMessage as _HM, AIMessage as _AM

        lcmsgs = []
        for item in raw:
            if item["role"] == "user":
                lcmsgs.append(_HM(content=item["content"]))
            elif item["role"] == "assistant":
                lcmsgs.append(_AM(content=item["content"]))
        chat_svc.memory.save_messages(conversation_id, lcmsgs)
        if summary:
            chat_svc.memory.set_summary(conversation_id, summary)
    except Exception as e:
        logger.error(f"Failed to persist chat turn for {conversation_id}: {e}")


async def _load_history_into_memory(session_id: str) -> None:
    """从 MySQL 加载历史到 in-memory 缓存（首次进入某会话时调用）。"""
    if not session_id:
        return
    try:
        from sqlalchemy.ext.asyncio import AsyncSession as _AS

        from src.infras.mysql import AsyncSessionLocal
        from src.services.chat_service import get_chat_service

        async with AsyncSessionLocal() as session:
            service = ConversationService(session)
            conv = await service.conversation_repo.get_with_messages(session_id)
            if conv is None:
                return
            raw = [
                {"role": m.role, "content": m.content}
                for m in sorted(conv.messages, key=lambda m: m.created_at or 0)
            ]
            get_chat_service().memory.prime_from_persistence(session_id, raw)
    except Exception as e:
        logger.warning(f"Failed to load history for {session_id}: {e}")


# ============ 路由 ============


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers() -> ProvidersResponse:
    """获取可用的模型提供商列表"""
    providers = settings.get_available_providers()
    default_provider = settings.get_default_provider()

    return ProvidersResponse(
        providers=[
            ProviderInfo(
                name=p["name"],
                display_name=p["display_name"],
                model_name=p["model_name"],
                available=p["available"],
            )
            for p in providers
        ],
        default=default_provider,
    )


@router.post("/message", response_model=ChatResponse, dependencies=[Depends(verify_api_key), Depends(chat_rate_limiter)])
async def chat_message(
    request: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> ChatResponse:
    """
    主对话接口（JSON）

    完整流程：
    1. 解析 provider / media / history
    2. 从 MySQL 加载历史到 in-memory 缓存
    3. 调用 chat_service.handle_chat
    4. 把 (user + assistant + summary) 写入 MySQL
    5. 返回响应
    """
    provider = x_model_provider or request.provider

    logger.info(
        f"Received chat request: session_id={request.session_id}, provider={provider}"
    )

    if _is_current_model_query(request.query):
        p, display_name, model_name = _resolve_provider_model(provider)
        return ChatResponse(
            answer=f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）",
            session_id=request.session_id,
            summary=None,
            trimmed_history=[],
        )

    await _load_history_into_memory(request.session_id)

    chat_service = get_chat_service()

    media_inputs = _to_agent_media_inputs(request.media_inputs)
    history = _to_langchain_history(request.history)

    result = await chat_service.handle_chat(
        session_id=request.session_id,
        query=request.query,
        history=history,
        media_inputs=media_inputs,
        use_direct_multimodal=request.use_direct_multimodal,
        provider=provider,
    )

    # 持久化（独立 session，确保成功提交后再返回响应）
    try:
        await _persist_turn(
            session=db,
            conversation_id=request.session_id,
            user_query=request.query,
            assistant_answer=result.answer,
            summary=result.summary,
            provider=provider,
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Persist turn commit failed: {e}")
        await db.rollback()

    from langchain_core.messages import HumanMessage

    return ChatResponse(
        answer=result.answer,
        session_id=request.session_id,
        summary=result.summary,
        trimmed_history=[
            ChatMessage(
                role="user" if isinstance(m, HumanMessage) else "assistant",
                content=m.content,
            )
            for m in result.trimmed_history
        ],
    )


@router.post("/stream", dependencies=[Depends(verify_api_key), Depends(chat_rate_limiter)])
async def chat_stream(
    request: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    流式对话接口（SSE）

    流式完成后会把 (user + assistant + summary) 一次性写库。
    """
    provider = x_model_provider or request.provider

    logger.info(
        f"Received stream request: session_id={request.session_id}, provider={provider}"
    )

    if _is_current_model_query(request.query):
        p, display_name, model_name = _resolve_provider_model(provider)
        answer = f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）"

        async def model_info_stream():
            yield f"data: {json.dumps({'content': answer}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'full_answer': answer}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            model_info_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    await _load_history_into_memory(request.session_id)

    media_inputs = _to_agent_media_inputs(request.media_inputs)
    history = _to_langchain_history(request.history)

    chat_service = get_chat_service()

    async def generate():
        full_answer = ""
        try:
            async for chunk in chat_service.handle_stream(
                session_id=request.session_id,
                query=request.query,
                history=history,
                media_inputs=media_inputs,
                use_direct_multimodal=request.use_direct_multimodal,
                provider=provider,
            ):
                if chunk:
                    full_answer += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 流结束后：尝试生成摘要、写库
            summary = None
            try:
                from src.agent.memory import ConversationMemory

                mem = chat_service.memory
                # 把刚刚的对话加入缓存再判断是否需要摘要
                from langchain_core.messages import AIMessage as _AM, HumanMessage as _HM

                cur = mem.get_messages(request.session_id)
                if request.query:
                    cur.append(_HM(content=request.query))
                cur.append(_AM(content=full_answer))
                trimmed = mem.trim_messages(cur)
                mem.save_messages(request.session_id, trimmed)
                if len(trimmed) >= chat_service.memory.MAX_TURNS * 2:
                    summary = await mem.update_summary(
                        session_id=request.session_id,
                        messages=trimmed,
                        provider=provider,
                    )
                    mem.save_messages(request.session_id, trimmed)
            except Exception as e:
                logger.warning(f"Stream post-process summary failed: {e}")

            try:
                await _persist_turn(
                    session=db,
                    conversation_id=request.session_id,
                    user_query=request.query,
                    assistant_answer=full_answer,
                    summary=summary,
                    provider=provider,
                )
                await db.commit()
            except Exception as e:
                logger.error(f"Stream persist failed: {e}")
                await db.rollback()

            yield f"data: {json.dumps({'done': True, 'full_answer': full_answer}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload", response_model=ChatResponse, dependencies=[Depends(verify_api_key), Depends(chat_rate_limiter)])
async def chat_with_upload(
    session_id: str = Form(...),
    query: str = Form(""),
    use_direct_multimodal: bool = Form(False),
    media_type: str = Form("auto"),
    file: Optional[UploadFile] = File(None),
    provider: Optional[str] = Form(None),
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> ChatResponse:
    """
    支持上传文件的对话接口（非流式）

    上传文件目前仍为非流式响应（避免 multipart + SSE 复杂度）。
    """
    actual_provider = provider or x_model_provider

    logger.info(
        f"Received upload chat: session_id={session_id}, media_type={media_type}, "
        f"provider={actual_provider}"
    )

    if _is_current_model_query(query):
        p, display_name, model_name = _resolve_provider_model(actual_provider)
        return ChatResponse(
            answer=f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）",
            session_id=session_id,
            summary=None,
            trimmed_history=[],
        )

    # 文件大小限制（默认 25MB，与 OpenAI Whisper 限制对齐）
    MAX_FILE_BYTES = 25 * 1024 * 1024
    media_inputs = []
    if file is not None:
        content = await file.read()
        if len(content) > MAX_FILE_BYTES:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=413,
                detail=f"File too large ({len(content)} > {MAX_FILE_BYTES})",
            )

        from src.agent.media import MediaInput as AgentMediaInput, MediaType

        type_mapping = {
            "text": MediaType.TEXT,
            "voice": MediaType.VOICE,
            "audio": MediaType.AUDIO,
            "image": MediaType.IMAGE,
            "video": MediaType.VIDEO,
            "auto": MediaType.AUTO,
        }
        media_inputs.append(
            AgentMediaInput(
                type=type_mapping.get(media_type.lower(), MediaType.AUTO),
                filename=file.filename,
                bytes_base64=content,
            )
        )

    await _load_history_into_memory(session_id)

    chat_service = get_chat_service()
    result = await chat_service.handle_chat(
        session_id=session_id,
        query=query,
        history=[],
        media_inputs=media_inputs,
        use_direct_multimodal=use_direct_multimodal,
        provider=actual_provider,
    )

    try:
        await _persist_turn(
            session=db,
            conversation_id=session_id,
            user_query=query or "[文件消息]",
            assistant_answer=result.answer,
            summary=result.summary,
            provider=actual_provider,
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Upload persist failed: {e}")
        await db.rollback()

    from langchain_core.messages import HumanMessage

    return ChatResponse(
        answer=result.answer,
        session_id=session_id,
        summary=result.summary,
        trimmed_history=[
            ChatMessage(
                role="user" if isinstance(m, HumanMessage) else "assistant",
                content=m.content,
            )
            for m in result.trimmed_history
        ],
    )