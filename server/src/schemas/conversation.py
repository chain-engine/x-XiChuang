# -*- coding: utf-8 -*-
"""
会话 Schema 定义

包含会话和消息管理的请求和响应模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """创建消息请求"""

    role: str = Field(..., description="消息角色：user/assistant/system")
    content: str = Field(..., description="消息内容", min_length=1)
    metadata: dict[str, Any] | None = Field(None, description="消息元数据")


class MessageUpdate(BaseModel):
    """更新消息请求"""

    content: str | None = Field(None, description="消息内容")
    metadata: dict[str, Any] | None = Field(None, description="消息元数据")


class MessageResponse(BaseModel):
    """消息响应"""

    id: int | None = Field(None, description="消息ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    metadata: dict[str, Any] | None = Field(None, description="消息元数据")


class ConversationCreate(BaseModel):
    """创建会话请求"""

    id: str | None = Field(None, description="会话ID（可选，不提供则自动生成）")
    title: str = Field(default="新对话", description="会话标题")
    model_provider: str = Field(default="tongyi", description="模型提供商")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": None,
                "title": "新对话",
                "model_provider": "tongyi",
            }
        }
    }


class ConversationUpdate(BaseModel):
    """更新会话请求"""

    title: str | None = Field(None, description="会话标题")
    summary: str | None = Field(None, description="会话摘要")
    model_provider: str | None = Field(None, description="模型提供商")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class ConversationResponse(BaseModel):
    """会话响应（不含消息列表）"""

    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    summary: str | None = Field(None, description="会话摘要")
    model_provider: str = Field(..., description="模型提供商")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class ConversationDetailResponse(BaseModel):
    """会话详情响应（含消息列表）"""

    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    summary: str | None = Field(None, description="会话摘要")
    model_provider: str = Field(..., description="模型提供商")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")
    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="消息列表"
    )
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class ConversationListResponse(BaseModel):
    """会话列表响应"""

    items: list[ConversationResponse] = Field(
        default_factory=list,
        description="会话列表"
    )
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")


class ConversationQuery(BaseModel):
    """会话查询参数"""

    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    keyword: str | None = Field(None, description="搜索关键词")
    model_provider: str | None = Field(None, description="按模型提供商筛选")
    order_by: str = Field(default="updated_at", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")


class SaveMessagesRequest(BaseModel):
    """保存消息请求"""

    messages: list[MessageCreate] = Field(..., description="消息列表", min_length=1)
    clear_existing: bool = Field(
        default=False,
        description="是否清除现有消息（默认追加）"
    )


class DeleteConversationResponse(BaseModel):
    """删除会话响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    deleted_count: int = Field(default=0, description="删除的消息数量")
