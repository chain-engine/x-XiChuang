# -*- coding: utf-8 -*-
"""
向量存储基础设施

提供向量数据库的抽象接口与具体实现，遵循 ABC 解耦规范。

统一风格：
    - VectorStoreProvider(ABC)       — 抽象接口
    - MilvusVectorStoreProvider      — Milvus 具体实现
    - get_vector_store_provider()    — 工厂函数（读配置创建实例）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.logger import logger


# ============================================================================
# 抽象接口
# ============================================================================


class VectorStoreProvider(ABC):
    """向量数据库抽象接口"""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """获取服务器统计信息"""
        ...

    @abstractmethod
    def list_collections(self) -> list[str]:
        """列出所有集合"""
        ...

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
        """获取集合详细信息"""
        ...

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        description: str = "",
        index_type: str = "AUTOINDEX",
        metric_type: str = "COSINE",
    ) -> bool:
        """创建集合"""
        ...

    @abstractmethod
    def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        ...

    @abstractmethod
    def insert(
        self,
        collection_name: str,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        """插入数据"""
        ...

    @abstractmethod
    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: list[str] | None = None,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """使用文本进行向量搜索"""
        ...

    @abstractmethod
    def delete_data(self, collection_name: str, expr: str) -> int:
        """按条件删除数据"""
        ...


# ============================================================================
# Milvus 具体实现
# ============================================================================


class MilvusVectorStoreProvider(VectorStoreProvider):
    """
    Milvus 向量数据库实现

    封装 pymilvus 客户端，支持向量检索、集合管理等。
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str = "",
        password: str = "",
    ) -> None:
        from src.core.config import settings

        self._host = host or settings.MILVUS_HOST
        self._port = port or settings.MILVUS_PORT
        self._user = user or settings.MILVUS_USER
        self._password = password or settings.MILVUS_PASSWORD
        self._client: Any = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """获取 pymilvus 客户端实例（懒加载）"""
        if self._client is None:
            try:
                from pymilvus import MilvusClient as PyMilvusClient

                uri = f"http://{self._host}:{self._port}"
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

    def _generate_embedding(self, text: str) -> list[float]:
        """生成文本向量嵌入"""
        try:
            from src.core.config import settings
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

    # ------------------------------------------------------------------
    # VectorStoreProvider 接口实现
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_stats(self) -> dict[str, Any]:
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
            return {"connected": False, "error": str(e)}

    def list_collections(self) -> list[str]:
        try:
            client = self._get_client()
            return client.list_collections() or []
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
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

    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        description: str = "",
        index_type: str = "AUTOINDEX",
        metric_type: str = "COSINE",
    ) -> bool:
        try:
            client = self._get_client()

            if collection_name in client.list_collections():
                logger.warning(f"Collection {collection_name} already exists")
                return False

            client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                description=description,
                index_params={"index_type": index_type, "metric_type": metric_type},
            )
            logger.info(f"Created collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def drop_collection(self, collection_name: str) -> bool:
        try:
            client = self._get_client()
            client.drop_collection(collection_name=collection_name)
            logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            raise

    def insert(
        self,
        collection_name: str,
        texts: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        try:
            client = self._get_client()
            embeddings = [self._generate_embedding(text) for text in texts]

            data = [{"text": text, "embedding": emb} for text, emb in zip(texts, embeddings)]
            if metadata:
                for i, meta in enumerate(metadata):
                    data[i].update(meta)

            result = client.insert(collection_name=collection_name, data=data)
            return result.get("ids", [])
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise

    async def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 10,
        output_fields: list[str] | None = None,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            client = self._get_client()
            query_vector = self._generate_embedding(query_text)

            search_params = {"metric_type": "COSINE", "params": {}}
            results = client.search(
                collection_name=collection_name,
                data=[query_vector],
                limit=top_k,
                output_fields=output_fields or ["text", "source"],
                filter=filter_expr,
                search_params=search_params,
            )

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

    def delete_data(self, collection_name: str, expr: str) -> int:
        try:
            client = self._get_client()
            result = client.delete(collection_name=collection_name, filter=expr)
            return result.get("delete_count", 0)
        except Exception as e:
            logger.error(f"Failed to delete data: {e}")
            raise


# ============================================================================
# 工厂函数
# ============================================================================

_provider: MilvusVectorStoreProvider | None = None


def get_vector_store_provider() -> MilvusVectorStoreProvider:
    """获取全局向量存储实例（单例）"""
    global _provider
    if _provider is None:
        _provider = MilvusVectorStoreProvider()
    return _provider


# ============================================================================
# 向后兼容别名
# ============================================================================

MilvusClient = MilvusVectorStoreProvider
get_milvus_client = get_vector_store_provider
