# -*- coding: utf-8 -*-
"""
健康检查服务模块

封装健康检查、版本信息的业务逻辑。
API 层仅接收请求并调用本服务，不直接操作数据库或外部依赖。
"""

from __future__ import annotations

import sys
import time
from typing import Any

import fastapi

from src.core.config import settings
from src.core.logger import logger


class HealthService:
    """
    健康检查服务

    封装系统健康检查和版本信息的业务逻辑。
    """

    async def check_health(self) -> dict[str, Any]:
        """
        执行完整健康检查。

        检查各组件的连通状态并返回结构化结果。

        Returns:
            包含整体状态、版本、时间戳和各组件检查结果的字典
        """
        from datetime import datetime

        checks: dict[str, dict[str, Any]] = {}
        overall_status = "healthy"

        # 检查数据库
        db_status = await self._check_database()
        checks["database"] = db_status
        if db_status["status"] != "healthy":
            overall_status = "degraded"

        # 检查 Milvus
        milvus_status = await self._check_milvus()
        checks["milvus"] = milvus_status
        if milvus_status["status"] != "healthy":
            overall_status = "degraded"

        # 检查 API 配置
        api_status = self._check_api_config()
        checks["api_config"] = api_status

        return {
            "status": overall_status,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow(),
            "checks": checks,
        }

    def get_version_info(self) -> dict[str, Any]:
        """
        获取版本信息。

        返回应用、Python 运行时和主要依赖的版本。

        Returns:
            版本信息字典
        """
        return {
            "app": {
                "version": settings.APP_VERSION,
                "name": settings.APP_NAME,
                "description": "多模态智能助手",
            },
            "python": sys.version.split()[0],
            "fastapi": fastapi.__version__,
            "environment": settings.ENVIRONMENT,
        }

    def get_config_summary(self) -> dict[str, Any]:
        """
        获取配置摘要（脱敏）。

        Returns:
            配置摘要字典
        """
        return settings.get_config_summary()

    # ============ 内部检查方法 ============

    async def _check_database(self) -> dict[str, Any]:
        """检查数据库连接"""
        start_time = time.perf_counter()
        try:
            from src.infras.database import async_engine

            async with async_engine().connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))

            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": "Connected",
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "message": str(e),
            }

    async def _check_milvus(self) -> dict[str, Any]:
        """检查 Milvus 连接"""
        start_time = time.perf_counter()
        try:
            from src.infras import get_vector_store_provider

            client = get_vector_store_provider()
            stats = client.get_stats()

            latency_ms = (time.perf_counter() - start_time) * 1000
            if stats.get("connected"):
                return {
                    "status": "healthy",
                    "latency_ms": latency_ms,
                    "message": f"Connected, {stats.get('collections_count', 0)} collections",
                }
            else:
                return {
                    "status": "unhealthy",
                    "latency_ms": latency_ms,
                    "message": stats.get("error", "Connection failed"),
                }
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Milvus health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "message": str(e),
            }

    def _check_api_config(self) -> dict[str, Any]:
        """检查 API 配置"""
        providers = settings.get_available_providers()
        available_count = sum(1 for p in providers if p["available"])

        if available_count > 0:
            return {
                "status": "healthy",
                "message": f"{available_count}/{len(providers)} AI providers configured",
            }
        else:
            return {
                "status": "degraded",
                "message": "No AI providers configured",
            }


# ============ 单例 ============

_health_service: HealthService | None = None


def get_health_service() -> HealthService:
    """
    获取健康检查服务单例。

    Returns:
        HealthService 实例
    """
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
