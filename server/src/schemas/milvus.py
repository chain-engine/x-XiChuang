# -*- coding: utf-8 -*-
"""
Milvus Schema 定义

包含 Milvus 向量数据库管理的请求和响应模型。
用于 ``/api/v1/milvus`` 下的所有接口。

Schema 分层：
- 请求 Schema（*Request）：负责参数格式校验
- 响应 Schema（*Response）：负责输出结构定义
- 业务规则校验由 services 层完成
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============ 集合信息 Schema ============


class CollectionInfo(BaseModel):
    """
    集合简要信息

    用于列表展示，不包含字段详情。
    """

    name: str = Field(..., description="集合名称")
    num_entities: int = Field(..., description="实体数量")
    dimension: int | None = Field(None, description="向量维度")
    index_type: str | None = Field(None, description="索引类型")
    description: str | None = Field(None, description="集合描述")


class FieldSchema(BaseModel):
    """
    字段模式定义

    描述集合中单个字段的结构信息。
    """

    name: str = Field(..., description="字段名称")
    data_type: str = Field(..., description="数据类型")
    description: str | None = Field(None, description="字段描述")
    is_primary_key: bool = Field(default=False, description="是否主键")
    is_indexed: bool = Field(default=False, description="是否建索引")


class CollectionDetail(BaseModel):
    """
    集合详细信息

    用于 ``GET /api/v1/milvus/collections/{name}``。
    """

    name: str = Field(..., description="集合名称")
    description: str | None = Field(None, description="集合描述")
    num_entities: int = Field(..., description="实体数量")
    dimension: int = Field(..., description="向量维度")
    index_type: str = Field(..., description="索引类型")
    metric_type: str = Field(..., description="度量类型")
    fields: list[FieldSchema] = Field(default_factory=list, description="字段列表")
    created_at: str | None = Field(None, description="创建时间")


# ============ 统计响应 Schema ============


class MilvusStatsResponse(BaseModel):
    """
    Milvus 统计响应

    用于 ``GET /api/v1/milvus/stats``。
    返回连接状态、集合列表、各集合数据量等信息。
    """

    connected: bool = Field(..., description="是否已连接")
    host: str | None = Field(None, description="主机地址")
    port: int | None = Field(None, description="端口号")
    collections_count: int | None = Field(None, description="集合数量")
    collections: list[CollectionInfo] | None = Field(None, description="集合列表")
    error: str | None = Field(None, description="错误信息（连接失败时）")


# ============ 搜索 Schema ============


class SearchRequest(BaseModel):
    """
    向量搜索请求

    用于 ``POST /api/v1/milvus/search``。
    使用文本查询在指定集合中搜索相似向量。
    """

    collection_name: str = Field(..., description="目标集合名称")
    query_text: str = Field(..., description="查询文本（将被向量化后检索）", min_length=1)
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    output_fields: list[str] = Field(
        default_factory=lambda: ["text", "source"],
        description="需要返回的字段列表"
    )
    filter_expr: str | None = Field(None, description="标量过滤表达式")
    round_decimal: int = Field(default=-1, description="距离保留小数位数，-1 不限制")


class SearchResultEntity(BaseModel):
    """
    搜索结果实体

    包含匹配文档的业务数据。
    """

    text: str | None = Field(None, description="文本内容")
    source: str | None = Field(None, description="来源标识")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")


class SearchResult(BaseModel):
    """
    单条搜索结果

    包含向量 ID、相似度距离和实体数据。
    """

    id: int = Field(..., description="向量 ID")
    distance: float = Field(..., description="相似度距离（越小越相似）")
    entity: SearchResultEntity = Field(..., description="实体数据")


class SearchResponse(BaseModel):
    """
    搜索响应

    用于 ``POST /api/v1/milvus/search`` 的返回。
    """

    success: bool = Field(..., description="是否成功")
    collection_name: str = Field(..., description="查询的集合名称")
    query_text: str = Field(..., description="原始查询文本")
    total: int = Field(default=0, description="结果总数")
    results: list[SearchResult] = Field(
        default_factory=list,
        description="搜索结果列表"
    )
    latency_ms: float | None = Field(None, description="查询延迟（毫秒）")
    error: str | None = Field(None, description="错误信息（失败时）")


# ============ 删除 Schema ============


class DeleteRequest(BaseModel):
    """
    删除数据请求

    用于 ``POST /api/v1/milvus/data/delete``。
    根据条件表达式删除指定集合中的数据。
    """

    collection_name: str = Field(..., description="目标集合名称")
    expr: str = Field(..., description="删除条件表达式，如 'id in [1,2,3]'")


class DeleteResponse(BaseModel):
    """删除数据响应"""

    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(default=0, description="删除数量")
    error: str | None = Field(None, description="错误信息（失败时）")


# ============ 集合操作 Schema ============


class DropCollectionRequest(BaseModel):
    """
    删除集合请求

    用于 ``POST /api/v1/milvus/collections/drop``。
    **警告：此操作不可逆，将删除整个集合及其所有数据！**
    """

    collection_name: str = Field(..., description="要删除的集合名称")


class CreateCollectionRequest(BaseModel):
    """
    创建集合请求

    用于 ``POST /api/v1/milvus/collections/create``。
    """

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


# ============ 知识库 Schema ============


class KnowledgeStatus(BaseModel):
    """
    知识库状态

    用于 ``GET /api/v1/milvus/knowledge-status``。
    """

    status: str = Field(..., description="状态")
    collection_name: str | None = Field(None, description="集合名称")
    document_count: int = Field(default=0, description="文档数量")
    last_build_time: str | None = Field(None, description="最后构建时间")
    error: str | None = Field(None, description="错误信息")


class RebuildKnowledgeResponse(BaseModel):
    """
    重建知识库响应

    用于 ``POST /api/v1/milvus/rebuild-knowledge``。
    """

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    collection_name: str | None = Field(None, description="集合名称")
    inserted_count: int = Field(default=0, description="插入数量")
    error: str | None = Field(None, description="错误信息（失败时）")
