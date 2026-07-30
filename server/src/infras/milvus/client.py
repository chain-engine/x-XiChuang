# -*- coding: utf-8 -*-
"""
Milvus 客户端封装

提供 Milvus 向量数据库的连接和操作接口。
"""

from __future__ import annotations

import time
from typing import Any

from src.core.config import settings
from src.core.logger import logger


class MilvusClient:
    """
    Milvus 向量数据库客户端

    封装 Milvus 的常用操作，支持向量检索、集合管理等。
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str = "",
        password: str = "",
    ) -> None:
        """
        初始化 Milvus 客户端

        Args:
            host: Milvus 主机地址
            port: Milvus 端口
            user: 用户名
            password: 密码
        """
        self._host = host or settings.MILVUS_HOST
        self._port = port or settings.MILVUS_PORT
        self._user = user or settings.MILVUS_USER
        self._password = password or settings.MILVUS_PASSWORD
        self._client = None
        self._connected = False

    def _get_client(self) -> Any:
        """
        获取 Milvus 客户端实例（懒加载）

        Returns:
            Milvus 客户端
        """
        if self._client is None:
            try:
                from pymilvus import MilvusClient as PyMilvusClient

                # 构建连接 URI
                uri = f"http://{self._host}:{self._port}"

                # 初始化客户端
                if self._user and self._password:
                    self._client = PyMilvusClient(uri=uri, token=f"{self._user}:{self._password}")
                else:
                    self._client = PyMilvusClient(uri=uri)

                self._connected = True
                logger.info(f"Milvus client connected to {self._host}:{self._port}")

            except ImportError:
                logger.error("pymilvus is not installed. Run: pip install pymilvus")
                raise RuntimeError("pymilvus is not installed")
            except Exception as e:
                logger.error(f"Failed to connect to Milvus: {e}")
                self._connected = False
                raise

        return self._client

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def get_stats(self) -> dict[str, Any]:
        """
        获取 Milvus 服务器统计信息

        Returns:
            统计信息字典
        """
        try:
            client = self._get_client()
            collections = client.list_collections() or []

            collection_info = []
            for name in collections:
                try:
                    info = client.get_collection_stats(name)
                    collection_info.append({
                        "name": name,
                        "num_entities": info.get("row_count", 0),
                    })
                except Exception:
                    collection_info.append({"name": name, "num_entities": 0})

            return {
                "connected": True,
                "host": self._host,
                "port": self._port,
                "collections_count": len(collections),
                "collections": collection_info,
            }
        except Exception as e:
            logger.error(f"Failed to get Milvus stats: {e}")
            return {
                "connected": False,
                "error": str(e),
            }

    def list_collections(self) -> list[str]:
        """
        列出所有集合

        Returns:
            集合名称列表
        """
        try:
            client = self._get_client()
            return client.list_collections() or []
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
        """
        获取集合详细信息

        Args:
            collection_name: 集合名称

        Returns:
            集合信息字典
        """
        try:
            client = self._get_client()
            if collection_name not in client.list_collections():
                return None

            stats = client.get_collection_stats(collection_name)
            schema = client.describe_collection(collection_name)

            return {
                "name": collection_name,
                "description": schema.get("description", ""),
                "num_entities": stats.get("row_count", 0),
                "dimension": schema.get("dimension", 0),
                "index_type": schema.get("index_type", ""),
                "metric_type": schema.get("metric_type", ""),
                "fields": schema.get("fields", []),
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: list[str] | None = None,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        使用文本进行向量搜索

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            top_k: 返回数量
            output_fields: 输出字段列表
            filter_expr: 过滤表达式

        Returns:
            搜索结果列表
        """
        try:
            client = self._get_client()

            # 生成文本向量
            query_vector = self._generate_embedding(query_text)

            # 执行搜索
            search_params = {"metric_type": "COSINE", "params": {}}

            results = client.search(
                collection_name=collection_name,
                data=[query_vector],
                limit=top_k,
                output_fields=output_fields or ["text", "source"],
                filter=filter_expr,
                search_params=search_params,
            )

            # 格式化结果
            formatted_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    formatted_results.append({
                        "id": hit.get("id"),
                        "distance": hit.get("distance"),
                        "entity": hit.get("entity", {}),
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search by text: {e}")
            raise

    def _generate_embedding(self, text: str) -> list[float]:
        """
        生成文本向量嵌入

        Args:
            text: 文本内容

        Returns:
            向量列表
        """
        try:
            import dashscope
            from dashscope import TextEmbedding

            dashscope.api_key = settings.ALIYUN_API_KEY

            response = TextEmbedding.call(
                model=settings.ALIYUN_EMBEDDING_MODEL_NAME,
                input=text,
            )

            if response.status_code == 200:
                return response.output["embeddings"][0]["embedding"]
            else:
                raise RuntimeError(f"Embedding API error: {response.message}")

        except ImportError:
            logger.error("dashscope is not installed. Run: pip install dashscope")
            raise RuntimeError("dashscope is not installed")
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def delete_data(self, collection_name: str, expr: str) -> int:
        """
        删除数据

        Args:
            collection_name: 集合名称
            expr: 删除条件表达式

        Returns:
            删除数量
        """
        try:
            client = self._get_client()
            result = client.delete(collection_name=collection_name, filter=expr)
            return result.get("delete_count", 0)
        except Exception as e:
            logger.error(f"Failed to delete data: {e}")
            raise

    def drop_collection(self, collection_name: str) -> bool:
        """
        删除集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        try:
            client = self._get_client()
            client.drop_collection(collection_name=collection_name)
            logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            raise

    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        description: str = "",
        index_type: str = "AUTOINDEX",
        metric_type: str = "COSINE",
    ) -> bool:
        """
        创建集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度
            description: 集合描述
            index_type: 索引类型
            metric_type: 度量类型

        Returns:
            是否成功
        """
        try:
            client = self._get_client()

            # 检查是否已存在
            if collection_name in client.list_collections():
                logger.warning(f"Collection {collection_name} already exists")
                return False

            # 创建集合
            client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                description=description,
                index_params={
                    "index_type": index_type,
                    "metric_type": metric_type,
                },
            )

            logger.info(f"Created collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def insert(
        self,
        collection_name: str,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        """
        插入数据

        Args:
            collection_name: 集合名称
            texts: 文本列表
            metadata: 元数据列表

        Returns:
            插入的 ID 列表
        """
        try:
            client = self._get_client()

            # 生成向量
            embeddings = [self._generate_embedding(text) for text in texts]

            # 准备数据
            data = [{"text": text, "embedding": emb} for text, emb in zip(texts, embeddings)]

            # 添加元数据
            if metadata:
                for i, meta in enumerate(metadata):
                    data[i].update(meta)

            # 插入数据
            result = client.insert(collection_name=collection_name, data=data)

            return result.get("ids", [])

        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise


# 全局 Milvus 客户端实例
_milvus_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """
    获取全局 Milvus 客户端实例

    Returns:
        MilvusClient 实例
    """
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient()
    return _milvus_client
