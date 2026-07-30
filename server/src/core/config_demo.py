#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置管理
支持从环境变量和YAML配置文件读取配置
"""

import os
from typing import Final, Any
from pathlib import Path
from dataclasses import dataclass, field
import yaml

from constants.enums import Environment


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    file_path: str = "logs/x-python.log"
    rotation: str = "1 day"
    retention: str = "7 days"
    compression: str = "zip"
    console_output: bool = True


@dataclass
class CORSConfig:
    """CORS配置"""
    enabled: bool = True
    allow_origins: str = "*"
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class RateLimitConfig:
    """限流配置"""
    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000


@dataclass
class DatabaseConfig:
    """数据库配置"""
    enabled: bool = False
    url: str = "sqlite:///./data/x-python.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis配置"""
    enabled: bool = False
    url: str = "redis://localhost:6379/0"
    pool_size: int = 10
    max_connections: int = 50
    decode_responses: bool = True
    socket_timeout: int = 5



@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


@dataclass
class ApiDocsConfig:
    """API文档配置"""
    enabled: bool = True
    title: str = "x-python API"
    description: str = "x-python Learning and Training Project API Documentation"
    version: str = "0.1.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"


def _to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值"""
    return value.lower() == 'true' if value else False


def _to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数"""
    return int(value) if value else default


