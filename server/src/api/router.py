# -*- coding: utf-8 -*-
"""
API 路由注册

统一管理所有 API 路由的注册和版本控制。

路由层级：
    app → api_router(prefix="/api") → router(prefix="/v1") → 各业务路由

版本约定：
    - v1 路由统一放在 ``api/v1/`` 下，每个模块自行声明 ``APIRouter(tags=[...])``
    - 新版本（v2）只需在 ``api/v2/`` 下新增模块并注册到新版本路由
    - 向后兼容通过多版本路由实现，旧版本路由保持不变
"""

from __future__ import annotations

from fastapi import APIRouter

from .v1 import conversations, health, milvus


# ============ v1 路由 ============

router = APIRouter(prefix="/v1")

# 各模块路由已在自身声明 tags，此处无需重复
router.include_router(health.router)
router.include_router(conversations.router, prefix="/conversations")
router.include_router(milvus.router, prefix="/milvus")


# ============ 主路由注册 ============

api_router = APIRouter(prefix="/api")
api_router.include_router(router)


__all__ = [
    "api_router",
    "router",
]
