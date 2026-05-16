"""
app/rag/pipeline.py
────────────────────
RAG Ingestion Pipeline — entry point for adding medical documents to ChromaDB.

Wires together: Loader → Chunker → Embedder → ChromaDB write.

Called by:
  - POST /api/v1/admin/ingest  (admin HTTP endpoint)
  - app/tasks/ingestion_tasks.py  (Celery background job)

Supports:
  - PDF and CSV ingestion
  - Raw bytes ingestion (from file uploads)
  - Idempotent re-ingestion (replaces old chunks from the same source)
  - Progress callbacks (Celery task updates)
"""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import structlog

from app.core.config import settings
from app.core.exceptions import DocumentIngestionError, EmbeddingServiceError
from app.rag.embeddings.local_embedder import LocalEmbedder
from app.rag.ingestion.chunker import Chunk, SemanticChunker
from app.rag.ingestion.csv_loader import MedicalCSVLoader
from app.rag.ingestion.pdf_loader import MedicalPDFLoader

logger = structlog.get_logger(__name__)

_EMBED_BATCH_SIZE  = 100   # texts per embedding call
_CHROMA_BATCH_SIZE = 200   # ids per ChromaDB add() call


@dataclass
class IngestionResult:
    source_name:    str
    doc_type:       str
    pages_loaded:   int
    chunks_created: int
    chunks_stored:  int
    chunks_skipped: int
    errors:         list[str] = field(default_factory=list)
    success:        bool = True


