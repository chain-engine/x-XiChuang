# -*- coding: utf-8 -*-
"""
对话 Schema 定义

包含聊天接口的请求和响应模型。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


class MediaInput(BaseModel):
    """媒体输入"""

    type: str = Field(..., description="媒体类型：text/voice/image/video/audio/auto")
    filename: str | None = Field(None, description="文件名")
    bytes_base64: str | None = Field(None, description="Base64 编码的文件内容")
    url: str | None = Field(None, description="文件 URL")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class ChatMessage(BaseModel):
    """对话历史中的单条消息"""

    role: str = Field(..., description="消息角色：'user' / 'assistant'")
    content: str = Field(..., description="消息文本内容")
    name: str | None = Field(None, description="消息发送者名称")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class ChatRequest(BaseModel):
    """标准对话请求体（JSON）"""

    session_id: str = Field(..., description="会话ID")
    query: str = Field(..., description="用户本轮输入的文本", min_length=1)
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="对话历史（可选）"
    )
    media_inputs: list[MediaInput] = Field(
        default_factory=list,
        description="多模态输入列表（可选）"
    )
    use_direct_multimodal: bool = Field(
        default=False,
        description="是否直接走多模态模型"
    )
    provider: str | None = Field(
        default=None,
        description="模型提供方：tongyi/deepseek/glm/doubao/kimi"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "abc123",
                "query": "你好，请介绍一下你自己",
                "history": [],
                "media_inputs": [],
                "use_direct_multimodal": False,
                "provider": "tongyi",
            }
        }
    }


class StreamChatRequest(BaseModel):
    """流式对话请求"""

    session_id: str = Field(..., description="会话ID")
    query: str = Field(..., description="用户本轮输入的文本")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="对话历史（可选）"
    )
    media_inputs: list[MediaInput] = Field(
        default_factory=list,
        description="多模态输入列表（可选）"
    )
    use_direct_multimodal: bool = Field(
        default=False,
        description="是否直接走多模态模型"
    )
    provider: str | None = Field(
        default=None,
        description="模型提供方"
    )


class UploadChatRequest(BaseModel):
    """上传文件对话请求"""

    session_id: str = Field(..., description="会话ID")
    query: str = Field(default="", description="用户文本输入")
    media_type: str = Field(default="auto", description="媒体类型：text/voice/image/video/audio/auto")
    use_direct_multimodal: bool = Field(default=False, description="是否直接走多模态模型")
    provider: str | None = Field(default=None, description="模型提供方")


class ChatResponse(BaseModel):
    """对话响应体"""

    answer: str = Field(..., description="回答文本")
    session_id: str = Field(..., description="会话ID")
    summary: str | None = Field(default=None, description="对话摘要")
    trimmed_history: list[ChatMessage] = Field(
        default_factory=list,
        description="裁剪后的对话历史"
    )
    model_info: dict[str, str] | None = Field(
        default=None,
        description="模型信息"
    )


class StreamChunk(BaseModel):
    """流式响应数据块"""

    content: str = Field(..., description="文本片段")
    done: bool = Field(default=False, description="是否完成")
    full_answer: str | None = Field(None, description="完整回答（仅 done=true 时）")
    error: str | None = Field(None, description="错误信息")


class ProviderInfo(BaseModel):
    """模型提供商信息"""

    name: str = Field(..., description="提供商名称")
    display_name: str = Field(..., description="显示名称")
    model_name: str = Field(..., description="模型名称")
    available: bool = Field(..., description="是否可用")


class ProvidersResponse(BaseModel):
    """可用模型提供商列表响应"""

    providers: list[ProviderInfo] = Field(..., description="提供商列表")
    default: str = Field(..., description="默认提供商")


class ChatStreamResponse(BaseModel):
    """流式对话响应（SSE 事件数据）"""

    event: str = Field(default="message", description="事件类型")
    data: dict[str, Any] = Field(..., description="事件数据")


# ============ LangGraph 状态与结果定义 ============


class ChatGraphState(BaseModel):
    """
    LangGraph 对话状态

    Attributes:
        messages: 当前所有对话消息
        media_inputs: 本次请求的多模态输入
        query: 用户文本问题
        use_direct_multimodal: 是否直接走多模态模型
        provider: 模型提供方
        answer: 模型回答
        summary: 对话摘要
        session_id: 真实会话 ID（用于记忆路由）
    """

    messages: list["BaseMessage"] = Field(default_factory=list)
    media_inputs: list[MediaInput] = Field(default_factory=list)
    query: str = ""
    use_direct_multimodal: bool = True
    provider: str | None = None
    answer: str | None = None
    summary: str | None = None
    session_id: str = ""

    # Pydantic v2: 允许节点直接修改字段（LangGraph 默认会原地写）
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ChatServiceResult(BaseModel):
    """
    对话服务结果

    Attributes:
        answer: 回答文本
        summary: 对话摘要
        trimmed_history: 裁剪后的对话历史
    """

    answer: str = Field(..., description="回答文本")
    summary: str | None = Field(None, description="对话摘要")
    trimmed_history: list[BaseMessage] = Field(default_factory=list, description="裁剪后的对话历史")
