# -*- coding: utf-8 -*-
"""
基类模块

提供通用抽象基类和基础实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Pydantic 模型基类"""

    class Config:
        """全局配置"""
        populate_by_name = True
        from_attributes = True


class PaginationParams(BaseSchema):
    """分页参数基类"""

    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class PageResult(BaseModel, Generic[T]):
    """分页结果基类"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")

    @property
    def total_pages(self) -> int:
        """计算总页数"""
        return (self.total + self.page_size - 1) // self.page_size if self.page_size > 0 else 0

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1


class RepositoryInterface(ABC, Generic[T]):
    """
    数据仓储接口基类

    定义标准的数据访问操作。
    """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建记录"""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> T | None:
        """根据 ID 获取记录"""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新记录"""
        pass

    @abstractmethod
    async def delete(self, entity_id: Any) -> bool:
        """删除记录"""
        pass

    @abstractmethod
    async def list_all(self) -> list[T]:
        """获取所有记录"""
        pass


class ServiceInterface(ABC, Generic[T]):
    """
    服务接口基类

    定义标准的业务逻辑操作。
    """

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> T:
        """执行业务逻辑"""
        pass
