# -*- coding: utf-8 -*-
"""会话实体模型。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infras.database import Base


class ConversationEntity(Base):
    """会话表实体。"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_provider: Mapped[str] = mapped_column(String(50), default="tongyi")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 关联消息
    messages: Mapped[List["MessageEntity"]] = relationship(
        "MessageEntity", back_populates="conversation", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "model_provider": self.model_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "messages": [m.to_dict() for m in self.messages],
        }
