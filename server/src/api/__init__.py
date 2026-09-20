# -*- coding: utf-8 -*-
"""
API 路由模块

提供 API 路由的统一管理和版本控制，以及统一响应构造。
"""

from .response import error_response, paginated_response, success_response
from .router import api_router, api_v1_router

__all__ = [
    "api_router",
    "api_v1_router",
    "success_response",
    "error_response",
    "paginated_response",
]
