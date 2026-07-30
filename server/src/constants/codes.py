# -*- coding: utf-8 -*-
"""
业务状态码定义

定义业务级别的状态码，用于前端逻辑判断。
所有枚举类均继承自 BaseEnum 基类。
"""

from .base import BaseEnum


class ResponseCodeEnum(BaseEnum):
    """
    响应状态码枚举

    业务状态码从 1000 开始，用于业务逻辑判断。
    """

    # ============ 通用状态码 (1000-1999) ============
    SUCCESS = (1000, "Success")
    PARAM_ERROR = (1001, "Parameter Error")
    PARAM_MISSING = (1002, "Parameter Missing")
    UNAUTHORIZED = (1003, "Unauthorized")
    FORBIDDEN = (1004, "Forbidden")
    NOT_FOUND = (1005, "Not Found")
    INTERNAL_ERROR = (1099, "Internal Error")

    # ============ 对话相关 (2000-2999) ============
    CHAT_SESSION_NOT_FOUND = (2001, "Chat Session Not Found")
    CHAT_MESSAGE_TOO_LONG = (2002, "Chat Message Too Long")
    CHAT_PROVIDER_UNAVAILABLE = (2003, "Chat Provider Unavailable")
    CHAT_MODEL_ERROR = (2004, "Chat Model Error")
    CHAT_TIMEOUT = (2005, "Chat Timeout")
    CHAT_HISTORY_CORRUPTED = (2006, "Chat History Corrupted")

    # ============ 会话管理相关 (3000-3999) ============
    CONVERSATION_NOT_FOUND = (3001, "Conversation Not Found")
    CONVERSATION_TITLE_REQUIRED = (3002, "Conversation Title Required")
    CONVERSATION_DUPLICATE = (3003, "Conversation Duplicate")
    CONVERSATION_ARCHIVE_FAILED = (3004, "Conversation Archive Failed")

    # ============ 文件/媒体相关 (4000-4999) ============
    FILE_TOO_LARGE = (4001, "File Too Large")
    FILE_TYPE_NOT_SUPPORTED = (4002, "File Type Not Supported")
    FILE_UPLOAD_FAILED = (4003, "File Upload Failed")
    FILE_NOT_FOUND = (4004, "File Not Found")
    FILE_PARSE_ERROR = (4005, "File Parse Error")
    MEDIA_TYPE_UNSUPPORTED = (4006, "Media Type Unsupported")

    # ============ 知识库/RAG 相关 (5000-5999) ============
    KNOWLEDGE_BASE_NOT_FOUND = (5001, "Knowledge Base Not Found")
    KNOWLEDGE_INGEST_FAILED = (5002, "Knowledge Ingest Failed")
    KNOWLEDGE_RETRIEVAL_FAILED = (5003, "Knowledge Retrieval Failed")
    EMBEDDING_FAILED = (5004, "Embedding Failed")
    VECTOR_SEARCH_FAILED = (5005, "Vector Search Failed")

    # ============ AI 模型相关 (6000-6999) ============
    MODEL_NOT_CONFIGURED = (6001, "Model Not Configured")
    MODEL_API_KEY_MISSING = (6002, "Model API Key Missing")
    MODEL_API_ERROR = (6003, "Model API Error")
    MODEL_RATE_LIMIT = (6004, "Model Rate Limit")
    MODEL_QUOTA_EXCEEDED = (6005, "Model Quota Exceeded")

    # ============ 数据库相关 (7000-7999) ============
    DB_CONNECTION_FAILED = (7001, "Database Connection Failed")
    DB_QUERY_FAILED = (7002, "Database Query Failed")
    DB_TRANSACTION_FAILED = (7003, "Database Transaction Failed")

    # ============ 外部服务相关 (8000-8999) ============
    EXTERNAL_SERVICE_ERROR = (8001, "External Service Error")
    SERVICE_TIMEOUT = (8002, "Service Timeout")
    SERVICE_UNAVAILABLE = (8003, "Service Unavailable")


class ErrorCodeEnum(BaseEnum):
    """
    错误代码枚举

    用于日志记录和错误追踪。
    """

    # 系统错误
    SYS_0001 = (1, "System Error 0001")
    SYS_0002 = (2, "System Error 0002")
    SYS_0003 = (3, "System Error 0003")

    # 业务错误
    BIZ_1001 = (1001, "Business Error 1001")
    BIZ_1002 = (1002, "Business Error 1002")

    # 外部服务错误
    EXT_2001 = (2001, "External Error 2001")
    EXT_2002 = (2002, "External Error 2002")
