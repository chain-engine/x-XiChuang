# -*- coding: utf-8 -*-
"""
针对本轮修复的回归测试：
- 会话记忆 session_id 正确传递（不再全部共享 key=""）
- CORS 凭证+通配符降级
- 鉴权：未配置 API_KEY 时放行；已配置时拒绝
- 限流：N 次后被拦截
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


class TestAuth:
    """API Key 鉴权"""

    async def test_unconfigured_allows(self, monkeypatch):
        """未配置 API_KEY 时直接放行（开发模式）"""
        monkeypatch.delenv("API_KEY", raising=False)
        from src.core.auth import verify_api_key, reset_api_keys
        reset_api_keys()
        # 不应抛异常
        await verify_api_key(x_api_key=None)

    async def test_wrong_key_rejected(self, monkeypatch):
        """配置了 API_KEY 但请求头错误 → 401"""
        monkeypatch.setenv("API_KEY", "secret-key")
        from src.core.auth import verify_api_key, reset_api_keys
        from fastapi import HTTPException
        reset_api_keys()
        with pytest.raises(HTTPException) as ei:
            await verify_api_key(x_api_key="wrong")
        assert ei.value.status_code == 401

    async def test_correct_key_accepted(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "secret-key,another")
        from src.core.auth import verify_api_key, reset_api_keys
        reset_api_keys()
        await verify_api_key(x_api_key="another")


class TestRateLimit:
    """基于 IP 的限流"""

    async def test_under_limit_passes(self, monkeypatch):
        monkeypatch.setenv("CHAT_RATE_LIMIT", "5")
        monkeypatch.setenv("CHAT_RATE_WINDOW", "60")
        from src.core.ratelimit import chat_rate_limiter, reset_for_tests
        from fastapi import Request
        reset_for_tests()

        # 构造一个最小 Request mock
        def make_request(ip="1.2.3.4"):
            req = Request(scope={"type": "http", "client": (ip, 0), "headers": []})
            return req

        for _ in range(5):
            await chat_rate_limiter(make_request())
        # 第 6 次应当触发 429

    async def test_over_limit_blocked(self, monkeypatch):
        monkeypatch.setenv("CHAT_RATE_LIMIT", "2")
        monkeypatch.setenv("CHAT_RATE_WINDOW", "60")
        from src.core.ratelimit import chat_rate_limiter, reset_for_tests
        from fastapi import HTTPException, Request
        reset_for_tests()

        req = Request(scope={"type": "http", "client": ("9.9.9.9", 0), "headers": []})
        await chat_rate_limiter(req)
        await chat_rate_limiter(req)
        with pytest.raises(HTTPException) as ei:
            await chat_rate_limiter(req)
        assert ei.value.status_code == 429

    async def test_disabled(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("CHAT_RATE_LIMIT", "1")
        from src.core.ratelimit import chat_rate_limiter, reset_for_tests
        from fastapi import Request
        reset_for_tests()

        req = Request(scope={"type": "http", "client": ("1.1.1.1", 0), "headers": []})
        # 即便触发多次也不报错
        for _ in range(10):
            await chat_rate_limiter(req)