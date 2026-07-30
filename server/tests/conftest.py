# -*- coding: utf-8 -*-
"""
测试共享 fixtures
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport


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
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)

    env_keys = [
        "ALIYUN_API_KEY", "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY", "GLM_API_KEY",
        "DOUBAO_API_KEY", "KIMI_API_KEY",
        "OPENAI_API_KEY", "AMAP_API_KEY",
        "MILVUS_HOST", "MILVUS_PORT",
        "MYSQL_HOST", "MYSQL_PASSWORD", "MYSQL_DATABASE",
        "DOUBAO_MODEL_NAME",
        "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Settings fixture：提供一个可定制的 Settings 实例
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_settings(monkeypatch) -> "Settings":
    """返回一个配置了 mock API Key 的 Settings 实例。"""
    monkeypatch.setenv("ALIYUN_API_KEY", "test-aliyun-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("GLM_API_KEY", "test-glm-key")
    monkeypatch.setenv("DOUBAO_API_KEY", "test-doubao-key")
    monkeypatch.setenv("DOUBAO_MODEL_NAME", "doubao-pro-32k")
    monkeypatch.setenv("KIMI_API_KEY", "test-kimi-key")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_DATABASE", "test_db")

    # 清除已导入的模块，重新加载
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith("src")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    from src.core.config import Settings
    return Settings()


@pytest.fixture
def empty_settings() -> "Settings":
    """返回一个所有 API Key 为空的 Settings 实例。"""
    from src.core.config import Settings
    return Settings()


# ---------------------------------------------------------------------------
# 临时目录
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """创建并返回一个临时目录，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# 数据库测试 fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def mock_db_session() -> AsyncMock:
    """返回一个 Mock 的 AsyncSession"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# API 测试 fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """返回一个测试用的 FastAPI 客户端"""
    # 清除已导入的模块
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith("src")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    # Mock 数据库初始化
    with patch("src.infras.mysql.async_init_db", new_callable=AsyncMock):
        from src.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# Mock 服务 fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_milvus_client() -> MagicMock:
    """返回一个 Mock 的 Milvus 客户端"""
    client = MagicMock()
    client.get_stats.return_value = {
        "connected": True,
        "host": "localhost",
        "port": 19530,
        "collections_count": 2,
        "collections": [
            {"name": "test_collection", "num_entities": 100}
        ]
    }
    client.list_collections.return_value = ["test_collection"]
    client.search_by_text = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_chat_service() -> MagicMock:
    """返回一个 Mock 的 ChatService"""
    from src.services.chat_service import ChatServiceResult

    service = MagicMock()
    service.handle_chat = AsyncMock(return_value=ChatServiceResult(
        answer="Test response",
        summary=None,
        trimmed_history=[]
    ))
    return service
