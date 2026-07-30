# -*- coding: utf-8 -*-
"""
Milvus Schema 定义

包含 Milvus 向量数据库管理的请求和响应模型。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CollectionInfo(BaseModel):
    """集合信息"""

    name: str = Field(..., description="集合名称")
    num_entities: int = Field(..., description="实体数量")
    dimension: int | None = Field(None, description="向量维度")
    index_type: str | None = Field(None, description="索引类型")
    description: str | None = Field(None, description="集合描述")


class MilvusStatsResponse(BaseModel):
    """Milvus 统计响应"""

    connected: bool = Field(..., description="是否已连接")
    host: str | None = Field(None, description="主机地址")
    port: int | None = Field(None, description="端口号")
    collections_count: int | None = Field(None, description="集合数量")
    collections: list[CollectionInfo] | None = Field(None, description="集合列表")
    error: str | None = Field(None, description="错误信息")


class FieldSchema(BaseModel):
    """字段模式"""

    name: str = Field(..., description="字段名称")
    data_type: str = Field(..., description="数据类型")
    description: str | None = Field(None, description="字段描述")
    is_primary_key: bool = Field(default=False, description="是否主键")
    is_indexed: bool = Field(default=False, description="是否建索引")


class CollectionDetail(BaseModel):
    """集合详情"""

    name: str = Field(..., description="集合名称")
    description: str | None = Field(None, description="集合描述")
    num_entities: int = Field(..., description="实体数量")
    dimension: int = Field(..., description="向量维度")
    index_type: str = Field(..., description="索引类型")
    metric_type: str = Field(..., description="度量类型")
    fields: list[FieldSchema] = Field(default_factory=list, description="字段列表")
    created_at: str | None = Field(None, description="创建时间")


class SearchRequest(BaseModel):
    """向量搜索请求"""

    collection_name: str = Field(..., description="集合名称")
    query_text: str = Field(..., description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    output_fields: list[str] = Field(
        default_factory=lambda: ["text", "source"],
        description="输出字段"
    )
    filter_expr: str | None = Field(None, description="过滤表达式")
    round_decimal: int = Field(default=-1, description="距离保留小数位数")


class SearchResultEntity(BaseModel):
    """搜索结果实体"""

    text: str | None = Field(None, description="文本内容")
    source: str | None = Field(None, description="来源")
    metadata: dict[str, Any] | None = Field(None, description="元数据")


class SearchResult(BaseModel):
    """搜索结果"""

    id: int = Field(..., description="向量ID")
    distance: float = Field(..., description="相似度距离")
    entity: SearchResultEntity = Field(..., description="实体数据")


class SearchResponse(BaseModel):
    """搜索响应"""

    success: bool = Field(..., description="是否成功")
    collection_name: str = Field(..., description="集合名称")
    query_text: str = Field(..., description="查询文本")
    total: int = Field(default=0, description="结果总数")
    results: list[SearchResult] = Field(
        default_factory=list,
        description="搜索结果"
    )
    latency_ms: float | None = Field(None, description="查询延迟（毫秒）")
    error: str | None = Field(None, description="错误信息")


class InsertRequest(BaseModel):
    """插入数据请求"""

    collection_name: str = Field(..., description="集合名称")
    texts: list[str] = Field(..., description="文本列表", min_length=1)
    metadata: list[dict[str, Any]] | None = Field(None, description="元数据列表")


class InsertResponse(BaseModel):
    """插入数据响应"""

    success: bool = Field(..., description="是否成功")
    collection_name: str = Field(..., description="集合名称")
    inserted_count: int = Field(default=0, description="插入数量")
    ids: list[int] = Field(default_factory=list, description="插入的ID列表")
    error: str | None = Field(None, description="错误信息")


class DeleteRequest(BaseModel):
    """删除数据请求"""

    collection_name: str = Field(..., description="集合名称")
    expr: str = Field(..., description="删除条件表达式，如 'id in [1,2,3]'")
    filter_expr: str | None = Field(None, description="过滤表达式（与 expr 二选一）")


class DeleteResponse(BaseModel):
    """删除数据响应"""

    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(default=0, description="删除数量")
    error: str | None = Field(None, description="错误信息")


class CreateCollectionRequest(BaseModel):
    """创建集合请求"""

    collection_name: str = Field(..., description="集合名称")
    dimension: int = Field(..., description="向量维度", ge=1, le=65536)
    description: str | None = Field(None, description="集合描述")
    index_type: str = Field(default="AUTOINDEX", description="索引类型")
    metric_type: str = Field(default="COSINE", description="度量类型")


class CreateCollectionResponse(BaseModel):
    """创建集合响应"""

    success: bool = Field(..., description="是否成功")
    collection_name: str = Field(..., description="集合名称")
    message: str | None = Field(None, description="操作消息")


class KnowledgeStatus(BaseModel):
    """知识库状态"""

    status: str = Field(..., description="状态")
    collection_name: str | None = Field(None, description="集合名称")
    document_count: int = Field(default=0, description="文档数量")
    last_build_time: str | None = Field(None, description="最后构建时间")
    error: str | None = Field(None, description="错误信息")


class RebuildKnowledgeResponse(BaseModel):
    """重建知识库响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    collection_name: str | None = Field(None, description="集合名称")
    inserted_count: int = Field(default=0, description="插入数量")
    error: str | None = Field(None, description="错误信息")
