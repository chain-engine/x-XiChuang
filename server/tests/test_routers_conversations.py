# -*- coding: utf-8 -*-
"""
会话路由模块单元测试

使用 mock 替代真实数据库，测试 API 端点的逻辑。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app.routers.conversations import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)


class TestPydanticModels:
    """请求模型验证测试"""

    def test_conversation_create_defaults(self):
        req = ConversationCreate()
        assert req.title == "新对话"
        assert req.model_provider == "tongyi"
        assert req.id is None

    def test_conversation_create_with_id(self):
        req = ConversationCreate(id="custom-id", title="测试会话")
        assert req.id == "custom-id"
        assert req.title == "测试会话"

    def test_conversation_update_partial(self):
        req = ConversationUpdate(title="新标题")
        assert req.title == "新标题"
        assert req.summary is None
        assert req.model_provider is None

    def test_message_create(self):
        msg = MessageCreate(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
