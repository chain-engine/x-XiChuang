# -*- coding: utf-8 -*-
"""
会话记忆模块

实现对话历史的存储、裁剪和摘要功能。
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.core.config import settings
from src.core.logger import logger
from src.agent.model import build_chat_model


class ConversationMemory:
    """
    会话记忆实现

    - 以 session_id 为键，在进程内存中保存消息列表
    - 仅保留最近 N 轮对话（用户 + 助手）
    - 使用大模型生成滚动摘要，作为长期记忆
    - 支持 LRU 淘汰策略，防止内存无限增长
    """

    # 最大会话数限制，超过后淘汰最旧的会话
    MAX_SESSIONS: int = 1000
    # 单个会话最大消息对数（用户+助手）
    MAX_TURNS: int = 10
    # 会话最大空闲时间（秒），超过后自动清理
    SESSION_TTL: int = 3600  # 1小时

    def __init__(self, max_turns: int = 10) -> None:
        self.max_turns = max_turns
        self._store: OrderedDict[str, List[BaseMessage]] = OrderedDict()
        self._summaries: Dict[str, str] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()

    def _evict_if_needed(self) -> None:
        """如果会话数超限，淘汰最旧的会话"""
        with self._lock:
            while len(self._store) >= self.MAX_SESSIONS:
                oldest_session_id, _ = self._store.popitem(last=False)
                self._summaries.pop(oldest_session_id, None)
                self._timestamps.pop(oldest_session_id, None)
                logger.debug(f"Evicted oldest session: {oldest_session_id}")

    def _clean_expired_sessions(self) -> None:
        """清理超时的会话"""
        current_time = time.time()
        expired = [
            sid for sid, ts in self._timestamps.items()
            if current_time - ts > self.SESSION_TTL
        ]
        for sid in expired:
            self._store.pop(sid, None)
            self._summaries.pop(sid, None)
            self._timestamps.pop(sid, None)
        if expired:
            logger.debug(f"Cleaned {len(expired)} expired sessions")

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """
        获取指定会话的历史消息列表

        Args:
            session_id: 会话ID

        Returns:
            消息列表（若不存在则返回空列表）
        """
        with self._lock:
            # 更新访问时间
            if session_id in self._timestamps:
                self._timestamps[session_id] = time.time()
                # 移动到末尾（LRU）
                self._store.move_to_end(session_id)
            return list(self._store.get(session_id, []))

    def save_messages(self, session_id: str, messages: List[BaseMessage]) -> None:
        """
        保存指定会话的消息列表

        Args:
            session_id: 会话ID
            messages: 消息列表
        """
        with self._lock:
            self._evict_if_needed()
            self._store[session_id] = list(messages)
            self._timestamps[session_id] = time.time()
            # 移动到末尾
            self._store.move_to_end(session_id)
            self._clean_expired_sessions()

    def trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        只保留最近 max_turns 轮对话（约等于 2 * max_turns 条消息）

        Args:
            messages: 完整消息列表

        Returns:
            裁剪后的消息列表
        """
        max_len = self.max_turns * 2
        if len(messages) <= max_len:
            return messages
        return messages[-max_len:]

    async def update_summary(
        self,
        session_id: str,
        messages: List[BaseMessage],
        provider: Optional[str] = None,
    ) -> Optional[str]:
        """
        使用大模型对当前会话做简短摘要

        Args:
            session_id: 会话ID
            messages: 需要摘要的消息列表
            provider: 指定模型提供方（可选）

        Returns:
            摘要文本；若 messages 为空则返回已有缓存摘要或 None
        """
        if not messages:
            return self._summaries.get(session_id)

        history_text = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in messages
            if isinstance(m, (HumanMessage, AIMessage))
        )

        prompt = (
            "请你用简洁的方式，总结下面对话的关键信息，便于后续继续聊天时作为长期记忆：\n\n"
            f"{history_text}\n\n"
            "输出要求：50-150字，中文。"
        )

        logger.debug("Updating summary for session_id=%s", session_id)

        try:
            summarizer, used_provider = build_chat_model(settings, preferred=provider)
            result = await summarizer.ainvoke([HumanMessage(content=prompt)])
            summary = str(result.content)
            with self._lock:
                self._summaries[session_id] = summary
            return summary
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            return self._summaries.get(session_id)

    def clear_session(self, session_id: str) -> None:
        """
        清除指定会话的所有数据

        Args:
            session_id: 会话ID
        """
        with self._lock:
            self._store.pop(session_id, None)
            self._summaries.pop(session_id, None)
            self._timestamps.pop(session_id, None)

    def get_all_sessions(self) -> List[str]:
        """获取所有会话ID列表"""
        with self._lock:
            return list(self._store.keys())

    def get_stats(self) -> Dict:
        """获取记忆统计信息"""
        with self._lock:
            return {
                "total_sessions": len(self._store),
                "max_sessions": self.MAX_SESSIONS,
                "session_ttl_seconds": self.SESSION_TTL,
                "max_turns_per_session": self.max_turns,
            }
