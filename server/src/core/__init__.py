# -*- coding: utf-8 -*-
"""
核心层模块

提供框架级底层核心能力：配置、日志、异常、中间件、统一响应。
"""

from .config import settings
from .exceptions import (
    AppException,
    BaseException,
    BusinessException,
    BusinessError,
    SystemException,
    SystemError,
    register_exception_handlers,
)
from .logger import logger, setup_logging

__all__ = [
    "settings",
    "logger",
    "setup_logging",
    "AppException",
    "BusinessException",
    "SystemException",
    "register_exception_handlers",
    # 向后兼容别名
    "BaseException",
    "BusinessError",
    "SystemError",
]
