# -*- coding: utf-8 -*-
"""
Milvus 数据管理服务

提供 Milvus 向量数据库的业务逻辑封装。
"""

from __future__ import annotations

from typing import Any, Optional

from src.core.logger import logger
from src.milvus import MilvusClient, get_milvus_client


class MilvusService:
    """
    Milvus 数据管理服务

    封装 Milvus 向量数据库的业务操作。
    """

    def __init__(self, client: Optional[MilvusClient] = None) -> None:
        """
        初始化 Milvus 服务

        Args:
            client: Milvus 客户端实例（可选，默认使用全局实例）
        """
        self._client = client

    @property
    def client(self) -> MilvusClient:
        """获取 Milvus 客户端（懒加载）"""
        if self._client is None:
            self._client = get_milvus_client()
        return self._client

    async def get_stats(self) -> dict[str, Any]:
        """
        获取 Milvus 服务器统计信息

        Returns:
            统计信息字典
        """
        try:
            return self.client.get_stats()
        except Exception as e:
            logger.error(f"Failed to get Milvus stats: {e}")
            return {"connected": False, "error": str(e)}

    async def list_collections(self) -> list[str]:
        """
        列出所有集合

        Returns:
            集合名称列表
        """
        try:
            return self.client.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def get_collection_info(self, collection_name: str) -> Optional[dict[str, Any]]:
        """
        获取集合详细信息

        Args:
            collection_name: 集合名称

        Returns:
            集合信息字典
        """
        try:
            return self.client.get_collection_info(collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        使用文本进行向量搜索

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            top_k: 返回数量
            output_fields: 输出字段

        Returns:
            搜索结果列表
        """
        try:
            return await self.client.search_by_text(
                collection_name=collection_name,
                query_text=query_text,
                top_k=top_k,
                output_fields=output_fields,
            )
        except Exception as e:
            logger.error(f"Failed to search by text: {e}")
            raise

    async def delete_data(self, collection_name: str, expr: str) -> int:
        """
        删除数据

        Args:
            collection_name: 集合名称
            expr: 删除条件表达式

        Returns:
            删除的数量
        """
        try:
            return self.client.delete_data(collection_name, expr)
        except Exception as e:
            logger.error(f"Failed to delete data: {e}")
            raise

    async def drop_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        try:
            return self.client.drop_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            raise

    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        description: str = "",
    ) -> bool:
        """
        创建集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度
            description: 集合描述

        Returns:
            是否成功
        """
        try:
            return self.client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                description=description,
            )
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    async def insert_texts(
        self,
        collection_name: str,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        """
        插入文本数据

        Args:
            collection_name: 集合名称
            texts: 文本列表
            metadata: 元数据列表

        Returns:
            插入的 ID 列表
        """
        try:
            return self.client.insert(
                collection_name=collection_name,
                texts=texts,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to insert texts: {e}")
            raise


# 全局服务实例
_milvus_service: Optional[MilvusService] = None


def get_milvus_service() -> MilvusService:
    """
    获取全局 Milvus 服务实例

    Returns:
        MilvusService 实例
    """
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service
