# -*- coding: utf-8 -*-
"""
枚举定义

提供业务相关的枚举类型。
所有枚举类均继承自 BaseEnum 基类。
"""

from .base import BaseEnum


class ResponseCode(BaseEnum):
    """
    响应状态码枚举

    HTTP 状态码规范：
    - 2xx: 成功
    - 4xx: 客户端错误
    - 5xx: 服务端错误
    """

    # 成功
    SUCCESS = (0, "Success")
    CREATED = (201, "Created")
    ACCEPTED = (202, "Accepted")
    NO_CONTENT = (204, "No Content")

    # 客户端错误
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Unauthorized")
    FORBIDDEN = (403, "Forbidden")
    NOT_FOUND = (404, "Not Found")
    METHOD_NOT_ALLOWED = (405, "Method Not Allowed")
    CONFLICT = (409, "Conflict")
    UNPROCESSABLE_ENTITY = (422, "Unprocessable Entity")
    TOO_MANY_REQUESTS = (429, "Too Many Requests")

    # 服务端错误
    INTERNAL_SERVER_ERROR = (500, "Internal Server Error")
    BAD_GATEWAY = (502, "Bad Gateway")
    SERVICE_UNAVAILABLE = (503, "Service Unavailable")
    GATEWAY_TIMEOUT = (504, "Gateway Timeout")


class MessageRole(BaseEnum):
    """
    消息角色枚举

    定义对话中消息的发送者角色。
    """

    SYSTEM = ("system", "System")
    USER = ("user", "User")
    ASSISTANT = ("assistant", "Assistant")
    TOOL = ("tool", "Tool")


class MediaType(BaseEnum):
    """
    媒体类型枚举

    定义支持的媒体类型。
    """

    TEXT = ("text", "Text")
    IMAGE = ("image", "Image")
    AUDIO = ("audio", "Audio")
    VIDEO = ("video", "Video")
    VOICE = ("voice", "Voice")
    AUTO = ("auto", "Auto Detect")


class ModelProvider(BaseEnum):
    """
    AI 模型提供商枚举

    定义支持的 AI 模型提供商。
    """

    TONGYI = ("tongyi", "千问")
    DEEPSEEK = ("deepseek", "DeepSeek")
    GLM = ("glm", "GLM")
    DOUBAO = ("doubao", "豆包")
    KIMI = ("kimi", "Kimi")
    MOCK = ("mock", "Mock")


class TaskStatus(BaseEnum):
    """
    任务状态枚举

    定义异步任务的执行状态。
    """

    PENDING = ("pending", "Pending")
    RUNNING = ("running", "Running")
    COMPLETED = ("completed", "Completed")
    FAILED = ("failed", "Failed")
    CANCELLED = ("cancelled", "Cancelled")


class StorageType(BaseEnum):
    """
    存储类型枚举

    定义支持的存储后端类型。
    """

    LOCAL = ("local", "Local Storage")
    OSS = ("oss", "Aliyun OSS")
    MINIO = ("minio", "MinIO")


class ConversationStatus(BaseEnum):
    """
    会话状态枚举

    定义会话的状态。
    """

    ACTIVE = ("active", "Active")
    ARCHIVED = ("archived", "Archived")
    DELETED = ("deleted", "Deleted")
