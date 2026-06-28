# -*- coding: utf-8 -*-
"""
会话记忆模块单元测试
"""

from langchain_core.messages import AIMessage, HumanMessage

from src.agent.memory import ConversationMemory


class TestConversationMemory:
    """ConversationMemory 测试"""

    def test_get_messages_empty(self):
        mem = ConversationMemory()
        assert mem.get_messages("nonexistent") == []

    def test_save_and_get_messages(self):
        mem = ConversationMemory()
        msgs = [HumanMessage(content="hello"), AIMessage(content="hi")]
        mem.save_messages("s1", msgs)
        result = mem.get_messages("s1")
        assert len(result) == 2
        assert result[0].content == "hello"
        assert result[1].content == "hi"

    def test_get_messages_returns_copy(self):
        """get_messages 应返回副本，修改不影响内部状态"""
        mem = ConversationMemory()
        mem.save_messages("s1", [HumanMessage(content="hello")])
        result = mem.get_messages("s1")
        result.append(AIMessage(content="extra"))
        assert len(mem.get_messages("s1")) == 1

    def test_clear_session(self):
        mem = ConversationMemory()
        mem.save_messages("s1", [HumanMessage(content="hello")])
        mem.clear_session("s1")
        assert mem.get_messages("s1") == []

    def test_clear_nonexistent_session(self):
        """清除不存在的 session 不应报错"""
        mem = ConversationMemory()
        mem.clear_session("nonexistent")  # 不抛异常

    def test_get_all_sessions(self):
        mem = ConversationMemory()
        mem.save_messages("s1", [HumanMessage(content="a")])
        mem.save_messages("s2", [HumanMessage(content="b")])
        sessions = mem.get_all_sessions()
        assert set(sessions) == {"s1", "s2"}


class TestTrimMessages:
    """trim_messages 测试"""

    def test_no_trimming_needed(self):
        mem = ConversationMemory(max_turns=5)
        msgs = [HumanMessage(content=f"msg{i}") for i in range(4)]
        trimmed = mem.trim_messages(msgs)
        assert len(trimmed) == 4

    def test_trimming_applied(self):
        mem = ConversationMemory(max_turns=3)
        msgs = [HumanMessage(content=f"msg{i}") for i in range(10)]
        trimmed = mem.trim_messages(msgs)
        # max_turns=3, max_len = 3*2 = 6
        assert len(trimmed) == 6
        assert trimmed[0].content == "msg4"

    def test_exact_boundary(self):
        mem = ConversationMemory(max_turns=2)
        msgs = [HumanMessage(content=f"msg{i}") for i in range(4)]
        trimmed = mem.trim_messages(msgs)
        assert len(trimmed) == 4

    def test_empty_messages(self):
        mem = ConversationMemory(max_turns=5)
        assert mem.trim_messages([]) == []


class TestUpdateSummary:
    """update_summary 异步测试"""

    async def test_empty_messages_returns_cached(self):
        """空消息列表时返回已有缓存摘要"""
        mem = ConversationMemory()
        mem._summaries["s1"] = "cached summary"
        result = await mem.update_summary("s1", [])
        assert result == "cached summary"

    async def test_empty_messages_no_cache(self):
        mem = ConversationMemory()
        result = await mem.update_summary("s1", [])
        assert result is None
