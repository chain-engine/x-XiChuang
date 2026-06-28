# -*- coding: utf-8 -*-
"""
媒体数据模型

定义多模态输入的数据结构。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """媒体类型枚举"""

    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"  # 录音
    TEXT = "text"
    AUTO = "auto"


class MediaInput(BaseModel):
    """
    统一的媒体输入模型（用于多模态对话）

    支持两种传入方式（二选一或同时提供）：
    1. URL：通过可访问的 HTTP(S) 地址引用媒体资源
    2. 字节内容：通过上传文件获得的原始 bytes

    Attributes:
        type: 媒体类型提示
        url: 媒体资源的 HTTP(S) URL
        filename: 上传文件的原始文件名
        bytes_base64: 媒体原始字节内容
    """

    type: MediaType = Field(
        default=MediaType.AUTO,
        description="媒体类型：audio/image/video/voice/text/auto",
    )
    url: Optional[str] = Field(
        default=None,
        description="媒体资源的 HTTP(S) URL"
    )
    filename: Optional[str] = Field(
        default=None,
        description="上传文件的原始文件名"
    )
    bytes_base64: Optional[bytes] = Field(
        default=None,
        description="媒体原始字节内容"
    )
