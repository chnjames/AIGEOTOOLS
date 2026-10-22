"""知识库管理服务 - 从 knowledge_base.py 迁移（简化版 RAG，支持文件上传和文本检索）

支持向量语义搜索（ChromaDB + all-MiniLM-L6-v2 本地嵌入模型）与关键词搜索。
若 chromadb 未安装或嵌入模型加载失败，自动降级为关键词搜索。

向量库扩展性说明
================

当前使用 **嵌入式 ChromaDB**（``PersistentClient``），数据存储在本地文件系统
（``./data/chroma_db``）。该方案的特点与适用场景：

- **适用规模**：中小规模知识库（< 100,000 文档 / < 500,000 文档分块）。
  嵌入式模式在单机文件系统上运行，无需额外服务部署，运维成本低。
- **性能特征**：HNSW 索引在内存中加载，查询延迟通常在毫秒级；
  但随着文档量增长，索引加载时间和内存占用会线性增加。
- **并发限制**：嵌入式 ChromaDB 不支持多进程并发写入，仅适合单实例部署。

大规模部署建议
--------------

当知识库规模超过 100k 文档或需要多实例部署时，建议迁移到：

1. **独立 ChromaDB 服务**：使用 ``HttpClient`` 连接独立部署的 ChromaDB
   Server，支持多客户端并发访问和横向扩展。
2. **Pinecone**：全托管向量数据库，支持十亿级向量，自动扩缩容，
   适合大规模生产环境。
3. **Weaviate**：开源向量搜索引擎，支持混合检索（向量 + 关键词）、
   GraphQL 查询接口，可自托管或使用云服务。
4. **Milvus / Qdrant**：其他高性能开源向量数据库选项。

迁移时只需替换 ``_init_vector_store_module()`` 中的客户端初始化逻辑，
保持 ``_chroma_collection`` 的 ``add`` / ``delete`` / ``query`` 接口兼容即可。
使用 :meth:`KnowledgeService.get_knowledge_stats` 可监控知识库规模，
在接近阈值时及时规划迁移。

降级策略
--------

当 ChromaDB 或嵌入模型不可用时（如依赖未安装、模型下载失败），
服务自动降级为基于 SQL LIKE + 字符重叠度的关键词搜索，
确保核心检索功能始终可用。
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FileError, ValidationError
from app.core.logging import get_logger
from app.models.knowledge_doc import KnowledgeDoc

logger = get_logger(__name__)
settings = get_settings()

CHUNK_SIZE = 500  # 字符数
CHUNK_OVERLAP = 50


def _get_directory_size(path: str) -> int:
    """递归计算目录的总大小（字节）。

    Args:
        path: 目录路径。

    Returns:
        总大小（字节），目录不存在时返回 0。
    """
    total = 0
    if not os.path.isdir(path):
        return 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for filename in filenames:
            fp = os.path.join(dirpath, filename)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


# ---------------------------------------------------------------------------
# Vector DB setup - ChromaDB chosen for embedded persistence + metadata filtering
# FAISS would require manual persistence/metadata handling; ChromaDB is higher-level.
# Uses DefaultEmbeddingFunction (all-MiniLM-L6-v2) - runs locally, no API key needed.
# ---------------------------------------------------------------------------
VECTOR_SEARCH_AVAILABLE = False
_chroma_client = None
_chroma_collection = None


def _init_vector_store_module() -> None:
    """Initialize ChromaDB at module import time; sets VECTOR_SEARCH_AVAILABLE flag."""
    global VECTOR_SEARCH_AVAILABLE, _chroma_client, _chroma_collection
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        os.makedirs("./data/chroma_db", exist_ok=True)
        _embedding_function = embedding_functions.DefaultEmbeddingFunction()
        _chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        _chroma_collection = _chroma_client.get_or_create_collection(
            name="knowledge_chunks",
            embedding_function=_embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        VECTOR_SEARCH_AVAILABLE = True
        logger.info("ChromaDB vector search initialized successfully")
    except ImportError:
        logger.warning("chromadb package not installed, falling back to keyword search")
        _chroma_client = None
        _chroma_collection = None
        VECTOR_SEARCH_AVAILABLE = False
    except Exception as e:
        logger.warning("ChromaDB failed to initialize, falling back to keyword search: %s", e)
        _chroma_client = None
        _chroma_collection = None
        VECTOR_SEARCH_AVAILABLE = False


_init_vector_store_module()


def read_text_file(file_path: str, file_ext: str) -> str:
    """读取文件内容（支持 txt/md/pdf/docx/doc，其他格式尝试按 UTF-8 文本读取）"""
    try:
        if file_ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif file_ext == ".pdf":
            try:
                import PyPDF2
                text_parts = []
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text_parts.append(page.extract_text() or "")
                return "\n\n".join(text_parts)
            except ImportError:
                logger.warning("PyPDF2 not installed, treating PDF as binary")
                raise ValidationError(f"不支持的文件格式或缺少解析库: {file_ext}")
        elif file_ext in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n\n".join([p.text for p in doc.paragraphs if p.text])
            except ImportError:
                logger.warning("python-docx not installed, cannot read DOCX file")
                raise ValidationError(f"不支持的文件格式或缺少解析库: {file_ext}")
        else:
            # Fallback: try to read as UTF-8 text
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        logger.error("Failed to read file %s: %s", file_path, e)
        raise FileError(f"读取文件失败：{e}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将文本按段落分块，带重叠窗口"""
    chunks = []
    paragraphs = re.split(r"\n\s*\n", text)
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap:] + "\n\n" + para if overlap > 0 else para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def simple_search(query: str, chunks: list[str], top_k: int = 5) -> list[tuple[int, float, str]]:
    """简单的关键词搜索（基于字符重叠度，不依赖向量数据库）"""
    query_chars = set(query.lower())
    results = []
    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        score = sum(1 for c in query_chars if c in chunk_lower) / len(query_chars) if query_chars else 0
        for word in re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}", query.lower()):
            if word in chunk_lower:
                score += 0.2
        if score > 0:
            results.append((i, min(score, 1.0), chunk))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._chunks_cache: dict[int, list[str]] = {}
        os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
        os.makedirs("./data/chroma_db", exist_ok=True)
        # Attempt to re-initialize vector store in case it failed at import
        # but dependencies have since become available (e.g. installed at runtime)
        if not VECTOR_SEARCH_AVAILABLE:
            _init_vector_store_module()

    # ------------------------------------------------------------------
    # Vector store helpers
    # ------------------------------------------------------------------

    def _init_vector_store(self) -> bool:
        """(Re-)initialize the ChromaDB vector store connection.

        Returns True if vector search is available after this call.
        Safe to call multiple times; will re-attempt initialization if it previously failed.
        """
        global VECTOR_SEARCH_AVAILABLE
        if not VECTOR_SEARCH_AVAILABLE:
            _init_vector_store_module()
        return VECTOR_SEARCH_AVAILABLE

    def _embed_and_index(self, doc_id: int, chunks: list[str], filename: str, brand: str = "") -> None:
        """Add document chunks to the ChromaDB vector store.

        Each chunk gets an ID of the form ``doc{doc_id}_chunk{i}`` and metadata
        containing doc_id, filename, brand, and chunk_index.

        Silently returns if vector search is unavailable; logs a warning on failure.
        """
        if not VECTOR_SEARCH_AVAILABLE or _chroma_collection is None:
            return
        if not chunks:
            return
        try:
            ids = [f"doc{doc_id}_chunk{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "doc_id": str(doc_id),
                    "filename": filename,
                    "brand": brand or "",
                    "chunk_index": str(i),
                }
                for i in range(len(chunks))
            ]
            _chroma_collection.add(ids=ids, documents=chunks, metadatas=metadatas)
            logger.info("Indexed doc %d with %d chunks to vector store", doc_id, len(chunks))
        except Exception as e:
            logger.warning("Failed to index doc %d in vector store: %s", doc_id, e)

    def _delete_from_vector_store(self, doc_id: int) -> None:
        """Remove all chunks belonging to ``doc_id`` from the ChromaDB collection."""
        if not VECTOR_SEARCH_AVAILABLE or _chroma_collection is None:
            return
        try:
            _chroma_collection.delete(where={"doc_id": str(doc_id)})
            logger.info("Deleted doc %d chunks from vector store", doc_id)
        except Exception as e:
            logger.warning("Failed to delete doc %d from vector store: %s", doc_id, e)

    async def _reindex_all(self) -> dict[str, Any]:
        """Rebuild the entire ChromaDB vector index from all documents in the database.

        This deletes the existing collection, re-creates it, and re-indexes every
        document. Useful for initial setup after installing chromadb or after
        a schema change.

        Returns a dict with counts of docs and chunks indexed.
        """
        global _chroma_collection
        result = await self._db.execute(select(KnowledgeDoc))
        docs = list(result.scalars().all())

        total_docs = 0
        total_chunks = 0

        if not self._init_vector_store() or _chroma_collection is None or _chroma_client is None:
            logger.warning("Cannot reindex: vector search not available")
            return {"indexed_docs": 0, "indexed_chunks": 0, "available": False}

        try:
            # Delete and recreate the collection to start fresh
            try:
                _chroma_client.delete_collection(name="knowledge_chunks")
            except Exception:
                pass  # collection may not exist yet
            from chromadb.utils import embedding_functions
            _embedding_function = embedding_functions.DefaultEmbeddingFunction()
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="knowledge_chunks",
                embedding_function=_embedding_function,
                metadata={"hnsw:space": "cosine"},
            )

            for doc in docs:
                # Re-read full text from file if available
                text = doc.content or ""
                if doc.file_path and os.path.exists(doc.file_path):
                    ext = f".{doc.file_type}" if doc.file_type else ".txt"
                    try:
                        text = read_text_file(doc.file_path, ext)
                    except Exception:
                        text = doc.content or ""
                chunks = chunk_text(text)
                if chunks:
                    self._embed_and_index(doc.id, chunks, doc.filename, doc.brand or "")
                    self._chunks_cache[doc.id] = chunks
                    total_docs += 1
                    total_chunks += len(chunks)

            logger.info("Reindex complete: %d docs / %d chunks", total_docs, total_chunks)
            return {
                "indexed_docs": total_docs,
                "indexed_chunks": total_chunks,
                "available": True,
            }
        except Exception as e:
            logger.error("Reindex failed: %s", e)
            return {"indexed_docs": total_docs, "indexed_chunks": total_chunks, "available": True, "error": str(e)}

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------

    async def upload_document(
        self, filename: str, content_bytes: bytes, brand: str = ""
    ) -> KnowledgeDoc:
        ext = Path(filename).suffix.lower()
        allowed = settings.allowed_extensions_list
        if ext not in allowed:
            raise FileError(f"不支持的文件类型：{ext}，支持：{allowed}")
        if len(content_bytes) > settings.MAX_UPLOAD_SIZE:
            raise FileError(f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")

        # Compute content hash and check for duplicates BEFORE saving to disk
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        existing = await self._db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            raise ValidationError("该文件已存在于知识库中（内容重复）")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = os.path.basename(filename)
        safe_name = f"{ts}_{basename}"
        file_path = os.path.join(settings.KNOWLEDGE_DIR, safe_name)
        os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content_bytes)

        text_content = read_text_file(file_path, ext)
        if not text_content or not text_content.strip():
            raise ValidationError("文件内容为空或无法解析，请检查文件是否有效")
        chunks = chunk_text(text_content)

        doc = KnowledgeDoc(
            filename=filename,
            file_path=file_path,
            content=text_content[:50000],
            content_hash=content_hash,
            file_type=ext.lstrip("."),
            brand=brand,
            chunk_count=len(chunks),
        )
        self._db.add(doc)
        await self._db.flush()
        self._chunks_cache[doc.id] = chunks
        # Embed and index into ChromaDB (no-op if vector search unavailable)
        self._embed_and_index(doc.id, chunks, filename, brand)
        logger.info("Knowledge doc uploaded: id=%s chunks=%d type=%s", doc.id, len(chunks), ext)
        return doc

    async def get_documents(self, brand: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        query = select(KnowledgeDoc)
        count_query = select(func.count(KnowledgeDoc.id))
        if brand:
            query = query.where(KnowledgeDoc.brand == brand)
            count_query = count_query.where(KnowledgeDoc.brand == brand)
        total = (await self._db.execute(count_query)).scalar() or 0
        query = query.order_by(KnowledgeDoc.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def delete_document(self, doc_id: int) -> bool:
        obj = await self._db.get(KnowledgeDoc, doc_id)
        if obj:
            try:
                if os.path.exists(obj.file_path):
                    os.remove(obj.file_path)
            except OSError:
                pass
            # Remove vector store chunks
            self._delete_from_vector_store(doc_id)
            await self._db.delete(obj)
            await self._db.flush()
            self._chunks_cache.pop(doc_id, None)
            return True
        return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        brand: str = "",
        top_k: int = 5,
        search_mode: str = "vector",
    ) -> list[dict[str, Any]]:
        """搜索知识库。

        Args:
            query: 查询文本。
            brand: 可选品牌过滤（空字符串表示不过滤）。
            top_k: 返回的最大结果数。
            search_mode: 搜索模式：
                - ``"vector"`` (default): 使用 ChromaDB 向量语义搜索。
                - ``"keyword"``: 使用关键词匹配搜索，不依赖向量数据库。
                - ``"hybrid"``: 合并向量和关键词结果，按分数排序去重。

        Returns:
            结果列表，每项为 dict，包含 doc_id, filename, content, score, search_type。
        """
        # ---- Vector search path ----
        if search_mode in ("vector", "hybrid") and VECTOR_SEARCH_AVAILABLE and _chroma_collection is not None:
            try:
                where_filter: dict[str, Any] | None = None
                if brand:
                    where_filter = {"brand": brand}

                # Request extra results to have room after dedup; cap at 20 to avoid overhead
                n_fetch = min(top_k * 3, 20)
                results = _chroma_collection.query(
                    query_texts=[query],
                    n_results=n_fetch,
                    where=where_filter,
                )

                vec_results: list[dict[str, Any]] = []
                if results and results.get("documents") and results["documents"][0]:
                    for doc, meta, dist in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    ):
                        # ChromaDB returns cosine distance (0 = identical); convert to similarity score
                        score = max(0.0, 1.0 - dist)
                        vec_results.append({
                            "doc_id": int(meta.get("doc_id", 0)),
                            "filename": meta.get("filename", ""),
                            "content": doc,
                            "score": round(score, 3),
                            "search_type": "vector",
                        })

                if search_mode == "vector":
                    if vec_results:
                        return vec_results[:top_k]
                    # 向量搜索无结果时回退到关键词搜索（文档可能尚未索引到向量库）
                    logger.info("Vector search returned no results, falling back to keyword search")
                    return await self._keyword_search(query, brand, top_k)

                # ---- Hybrid mode: merge with keyword results ----
                keyword_results = await self._keyword_search(query, brand, top_k)
                seen: set[tuple[int, str]] = set()
                merged: list[dict[str, Any]] = []
                for r in vec_results + keyword_results:
                    # Use doc_id + content prefix as dedup key
                    key = (r["doc_id"], r["content"][:80])
                    if key not in seen:
                        seen.add(key)
                        merged.append(r)
                merged.sort(key=lambda x: x["score"], reverse=True)
                return merged[:top_k]

            except Exception as e:
                logger.warning("Vector search failed, falling back to keyword: %s", e)

        # ---- Keyword search (fallback / explicit mode) ----
        return await self._keyword_search(query, brand, top_k)

    async def _keyword_search(
        self, query: str, brand: str = "", top_k: int = 5
    ) -> list[dict[str, Any]]:
        """关键词搜索：优先使用 SQL LIKE 过滤，回退到全量匹配。"""
        # 先用 SQL LIKE 过滤包含查询词的文档，避免全量加载
        # 转义用户输入中的 LIKE 通配符（%、_、\），防止通配符注入；使用 backslash 作为 escape 字符
        escaped_query = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{escaped_query}%"
        stmt = select(KnowledgeDoc)
        if brand:
            stmt = stmt.where(KnowledgeDoc.brand == brand)
        # 尝试 SQL LIKE 过滤（仅对 content 字段有效），显式声明 escape 字符
        filtered_stmt = stmt.where(KnowledgeDoc.content.like(like_pattern, escape="\\"))
        filtered_result = await self._db.execute(filtered_stmt)
        docs = list(filtered_result.scalars().all())

        # 如果 LIKE 过滤结果为空，回退到全量查询（可能是文件名匹配或缓存内容）
        if not docs:
            full_result = await self._db.execute(stmt)
            docs = list(full_result.scalars().all())

        all_chunks: list[tuple[int, str, str]] = []  # (doc_id, filename, chunk)
        for doc in docs[:50]:  # 限制最多处理 50 个文档，避免内存溢出
            if doc.id in self._chunks_cache:
                chunks = self._chunks_cache[doc.id]
            else:
                text = doc.content or ""
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        text = read_text_file(
                            doc.file_path,
                            f".{doc.file_type}" if doc.file_type else ".txt",
                        )
                    except Exception:
                        text = doc.content or ""
                chunks = chunk_text(text)
                self._chunks_cache[doc.id] = chunks
            for chunk in chunks:
                all_chunks.append((doc.id, doc.filename, chunk))

        chunk_texts = [c[2] for c in all_chunks]
        results = simple_search(query, chunk_texts, top_k=top_k)
        return [
            {
                "doc_id": all_chunks[idx][0],
                "filename": all_chunks[idx][1],
                "content": chunk,
                "score": round(score, 3),
                "search_type": "keyword",
            }
            for idx, score, chunk in results
        ]

    async def get_context_for_query(
        self,
        query: str,
        brand: str = "",
        top_k: int = 3,
        search_mode: str = "vector",
    ) -> str:
        """获取相关上下文文本（用于注入生成 Prompt）。

        Args:
            query: 查询文本。
            brand: 可选品牌过滤。
            top_k: 检索片段数。
            search_mode: 传递给 search() 的搜索模式 (vector/keyword/hybrid)。
        """
        results = await self.search(query, brand, top_k, search_mode)
        if not results:
            return ""
        parts = []
        for r in results:
            parts.append(f"【来自 {r['filename']}】\n{r['content']}")
        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # 知识库统计与扩展性监控
    # ------------------------------------------------------------------

    # 嵌入式 ChromaDB 的推荐文档上限（超过此值建议迁移到独立向量数据库服务）
    _RECOMMENDED_DOC_LIMIT = 100_000

    async def get_knowledge_stats(self) -> dict[str, Any]:
        """获取知识库规模统计信息，用于扩展性评估与容量监控。

        返回内容包括：
        - ``doc_count``：知识库文档总数（数据库 knowledge_docs 表行数）。
        - ``total_chunks``：所有文档的分块总数（sum of chunk_count）。
        - ``vector_search_available``：向量搜索是否可用（ChromaDB 是否已初始化）。
        - ``vector_store_count``：ChromaDB 向量集合中的条目数（不可用时为 None）。
        - ``storage_dir_size_bytes``：ChromaDB 存储目录大小（字节）。
        - ``storage_dir_path``：ChromaDB 存储目录路径。
        - ``recommended_doc_limit``：推荐文档上限（100,000）。
        - ``approaching_limit``：文档数是否接近推荐上限（达到 80%）。
        - ``brands``：各品牌的文档数分布。

        Returns:
            包含上述统计信息的字典。
        """
        # 文档总数与分块总数
        count_result = await self._db.execute(
            select(func.count(KnowledgeDoc.id))
        )
        doc_count = count_result.scalar() or 0

        chunks_result = await self._db.execute(
            select(func.sum(KnowledgeDoc.chunk_count))
        )
        total_chunks = chunks_result.scalar() or 0

        # 向量存储条目数
        vector_store_count: Optional[int] = None
        if VECTOR_SEARCH_AVAILABLE and _chroma_collection is not None:
            try:
                vector_store_count = _chroma_collection.count()
            except Exception as e:
                logger.warning("Failed to get ChromaDB collection count: %s", e)
                vector_store_count = None

        # 存储目录大小
        storage_dir = os.path.abspath("./data/chroma_db")
        storage_dir_size = _get_directory_size(storage_dir)

        # 各品牌文档分布
        brand_result = await self._db.execute(
            select(
                KnowledgeDoc.brand,
                func.count(KnowledgeDoc.id),
            )
            .group_by(KnowledgeDoc.brand)
        )
        brands: dict[str, int] = {}
        for brand_name, cnt in brand_result.all():
            brands[brand_name or "(未指定)"] = cnt

        approaching_limit = doc_count >= int(self._RECOMMENDED_DOC_LIMIT * 0.8)

        return {
            "doc_count": doc_count,
            "total_chunks": total_chunks,
            "vector_search_available": VECTOR_SEARCH_AVAILABLE,
            "vector_store_count": vector_store_count,
            "storage_dir_size_bytes": storage_dir_size,
            "storage_dir_path": storage_dir,
            "recommended_doc_limit": self._RECOMMENDED_DOC_LIMIT,
            "approaching_limit": approaching_limit,
            "brands": brands,
        }
