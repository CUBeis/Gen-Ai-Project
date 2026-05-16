"""
embedding_service/model_loader.py
──────────────────────────────────
Model management and embedding generation.
"""
import asyncio
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class ModelLoader:
    """Load and cache embedding models for on-demand generation."""

    def __init__(self) -> None:
        self.model = None
        self.model_name: Optional[str] = None

    async def load_model(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Load embedding model from HuggingFace."""
        if self.model_name == model_name:
            return  # Already loaded

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("model_loader.loading", model_name=model_name)

            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(model_name),
            )
            self.model_name = model_name

            logger.info("model_loader.loaded", model_name=model_name)

        except Exception as exc:
            logger.error("model_loader.failed", error=str(exc))
            raise

    async def embed(self, text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
        """Generate embedding for a single text."""
        await self.load_model(model_name)

        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.model.encode(text, convert_to_tensor=False),
        )

        return embedding.tolist() if hasattr(embedding, "tolist") else embedding

    async def embed_batch(
        self, texts: list[str], model_name: str = "all-MiniLM-L6-v2"
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        await self.load_model(model_name)

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_tensor=False),
        )

        # Convert numpy array to list of lists
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [e.tolist() if hasattr(e, "tolist") else e for e in embeddings]