def _to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数"""
    return float(value) if value else default


class Settings:
    """应用配置类

    支持从环境变量和YAML配置文件读取配置
    优先级：环境变量 > YAML配置文件 > 默认配置
    """

    # 配置文件路径
    CONFIG_FILE_PATH: Final[str] = 'config/config.yaml'

    def __init__(self) -> None:
        """初始化配置"""
        self._config: dict[str, Any] = self._load_config()
        self._parse_config()

    def _load_config(self) -> dict[str, Any]:
        """加载配置

        优先级：环境变量 > YAML配置文件 > 默认配置
        """
        config: dict[str, Any] = self._get_default_config()
        self._load_from_file(config)
        self._load_from_env(config)
        return config

    def _get_default_config(self) -> dict[str, Any]:
        """获取默认配置

        Returns:
            dict[str, Any]: 默认配置字典
        """
        return {
            'app': {
                'name': 'x-python',
                'version': '0.1.0',
                'description': 'Python Learning and Training Project',
                'environment': 'development',
                'debug': True,
                'timezone': 'Asia/Shanghai',
                'locale': 'zh_CN'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': 1,
                'reload': True
            },
            'logging': {
                'level': 'INFO',
                'format': '{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
                'file_path': 'logs/x-python.log',
                'rotation': '1 day',
                'retention': '7 days',
                'compression': 'zip',
                'console_output': True
            },
            'cors': {
                'enabled': True,
                'allow_origins': '*',
                'allow_credentials': True,
                'allow_methods': ['*'],
                'allow_headers': ['*']
            },
            'rate_limit': {
                'enabled': True,
                'requests_per_minute': 60,
                'requests_per_hour': 1000
            },
            'database': {
                'enabled': False,
                'url': 'sqlite:///./data/x-python.db',
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'echo': False
            },
            'redis': {
                'enabled': False,
                'url': 'redis://localhost:6379/0',
                'pool_size': 10,
                'max_connections': 50,
                'decode_responses': True,
                'socket_timeout': 5
            },
            'security': {
                'secret_key': 'your-secret-key-here',
                'algorithm': 'HS256',
                'access_token_expire_minutes': 30,
                'refresh_token_expire_days': 7
            },
            'api_docs': {
                'enabled': True,
                'title': 'x-python API',
                'description': 'x-python Learning and Training Project API Documentation',
                'version': '0.1.0',
                'docs_url': '/docs',
                'redoc_url': '/redoc',
                'openapi_url': '/openapi.json'
            }
        }

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """递归合并配置

        Args:
            base: 基础配置字典
            override: 要覆盖的配置字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_from_file(self, config: dict[str, Any]) -> None:
        """从YAML文件加载配置"""
        config_file: Path = Path(self.CONFIG_FILE_PATH)
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    file_config: dict[str, Any] = yaml.safe_load(f) or {}
                self._merge_config(config, file_config)
            except Exception as e:
                print(f"Warning: Cannot load config file {self.CONFIG_FILE_PATH}: {e}")

    def _load_from_env(self, config: dict[str, Any]) -> None:
        """从环境变量加载配置

        Args:
            config: 配置字典
        """
        # 应用配置
        if (value := os.environ.get('APP_NAME')):
            config['app']['name'] = value
        if (value := os.environ.get('APP_VERSION')):
            config['app']['version'] = value
        if (value := os.environ.get('APP_ENVIRONMENT')):
            config['app']['environment'] = value
        if (value := os.environ.get('APP_DEBUG')):
            config['app']['debug'] = _to_bool(value)

        # 服务器配置
        if (value := os.environ.get('SERVER_HOST')):
            config['server']['host'] = value
        if (value := os.environ.get('SERVER_PORT')):
            config['server']['port'] = _to_int(value)
        if (value := os.environ.get('SERVER_WORKERS')):
            config['server']['workers'] = _to_int(value)
        if (value := os.environ.get('SERVER_RELOAD')):
            config['server']['reload'] = _to_bool(value)

        # 日志配置
        if (value := os.environ.get('LOG_LEVEL')):
            config['logging']['level'] = value
        if (value := os.environ.get('LOG_FILE_PATH')):
            config['logging']['file_path'] = value
        if (value := os.environ.get('LOG_ROTATION')):
            config['logging']['rotation'] = value
        if (value := os.environ.get('LOG_RETENTION')):
            config['logging']['retention'] = value
        if (value := os.environ.get('LOG_COMPRESSION')):
            config['logging']['compression'] = value
        if (value := os.environ.get('LOG_CONSOLE_OUTPUT')):
            config['logging']['console_output'] = _to_bool(value)

        # CORS配置
        if (value := os.environ.get('CORS_ENABLED')):
            config['cors']['enabled'] = _to_bool(value)
        if (value := os.environ.get('CORS_ALLOW_ORIGINS')):
            config['cors']['allow_origins'] = value
        if (value := os.environ.get('CORS_ALLOW_CREDENTIALS')):
            config['cors']['allow_credentials'] = _to_bool(value)
        if (value := os.environ.get('CORS_ALLOW_METHODS')):
            config['cors']['allow_methods'] = value.split(',')
        if (value := os.environ.get('CORS_ALLOW_HEADERS')):
            config['cors']['allow_headers'] = value.split(',')

        # 限流配置
        if (value := os.environ.get('RATE_LIMIT_ENABLED')):
            config['rate_limit']['enabled'] = _to_bool(value)
        if (value := os.environ.get('RATE_LIMIT_REQUESTS_PER_MINUTE')):
            config['rate_limit']['requests_per_minute'] = _to_int(value)
        if (value := os.environ.get('RATE_LIMIT_REQUESTS_PER_HOUR')):
            config['rate_limit']['requests_per_hour'] = _to_int(value)

        # 数据库配置
        if (value := os.environ.get('DATABASE_ENABLED')):
            config['database']['enabled'] = _to_bool(value)
        if (value := os.environ.get('DATABASE_URL')):
            config['database']['url'] = value
        if (value := os.environ.get('DATABASE_POOL_SIZE')):
            config['database']['pool_size'] = _to_int(value)
        if (value := os.environ.get('DATABASE_MAX_OVERFLOW')):
            config['database']['max_overflow'] = _to_int(value)
        if (value := os.environ.get('DATABASE_POOL_TIMEOUT')):
            config['database']['pool_timeout'] = _to_int(value)
        if (value := os.environ.get('DATABASE_POOL_RECYCLE')):
            config['database']['pool_recycle'] = _to_int(value)
        if (value := os.environ.get('DATABASE_ECHO')):
            config['database']['echo'] = _to_bool(value)

        # Redis配置
        if (value := os.environ.get('REDIS_ENABLED')):
            config['redis']['enabled'] = _to_bool(value)
        if (value := os.environ.get('REDIS_URL')):
            config['redis']['url'] = value
        if (value := os.environ.get('REDIS_POOL_SIZE')):
            config['redis']['pool_size'] = _to_int(value)
        if (value := os.environ.get('REDIS_MAX_CONNECTIONS')):
            config['redis']['max_connections'] = _to_int(value)
        if (value := os.environ.get('REDIS_DECODE_RESPONSES')):
            config['redis']['decode_responses'] = _to_bool(value)
        if (value := os.environ.get('REDIS_SOCKET_TIMEOUT')):
            config['redis']['socket_timeout'] = _to_int(value)

        # 安全配置
        if (value := os.environ.get('SECRET_KEY')):
            config['security']['secret_key'] = value
        if (value := os.environ.get('SECURITY_ALGORITHM')):
            config['security']['algorithm'] = value
        if (value := os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES')):
            config['security']['access_token_expire_minutes'] = _to_int(value)
        if (value := os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS')):
            config['security']['refresh_token_expire_days'] = _to_int(value)

        # API文档配置
        if (value := os.environ.get('API_DOCS_ENABLED')):
            config['api_docs']['enabled'] = _to_bool(value)

    def _parse_config(self) -> None:
        """解析配置到具体配置对象"""
        self.app_name: str = self._config['app']['name']
        self.app_version: str = self._config['app']['version']
        self.app_description: str = self._config['app'].get('description', 'x-python Learning and Training Project')
        self.app_environment: str = self._config['app']['environment']
        self.app_debug: bool = self._config['app']['debug']
        self.app_timezone: str = self._config['app'].get('timezone', 'Asia/Shanghai')
        self.app_locale: str = self._config['app'].get('locale', 'zh_CN')

        self.server = ServerConfig(**self._config['server'])
        self.logging = LoggingConfig(**self._config['logging'])
        self.cors = CORSConfig(**self._config['cors'])
        self.rate_limit = RateLimitConfig(**self._config['rate_limit'])
        self.database = DatabaseConfig(**self._config['database'])
        self.redis = RedisConfig(**self._config['redis'])
        self.security = SecurityConfig(**self._config['security'])
        self.api_docs = ApiDocsConfig(**self._config['api_docs'])

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_environment == Environment.DEVELOPMENT.desc

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.app_environment == Environment.TESTING.desc

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_environment == Environment.PRODUCTION.desc

    def reload(self) -> None:
        """重新加载配置"""
        self._config = self._load_config()
        self._parse_config()


# 创建全局配置实例
settings: Final[Settings] = Settings()