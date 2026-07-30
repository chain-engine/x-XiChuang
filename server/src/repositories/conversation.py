# -*- coding: utf-8 -*-
"""
会话仓储

封装会话和消息的数据库访问操作。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import delete, desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError, QueryError
from src.core.logger import logger
from src.infras.mysql.models import Conversation, Message
from .base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    会话仓储

    封装会话数据的数据库访问操作。
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        初始化会话仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(Conversation, session)

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        """
        根据 ID 获取会话

        Args:
            conversation_id: 会话 ID

        Returns:
            会话实例或 None
        """
        try:
            result = await self._session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise QueryError(f"Failed to get conversation: {e}") from e

    async def get_with_messages(self, conversation_id: str) -> Conversation | None:
        """
        获取会话及其消息列表

        Args:
            conversation_id: 会话 ID

        Returns:
            包含消息的会话实例或 None
        """
        try:
            result = await self._session.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.id == conversation_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get conversation with messages {conversation_id}: {e}")
            raise QueryError(f"Failed to get conversation: {e}") from e

    async def get_with_messages_or_raise(self, conversation_id: str) -> Conversation:
        """
        获取会话及其消息，不存在则抛出异常

        Args:
            conversation_id: 会话 ID

        Returns:
            包含消息的会话实例

        Raises:
            NotFoundError: 会话不存在
        """
        conversation = await self.get_with_messages(conversation_id)
        if conversation is None:
            raise NotFoundError(f"Conversation '{conversation_id}' not found")
        return conversation

    async def create(
        self,
        conversation_id: str,
        title: str = "新对话",
        model_provider: str = "tongyi",
        **kwargs: Any,
    ) -> Conversation:
        """
        创建会话

        Args:
            conversation_id: 会话 ID
            title: 会话标题
            model_provider: 模型提供商
            **kwargs: 额外字段

        Returns:
            创建的会话实例
        """
        try:
            # 检查是否已存在
            existing = await self.get_by_id(conversation_id)
            if existing:
                raise ConflictError(f"Conversation '{conversation_id}' already exists")

            conversation = Conversation(
                id=conversation_id,
                title=title,
                model_provider=model_provider,
                **kwargs,
            )
            self._session.add(conversation)
            await self._session.commit()
            await self._session.refresh(conversation)
            logger.info(f"Created conversation: {conversation_id}")
            return conversation
        except ConflictError:
            raise
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create conversation: {e}")
            raise QueryError(f"Failed to create conversation: {e}") from e

    async def list_recent(
        self,
        limit: int = 20,
        offset: int = 0,
        keyword: str | None = None,
        model_provider: str | None = None,
    ) -> tuple[Sequence[Conversation], int]:
        """
        获取最近的会话列表（带分页）

        Args:
            limit: 返回数量限制
            offset: 偏移量
            keyword: 搜索关键词（标题）
            model_provider: 模型提供商筛选

        Returns:
            (会话列表, 总数)
        """
        try:
            # 构建查询
            query = select(Conversation)
            count_query = select(func.count(Conversation.id))

            # 应用筛选
            if keyword:
                query = query.where(Conversation.title.ilike(f"%{keyword}%"))
                count_query = count_query.where(Conversation.title.ilike(f"%{keyword}%"))
            if model_provider:
                query = query.where(Conversation.model_provider == model_provider)
                count_query = count_query.where(Conversation.model_provider == model_provider)

            # 获取总数
            count_result = await self._session.execute(count_query)
            total = count_result.scalar_one() or 0

            # 获取分页数据
            query = query.order_by(desc(Conversation.updated_at))
            query = query.offset(offset).limit(limit)

            result = await self._session.execute(query)
            conversations = result.scalars().all()

            return conversations, total
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            raise QueryError(f"Failed to list conversations: {e}") from e

    async def update_title(self, conversation_id: str, title: str) -> Conversation:
        """
        更新会话标题

        Args:
            conversation_id: 会话 ID
            title: 新标题

        Returns:
            更新后的会话实例
        """
        return await self.update(conversation_id, title=title)

    async def update_summary(self, conversation_id: str, summary: str) -> Conversation:
        """
        更新会话摘要

        Args:
            conversation_id: 会话 ID
            summary: 新摘要

        Returns:
            更新后的会话实例
        """
        return await self.update(conversation_id, summary=summary)

    async def touch(self, conversation_id: str) -> bool:
        """
        更新会话的更新时间

        Args:
            conversation_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            conversation = await self.get_by_id_or_raise(conversation_id)
            conversation.updated_at = datetime.utcnow()
            await self._session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to touch conversation {conversation_id}: {e}")
            return False

    async def delete_with_messages(self, conversation_id: str) -> bool:
        """
        删除会话及其所有消息

        Args:
            conversation_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            conversation = await self.get_by_id_or_raise(conversation_id)
            await self._session.delete(conversation)
            await self._session.commit()
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise QueryError(f"Failed to delete conversation: {e}") from e

    async def bulk_delete(self, conversation_ids: list[str]) -> int:
        """
        批量删除会话

        Args:
            conversation_ids: 会话 ID 列表

        Returns:
            删除数量
        """
        try:
            result = await self._session.execute(
                delete(Conversation).where(Conversation.id.in_(conversation_ids))
            )
            await self._session.commit()
            deleted_count = result.rowcount or 0
            logger.info(f"Bulk deleted {deleted_count} conversations")
            return deleted_count
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to bulk delete conversations: {e}")
            raise QueryError(f"Failed to bulk delete conversations: {e}") from e


class MessageRepository(BaseRepository[Message]):
    """
    消息仓储

    封装消息数据的数据库访问操作。
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        初始化消息仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(Message, session)

    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """
        创建消息

        Args:
            conversation_id: 会话 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            **kwargs: 额外字段

        Returns:
            创建的消息实例
        """
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                **kwargs,
            )
            self._session.add(message)
            await self._session.commit()
            await self._session.refresh(message)

            # 更新会话的更新时间
            await self._update_conversation_timestamp(conversation_id)

            logger.debug(f"Created message for conversation {conversation_id}")
            return message
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to create message: {e}")
            raise QueryError(f"Failed to create message: {e}") from e

    async def get_by_conversation(
        self,
        conversation_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Message]:
        """
        获取会话的所有消息

        Args:
            conversation_id: 会话 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            消息列表
        """
        try:
            query = select(Message).where(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at)

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self._session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            raise QueryError(f"Failed to get messages: {e}") from e

    async def count_by_conversation(self, conversation_id: str) -> int:
        """
        获取会话的消息数量

        Args:
            conversation_id: 会话 ID

        Returns:
            消息数量
        """
        try:
            result = await self._session.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conversation_id
                )
            )
            return result.scalar_one() or 0
        except Exception as e:
            logger.error(f"Failed to count messages for conversation {conversation_id}: {e}")
            raise QueryError(f"Failed to count messages: {e}") from e

    async def delete_by_conversation(self, conversation_id: str) -> int:
        """
        删除会话的所有消息

        Args:
            conversation_id: 会话 ID

        Returns:
            删除数量
        """
        try:
            result = await self._session.execute(
                delete(Message).where(Message.conversation_id == conversation_id)
            )
            await self._session.commit()
            deleted_count = result.rowcount or 0
            logger.debug(f"Deleted {deleted_count} messages for conversation {conversation_id}")
            return deleted_count
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete messages for conversation {conversation_id}: {e}")
            raise QueryError(f"Failed to delete messages: {e}") from e

    async def bulk_create(
        self,
        conversation_id: str,
        messages: list[dict[str, str]],
    ) -> list[Message]:
        """
        批量创建消息

        Args:
            conversation_id: 会话 ID
            messages: 消息列表 [{"role": "user", "content": "..."}, ...]

        Returns:
            创建的消息列表
        """
        try:
            message_objects = [
                Message(conversation_id=conversation_id, **msg)
                for msg in messages
            ]
            self._session.add_all(message_objects)
            await self._session.commit()

            # 重新查询以获取完整的消息对象
            for msg in message_objects:
                await self._session.refresh(msg)

            # 更新会话的更新时间
            await self._update_conversation_timestamp(conversation_id)

            logger.info(f"Bulk created {len(message_objects)} messages for conversation {conversation_id}")
            return message_objects
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to bulk create messages: {e}")
            raise QueryError(f"Failed to bulk create messages: {e}") from e

    async def _update_conversation_timestamp(self, conversation_id: str) -> None:
        """更新会话的更新时间"""
        try:
            result = await self._session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.updated_at = datetime.utcnow()
                await self._session.commit()
        except Exception as e:
            logger.warning(f"Failed to update conversation timestamp: {e}")
