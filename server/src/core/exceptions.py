# -*- coding: utf-8 -*-
"""
全局异常定义模块

定义业务异常和系统异常基类，提供统一的异常处理机制。
"""

from typing import Final

from .logger import logger


# ============================================================================
# 异常基类
# ============================================================================

class BaseException(Exception):
    """
    异常基类

    所有自定义异常的父类，提供统一的异常属性接口。
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        detail: str | None = None
    ) -> None:
        self.message: str = message
        self.code: int = code
        self.detail: str | None = detail
        super().__init__(self.message)


class BusinessError(BaseException):
    """
    业务异常

    用于业务逻辑验证失败、资源冲突等业务层面的错误。
    默认 HTTP 状态码: 400
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        detail: str | None = None
    ) -> None:
        super().__init__(message, code, detail)
        logger.warning(f"BusinessError: {message}")


class SystemError(BaseException):
    """
    系统异常

    用于系统级错误，如数据库故障、外部服务不可用等。
    默认 HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        detail: str | None = None
    ) -> None:
        super().__init__(message, code, detail)
        logger.error(f"SystemError: {message}")


# ============================================================================
# 通用业务异常
# ============================================================================

class NotFoundError(BusinessError):
    """
    资源未找到异常

    当请求的资源不存在时抛出。
    HTTP 状态码: 404
    """

    def __init__(self, message: str = "Resource not found", detail: str | None = None) -> None:
        super().__init__(message, 404, detail)


class ValidationError(BusinessError):
    """
    参数校验异常

    当输入参数验证失败时抛出。
    HTTP 状态码: 400
    """

    def __init__(self, message: str = "Validation failed", detail: str | None = None) -> None:
        super().__init__(message, 400, detail)


class UnauthorizedError(BusinessError):
    """
    未授权异常

    当用户未认证或认证信息无效时抛出。
    HTTP 状态码: 401
    """

    def __init__(self, message: str = "Unauthorized", detail: str | None = None) -> None:
        super().__init__(message, 401, detail)


class ForbiddenError(BusinessError):
    """
    禁止访问异常

    当用户已认证但无权限访问资源时抛出。
    HTTP 状态码: 403
    """

    def __init__(self, message: str = "Forbidden", detail: str | None = None) -> None:
        super().__init__(message, 403, detail)


class ConflictError(BusinessError):
    """
    资源冲突异常

    当资源操作产生冲突时抛出，如重复创建唯一资源。
    HTTP 状态码: 409
    """

    def __init__(self, message: str = "Resource conflict", detail: str | None = None) -> None:
        super().__init__(message, 409, detail)


class RateLimitError(BusinessError):
    """
    限流异常

    当请求频率超过限制时抛出。
    HTTP 状态码: 429
    """

    def __init__(self, message: str = "Rate limit exceeded", detail: str | None = None) -> None:
        super().__init__(message, 429, detail)


# ============================================================================
# 文档与知识库相关异常
# ============================================================================

class DocumentError(BusinessError):
    """
    文档处理异常

    当文档解析、转换或处理失败时抛出。
    HTTP 状态码: 400
    """

    def __init__(
        self,
        message: str = "Document processing failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 400, detail)


class DocumentParseError(DocumentError):
    """
    文档解析异常

    当文档格式无法解析时抛出。
    """

    def __init__(self, message: str = "Document parse failed", detail: str | None = None) -> None:
        super().__init__(message, detail)


class DocumentTooLargeError(DocumentError):
    """
    文档过大异常

    当文档大小超过限制时抛出。
    """

    def __init__(self, message: str = "Document too large", detail: str | None = None) -> None:
        super().__init__(message, detail)


# ============================================================================
# AI 服务相关异常
# ============================================================================

class EmbeddingError(SystemError):
    """
    向量化异常

    当文本向量化（Embedding）生成失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Embedding generation failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class GenerationError(SystemError):
    """
    生成异常

    当 AI 内容生成失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Generation failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class ModelUnavailableError(SystemError):
    """
    模型不可用异常

    当指定的 AI 模型不可用或未配置时抛出。
    HTTP 状态码: 503
    """

    def __init__(
        self,
        message: str = "Model unavailable",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 503, detail)


# ============================================================================
# 向量存储相关异常
# ============================================================================

class VectorStoreError(SystemError):
    """
    向量存储异常

    当向量数据库操作失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Vector store operation failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class VectorNotFoundError(NotFoundError):
    """
    向量未找到异常

    当检索不到相关向量时抛出。
    """

    def __init__(
        self,
        message: str = "Vector not found",
        detail: str | None = None
    ) -> None:
        super().__init__(message, detail)


class RetrievalError(SystemError):
    """
    检索异常

    当向量检索失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Retrieval failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


# ============================================================================
# 数据库相关异常
# ============================================================================

class DatabaseError(SystemError):
    """
    数据库异常

    当数据库操作失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class ConnectionError(DatabaseError):
    """
    数据库连接异常

    当无法连接到数据库时抛出。
    """

    def __init__(
        self,
        message: str = "Database connection failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, detail)


class QueryError(DatabaseError):
    """
    查询异常

    当数据库查询执行失败时抛出。
    """

    def __init__(
        self,
        message: str = "Database query failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, detail)


# ============================================================================
# 外部服务相关异常
# ============================================================================

class ExternalServiceError(SystemError):
    """
    外部服务异常

    当调用外部服务失败时抛出。
    HTTP 状态码: 502
    """

    def __init__(
        self,
        message: str = "External service call failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 502, detail)


class TimeoutError(ExternalServiceError):
    """
    超时异常

    当外部服务响应超时时抛出。
    """

    def __init__(
        self,
        message: str = "Request timeout",
        detail: str | None = None
    ) -> None:
        super().__init__(message, detail)


# ============================================================================
# 配置相关异常
# ============================================================================

class ConfigurationError(SystemError):
    """
    配置异常

    当配置项缺失或无效时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Configuration error",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class MissingConfigError(ConfigurationError):
    """
    配置缺失异常

    当必需的配置文件或配置项缺失时抛出。
    """

    def __init__(
        self,
        message: str = "Required configuration missing",
        detail: str | None = None
    ) -> None:
        super().__init__(message, detail)


# ============================================================================
# 存储相关异常
# ============================================================================

class StorageError(SystemError):
    """
    存储异常

    当文件存储操作失败时抛出。
    HTTP 状态码: 500
    """

    def __init__(
        self,
        message: str = "Storage operation failed",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


class StorageFileNotFoundError(StorageError):
    """
    存储文件未找到异常

    当请求的存储文件不存在时抛出。
    """

    def __init__(
        self,
        message: str = "Storage file not found",
        detail: str | None = None
    ) -> None:
        super().__init__(message, 500, detail)


# ============================================================================
# 模块导出
# ============================================================================

__all__: Final[list[str]] = [
    # 基类
    "BaseException",
    "BusinessError",
    "SystemError",
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
    "ConnectionError",
    "QueryError",
    # 外部服务异常
    "ExternalServiceError",
    "TimeoutError",
    # 配置异常
    "ConfigurationError",
    "MissingConfigError",
    # 存储异常
    "StorageError",
    "FileNotFoundError",
]
