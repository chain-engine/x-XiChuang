# -*- coding: utf-8 -*-
"""
Milvus 路由模块单元测试

测试请求模型验证和端点基本逻辑。
"""

import pytest

from src.app.routers.milvus import (
    CollectionInfo,
    DeleteRequest,
    DeleteResponse,
    MilvusStatsResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)


class TestPydanticModels:
    """请求/响应模型验证测试"""

    def test_search_request_defaults(self):
        req = SearchRequest(
            collection_name="test_col",
            query_text="hello",
        )
        assert req.top_k == 10
        assert req.output_fields == ["text", "source"]

    def test_search_request_custom(self):
        req = SearchRequest(
            collection_name="col",
            query_text="test",
            top_k=5,
            output_fields=["text"],
        )
        assert req.top_k == 5
        assert req.output_fields == ["text"]

    def test_search_request_top_k_bounds(self):
        """top_k 应在 1-100 范围内"""
        with pytest.raises(Exception):
            SearchRequest(collection_name="c", query_text="q", top_k=0)
        with pytest.raises(Exception):
            SearchRequest(collection_name="c", query_text="q", top_k=101)

    def test_delete_request(self):
        req = DeleteRequest(collection_name="c", expr="id in [1,2,3]")
        assert req.expr == "id in [1,2,3]"

    def test_collection_info(self):
        info = CollectionInfo(name="test", num_entities=100)
        assert info.name == "test"
        assert info.num_entities == 100

    def test_milvus_stats_response(self):
        resp = MilvusStatsResponse(connected=True, host="localhost", port=19530)
        assert resp.connected is True
        assert resp.collections is None

    def test_search_response(self):
        resp = SearchResponse(success=True, results=[])
        assert resp.success is True
        assert resp.results == []

    def test_delete_response(self):
        resp = DeleteResponse(success=True, deleted_count=5)
        assert resp.deleted_count == 5
