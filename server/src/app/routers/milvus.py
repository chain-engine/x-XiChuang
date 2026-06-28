# -*- coding: utf-8 -*-
"""
Milvus 数据管理 API 路由

提供 Milvus 向量数据库的数据查询、管理接口，方便运维操作。
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agent.knowledge import knowledge_base
from src.core.logger import logger
from src.app.services.milvus_service import get_milvus_service


router = APIRouter()


class CollectionInfo(BaseModel):
    """集合信息"""

    name: str = Field(..., description="集合名称")
    num_entities: int = Field(..., description="实体数量")


class MilvusStatsResponse(BaseModel):
    """Milvus 统计响应"""

    connected: bool = Field(..., description="是否已连接")
    host: Optional[str] = Field(None, description="主机地址")
    port: Optional[int] = Field(None, description="端口号")
    collections_count: Optional[int] = Field(None, description="集合数量")
    collections: Optional[List[CollectionInfo]] = Field(None, description="集合列表")
    error: Optional[str] = Field(None, description="错误信息")


class SearchRequest(BaseModel):
    """搜索请求"""

    collection_name: str = Field(..., description="集合名称")
    query_text: str = Field(..., description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    output_fields: List[str] = Field(default_factory=lambda: ["text", "source"], description="输出字段")


class SearchResult(BaseModel):
    """搜索结果"""

    id: int = Field(..., description="向量ID")
    distance: float = Field(..., description="距离")
    entity: Dict[str, Any] = Field(default_factory=dict, description="实体数据")


class SearchResponse(BaseModel):
    """搜索响应"""

    success: bool = Field(..., description="是否成功")
    results: List[SearchResult] = Field(default_factory=list, description="搜索结果")
    error: Optional[str] = Field(None, description="错误信息")


class DeleteRequest(BaseModel):
    """删除请求"""

    collection_name: str = Field(..., description="集合名称")
    expr: str = Field(..., description="删除条件表达式，如 'id in [1,2,3]'")


class DeleteResponse(BaseModel):
    """删除响应"""

    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(default=0, description="删除数量")
    error: Optional[str] = Field(None, description="错误信息")


@router.get("/stats", response_model=MilvusStatsResponse)
async def get_stats() -> MilvusStatsResponse:
    """
    获取 Milvus 服务器统计信息

    返回连接状态、集合列表、各集合数据量等信息。
    """
    try:
        service = get_milvus_service()
        stats = await service.get_stats()

        collections = [
            CollectionInfo(name=c["name"], num_entities=c["num_entities"])
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


@router.get("/knowledge-status", summary="知识库 / Milvus 构建诊断")
async def knowledge_status() -> Dict[str, Any]:
    """
    说明：仅「连接 Milvus」不会自动建集合；集合由知识库模块在 ingest 时创建。

    若 `collections` 一直为空，先看本接口的 `readme_exists`、`aliyun_api_key_configured`、`last_build_error`。
    """
    return knowledge_base.get_status()


@router.post("/rebuild-knowledge", summary="强制重建知识库并写入 Milvus")
async def rebuild_knowledge() -> Dict[str, Any]:
    """
    从仓库根目录 README.md 与 data/knowledge/**/*.md 重新向量化并写入集合 `x_multimodal_knowledge`。

    需配置有效的通义 Embedding Key（settings.ALIYUN_API_KEY，或与 DASHSCOPE_API_KEY 兼容读取）。
    可能耗时数十秒，请勿重复狂点。
    """
    try:
        return await asyncio.to_thread(knowledge_base.rebuild)
    except Exception as e:
        logger.exception("rebuild-knowledge failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/collections", response_model=List[str])
async def list_collections() -> List[str]:
    """
    列出所有集合

    返回 Milvus 中所有集合的名称列表。
    """
    try:
        service = get_milvus_service()
        return await service.list_collections()
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_name}")
async def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """
    获取指定集合的详细信息

    Args:
        collection_name: 集合名称

    Returns:
        集合信息，包括实体数量、字段等
    """
    try:
        service = get_milvus_service()
        info = await service.get_collection_info(collection_name)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_data(request: SearchRequest) -> SearchResponse:
    """
    搜索向量数据

    使用文本查询在指定集合中搜索相似向量。

    Args:
        request: 搜索请求参数

    Returns:
        搜索结果列表
    """
    try:
        service = get_milvus_service()
        results = await service.search_by_text(
            collection_name=request.collection_name,
            query_text=request.query_text,
            top_k=request.top_k,
            output_fields=request.output_fields,
        )

        search_results = [
            SearchResult(
                id=r["id"],
                distance=r["distance"],
                entity=r.get("entity", {}),
            )
            for r in results
        ]

        return SearchResponse(success=True, results=search_results)
    except Exception as e:
        logger.error(f"Failed to search data: {e}")
        return SearchResponse(success=False, error=str(e))


@router.delete("/data", response_model=DeleteResponse)
async def delete_data(request: DeleteRequest) -> DeleteResponse:
    """
    删除向量数据

    根据条件表达式删除指定集合中的数据。

    Args:
        request: 删除请求参数

    Returns:
        删除结果
    """
    try:
        service = get_milvus_service()
        deleted_count = await service.delete_data(
            collection_name=request.collection_name,
            expr=request.expr,
        )
        return DeleteResponse(success=True, deleted_count=deleted_count)
    except Exception as e:
        logger.error(f"Failed to delete data: {e}")
        return DeleteResponse(success=False, error=str(e))


@router.delete("/collections/{collection_name}")
async def drop_collection(collection_name: str) -> Dict[str, Any]:
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
            return {"success": True, "message": f"Collection '{collection_name}' dropped"}
        raise HTTPException(status_code=500, detail="Failed to drop collection")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to drop collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
