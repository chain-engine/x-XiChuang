# -*- coding: utf-8 -*-
"""
MySQL ORM 模型单元测试
"""

from datetime import datetime

from src.infra.mysql.models import Base, Conversation, Message


class TestConversationModel:
    """Conversation 模型测试"""

    def test_create_conversation(self):
        conv = Conversation(id="test-id", title="测试会话", model_provider="tongyi")
        assert conv.id == "test-id"
        assert conv.title == "测试会话"
        assert conv.model_provider == "tongyi"
        assert conv.summary is None

    def test_custom_model_provider(self):
        conv = Conversation(id="id", title="t", model_provider="deepseek")
        assert conv.model_provider == "deepseek"

    def test_tablename(self):
        assert Conversation.__tablename__ == "conversations"

    def test_to_dict_without_timestamps(self):
        conv = Conversation(id="id-123", title="hello")
        conv.created_at = None
        conv.updated_at = None
        d = conv.to_dict()
        assert d["id"] == "id-123"
        assert d["title"] == "hello"
        assert d["created_at"] is None
        assert d["messages"] == []

    def test_to_dict_with_timestamps(self):
        conv = Conversation(id="id-123", title="hello")
        now = datetime(2025, 1, 1, 12, 0, 0)
        conv.created_at = now
        conv.updated_at = now
        d = conv.to_dict()
        assert d["created_at"] == "2025-01-01T12:00:00"


class TestMessageModel:
    """Message 模型测试"""

    def test_create_message(self):
        msg = Message(conversation_id="conv-1", role="user", content="你好")
        assert msg.conversation_id == "conv-1"
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_tablename(self):
        assert Message.__tablename__ == "messages"

    def test_to_dict_without_timestamp(self):
        msg = Message(conversation_id="c1", role="assistant", content="hi")
        msg.created_at = None
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "hi"
        assert d["created_at"] is None

    def test_to_dict_with_timestamp(self):
        msg = Message(conversation_id="c1", role="user", content="hi")
        now = datetime(2025, 6, 15, 10, 30, 0)
        msg.created_at = now
        d = msg.to_dict()
        assert d["created_at"] == "2025-06-15T10:30:00"


class TestBaseClass:
    """Base 基类测试"""

    def test_base_exists(self):
        assert Base is not None
        assert hasattr(Base, "metadata")
