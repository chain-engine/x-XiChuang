# -*- coding: utf-8 -*-
"""
文件存储服务单元测试
"""

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.infra.storage import AliyunOSSStorage, FileStorage, LocalStorage


class TestLocalStorage:
    """LocalStorage 测试"""

    def test_init_creates_directories(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir / "statics"))
        for category in ["images", "audio", "videos", "files"]:
            assert (tmp_dir / "statics" / category).exists()

    def test_generate_filename(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir / "statics"))
        filename = storage._generate_filename("photo.jpg", "images")
        assert filename.startswith("images_")
        assert filename.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_save_and_exists(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir / "statics"))
        data = io.BytesIO(b"hello world")
        path = await storage.save(data, "test.txt", "files")
        assert await storage.exists(path)
        # 文件内容检查
        with open(path, "rb") as f:
            assert f.read() == b"hello world"

    @pytest.mark.asyncio
    async def test_delete_existing_file(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir / "statics"))
        data = io.BytesIO(b"data")
        path = await storage.save(data, "del.txt", "files")
        assert await storage.delete(path) is True
        assert not await storage.exists(path)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir / "statics"))
        assert await storage.delete(str(tmp_dir / "nope.txt")) is False

    def test_get_url(self, tmp_dir):
        storage = LocalStorage(base_dir="server/statics")
        url = storage.get_url("server/statics/files/test.txt")
        assert url == "/statics/files/test.txt"

    def test_recording_category_maps_to_videos(self, tmp_dir):
        storage = LocalStorage(base_dir=str(tmp_dir))
        assert storage._get_category_dir("recording") == tmp_dir / "videos"


class TestAliyunOSSStorage:
    """AliyunOSSStorage 测试"""

    def test_get_url(self):
        storage = AliyunOSSStorage(
            access_key_id="key",
            access_key_secret="secret",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            bucket_name="my-bucket",
        )
        url = storage.get_url("images/photo.jpg")
        assert url == "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/images/photo.jpg"

    def test_get_client_raises_without_oss2(self):
        storage = AliyunOSSStorage(
            access_key_id="key",
            access_key_secret="secret",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            bucket_name="my-bucket",
        )
        with patch.dict("sys.modules", {"oss2": None}):
            with pytest.raises(RuntimeError, match="oss2"):
                storage._get_client()


class TestFileStorage:
    """FileStorage 门面类测试"""

    def test_media_type_mapping(self):
        storage = FileStorage(backend=LocalStorage(base_dir="/tmp/test-storage"))
        assert storage._map_media_type_to_category("text") == "files"
        assert storage._map_media_type_to_category("voice") == "audio"
        assert storage._map_media_type_to_category("audio") == "audio"
        assert storage._map_media_type_to_category("image") == "images"
        assert storage._map_media_type_to_category("video") == "videos"
        assert storage._map_media_type_to_category("recording") == "recording"
        assert storage._map_media_type_to_category("unknown") == "files"
