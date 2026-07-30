# -*- coding: utf-8 -*-
"""
会话服务模块

封装会话和消息的业务逻辑。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logger import logger
from src.repositories.conversation import ConversationRepository, MessageRepository

if TYPE_CHECKING:
    from src.schemas.conversation import (
        ConversationCreate,
        ConversationUpdate,
        MessageCreate,
    )


class ConversationService:
    """
    会话服务

    封装会话管理的业务逻辑。
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        初始化会话服务

        Args:
            session: 异步数据库会话
        """
        self._session = session
        self._conversation_repo: Optional[ConversationRepository] = None
        self._message_repo: Optional[MessageRepository] = None

    @property
    def conversation_repo(self) -> ConversationRepository:
        """获取会话仓储（懒加载）"""
        if self._conversation_repo is None:
            self._conversation_repo = ConversationRepository(self._session)
        return self._conversation_repo

    @property
    def message_repo(self) -> MessageRepository:
        """获取消息仓储（懒加载）"""
        if self._message_repo is None:
            self._message_repo = MessageRepository(self._session)
        return self._message_repo

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        keyword: str | None = None,
        model_provider: str | None = None,
    ) -> tuple[list, int]:
        """
        获取会话列表

        Args:
            limit: 返回数量限制
            offset: 偏移量
            keyword: 搜索关键词
            model_provider: 模型提供商筛选

        Returns:
            (会话列表, 总数)
        """
        return await self.conversation_repo.list_recent(
            limit=limit,
            offset=offset,
            keyword=keyword,
            model_provider=model_provider,
        )

    async def get_conversation(self, conversation_id: str) -> dict:
        """
        获取会话详情

        Args:
            conversation_id: 会话 ID

        Returns:
            会话详情字典

        Raises:
            NotFoundError: 会话不存在
        """
        conversation = await self.conversation_repo.get_with_messages_or_raise(conversation_id)
        return self._to_conversation_detail_dict(conversation)

    async def create_conversation(
        self,
        conversation_id: str | None = None,
        title: str = "新对话",
        model_provider: str = "tongyi",
    ) -> dict:
        """
        创建会话

        Args:
            conversation_id: 会话 ID（可选，不提供则自动生成）
            title: 会话标题
            model_provider: 模型提供商

        Returns:
            创建的会话信息

        Raises:
            ConflictError: 会话已存在
        """
        import uuid

        conv_id = conversation_id or str(uuid.uuid4())

        conversation = await self.conversation_repo.create(
            conversation_id=conv_id,
            title=title,
            model_provider=model_provider,
        )

        return self._to_conversation_dict(conversation)

    async def update_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        summary: str | None = None,
        model_provider: str | None = None,
    ) -> dict:
        """
        更新会话

        Args:
            conversation_id: 会话 ID
            title: 新标题
            summary: 新摘要
            model_provider: 新模型提供商

        Returns:
            更新后的会话信息

        Raises:
            NotFoundError: 会话不存在
        """
        updates = {}
        if title is not None:
            updates["title"] = title
        if summary is not None:
            updates["summary"] = summary
        if model_provider is not None:
            updates["model_provider"] = model_provider

        if updates:
            conversation = await self.conversation_repo.update(conversation_id, **updates)
        else:
            conversation = await self.conversation_repo.get_by_id_or_raise(conversation_id)

        return self._to_conversation_dict(conversation)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除会话

        Args:
            conversation_id: 会话 ID

        Returns:
            是否成功

        Raises:
            NotFoundError: 会话不存在
        """
        return await self.conversation_repo.delete_with_messages(conversation_id)

    async def save_messages(
        self,
        conversation_id: str,
        messages: list[dict],
        clear_existing: bool = False,
    ) -> dict:
        """
        保存消息

        Args:
            conversation_id: 会话 ID
            messages: 消息列表
            clear_existing: 是否清除现有消息

        Returns:
            更新后的会话详情
        """
        conversation = await self.conversation_repo.get_with_messages(conversation_id)

        if conversation is None:
            # 自动创建会话
            conversation = await self.conversation_repo.create(
                conversation_id=conversation_id,
                title="新对话",
            )

            # 根据第一条用户消息更新标题
            first_user_msg = next(
                (m for m in messages if m.get("role") == "user"), None
            )
            if first_user_msg:
                content = first_user_msg.get("content", "")
                conversation.title = content[:20] + ("..." if len(content) > 20 else "")

        elif clear_existing:
            # 清除旧消息
            await self.message_repo.delete_by_conversation(conversation_id)

        # 添加新消息
        await self.message_repo.bulk_create(conversation_id, messages)

        # 重新加载会话
        conversation = await self.conversation_repo.get_with_messages_or_raise(conversation_id)

        return self._to_conversation_detail_dict(conversation)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> dict:
        """
        添加单条消息

        Args:
            conversation_id: 会话 ID
            role: 消息角色
            content: 消息内容

        Returns:
            创建的消息信息
        """
        # 确保会话存在
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            conversation = await self.conversation_repo.create(
                conversation_id=conversation_id,
                title="新对话",
            )

        message = await self.message_repo.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )

        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }

    def _to_conversation_dict(self, conversation) -> dict:
        """转换为会话字典"""
        return {
            "id": conversation.id,
            "title": conversation.title,
            "summary": conversation.summary,
            "model_provider": conversation.model_provider,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        }

    def _to_conversation_detail_dict(self, conversation) -> dict:
        """转换为会话详情字典（含消息）"""
        return {
            "id": conversation.id,
            "title": conversation.title,
            "summary": conversation.summary,
            "model_provider": conversation.model_provider,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                for msg in sorted(conversation.messages, key=lambda m: m.created_at or 0)
            ],
        }


# 服务工厂函数
_conversation_service_factory = None


def get_conversation_service(session: AsyncSession) -> ConversationService:
    """
    获取会话服务实例

    Args:
        session: 异步数据库会话

    Returns:
        ConversationService 实例
    """
    return ConversationService(session)
