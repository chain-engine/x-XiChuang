# -*- coding: utf-8 -*-
"""
媒体数据模型单元测试
"""

from src.agent.media import MediaInput, MediaType


class TestMediaType:
    """MediaType 枚举测试"""

    def test_all_types(self):
        assert MediaType.AUDIO.value == "audio"
        assert MediaType.IMAGE.value == "image"
        assert MediaType.VIDEO.value == "video"
        assert MediaType.VOICE.value == "voice"
        assert MediaType.TEXT.value == "text"
        assert MediaType.AUTO.value == "auto"


class TestMediaInput:
    """MediaInput 模型测试"""

    def test_default_values(self):
        m = MediaInput()
        assert m.type == MediaType.AUTO
        assert m.url is None
        assert m.filename is None
        assert m.bytes_base64 is None

    def test_with_url(self):
        m = MediaInput(type=MediaType.IMAGE, url="https://example.com/img.png")
        assert m.type == MediaType.IMAGE
        assert m.url == "https://example.com/img.png"

    def test_with_bytes(self):
        data = b"fake image data"
        m = MediaInput(type=MediaType.VIDEO, bytes_base64=data, filename="video.mp4")
        assert m.bytes_base64 == data
        assert m.filename == "video.mp4"

    def test_from_dict(self):
        d = {"type": "audio", "url": "https://example.com/a.mp3"}
        m = MediaInput(**d)
        assert m.type == MediaType.AUDIO

    def test_invalid_type_string(self):
        """无效的 type 字符串应该触发验证错误"""
        import pytest
        with pytest.raises(Exception):
            MediaInput(type="invalid_type")
