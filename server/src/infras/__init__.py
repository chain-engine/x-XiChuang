# -*- coding: utf-8 -*-
"""
基础设施层模块

本层封装第三方中间件、客户端、连接生命周期、底层资源管理，
仅提供基础资源，不包含业务逻辑。

核心原则：
    - 每个模块基于抽象基类（ABC）定义标准接口
    - 业务层仅依赖抽象接口，实现类可动态替换解耦
    - infra 永不反向依赖 repository/service/api

统一风格：
    - XxxProvider(ABC)         — 抽象接口
    - YyyXxxProvider           — 具体实现
    - get_xxx_provider()       — 工厂函数（读配置创建实例）

子模块：
    - database: DatabaseProvider → MySqlProvider（ABC 接口 + 连接管理）
    - milvus:   VectorStoreProvider → MilvusVectorStoreProvider
    - storage:  StorageProvider → LocalStorage / AliyunOSSStorage
"""

from .database import (
    Base,
    DatabaseProvider,
    MySqlProvider,
    get_database_provider,
    get_cached_database_provider,
    get_db,
    get_async_db,
    init_db,
    async_init_db,
    engine,
    async_engine,
    SessionLocal,
    AsyncSessionLocal,
)

from .milvus import (
    MilvusClient,
    MilvusVectorStoreProvider,
    VectorStoreProvider,
    get_milvus_client,
    get_vector_store_provider,
)
from .storage import (
    StorageProvider,
    LocalStorage,
    AliyunOSSStorage,
    UploadResult,
    get_storage_provider,
    get_cached_storage_provider,
    # 向后兼容
    FileStorage,
    StorageBackend,
    get_storage,
)

__all__ = [
    # 数据库
    "Base",
    "DatabaseProvider",
    "MySqlProvider",
    "get_database_provider",
    "get_cached_database_provider",
    "get_db",
    "get_async_db",
    "init_db",
    "async_init_db",
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    # Milvus 向量数据库
    "VectorStoreProvider",
    "MilvusVectorStoreProvider",
    "get_vector_store_provider",
    "MilvusClient",
    "get_milvus_client",
    # 文件存储
    "StorageProvider",
    "LocalStorage",
    "AliyunOSSStorage",
    "UploadResult",
    "get_storage_provider",
    "get_cached_storage_provider",
    "FileStorage",
    "StorageBackend",
    "get_storage",
]
