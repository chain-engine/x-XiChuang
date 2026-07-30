# -*- coding: utf-8 -*-
"""
仓储基类

提供通用仓储模式的基础实现。
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError, QueryError
from src.core.logger import logger


T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    数据仓储基类

    提供通用的 CRUD 操作模板方法。
    子类通过指定 model_class 来确定操作的模型类型。

    Attributes:
        model_class: 操作的模型类
        session: 数据库会话
    """

    def __init__(self, model_class: type[T], session: AsyncSession) -> None:
        """
        初始化仓储

        Args:
            model_class: 模型类
            session: 异步数据库会话
        """
        self._model_class = model_class
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """获取数据库会话"""
        return self._session

    async def create(self, **kwargs: Any) -> T:
        """
        创建记录

        Args:
            **kwargs: 模型字段值

        Returns:
            创建的模型实例
        """
        try:
            instance = self._model_class(**kwargs)
            self._session.add(instance)
            await self._session.commit()
            await self._session.refresh(instance)
            logger.debug(f"Created {self._model_class.__name__}: {instance}")
            return instance
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create {self._model_class.__name__}: {e}")
            raise QueryError(f"Failed to create record: {e}") from e

    async def get_by_id(self, entity_id: Any) -> T | None:
        """
        根据 ID 获取记录

        Args:
            entity_id: 主键 ID

        Returns:
            模型实例或 None
        """
        try:
            result = await self._session.execute(
                select(self._model_class).where(
                    self._model_class.__table__.primary_key.columns.values()[0] == entity_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get {self._model_class.__name__} by id {entity_id}: {e}")
            raise QueryError(f"Failed to get record: {e}") from e

    async def get_by_id_or_raise(self, entity_id: Any) -> T:
        """
        根据 ID 获取记录，不存在则抛出异常

        Args:
            entity_id: 主键 ID

        Returns:
            模型实例

        Raises:
            NotFoundError: 记录不存在
        """
        instance = await self.get_by_id(entity_id)
        if instance is None:
            raise NotFoundError(f"{self._model_class.__name__} with id '{entity_id}' not found")
        return instance

    async def update(self, entity_id: Any, **kwargs: Any) -> T:
        """
        更新记录

        Args:
            entity_id: 主键 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的模型实例
        """
        try:
            instance = await self.get_by_id_or_raise(entity_id)
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            await self._session.commit()
            await self._session.refresh(instance)
            logger.debug(f"Updated {self._model_class.__name__} {entity_id}")
            return instance
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to update {self._model_class.__name__} {entity_id}: {e}")
            raise QueryError(f"Failed to update record: {e}") from e

    async def delete(self, entity_id: Any) -> bool:
        """
        删除记录

        Args:
            entity_id: 主键 ID

        Returns:
            是否删除成功
        """
        try:
            instance = await self.get_by_id_or_raise(entity_id)
            await self._session.delete(instance)
            await self._session.commit()
            logger.debug(f"Deleted {self._model_class.__name__} {entity_id}")
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete {self._model_class.__name__} {entity_id}: {e}")
            raise QueryError(f"Failed to delete record: {e}") from e

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """
        获取所有记录

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            模型实例列表
        """
        try:
            query = select(self._model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            result = await self._session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to list {self._model_class.__name__}: {e}")
            raise QueryError(f"Failed to list records: {e}") from e

    async def count(self) -> int:
        """
        获取记录总数

        Returns:
            记录数量
        """
        try:
            result = await self._session.execute(
                select(func.count()).select_from(self._model_class)
            )
            return result.scalar_one() or 0
        except Exception as e:
            logger.error(f"Failed to count {self._model_class.__name__}: {e}")
            raise QueryError(f"Failed to count records: {e}") from e

    async def exists(self, entity_id: Any) -> bool:
        """
        检查记录是否存在

        Args:
            entity_id: 主键 ID

        Returns:
            是否存在
        """
        instance = await self.get_by_id(entity_id)
        return instance is not None
