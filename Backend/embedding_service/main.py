"""
embedding_service/main.py
─────────────────────────
Standalone FastAPI service for embedding generation.
Run separately from the main API (port 8001 by default).

Provides a single endpoint: POST /embed
"""
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import structlog
from embedding_service.model_loader import ModelLoader

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Nerve AI Embedding Service",
    version="1.0.0",
    description="Generate embeddings for medical documents and queries",
)

# Load model at startup
model_loader = ModelLoader()


@app.on_event("startup")
async def startup():
    """Load embedding model on service startup."""
    logger.info("embedding_service.startup")
    await model_loader.load_model()
    logger.info("embedding_service.model_loaded")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("embedding_service.shutdown")


class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""
    text: str
    model: str = "all-MiniLM-L6-v2"


class EmbeddingResponse(BaseModel):
    """Response with generated embedding."""
    embedding: list[float]
    model: str
    dimension: int


class BatchEmbeddingRequest(BaseModel):
    """Batch embedding request."""
    texts: list[str]
    model: str = "all-MiniLM-L6-v2"


class BatchEmbeddingResponse(BaseModel):
    """Batch embedding response."""
    embeddings: list[list[float]]
    model: str
    dimension: int


@app.post(
    "/embed",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
)
async def embed_single(request: EmbeddingRequest) -> EmbeddingResponse:
    """Generate embedding for a single text."""
    try:
        embedding = await model_loader.embed(request.text, request.model)
        return EmbeddingResponse(
            embedding=embedding,
            model=request.model,
            dimension=len(embedding),
        )
    except Exception as exc:
        logger.error("embedding.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding generation failed",
        )


@app.post(
    "/embed-batch",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
)
async def embed_batch(request: BatchEmbeddingRequest) -> BatchEmbeddingResponse:
    """Generate embeddings for multiple texts."""
    try:
        embeddings = await model_loader.embed_batch(request.texts, request.model)
        return BatchEmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            dimension=len(embeddings[0]) if embeddings else 0,
        )
    except Exception as exc:
        logger.error("embedding_batch.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch embedding generation failed",
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "embedding"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
