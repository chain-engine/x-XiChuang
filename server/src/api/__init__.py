# -*- coding: utf-8 -*-
"""
API 路由模块

提供 API 路由的统一管理和版本控制。
"""

from .route import api_router, api_v1_router

__all__ = [
    "api_router",
    "api_v1_router",
]
