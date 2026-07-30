# -*- coding: utf-8 -*-
"""
API v1 版本路由

包含所有 v1 版本的 API 路由定义。
"""

from . import health, chat, conversations, milvus

__all__ = [
    "health",
    "chat",
    "conversations",
    "milvus",
]
