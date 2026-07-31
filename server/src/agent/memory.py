# -*- coding: utf-8 -*-
"""
会话记忆模块

实现对话历史的内存 LRU 缓存、裁剪和摘要功能。

数据模型：
- MySQL (Conversation/Message) 是**唯一持久源**。
- 本类的 in-memory 字典只是 LRU 缓存，目的是减少每轮都从 DB 拉历史。
- 缓存由「读取时按需填充」+ 「写入时更新」组成。

线程安全：所有写操作通过 self._lock 串行化。
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.core.config import settings
from src.core.logger import logger
from src.agent.model import build_chat_model


def _to_langchain_messages(items: List[dict]) -> List[BaseMessage]:
    """把 [{role, content}] 转成 LangChain 消息对象。"""
    out: List[BaseMessage] = []
    for it in items:
        role = (it.get("role") or "").lower()
        content = it.get("content") or ""
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        elif role == "system":
            out.append(SystemMessage(content=content))
        # 其他 role 忽略
    return out


def _from_langchain_messages(messages: List[BaseMessage]) -> List[dict]:
    """把 LangChain 消息对象转回可持久化字典。"""
    out: List[dict] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            out.append({"role": "assistant", "content": m.content})
        elif isinstance(m, SystemMessage):
            out.append({"role": "system", "content": m.content})
    return out


class ConversationMemory:
    """
    会话记忆实现（MySQL 持久层之上的 LRU 缓存）

    - 以 session_id 为键，在进程内存中保存消息列表
    - 仅保留最近 N 轮对话（用户 + 助手）
    - 使用大模型生成滚动摘要，作为长期记忆
    - 支持 LRU 淘汰策略，防止内存无限增长
    - **持久层（MySQL）由 ConversationService 维护；本类仅做缓存**
    """

    MAX_SESSIONS: int = 1000           # 超过后淘汰最旧的会话
    MAX_TURNS: int = 10                # 单个会话最大消息对数（用户+助手）
    SESSION_TTL: int = 3600            # 会话最大空闲时间（秒），超过后清理缓存

    def __init__(self, max_turns: int = 10) -> None:
        self.max_turns = max_turns
        self._store: "OrderedDict[str, List[BaseMessage]]" = OrderedDict()
        self._summaries: Dict[str, str] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        # 防止同 session 反复打到 DB 的简易 lock
        self._fetch_locks: Dict[str, asyncio.Lock] = {}

    def _evict_if_needed(self) -> None:
        """如果会话数超限，淘汰最旧的会话"""
        with self._lock:
            while len(self._store) >= self.MAX_SESSIONS:
                oldest_session_id, _ = self._store.popitem(last=False)
                self._summaries.pop(oldest_session_id, None)
                self._timestamps.pop(oldest_session_id, None)
                logger.debug(f"Evicted oldest session: {oldest_session_id}")

    def _clean_expired_sessions(self) -> None:
        """清理超时的会话缓存"""
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
            logger.debug(f"Cleaned {len(expired)} expired session caches")

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """
        获取指定会话的历史消息列表（仅查缓存）。

        如果缓存未命中，返回空列表——调用方需要先 ensure_persisted 触发 DB 加载。
        """
        if not session_id:
            return []
        with self._lock:
            if session_id in self._timestamps:
                self._timestamps[session_id] = time.time()
                self._store.move_to_end(session_id)
            return list(self._store.get(session_id, []))

    def prime_from_persistence(self, session_id: str, raw_messages: List[dict]) -> List[BaseMessage]:
        """
        把持久层加载的消息填入缓存，返回完整消息列表。

        同一 session 在第一次填充后会保留缓存，直到 TTL 过期或被 LRU 淘汰。
        """
        if not session_id:
            return []
        msgs = _to_langchain_messages(raw_messages)
        with self._lock:
            self._evict_if_needed()
            self._store[session_id] = list(msgs)
            self._timestamps[session_id] = time.time()
            self._store.move_to_end(session_id)
            self._clean_expired_sessions()
        return list(msgs)

    def save_messages(self, session_id: str, messages: List[BaseMessage]) -> None:
        """
        更新会话缓存（**仅缓存，不写 DB**）。
        DB 持久化由 ChatService 在 summarize_node 后调用 ConversationService 完成。
        """
        if not session_id:
            return
        with self._lock:
            self._evict_if_needed()
            self._store[session_id] = list(messages)
            self._timestamps[session_id] = time.time()
            self._store.move_to_end(session_id)
            self._clean_expired_sessions()

    def trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """只保留最近 max_turns 轮对话（约等于 2 * max_turns 条消息）"""
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
        """使用大模型对当前会话做简短摘要。失败时返回已有缓存摘要。"""
        if not session_id:
            return None

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

    def get_summary(self, session_id: str) -> Optional[str]:
        """获取已缓存的摘要（不触发 LLM 调用）。"""
        if not session_id:
            return None
        with self._lock:
            return self._summaries.get(session_id)

    def set_summary(self, session_id: str, summary: Optional[str]) -> None:
        """写入/覆盖会话摘要缓存。"""
        if not session_id:
            return
        with self._lock:
            if summary:
                self._summaries[session_id] = summary
            else:
                self._summaries.pop(session_id, None)

    def clear_session(self, session_id: str) -> None:
        """清除指定会话的所有缓存。"""
        with self._lock:
            self._store.pop(session_id, None)
            self._summaries.pop(session_id, None)
            self._timestamps.pop(session_id, None)

    def get_all_sessions(self) -> List[str]:
        """获取所有缓存中的会话ID列表"""
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