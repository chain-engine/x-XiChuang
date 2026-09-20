# -*- coding: utf-8 -*-
"""
服务层模块

提供业务逻辑层实现，封装核心业务规则和流程。
"""

from .base import (
    IChatService,
    IConversationService,
    IMilvusService,
    ChatRequest,
    ChatResponse,
    StreamChunk,
)
from .chat_service import ChatService, get_chat_service
from .conversation_service import ConversationService, get_conversation_service
from .milvus_service import MilvusService, get_milvus_service

__all__ = [
    # 接口
    "IChatService",
    "IConversationService",
    "IMilvusService",
    # 请求/响应模型
    "ChatRequest",
    "ChatResponse",
    "StreamChunk",
    # 实现
    "ChatService",
    "get_chat_service",
    "ConversationService",
    "get_conversation_service",
    "MilvusService",
    "get_milvus_service",
]
