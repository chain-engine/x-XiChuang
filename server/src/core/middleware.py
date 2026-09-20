# -*- coding: utf-8 -*-
"""
中间件模块

提供全局中间件：请求追踪、请求日志、异常处理。
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Awaitable, Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logger import logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp


# ============ 请求追踪中间件 ============


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求 ID 中间件

    为每个请求生成唯一的 request_id，注入 logger 上下文，
    并在响应头中返回 X-Request-ID。
    支持通过 X-Request-ID header 手动传递 request_id。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
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
    - Request ID
    """

    SENSITIVE_HEADERS: frozenset[str] = frozenset({
        "authorization", "cookie", "x-api-key", "x-token",
    })

    SENSITIVE_BODY_FIELDS: frozenset[str] = frozenset({
        "password", "token", "secret", "api_key",
        "access_key", "access_key_id", "access_key_secret",
    })

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        # 记录请求
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "headers": self._mask_headers(dict(request.headers)),
            "request_id": request_id,
        }

        logger.info(f"--> [{request_id}] {request.method} {request.url.path}")

        # 处理请求
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            log_level = "info" if response.status_code < 400 else "warning"
            log_func = logger.info if response.status_code < 400 else logger.warning
            log_func(
                f"<-- [{request_id}] {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms"
            )
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"<-- [{request_id}] {request.method} {request.url.path} "
                f"ERROR={type(exc).__name__}: {exc} duration={duration_ms:.2f}ms"
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        if request.client:
            return request.client.host
        return "-"

    def _mask_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """遮蔽敏感请求头"""
        return {
            k: ("***" if k.lower() in self.SENSITIVE_HEADERS else v)
            for k, v in headers.items()
        }


# ============ 异常处理中间件 ============


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
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

        from src.core.config import settings
        from src.core.exceptions import AppException

        request_id = getattr(request.state, "request_id", "-")

        if isinstance(exc, AppException):
            logger.warning(
                f"[{request_id}] Business error: {exc.message}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=exc.status_code if exc.status_code < 600 else 500,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                },
            )

        # 系统异常
        logger.exception(f"[{request_id}] Unhandled exception: {exc}")

        if settings.DEBUG:
            import traceback

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "Internal server error",
                    "detail": traceback.format_exc(),
                    "request_id": request_id,
                },
            )

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id,
            },
        )


# ============ API Key 鉴权中间件 ============


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """
    API Key 鉴权中间件

    通过环境变量 API_KEY 配置静态密钥（多个用英文逗号分隔）。
    客户端在请求头 X-API-Key 中传递。
    未配置 API_KEY 时跳过校验（开发模式）。
    """

    # 跳过鉴权的路径前缀
    _SKIP_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/openapi.json", "/health")

    def __init__(self, app: "ASGIApp") -> None:
        super().__init__(app)
        self._keys: list[str] = self._load_keys()

    @staticmethod
    def _load_keys() -> list[str]:
        import os
        raw = os.getenv("API_KEY", "").strip()
        return [k.strip() for k in raw.split(",") if k.strip()] if raw else []

    def reload_keys(self) -> None:
        """热加载 API Key（供测试或配置更新使用）"""
        self._keys = self._load_keys()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 未配置密钥 → 开发模式，直接放行
        if not self._keys:
            return await call_next(request)

        # 跳过不需要鉴权的路径
        if request.url.path.startswith(self._SKIP_PREFIXES):
            return await call_next(request)

        # 校验 X-API-Key
        api_key = request.headers.get("x-api-key", "")
        if not api_key or api_key not in self._keys:
            from fastapi.responses import JSONResponse

            request_id = getattr(request.state, "request_id", "-")
            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "message": "Invalid or missing API key",
                    "request_id": request_id,
                },
            )

        return await call_next(request)


# ============ 中间件注册函数 ============


def setup_middlewares(app: "ASGIApp") -> None:
    """
    注册所有中间件到应用

    中间件按注册顺序执行，后注册的中间件先执行。
    执行顺序：RequestID → ExceptionHandling → RequestLogging → CORS

    Args:
        app: FastAPI 应用实例
    """
    from fastapi import FastAPI

    from src.core.config import settings

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    # CORS 中间件（最外层）
    cors_origins = settings.CORS_ORIGINS
    if settings.CORS_ALLOW_CREDENTIALS and "*" in cors_origins:
        cors_origins = [
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 异常处理中间件
    app.add_middleware(ExceptionHandlingMiddleware)

    # API Key 鉴权中间件
    app.add_middleware(ApiKeyMiddleware)

    # 请求 ID 中间件（最内层）
    app.add_middleware(RequestIDMiddleware)

    logger.info("All middlewares registered successfully")
