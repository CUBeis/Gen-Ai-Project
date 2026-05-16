"""
app/rag/retrieval/reranker.py
──────────────────────────────
Cross-encoder reranker — second-stage retrieval filter.

Why two stages:
  Stage 1 (retriever.py): bi-encoder similarity search — fast but approximate.
    Retrieves top-K candidates (default 10) using pre-computed vectors.
  Stage 2 (this file):    cross-encoder scoring — slower but highly accurate.
    Re-scores every (query, chunk) pair jointly and keeps only top-N (default 5).

The cross-encoder reads the query AND the chunk text together, giving it full
attention across both — dramatically better than the bi-encoder's dot product.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - 22M parameters — runs in ~20ms per pair on CPU
  - Optimised for passage relevance (not semantic similarity)
  - Downloadable from HuggingFace; cached in ~/.cache/huggingface/

Lazy loading strategy:
  The CrossEncoder is ~85 MB. It's loaded on the first rerank() call and
  cached for the lifetime of the process. FastAPI startup is not blocked.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.rag.retrieval.retriever import SearchResult

logger = structlog.get_logger(__name__)

# Default model — change to a larger model for better accuracy if CPU budget allows
_DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """
    Reranks a list of retrieved chunks using a cross-encoder model.

    Usage:
        reranker = CrossEncoderReranker()
        top_chunks = reranker.rerank(query, chunks, top_n=5)

    The model is lazy-loaded on first use.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model      = None   # lazy-loaded

    def rerank(
        self,
        query:   str,
        chunks:  list["SearchResult"],
        top_n:   int | None = None,
    ) -> list["SearchResult"]:
        """
        Re-score chunks against the query and return the top_n highest-scoring.

        Args:
            query  : The reformulated search query.
            chunks : SearchResult list from ClinicalRetriever (already sorted by relevance).
            top_n  : How many to keep. Defaults to settings.RAG_RERANK_TOP_N.

        Returns:
            Subset of chunks re-sorted by cross-encoder score, highest first.
            Falls back to relevance_score ordering if the model fails.
        """
        from app.core.config import settings
        n = top_n or settings.RAG_RERANK_TOP_N

        if not chunks:
            return []

        # If fewer chunks than top_n, skip reranking (no benefit)
        if len(chunks) <= n:
            return chunks

        model = self._get_model()
        if model is None:
            # Model failed to load — fall back to bi-encoder scores
            logger.warning("reranker.model_unavailable_using_fallback")
            return chunks[:n]

        try:
            pairs  = [(query, chunk.text) for chunk in chunks]
            scores = model.predict(pairs, show_progress_bar=False)

            for chunk, score in zip(chunks, scores):
                chunk.metadata["rerank_score"] = float(score)

            reranked = sorted(chunks, key=lambda c: c.metadata.get("rerank_score", 0.0), reverse=True)

            logger.debug(
                "reranker.done",
                input_chunks=len(chunks),
                kept=n,
                top_score=round(reranked[0].metadata.get("rerank_score", 0), 3) if reranked else None,
            )
            return reranked[:n]

        except Exception as exc:
            logger.warning("reranker.failed_using_fallback", error=str(exc))
            return chunks[:n]

    def warmup(self) -> bool:
        """
        Pre-load the model during application startup (optional).
        Returns True if successfully loaded.

        Call this from the lifespan function in main.py if you want
        zero-latency on the first RAG query.
        """
        model = self._get_model()
        return model is not None

    def _get_model(self):
        """Lazy-load and cache the CrossEncoder model."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
            logger.info("reranker.loading_model", model=self._model_name)
            self._model = CrossEncoder(self._model_name)
            logger.info("reranker.model_loaded", model=self._model_name)
            return self._model
        except Exception as exc:
            logger.error("reranker.model_load_failed",
                         model=self._model_name, error=str(exc))
            return None
