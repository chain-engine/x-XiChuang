# -*- coding: utf-8 -*-
"""
Milvus 数据库客户端

提供向量数据库的查询和管理功能，方便运维进行数据管理和分析。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pymilvus import Collection, connections, utility

from src.config.settings import settings
from src.core.logger import logger


class MilvusClient:
    """
    Milvus 数据库客户端封装

    提供数据查询、统计和管理功能。
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        alias: str = "default",
    ):
        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self.alias = alias
        self._connected = False

    def connect(self) -> bool:
        """连接到 Milvus 服务器"""
        if self._connected:
            return True

        try:
            connections.connect(
                alias=self.alias,
                host=self.host,
                port=self.port,
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self._connected:
            try:
                connections.disconnect(self.alias)
                self._connected = False
                logger.info("Disconnected from Milvus")
            except Exception as e:
                logger.error(f"Failed to disconnect from Milvus: {e}")

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        if not self.connect():
            return []
        try:
            return utility.list_collections(using=self.alias)
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合详细信息"""
        if not self.connect():
            return None

        try:
            if not utility.has_collection(collection_name, using=self.alias):
                return None

            collection = Collection(collection_name, using=self.alias)
            collection.load()

            return {
                "name": collection_name,
                "schema": {
                    "fields": [
                        {
                            "name": field.name,
                            "dtype": str(field.dtype),
                            "is_primary": field.is_primary,
                            "dim": getattr(field, "dim", None),
                        }
                        for field in collection.schema.fields
                    ],
                    "description": collection.schema.description,
                },
                "num_entities": collection.num_entities,
                "indexes": [
                    {
                        "field_name": idx.field_name,
                        "index_name": idx.index_name,
                        "params": idx.params,
                    }
                    for idx in collection.indexes
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    def query_data(
        self,
        collection_name: str,
        expr: str = "",
        output_fields: List[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询集合中的数据

        Args:
            collection_name: 集合名称
            expr: 过滤表达式
            output_fields: 输出字段列表
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            查询结果列表
        """
        if not self.connect():
            return []

        try:
            if not utility.has_collection(collection_name, using=self.alias):
                logger.warning(f"Collection {collection_name} does not exist")
                return []

            collection = Collection(collection_name, using=self.alias)
            collection.load()

            results = collection.query(
                expr=expr or None,
                output_fields=output_fields,
                limit=limit,
                offset=offset,
            )

            return results
        except Exception as e:
            logger.error(f"Failed to query data: {e}")
            return []

    def search_data(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        output_fields: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量搜索

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回数量
            output_fields: 输出字段

        Returns:
            搜索结果列表
        """
        if not self.connect():
            return []

        try:
            if not utility.has_collection(collection_name, using=self.alias):
                logger.warning(f"Collection {collection_name} does not exist")
                return []

            collection = Collection(collection_name, using=self.alias)
            collection.load()

            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=output_fields,
            )

            # 格式化结果
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.id,
                        "distance": hit.distance,
                        "entity": hit.entity._row_data if hasattr(hit, "entity") else {},
                    })

            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search data: {e}")
            return []

    def delete_data(
        self,
        collection_name: str,
        expr: str,
    ) -> int:
        """
        删除数据

        Args:
            collection_name: 集合名称
            expr: 删除条件表达式

        Returns:
            删除的数量
        """
        if not self.connect():
            return 0

        try:
            if not utility.has_collection(collection_name, using=self.alias):
                logger.warning(f"Collection {collection_name} does not exist")
                return 0

            collection = Collection(collection_name, using=self.alias)
            result = collection.delete(expr)
            logger.info(f"Deleted {result.delete_count} entities from {collection_name}")
            return result.delete_count
        except Exception as e:
            logger.error(f"Failed to delete data: {e}")
            return 0

    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用文本进行向量搜索（需要 embedding）

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            top_k: 返回数量
            output_fields: 输出字段

        Returns:
            搜索结果列表
        """
        import asyncio

        try:
            from langchain_community.embeddings import DashScopeEmbeddings
            from src.config.settings import settings as app_settings

            embeddings = DashScopeEmbeddings(
                model=app_settings.ALIYUN_EMBEDDING_MODEL_NAME,
                dashscope_api_key=app_settings.ALIYUN_API_KEY,
            )

            # 生成查询向量
            def _embed():
                return embeddings.embed_query(query_text)

            query_vector = await asyncio.to_thread(_embed)

            return self.search_data(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=top_k,
                output_fields=output_fields,
            )
        except Exception as e:
            logger.error(f"Failed to search by text: {e}")
            return []

    def drop_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        if not self.connect():
            return False

        try:
            if not utility.has_collection(collection_name, using=self.alias):
                logger.warning(f"Collection {collection_name} does not exist")
                return False

            utility.drop_collection(collection_name, using=self.alias)
            logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取 Milvus 服务器统计信息"""
        if not self.connect():
            return {"connected": False}

        try:
            collections = self.list_collections()
            stats = {
                "connected": True,
                "host": self.host,
                "port": self.port,
                "collections_count": len(collections),
                "collections": [],
            }

            for coll_name in collections:
                coll_info = self.get_collection_info(coll_name)
                if coll_info:
                    stats["collections"].append({
                        "name": coll_name,
                        "num_entities": coll_info["num_entities"],
                    })

            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"connected": False, "error": str(e)}


# 全局客户端实例
_milvus: Optional[MilvusClient] = None


def get_milvus_client() -> MilvusClient:
    """获取全局 Milvus 客户端实例"""
    global _milvus
    if _milvus is None:
        _milvus = MilvusClient()
    return _milvus
