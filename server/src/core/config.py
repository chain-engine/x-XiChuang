"""
统一配置管理

参考 config_demo.py 的写法，使用 dataclass 组织配置，
支持从 .env 文件、环境变量和 YAML 配置文件加载。
配置优先级：环境变量 > .env 文件 > YAML 配置文件 > 默认值
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def _to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值"""
    return value.lower() in ("true", "1", "yes") if value else False


def _to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数"""
    return int(value) if value else default


def _to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数"""
    return float(value) if value else default


# ============ 配置数据类 ============


@dataclass
class AppConfig:
    """应用基础配置"""
    name: str = "西窗 XiChuang"
    version: str = "1.0.0"
    description: str = "多模态智能助手 - 支持文本、语音、图片、视频对话"
    environment: str = "development"
    debug: bool = True


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    dir: str = "logs"
    retention_days: int = 7
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"


@dataclass
class CORSConfig:
    """CORS 配置"""
    allow_origins: list[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = False
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class ModelProviderConfig:
    """模型提供商配置"""
    api_key: str = ""
    api_base: str = ""
    model_name: str = ""
    enabled: bool = False


@dataclass
class EmbeddingConfig:
    """嵌入模型配置"""
    model_name: str = "text-embedding-v1"
    chunk_size: int = 1500
    chunk_overlap: int = 200


@dataclass
class MilvusConfig:
    """Milvus 向量数据库配置"""
    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""


@dataclass
class MySQLConfig:
    """MySQL 数据库配置"""
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "xichuang"


@dataclass
class StorageConfig:
    """文件存储配置"""
    type: str = "local"
    static_dir: str = "server/statics"


@dataclass
class AliyunOSSConfig:
    """阿里云 OSS 配置"""
    access_key_id: str = ""
    access_key_secret: str = ""
    endpoint: str = "oss-cn-hangzhou.aliyuncs.com"
    bucket_name: str = ""


@dataclass
class AIConfig:
    """AI 模型通用配置"""
    temperature: float = 0.0
    max_tokens: int = 4096
    request_timeout: int = 120


# ============ 主配置类 ============


class Settings:
    """
    全局配置类

    使用 dataclass 组织配置，支持从环境变量加载。
    配置优先级：环境变量 > .env 文件 > 默认值
    """

    # 配置文件路径（可选）
    CONFIG_FILE_PATH: Final[str] = "config/config.yaml"

    def __init__(self) -> None:
        """初始化配置"""
        self._parse_from_env()

    def _parse_from_env(self) -> None:
        """从环境变量解析配置"""
        # ============ 应用基础配置 ============
        self.APP_NAME = os.getenv("APP_NAME", "西窗 XiChuang")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = _to_bool(os.getenv("DEBUG"))
        self.STRUCTURED = _to_bool(os.getenv("STRUCTURED"))
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = _to_int(os.getenv("PORT"), 8000)

        # 环境标识
        self.IS_PRODUCTION = self.ENVIRONMENT == "production"
        self.IS_DEVELOPMENT = self.ENVIRONMENT == "development"
        self.IS_TESTING = self.ENVIRONMENT == "testing"

        # ============ 应用配置对象 ============
        self.app = AppConfig(
            name=self.APP_NAME,
            version=self.APP_VERSION,
            environment=self.ENVIRONMENT,
            debug=self.DEBUG,
        )

        self.server = ServerConfig(
            host=self.HOST,
            port=self.PORT,
        )

        # ============ 日志配置 ============
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if self.IS_DEVELOPMENT else "INFO")
        self.LOG_DIR = os.getenv("LOG_DIR", "logs")
        self.LOG_RETENTION_DAYS = _to_int(os.getenv("LOG_RETENTION_DAYS"), 7)

        self.logging = LoggingConfig(
            level=self.LOG_LEVEL,
            dir=self.LOG_DIR,
            retention_days=self.LOG_RETENTION_DAYS,
        )

        # ============ CORS 配置 ============
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = [o.strip() for o in cors_origins.split(",")]
        self.CORS_ALLOW_CREDENTIALS = _to_bool(os.getenv("CORS_ALLOW_CREDENTIALS"))

        self.cors = CORSConfig(
            allow_origins=self.CORS_ORIGINS,
            allow_credentials=self.CORS_ALLOW_CREDENTIALS,
        )

        # ============ 阿里云千问配置 ============
        self.ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or ""
        self.ALIYUN_API_BASE = os.getenv(
            "ALIYUN_API_BASE",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.ALIYUN_MODEL_NAME = os.getenv("ALIYUN_MODEL_NAME", "qwen-plus")
        self.ALIYUN_EMBEDDING_MODEL_NAME = os.getenv(
            "ALIYUN_EMBEDDING_MODEL_NAME",
            "text-embedding-v1"
        )

        self.tongyi = ModelProviderConfig(
            api_key=self.ALIYUN_API_KEY,
            api_base=self.ALIYUN_API_BASE,
            model_name=self.ALIYUN_MODEL_NAME,
            enabled=bool(self.ALIYUN_API_KEY and self.ALIYUN_MODEL_NAME),
        )

        self.embedding = EmbeddingConfig(
            model_name=self.ALIYUN_EMBEDDING_MODEL_NAME,
        )

        # ============ DeepSeek 配置 ============
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_API_BASE = os.getenv(
            "DEEPSEEK_API_BASE",
            "https://api.deepseek.com/v1"
        )
        self.DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

        self.deepseek = ModelProviderConfig(
            api_key=self.DEEPSEEK_API_KEY,
            api_base=self.DEEPSEEK_API_BASE,
            model_name=self.DEEPSEEK_MODEL_NAME,
            enabled=bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_MODEL_NAME),
        )

        # ============ GLM/智谱 配置 ============
        self.GLM_API_KEY = os.getenv("GLM_API_KEY", "")
        self.GLM_API_BASE = os.getenv(
            "GLM_API_BASE",
            "https://open.bigmodel.cn/api/paas/v4"
        )
        self.GLM_MODEL_NAME = os.getenv("GLM_MODEL_NAME", "glm-4")

        self.glm = ModelProviderConfig(
            api_key=self.GLM_API_KEY,
            api_base=self.GLM_API_BASE,
            model_name=self.GLM_MODEL_NAME,
            enabled=bool(self.GLM_API_KEY and self.GLM_MODEL_NAME),
        )

        # ============ 火山/豆包 配置 ============
        self.DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "")
        self.DOUBAO_API_BASE = os.getenv(
            "DOUBAO_API_BASE",
            "https://ark.cn-beijing.volces.com/api/v3"
        )
        self.DOUBAO_MODEL_NAME = os.getenv("DOUBAO_MODEL_NAME", "")

        self.doubao = ModelProviderConfig(
            api_key=self.DOUBAO_API_KEY,
            api_base=self.DOUBAO_API_BASE,
            model_name=self.DOUBAO_MODEL_NAME,
            enabled=bool(self.DOUBAO_API_KEY and self.DOUBAO_MODEL_NAME),
        )

        # ============ Kimi/月之暗面 配置 ============
        self.KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
        self.KIMI_API_BASE = os.getenv(
            "KIMI_API_BASE",
            "https://api.moonshot.cn/v1"
        )
        self.KIMI_MODEL_NAME = os.getenv("KIMI_MODEL_NAME", "moonshot-v1-8k")

        self.kimi = ModelProviderConfig(
            api_key=self.KIMI_API_KEY,
            api_base=self.KIMI_API_BASE,
            model_name=self.KIMI_MODEL_NAME,
            enabled=bool(self.KIMI_API_KEY and self.KIMI_MODEL_NAME),
        )

        # ============ OpenAI 配置（用于 Whisper） ============
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

        # ============ Milvus 向量数据库配置 ============
        # 默认 localhost；Docker 部署通过环境变量覆盖为 milvus
        self.MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = _to_int(os.getenv("MILVUS_PORT"), 19530)
        self.MILVUS_USER = os.getenv("MILVUS_USER", "")
        self.MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "")

        self.milvus = MilvusConfig(
            host=self.MILVUS_HOST,
            port=self.MILVUS_PORT,
            user=self.MILVUS_USER,
            password=self.MILVUS_PASSWORD,
        )

        # ============ MySQL 数据库配置 ============
        self.MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.MYSQL_PORT = _to_int(os.getenv("MYSQL_PORT"), 3306)
        self.MYSQL_USER = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        self.MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "xichuang")

        self.mysql = MySQLConfig(
            host=self.MYSQL_HOST,
            port=self.MYSQL_PORT,
            user=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            database=self.MYSQL_DATABASE,
        )

        # ============ 存储配置 ============
        self.STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
        self.STATIC_DIR = os.getenv("STATIC_DIR", "server/statics")

        self.storage = StorageConfig(
            type=self.STORAGE_TYPE,
            static_dir=self.STATIC_DIR,
        )

        # ============ 阿里云 OSS 配置 ============
        self.ALIYUN_OSS_ACCESS_KEY_ID = os.getenv("ALIYUN_OSS_ACCESS_KEY_ID", "")
        self.ALIYUN_OSS_ACCESS_KEY_SECRET = os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "")
        self.ALIYUN_OSS_ENDPOINT = os.getenv("ALIYUN_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
        self.ALIYUN_OSS_BUCKET_NAME = os.getenv("ALIYUN_OSS_BUCKET_NAME", "")

        self.oss = AliyunOSSConfig(
            access_key_id=self.ALIYUN_OSS_ACCESS_KEY_ID,
            access_key_secret=self.ALIYUN_OSS_ACCESS_KEY_SECRET,
            endpoint=self.ALIYUN_OSS_ENDPOINT,
            bucket_name=self.ALIYUN_OSS_BUCKET_NAME,
        )

        # ============ AI 模型通用配置 ============
        self.TEMPERATURE = _to_float(os.getenv("TEMPERATURE"), 0.0)
        self.MAX_TOKENS = _to_int(os.getenv("MAX_TOKENS"), 4096)
        self.REQUEST_TIMEOUT = _to_int(os.getenv("REQUEST_TIMEOUT"), 120)

        self.ai = AIConfig(
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
            request_timeout=self.REQUEST_TIMEOUT,
        )

    # ============ 计算属性 ============

    @property
    def DATABASE_URL(self) -> str:
        """获取同步数据库连接 URL"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """获取异步数据库连接 URL"""
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def PROJECT_ROOT(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parents[2]

    @property
    def STATIC_DIR_PATH(self) -> Path:
        """获取静态文件目录"""
        return self.PROJECT_ROOT / self.STATIC_DIR

    @property
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
        validators = {
            "tongyi": lambda: self.tongyi.enabled,
            "deepseek": lambda: self.deepseek.enabled,
            "glm": lambda: self.glm.enabled,
            "doubao": lambda: self.doubao.enabled,
            "kimi": lambda: self.kimi.enabled,
            "mock": lambda: True,
        }
        validator = validators.get(provider)
        return validator() if validator else False

    def get_provider_display_name(self, provider: str) -> str:
        """获取提供商显示名称"""
        display_names = {
            "tongyi": "千问",
            "deepseek": "DeepSeek",
            "glm": "GLM",
            "doubao": "豆包",
            "kimi": "Kimi",
        }
        return display_names.get(provider, "未知")

    def get_provider_model_name(self, provider: str) -> str:
        """获取提供商的模型名称"""
        model_names = {
            "tongyi": self.ALIYUN_MODEL_NAME,
            "deepseek": self.DEEPSEEK_MODEL_NAME,
            "glm": self.GLM_MODEL_NAME,
            "doubao": self.DOUBAO_MODEL_NAME,
            "kimi": self.KIMI_MODEL_NAME,
        }
        return model_names.get(provider, "unknown")

    def get_available_providers(self) -> list[dict[str, Any]]:
        """获取所有可用的模型提供商列表"""
        return [
            {
                "name": "tongyi",
                "display_name": "千问",
                "model_name": self.ALIYUN_MODEL_NAME,
                "available": self.tongyi.enabled,
            },
            {
                "name": "deepseek",
                "display_name": "DeepSeek",
                "model_name": self.DEEPSEEK_MODEL_NAME,
                "available": self.deepseek.enabled,
            },
            {
                "name": "glm",
                "display_name": "GLM",
                "model_name": self.GLM_MODEL_NAME,
                "available": self.glm.enabled,
            },
            {
                "name": "doubao",
                "display_name": "豆包",
                "model_name": self.DOUBAO_MODEL_NAME,
                "available": self.doubao.enabled,
            },
            {
                "name": "kimi",
                "display_name": "Kimi",
                "model_name": self.KIMI_MODEL_NAME,
                "available": self.kimi.enabled,
            },
        ]

    def get_default_provider(self) -> str:
        """获取默认的模型提供商"""
        priority = ["tongyi", "deepseek", "glm", "doubao", "kimi"]
        for provider in priority:
            if self.validate_model_config(provider):
                return provider
        return "tongyi"

    def get_config_summary(self) -> dict[str, Any]:
        """获取配置摘要（用于健康检查）"""
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
