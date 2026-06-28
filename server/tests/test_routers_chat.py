# -*- coding: utf-8 -*-
"""
聊天路由模块单元测试

主要测试辅助函数和 API 端点（mock 依赖服务）。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app.routers.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    _is_current_model_query,
    _resolve_provider_model,
    ProviderInfo,
    ProvidersResponse,
)


# ---------------------------------------------------------------------------
# 辅助函数测试
# ---------------------------------------------------------------------------

class TestIsCurrentModelQuery:
    """_is_current_model_query 测试"""

    def test_chinese_patterns(self):
        assert _is_current_model_query("当前使用的是什么模型") is True
        assert _is_current_model_query("你现在用的哪个模型") is True
        assert _is_current_model_query("哪个模型在运行") is True

    def test_english_patterns(self):
        assert _is_current_model_query("what model are you using") is True
        assert _is_current_model_query("which model is active") is True
        assert _is_current_model_query("current model") is True

    def test_provider_keyword(self):
        assert _is_current_model_query("provider") is True

    def test_normal_query(self):
        assert _is_current_model_query("今天天气怎么样") is False
        assert _is_current_model_query("帮我写一段代码") is False

    def test_empty_query(self):
        assert _is_current_model_query("") is False
        assert _is_current_model_query(None) is False

    def test_case_insensitive(self):
        assert _is_current_model_query("WHAT MODEL") is True
        assert _is_current_model_query("Provider") is True


class TestResolveProviderModel:
    """_resolve_provider_model 测试"""

    def test_known_provider(self, fake_settings):
        with patch("src.config.settings.settings", fake_settings):
            provider, display, model = _resolve_provider_model("tongyi")
            assert provider == "tongyi"
            assert display == "千问"
            assert model == "qwen-plus"

    def test_unknown_provider_falls_back(self, fake_settings):
        with patch("src.config.settings.settings", fake_settings):
            provider, display, model = _resolve_provider_model("nonexistent")
            assert provider in ("tongyi", "deepseek", "glm", "doubao", "kimi")

    def test_none_provider(self, fake_settings):
        with patch("src.config.settings.settings", fake_settings):
            provider, display, model = _resolve_provider_model(None)
            assert provider == "tongyi"


class TestPydanticModels:
    """Pydantic 模型验证测试"""

    def test_chat_message(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_chat_request_defaults(self):
        req = ChatRequest(session_id="s1", query="hi")
        assert req.history == []
        assert req.media_inputs == []
        assert req.use_direct_multimodal is False
        assert req.provider is None

    def test_chat_response(self):
        resp = ChatResponse(answer="hi", session_id="s1")
        assert resp.summary is None
        assert resp.trimmed_history == []


# ---------------------------------------------------------------------------
# API 端点测试（使用 TestClient + mock）
# ---------------------------------------------------------------------------


class TestGetProvidersEndpoint:
    """GET /api/chat/providers 测试"""

    def test_returns_providers_list(self, fake_settings):
        with patch("src.config.settings.settings", fake_settings):
            from src.app.main import create_app
            app = create_app()
            test_client = TestClient(app)
            resp = test_client.get("/api/chat/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "default" in data
        assert len(data["providers"]) == 5
