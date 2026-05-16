"""
app/rag/embeddings/local_embedder.py
──────────────────────────────────────
HTTP client for the local embedding sidecar (all-MiniLM-L6-v2).

The model runs as a separate FastAPI process (embedding_service/).
This module is the only file in the main backend that knows the sidecar URL.

Why a sidecar instead of loading the model directly in FastAPI:
  - all-MiniLM-L6-v2 is ~90 MB — loading it in every Uvicorn worker wastes RAM
  - The sidecar loads the model once; all workers share it via HTTP
  - If the sidecar crashes, only embedding calls fail — the rest of the API keeps running
  - Swapping to a GPU embedding model later = change the sidecar only

Provides:
  - sync  embed_batch()  / embed_single()  — for ingestion jobs (called from Celery)
  - async aembed_batch() / aembed_single() — for live RAG queries (called from agents)
  - health_check()                         — used by the ingestion pipeline before jobs
"""
from __future__ import annotations

from typing import Optional

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import EmbeddingServiceError

logger = structlog.get_logger(__name__)

_SINGLE_TIMEOUT = 10.0
_BATCH_TIMEOUT  = 60.0


class LocalEmbedder:
    """
    Sync + async wrapper around the embedding sidecar.

    Usage (async — in agents):
        embedder = LocalEmbedder()
        vector = await embedder.aembed_single("What is the dosage of metformin?")

    Usage (sync — in Celery tasks):
        embedder = LocalEmbedder()
        vectors = embedder.embed_batch(["fact one", "fact two"])
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url        = (base_url or settings.EMBEDDING_SERVICE_URL).rstrip("/")
        self._embed_endpoint  = f"{self._base_url}/embed"
        self._health_endpoint = f"{self._base_url}/health"

    # ── Async interface ────────────────────────────────────────────────────────
    async def aembed_single(self, text: str) -> list[float]:
        """Embed a single text asynchronously. Used in the RAG query path."""
        vectors = await self.aembed_batch([text])
        return vectors[0]

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts asynchronously.
        Auto-batches inputs larger than 500 to respect sidecar memory limits.

        Raises:
            EmbeddingServiceError: If the sidecar is unreachable or errors.
        """
        if not texts:
            return []

        if len(texts) > 500:
            return await self._aembed_batched(texts, batch_size=200)

        try:
            async with httpx.AsyncClient(timeout=_BATCH_TIMEOUT) as client:
                resp = await client.post(
                    self._embed_endpoint,
                    json={"texts": texts, "normalize": True},
                )
                resp.raise_for_status()
                return resp.json()["embeddings"]

        except httpx.TimeoutException as exc:
            logger.error("embedder.timeout", num_texts=len(texts))
            raise EmbeddingServiceError(
                detail="Embedding service timed out. Please try again."
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("embedder.http_error", status=exc.response.status_code)
            raise EmbeddingServiceError(
                detail=f"Embedding service returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("embedder.connection_error", error=str(exc))
            raise EmbeddingServiceError(
                detail="Embedding service is unreachable. Ensure it is running."
            ) from exc

    async def _aembed_batched(self, texts: list[str], batch_size: int = 200) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = await self.aembed_batch(batch)
            all_vectors.extend(vectors)
            logger.debug("embedder.batch_progress",
                         processed=min(i + batch_size, len(texts)), total=len(texts))
        return all_vectors

    # ── Sync interface (Celery / ingestion jobs) ───────────────────────────────
    def embed_single(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Synchronous batch embed — for use in Celery ingestion tasks.
        Raises EmbeddingServiceError if the sidecar is unavailable.
        """
        if not texts:
            return []

        if len(texts) > 500:
            return self._embed_batched(texts, batch_size=200)

        try:
            resp = httpx.post(
                self._embed_endpoint,
                json={"texts": texts, "normalize": True},
                timeout=_BATCH_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]
        except httpx.TimeoutException as exc:
            raise EmbeddingServiceError(detail="Embedding service timed out.") from exc
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            raise EmbeddingServiceError(detail=f"Embedding service error: {exc}") from exc

    def _embed_batched(self, texts: list[str], batch_size: int = 200) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            all_vectors.extend(self.embed_batch(texts[i : i + batch_size]))
        return all_vectors

    # ── Health check ──────────────────────────────────────────────────────────
    def health_check(self) -> bool:
        """Return True if the sidecar is reachable. Called before ingestion jobs."""
        try:
            resp = httpx.get(self._health_endpoint, timeout=5.0)
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def ahealth_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self._health_endpoint)
                return resp.status_code == 200
        except httpx.RequestError:
            return False


# Module-level singleton — import this in agents and tasks
embedder = LocalEmbedder()
