# -*- coding: utf-8 -*-
"""
健康检查路由

提供系统健康检查和版本信息接口。
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from src.core.config import settings
from src.core.logger import logger
from src.schemas.common import HealthResponse, HealthStatus, VersionResponse, VersionInfo


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(request: Request) -> HealthResponse:
    """
    健康检查接口

    检查系统各组件的健康状态，包括：
    - 数据库连接
    - Milvus 连接
    - 应用状态

    Returns:
        HealthResponse: 健康状态响应
    """
    checks: dict[str, HealthStatus] = {}
    overall_status = "healthy"

    # 检查数据库
    db_status = await _check_database()
    checks["database"] = db_status
    if db_status.status != "healthy":
        overall_status = "degraded"

    # 检查 Milvus
    milvus_status = await _check_milvus()
    checks["milvus"] = milvus_status
    if milvus_status.status != "healthy":
        overall_status = "degraded"

    # 检查 API 配置
    api_status = _check_api_config()
    checks["api_config"] = api_status

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        checks=checks,
    )


@router.get("/health/live", tags=["health"])
async def liveness_probe() -> dict[str, str]:
    """
    存活探针

    用于 Kubernetes liveness probe。
    只检查应用是否存活，不检查依赖。

    Returns:
        {"status": "alive"}
    """
    return {"status": "alive"}


@router.get("/health/ready", tags=["health"])
async def readiness_probe() -> dict[str, Any]:
    """
    就绪探针

    用于 Kubernetes readiness probe。
    检查所有依赖是否就绪。

    Returns:
        就绪状态
    """
    # 快速检查数据库
    try:
        db_status = await _check_database()
        if db_status.status != "healthy":
            return {
                "ready": False,
                "reason": "Database not ready",
            }
    except Exception as e:
        return {
            "ready": False,
            "reason": f"Database check failed: {e}",
        }

    return {"ready": True}


@router.get("/version", response_model=VersionResponse, tags=["health"])
async def get_version() -> VersionResponse:
    """
    获取版本信息

    返回应用、Python 和主要依赖的版本信息。

    Returns:
        VersionResponse: 版本信息
    """
    return VersionResponse(
        app=VersionInfo(
            version=settings.APP_VERSION,
            name=settings.APP_NAME,
            description="多模态智能助手",
        ),
        python=sys.version.split()[0],
        fastapi="0.111.0",
        environment=settings.ENVIRONMENT,
    )


@router.get("/config/summary", tags=["health"])
async def get_config_summary() -> dict[str, Any]:
    """
    获取配置摘要（脱敏）

    返回配置信息（敏感字段已脱敏）。

    Returns:
        配置摘要
    """
    return settings.get_config_summary()


# ============ 内部检查函数 ============

async def _check_database() -> HealthStatus:
    """检查数据库连接"""
    start_time = time.perf_counter()
    try:
        from src.infras.mysql import async_engine

        async with async_engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))

        latency_ms = (time.perf_counter() - start_time) * 1000
        return HealthStatus(
            status="healthy",
            latency_ms=latency_ms,
            message="Connected",
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"Database health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            latency_ms=latency_ms,
            message=str(e),
        )


async def _check_milvus() -> HealthStatus:
    """检查 Milvus 连接"""
    start_time = time.perf_counter()
    try:
        from src.milvus import get_milvus_client

        client = get_milvus_client()
        stats = client.get_stats()

        latency_ms = (time.perf_counter() - start_time) * 1000
        if stats.get("connected"):
            return HealthStatus(
                status="healthy",
                latency_ms=latency_ms,
                message=f"Connected, {stats.get('collections_count', 0)} collections",
            )
        else:
            return HealthStatus(
                status="unhealthy",
                latency_ms=latency_ms,
                message=stats.get("error", "Connection failed"),
            )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"Milvus health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            latency_ms=latency_ms,
            message=str(e),
        )


def _check_api_config() -> HealthStatus:
    """检查 API 配置"""
    providers = settings.get_available_providers()
    available_count = sum(1 for p in providers if p["available"])

    if available_count > 0:
        return HealthStatus(
            status="healthy",
            message=f"{available_count}/{len(providers)} AI providers configured",
        )
    else:
        return HealthStatus(
            status="degraded",
            message="No AI providers configured",
        )
