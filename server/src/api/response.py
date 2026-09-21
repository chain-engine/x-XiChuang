# -*- coding: utf-8 -*-
"""
统一响应封装模块

提供全局统一的 JSONResponse 构造函数，所有 API 路由必须使用本模块
提供的 ``success_response`` / ``error_response`` / ``paginated_response``
构造响应，禁止直接返回 dict 或自定义 Pydantic model。

响应体结构（BaseResp）::

    {
        "code": 200,
        "message": "success",
        "data": { ... },
        "timestamp": "2026-09-21T12:00:00+00:00",
        "request_id": "a1b2c3d4"
    }

分页响应会在 data 中额外包含分页元信息::

    {
        "code": 200,
        "message": "success",
        "data": {
            "items": [...],
            "total": 100,
            "page": 1,
            "page_size": 20,
            "total_pages": 5
        },
        "timestamp": "...",
        "request_id": "..."
    }

Functions:
    success_response:     构造统一成功响应
    error_response:       构造统一错误响应
    paginated_response:   构造统一分页响应
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.constants import MSG_INTERNAL_ERROR, MSG_SUCCESS


# ============ 内部工具 ============


def _build_payload(
    *,
    code: int,
    message: str,
    data: Any = None,
    request: Request | None = None,
) -> dict[str, Any]:
    """
    构造统一响应体（BaseResp）。

    Args:
        code: 业务状态码（与 HTTP status code 保持一致）
        message: 响应描述
        data: 业务数据
        request: 当前请求对象（用于提取 request_id）

    Returns:
        统一格式的响应字典
    """
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if request is not None:
        payload["request_id"] = getattr(request.state, "request_id", None)
    return payload


# ============ 公共响应构造函数 ============


def success_response(
    data: Any,
    request: Request,
    *,
    code: int = 200,
    message: str = MSG_SUCCESS,
) -> JSONResponse:
    """
    构造统一成功响应。

    所有正常业务返回都**必须**使用本函数包装，禁止直接返回 dict。

    Args:
        data: 业务数据（dict / list / Pydantic model_dump 均可）
        request: 当前请求对象
        code: HTTP 状态码，默认 200
        message: 响应描述，默认 "success"

    Returns:
        JSONResponse: 统一格式的成功响应
    """
    payload = _build_payload(
        code=code,
        message=message,
        data=data,
        request=request,
    )
    return JSONResponse(status_code=code, content=payload)


def error_response(
    request: Request,
    *,
    code: int = 500,
    message: str = MSG_INTERNAL_ERROR,
    data: Any = None,
) -> JSONResponse:
    """
    构造统一错误响应。

    由全局异常处理器（core/exceptions.py）调用，路由层一般不直接使用。

    Args:
        request: 当前请求对象
        code: HTTP 状态码
        message: 错误描述
        data: 附加错误详情（校验错误列表等），默认 None

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    payload = _build_payload(
        code=code,
        message=message,
        data=data,
        request=request,
    )
    return JSONResponse(status_code=code, content=payload)


def paginated_response(
    items: list[Any],
    total: int,
    request: Request,
    *,
    page: int = 1,
    page_size: int = 20,
    code: int = 200,
    message: str = MSG_SUCCESS,
) -> JSONResponse:
    """
    构造统一分页响应。

    分页元信息（total / page / page_size / total_pages）与 items 并列在 data 中。

    Args:
        items: 当前页数据列表
        total: 总记录数
        request: 当前请求对象
        page: 当前页码
        page_size: 每页大小
        code: HTTP 状态码
        message: 响应描述

    Returns:
        JSONResponse: 统一格式的分页响应
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    data = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
    return success_response(data=data, request=request, code=code, message=message)
