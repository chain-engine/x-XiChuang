# -*- coding: utf-8 -*-
"""
Schemas 模块测试
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError

from src.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ProviderInfo,
    ProvidersResponse,
    MediaInput,
)
from src.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from src.schemas.common import (
    BaseQuery,
    HealthResponse,
    HealthStatus,
    VersionResponse,
    VersionInfo,
)
from src.schemas.milvus import (
    CollectionInfo,
    SearchRequest,
    SearchResponse,
    SearchResult,
)


class TestChatSchemas:
    """聊天 Schema 测试"""

    def test_chat_message(self):
        """测试聊天消息模型"""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_request(self):
        """测试聊天请求模型"""
        req = ChatRequest(
            session_id="test-session",
            query="Hello, how are you?"
        )
        assert req.session_id == "test-session"
        assert req.query == "Hello, how are you?"
        assert req.history == []
        assert req.media_inputs == []
        assert req.use_direct_multimodal is False

    def test_chat_request_with_media(self):
        """测试带媒体的聊天请求"""
        req = ChatRequest(
            session_id="test",
            query="Describe this image",
            media_inputs=[
                MediaInput(type="image", filename="test.jpg")
            ]
        )
        assert len(req.media_inputs) == 1
        assert req.media_inputs[0].type == "image"

    def test_chat_request_validation(self):
        """测试聊天请求校验"""
        with pytest.raises(PydanticValidationError):
            ChatRequest(session_id="test", query="")  # query 为空应失败

    def test_chat_response(self):
        """测试聊天响应模型"""
        resp = ChatResponse(
            answer="I am fine",
            session_id="test",
            summary="Greeting"
        )
        assert resp.answer == "I am fine"
        assert resp.session_id == "test"
        assert resp.summary == "Greeting"

    def test_provider_info(self):
        """测试提供商信息模型"""
        info = ProviderInfo(
            name="tongyi",
            display_name="千问",
            model_name="qwen-plus",
            available=True
        )
        assert info.name == "tongyi"
        assert info.available is True

    def test_providers_response(self):
        """测试提供商列表响应"""
        resp = ProvidersResponse(
            providers=[
                ProviderInfo(name="tongyi", display_name="千问", model_name="qwen", available=True)
            ],
            default="tongyi"
        )
        assert resp.default == "tongyi"
        assert len(resp.providers) == 1


class TestConversationSchemas:
    """会话 Schema 测试"""

    def test_conversation_create(self):
        """测试创建会话模型"""
        conv = ConversationCreate(title="Test Chat")
        assert conv.title == "Test Chat"
        assert conv.model_provider == "tongyi"
        assert conv.id is None

    def test_conversation_create_with_id(self):
        """测试带 ID 创建会话"""
        conv = ConversationCreate(id="custom-id", title="Custom Chat")
        assert conv.id == "custom-id"

    def test_conversation_update(self):
        """测试更新会话模型"""
        update = ConversationUpdate(title="New Title", summary="New summary")
        assert update.title == "New Title"
        assert update.summary == "New summary"
        assert update.model_provider is None

    def test_message_create(self):
        """测试创建消息模型"""
        msg = MessageCreate(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_response(self):
        """测试消息响应模型"""
        msg = MessageResponse(
            id=1,
            role="assistant",
            content="How can I help?",
            created_at=datetime.now()
        )
        assert msg.id == 1
        assert msg.role == "assistant"


class TestCommonSchemas:
    """通用 Schema 测试"""

    def test_base_query(self):
        """测试基础查询模型"""
        query = BaseQuery(page=1, page_size=20)
        assert query.page == 1
        assert query.page_size == 20

    def test_base_query_defaults(self):
        """测试基础查询默认值"""
        query = BaseQuery()
        assert query.page == 1
        assert query.page_size == 20

    def test_health_status(self):
        """测试健康状态模型"""
        status = HealthStatus(
            status="healthy",
            latency_ms=10.5,
            message="OK"
        )
        assert status.status == "healthy"
        assert status.latency_ms == 10.5

    def test_health_response(self):
        """测试健康响应模型"""
        resp = HealthResponse(
            status="healthy",
            version="1.0.0",
            checks={"database": HealthStatus(status="healthy")}
        )
        assert resp.status == "healthy"
        assert "database" in resp.checks

    def test_version_info(self):
        """测试版本信息模型"""
        info = VersionInfo(
            version="1.0.0",
            name="XiChuang",
            description="AI Assistant"
        )
        assert info.version == "1.0.0"

    def test_version_response(self):
        """测试版本响应模型"""
        resp = VersionResponse(
            app=VersionInfo(version="1.0.0", name="XiChuang", description=""),
            python="3.11.0",
            fastapi="0.111.0",
            environment="development"
        )
        assert resp.python == "3.11.0"
        assert resp.environment == "development"


class TestMilvusSchemas:
    """Milvus Schema 测试"""

    def test_collection_info(self):
        """测试集合信息模型"""
        info = CollectionInfo(
            name="test_collection",
            num_entities=100,
            dimension=768
        )
        assert info.name == "test_collection"
        assert info.num_entities == 100

    def test_search_request(self):
        """测试搜索请求模型"""
        req = SearchRequest(
            collection_name="test",
            query_text="search query",
            top_k=5
        )
        assert req.collection_name == "test"
        assert req.top_k == 5
        assert req.output_fields == ["text", "source"]

    def test_search_request_validation(self):
        """测试搜索请求校验"""
        with pytest.raises(PydanticValidationError):
            SearchRequest(
                collection_name="test",
                query_text="query",
                top_k=0  # top_k 必须 >= 1
            )

    def test_search_result(self):
        """测试搜索结果模型"""
        result = SearchResult(
            id=1,
            distance=0.95,
            entity={"text": "result text"}
        )
        assert result.id == 1
        assert result.distance == 0.95

    def test_search_response(self):
        """测试搜索响应模型"""
        resp = SearchResponse(
            success=True,
            collection_name="test",
            query_text="query",
            results=[]
        )
        assert resp.success is True
        assert resp.total == 0
