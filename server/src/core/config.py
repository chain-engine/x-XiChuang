# -*- coding: utf-8 -*-
"""
统一配置管理

从环境变量和配置文件加载配置，提供类型安全的配置访问。
支持多环境配置切换（开发/测试/生产）。
"""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

# 加载 .env 文件
_load_env_result = load_dotenv()


class Settings:
    """
    全局配置类

    从环境变量加载配置，支持多模型提供商配置。
    配置优先级：环境变量 > .env 文件 > 默认值
    """

    # ============ 环境标识 ============
    ENVIRONMENT: Final[str] = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION: Final[bool] = ENVIRONMENT == "production"
    IS_DEVELOPMENT: Final[bool] = ENVIRONMENT == "development"
    IS_TESTING: Final[bool] = ENVIRONMENT == "testing"

    # ============ 应用基础配置 ============
    APP_NAME: Final[str] = "西窗 XiChuang"
    APP_VERSION: Final[str] = "1.0.0"
    DEBUG: Final[bool] = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST: Final[str] = os.getenv("HOST", "0.0.0.0")
    PORT: Final[int] = int(os.getenv("PORT", "8000"))
    STRUCTURED: Final[bool] = os.getenv("STRUCTURED", "False").lower() in ("true", "1", "yes")

    # ============ 阿里云千问配置 ============
    ALIYUN_API_KEY: Final[str] = os.getenv("ALIYUN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or ""
    ALIYUN_API_BASE: Final[str] = os.getenv(
        "ALIYUN_API_BASE",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    ALIYUN_MODEL_NAME: Final[str] = os.getenv("ALIYUN_MODEL_NAME", "qwen-plus")
    ALIYUN_EMBEDDING_MODEL_NAME: Final[str] = os.getenv(
        "ALIYUN_EMBEDDING_MODEL_NAME",
        "text-embedding-v1"
    )

    # ============ DeepSeek 配置 ============
    DEEPSEEK_API_KEY: Final[str] = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_BASE: Final[str] = os.getenv(
        "DEEPSEEK_API_BASE",
        "https://api.deepseek.com/v1"
    )
    DEEPSEEK_MODEL_NAME: Final[str] = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

    # ============ GLM/智谱 配置 ============
    GLM_API_KEY: Final[str] = os.getenv("GLM_API_KEY", "")
    GLM_API_BASE: Final[str] = os.getenv(
        "GLM_API_BASE",
        "https://open.bigmodel.cn/api/paas/v4"
    )
    GLM_MODEL_NAME: Final[str] = os.getenv("GLM_MODEL_NAME", "glm-4")

    # ============ 火山/豆包 配置 ============
    DOUBAO_API_KEY: Final[str] = os.getenv("DOUBAO_API_KEY", "")
    DOUBAO_API_BASE: Final[str] = os.getenv(
        "DOUBAO_API_BASE",
        "https://ark.cn-beijing.volces.com/api/v3"
    )
    DOUBAO_MODEL_NAME: Final[str] = os.getenv("DOUBAO_MODEL_NAME", "")

    # ============ Kimi/月之暗面 配置 ============
    KIMI_API_KEY: Final[str] = os.getenv("KIMI_API_KEY", "")
    KIMI_API_BASE: Final[str] = os.getenv(
        "KIMI_API_BASE",
        "https://api.moonshot.cn/v1"
    )
    KIMI_MODEL_NAME: Final[str] = os.getenv("KIMI_MODEL_NAME", "moonshot-v1-8k")

    # ============ OpenAI 配置（用于 Whisper） ============
    OPENAI_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY", "")

    # ============ 高德地图 API 配置 ============
    AMAP_API_KEY: Final[str] = os.getenv("AMAP_API_KEY", "")

    # ============ Milvus 向量数据库配置 ============
    MILVUS_HOST: Final[str] = os.getenv("MILVUS_HOST", "192.168.21.254")
    MILVUS_PORT: Final[int] = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_USER: Final[str] = os.getenv("MILVUS_USER", "")
    MILVUS_PASSWORD: Final[str] = os.getenv("MILVUS_PASSWORD", "")

    # ============ MySQL 数据库配置 ============
    MYSQL_HOST: Final[str] = os.getenv("MYYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: Final[int] = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: Final[str] = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: Final[str] = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: Final[str] = os.getenv("MYSQL_DATABASE", "xichuang")

    # ============ 存储配置 ============
    STORAGE_TYPE: Final[str] = os.getenv("STORAGE_TYPE", "local")
    STATIC_DIR: Final[str] = os.getenv("STATIC_DIR", "server/statics")

    # ============ 阿里云 OSS 配置 ============
    ALIYUN_OSS_ACCESS_KEY_ID: Final[str] = os.getenv("ALIYUN_OSS_ACCESS_KEY_ID", "")
    ALIYUN_OSS_ACCESS_KEY_SECRET: Final[str] = os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "")
    ALIYUN_OSS_ENDPOINT: Final[str] = os.getenv("ALIYUN_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
    ALIYUN_OSS_BUCKET_NAME: Final[str] = os.getenv("ALIYUN_OSS_BUCKET_NAME", "")

    # ============ AI 模型通用配置 ============
    TEMPERATURE: Final[float] = float(os.getenv("TEMPERATURE", "0"))
    MAX_TOKENS: Final[int] = int(os.getenv("MAX_TOKENS", "4096"))
    REQUEST_TIMEOUT: Final[int] = int(os.getenv("REQUEST_TIMEOUT", "120"))

    # ============ CORS 配置 ============
    CORS_ORIGINS: Final[list[str]] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    ]
    CORS_ALLOW_CREDENTIALS: Final[bool] = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in (
        "true", "1", "yes"
    )

    # ============ 日志配置 ============
    LOG_LEVEL: Final[str] = os.getenv(
        "LOG_LEVEL",
        "DEBUG" if IS_DEVELOPMENT else "INFO"
    )
    LOG_DIR: Final[str] = os.getenv("LOG_DIR", "logs")
    LOG_RETENTION_DAYS: Final[int] = int(os.getenv("LOG_RETENTION_DAYS", "7"))

    # ============ 计算属性 ============

    @cached_property
    def DATABASE_URL(self) -> str:
        """获取同步数据库连接 URL"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @cached_property
    def ASYNC_DATABASE_URL(self) -> str:
        """获取异步数据库连接 URL"""
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @cached_property
    def PROJECT_ROOT(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parents[2]

    @cached_property
    def STATIC_DIR_PATH(self) -> Path:
        """获取静态文件目录"""
        return self.PROJECT_ROOT / self.STATIC_DIR

    @cached_property
    def LOG_DIR_PATH(self) -> Path:
        """获取日志目录"""
        return self.PROJECT_ROOT / self.LOG_DIR

    # ============ 模型配置验证 ============

    def validate_model_config(self, provider: str) -> bool:
        """
        验证指定模型提供商的配置是否完整

        Args:
            provider: 提供商名称 (tongyi/deepseek/glm/doubao/kimi)

        Returns:
            配置是否完整有效
        """
        validators: dict[str, lambda] = {
            "tongyi": lambda: bool(self.ALIYUN_API_KEY and self.ALIYUN_MODEL_NAME),
            "deepseek": lambda: bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_MODEL_NAME),
            "glm": lambda: bool(self.GLM_API_KEY and self.GLM_MODEL_NAME),
            "doubao": lambda: bool(self.DOUBAO_API_KEY and self.DOUBAO_MODEL_NAME),
            "kimi": lambda: bool(self.KIMI_API_KEY and self.KIMI_MODEL_NAME),
            "mock": lambda: True,
        }
        return validators.get(provider, lambda: False)()

    def get_provider_display_name(self, provider: str) -> str:
        """
        获取提供商显示名称

        Args:
            provider: 提供商名称

        Returns:
            显示名称
        """
        display_names: dict[str, str] = {
            "tongyi": "千问",
            "deepseek": "DeepSeek",
            "glm": "GLM",
            "doubao": "豆包",
            "kimi": "Kimi",
        }
        return display_names.get(provider, "未知")

    def get_provider_model_name(self, provider: str) -> str:
        """
        获取提供商的模型名称

        Args:
            provider: 提供商名称

        Returns:
            模型名称
        """
        model_names: dict[str, str] = {
            "tongyi": self.ALIYUN_MODEL_NAME,
            "deepseek": self.DEEPSEEK_MODEL_NAME,
            "glm": self.GLM_MODEL_NAME,
            "doubao": self.DOUBAO_MODEL_NAME,
            "kimi": self.KIMI_MODEL_NAME,
        }
        return model_names.get(provider, "unknown")

    def get_available_providers(self) -> list[dict[str, Any]]:
        """
        获取所有可用的模型提供商列表

        Returns:
            提供商信息列表
        """
        providers = [
            {
                "name": "tongyi",
                "display_name": "千问",
                "model_name": self.ALIYUN_MODEL_NAME,
                "available": self.validate_model_config("tongyi"),
            },
            {
                "name": "deepseek",
                "display_name": "DeepSeek",
                "model_name": self.DEEPSEEK_MODEL_NAME,
                "available": self.validate_model_config("deepseek"),
            },
            {
                "name": "glm",
                "display_name": "GLM",
                "model_name": self.GLM_MODEL_NAME,
                "available": self.validate_model_config("glm"),
            },
            {
                "name": "doubao",
                "display_name": "豆包",
                "model_name": self.DOUBAO_MODEL_NAME,
                "available": self.validate_model_config("doubao"),
            },
            {
                "name": "kimi",
                "display_name": "Kimi",
                "model_name": self.KIMI_MODEL_NAME,
                "available": self.validate_model_config("kimi"),
            },
        ]
        return providers

    def get_default_provider(self) -> str:
        """
        获取默认的模型提供商

        按优先级依次检查：tongyi > deepseek > glm > doubao > kimi

        Returns:
            默认提供商名称
        """
        priority = ["tongyi", "deepseek", "glm", "doubao", "kimi"]
        for provider in priority:
            if self.validate_model_config(provider):
                return provider
        return "tongyi"

    def get_config_summary(self) -> dict[str, Any]:
        """
        获取配置摘要（用于健康检查）

        Returns:
            配置摘要信息
        """
        return {
            "app_name": self.APP_NAME,
            "version": self.APP_VERSION,
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "providers": self.get_available_providers(),
            "default_provider": self.get_default_provider(),
            "milvus": {
                "host": self.MILVUS_HOST,
                "port": self.MILVUS_PORT,
            },
            "database": {
                "host": self.MYSQL_HOST,
                "port": self.MYSQL_PORT,
                "database": self.MYSQL_DATABASE,
            },
        }


# 全局配置单例
settings: Final[Settings] = Settings()
