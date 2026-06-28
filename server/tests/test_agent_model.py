# -*- coding: utf-8 -*-
"""
Agent 模型路由模块单元测试
"""

from unittest.mock import MagicMock, patch

from src.agent.model import ModelProvider, build_chat_model


class TestModelProvider:
    """ModelProvider 枚举测试"""

    def test_enum_values(self):
        assert ModelProvider.tongyi.value == "tongyi"
        assert ModelProvider.deepseek.value == "deepseek"
        assert ModelProvider.glm.value == "glm"
        assert ModelProvider.doubao.value == "doubao"
        assert ModelProvider.kimi.value == "kimi"
        assert ModelProvider.mock.value == "mock"


class TestBuildChatModel:
    """build_chat_model 函数测试"""

    @patch("src.agent.model.ChatOpenAI")
    def test_preferred_provider_valid(self, mock_chat, fake_settings):
        """指定的 provider 可用时使用它"""
        mock_chat.return_value = MagicMock()
        model, provider = build_chat_model(fake_settings, preferred="tongyi")
        assert provider == ModelProvider.tongyi
        mock_chat.assert_called_once()

    @patch("src.agent.model.ChatOpenAI")
    def test_preferred_provider_unknown(self, mock_chat, fake_settings):
        """未知 provider 按优先级回退"""
        mock_chat.return_value = MagicMock()
        model, provider = build_chat_model(fake_settings, preferred="nonexistent")
        assert provider == ModelProvider.tongyi

    @patch("src.agent.model.ChatOpenAI")
    def test_preferred_provider_not_configured(self, mock_chat, empty_settings):
        """指定的 provider 未配置时按优先级选择"""
        mock_chat.return_value = MagicMock()
        model, provider = build_chat_model(empty_settings, preferred="deepseek")
        # deepseek 没有 key，回退到 mock
        assert provider == ModelProvider.mock

    @patch("src.agent.model.ChatOpenAI")
    def test_fallback_to_mock(self, mock_chat, empty_settings):
        """所有真实 provider 都不可用时回退到 mock"""
        mock_chat.return_value = MagicMock()
        model, provider = build_chat_model(empty_settings)
        assert provider == ModelProvider.mock

    @patch("src.agent.model.ChatOpenAI")
    def test_no_preferred_selects_first_available(self, mock_chat, fake_settings):
        """不指定 preferred 时选择优先级最高的可用 provider"""
        mock_chat.return_value = MagicMock()
        model, provider = build_chat_model(fake_settings)
        assert provider == ModelProvider.tongyi

    @patch("src.agent.model.ChatOpenAI")
    def test_build_with_correct_config(self, mock_chat, fake_settings):
        """构建的 ChatOpenAI 实例使用正确的配置"""
        mock_chat.return_value = MagicMock()
        build_chat_model(fake_settings, preferred="tongyi")
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["api_key"] == "test-aliyun-key"
        assert call_kwargs["model"] == "qwen-plus"
