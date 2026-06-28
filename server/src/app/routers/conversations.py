# -*- coding: utf-8 -*-
"""
会话 API 路由

提供会话和消息的 CRUD 接口。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.mysql import get_async_db, Conversation, Message
from src.core.logger import logger

router = APIRouter()


# ============ Pydantic Models ============

class MessageCreate(BaseModel):
    """创建消息请求"""
    role: str = Field(..., description="消息角色：user/assistant")
    content: str = Field(..., description="消息内容")


class MessageResponse(BaseModel):
    """消息响应"""
    role: str
    content: str
    created_at: Optional[str] = None


class ConversationCreate(BaseModel):
    """创建会话请求"""
    id: Optional[str] = Field(None, description="会话ID（可选，不提供则自动生成）")
    title: str = Field(default="新对话", description="会话标题")
    model_provider: str = Field(default="tongyi", description="模型提供商")


class ConversationUpdate(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, description="会话标题")
    summary: Optional[str] = Field(None, description="会话摘要")
    model_provider: Optional[str] = Field(None, description="模型提供商")


class ConversationResponse(BaseModel):
    """会话响应（不含消息）"""
    id: str
    title: str
    summary: Optional[str] = None
    model_provider: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationDetailResponse(BaseModel):
    """会话详情响应（含消息）"""
    id: str
    title: str
    summary: Optional[str] = None
    model_provider: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[MessageResponse] = []


class SaveMessagesRequest(BaseModel):
    """保存消息请求"""
    messages: List[MessageCreate] = Field(..., description="消息列表")


# ============ API Endpoints ============

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_async_db)
) -> List[ConversationResponse]:
    """
    获取所有会话列表

    按更新时间倒序返回。
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation)
        .order_by(desc(Conversation.updated_at))
    )
    conversations = result.scalars().all()

    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            summary=conv.summary,
            model_provider=conv.model_provider,
            created_at=conv.created_at.isoformat() if conv.created_at else None,
            updated_at=conv.updated_at.isoformat() if conv.updated_at else None,
        )
        for conv in conversations
    ]


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_async_db)
) -> ConversationResponse:
    """
    创建新会话
    """
    import uuid

    conv_id = request.id or str(uuid.uuid4())

    # 检查是否已存在
    from sqlalchemy import select
    existing = await db.execute(
        select(Conversation).where(Conversation.id == conv_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="会话已存在")

    conversation = Conversation(
        id=conv_id,
        title=request.title,
        model_provider=request.model_provider,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    logger.info(f"Created conversation: {conv_id}")

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        model_provider=conversation.model_provider,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> ConversationDetailResponse:
    """
    获取会话详情（包含消息）
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        model_provider=conversation.model_provider,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
        messages=[
            MessageResponse(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat() if msg.created_at else None,
            )
            for msg in conversation.messages
        ],
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> ConversationResponse:
    """
    更新会话信息
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    if request.title is not None:
        conversation.title = request.title
    if request.summary is not None:
        conversation.summary = request.summary
    if request.model_provider is not None:
        conversation.model_provider = request.model_provider

    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        model_provider=conversation.model_provider,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """
    删除会话及其所有消息
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.delete(conversation)
    await db.commit()

    logger.info(f"Deleted conversation: {conversation_id}")

    return {"success": True, "message": "会话已删除"}


@router.post("/{conversation_id}/messages", response_model=ConversationDetailResponse)
async def save_messages(
    conversation_id: str,
    request: SaveMessagesRequest,
    db: AsyncSession = Depends(get_async_db)
) -> ConversationDetailResponse:
    """
    保存会话消息

    如果会话不存在则自动创建。
    每次保存会清除旧消息并添加新消息。
    """
    from sqlalchemy import select
    import uuid

    # 查找或创建会话
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        # 自动创建会话
        conversation = Conversation(
            id=conversation_id,
            title="新对话",
        )
        db.add(conversation)
        await db.flush()
    else:
        # 清除旧消息
        for msg in conversation.messages:
            await db.delete(msg)

    # 添加新消息
    for msg_data in request.messages:
        message = Message(
            conversation_id=conversation_id,
            role=msg_data.role,
            content=msg_data.content,
        )
        db.add(message)

    # 根据第一条用户消息更新标题
    if conversation.title == "新对话":
        first_user_msg = next(
            (m for m in request.messages if m.role == "user"), None
        )
        if first_user_msg:
            conversation.title = first_user_msg.content[:20] + (
                "..." if len(first_user_msg.content) > 20 else ""
            )

    await db.commit()
    await db.refresh(conversation)

    # 重新加载消息
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one()

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        model_provider=conversation.model_provider,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
        messages=[
            MessageResponse(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat() if msg.created_at else None,
            )
            for msg in conversation.messages
        ],
    )
