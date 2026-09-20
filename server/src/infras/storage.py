"""
存储抽象层（Storage Abstraction Layer）

提供统一的文件存储接口，业务代码不关心底层存储实现。
支持的后端：
    - LocalStorage：本地文件系统（开发环境默认）
    - AliyunOSSStorage：阿里云 OSS 对象存储（生产环境推荐）

通过配置切换实现，业务代码零改动：

    ALIYUN_OSS_ACCESS_KEY_ID=xxx
    ALIYUN_OSS_ACCESS_KEY_SECRET=xxx
    ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
    ALIYUN_OSS_BUCKET_NAME=my-bucket

Usage:
    from src.infras.storage import get_storage_provider

    provider = get_storage_provider()       # 从配置自动创建
    result = provider.upload_file(file_bytes, "avatars/user.png", content_type="image/png")
    url = provider.get_download_url("avatars/user.png")
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from src.core.logger import logger


# ============================================================
# 统一返回结构
# ============================================================


class UploadResult:
    """上传结果，所有 provider 返回同一结构。"""

    __slots__ = ("key", "url", "size", "storage", "content_type")

    def __init__(
        self,
        key: str,
        url: str,
        size: int,
        storage: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.key = key
        self.url = url
        self.size = size
        self.storage = storage
        self.content_type = content_type

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "url": self.url,
            "size": self.size,
            "storage": self.storage,
            "content_type": self.content_type,
        }


# ============================================================
# 抽象基类
# ============================================================


class StorageProvider(ABC):
    """存储提供者抽象接口。

    所有存储后端必须实现此接口。业务层仅依赖此抽象，
    切换存储实现只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def upload_file(
        self,
        data: bytes | BinaryIO,
        key: str,
        *,
        content_type: str = "application/octet-stream",
    ) -> UploadResult:
        """上传文件。

        Args:
            data: 文件内容（bytes 或可读的文件对象）
            key: 存储路径键，如 "avatars/user.png"
            content_type: MIME 类型

        Returns:
            UploadResult: 上传结果（含 key、url、size、storage 类型）
        """

    @abstractmethod
    def get_download_url(self, key: str) -> str:
        """获取文件下载 URL。

        本地存储返回相对路径；云存储返回完整 URL。

        Args:
            key: 存储路径键

        Returns:
            str: 可访问的 URL 或相对路径
        """

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """删除文件。

        Args:
            key: 存储路径键

        Returns:
            bool: 删除是否成功
        """

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """判断文件是否存在。

        Args:
            key: 存储路径键

        Returns:
            bool: 文件是否存在
        """

    def make_object_key(self, folder: str, filename: str) -> str:
        """生成唯一的对象存储键。

        使用 时间戳+SHA1 保证唯一性，避免文件名冲突。

        Args:
            folder: 目录前缀，如 "avatars"
            filename: 原始文件名

        Returns:
            str: 唯一的存储键
        """
        safe_name = os.path.basename(filename)
        stem, ext = os.path.splitext(safe_name)
        digest = hashlib.sha1(
            f"{datetime.now(timezone.utc).isoformat()}:{safe_name}".encode("utf-8")
        ).hexdigest()[:12]
        unique_name = f"{stem}-{digest}{ext}"

        folder_clean = folder.strip("/")
        if folder_clean:
            return f"{folder_clean}/{unique_name}"
        return unique_name


# ============================================================
# 本地文件系统实现
# ============================================================


class LocalStorage(StorageProvider):
    """本地文件系统存储。

    文件保存在项目 static 目录下，适合开发和测试环境。
    通过 FastAPI 的 StaticFiles 中间件提供静态文件服务。
    """

    def __init__(
        self, base_dir: str = "server/statics", public_prefix: str = "/statics"
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.public_prefix = public_prefix.rstrip("/")
        logger.info(f"LocalStorage initialized: base_dir={self.base_dir}")

    def upload_file(
        self,
        data: bytes | BinaryIO,
        key: str,
        *,
        content_type: str = "application/octet-stream",
    ) -> UploadResult:
        target = (self.base_dir / key).resolve()

        # 安全检查：防止路径穿越
        try:
            target.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"非法的存储路径: {key}") from exc

        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            target.write_bytes(data)
            size = len(data)
        else:
            content = data.read()
            target.write_bytes(content)
            size = len(content)

        url = f"{self.public_prefix}/{key.lstrip('/')}"
        logger.info(f"LocalStorage upload: key={key} size={size}")
        return UploadResult(
            key=key, url=url, size=size, storage="local", content_type=content_type
        )

    def get_download_url(self, key: str) -> str:
        """返回本地相对路径（由 StaticFiles 中间件直接服务）。"""
        return f"{self.public_prefix}/{key.lstrip('/')}"

    def delete_file(self, key: str) -> bool:
        target = (self.base_dir / key).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            return False
        if target.is_file():
            target.unlink()
            logger.info(f"LocalStorage deleted: key={key}")
            return True
        return False

    def file_exists(self, key: str) -> bool:
        target = (self.base_dir / key).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            return False
        return target.is_file()


