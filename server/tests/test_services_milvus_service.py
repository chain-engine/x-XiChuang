# -*- coding: utf-8 -*-
"""
Milvus 服务模块单元测试

使用 mock 替代真实 Milvus 客户端。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.services.milvus_service import MilvusService, get_milvus_service


class TestMilvusService:
    """MilvusService 测试"""

    def test_lazy_client_initialization(self):
        service = MilvusService()
        assert service._client is None

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {
            "connected": True,
            "host": "localhost",
            "port": 19530,
            "collections_count": 2,
            "collections": [
                {"name": "col1", "num_entities": 100},
                {"name": "col2", "num_entities": 50},
            ],
        }
        service._client = mock_client

        result = await service.get_stats()
        assert result["connected"] is True
        assert result["collections_count"] == 2

    @pytest.mark.asyncio
    async def test_get_stats_failure(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.get_stats.side_effect = Exception("connection refused")
        service._client = mock_client

        result = await service.get_stats()
        assert result["connected"] is False
        assert "connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_list_collections(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["col1", "col2"]
        service._client = mock_client

        result = await service.list_collections()
        assert result == ["col1", "col2"]

    @pytest.mark.asyncio
    async def test_list_collections_error_propagation(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.list_collections.side_effect = Exception("failed")
        service._client = mock_client

        with pytest.raises(Exception, match="failed"):
            await service.list_collections()

    @pytest.mark.asyncio
    async def test_search_by_text(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.search_by_text = AsyncMock(return_value=[
            {"id": 1, "distance": 0.95, "entity": {"text": "hello"}},
        ])
        service._client = mock_client

        results = await service.search_by_text("col", "hello", top_k=5)
        assert len(results) == 1
        assert results[0]["distance"] == 0.95

    @pytest.mark.asyncio
    async def test_drop_collection(self):
        service = MilvusService()
        mock_client = MagicMock()
        mock_client.drop_collection.return_value = True
        service._client = mock_client

        result = await service.drop_collection("test_col")
        assert result is True


class TestGetMilvusService:
    """get_milvus_service 单例测试"""

    def test_returns_instance(self):
        with patch("src.app.services.milvus_service._milvus_service", None):
            with patch("src.app.services.milvus_service.MilvusService") as MockService:
                mock_instance = MagicMock()
                MockService.return_value = mock_instance
                # 重置全局变量
                import src.app.services.milvus_service as mod
                mod._milvus_service = None
                result = get_milvus_service()
                assert result is not None
                mod._milvus_service = None
