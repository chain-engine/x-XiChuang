# -*- coding: utf-8 -*-
"""
API 路由注册

统一管理所有 API 路由的注册和版本控制。
"""

from __future__ import annotations

from fastapi import APIRouter

from .v1 import chat, conversations, health, milvus


# ============ API 版本路由 ============

# v1 路由
api_v1_router = APIRouter(prefix="/v1")

# 注册 v1 子路由
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_v1_router.include_router(milvus.router, prefix="/milvus", tags=["milvus"])


# ============ 主路由注册 ============

# API 主路由（包含所有版本）
api_router = APIRouter(prefix="/api")

# 注册 v1 路由
api_router.include_router(api_v1_router)


__all__ = [
    "api_router",
    "api_v1_router",
]
