# -*- coding: utf-8 -*-
"""
服务层接口

定义业务逻辑层的抽象契约。
所有具体服务必须实现对应的接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel


# ============ 请求/响应模型 ============

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: list[dict[str, str]] | None = None
    model: str | None = None
    temperature: float | None = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    reply: str
    model: str
    usage: dict[str, int] | None = None


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str
    done: bool = False


# ============ 聊天服务接口 ============

class IChatService(ABC):
    """
    聊天服务接口

    定义 AI 对话服务的抽象契约。
    """

    @abstractmethod
    async def handle_chat(
        self,
        session_id: str,
        query: str,
        history: list,
        media_inputs: list,
        use_direct_multimodal: bool = True,
        provider: str | None = None,
    ) -> Any:
        """执行完整的对话流程（非流式）"""
        ...

    @abstractmethod
    async def handle_stream(
        self,
        session_id: str,
        query: str,
        history: list,
        media_inputs: list,
        use_direct_multimodal: bool = True,
        provider: str | None = None,
    ):
        """流式对话处理（返回 AsyncIterator）"""
        ...


# ============ 会话服务接口 ============

class IConversationService(ABC):
    """
    会话服务接口

    定义会话管理服务的抽象契约。
    """

    @abstractmethod
    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        keyword: str | None = None,
        model_provider: str | None = None,
    ) -> tuple[list, int]:
        """获取会话列表"""
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """获取单个会话详情"""
        ...

    @abstractmethod
    async def create_conversation(
        self,
        conversation_id: str | None = None,
        title: str = "新对话",
        model_provider: str = "tongyi",
    ) -> dict[str, Any]:
        """创建新会话"""
        ...

    @abstractmethod
    async def update_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        summary: str | None = None,
        model_provider: str | None = None,
    ) -> dict[str, Any]:
        """更新会话信息"""
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        ...

    @abstractmethod
    async def save_messages(
        self,
        conversation_id: str,
        messages: list[dict[str, str]],
        clear_existing: bool = False,
    ) -> dict[str, Any]:
        """批量保存消息"""
        ...

    @abstractmethod
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        """添加单条消息"""
        ...

    @abstractmethod
    async def persist_chat_turn(
        self,
        conversation_id: str,
        user_query: str,
        assistant_answer: str,
        summary: str | None = None,
        provider: str | None = None,
    ) -> None:
        """持久化一轮对话"""
        ...

    @abstractmethod
    async def load_history_to_memory(self, session_id: str) -> None:
        """从数据库加载历史到 in-memory 缓存"""
        ...


# ============ Milvus 服务接口 ============

class IMilvusService(ABC):
    """
    Milvus 向量存储服务接口

    定义向量数据库操作的抽象契约。
    """

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """获取 Milvus 统计信息"""
        ...

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """列出所有集合"""
        ...

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
        """获取集合详情"""
        ...

    @abstractmethod
    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """文本搜索"""
        ...

    @abstractmethod
    async def delete_data(
        self,
        collection_name: str,
        expr: str,
    ) -> int:
        """删除数据"""
        ...

    @abstractmethod
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        ...
