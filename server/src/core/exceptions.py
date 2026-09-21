# -*- coding: utf-8 -*-
"""
全局异常定义模块

定义应用异常层次结构，提供全局异常处理器注册。

职责：
1. 定义统一的异常类层次（AppException -> BusinessException / SystemException）
2. 注册全局异常处理器，将所有异常转换为标准 JSONResponse
3. 404、405、500、限流、权限等异常全部在此捕获，**不对外暴露原始堆栈**

异常层次::

    AppException
    ├── BusinessException (4xx)
    │   ├── NotFoundError (404)
    │   ├── ValidationError (400)
    │   ├── UnauthorizedError (401)
    │   ├── ForbiddenError (403)
    │   ├── ConflictError (409)
    │   └── RateLimitError (429)
    └── SystemException (5xx)
        ├── DatabaseError
        ├── ExternalServiceError
        ├── EmbeddingError
        ├── GenerationError
        └── ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from fastapi import FastAPI, Request


# ============================================================================
# 异常基类
# ============================================================================


class AppException(Exception):
    """
    应用异常基类

    所有自定义异常的父类，提供统一的异常属性接口。
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        status_code: int = 500,
        details: Any = None,
    ) -> None:
        self.message: str = message
        self.code: int = code
        self.status_code: int = status_code
        self.details: Any = details
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details is not None:
            result["details"] = self.details
        return result


class BusinessException(AppException):
    """
    业务异常

    用于业务逻辑验证失败、资源冲突等业务层面的错误。
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message, code, status_code, details)


class SystemException(AppException):
    """
    系统异常

    用于系统级错误，如数据库故障、外部服务不可用等。
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        status_code: int = 500,
        details: Any = None,
    ) -> None:
        super().__init__(message, code, status_code, details)


# ============================================================================
# 通用业务异常
# ============================================================================


class NotFoundError(BusinessException):
    """资源未找到异常（HTTP 404）"""

    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(message, 404, 404, details)


class ValidationError(BusinessException):
    """参数校验异常（HTTP 400）"""

    def __init__(self, message: str = "Validation failed", details: Any = None) -> None:
        super().__init__(message, 400, 400, details)


class UnauthorizedError(BusinessException):
    """未授权异常（HTTP 401）"""

    def __init__(self, message: str = "Unauthorized", details: Any = None) -> None:
        super().__init__(message, 401, 401, details)


class ForbiddenError(BusinessException):
    """禁止访问异常（HTTP 403）"""

    def __init__(self, message: str = "Forbidden", details: Any = None) -> None:
        super().__init__(message, 403, 403, details)


class ConflictError(BusinessException):
    """资源冲突异常（HTTP 409）"""

    def __init__(self, message: str = "Resource conflict", details: Any = None) -> None:
        super().__init__(message, 409, 409, details)


class RateLimitError(BusinessException):
    """限流异常（HTTP 429）"""

    def __init__(self, message: str = "Rate limit exceeded", details: Any = None) -> None:
        super().__init__(message, 429, 429, details)


# ============================================================================
# 文档与知识库相关异常
# ============================================================================


class DocumentError(BusinessException):
    """文档处理异常（HTTP 400）"""

    def __init__(self, message: str = "Document processing failed", details: Any = None) -> None:
        super().__init__(message, 400, 400, details)


class DocumentParseError(DocumentError):
    """文档解析异常"""

    def __init__(self, message: str = "Document parse failed", details: Any = None) -> None:
        super().__init__(message, details)


class DocumentTooLargeError(DocumentError):
    """文档过大异常"""

    def __init__(self, message: str = "Document too large", details: Any = None) -> None:
        super().__init__(message, details)


# ============================================================================
# AI 服务相关异常
# ============================================================================


