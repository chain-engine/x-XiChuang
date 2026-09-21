# -*- coding: utf-8 -*-
"""
会话 API 路由

提供会话管理、消息 CRUD 和 AI 对话接口。

职责边界：
- 本文件仅处理 HTTP 请求接入，**不实现任何业务逻辑，不直接操作数据库**
- 会话 CRUD 委托给 ``services/conversation_service.py``
- AI 推理委托给 ``services/chat_service.py``
- 辅助逻辑（provider 解析、消息转换等）封装在 ``services/chat_helpers.py``
- 所有响应使用 ``api/response.py`` 的统一响应封装
- PUT / DELETE 语义统一使用 POST 提交

接口列表：
- ``GET    /``                          — 会话列表
- ``POST   /``                          — 创建会话
- ``GET    /providers``                 — 可用模型提供商列表
- ``GET    /{id}``                      — 会话详情（含消息）
- ``POST   /{id}/update``              — 更新会话
- ``POST   /{id}/delete``              — 删除会话
- ``POST   /{id}/messages``            — 保存消息
- ``POST   /message``                  — AI 对话（JSON，非流式）
- ``POST   /stream``                   — AI 对话（SSE 流式）
- ``POST   /upload``                   — 上传文件对话
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from fastapi.responses import StreamingResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.response import success_response, paginated_response
from src.core.config import settings
from src.core.logger import logger
from src.infras.database import get_async_db
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ProviderInfo,
    ProvidersResponse,
)
from src.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    DeleteConversationResponse,
    MessageResponse,
    SaveMessagesRequest,
)
from src.services.chat_helpers import (
    build_model_info_answer,
    is_model_query,
    langchain_messages_to_schema,
    resolve_provider_model,
    to_agent_media_inputs,
    to_langchain_history,
)
from src.services.chat_service import get_chat_service
from src.services.conversation_service import ConversationService


router = APIRouter(tags=["会话"])


# ============ 依赖注入 ============


def get_conversation_service(
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> ConversationService:
    """获取会话服务实例"""
    return ConversationService(session)


# ============ 会话 CRUD 接口 ============


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="会话列表",
    description="按更新时间倒序返回会话列表，支持分页、关键词搜索和模型提供商筛选。",
)
async def list_conversations(
    request: Request,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    page: int = Query(default=1, ge=1, description="当前页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页大小，最大 100"),
    keyword: str | None = Query(default=None, description="搜索关键词（匹配标题）"),
    model_provider: str | None = Query(default=None, description="按模型提供商筛选"),
) -> Any:
    """
    获取所有会话列表

    按更新时间倒序返回，支持分页和筛选。

    Args:
        page: 页码
        page_size: 每页大小
        keyword: 搜索关键词
        model_provider: 模型提供商筛选

    Returns:
        分页会话列表
    """
    conversations, total = await service.list_conversations(
        limit=page_size,
        offset=(page - 1) * page_size,
        keyword=keyword,
        model_provider=model_provider,
    )

    items = [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            summary=conv.summary,
            model_provider=conv.model_provider,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        ).model_dump(mode="json")
        for conv in conversations
    ]

    return paginated_response(
        items=items,
        total=total,
        request=request,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ConversationResponse,
    summary="创建会话",
    description="创建一个新的对话会话。可选指定会话 ID，不提供则自动生成。",
)
async def create_conversation(
    request: Request,
    body: ConversationCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Any:
    """
    创建新会话

    Args:
        body: 创建会话请求体

    Returns:
        创建的会话信息
    """
    result = await service.create_conversation(
        conversation_id=body.id,
        title=body.title,
        model_provider=body.model_provider,
    )

    data = ConversationResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.get(
    "/providers",
    response_model=ProvidersResponse,
    summary="模型提供商列表",
    description="返回当前可用的 AI 模型提供商列表及默认提供商。",
)
async def get_providers(request: Request) -> Any:
    """
    获取可用的模型提供商列表

    Returns:
        可用提供商列表及默认提供商标识
    """
    providers = settings.get_available_providers()
    default_provider = settings.get_default_provider()

    data = ProvidersResponse(
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
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="会话详情",
    description="获取指定会话的详细信息，包含完整消息列表。",
)
async def get_conversation(
    conversation_id: str,
    request: Request,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Any:
    """
    获取会话详情（包含消息）

    Args:
        conversation_id: 会话 ID

    Returns:
        会话详情响应（含消息列表）
    """
    result = await service.get_conversation(conversation_id)

    data = ConversationDetailResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        messages=[
            MessageResponse(
                id=msg.get("id"),
                role=msg["role"],
                content=msg["content"],
                created_at=msg.get("created_at"),
            )
            for msg in result.get("messages", [])
        ],
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.post(
    "/{conversation_id}/update",
    response_model=ConversationResponse,
    summary="更新会话",
    description="更新指定会话的标题、摘要或模型提供商。PUT 语义统一使用 POST 提交。",
)
async def update_conversation(
    conversation_id: str,
    request: Request,
    body: ConversationUpdate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Any:
    """
    更新会话信息

    Args:
        conversation_id: 会话 ID
        body: 更新请求体

    Returns:
        更新后的会话信息
    """
    result = await service.update_conversation(
        conversation_id=conversation_id,
        title=body.title,
        summary=body.summary,
        model_provider=body.model_provider,
    )

    data = ConversationResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.post(
    "/{conversation_id}/delete",
    response_model=DeleteConversationResponse,
    summary="删除会话",
    description="删除指定会话及其所有消息。DELETE 语义统一使用 POST 提交。",
)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Any:
    """
    删除会话及其所有消息

    Args:
        conversation_id: 会话 ID

    Returns:
        删除结果
    """
    await service.delete_conversation(conversation_id)
    logger.info(f"Deleted conversation: {conversation_id}")

    data = DeleteConversationResponse(
        success=True,
        message="会话已删除",
        deleted_count=1,
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationDetailResponse,
    summary="保存消息",
    description="保存会话消息。如果会话不存在则自动创建。支持追加或覆盖模式。",
)
async def save_messages(
    conversation_id: str,
    request: Request,
    body: SaveMessagesRequest,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Any:
    """
    保存会话消息

    如果会话不存在则自动创建。
    每次保存会清除旧消息并添加新消息。

    Args:
        conversation_id: 会话 ID
        body: 保存消息请求

    Returns:
        更新后的会话详情
    """
    result = await service.save_messages(
        conversation_id=conversation_id,
        messages=[{"role": m.role, "content": m.content} for m in body.messages],
        clear_existing=body.clear_existing,
    )

    data = ConversationDetailResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        messages=[
            MessageResponse(
                id=msg.get("id"),
                role=msg["role"],
                content=msg["content"],
                created_at=msg.get("created_at"),
            )
            for msg in result.get("messages", [])
        ],
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


# ============ AI 对话接口 ============


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="AI 对话（非流式）",
    description="主对话接口，接收用户输入并返回 AI 回答。支持多模态输入和历史上下文。",
)
async def chat_message(
    request: Request,
    body: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    主对话接口（JSON）

    完整流程：
    1. 解析 provider / media / history
    2. 从 MySQL 加载历史到 in-memory 缓存
    3. 调用 chat_service.handle_chat
    4. 把 (user + assistant + summary) 写入 MySQL
    5. 返回响应
    """
    provider = x_model_provider or body.provider

    logger.info(
        f"Received chat request: session_id={body.session_id}, provider={provider}"
    )

    # 快速回答：用户询问当前模型
    if is_model_query(body.query):
        answer = build_model_info_answer(provider)
        data = ChatResponse(
            answer=answer,
            session_id=body.session_id,
            summary=None,
            trimmed_history=[],
        ).model_dump(mode="json")
        return success_response(data=data, request=request)

    # 从 MySQL 加载历史到 in-memory 缓存
    conv_service = ConversationService(db)
    await conv_service.load_history_to_memory(body.session_id)

    chat_service = get_chat_service()

    media_inputs = to_agent_media_inputs(body.media_inputs)
    history = to_langchain_history(body.history)

    result = await chat_service.handle_chat(
        session_id=body.session_id,
        query=body.query,
        history=history,
        media_inputs=media_inputs,
        use_direct_multimodal=body.use_direct_multimodal,
        provider=provider,
    )

    # 持久化
    try:
        await conv_service.persist_chat_turn(
            conversation_id=body.session_id,
            user_query=body.query,
            assistant_answer=result.answer,
            summary=result.summary,
            provider=provider,
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Persist turn commit failed: {e}")
        await db.rollback()

    data = ChatResponse(
        answer=result.answer,
        session_id=body.session_id,
        summary=result.summary,
        trimmed_history=langchain_messages_to_schema(result.trimmed_history),
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.post(
    "/stream",
    summary="AI 对话（流式 SSE）",
    description="流式对话接口，通过 Server-Sent Events 逐步返回 AI 回答。流式完成后一次性写库。",
)
async def chat_stream(
    request: Request,
    body: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    流式对话接口（SSE）

    流式完成后会把 (user + assistant + summary) 一次性写库。
    """
    provider = x_model_provider or body.provider

    logger.info(
        f"Received stream request: session_id={body.session_id}, provider={provider}"
    )

    # 快速回答：用户询问当前模型
    if is_model_query(body.query):
        answer = build_model_info_answer(provider)

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

    # 从 MySQL 加载历史到 in-memory 缓存
    conv_service = ConversationService(db)
    await conv_service.load_history_to_memory(body.session_id)

    media_inputs = to_agent_media_inputs(body.media_inputs)
    history = to_langchain_history(body.history)

    chat_service = get_chat_service()

    async def generate():
        full_answer = ""
        try:
            async for chunk in chat_service.handle_stream(
                session_id=body.session_id,
                query=body.query,
                history=history,
                media_inputs=media_inputs,
                use_direct_multimodal=body.use_direct_multimodal,
                provider=provider,
            ):
                if chunk:
                    full_answer += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 流结束后：尝试生成摘要、写库
            summary = None
            try:
                mem = chat_service.memory
                from langchain_core.messages import AIMessage as _AM, HumanMessage as _HM

                cur = mem.get_messages(body.session_id)
                if body.query:
                    cur.append(_HM(content=body.query))
                cur.append(_AM(content=full_answer))
                trimmed = mem.trim_messages(cur)
                mem.save_messages(body.session_id, trimmed)
                if len(trimmed) >= chat_service.memory.MAX_TURNS * 2:
                    summary = await mem.update_summary(
                        session_id=body.session_id,
                        messages=trimmed,
                        provider=provider,
                    )
                    mem.save_messages(body.session_id, trimmed)
            except Exception as e:
                logger.warning(f"Stream post-process summary failed: {e}")

            try:
                await conv_service.persist_chat_turn(
                    conversation_id=body.session_id,
                    user_query=body.query,
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


@router.post(
    "/upload",
    response_model=ChatResponse,
    summary="上传文件对话",
    description="支持上传文件的对话接口（非流式）。上传文件后与 AI 对话。",
)
async def chat_with_upload(
    request: Request,
    session_id: str = Form(..., description="会话ID"),
    query: str = Form("", description="用户文本输入"),
    use_direct_multimodal: bool = Form(False, description="是否直接走多模态模型"),
    media_type: str = Form("auto", description="媒体类型：auto/image/voice/video"),
    file: Optional[UploadFile] = File(None, description="上传文件"),
    provider: Optional[str] = Form(None, description="模型提供方"),
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    支持上传文件的对话接口（非流式）

    上传文件目前仍为非流式响应（避免 multipart + SSE 复杂度）。
    """
    actual_provider = provider or x_model_provider

    logger.info(
        f"Received upload chat: session_id={session_id}, media_type={media_type}, "
        f"provider={actual_provider}"
    )

    # 快速回答：用户询问当前模型
    if is_model_query(query):
        answer = build_model_info_answer(actual_provider)
        data = ChatResponse(
            answer=answer,
            session_id=session_id,
            summary=None,
            trimmed_history=[],
        ).model_dump(mode="json")
        return success_response(data=data, request=request)

    # 文件大小限制（默认 25MB）
    MAX_FILE_BYTES = 25 * 1024 * 1024
    media_inputs = []
    if file is not None:
        content = await file.read()
        if len(content) > MAX_FILE_BYTES:
            from src.core.exceptions import BusinessException
            raise BusinessException(
                message=f"File too large ({len(content)} > {MAX_FILE_BYTES})",
                code=413,
                status_code=413,
            )

        from src.services.chat_helpers import build_media_input_from_upload
        media_inputs.append(
            build_media_input_from_upload(content, file.filename, media_type)
        )

    # 从 MySQL 加载历史到 in-memory 缓存
    conv_service = ConversationService(db)
    await conv_service.load_history_to_memory(session_id)

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
        await conv_service.persist_chat_turn(
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

    data = ChatResponse(
        answer=result.answer,
        session_id=session_id,
        summary=result.summary,
        trimmed_history=langchain_messages_to_schema(result.trimmed_history),
    ).model_dump(mode="json")
    return success_response(data=data, request=request)
