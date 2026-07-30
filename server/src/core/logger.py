# -*- coding: utf-8 -*-
"""
日志模块

提供统一的日志配置和记录功能，支持请求上下文追踪。
"""

import os
import sys
from contextvars import ContextVar
from typing import Callable, Final

from loguru import logger

# ============================================================================
# 上下文变量
# ============================================================================

# 请求 ID 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# 会话 ID 上下文变量
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


# ============================================================================
# 上下文管理函数
# ============================================================================

def generate_request_id() -> str:
    """生成唯一的请求 ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def bind_request_id(request_id: str) -> None:
    """绑定请求 ID 到当前上下文"""
    request_id_var.set(request_id)


def get_request_id() -> str:
    """获取当前请求 ID"""
    return request_id_var.get()


def bind_session_id(session_id: str) -> None:
    """绑定会话 ID 到当前上下文"""
    session_id_var.set(session_id)


def get_session_id() -> str:
    """获取当前会话 ID"""
    return session_id_var.get()


def clear_context() -> None:
    """清除上下文变量"""
    request_id_var.set("")
    session_id_var.set("")


# ============================================================================
# 日志格式化器
# ============================================================================

class ContextFormatter:
    """上下文感知的日志格式化器"""

    def __call__(self, record: dict) -> str:
        # 添加请求 ID 到日志记录
        request_id = request_id_var.get()
        if request_id:
            record["extra"]["request_id"] = request_id

        # 添加会话 ID 到日志记录
        session_id = session_id_var.get()
        if session_id:
            record["extra"]["session_id"] = session_id

        return (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{extra[request_id]:[request_id]} "
            "{extra[session_id]:|[session_id]} "
            "- {message}\n"
        )


# ============================================================================
# 日志配置
# ============================================================================

# 确保日志目录存在
log_dir: Final[str] = 'logs'
os.makedirs(log_dir, exist_ok=True)

# 移除默认的处理器
logger.remove()

# 配置日志格式化器
formatter = ContextFormatter()

# 配置日志输出到文件
logger.add(
    os.path.join(log_dir, 'x-langchain_{time}.log'),
    rotation='1 day',
    retention='7 days',
    compression='zip',
    level='INFO',
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra[request_id]:[request_id]} {extra[session_id]:|[session_id]} - {message}",
)

# 配置日志输出到控制台
console_sink: Callable[[str], None] = lambda msg: print(msg, end="")
logger.add(
    sink=console_sink,
    level='DEBUG',
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra[request_id]:[request_id]} {extra[session_id]:|[session_id]} - {message}",
)

# 导出
__all__: Final[list[str]] = [
    'logger',
    'request_id_var',
    'session_id_var',
    'generate_request_id',
    'bind_request_id',
    'get_request_id',
    'bind_session_id',
    'get_session_id',
    'clear_context',
]
