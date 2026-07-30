# -*- coding: utf-8 -*-
"""
聊天 API 路由

提供对话和文件上传接口。
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import StreamingResponse

from src.core.config import settings
from src.core.logger import logger
from src.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MediaInput,
    ProviderInfo,
    ProvidersResponse,
)
from src.services.chat_service import get_chat_service


router = APIRouter()


def _resolve_provider_model(provider: Optional[str]) -> tuple[str, str, str]:
    """
    解析当前请求实际使用的 provider/model

    Args:
        provider: 请求指定的 provider

    Returns:
        (provider, display_name, model_name)
    """
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
    """判断用户是否在询问当前使用的模型"""
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


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers() -> ProvidersResponse:
    """
    获取可用的模型提供商列表

    Returns:
        ProvidersResponse: 提供商列表和默认提供商
    """
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


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
) -> ChatResponse:
    """
    主对话接口（JSON）

    Args:
        request: 对话请求
        x_model_provider: Header 中指定的模型提供方

    Returns:
        ChatResponse: 对话响应
    """
    # 合并 provider 参数
    provider = x_model_provider or request.provider

    logger.info(
        f"Received chat request: session_id={request.session_id}, provider={provider}"
    )

    # 处理模型查询
    if _is_current_model_query(request.query):
        p, display_name, model_name = _resolve_provider_model(provider)
        return ChatResponse(
            answer=f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）",
            session_id=request.session_id,
            summary=None,
            trimmed_history=[],
        )

    # 执行对话
    chat_service = get_chat_service()

    # 转换 media_inputs
    media_inputs = []
    for mi in request.media_inputs:
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
                type=type_mapping.get(mi.type.lower(), MediaType.AUTO),
                filename=mi.filename,
                bytes_base64=mi.bytes_base64,
            )
        )

    # 转换历史消息
    from langchain_core.messages import HumanMessage, AIMessage
    history = []
    for msg in request.history:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    # 执行对话
    result = await chat_service.handle_chat(
        session_id=request.session_id,
        query=request.query,
        history=history,
        media_inputs=media_inputs,
        use_direct_multimodal=request.use_direct_multimodal,
        provider=provider,
    )

    return ChatResponse(
        answer=result.answer,
        session_id=request.session_id,
        summary=result.summary,
        trimmed_history=[
            ChatMessage(role="user" if isinstance(m, HumanMessage) else "assistant", content=m.content)
            for m in result.trimmed_history
        ],
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
):
    """
    流式对话接口（SSE）

    返回 Server-Sent Events 流。

    Args:
        request: 对话请求
        x_model_provider: Header 中指定的模型提供方

    Returns:
        StreamingResponse: SSE 流
    """
    provider = x_model_provider or request.provider

    logger.info(
        f"Received stream request: session_id={request.session_id}, provider={provider}"
    )

    # 处理模型查询
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

    async def generate():
        try:
            chat_service = get_chat_service()

            # 转换历史消息
            from langchain_core.messages import HumanMessage, AIMessage
            history = []
            for msg in request.history:
                if msg.role == "user":
                    history.append(HumanMessage(content=msg.content))
                else:
                    history.append(AIMessage(content=msg.content))

            # 流式生成
            full_answer = ""
            async for chunk in chat_service.handle_stream(
                session_id=request.session_id,
                query=request.query,
                history=history,
                media_inputs=[],
                use_direct_multimodal=request.use_direct_multimodal,
                provider=provider,
            ):
                full_answer += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

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


@router.post("/upload", response_model=ChatResponse)
async def chat_with_upload(
    session_id: str = Form(...),
    query: str = Form(""),
    use_direct_multimodal: bool = Form(False),
    media_type: str = Form("auto"),
    file: Optional[UploadFile] = File(None),
    provider: Optional[str] = Form(None),
    x_model_provider: Annotated[Optional[str], Header(alias="X-Model-Provider")] = None,
) -> ChatResponse:
    """
    支持上传文件的对话接口

    Args:
        session_id: 会话ID
        query: 用户文本输入
        use_direct_multimodal: 是否直接走多模态模型
        media_type: 媒体类型
        file: 上传的文件
        provider: 表单中的模型提供方
        x_model_provider: Header 中指定的模型提供方

    Returns:
        ChatResponse: 对话响应
    """
    actual_provider = provider or x_model_provider

    logger.info(
        f"Received upload chat: session_id={session_id}, media_type={media_type}, "
        f"provider={actual_provider}"
    )

    # 处理模型查询
    if _is_current_model_query(query):
        p, display_name, model_name = _resolve_provider_model(actual_provider)
        return ChatResponse(
            answer=f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）",
            session_id=session_id,
            summary=None,
            trimmed_history=[],
        )

    # 处理文件上传
    media_inputs = []
    if file is not None:
        content = await file.read()

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

    # 执行对话
    chat_service = get_chat_service()
    result = await chat_service.handle_chat(
        session_id=session_id,
        query=query,
        history=[],
        media_inputs=media_inputs,
        use_direct_multimodal=use_direct_multimodal,
        provider=actual_provider,
    )

    from langchain_core.messages import HumanMessage, AIMessage

    return ChatResponse(
        answer=result.answer,
        session_id=session_id,
        summary=result.summary,
        trimmed_history=[
            ChatMessage(role="user" if isinstance(m, HumanMessage) else "assistant", content=m.content)
            for m in result.trimmed_history
        ],
    )
