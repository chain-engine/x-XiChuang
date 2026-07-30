# -*- coding: utf-8 -*-
"""
通用 Schema 定义

包含跨模块使用的通用模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseQuery(BaseModel):
    """基础查询参数"""

    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

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


class HealthStatus(BaseModel):
    """健康状态详情"""

    status: str = Field(..., description="状态：healthy/unhealthy/degraded")
    latency_ms: float | None = Field(None, description="延迟（毫秒）")
    message: str | None = Field(None, description="状态消息")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="整体状态：healthy/unhealthy/degraded")
    version: str = Field(..., description="应用版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")
    checks: dict[str, HealthStatus] = Field(
        default_factory=dict,
        description="各组件健康状态"
    )


class VersionInfo(BaseModel):
    """版本信息"""

    version: str = Field(..., description="应用版本")
    name: str = Field(..., description="应用名称")
    description: str = Field(..., description="应用描述")


class VersionResponse(BaseModel):
    """版本信息响应"""

    app: VersionInfo = Field(..., description="应用信息")
    python: str = Field(..., description="Python 版本")
    fastapi: str = Field(..., description="FastAPI 版本")
    environment: str = Field(..., description="运行环境")


class ErrorDetail(BaseModel):
    """错误详情"""

    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    detail: str | None = Field(None, description="详细错误信息")
    trace_id: str | None = Field(None, description="追踪ID")


class ErrorResponse(BaseModel):
    """错误响应"""

    code: int = Field(..., description="业务状态码")
    message: str = Field(..., description="错误消息")
    trace_id: str | None = Field(None, description="追踪ID")
    detail: str | None = Field(None, description="详细错误信息")


class SuccessResponse(BaseModel, Generic[T]):
    """成功响应"""

    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="成功消息")
    data: T | None = Field(None, description="响应数据")
    trace_id: str | None = Field(None, description="追踪ID")
