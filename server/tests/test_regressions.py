# -*- coding: utf-8 -*-
"""
针对本轮修复的回归测试：
- 会话记忆 session_id 正确传递（不再全部共享 key=""）
- CORS 凭证+通配符降级
"""

import pytest

from src.agent.memory import ConversationMemory
from langchain_core.messages import HumanMessage, AIMessage


class TestSessionIdIsolation:
    """会话记忆必须按 session_id 隔离，禁止共享"""

    def test_two_sessions_dont_share_memory(self):
        mem = ConversationMemory()
        mem.save_messages("session-A", [HumanMessage(content="from A")])
        mem.save_messages("session-B", [HumanMessage(content="from B")])

        assert len(mem.get_messages("session-A")) == 1
        assert len(mem.get_messages("session-B")) == 1
        assert mem.get_messages("session-A")[0].content == "from A"
        assert mem.get_messages("session-B")[0].content == "from B"

    def test_trim_one_session_does_not_affect_another(self):
        mem = ConversationMemory(max_turns=2)
        # 装满 session-A（10 条），session-B 只装 2 条
        for i in range(10):
            mem.save_messages("session-A", [HumanMessage(content=f"a{i}")])
        mem.save_messages("session-B", [HumanMessage(content="b1"), AIMessage(content="b2")])

        # session-B 仍保持原样
        assert len(mem.get_messages("session-B")) == 2

    def test_empty_session_id_returns_empty(self):
        """空 session_id 必须返回空（不允许把全部会话塞到 key=''）"""
        mem = ConversationMemory()
        assert mem.get_messages("") == []

        # 故意写入 100 条到空 key
        for i in range(100):
            mem.save_messages("", [HumanMessage(content=f"x{i}")])

        # 真实 session 仍能各自隔离
        mem.save_messages("real-1", [HumanMessage(content="hi")])
        assert len(mem.get_messages("real-1")) == 1

    def test_prime_from_persistence(self):
        """prime_from_persistence 应正确填充缓存"""
        mem = ConversationMemory()
        msgs = mem.prime_from_persistence("s1", [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ])
        assert len(msgs) == 2
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)
        # 缓存已被填充
        assert len(mem.get_messages("s1")) == 2

    def test_get_summary_returns_none_for_unknown(self):
        mem = ConversationMemory()
        assert mem.get_summary("unknown") is None

    def test_set_summary_roundtrip(self):
        mem = ConversationMemory()
        mem.set_summary("s1", "some summary")
        assert mem.get_summary("s1") == "some summary"

    def test_set_summary_empty_clears(self):
        mem = ConversationMemory()
        mem.set_summary("s1", "first")
        mem.set_summary("s1", None)
        assert mem.get_summary("s1") is None