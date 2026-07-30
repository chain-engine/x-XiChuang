# -*- coding: utf-8 -*-
"""
会话 API 路由

提供会话和消息的 CRUD 接口。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import logger
from src.infras.mysql import get_async_db
from src.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    DeleteConversationResponse,
    MessageResponse,
    SaveMessagesRequest,
)
from src.services.conversation_service import ConversationService


router = APIRouter()


def get_conversation_service(
    session: Annotated[AsyncSession, Depends(get_async_db)]
) -> ConversationService:
    """获取会话服务实例"""
    return ConversationService(session)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    page: int = Query(default=1, ge=1, description="当前页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    keyword: str | None = Query(default=None, description="搜索关键词"),
    model_provider: str | None = Query(default=None, description="按模型提供商筛选"),
) -> ConversationListResponse:
    """
    获取所有会话列表

    按更新时间倒序返回。

    Args:
        service: 会话服务
        page: 页码
        page_size: 每页大小
        keyword: 搜索关键词
        model_provider: 模型提供商筛选

    Returns:
        ConversationListResponse: 会话列表响应
    """
    offset = (page - 1) * page_size

    conversations, total = await service.list_conversations(
        limit=page_size,
        offset=offset,
        keyword=keyword,
        model_provider=model_provider,
    )

    return ConversationListResponse(
        items=[
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                summary=conv.summary,
                model_provider=conv.model_provider,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv in conversations
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    """
    创建新会话

    Args:
        request: 创建会话请求
        service: 会话服务

    Returns:
        ConversationResponse: 创建的会话信息
    """
    result = await service.create_conversation(
        conversation_id=request.id,
        title=request.title,
        model_provider=request.model_provider,
    )

    return ConversationResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationDetailResponse:
    """
    获取会话详情（包含消息）

    Args:
        conversation_id: 会话 ID
        service: 会话服务

    Returns:
        ConversationDetailResponse: 会话详情响应
    """
    result = await service.get_conversation(conversation_id)

    return ConversationDetailResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        messages=[
            MessageResponse(
                id=msg.get("id"),
                role=msg["role"],
                content=msg["content"],
                created_at=msg.get("created_at"),
            )
            for msg in result.get("messages", [])
        ],
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    """
    更新会话信息

    Args:
        conversation_id: 会话 ID
        request: 更新会话请求
        service: 会话服务

    Returns:
        ConversationResponse: 更新后的会话信息
    """
    result = await service.update_conversation(
        conversation_id=conversation_id,
        title=request.title,
        summary=request.summary,
        model_provider=request.model_provider,
    )

    return ConversationResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
    )


@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> DeleteConversationResponse:
    """
    删除会话及其所有消息

    Args:
        conversation_id: 会话 ID
        service: 会话服务

    Returns:
        DeleteConversationResponse: 删除结果
    """
    await service.delete_conversation(conversation_id)
    logger.info(f"Deleted conversation: {conversation_id}")

    return DeleteConversationResponse(
        success=True,
        message="会话已删除",
        deleted_count=1,
    )


@router.post("/{conversation_id}/messages", response_model=ConversationDetailResponse)
async def save_messages(
    conversation_id: str,
    request: SaveMessagesRequest,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationDetailResponse:
    """
    保存会话消息

    如果会话不存在则自动创建。
    每次保存会清除旧消息并添加新消息。

    Args:
        conversation_id: 会话 ID
        request: 保存消息请求
        service: 会话服务

    Returns:
        ConversationDetailResponse: 更新后的会话详情
    """
    result = await service.save_messages(
        conversation_id=conversation_id,
        messages=[{"role": m.role, "content": m.content} for m in request.messages],
        clear_existing=request.clear_existing,
    )

    return ConversationDetailResponse(
        id=result["id"],
        title=result["title"],
        summary=result.get("summary"),
        model_provider=result["model_provider"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        messages=[
            MessageResponse(
                id=msg.get("id"),
                role=msg["role"],
                content=msg["content"],
                created_at=msg.get("created_at"),
            )
            for msg in result.get("messages", [])
        ],
    )
