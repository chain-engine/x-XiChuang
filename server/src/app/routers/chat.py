# -*- coding: utf-8 -*-
"""
聊天 API 路由

提供对话和文件上传接口。
"""

import json
import re
from typing import List, Optional

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.core.logger import logger
from src.app.services.chat_service import ChatService
from src.agent.media import MediaInput, MediaType


router = APIRouter()
chat_service = ChatService()


def _resolve_provider_model(provider: Optional[str]) -> tuple[str, str, str]:
    """
    解析当前请求实际使用的 provider/model，并返回用于展示的信息。
    Returns:
        (provider, display_name, model_name)
    """
    from src.config.settings import settings

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


class ChatMessage(BaseModel):
    """对话历史中的单条消息"""

    role: str = Field(..., description="消息角色：'user' / 'assistant'")
    content: str = Field(..., description="消息文本内容")


class ChatRequest(BaseModel):
    """标准对话请求体（JSON）"""

    session_id: str = Field(..., description="会话ID")
    query: str = Field(..., description="用户本轮输入的文本")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="对话历史（可选）",
    )
    media_inputs: List[MediaInput] = Field(
        default_factory=list,
        description="多模态输入列表（可选）",
    )
    use_direct_multimodal: bool = Field(
        default=False,
        description="是否直接走多模态模型",
    )
    provider: Optional[str] = Field(
        default=None,
        description="模型提供方：tongyi/deepseek/glm/doubao/kimi",
    )


class ChatResponse(BaseModel):
    """对话响应体"""

    answer: str = Field(..., description="回答文本")
    session_id: str = Field(..., description="会话ID")
    summary: Optional[str] = Field(default=None, description="对话摘要")
    trimmed_history: List[ChatMessage] = Field(
        default_factory=list,
        description="裁剪后的对话历史",
    )


class ProviderInfo(BaseModel):
    """模型提供商信息"""

    name: str = Field(..., description="提供商名称")
    display_name: str = Field(..., description="显示名称")
    available: bool = Field(..., description="是否可用")


class ProvidersResponse(BaseModel):
    """可用模型提供商列表响应"""

    providers: List[ProviderInfo] = Field(..., description="提供商列表")
    default: str = Field(..., description="默认提供商")


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers() -> ProvidersResponse:
    """
    获取可用的模型提供商列表

    返回所有配置的模型提供商及其可用状态。
    """
    from src.config.settings import settings

    providers = settings.get_available_providers()
    default_provider = settings.get_default_provider()

    return ProvidersResponse(
        providers=[
            ProviderInfo(
                name=p["name"],
                display_name=p["display_name"],
                available=p["available"],
            )
            for p in providers
        ],
        default=default_provider,
    )


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    x_model_provider: Optional[str] = Header(default=None, alias="X-Model-Provider"),
) -> ChatResponse:
    """
    主对话接口（JSON）

    Args:
        request: 对话请求
        x_model_provider: Header 中指定的模型提供方

    Returns:
        对话响应
    """
    if x_model_provider:
        request.provider = x_model_provider

    logger.info(
        "Received chat request for session_id=%s, provider=%s",
        request.session_id,
        request.provider,
    )

    if _is_current_model_query(request.query):
        provider, display_name, model_name = _resolve_provider_model(request.provider)
        answer = (
            f"当前会话绑定模型为：{display_name}（provider: {provider}，model: {model_name}）。"
            "该信息由服务端配置直接返回。"
        )
        return ChatResponse(
            answer=answer,
            session_id=request.session_id,
            summary=None,
            trimmed_history=[],
        )

    result = await chat_service.handle_chat(request)

    return ChatResponse(
        answer=result.answer,
        session_id=request.session_id,
        summary=result.summary,
        trimmed_history=[
            ChatMessage(role=m.role, content=m.content) for m in result.trimmed_history
        ],
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    x_model_provider: Optional[str] = Header(default=None, alias="X-Model-Provider"),
):
    """
    流式对话接口（SSE）

    返回 Server-Sent Events 流，每个事件包含一个文本片段。
    """
    if x_model_provider:
        request.provider = x_model_provider

    logger.info(
        "Received stream request for session_id=%s, provider=%s",
        request.session_id,
        request.provider,
    )

    if _is_current_model_query(request.query):
        provider, display_name, model_name = _resolve_provider_model(request.provider)
        answer = (
            f"当前会话绑定模型为：{display_name}（provider: {provider}，model: {model_name}）。"
            "该信息由服务端配置直接返回。"
        )

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
            # 知识库检索（可选，简化版）
            from src.agent.knowledge import knowledge_base
            query = request.query
            if query.strip():
                snippets = await knowledge_base.aretrieve(query, k=4)
                if snippets:
                    joined = "\n\n---\n\n".join(snippets)
                    query = f"{query}\n\n[知识库检索结果]\n{joined}"

            # 流式生成
            from src.agent.multimodal import MultimodalModelClient
            from src.agent.memory import ConversationMemory
            from langchain_core.messages import HumanMessage, AIMessage

            client = MultimodalModelClient()
            memory = ConversationMemory()

            # 获取历史
            history = memory.get_messages(request.session_id)
            for msg in request.history:
                if msg.role == "user":
                    history.append(HumanMessage(content=msg.content))
                else:
                    history.append(AIMessage(content=msg.content))

            full_answer = ""
            async for chunk in client.stream_chat(
                session_id=request.session_id,
                query=query,
                history=history,
                media_inputs=request.media_inputs or [],
                use_direct_multimodal=request.use_direct_multimodal,
                provider=request.provider,
            ):
                full_answer += chunk
                # SSE 格式
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'done': True, 'full_answer': full_answer}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("Stream error: %s", e)
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
    x_model_provider: Optional[str] = Header(default=None, alias="X-Model-Provider"),
) -> ChatResponse:
    """
    支持上传文件的对话接口

    Args:
        session_id: 会话ID
        query: 用户文本输入
        use_direct_multimodal: 是否直接走多模态模型
        media_type: 媒体类型（text/voice/image/video/audio/auto）
        file: 上传的文件
        provider: 表单中的模型提供方
        x_model_provider: Header 中指定的模型提供方

    Returns:
        对话响应
    """
    # 优先使用表单中的 provider，其次使用 Header
    actual_provider = provider or x_model_provider

    logger.info(
        "Received upload chat for session_id=%s, media_type=%s, provider=%s",
        session_id,
        media_type,
        actual_provider,
    )

    if _is_current_model_query(query):
        provider, display_name, model_name = _resolve_provider_model(actual_provider)
        answer = (
            f"当前会话绑定模型为：{display_name}（provider: {provider}，model: {model_name}）。"
            "该信息由服务端配置直接返回。"
        )
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            summary=None,
            trimmed_history=[],
        )

    media_inputs: List[MediaInput] = []

    if file is not None:
        content = await file.read()

        # 映射媒体类型
        type_mapping = {
            "text": MediaType.TEXT,
            "voice": MediaType.VOICE,
            "audio": MediaType.AUDIO,
            "image": MediaType.IMAGE,
            "video": MediaType.VIDEO,
            "auto": MediaType.AUTO,
        }
        mapped_type = type_mapping.get(media_type.lower(), MediaType.AUTO)

        media_inputs.append(
            MediaInput(
                type=mapped_type,
                filename=file.filename,
                bytes_base64=content,
            )
        )

    request = ChatRequest(
        session_id=session_id,
        query=query,
        media_inputs=media_inputs,
        use_direct_multimodal=use_direct_multimodal,
        provider=actual_provider,
    )

    result = await chat_service.handle_chat(request)

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
