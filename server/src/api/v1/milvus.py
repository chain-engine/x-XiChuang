# -*- coding: utf-8 -*-
"""
Milvus 数据管理 API 路由

提供 Milvus 向量数据库的数据查询、管理接口。

职责边界：
- 本文件仅处理 HTTP 请求接入，**不实现任何业务逻辑**
- 所有 Milvus 操作委托给 ``services/milvus_service.py``
- 所有响应使用 ``api/response.py`` 的统一响应封装
- PUT / DELETE 语义统一使用 POST 提交

接口列表：
- ``GET  /stats``                    — Milvus 服务器统计信息
- ``GET  /knowledge-status``         — 知识库构建诊断
- ``POST /rebuild-knowledge``        — 强制重建知识库
- ``GET  /collections``              — 列出所有集合
- ``GET  /collections/{name}``       — 获取集合详情
- ``POST /search``                   — 搜索向量数据
- ``POST /data/delete``              — 删除向量数据
- ``POST /collections/drop``         — 删除集合
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Request

from src.api.response import success_response
from src.core.logger import logger
from src.schemas.milvus import (
    CollectionDetail,
    CollectionInfo,
    DeleteRequest,
    DeleteResponse,
    DropCollectionRequest,
    MilvusStatsResponse,
    RebuildKnowledgeResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultEntity,
)
from src.services.milvus_service import get_milvus_service


router = APIRouter(tags=["知识库"])


@router.get(
    "/stats",
    response_model=MilvusStatsResponse,
    summary="Milvus 统计信息",
    description="返回 Milvus 连接状态、集合列表及各集合数据量。",
)
async def get_stats(request: Request) -> Any:
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

        data = MilvusStatsResponse(
            connected=stats.get("connected", False),
            host=stats.get("host"),
            port=stats.get("port"),
            collections_count=stats.get("collections_count"),
            collections=collections,
            error=stats.get("error"),
        ).model_dump(mode="json", exclude_none=True)
        return success_response(data=data, request=request)
    except Exception as e:
        logger.error(f"Failed to get Milvus stats: {e}")
        data = MilvusStatsResponse(connected=False, error=str(e)).model_dump(
            mode="json", exclude_none=True
        )
        return success_response(data=data, request=request)


@router.get(
    "/knowledge-status",
    summary="知识库状态",
    description="获取知识库 / Milvus 构建诊断信息。",
)
async def knowledge_status(request: Request) -> Any:
    """
    获取知识库 / Milvus 构建诊断

    Returns:
        知识库状态信息
    """
    try:
        from src.agent.knowledge import knowledge_base
        data = knowledge_base.get_status()
    except Exception as e:
        logger.error(f"Failed to get knowledge status: {e}")
        data = {"status": "error", "error": str(e)}

    return success_response(data=data, request=request)


@router.post(
    "/rebuild-knowledge",
    response_model=RebuildKnowledgeResponse,
    summary="重建知识库",
    description="从仓库 README.md 与 data/knowledge/**/*.md 重新向量化并写入集合。",
)
async def rebuild_knowledge(request: Request) -> Any:
    """
    强制重建知识库并写入 Milvus

    从仓库根目录 README.md 与 data/knowledge/**/*.md 重新向量化并写入集合。

    Returns:
        重建结果
    """
    try:
        from src.agent.knowledge import knowledge_base

        result = await asyncio.to_thread(knowledge_base.rebuild)

        data = RebuildKnowledgeResponse(
            success=True,
            message="Knowledge base rebuilt successfully",
            collection_name=result.get("collection_name"),
            inserted_count=result.get("inserted_count", 0),
        ).model_dump(mode="json")
        return success_response(data=data, request=request)
    except Exception as e:
        logger.exception(f"Failed to rebuild knowledge: {e}")
        data = RebuildKnowledgeResponse(
            success=False,
            message="Failed to rebuild knowledge base",
            error=str(e),
        ).model_dump(mode="json")
        return success_response(data=data, request=request)


@router.get(
    "/collections",
    summary="列出所有集合",
    description="返回 Milvus 中所有集合的名称列表。",
)
async def list_collections(request: Request) -> Any:
    """
    列出所有集合

    Returns:
        集合名称列表
    """
    try:
        service = get_milvus_service()
        collections = await service.list_collections()
        return success_response(data=collections, request=request)
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        from src.core.exceptions import SystemException
        raise SystemException(message=f"Failed to list collections: {e}") from e


@router.get(
    "/collections/{collection_name}",
    response_model=CollectionDetail,
    summary="集合详情",
    description="获取指定集合的详细信息，包括字段、索引、实体数量等。",
)
async def get_collection_info(
    collection_name: str,
    request: Request,
) -> Any:
    """
    获取指定集合的详细信息

    Args:
        collection_name: 集合名称

    Returns:
        CollectionDetail: 集合详细信息
    """
    service = get_milvus_service()
    info = await service.get_collection_info(collection_name)

    if info is None:
        from src.core.exceptions import NotFoundError
        raise NotFoundError(message=f"Collection '{collection_name}' not found")

    data = CollectionDetail(
        name=info["name"],
        description=info.get("description"),
        num_entities=info.get("num_entities", 0),
        dimension=info.get("dimension", 0),
        index_type=info.get("index_type", ""),
        metric_type=info.get("metric_type", ""),
    ).model_dump(mode="json")
    return success_response(data=data, request=request)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="搜索向量数据",
    description="使用文本查询在指定集合中搜索相似向量。",
)
async def search_data(
    request_body: SearchRequest,
    request: Request,
) -> Any:
    """
    搜索向量数据

    使用文本查询在指定集合中搜索相似向量。

    Args:
        request_body: 搜索请求参数

    Returns:
        SearchResponse: 搜索结果
    """
    start_time = time.perf_counter()

    try:
        service = get_milvus_service()
        results = await service.search_by_text(
            collection_name=request_body.collection_name,
            query_text=request_body.query_text,
            top_k=request_body.top_k,
            output_fields=request_body.output_fields,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        data = SearchResponse(
            success=True,
            collection_name=request_body.collection_name,
            query_text=request_body.query_text,
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
        ).model_dump(mode="json")
        return success_response(data=data, request=request)
    except Exception as e:
        logger.error(f"Failed to search data: {e}")
        data = SearchResponse(
            success=False,
            collection_name=request_body.collection_name,
            query_text=request_body.query_text,
            error=str(e),
        ).model_dump(mode="json")
        return success_response(data=data, request=request)


@router.post(
    "/data/delete",
    response_model=DeleteResponse,
    summary="删除向量数据",
    description="根据条件表达式删除指定集合中的数据。PUT/DELETE 语义统一使用 POST 提交。",
)
async def delete_data(
    request_body: DeleteRequest,
    request: Request,
) -> Any:
    """
    删除向量数据

    根据条件表达式删除指定集合中的数据。

    Args:
        request_body: 删除请求参数

    Returns:
        DeleteResponse: 删除结果
    """
    try:
        service = get_milvus_service()
        deleted_count = await service.delete_data(
            collection_name=request_body.collection_name,
            expr=request_body.expr,
        )
        data = DeleteResponse(
            success=True,
            deleted_count=deleted_count,
        ).model_dump(mode="json")
        return success_response(data=data, request=request)
    except Exception as e:
        logger.error(f"Failed to delete data: {e}")
        data = DeleteResponse(
            success=False,
            error=str(e),
        ).model_dump(mode="json")
        return success_response(data=data, request=request)


@router.post(
    "/collections/drop",
    summary="删除集合",
    description="删除指定集合及其所有数据。**警告：此操作不可逆！** PUT/DELETE 语义统一使用 POST 提交。",
)
async def drop_collection(
    request_body: DropCollectionRequest,
    request: Request,
) -> Any:
    """
    删除集合

    警告：此操作不可逆，将删除整个集合及其所有数据！

    Args:
        request_body: 包含要删除的集合名称

    Returns:
        操作结果
    """
    service = get_milvus_service()
    success = await service.drop_collection(request_body.collection_name)

    if success:
        return success_response(
            data={"message": f"Collection '{request_body.collection_name}' dropped"},
            request=request,
        )

    from src.core.exceptions import SystemException
    raise SystemException(message="Failed to drop collection")
