# -*- coding: utf-8 -*-
"""
文件存储服务

支持本地存储和阿里云OSS存储，可通过配置切换。
"""

from __future__ import annotations

import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from src.config.settings import settings
from src.core.logger import logger


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    async def save(self, file_data: BinaryIO, filename: str, category: str) -> str:
        """
        保存文件并返回文件路径或URL

        Args:
            file_data: 文件数据流
            filename: 原始文件名
            category: 文件类别 (images/audio/videos/files)

        Returns:
            文件路径或URL
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """删除文件"""
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        pass


class LocalStorage(StorageBackend):
    """本地文件存储"""

    def __init__(self, base_dir: str = "server/statics"):
        self.base_dir = Path(base_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        for category in ["images", "audio", "videos", "files"]:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_filename: str, category: str) -> str:
        """生成唯一文件名"""
        ext = Path(original_filename).suffix or ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{category}_{timestamp}_{unique_id}{ext}"

    def _get_category_dir(self, category: str) -> Path:
        """获取类别目录"""
        if category == "recording":
            return self.base_dir / "videos"
        return self.base_dir / category

    async def save(self, file_data: BinaryIO, filename: str, category: str) -> str:
        """保存文件到本地"""
        category_dir = self._get_category_dir(category)
        new_filename = self._generate_filename(filename, category)
        file_path = category_dir / new_filename

        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file_data, f)
            logger.info(f"File saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise

    async def delete(self, file_path: str) -> bool:
        """删除本地文件"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return Path(file_path).exists()

    def get_url(self, file_path: str) -> str:
        """获取文件访问URL（本地存储返回相对路径）"""
        return f"/statics/{file_path.replace('server/statics/', '')}"


class AliyunOSSStorage(StorageBackend):
    """阿里云OSS存储（预留实现）"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket_name: str,
    ):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self._client = None

    def _get_client(self):
        """获取OSS客户端（懒加载）"""
        if self._client is None:
            try:
                import oss2

                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self._client = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            except ImportError:
                raise RuntimeError(
                    "请安装oss2库: pip install oss2"
                )
        return self._client

    async def save(self, file_data: BinaryIO, filename: str, category: str) -> str:
        """保存文件到OSS"""
        client = self._get_client()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        ext = Path(filename).suffix or ""
        object_key = f"{category}/{category}_{timestamp}_{unique_id}{ext}"

        try:
            client.put_object(object_key, file_data.read())
            logger.info(f"File uploaded to OSS: {object_key}")
            return object_key
        except Exception as e:
            logger.error(f"Failed to upload to OSS: {e}")
            raise

    async def delete(self, file_path: str) -> bool:
        """删除OSS文件"""
        try:
            client = self._get_client()
            client.delete_object(file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from OSS: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """检查OSS文件是否存在"""
        try:
            client = self._get_client()
            return client.object_exists(file_path)
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        """获取OSS文件访问URL"""
        return f"https://{self.bucket_name}.{self.endpoint}/{file_path}"


class FileStorage:
    """
    文件存储服务门面

    根据配置自动选择存储后端（本地/OSS）
    """

    def __init__(self, backend: Optional[StorageBackend] = None):
        self._backend = backend or self._create_backend()

    def _create_backend(self) -> StorageBackend:
        """根据配置创建存储后端"""
        if settings.ALIYUN_OSS_ACCESS_KEY_ID and settings.ALIYUN_OSS_BUCKET_NAME:
            logger.info("Using Aliyun OSS storage backend")
            return AliyunOSSStorage(
                access_key_id=settings.ALIYUN_OSS_ACCESS_KEY_ID,
                access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
                endpoint=settings.ALIYUN_OSS_ENDPOINT,
                bucket_name=settings.ALIYUN_OSS_BUCKET_NAME,
            )

        logger.info("Using local storage backend")
        return LocalStorage()

    async def save_file(
        self,
        file_data: BinaryIO,
        filename: str,
        media_type: str = "file",
    ) -> Tuple[str, str]:
        """
        保存文件

        Args:
            file_data: 文件数据流
            filename: 原始文件名
            media_type: 媒体类型 (text/voice/image/video/file)

        Returns:
            (文件路径, 访问URL)
        """
        category = self._map_media_type_to_category(media_type)
        file_path = await self._backend.save(file_data, filename, category)
        url = self._backend.get_url(file_path)
        return file_path, url

    def _map_media_type_to_category(self, media_type: str) -> str:
        """映射媒体类型到存储目录"""
        mapping = {
            "text": "files",
            "voice": "audio",
            "audio": "audio",
            "image": "images",
            "video": "videos",
            "file": "files",
            "recording": "recording",
        }
        return mapping.get(media_type.lower(), "files")

    async def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        return await self._backend.delete(file_path)

    async def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return await self._backend.exists(file_path)

    def get_file_url(self, file_path: str) -> str:
        """获取文件URL"""
        return self._backend.get_url(file_path)


# 全局存储实例
_storage_instance: Optional[FileStorage] = None


def get_storage() -> FileStorage:
    """获取全局存储实例"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = FileStorage()
    return _storage_instance
