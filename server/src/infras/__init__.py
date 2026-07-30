# -*- coding: utf-8 -*-
"""
基础设施层模块

封装第三方中间件、客户端、连接生命周期管理。
提供数据库、向量存储、文件存储等基础设施服务。
"""

from .mysql import (
    Base,
    Conversation,
    Message,
    get_async_db,
    get_db,
    init_db,
    async_init_db,
    engine,
    async_engine,
    SessionLocal,
    AsyncSessionLocal,
)

from .milvus import MilvusClient, get_milvus_client
from .storage import FileStorage, StorageBackend, get_storage

__all__ = [
    # MySQL 数据库
    "Base",
    "Conversation",
    "Message",
    "get_async_db",
    "get_db",
    "init_db",
    "async_init_db",
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    # Milvus 向量数据库
    "MilvusClient",
    "get_milvus_client",
    # 文件存储
    "FileStorage",
    "StorageBackend",
    "get_storage",
]
