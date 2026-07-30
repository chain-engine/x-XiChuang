# -*- coding: utf-8 -*-
"""
模型路由模块

支持多个大模型提供商的路由和切换。
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple

from langchain_openai import ChatOpenAI

from src.core.config import Settings, settings
from src.core.logger import logger


class ModelProvider(str, Enum):
    """
    支持的模型提供商枚举
    """

    tongyi = "tongyi"      # 千问（默认）
    deepseek = "deepseek"  # DeepSeek
    glm = "glm"            # 智谱/GLM
    doubao = "doubao"      # 火山/豆包
    kimi = "kimi"          # 月之暗面/Kimi
    mock = "mock"          # 本地Mock（用于测试）


def build_chat_model(
    settings: Settings,
    preferred: str | None = None,
) -> Tuple[ChatOpenAI, ModelProvider]:
    """
    根据优先级创建 ChatOpenAI 实例。

    策略：
    1. 如果 preferred 显式指定且配置完整，则使用指定提供商；
    2. 否则按优先级选择：tongyi > deepseek > glm > doubao > kimi > mock

    Args:
        settings: 全局配置对象（包含 API Key、Base URL、Model 名称等）
        preferred: 优先使用的提供方（可选；例如 'tongyi'）

    Returns:
        (llm, provider): ChatOpenAI 实例和实际使用的提供商枚举
    """

    # 默认优先级顺序
    priority_order: list[ModelProvider] = [
        ModelProvider.tongyi,
        ModelProvider.deepseek,
        ModelProvider.glm,
        ModelProvider.doubao,
        ModelProvider.kimi,
    ]

    # 如果指定了优先提供商，先尝试使用
    if preferred:
        try:
            provider = ModelProvider(preferred)
        except ValueError:
            logger.warning(f"Unknown provider: {preferred}, using default")
            provider = None
        else:
            if settings.validate_model_config(provider.value):
                return _build_for_provider(settings, provider), provider

    # 按默认优先级选择
    for provider in priority_order:
        if settings.validate_model_config(provider.value):
            return _build_for_provider(settings, provider), provider

    # 最后兜底 mock（如果用户没有配置任何真实模型）
    provider = ModelProvider.mock
    model = ChatOpenAI(
        api_key="dummy-key",
        base_url="http://localhost:8001/v1",
        model="mock-model",
        temperature=settings.TEMPERATURE,
    )
    return model, provider


def _build_for_provider(settings: Settings, provider: ModelProvider) -> ChatOpenAI:
    """
    根据提供商构建对应的 ChatOpenAI 实例

    Args:
        settings: 配置对象
        provider: 提供商枚举

    Returns:
        ChatOpenAI 实例
    """
    configs = {
        ModelProvider.tongyi: {
            "api_key": settings.ALIYUN_API_KEY,
            "base_url": settings.ALIYUN_API_BASE,
            "model": settings.ALIYUN_MODEL_NAME,
        },
        ModelProvider.deepseek: {
            "api_key": settings.DEEPSEEK_API_KEY,
            "base_url": settings.DEEPSEEK_API_BASE,
            "model": settings.DEEPSEEK_MODEL_NAME,
        },
        ModelProvider.glm: {
            "api_key": settings.GLM_API_KEY,
            "base_url": settings.GLM_API_BASE,
            "model": settings.GLM_MODEL_NAME,
        },
        ModelProvider.doubao: {
            "api_key": settings.DOUBAO_API_KEY,
            "base_url": settings.DOUBAO_API_BASE,
            "model": settings.DOUBAO_MODEL_NAME,
        },
        ModelProvider.kimi: {
            "api_key": settings.KIMI_API_KEY,
            "base_url": settings.KIMI_API_BASE,
            "model": settings.KIMI_MODEL_NAME,
        },
    }

    config = configs.get(provider, {})
    return ChatOpenAI(
        api_key=config.get("api_key", "dummy-key"),
        base_url=config.get("base_url", "http://localhost:8001/v1"),
        model=config.get("model", "mock-model"),
        temperature=settings.TEMPERATURE,
    )
