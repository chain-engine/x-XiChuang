# -*- coding: utf-8 -*-
"""
统一响应封装

提供标准化的 API 响应结构，支持泛型类型。
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class BaseResp(BaseModel, Generic[T]):
    """
    统一响应封装

    所有 API 响应统一使用此结构，确保前端处理一致性。

    Attributes:
        code: 业务状态码，0 表示成功，非 0 表示错误
        message: 响应消息，用于前端提示
        data: 响应数据，可为任意类型
        trace_id: 请求追踪 ID（可选）
    """

    code: int = Field(default=0, description="业务状态码，0=成功")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str | None = Field(default=None, description="追踪ID")

    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "code": 0,
                "message": "success",
                "data": {"id": "123", "name": "example"},
            }
        }


class SuccessResp(BaseResp[T]):
    """
    成功响应

    快捷响应类，默认 code=0, message="success"

    Example:
        return SuccessResp(data={"id": 1})
    """

    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="响应消息")


class ErrorResp(BaseResp[None]):
    """
    错误响应

    快捷响应类，用于返回错误信息

    Attributes:
        code: 错误码，默认为 500
        message: 错误消息
        detail: 详细错误信息（仅开发环境显示）
    """

    code: int = Field(default=500, description="错误码")
    message: str = Field(default="Internal server error", description="错误消息")
    detail: str | None = Field(default=None, description="详细错误信息")

    @classmethod
    def from_exception(
        cls,
        message: str,
        code: int = 500,
        detail: str | None = None,
    ) -> ErrorResp:
        """
        从异常创建错误响应

        Args:
            message: 错误消息
            code: 错误码
            detail: 详细错误信息

        Returns:
            ErrorResp 实例
        """
        return cls(
            code=code,
            message=message,
            detail=detail,
        )


class PaginatedData(BaseModel, Generic[T]):
    """
    分页数据封装

    用于列表类接口的分页响应。

    Attributes:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        total_pages: 总页数
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
    ) -> PaginatedData[T]:
        """
        创建分页数据

        Args:
            items: 数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页大小

        Returns:
            PaginatedData 实例
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ListResp(BaseResp[list[T]]):
    """
    列表响应

    用于返回数据列表的响应。
    """

    pass


class DetailResp(BaseResp[T]):
    """
    详情响应

    用于返回单个对象详情的响应。
    """

    pass


# ============ 快捷响应工厂函数 ============


def success(data: T | None = None, message: str = "success") -> SuccessResp[T]:
    """
    创建成功响应

    Args:
        data: 响应数据
        message: 成功消息

    Returns:
        SuccessResp 实例
    """
    return SuccessResp(data=data, message=message)


def error(
    message: str,
    code: int = 500,
    detail: str | None = None,
) -> ErrorResp:
    """
    创建错误响应

    Args:
        message: 错误消息
        code: 错误码
        detail: 详细错误信息

    Returns:
        ErrorResp 实例
    """
    return ErrorResp.from_exception(message=message, code=code, detail=detail)


def paginated(
    items: list[T],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "success",
) -> SuccessResp[PaginatedData[T]]:
    """
    创建分页响应

    Args:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        message: 响应消息

    Returns:
        分页响应
    """
    return SuccessResp(
        data=PaginatedData.create(items=items, total=total, page=page, page_size=page_size),
        message=message,
    )