class EmbeddingError(SystemException):
    """向量化异常（HTTP 500）"""

    def __init__(self, message: str = "Embedding generation failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class GenerationError(SystemException):
    """生成异常（HTTP 500）"""

    def __init__(self, message: str = "Generation failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class ModelUnavailableError(SystemException):
    """模型不可用异常（HTTP 503）"""

    def __init__(self, message: str = "Model unavailable", details: Any = None) -> None:
        super().__init__(message, 503, 503, details)


# ============================================================================
# 向量存储相关异常
# ============================================================================


class VectorStoreError(SystemException):
    """向量存储异常（HTTP 500）"""

    def __init__(self, message: str = "Vector store operation failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class VectorNotFoundError(NotFoundError):
    """向量未找到异常"""

    def __init__(self, message: str = "Vector not found", details: Any = None) -> None:
        super().__init__(message, details)


class RetrievalError(SystemException):
    """检索异常（HTTP 500）"""

    def __init__(self, message: str = "Retrieval failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


# ============================================================================
# 数据库相关异常
# ============================================================================


class DatabaseError(SystemException):
    """数据库异常（HTTP 500）"""

    def __init__(self, message: str = "Database operation failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""

    def __init__(self, message: str = "Database connection failed", details: Any = None) -> None:
        super().__init__(message, details)


class QueryError(DatabaseError):
    """查询异常"""

    def __init__(self, message: str = "Database query failed", details: Any = None) -> None:
        super().__init__(message, details)


# ============================================================================
# 外部服务相关异常
# ============================================================================


class ExternalServiceError(SystemException):
    """外部服务异常（HTTP 502）"""

    def __init__(self, message: str = "External service call failed", details: Any = None) -> None:
        super().__init__(message, 502, 502, details)


class ServiceTimeoutError(ExternalServiceError):
    """超时异常"""

    def __init__(self, message: str = "Request timeout", details: Any = None) -> None:
        super().__init__(message, details)


# ============================================================================
# 配置相关异常
# =============================================================================


class ConfigurationError(SystemException):
    """配置异常（HTTP 500）"""

    def __init__(self, message: str = "Configuration error", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class MissingConfigError(ConfigurationError):
    """配置缺失异常"""

    def __init__(self, message: str = "Required configuration missing", details: Any = None) -> None:
        super().__init__(message, details)


# ============================================================================# 依赖注入相关异常
# =============================================================================


class DependencyNotFoundError(Exception):
    """依赖未找到异常。

    当容器无法解析某个依赖类型时抛出。

    Attributes:
        dependency_type: 未找到的依赖类型
    """

    def __init__(self, dependency_type: type) -> None:
        """初始化依赖未找到异常。

        Args:
            dependency_type: 未找到的依赖类型
        """
        self.dependency_type: type = dependency_type
        super().__init__(
            f"Dependency not found: {dependency_type.__name__}. "
            f"Please register it first using container.register()."
        )


class CircularDependencyError(Exception):
    """循环依赖异常。

    当检测到循环依赖时抛出。

    Attributes:
        dependency_chain: 依赖链
    """

    def __init__(self, dependency_chain: list[type]) -> None:
        """初始化循环依赖异常。

        Args:
            dependency_chain: 产生循环的依赖类型链
        """
        self.dependency_chain: list[type] = dependency_chain
        chain_str: str = " -> ".join(t.__name__ for t in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


# ============================================================================# 存储相关异常
# ============================================================================


class StorageError(SystemException):
    """存储异常（HTTP 500）"""

    def __init__(self, message: str = "Storage operation failed", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


class StorageFileNotFoundError(StorageError):
    """存储文件未找到异常"""

    def __init__(self, message: str = "Storage file not found", details: Any = None) -> None:
        super().__init__(message, 500, 500, details)


# ============================================================================
# 全局异常处理器注册
# ============================================================================


def register_exception_handlers(app: "FastAPI") -> None:
    """
    注册全局异常处理器。

    统一捕获以下异常并转换为标准 JSONResponse（BaseResp 格式），
    **不对外暴露原始服务堆栈**：

    - ``AppException``           → 自定义业务/系统异常
    - ``RequestValidationError`` → 请求参数校验异常（422）
    - ``StarletteHTTPException`` → HTTP 异常（404 / 405 等）
    - ``Exception``              → 未捕获的系统异常（500）

    Args:
        app: FastAPI 应用实例
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from src.api.response import error_response
    from src.constants.base import MSG_INTERNAL_ERROR, MSG_VALIDATION_ERROR

    @app.exception_handler(AppException)
    async def _app_exception_handler(request: "Request", exc: AppException) -> Any:
        """处理自定义应用异常（业务异常 + 系统异常）"""
        return error_response(
            request=request,
            code=exc.status_code,
            message=exc.message,
            data=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: "Request", exc: RequestValidationError
    ) -> Any:
        """处理请求参数校验异常（Pydantic / FastAPI 自动校验失败）"""
        return error_response(
            request=request,
            code=422,
            message=MSG_VALIDATION_ERROR,
            data=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: "Request", exc: StarletteHTTPException
    ) -> Any:
        """
        处理 HTTP 异常。

        覆盖 404（Not Found）、405（Method Not Allowed）等场景，
        全部转换为标准 JSONResponse，不返回 HTML 默认页面。
        """
        message = str(exc.detail) if exc.detail else _http_status_message(exc.status_code)
        return error_response(
            request=request,
            code=exc.status_code,
            message=message,
        )

    @app.exception_handler(Exception)
    async def _generic_exception_handler(request: "Request", exc: Exception) -> Any:
        """
        处理未捕获的异常。

        所有未预期的异常统一返回 500，不对外暴露堆栈信息。
        """
        from loguru import logger as _logger

        _logger.exception(f"Unhandled exception: {exc}")
        return error_response(
            request=request,
            code=500,
            message=MSG_INTERNAL_ERROR,
        )


def _http_status_message(status_code: int) -> str:
    """根据 HTTP 状态码返回默认描述（不暴露内部信息）"""
    _messages: dict[int, str] = {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Resource not found",
        405: "Method not allowed",
        408: "Request timeout",
        409: "Resource conflict",
        413: "Payload too large",
        422: "Validation failed",
        429: "Rate limit exceeded",
        500: "Internal server error",
        502: "Bad gateway",
        503: "Service unavailable",
    }
    return _messages.get(status_code, "Unknown error")


# ============================================================================
# 模块导出
# ============================================================================

__all__: Final[list[str]] = [
    # 基类
    "AppException",
    "BusinessException",
    "SystemException",
    # 通用业务异常
    "NotFoundError",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "RateLimitError",
    # 文档相关异常
    "DocumentError",
    "DocumentParseError",
    "DocumentTooLargeError",
    # AI 服务异常
    "EmbeddingError",
    "GenerationError",
    "ModelUnavailableError",
    # 向量存储异常
    "VectorStoreError",
    "VectorNotFoundError",
    "RetrievalError",
    # 数据库异常
    "DatabaseError",
    "DatabaseConnectionError",
    "QueryError",
    # 外部服务异常
    "ExternalServiceError",
    "ServiceTimeoutError",
    # 配置异常
    "ConfigurationError",
    "MissingConfigError",
    # 存储异常
    "StorageError",
    "StorageFileNotFoundError",
    # 异常处理器注册
    "register_exception_handlers",
]
