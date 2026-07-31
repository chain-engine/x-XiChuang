# -*- coding: utf-8 -*-
"""
基于进程内内存的限流

策略：固定窗口 + 计数器。每个路由可配置 (limit, window_seconds)。
- 不需要 Redis 等外部依赖
- 进程重启后计数器清空（适合中小规模；生产推荐替换为 Redis）

环境变量：
- CHAT_RATE_LIMIT（默认 60，每分钟每 IP 允许请求次数）
- CHAT_RATE_WINDOW（默认 60 秒）
- RATE_LIMIT_ENABLED（默认 true；设为 "false" 可关闭）
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Tuple

from fastapi import Depends, HTTPException, Request, status


_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "60"))
_WINDOW = int(os.getenv("CHAT_RATE_WINDOW", "60"))
_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in {"false", "0", "no"}


class _FixedWindowCounter:
    """按 IP + 路由 key 维护滑动窗口（精确到请求时间戳 deque）"""

    def __init__(self) -> None:
        self._buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check_and_record(self, key: Tuple[str, str], limit: int, window: int) -> bool:
        """检查是否超限，未超限则记录一次，返回 True 表示放行"""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            # 丢弃窗口外的旧时间戳
            cutoff = now - window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


_counter = _FixedWindowCounter()


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP（支持反代）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def chat_rate_limiter(request: Request) -> None:
    """chat 接口的限流依赖。配置 / 环境变量生效。"""
    if not _ENABLED:
        return

    ip = _get_client_ip(request)
    key = (ip, "chat")
    ok = _counter.check_and_record(key, _LIMIT, _WINDOW)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {_LIMIT} requests per {_WINDOW}s per IP",
            headers={"Retry-After": str(_WINDOW)},
        )


def reset_for_tests() -> None:
    """供测试重置内部状态"""
    global _counter
    _counter = _FixedWindowCounter()