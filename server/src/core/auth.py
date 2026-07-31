# -*- coding: utf-8 -*-
"""
简单 API Key 鉴权依赖

生产级部署建议用 JWT 或 OAuth；这里给出最小可用实现：
- 通过环境变量 API_KEY 配置静态密钥（多个用英文逗号分隔）
- 客户端在请求头 X-API-Key 中传递
- 未配置 API_KEY 时跳过校验（开发模式）
"""

from __future__ import annotations

import os
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status


_API_KEYS: Optional[List[str]] = None


def _load_api_keys() -> List[str]:
    """从环境变量加载允许的 API Key 列表（仅解析一次）"""
    global _API_KEYS
    if _API_KEYS is None:
        raw = os.getenv("API_KEY", "").strip()
        if raw:
            _API_KEYS = [k.strip() for k in raw.split(",") if k.strip()]
        else:
            _API_KEYS = []
    return _API_KEYS


def reset_api_keys() -> None:
    """供测试使用的重置函数"""
    global _API_KEYS
    _API_KEYS = None


async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    API Key 鉴权依赖

    用法：
        @router.post("/message", dependencies=[Depends(verify_api_key)])

    行为：
    - API_KEY 未配置 → 直接通过（开发模式）
    - 已配置 → 必须匹配 X-API-Key，否则 401
    """
    keys = _load_api_keys()
    if not keys:
        # 未配置密钥，开发模式跳过鉴权
        return

    if not x_api_key or x_api_key not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )