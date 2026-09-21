# -*- coding: utf-8 -*-
"""
对话辅助工具模块

封装对话流程中可复用的业务逻辑，供 service 层调用。
API 层不应直接使用本模块。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable, Optional, Tuple

from src.core.config import settings
from src.constants.enums import MediaType

if TYPE_CHECKING:
    from src.agent.media import MediaInput as AgentMediaInput


# ============ Provider 解析 ============

_PROVIDER_MAP: dict[str, Tuple[str, str]] = {
    "tongyi": ("千问", settings.ALIYUN_MODEL_NAME),
    "deepseek": ("DeepSeek", settings.DEEPSEEK_MODEL_NAME),
    "glm": ("GLM", settings.GLM_MODEL_NAME),
    "doubao": ("豆包", settings.DOUBAO_MODEL_NAME),
    "kimi": ("Kimi", settings.KIMI_MODEL_NAME),
}


def resolve_provider_model(provider: Optional[str]) -> Tuple[str, str, str]:
    """
    解析当前请求实际使用的 provider / display_name / model_name。

    Args:
        provider: 请求指定的 provider 标识

    Returns:
        (provider_key, display_name, model_name) 三元组
    """
    selected = (provider or "").strip().lower()
    if selected not in _PROVIDER_MAP:
        selected = settings.get_default_provider()

    display_name, model_name = _PROVIDER_MAP.get(selected, ("未知", "unknown"))
    return selected, display_name, model_name


def build_model_info_answer(provider: Optional[str]) -> str:
    """
    构造「当前模型信息」的回答文本。

    当用户询问当前使用的模型时调用。

    Args:
        provider: 请求指定的 provider 标识

    Returns:
        格式化的模型信息字符串
    """
    p, display_name, model_name = resolve_provider_model(provider)
    return f"当前会话绑定模型为：{display_name}（provider: {p}，model: {model_name}）"


def is_model_query(query: str) -> bool:
    """
    判断用户是否在询问当前使用的模型。

    Args:
        query: 用户输入文本

    Returns:
        True 表示用户在询问模型信息
    """
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


# ============ 多模态输入转换 ============


_TYPE_MAPPING: dict[str, MediaType] = {
    "text": MediaType.TEXT,
    "voice": MediaType.VOICE,
    "audio": MediaType.AUDIO,
    "image": MediaType.IMAGE,
    "video": MediaType.VIDEO,
    "auto": MediaType.AUTO,
}


def to_agent_media_inputs(items: Iterable) -> list:
    """
    把 schema 层的 MediaInput 转成 agent 层使用的 MediaInput。

    Args:
        items: schema 层 MediaInput 可迭代对象

    Returns:
        agent 层 MediaInput 列表
    """
    from src.agent.media import MediaInput as AgentMediaInput

    result = []
    for mi in items:
        result.append(
            AgentMediaInput(
                type=_TYPE_MAPPING.get(mi.type.lower(), MediaType.AUTO),
                filename=mi.filename,
                url=mi.url,
                bytes_base64=mi.bytes_base64,
            )
        )
    return result


def build_media_input_from_upload(
    content: bytes,
    filename: str | None,
    media_type: str,
) -> "AgentMediaInput":
    """
    从上传文件内容构建 agent 层 MediaInput。

    Args:
        content: 文件二进制内容
        filename: 文件名
        media_type: 媒体类型标识

    Returns:
        agent 层 MediaInput 实例
    """
    from src.agent.media import MediaInput as AgentMediaInput

    return AgentMediaInput(
        type=_TYPE_MAPPING.get(media_type.lower(), MediaType.AUTO),
        filename=filename,
        bytes_base64=content,
    )


# ============ LangChain 消息转换 ============


def to_langchain_history(items: Iterable) -> list:
    """
    把 schema 层的 ChatMessage 转成 LangChain 消息列表。

    Args:
        items: schema 层 ChatMessage 可迭代对象

    Returns:
        LangChain BaseMessage 列表
    """
    from langchain_core.messages import AIMessage, HumanMessage

    out = []
    for msg in items:
        if msg.role == "user":
            out.append(HumanMessage(content=msg.content))
        else:
            out.append(AIMessage(content=msg.content))
    return out


def langchain_messages_to_schema(messages: Iterable) -> list:
    """
    把 LangChain 消息列表转成 schema 层 ChatMessage 字典列表。

    Args:
        messages: LangChain BaseMessage 可迭代对象

    Returns:
        包含 role 和 content 的字典列表
    """
    from langchain_core.messages import HumanMessage

    result = []
    for m in messages:
        result.append({
            "role": "user" if isinstance(m, HumanMessage) else "assistant",
            "content": m.content,
        })
    return result
