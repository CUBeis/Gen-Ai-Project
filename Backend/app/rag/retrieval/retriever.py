"""
app/rag/retrieval/retriever.py
───────────────────────────────
ChromaDB retriever — executes vector similarity searches against both
clinical knowledge and patient episodic memory collections.

Critical design principle — patient isolation:
  Every query against patient_memory MUST include
  `where={"patient_id": patient_id}` as a pre-filter.
  This is enforced structurally — you cannot call search_patient_memory()
  without providing a patient_id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.core.config import settings
from app.rag.embeddings.local_embedder import LocalEmbedder

logger = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    """One retrieved chunk with its relevance score and provenance."""
    text:            str
    source:          str
    page:            Optional[int]
    relevance_score: float
    doc_type:        str = "unknown"
    language:        str = "en"
    metadata:        dict = field(default_factory=dict)


class ClinicalRetriever:
    """
    Retrieves relevant chunks from ChromaDB for the RAG pipeline.
    Instantiated once at app startup. Thread-safe.
    """

    def __init__(self, embedder: Optional[LocalEmbedder] = None) -> None:
        self._embedder     = embedder or LocalEmbedder()
        self._chroma_path  = settings.CHROMA_PATH
        self._clinical_col = settings.CHROMA_CLINICAL_COLLECTION
        self._memory_col   = settings.CHROMA_MEMORY_COLLECTION
        self._client       = None   # lazy-loaded

    # ── Clinical knowledge ─────────────────────────────────────────────────────
    async def search_clinical(
        self,
        query: str,
        top_k: Optional[int] = None,
        language_filter: Optional[str] = None,
        doc_type_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Embed query text and search the clinical_knowledge collection."""
        embedding = await self._embedder.aembed_single(query)
        return await self.search_clinical_by_vector(
            embedding, top_k, language_filter, doc_type_filter
        )

    async def search_clinical_by_vector(
        self,
        embedding: list[float],
        top_k: Optional[int] = None,
        language_filter: Optional[str] = None,
        doc_type_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search using a pre-computed embedding (avoids re-embedding the same query)."""
        k = top_k or settings.RAG_TOP_K
        where_filter = self._build_where(language=language_filter, doc_type=doc_type_filter)

        try:
            col = self._get_collection(self._clinical_col)
            count = self._safe_count(col)
            if count == 0:
                return []

            kwargs: dict = {
                "query_embeddings": [embedding],
                "n_results": min(k, count),
                "include": ["documents", "metadatas", "distances"],
            }
            if where_filter:
                kwargs["where"] = where_filter

            return self._parse(col.query(**kwargs))

        except Exception as exc:
            logger.warning("retriever.clinical_failed", error=str(exc))
            return []

    # ── Patient episodic memory ────────────────────────────────────────────────
    async def search_patient_memory(
        self,
        query: str,
        patient_id: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Embed and search the patient_memory collection for one patient."""
        embedding = await self._embedder.aembed_single(query)
        return await self.search_patient_memory_by_vector(embedding, patient_id, top_k)

    async def search_patient_memory_by_vector(
        self,
        embedding: list[float],
        patient_id: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Search using a pre-computed embedding. patient_id is MANDATORY."""
        try:
            col   = self._get_collection(self._memory_col)
            where = {"patient_id": patient_id}
            count = self._safe_count(col, where=where)
            if count == 0:
                return []

            results = col.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count),
                where=where,                       # ← enforces patient isolation
                include=["documents", "metadatas", "distances"],
            )
            return self._parse(results)

        except Exception as exc:
            logger.warning("retriever.memory_failed",
                           patient_id=patient_id, error=str(exc))
            return []

    # ── Admin ──────────────────────────────────────────────────────────────────
    def collection_stats(self) -> dict:
        try:
            return {
                "clinical_knowledge_chunks": self._get_collection(self._clinical_col).count(),
                "patient_memory_facts":      self._get_collection(self._memory_col).count(),
            }
        except Exception as exc:
            logger.warning("retriever.stats_failed", error=str(exc))
            return {}

    def delete_patient_memory(self, patient_id: str) -> int:
        """Delete all memory vectors for a patient (GDPR erasure)."""
        try:
            col     = self._get_collection(self._memory_col)
            results = col.get(where={"patient_id": patient_id})
            ids     = results.get("ids", [])
            if ids:
                col.delete(ids=ids)
            logger.info("retriever.patient_memory_deleted",
                        patient_id=patient_id, count=len(ids))
            return len(ids)
        except Exception as exc:
            logger.error("retriever.delete_failed",
                         patient_id=patient_id, error=str(exc))
            return 0

    # ── Internals ──────────────────────────────────────────────────────────────
    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._chroma_path)
        return self._client

    def _get_collection(self, name: str):
        return self._get_client().get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _safe_count(collection, where: Optional[dict] = None) -> int:
        try:
            if where:
                return len(collection.get(where=where, limit=10_000).get("ids", []))
            return collection.count()
        except Exception:
            return 0

    @staticmethod
    def _parse(results: dict) -> list[SearchResult]:
        chunks: list[SearchResult] = []
        docs      = results.get("documents", [[]])[0]
        metas     = results.get("metadatas",  [[]])[0]
        distances = results.get("distances",  [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            if not doc or not doc.strip():
                continue
            chunks.append(SearchResult(
                text=doc.strip(),
                source=meta.get("source", "unknown"),
                page=meta.get("page"),
                relevance_score=round(float(1.0 - dist), 4),
                doc_type=meta.get("doc_type", "unknown"),
                language=meta.get("language", "en"),
                metadata=meta,
            ))

        return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)

    @staticmethod
    def _build_where(
        language: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> Optional[dict]:
        conditions = []
        if language:
            conditions.append({"language": {"$eq": language}})
        if doc_type:
            conditions.append({"doc_type": {"$eq": doc_type}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
