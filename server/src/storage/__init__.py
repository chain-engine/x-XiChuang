# -*- coding: utf-8 -*-
"""
文件存储模块

支持本地存储和阿里云OSS存储，可通过配置切换。
"""

from .service import FileStorage, get_storage

__all__ = [
    "FileStorage",
    "get_storage",
]