# ============================================================
# 阿里云 OSS 存储实现
# ============================================================


class AliyunOSSStorage(StorageProvider):
    """阿里云 OSS 对象存储。

    通过 oss2 调用阿里云 OSS API。
    需要安装 oss2：
        uv pip install oss2
    """

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket_name: str,
        prefix: str = "",
        public_url: str = "",
    ) -> None:
        try:
            import oss2
        except ImportError as exc:
            raise ImportError(
                "阿里云 OSS 存储需要 oss2，请执行: uv pip install oss2"
            ) from exc

        self._bucket_name = bucket_name
        self._prefix = prefix.strip("/")
        self._public_url = public_url.rstrip("/") if public_url else ""

        auth = oss2.Auth(access_key_id, access_key_secret)
        self._client = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
        logger.info(
            f"AliyunOSSStorage initialized: bucket={bucket_name} endpoint={endpoint}"
        )

    def _full_key(self, key: str) -> str:
        """拼接 prefix。"""
        key_clean = key.strip("/")
        if self._prefix:
            return f"{self._prefix}/{key_clean}"
        return key_clean

    def _get_public_url(self, key: str) -> str:
        """获取公开访问 URL。"""
        if self._public_url:
            return f"{self._public_url}/{key}"
        return f"https://{self._bucket_name}.{self._client.endpoint}/{key}"

    def upload_file(
        self,
        data: bytes | BinaryIO,
        key: str,
        *,
        content_type: str = "application/octet-stream",
    ) -> UploadResult:
        full_key = self._full_key(key)

        if not isinstance(data, bytes):
            data = data.read()

        self._client.put_object(full_key, data)
        url = self._get_public_url(full_key)
        logger.info(f"AliyunOSSStorage upload: key={full_key} size={len(data)}")
        return UploadResult(
            key=full_key,
            url=url,
            size=len(data),
            storage="oss",
            content_type=content_type,
        )

    def get_download_url(self, key: str) -> str:
        full_key = self._full_key(key)
        return self._get_public_url(full_key)

    def delete_file(self, key: str) -> bool:
        full_key = self._full_key(key)
        try:
            self._client.delete_object(full_key)
            logger.info(f"AliyunOSSStorage deleted: key={full_key}")
            return True
        except Exception as e:
            logger.warning(f"AliyunOSSStorage delete failed: key={full_key} error={e}")
            return False

    def file_exists(self, key: str) -> bool:
        full_key = self._full_key(key)
        try:
            return self._client.object_exists(full_key)
        except Exception:
            return False


# ============================================================
# 工厂函数
# ============================================================

# 模块级缓存，避免每次请求都重新创建
_provider: StorageProvider | None = None


def get_storage_provider() -> StorageProvider:
    """根据配置创建存储提供者实例。

    从 settings 读取阿里云 OSS 配置，有完整凭证则使用 OSS，
    否则回退到本地文件系统存储。

    Returns:
        StorageProvider: 存储提供者实例
    """
    from src.core.config import settings

    if settings.ALIYUN_OSS_ACCESS_KEY_ID and settings.ALIYUN_OSS_BUCKET_NAME:
        logger.info("Using Aliyun OSS storage backend")
        return AliyunOSSStorage(
            access_key_id=settings.ALIYUN_OSS_ACCESS_KEY_ID,
            access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
            endpoint=settings.ALIYUN_OSS_ENDPOINT,
            bucket_name=settings.ALIYUN_OSS_BUCKET_NAME,
        )

    logger.info("Using local storage backend (no OSS credentials configured)")
    return LocalStorage()


def get_cached_storage_provider() -> StorageProvider:
    """获取缓存的存储提供者（应用级别单例）。"""
    global _provider
    if _provider is None:
        _provider = get_storage_provider()
    return _provider


# ============================================================
# 向后兼容别名（旧名称 → 新名称）
# ============================================================
StorageBackend = StorageProvider
FileStorage = StorageProvider
get_storage = get_cached_storage_provider


__all__ = [
    # 核心类型
    "StorageProvider",
    "LocalStorage",
    "AliyunOSSStorage",
    "UploadResult",
    # 工厂函数
    "get_storage_provider",
    "get_cached_storage_provider",
    # 向后兼容
    "StorageBackend",
    "FileStorage",
    "get_storage",
]
