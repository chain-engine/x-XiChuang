# -*- coding: utf-8 -*-
"""
配置管理模块

从 .env 文件加载配置，提供统一的配置访问接口。
支持多个大模型提供商：千问、DeepSeek、GLM、火山/豆包、Kimi。
"""

import os
from typing import List, Optional

from dotenv import load_dotenv


class Settings:
    """
    配置类，从环境变量中读取配置

    支持的模型提供商:
    - tongyi (千问) - 默认
    - deepseek
    - glm (智谱/GLM)
    - doubao (火山/豆包)
    - kimi (月之暗面)
    """

    def __init__(self) -> None:
        # 加载 .env 文件
        load_dotenv()

        # ============ 阿里云千问配置 ============
        # 兼容不同环境变量命名：DashScope 通常叫 DASHSCOPE_API_KEY
        self.ALIYUN_API_KEY: str = (
            os.getenv("ALIYUN_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or ""
        )
        self.ALIYUN_API_BASE: str = os.getenv(
            "ALIYUN_API_BASE",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.ALIYUN_MODEL_NAME: str = os.getenv("ALIYUN_MODEL_NAME", "qwen-plus")
        self.ALIYUN_EMBEDDING_MODEL_NAME: str = os.getenv(
            "ALIYUN_EMBEDDING_MODEL_NAME",
            "text-embedding-v1"
        )

        # ============ DeepSeek 配置 ============
        self.DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_API_BASE: str = os.getenv(
            "DEEPSEEK_API_BASE",
            "https://api.deepseek.com/v1"
        )
        self.DEEPSEEK_MODEL_NAME: str = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

        # ============ GLM/智谱 配置 ============
        self.GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
        self.GLM_API_BASE: str = os.getenv(
            "GLM_API_BASE",
            "https://open.bigmodel.cn/api/paas/v4"
        )
        self.GLM_MODEL_NAME: str = os.getenv("GLM_MODEL_NAME", "glm-4")

        # ============ 火山/豆包 配置 ============
        self.DOUBAO_API_KEY: str = os.getenv("DOUBAO_API_KEY", "")
        self.DOUBAO_API_BASE: str = os.getenv(
            "DOUBAO_API_BASE",
            "https://ark.cn-beijing.volces.com/api/v3"
        )
        self.DOUBAO_MODEL_NAME: str = os.getenv("DOUBAO_MODEL_NAME", "")

        # ============ Kimi/月之暗面 配置 ============
        self.KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
        self.KIMI_API_BASE: str = os.getenv(
            "KIMI_API_BASE",
            "https://api.moonshot.cn/v1"
        )
        self.KIMI_MODEL_NAME: str = os.getenv("KIMI_MODEL_NAME", "moonshot-v1-8k")

        # ============ 阿里云 OSS 配置（可选） ============
        self.ALIYUN_OSS_ACCESS_KEY_ID: str = os.getenv("ALIYUN_OSS_ACCESS_KEY_ID", "")
        self.ALIYUN_OSS_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "")
        self.ALIYUN_OSS_ENDPOINT: str = os.getenv("ALIYUN_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
        self.ALIYUN_OSS_BUCKET_NAME: str = os.getenv("ALIYUN_OSS_BUCKET_NAME", "")

        # ============ OpenAI 配置（用于 Whisper） ============
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

        # ============ 高德地图 API 配置 ============
        self.AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")

        # ============ 通用配置 ============
        try:
            self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0"))
        except ValueError:
            self.TEMPERATURE: float = 0.0

        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
        self.STRUCTURED: bool = os.getenv("STRUCTURED", "False").lower() == "true"

        # ============ Milvus 向量数据库配置 ============
        self.MILVUS_HOST: str = os.getenv("MILVUS_HOST", "192.168.21.254")
        try:
            self.MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
        except ValueError:
            self.MILVUS_PORT: int = 19530

        # ============ 存储配置 ============
        self.STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # local 或 oss
        self.STATIC_DIR: str = os.getenv("STATIC_DIR", "server/statics")

        # ============ MySQL 数据库配置 ============
        self.MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
        try:
            self.MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
        except ValueError:
            self.MYSQL_PORT: int = 3306
        self.MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
        self.MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "xichuang")

    @property
    def DATABASE_URL(self) -> str:
        """获取数据库连接 URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """获取异步数据库连接 URL"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    def validate_model_config(self, model_name: str) -> bool:
        """
        验证模型配置是否完整

        Args:
            model_name: 模型名称 (tongyi/deepseek/glm/doubao/kimi)

        Returns:
            bool: 配置是否完整
        """
        validators = {
            "tongyi": lambda: bool(self.ALIYUN_API_KEY and self.ALIYUN_MODEL_NAME),
            "deepseek": lambda: bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_MODEL_NAME),
            "glm": lambda: bool(self.GLM_API_KEY and self.GLM_MODEL_NAME),
            "doubao": lambda: bool(self.DOUBAO_API_KEY and self.DOUBAO_MODEL_NAME),
            "kimi": lambda: bool(self.KIMI_API_KEY and self.KIMI_MODEL_NAME),
            "mock": lambda: True,
        }
        return validators.get(model_name, lambda: False)()

    def get_available_providers(self) -> List[dict]:
        """
        获取所有可用的模型提供商列表

        Returns:
            List[dict]: 可用提供商列表，每项包含 name, display_name, available
        """
        providers = [
            {"name": "tongyi", "display_name": "千问", "available": self.validate_model_config("tongyi")},
            {"name": "deepseek", "display_name": "DeepSeek", "available": self.validate_model_config("deepseek")},
            {"name": "glm", "display_name": "GLM", "available": self.validate_model_config("glm")},
            {"name": "doubao", "display_name": "豆包", "available": self.validate_model_config("doubao")},
            {"name": "kimi", "display_name": "Kimi", "available": self.validate_model_config("kimi")},
        ]
        return providers

    def get_default_provider(self) -> str:
        """
        获取默认的模型提供商

        优先级: tongyi > deepseek > glm > doubao > kimi
        如果都不可用，默认返回 tongyi
        """
        priority = ["tongyi", "deepseek", "glm", "doubao", "kimi"]
        for provider in priority:
            if self.validate_model_config(provider):
                return provider
        return "tongyi"


# 创建全局配置实例
settings: Settings = Settings()
