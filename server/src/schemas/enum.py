# -*- coding: utf-8 -*-
"""
模型相关枚举定义

提供模型提供商等与模型路由相关的枚举类型。
"""

from __future__ import annotations

from enum import Enum


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
