# -*- coding: utf-8 -*-
"""
知识库模块

基于 Milvus 向量数据库实现 RAG 检索增强功能。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import List, Optional

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores.milvus import Milvus
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import settings
from src.core.logger import logger

# 通义 text-embedding-v1：单次文本长度需在 [1, 2048]（按字符/Token 限制，取保守字符上限）
_EMBED_CHUNK_SIZE = 1500
_EMBED_CHUNK_OVERLAP = 200


class KnowledgeBase:
    """
    知识库封装类

    默认从项目根目录下的 README 与 data/knowledge 目录中加载文本，
    构建 Milvus 向量索引，并通过通义的 DashScope embedding 接口进行向量化。
    支持动态配置知识库路径。
    """

    def __init__(self) -> None:
        self._vectorstore: Optional[Milvus] = None
        self._build_attempted: bool = False
        self._last_build_error: Optional[str] = None
        self._source_paths: List[Path] = []

    @staticmethod
    def _repo_root() -> Path:
        """knowledge.py 位于 <repo>/server/src/agent/knowledge.py → 仓库根目录"""
        return Path(__file__).resolve().parents[3]

    def _get_knowledge_sources(self) -> List[Path]:
        """
        获取知识库源路径列表

        支持多种配置方式：
        1. 环境变量 KNOWLEDGE_BASE_PATHS（逗号分隔的路径列表）
        2. 默认路径：README.md + data/knowledge/*.md

        Returns:
            知识库源文件路径列表
        """
        sources: List[Path] = []
        root = self._repo_root()

        # 1. 优先使用环境变量配置
        env_paths = os.getenv("KNOWLEDGE_BASE_PATHS", "").strip()
        if env_paths:
            for path_str in env_paths.split(","):
                path_str = path_str.strip()
                if not path_str:
                    continue
                path = Path(path_str)
                if not path.is_absolute():
                    path = root / path
                if path.exists():
                    if path.is_file():
                        sources.append(path)
                    elif path.is_dir():
                        sources.extend(path.rglob("*.md"))
                        sources.extend(path.rglob("*.txt"))
                else:
                    logger.warning(f"Knowledge source path does not exist: {path}")
            if sources:
                logger.info(f"Loaded {len(sources)} knowledge sources from KNOWLEDGE_BASE_PATHS")
                return sources

        # 2. 默认路径：README.md
        readme_path = root / "README.md"
        if readme_path.exists():
            sources.append(readme_path)

        # 3. 默认路径：data/knowledge 目录
        knowledge_dir = root / "data" / "knowledge"
        if knowledge_dir.exists():
            md_files = list(knowledge_dir.rglob("*.md"))
            sources.extend(md_files)

        return sources

    def get_status(self) -> dict:
        """供运维/Swagger 诊断：为何不建 Milvus、当前是否已就绪（不含密钥内容）"""
        root = self._repo_root()
        readme_path = root / "README.md"
        knowledge_dir = root / "data" / "knowledge"
        sources = self._get_knowledge_sources()

        return {
            "repo_root": str(root),
            "readme_path": str(readme_path),
            "readme_exists": readme_path.exists(),
            "knowledge_dir": str(knowledge_dir),
            "knowledge_md_count": len([p for p in sources if p.suffix == ".md"]),
            "total_sources": len(sources),
            "source_paths": [str(p) for p in sources],
            "aliyun_api_key_configured": bool(settings.ALIYUN_API_KEY),
            "embedding_model": settings.ALIYUN_EMBEDDING_MODEL_NAME,
            "milvus_host": settings.MILVUS_HOST,
            "milvus_port": settings.MILVUS_PORT,
            "collection_name": "x_multimodal_knowledge",
            "embedding_chunk_max_chars": _EMBED_CHUNK_SIZE,
            "vectorstore_ready": self._vectorstore is not None,
            "build_attempted": self._build_attempted,
            "last_build_error": self._last_build_error,
            "hint": "可通过 KNOWLEDGE_BASE_PATHS 环境变量自定义知识库路径，多个路径用逗号分隔。",
        }

    def rebuild(self) -> dict:
        """重置状态并重新从配置的知识库源写入 Milvus"""
        self._vectorstore = None
        self._build_attempted = False
        self._last_build_error = None
        self.ensure_built()
        status = self.get_status()
        status["rebuild_success"] = self._vectorstore is not None
        return status

    def _build_vectorstore(self) -> Optional[Milvus]:
        """
        构建向量存储

        Returns:
            Milvus 向量存储实例，如果构建失败则返回 None
        """
        root = self._repo_root()
        self._last_build_error = None

        texts: List[str] = []
        metadatas: List[dict] = []

        # 获取知识库源路径
        self._source_paths = self._get_knowledge_sources()

        for path in self._source_paths:
            try:
                content = path.read_text(encoding="utf-8")
                texts.append(content)
                metadatas.append({"source": str(path.relative_to(root)) if path.is_relative_to(root) else str(path)})
            except Exception as exc:
                logger.warning("Failed to read knowledge file %s: %s", path, exc)

        if not texts:
            msg = "no documents: no valid knowledge sources found. Check KNOWLEDGE_BASE_PATHS or ensure README.md and data/knowledge/*.md exist."
            self._last_build_error = msg
            logger.info("Knowledge base has no documents; retrieval node will be a no-op.")
            return None

        # 检查 API Key
        if not settings.ALIYUN_API_KEY:
            msg = "ALIYUN_API_KEY / DASHSCOPE_API_KEY not configured in server/.env"
            self._last_build_error = msg
            logger.warning("ALIYUN_API_KEY not set, knowledge base will not work")
            return None

        # 整篇 README 往往远超 2048，必须切块后再 embedding，否则会 400 InvalidParameter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=_EMBED_CHUNK_SIZE,
            chunk_overlap=_EMBED_CHUNK_OVERLAP,
            length_function=len,
        )
        chunk_texts: List[str] = []
        chunk_metas: List[dict] = []
        for raw, meta in zip(texts, metadatas):
            for i, piece in enumerate(splitter.split_text(raw)):
                piece = piece.strip()
                if not piece:
                    continue
                chunk_texts.append(piece)
                m = dict(meta)
                m["chunk_index"] = i
                chunk_metas.append(m)

        if not chunk_texts:
            msg = "after chunking, no non-empty text segments (check source files)"
            self._last_build_error = msg
            logger.warning("Knowledge base chunking produced no segments")
            return None

        try:
            embeddings = DashScopeEmbeddings(
                model=settings.ALIYUN_EMBEDDING_MODEL_NAME,
                dashscope_api_key=settings.ALIYUN_API_KEY,
            )

            # Milvus 连接配置
            connection_args = {
                "host": settings.MILVUS_HOST,
                "port": settings.MILVUS_PORT,
            }

            logger.info(
                "Ingesting %d chunks from %d source document(s) into Milvus (chunk_size≈%s)",
                len(chunk_texts),
                len(texts),
                _EMBED_CHUNK_SIZE,
            )

            # 创建 Milvus 向量存储
            vectorstore = Milvus.from_texts(
                texts=chunk_texts,
                embedding=embeddings,
                metadatas=chunk_metas,
                collection_name="x_multimodal_knowledge",
                connection_args=connection_args,
                drop_old=False,  # 如果集合已存在，保留原有数据
            )
            logger.info("Milvus vectorstore created successfully")
            return vectorstore
        except Exception as e:
            self._last_build_error = str(e)
            logger.error(f"Failed to create Milvus vectorstore: {e}")
            return None

    def ensure_built(self) -> None:
        """确保向量存储已构建"""
        if self._vectorstore is None and not self._build_attempted:
            self._build_attempted = True
            self._vectorstore = self._build_vectorstore()

    async def aretrieve(self, query: str, k: int = 4) -> List[str]:
        """
        异步封装的检索接口，返回若干段匹配文档内容

        Args:
            query: 用户查询文本（为空/全空白则直接返回空列表）
            k: 返回的相似片段数量（默认 4）

        Returns:
            文档片段列表（按相似度排序）
        """
        self.ensure_built()
        if self._vectorstore is None or not query.strip():
            return []

        def _search() -> List[str]:
            try:
                docs = self._vectorstore.similarity_search(query, k=k)
                return [d.page_content for d in docs]
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []

        return await asyncio.to_thread(_search)

    def retrieve(self, query: str, k: int = 4) -> List[str]:
        """
        同步检索接口

        Args:
            query: 用户查询文本
            k: 返回的相似片段数量

        Returns:
            文档片段列表
        """
        self.ensure_built()
        if self._vectorstore is None or not query.strip():
            return []

        try:
            docs = self._vectorstore.similarity_search(query, k=k)
            return [d.page_content for d in docs]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


# 全局知识库实例
knowledge_base = KnowledgeBase()
