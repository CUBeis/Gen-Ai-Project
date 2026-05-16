"""
app/rag/embeddings/cohere_embedder.py
─────────────────────────────────────
Cohere multilingual embeddings — matches the Rag/chroma_db index.
"""
from __future__ import annotations

import time
from typing import Optional

import cohere
import structlog

from app.core.config import settings
from app.core.exceptions import EmbeddingServiceError

logger = structlog.get_logger(__name__)


class CohereEmbedder:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        key = api_key or settings.COHERE_API_KEY
        if not key:
            raise EmbeddingServiceError(detail="COHERE_API_KEY is required for medical RAG retrieval.")
        self._client = cohere.Client(key)
        self._model = model or settings.COHERE_EMBEDDING_MODEL

    def embed_query(self, query: str) -> list[float]:
        return self._embed([query], input_type="search_query")[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, input_type="search_document")

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.embed(
                    texts=texts,
                    model=self._model,
                    input_type=input_type,
                )
                return response.embeddings
            except Exception as exc:
                if attempt < max_retries - 1:
                    logger.warning("cohere_embed.retry", attempt=attempt + 1, error=str(exc))
                    time.sleep(2)
                else:
                    raise EmbeddingServiceError(detail=f"Cohere embed failed: {exc}") from exc
        return []
