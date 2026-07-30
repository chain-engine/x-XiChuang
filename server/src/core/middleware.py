# -*- coding: utf-8 -*-
"""
中间件模块

提供全局中间件：请求日志、异常处理、CORS、追踪ID等。
"""

from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING, Awaitable, Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.logger import logger
from src.core.response import BaseResp

if TYPE_CHECKING:
    from starlette.types import ASGIApp


# ============ 请求追踪中间件 ============

class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    请求追踪中间件

    为每个请求生成唯一的 trace_id，并在响应头中返回。
    支持通过 X-Trace-ID header 手动传递 trace_id。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 获取或生成 trace_id
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        # 将 trace_id 注入到 request state 中
        request.state.trace_id = trace_id

        # 处理请求
        response = await call_next(request)

        # 在响应头中添加 trace_id
        response.headers["X-Trace-ID"] = trace_id

        return response


# ============ 请求日志中间件 ============

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录所有 HTTP 请求的详细信息，包括：
    - 请求方法、路径、查询参数
    - 请求体（可选，敏感字段脱敏）
    - 响应状态码
    - 请求耗时
    - 客户端 IP
    - Trace ID
    """

    SENSITIVE_FIELDS: frozenset[str] = frozenset({
        "password", "token", "secret", "api_key", "authorization",
        "access_key", "access_key_id", "access_key_secret",
    })

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()
        trace_id = getattr(request.state, "trace_id", "-")

        # 记录请求
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "trace_id": trace_id,
        }

        # 脱敏处理
        log_data = self._sanitize_log_data(log_data)

        logger.info(f"--> [{trace_id}] {request.method} {request.url.path}")

        # 处理请求
        try:
            response = await call_next(request)

            # 计算耗时
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录响应
            log_level = "info" if response.status_code < 400 else "warning"
            log_func = logger.info if response.status_code < 400 else logger.warning

            log_func(
                f"<-- [{trace_id}] {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms"
            )

            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"<-- [{trace_id}] {request.method} {request.url.path} "
                f"ERROR={type(exc).__name__}: {exc} duration={duration_ms:.2f}ms"
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "-"

    def _sanitize_log_data(self, data: dict) -> dict:
        """脱敏处理敏感字段"""
        sanitized = {}
        for key, value in data.items():
            lower_key = key.lower()
            if lower_key in self.SENSITIVE_FIELDS:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_log_data(value)
            else:
                sanitized[key] = value
        return sanitized


# ============ 异常处理中间件 ============

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理中间件

    统一拦截所有未处理的异常，返回标准化的 JSON 响应。
    避免向客户端暴露敏感的堆栈信息。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            return self._handle_exception(request, exc)

    def _handle_exception(self, request: Request, exc: Exception) -> Response:
        """处理异常并返回标准化响应"""
        from fastapi.responses import JSONResponse
        from src.core.exceptions import BaseException

        trace_id = getattr(request.state, "trace_id", "-")

        if isinstance(exc, BaseException):
            # 业务异常
            logger.warning(f"[{trace_id}] Business error: {exc.message}", exc_info=True)
            return JSONResponse(
                status_code=exc.code if exc.code < 600 else 500,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "trace_id": trace_id,
                },
            )

        # 系统异常
        logger.exception(f"[{trace_id}] Unhandled exception: {exc}")

        # 根据环境返回不同详细程度的错误信息
        if settings.DEBUG:
            import traceback
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "Internal server error",
                    "detail": traceback.format_exc(),
                    "trace_id": trace_id,
                },
            )

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "trace_id": trace_id,
            },
        )


# ============ 中间件注册函数 ============

def register_middlewares(app: "ASGIApp") -> None:
    """
    注册所有中间件到应用

    中间件按注册顺序执行，所以后注册的中间件先执行。
    执行顺序：TraceID -> ExceptionHandler -> RequestLogging -> CORS

    Args:
        app: FastAPI 应用实例
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    # CORS 中间件（最外层）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 异常处理中间件
    app.add_middleware(ExceptionHandlerMiddleware)

    # 追踪 ID 中间件（最内层）
    app.add_middleware(TraceIDMiddleware)

    logger.info("All middlewares registered successfully")
