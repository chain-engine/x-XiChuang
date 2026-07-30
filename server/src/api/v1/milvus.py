# -*- coding: utf-8 -*-
"""
Milvus 数据管理 API 路由

提供 Milvus 向量数据库的数据查询、管理接口。
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from src.core.logger import logger
from src.schemas.milvus import (
    CollectionDetail,
    CollectionInfo,
    DeleteRequest,
    DeleteResponse,
    MilvusStatsResponse,
    RebuildKnowledgeResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultEntity,
)
from src.services.milvus_service import get_milvus_service


router = APIRouter()


@router.get("/stats", response_model=MilvusStatsResponse)
async def get_stats() -> MilvusStatsResponse:
    """
    获取 Milvus 服务器统计信息

    返回连接状态、集合列表、各集合数据量等信息。

    Returns:
        MilvusStatsResponse: Milvus 统计信息
    """
    try:
        service = get_milvus_service()
        stats = await service.get_stats()

        collections = [
            CollectionInfo(
                name=c["name"],
                num_entities=c["num_entities"],
            )
            for c in stats.get("collections", [])
        ]

        return MilvusStatsResponse(
            connected=stats.get("connected", False),
            host=stats.get("host"),
            port=stats.get("port"),
            collections_count=stats.get("collections_count"),
            collections=collections,
            error=stats.get("error"),
        )
    except Exception as e:
        logger.error(f"Failed to get Milvus stats: {e}")
        return MilvusStatsResponse(connected=False, error=str(e))


@router.get("/knowledge-status")
async def knowledge_status() -> dict[str, Any]:
    """
    获取知识库/Milvus 构建诊断

    Returns:
        知识库状态信息
    """
    try:
        from src.agent.knowledge import knowledge_base
        return knowledge_base.get_status()
    except Exception as e:
        logger.error(f"Failed to get knowledge status: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/rebuild-knowledge", response_model=RebuildKnowledgeResponse)
async def rebuild_knowledge() -> RebuildKnowledgeResponse:
    """
    强制重建知识库并写入 Milvus

    从仓库根目录 README.md 与 data/knowledge/**/*.md 重新向量化并写入集合。

    Returns:
        重建结果
    """
    try:
        from src.agent.knowledge import knowledge_base

        result = await asyncio.to_thread(knowledge_base.rebuild)

        return RebuildKnowledgeResponse(
            success=True,
            message="Knowledge base rebuilt successfully",
            collection_name=result.get("collection_name"),
            inserted_count=result.get("inserted_count", 0),
        )
    except Exception as e:
        logger.exception(f"Failed to rebuild knowledge: {e}")
        return RebuildKnowledgeResponse(
            success=False,
            message="Failed to rebuild knowledge base",
            error=str(e),
        )


@router.get("/collections")
async def list_collections() -> list[str]:
    """
    列出所有集合

    Returns:
        集合名称列表
    """
    try:
        service = get_milvus_service()
        return await service.list_collections()
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/collections/{collection_name}")
async def get_collection_info(collection_name: str) -> CollectionDetail:
    """
    获取指定集合的详细信息

    Args:
        collection_name: 集合名称

    Returns:
        CollectionDetail: 集合详细信息
    """
    try:
        service = get_milvus_service()
        info = await service.get_collection_info(collection_name)

        if info is None:
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{collection_name}' not found"
            )

        return CollectionDetail(
            name=info["name"],
            description=info.get("description"),
            num_entities=info.get("num_entities", 0),
            dimension=info.get("dimension", 0),
            index_type=info.get("index_type", ""),
            metric_type=info.get("metric_type", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/search", response_model=SearchResponse)
async def search_data(request: SearchRequest) -> SearchResponse:
    """
    搜索向量数据

    使用文本查询在指定集合中搜索相似向量。

    Args:
        request: 搜索请求参数

    Returns:
        SearchResponse: 搜索结果
    """
    import time
    start_time = time.perf_counter()

    try:
        service = get_milvus_service()
        results = await service.search_by_text(
            collection_name=request.collection_name,
            query_text=request.query_text,
            top_k=request.top_k,
            output_fields=request.output_fields,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            success=True,
            collection_name=request.collection_name,
            query_text=request.query_text,
            total=len(results),
            results=[
                SearchResult(
                    id=r["id"],
                    distance=r["distance"],
                    entity=SearchResultEntity(
                        text=r.get("entity", {}).get("text"),
                        source=r.get("entity", {}).get("source"),
                    ),
                )
                for r in results
            ],
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(f"Failed to search data: {e}")
        return SearchResponse(
            success=False,
            collection_name=request.collection_name,
            query_text=request.query_text,
            error=str(e),
        )


@router.delete("/data", response_model=DeleteResponse)
async def delete_data(request: DeleteRequest) -> DeleteResponse:
    """
    删除向量数据

    根据条件表达式删除指定集合中的数据。

    Args:
        request: 删除请求参数

    Returns:
        DeleteResponse: 删除结果
    """
    try:
        service = get_milvus_service()
        deleted_count = await service.delete_data(
            collection_name=request.collection_name,
            expr=request.expr,
        )
        return DeleteResponse(
            success=True,
            deleted_count=deleted_count,
        )
    except Exception as e:
        logger.error(f"Failed to delete data: {e}")
        return DeleteResponse(
            success=False,
            error=str(e),
        )


@router.delete("/collections/{collection_name}")
async def drop_collection(collection_name: str) -> dict[str, Any]:
    """
    删除集合

    警告：此操作不可逆，将删除整个集合及其所有数据！

    Args:
        collection_name: 要删除的集合名称

    Returns:
        操作结果
    """
    try:
        service = get_milvus_service()
        success = await service.drop_collection(collection_name)

        if success:
            return {
                "success": True,
                "message": f"Collection '{collection_name}' dropped"
            }
        raise HTTPException(status_code=500, detail="Failed to drop collection")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to drop collection: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
