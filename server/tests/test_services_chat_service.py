# -*- coding: utf-8 -*-
"""
对话服务模块单元测试

使用 mock 替代真实 LLM 和知识库调用。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.app.services.chat_service import ChatGraphState, ChatServiceResult


class TestChatGraphState:
    """ChatGraphState 状态模型测试"""

    def test_default_values(self):
        state = ChatGraphState()
        assert state.messages == []
        assert state.media_inputs == []
        assert state.query == ""
        assert state.use_direct_multimodal is True
        assert state.provider is None
        assert state.answer is None
        assert state.summary is None

    def test_custom_values(self):
        from src.agent.media import MediaInput, MediaType

        media = MediaInput(type=MediaType.IMAGE, url="https://example.com/img.png")
        state = ChatGraphState(
            messages=[HumanMessage(content="hi")],
            query="hello",
            provider="tongyi",
            media_inputs=[media],
        )
        assert len(state.messages) == 1
        assert state.query == "hello"
        assert state.provider == "tongyi"
        assert len(state.media_inputs) == 1


class TestChatServiceResult:
    """ChatServiceResult 数据类测试"""

    def test_creation(self):
        result = ChatServiceResult(
            answer="hello",
            summary="a summary",
            trimmed_history=[HumanMessage(content="hi"), AIMessage(content="hello")],
        )
        assert result.answer == "hello"
        assert result.summary == "a summary"
        assert len(result.trimmed_history) == 2

    def test_none_summary(self):
        result = ChatServiceResult(
            answer="ok",
            summary=None,
            trimmed_history=[],
        )
        assert result.summary is None
