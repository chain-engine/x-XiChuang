# -*- coding: utf-8 -*-
"""
通用 Schema 定义

包含跨模块使用的通用基础模型，包括：
- 分页参数基类 ``PageQuery``
- 排序参数基类 ``SortQuery``
- 统一响应模型 ``ApiResponse``（供序列化 / 测试使用，路由层应使用 api/response.py）

使用示例::

    class MyListQuery(PageQuery, SortQuery):
        keyword: str | None = None

    # API 层接收参数后透传给 service：
    items, total = await service.list_items(
        limit=query.page_size,
        offset=(query.page - 1) * query.page_size,
        order_by=query.order_by,
        order_desc=query.order_desc,
    )
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ============ 分页 / 排序 / 过滤参数基类 ============


class PageQuery(BaseModel):
    """
    分页参数基类

    所有需要分页的查询 Schema 应继承此类。
    API 层仅接收参数，不做分页计算，透传给 service 层。
    """

    page: int = Field(default=1, ge=1, description="当前页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小，最大 100")


class SortQuery(BaseModel):
    """
    排序参数基类

    所有需要排序的查询 Schema 应继承此类。
    """

    order_by: str = Field(default="created_at", description="排序字段名")
    order_desc: bool = Field(default=True, description="是否降序排列，true=DESC")


class FilterQuery(BaseModel):
    """
    过滤参数基类

    提供通用的关键词搜索字段，子类可扩展更多过滤条件。
    """

    keyword: str | None = Field(default=None, description="关键词搜索（模糊匹配）")


# ============ 统一响应模型 ============
# 注意：路由层应使用 api/response.py 的 success_response / error_response
#       构造 JSONResponse。以下模型仅用于类型标注、序列化和单元测试。


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应数据体

    用于 api/response.py 的 paginated_response 构造分页 data 字段。
    """

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[T]:
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应模型（BaseResp）

    用于 api/response.py 的 success_response / error_response 构造 JSONResponse。
    路由层不应直接实例化此类，而是调用 api/response.py 中的工具函数。
    """

    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    timestamp: str | None = Field(default=None, description="响应时间戳")
    request_id: str | None = Field(default=None, description="请求追踪ID")
