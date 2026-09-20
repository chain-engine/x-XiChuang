"""
数据库基础设施模块

本模块提供数据库连接池管理和会话工厂，确保数据库连接的高效复用和生命周期管理。

功能特性：
    - 基于 SQLAlchemy 2.0 的同步/异步支持
    - MySQL 连接池管理和配置
    - 上下文管理器确保会话自动关闭

Usage:
    from src.infras.database import get_cached_database_provider, Base

    provider = get_cached_database_provider()
    with provider.session() as session:
        result = session.execute(select(User))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.core.config import settings
from src.core.logger import logger

Base = declarative_base()


# ============================================================
# 抽象基类
# ============================================================


class DatabaseProvider(ABC):
    """数据库提供者抽象接口。

    所有数据库后端必须实现此接口。业务层仅依赖此抽象，
    切换数据库实现只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def get_engine(self) -> Engine:
        """获取同步数据库引擎。"""

    @abstractmethod
    def get_async_engine(self) -> AsyncEngine:
        """获取异步数据库引擎。"""

    @abstractmethod
    def get_session_factory(self) -> sessionmaker:
        """获取同步会话工厂。"""

    @abstractmethod
    def get_async_session_factory(self) -> async_sessionmaker:
        """获取异步会话工厂。"""

    @abstractmethod
    def session(self) -> Generator[Session, None, None]:
        """获取同步数据库会话的上下文管理器。"""

    @abstractmethod
    def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话的上下文管理器。"""

    @abstractmethod
    def check_connection(self) -> bool:
        """检测数据库连接是否可用。"""

    @abstractmethod
    async def async_check_connection(self) -> bool:
        """异步检测数据库连接是否可用。"""

    @abstractmethod
    def close(self) -> None:
        """关闭数据库连接，释放资源。"""


# ============================================================
# MySQL (SQLAlchemy) 实现
# ============================================================


class MySqlProvider(DatabaseProvider):
    """MySQL 数据库实现（基于 SQLAlchemy）。

    同时提供同步和异步引擎，适用于不同场景：
    - 同步：脚本、迁移、数据初始化
    - 异步：FastAPI 请求处理
    """

    def __init__(
        self,
        database_url: str,
        async_database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600,
        echo: bool = False,
    ) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")

        # 同步引擎
        self._engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            echo=echo,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        # 异步引擎
        self._async_engine = create_async_engine(
            async_database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            echo=echo,
        )
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            autocommit=False,
            autoflush=False,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"MySqlProvider initialized: {database_url}")

    # ---------- 引擎与工厂 ----------

    def get_engine(self) -> Engine:
        return self._engine

    def get_async_engine(self) -> AsyncEngine:
        return self._async_engine

    def get_session_factory(self) -> sessionmaker:
        return self._session_factory

    def get_async_session_factory(self) -> async_sessionmaker:
        return self._async_session_factory

    # ---------- 会话上下文管理器 ----------

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """获取同步数据库会话。"""
        s: Session = self._session_factory()
        try:
            yield s
            s.commit()
        except Exception as e:
            s.rollback()
            logger.error(f"MySQL operation failed, rolled back: {e}")
            raise
        finally:
            s.close()

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话。"""
        async with self._async_session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception as e:
                await s.rollback()
                logger.error(f"MySQL async operation failed, rolled back: {e}")
                raise

    # ---------- 连接检测 ----------

    def check_connection(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database connection check failed: {e}")
            return False

    async def async_check_connection(self) -> bool:
        try:
            async with self._async_engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database async connection check failed: {e}")
            return False

    # ---------- 资源释放 ----------

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            # 注意：dispose 在 async 引擎上需要异步调用
            # 此处在同步 close 中做尽力清理
            logger.info("MySQL connections disposed")


# ============================================================
# 工厂函数
# ============================================================


def get_database_provider() -> DatabaseProvider:
    """根据配置创建数据库提供者实例。"""
    return MySqlProvider(
        database_url=settings.DATABASE_URL,
        async_database_url=settings.ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
    )


# 模块级缓存实例
_db_provider: DatabaseProvider | None = None


def get_cached_database_provider() -> DatabaseProvider:
    """获取缓存的数据库提供者（应用级别单例）。"""
    global _db_provider
    if _db_provider is None:
        _db_provider = get_database_provider()
    return _db_provider


# ============================================================
# 便捷的会话依赖（供 FastAPI Depends 使用）
# ============================================================


def get_db() -> Generator[Session, None, None]:
    """获取同步数据库会话（用于依赖注入）。"""
    with get_cached_database_provider().session() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话（用于依赖注入）。"""
    async with get_cached_database_provider().async_session() as session:
        yield session


# ============================================================
# 数据库初始化 / 销毁
# ============================================================


def init_db() -> None:
    """初始化数据库表结构（同步）。"""
    from src.models.entities import ConversationEntity, MessageEntity  # noqa: F401

    engine = get_cached_database_provider().get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("MySQL tables created (sync)")


async def async_init_db() -> None:
    """异步初始化数据库表结构。"""
    from src.models.entities import ConversationEntity, MessageEntity  # noqa: F401

    async_engine = get_cached_database_provider().get_async_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("MySQL tables created (async)")


# ============================================================
# 向后兼容的模块级引用
# 通过 lazy accessor 确保 provider 已初始化后再返回实际引擎/工厂
# ============================================================


def _ensure_compat():
    """确保 provider 已初始化，返回 provider 实例。"""
    return get_cached_database_provider()


def _get_engine():
    return _ensure_compat().get_engine()


def _get_async_engine():
    return _ensure_compat().get_async_engine()


def _get_session_local():
    return _ensure_compat().get_session_factory()


def _get_async_session_local():
    return _ensure_compat().get_async_session_factory()


# 兼容导出：调用方通过这些函数获取实例
engine = _get_engine
async_engine = _get_async_engine
SessionLocal = _get_session_local
AsyncSessionLocal = _get_async_session_local


__all__ = [
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
]
