# -*- coding: utf-8 -*-
"""
健康检查 Schema 定义

包含健康检查和版本信息相关的 Pydantic 模型。
用于 ``GET /api/v1/health`` 和 ``GET /api/v1/version`` 接口。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """
    单个组件的健康状态详情

    用于描述数据库、缓存等依赖组件的连通状态。
    """

    status: str = Field(
        ...,
        description="组件状态：healthy（健康） / unhealthy（异常） / degraded（降级）",
        examples=["healthy"],
    )
    latency_ms: float | None = Field(
        None,
        description="组件响应延迟（毫秒）",
        examples=[1.23],
    )
    message: str | None = Field(
        None,
        description="状态描述信息，异常时包含错误摘要",
        examples=["Connected"],
    )


class HealthResponse(BaseModel):
    """
    健康检查响应

    返回系统整体健康状态及各组件详情。
    用于 ``GET /api/v1/health``。
    """

    status: str = Field(
        ...,
        description="系统整体状态：healthy / unhealthy / degraded",
        examples=["healthy"],
    )
    version: str = Field(
        ...,
        description="应用版本号",
        examples=["1.0.0"],
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="检查时间（UTC）",
    )
    checks: dict[str, HealthStatus] = Field(
        default_factory=dict,
        description="各组件健康状态映射，key 为组件名称（database / milvus / api_config）",
    )


class VersionInfo(BaseModel):
    """
    应用版本信息

    描述应用的基本信息。
    """

    version: str = Field(..., description="应用版本号", examples=["1.0.0"])
    name: str = Field(..., description="应用名称", examples=["XiChuang"])
    description: str = Field(..., description="应用描述", examples=["多模态智能助手"])


class VersionResponse(BaseModel):
    """
    版本信息响应

    返回应用、运行时及主要依赖的版本信息。
    用于 ``GET /api/v1/version``。
    """

    app: VersionInfo = Field(..., description="应用信息")
    python: str = Field(..., description="Python 运行时版本", examples=["3.12.0"])
    fastapi: str = Field(..., description="FastAPI 框架版本", examples=["0.115.0"])
    environment: str = Field(
        ...,
        description="运行环境：development / staging / production",
        examples=["development"],
    )
