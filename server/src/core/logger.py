# -*- coding: utf-8 -*-
"""
日志模块

提供统一的日志配置和记录功能，支持 JSON 结构化输出和控制台彩色输出。
"""

import json
import os
import sys
from typing import Any, Callable, Final

from loguru import logger

# 开发模式标识
_DEV: bool = "development" in os.getenv("ENVIRONMENT", "development")


# ============================================================================
# 日志目录路径
# ============================================================================


def get_log_dir_path() -> str:
    """获取日志目录的绝对路径"""
    from src.core.config import settings

    return str(settings.LOG_DIR_PATH)


# ============================================================================
# 辅助函数
# ============================================================================


def _get_client_ip(headers: dict[str, str]) -> str:
    """从请求头中获取客户端真实 IP"""
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = headers.get("x-real-ip", "")
    if real_ip:
        return real_ip
    return "-"


def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
    """遮蔽敏感请求头"""
    _SENSITIVE_KEYS = {"authorization", "cookie", "x-api-key", "x-token"}
    return {k: ("***" if k.lower() in _SENSITIVE_KEYS else v) for k, v in headers.items()}


# ============================================================================
# 日志格式化器
# ============================================================================


def _json_formatter(record: dict[str, Any]) -> str:
    """JSON 格式化器（文件输出）"""
    from src.core.config import settings

    record["extra"].setdefault("request_id", None)
    record["extra"].setdefault("session_id", None)

    log_record = {
        "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
        "request_id": record["extra"]["request_id"],
        "session_id": record["extra"]["session_id"],
        "app": settings.APP_NAME,
        "env": settings.ENVIRONMENT,
    }
    if record["exception"]:
        log_record["exception"] = str(record["exception"])

    return json.dumps(log_record, ensure_ascii=False) + "\n"


def _console_format(record: dict[str, Any]) -> str:
    """控制台格式化器（开发模式彩色输出）"""
    record["extra"].setdefault("request_id", None)
    record["extra"].setdefault("session_id", None)

    colors = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    reset = "\033[0m"
    level_color = colors.get(record["level"].name, "")
    ts = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    prefix = f"{level_color}{ts} | {record['level'].name:<8}{reset}"
    location = f"{record['name']}:{record['function']}:{record['line']}"
    req = f" [rid:{record['extra']['request_id']}]" if record["extra"]["request_id"] else ""
    return f"{prefix} | {location}{req} - {record['message']}\n"


def _json_serializer(obj: Any) -> str:
    """JSON 序列化器（处理不可序列化的对象）"""
    return str(obj)


# ============================================================================
# 日志配置
# ============================================================================

# 移除默认的处理器
logger.remove()

# 开发模式下添加控制台输出
if _DEV:
    logger.add(
        sink=sys.stderr,
        level="DEBUG",
        format=_console_format,
        colorize=True,
    )


def setup_logging() -> None:
    """
    初始化日志系统

    应在应用启动时调用一次。从 Settings 读取配置，
    添加文件日志 sink 和（非开发环境的）控制台 sink。
    """
    from src.core.config import settings

    # 文件日志 — JSON 格式
    file_path = settings.logging.file_path
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    logger.add(
        sink=file_path,
        rotation=settings.logging.rotation,
        retention=settings.logging.retention,
        compression=settings.logging.compression,
        level=settings.logging.level,
        format=_json_formatter,
        enqueue=True,
    )

    # 非开发环境：添加控制台输出
    if not _DEV and settings.logging.console_output:
        logger.add(
            sink=sys.stderr,
            level=settings.logging.level,
            format=_json_formatter,
            enqueue=True,
        )


# ============================================================================
# 模块导出
# ============================================================================

__all__: Final[list[str]] = [
    "logger",
    "setup_logging",
]
