"""
app/rag/clinical_config.py
──────────────────────────
Paths and constants synced from the standalone Rag/ folder at repo root.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings

RAG_ROOT = Path(settings.RAG_PROJECT_PATH)
DATA_DIR = RAG_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DISEASES_DIR = RAW_DATA_DIR / "diseases"
OPENFDA_DIR = RAW_DATA_DIR / "openfda"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHROMA_DB_PATH = Path(settings.rag_chroma_path)
EVALUATION_DIR = RAG_ROOT / "evaluation"

COLLECTION_NAME = settings.RAG_MEDICAL_COLLECTION
CHUNK_SIZE = 512
CHUNK_OVERLAP = 100
BATCH_SIZE = 48
RETRIEVE_TOP_K = settings.RAG_TOP_K
FINAL_TOP_K = settings.RAG_RERANK_TOP_N
