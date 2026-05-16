"""
Backend RAG package — synced with the standalone Rag/ folder at repo root.

Modules:
  clinical_config     — paths to Rag/data and Rag/chroma_db
  retrieval/          — hybrid + legacy retrievers
  embeddings/         — Cohere (medical index) + local sidecar
  multilingual/       — auto-translate to English for retrieval
  pipeline.py         — PDF/CSV ingestion into clinical_knowledge
"""
from app.rag.clinical_config import COLLECTION_NAME, CHROMA_DB_PATH, RAG_ROOT

__all__ = ["COLLECTION_NAME", "CHROMA_DB_PATH", "RAG_ROOT"]
