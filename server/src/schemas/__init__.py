# -*- coding: utf-8 -*-
"""
API Schema 模块

统一管理所有 API 的请求和响应 Pydantic 模型。
"""

from .chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ProviderInfo,
    ProvidersResponse,
    StreamChatRequest,
    UploadChatRequest,
)
from .conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    SaveMessagesRequest,
)
from .common import (
    BaseQuery,
    HealthResponse,
    VersionResponse,
)
from .milvus import (
    CollectionInfo,
    DeleteRequest,
    DeleteResponse,
    MilvusStatsResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

__all__ = [
    # Chat schemas
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ProviderInfo",
    "ProvidersResponse",
    "StreamChatRequest",
    "UploadChatRequest",
    # Conversation schemas
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "MessageCreate",
    "MessageResponse",
    "SaveMessagesRequest",
    # Common schemas
    "BaseQuery",
    "HealthResponse",
    "VersionResponse",
    # Milvus schemas
    "CollectionInfo",
    "MilvusStatsResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "DeleteRequest",
    "DeleteResponse",
]
