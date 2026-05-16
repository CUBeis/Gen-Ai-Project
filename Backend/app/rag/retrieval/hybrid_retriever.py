"""
app/rag/retrieval/hybrid_retriever.py
─────────────────────────────────────
Hybrid retrieval pipeline synced from Rag/retrieval.py:
  Semantic (Cohere) + BM25 → MMR → Cohere rerank
"""
from __future__ import annotations

import time
from typing import Optional

import chromadb
import numpy as np
import structlog
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.rag.embeddings.cohere_embedder import CohereEmbedder
from app.rag.retrieval.retriever import SearchResult

logger = structlog.get_logger(__name__)


class HybridClinicalRetriever:
    """Retrieves from the medical_rag ChromaDB collection built by the Rag/ pipeline."""

    def __init__(self) -> None:
        self._embedder = CohereEmbedder()
        self._chroma_path = settings.rag_chroma_path
        self._collection_name = settings.RAG_MEDICAL_COLLECTION
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    def _load_collection(self):
        if self._collection is None:
            self._client = chromadb.PersistentClient(
                path=self._chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_collection(self._collection_name)
        return self._collection

    def retrieve(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        entity_type: Optional[str] = None,
        source_type: Optional[str] = None,
        use_hybrid: bool = True,
        use_mmr: bool = True,
        use_rerank: bool = True,
    ) -> list[SearchResult]:
        top_k = top_k or settings.RAG_RERANK_TOP_N
        collection = self._load_collection()
        cohere = self._embedder._client

        if use_hybrid:
            chunks = self._hybrid_retrieve(
                query, collection, top_k=settings.RAG_TOP_K,
                entity_type=entity_type, source_type=source_type,
            )
        else:
            chunks = self._semantic_retrieve(
                query, collection, top_k=settings.RAG_TOP_K,
                entity_type=entity_type, source_type=source_type,
            )

        if use_mmr and chunks:
            query_embedding = self._embedder.embed_query(query)
            chunks = self._mmr(chunks, query_embedding, top_k=top_k)

        if use_rerank and chunks:
            chunks = self._rerank(query, chunks, cohere, top_k=top_k)

        return [self._to_search_result(c) for c in chunks[:top_k]]

    def _semantic_retrieve(
        self, query, collection, top_k, entity_type=None, source_type=None,
    ) -> list[dict]:
        query_embedding = self._embedder.embed_query(query)
        where = self._build_filter(entity_type, source_type)
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances", "embeddings"],
        }
        if where:
            kwargs["where"] = where
        results = collection.query(**kwargs)
        return self._parse_raw(results)

    def _hybrid_retrieve(
        self, query, collection, top_k, entity_type=None, source_type=None,
    ) -> list[dict]:
        alpha = settings.RAG_HYBRID_ALPHA
        semantic_chunks = self._semantic_retrieve(
            query, collection, top_k=top_k * 2,
            entity_type=entity_type, source_type=source_type,
        )
        if not semantic_chunks:
            return []

        corpus = [c["text"].lower().split() for c in semantic_chunks]
        bm25 = BM25Okapi(corpus)
        bm25_scores = bm25.get_scores(query.lower().split())
        bm25_max = max(bm25_scores) if max(bm25_scores) > 0 else 1
        bm25_norm = bm25_scores / bm25_max

        for i, chunk in enumerate(semantic_chunks):
            chunk["bm25_score"] = round(float(bm25_norm[i]), 4)
            chunk["hybrid_score"] = round(
                alpha * chunk["score"] + (1 - alpha) * bm25_norm[i], 4
            )

        semantic_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return semantic_chunks[:top_k]

    def _mmr(self, chunks: list[dict], query_embedding: list[float], top_k: int) -> list[dict]:
        lambda_param = settings.RAG_MMR_LAMBDA
        if not chunks:
            return []

        query_vec = np.array(query_embedding).reshape(1, -1)
        candidates = list(chunks)
        selected: list[dict] = []

        while len(selected) < top_k and candidates:
            relevance_scores = []
            for c in candidates:
                doc_vec = np.array(c["embedding"]).reshape(1, -1)
                sim = float(
                    np.dot(query_vec, doc_vec.T)
                    / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-9)
                )
                relevance_scores.append(sim)

            if not selected:
                redundancy_scores = [0.0] * len(candidates)
            else:
                redundancy_scores = []
                for c in candidates:
                    doc_vec = np.array(c["embedding"]).reshape(1, -1)
                    max_sim = max(
                        float(
                            np.dot(np.array(s["embedding"]).reshape(1, -1), doc_vec.T)
                            / (np.linalg.norm(s["embedding"]) * np.linalg.norm(doc_vec) + 1e-9)
                        )
                        for s in selected
                    )
                    redundancy_scores.append(max_sim)

            mmr_scores = [
                lambda_param * rel - (1 - lambda_param) * red
                for rel, red in zip(relevance_scores, redundancy_scores)
            ]
            best_idx = int(np.argmax(mmr_scores))
            selected.append(candidates.pop(best_idx))

        return selected

    def _rerank(self, query: str, chunks: list[dict], cohere_client, top_k: int) -> list[dict]:
        if not chunks:
            return []
        documents = [c["text"] for c in chunks]
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = cohere_client.rerank(
                    model=settings.COHERE_RERANK_MODEL,
                    query=query,
                    documents=documents,
                    top_n=top_k,
                )
                break
            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise exc

        reranked = []
        for i, result in enumerate(response.results):
            chunk = chunks[result.index].copy()
            chunk["rerank_score"] = round(result.relevance_score, 4)
            chunk["rank"] = i + 1
            reranked.append(chunk)
        return reranked

    @staticmethod
    def _build_filter(entity_type: Optional[str], source_type: Optional[str]) -> Optional[dict]:
        conditions = []
        if entity_type:
            conditions.append({"entity_type": {"$eq": entity_type}})
        if source_type:
            conditions.append({"source_type": {"$eq": source_type}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _parse_raw(results: dict) -> list[dict]:
        chunks = []
        for i in range(len(results["ids"][0])):
            chunks.append({
                "id": results["ids"][0][i],
                "score": round(1 - results["distances"][0][i], 4),
                "text": results["documents"][0][i],
                "embedding": results["embeddings"][0][i],
                "entity_name": results["metadatas"][0][i].get("entity_name"),
                "entity_type": results["metadatas"][0][i].get("entity_type"),
                "source_type": results["metadatas"][0][i].get("source_type"),
                "url": results["metadatas"][0][i].get("url"),
            })
        return chunks

    @staticmethod
    def _to_search_result(chunk: dict) -> SearchResult:
        return SearchResult(
            text=chunk["text"],
            source=chunk.get("entity_name") or chunk.get("source_type") or "medical_rag",
            page=None,
            relevance_score=chunk.get("rerank_score") or chunk.get("hybrid_score") or chunk.get("score", 0.0),
            doc_type=chunk.get("entity_type", "clinical"),
            language="en",
            metadata={
                "entity_name": chunk.get("entity_name"),
                "entity_type": chunk.get("entity_type"),
                "source_type": chunk.get("source_type"),
                "url": chunk.get("url"),
                "rerank_score": chunk.get("rerank_score"),
            },
        )
