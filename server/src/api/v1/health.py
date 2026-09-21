# -*- coding: utf-8 -*-
"""
健康检查路由

提供系统健康检查和版本信息接口。

职责边界：
- 本文件仅处理 HTTP 请求接入，**不实现任何业务逻辑**
- 所有检查逻辑委托给 ``services/health_service.py``
- 所有响应使用 ``api/response.py`` 的统一响应封装

接口列表：
- ``GET /health``         — 完整健康检查（数据库、缓存连通状态）
- ``GET /health/live``    — 存活探针（Kubernetes liveness probe）
- ``GET /health/ready``   — 就绪探针（Kubernetes readiness probe）
- ``GET /version``        — 版本信息
- ``GET /config/summary`` — 配置摘要（脱敏）
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from src.api.response import success_response
from src.schemas.health import HealthResponse, VersionResponse
from src.services.health_service import get_health_service


router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查系统各组件的健康状态，包括数据库连接、Milvus 连接、API 配置。",
)
async def health_check(request: Request) -> HealthResponse:
    """
    健康检查接口

    检查系统各组件的健康状态，包括：
    - 数据库连接
    - Milvus 连接
    - 应用状态

    Returns:
        HealthResponse: 健康状态响应，包含整体状态和各组件详情
    """
    service = get_health_service()
    data = await service.check_health()

    from src.schemas.health import HealthStatus

    return success_response(
        data=HealthResponse(
            status=data["status"],
            version=data["version"],
            timestamp=data["timestamp"],
            checks={
                k: HealthStatus(
                    status=v["status"],
                    latency_ms=v.get("latency_ms"),
                    message=v.get("message"),
                )
                for k, v in data["checks"].items()
            },
        ).model_dump(mode="json"),
        request=request,
    )


@router.get(
    "/health/live",
    summary="存活探针",
    description="用于 Kubernetes liveness probe，只检查应用是否存活，不检查依赖。",
)
async def liveness_probe(request: Request) -> Any:
    """
    存活探针

    用于 Kubernetes liveness probe。
    只检查应用是否存活，不检查依赖。

    Returns:
        {"code": 200, "message": "success", "data": {"status": "alive"}}
    """
    return success_response(data={"status": "alive"}, request=request)


@router.get(
    "/health/ready",
    summary="就绪探针",
    description="用于 Kubernetes readiness probe，检查所有依赖是否就绪。",
)
async def readiness_probe(request: Request) -> Any:
    """
    就绪探针

    用于 Kubernetes readiness probe。
    检查所有依赖是否就绪。

    Returns:
        就绪状态
    """
    service = get_health_service()
    data = await service.check_health()

    ready = data["status"] == "healthy"
    return success_response(
        data={"ready": ready},
        request=request,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="版本信息",
    description="返回应用、Python 运行时和主要依赖的版本信息。",
)
async def get_version(request: Request) -> Any:
    """
    获取版本信息

    返回应用、Python 和主要依赖的版本信息。

    Returns:
        VersionResponse: 版本信息
    """
    service = get_health_service()
    data = service.get_version_info()
    return success_response(data=data, request=request)


@router.get(
    "/config/summary",
    summary="配置摘要",
    description="返回配置信息（敏感字段已脱敏），仅用于运维排查。",
)
async def get_config_summary(request: Request) -> Any:
    """
    获取配置摘要（脱敏）

    返回配置信息（敏感字段已脱敏）。

    Returns:
        配置摘要
    """
    service = get_health_service()
    data = service.get_config_summary()
    return success_response(data=data, request=request)