class IngestionPipeline:
    """
    Full document ingestion pipeline.
    Instantiated per job — not a singleton — so each job has clean state.
    """

    def __init__(
        self,
        embedder:    Optional[LocalEmbedder]   = None,
        chunker:     Optional[SemanticChunker] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._embedder   = embedder  or LocalEmbedder()
        self._chunker    = chunker   or SemanticChunker()
        self._pdf_loader = MedicalPDFLoader()
        self._csv_loader = MedicalCSVLoader()
        self._progress   = progress_cb or (lambda msg: None)
        self._chroma     = None

    # ── Public: ingest from file path ─────────────────────────────────────────
    async def ingest_file(
        self,
        file_path:        str | Path,
        doc_type:         str = "clinical_guideline",
        source_name:      Optional[str] = None,
        language:         str = "en",
        schema:           str = "auto",
        replace_existing: bool = True,
    ) -> IngestionResult:
        """
        Ingest a single PDF or CSV into clinical_knowledge collection.

        Args:
            file_path       : Absolute path to the file.
            doc_type        : Metadata tag — "clinical_guideline" | "drug_interactions"
                              | "lab_reference" | "patient_leaflet"
            source_name     : Citation label (defaults to filename).
            language        : ISO 639-1 document language.
            schema          : CSV schema hint — passed to MedicalCSVLoader.
            replace_existing: Delete old chunks from this source before writing.
        """
        path = Path(file_path)
        name = source_name or path.name

        self._progress(f"Starting ingestion: {name}")
        logger.info("ingestion.start", source=name, doc_type=doc_type)

        # Guard: embedding sidecar must be reachable before starting
        if not self._embedder.health_check():
            raise EmbeddingServiceError(
                detail="Embedding service is offline. Cannot ingest documents."
            )

        # Step 1 — Load
        try:
            documents = self._load(path, name, doc_type, language, schema)
        except Exception as exc:
            raise DocumentIngestionError(
                detail=f"Failed to load '{name}': {exc}"
            ) from exc

        self._progress(f"Loaded {len(documents)} pages/rows")

        # Step 2 — Chunk
        try:
            chunks = self._chunker.chunk(documents)
        except Exception as exc:
            raise DocumentIngestionError(
                detail=f"Chunking failed for '{name}': {exc}"
            ) from exc

        self._progress(f"Created {len(chunks)} chunks")

        # Step 3 — Optionally replace old chunks from same source
        if replace_existing:
            deleted = self._delete_by_source(name)
            if deleted:
                logger.info("ingestion.replaced_existing",
                            source=name, deleted=deleted)

        # Step 4 — Embed + write to ChromaDB
        result = await self._embed_and_store(chunks, name, doc_type)
        result.pages_loaded = len(documents)

        self._progress(
            f"Done — {result.chunks_stored} stored, {result.chunks_skipped} skipped"
        )
        logger.info(
            "ingestion.complete",
            source=name,
            pages=result.pages_loaded,
            chunks_stored=result.chunks_stored,
            chunks_skipped=result.chunks_skipped,
            errors=len(result.errors),
        )
        return result

    # ── Public: ingest from raw bytes (HTTP upload) ────────────────────────────
    async def ingest_bytes(
        self,
        data:         bytes,
        filename:     str,
        content_type: str,
        doc_type:     str = "clinical_guideline",
        language:     str = "en",
        schema:       str = "auto",
    ) -> IngestionResult:
        """Write bytes to a temp file, delegate to ingest_file(), clean up."""
        suffix = ".pdf" if "pdf" in content_type else ".csv"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        try:
            os.write(tmp_fd, data)
            os.close(tmp_fd)
            return await self.ingest_file(
                file_path=tmp_path,
                doc_type=doc_type,
                source_name=filename,
                language=language,
                schema=schema,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ── Step 1: Route to correct loader ───────────────────────────────────────
    def _load(
        self,
        path:     Path,
        name:     str,
        doc_type: str,
        language: str,
        schema:   str,
    ):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._pdf_loader.load(path, name, doc_type, language)
        elif suffix in (".csv", ".tsv"):
            return self._csv_loader.load(
                path, schema=schema, source_name=name, language=language
            )
        else:
            raise DocumentIngestionError(
                detail=f"Unsupported file type '{suffix}'. Accepted: .pdf, .csv, .tsv"
            )

    # ── Step 4: Embed + write ──────────────────────────────────────────────────
    async def _embed_and_store(
        self,
        chunks:      list[Chunk],
        source_name: str,
        doc_type:    str,
    ) -> IngestionResult:
        result = IngestionResult(
            source_name=source_name,
            doc_type=doc_type,
            pages_loaded=0,
            chunks_created=len(chunks),
            chunks_stored=0,
            chunks_skipped=0,
        )

        if not chunks:
            return result

        collection = self._get_collection(settings.CHROMA_CLINICAL_COLLECTION)

        for i in range(0, len(chunks), _EMBED_BATCH_SIZE):
            batch = chunks[i : i + _EMBED_BATCH_SIZE]
            texts = [c.text for c in batch]

            # Embed
            try:
                embeddings = self._embedder.embed_batch(texts)
            except EmbeddingServiceError as exc:
                msg = f"Embed failed at chunk {i}: {exc}"
                result.errors.append(msg)
                result.chunks_skipped += len(batch)
                logger.warning("ingestion.embed_failed", batch_start=i, error=str(exc))
                continue

            # Write to ChromaDB in sub-batches
            ids       = [str(uuid.uuid4()) for _ in batch]
            metadatas = [c.metadata for c in batch]

            try:
                for j in range(0, len(batch), _CHROMA_BATCH_SIZE):
                    collection.add(
                        ids=ids[j : j + _CHROMA_BATCH_SIZE],
                        embeddings=embeddings[j : j + _CHROMA_BATCH_SIZE],
                        documents=texts[j : j + _CHROMA_BATCH_SIZE],
                        metadatas=metadatas[j : j + _CHROMA_BATCH_SIZE],
                    )
                result.chunks_stored += len(batch)
            except Exception as exc:
                msg = f"ChromaDB write failed at chunk {i}: {exc}"
                result.errors.append(msg)
                result.chunks_skipped += len(batch)
                logger.error("ingestion.chroma_write_failed", error=msg)

            self._progress(f"Stored {result.chunks_stored}/{len(chunks)} chunks…")

        if result.errors:
            result.success = False

        return result

    # ── ChromaDB helpers ───────────────────────────────────────────────────────
    def _get_chroma(self):
        if self._chroma is None:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        return self._chroma

    def _get_collection(self, name: str):
        return self._get_chroma().get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def _delete_by_source(self, source_name: str) -> int:
        """Remove all chunks previously ingested from this source name."""
        try:
            col     = self._get_collection(settings.CHROMA_CLINICAL_COLLECTION)
            results = col.get(where={"source": source_name})
            ids     = results.get("ids", [])
            if ids:
                col.delete(ids=ids)
            return len(ids)
        except Exception as exc:
            logger.warning("ingestion.delete_failed",
                           source=source_name, error=str(exc))
            return 0
