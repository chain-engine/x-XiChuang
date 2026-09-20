# -*- coding: utf-8 -*-
"""
数据仓储层

封装数据库 CRUD 操作，实现数据访问逻辑与业务逻辑的分离。
"""

from .base import IRepository, BaseRepository
from .conversation import ConversationRepository, MessageRepository

__all__ = [
    "IRepository",
    "BaseRepository",
    "ConversationRepository",
    "MessageRepository",
]
