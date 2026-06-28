# -*- coding: utf-8 -*-
"""
测试共享 fixtures
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 将 server/ 加入 sys.path，确保测试中可以直接 import src
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


# ---------------------------------------------------------------------------
# 环境变量：防止加载真实 .env 导致测试依赖外部服务
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """每个测试运行前清空关键环境变量，防止误连真实服务。

    同时 patch load_dotenv 为空操作，阻止 Settings 从 .env 文件重新加载。
    """
    # patch settings 模块中已绑定的 load_dotenv 引用
    import sys
    settings_module = sys.modules["src.config.settings"]
    monkeypatch.setattr(settings_module, "load_dotenv", lambda *a, **kw: None)

    env_keys = [
        "ALIYUN_API_KEY", "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY", "GLM_API_KEY",
        "DOUBAO_API_KEY", "KIMI_API_KEY",
        "OPENAI_API_KEY", "AMAP_API_KEY",
        "MILVUS_HOST", "MYSQL_HOST", "MYSQL_PASSWORD",
        "DOUBAO_MODEL_NAME",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Settings fixture：提供一个可定制的 Settings 实例
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_settings(monkeypatch):
    """返回一个配置了 mock API Key 的 Settings 实例。"""
    monkeypatch.setenv("ALIYUN_API_KEY", "test-aliyun-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("GLM_API_KEY", "test-glm-key")
    monkeypatch.setenv("DOUBAO_API_KEY", "test-doubao-key")
    monkeypatch.setenv("DOUBAO_MODEL_NAME", "doubao-pro-32k")
    monkeypatch.setenv("KIMI_API_KEY", "test-kimi-key")

    from src.config.settings import Settings
    return Settings()


@pytest.fixture
def empty_settings(monkeypatch):
    """返回一个所有 API Key 为空的 Settings 实例。"""
    from src.config.settings import Settings
    return Settings()


# ---------------------------------------------------------------------------
# 临时目录
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_dir():
    """创建并返回一个临时目录，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
