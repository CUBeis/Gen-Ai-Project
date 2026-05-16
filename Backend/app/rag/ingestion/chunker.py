"""
app/rag/ingestion/chunker.py
─────────────────────────────
Semantic chunker — splits Documents into chunks optimised for RAG retrieval.

Strategy (two-stage):
  1. SemanticChunker (primary)
     Splits text at meaning boundaries using cosine distance between sentence
     embeddings.  Produces variable-length chunks that respect topic coherence.
     Uses the same all-MiniLM-L6-v2 model as the retrieval embedding for
     consistency — a chunk boundary in embedding space = a boundary in retrieval.

  2. RecursiveCharacterTextSplitter (fallback + overflow guard)
     Applied to any chunk that exceeds MAX_CHUNK_CHARS.
     Also used as the sole strategy when the embedding sidecar is unavailable
     (e.g., during offline ingestion jobs).

Why NOT fixed-size chunking:
  A drug interaction note might be 120 words; a clinical guideline paragraph
  might be 800 words.  Splitting by character count splits mid-sentence and
  merges unrelated topics.  Semantic splitting preserves context.

Output metadata added per chunk:
  - chunk_index      : position within the parent document
  - chunk_char_count : character length
  - All parent document metadata is preserved
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.rag.ingestion.pdf_loader import Document

logger = structlog.get_logger(__name__)

# ── Tuning constants ───────────────────────────────────────────────────────────
MAX_CHUNK_CHARS  = 1_200     # Chunks larger than this get split by fallback
MIN_CHUNK_CHARS  = 80        # Chunks smaller than this are discarded
CHUNK_OVERLAP    = 100       # Character overlap between fallback chunks
FALLBACK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass
class Chunk:
    """A single RAG-ready text unit with full metadata."""
    text:     str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.text = self.text.strip()


class SemanticChunker:
    """
    Two-stage chunker: semantic splitting → overflow guard.

    Usage:
        chunker = SemanticChunker()
        chunks = chunker.chunk(documents)
    """

    def __init__(self, embedding_service_url: Optional[str] = None) -> None:
        """
        Args:
            embedding_service_url: Override for the local embedding sidecar URL.
                                   Defaults to settings.EMBEDDING_SERVICE_URL.
        """
        from app.core.config import settings
        self._embed_url  = embedding_service_url or settings.EMBEDDING_SERVICE_URL
        self._splitter   = None    # lazy-loaded (heavy import)
        self._fallback   = self._build_fallback_splitter()

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """
        Chunk a list of Documents into RAG-ready Chunks.

        Args:
            documents: Output from MedicalPDFLoader or MedicalCSVLoader.

        Returns:
            Flat list of Chunk objects with inherited metadata.
        """
        all_chunks: list[Chunk] = []

        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            all_chunks.extend(doc_chunks)

        logger.info(
            "chunker.done",
            input_docs=len(documents),
            output_chunks=len(all_chunks),
        )
        return all_chunks

    def _chunk_document(self, doc: Document) -> list[Chunk]:
        """Split a single Document into Chunks."""
        text = doc.content

        # Try semantic splitting first
        try:
            raw_chunks = self._semantic_split(text)
        except Exception as exc:
            logger.warning(
                "chunker.semantic_failed_using_fallback",
                error=str(exc),
                source=doc.metadata.get("source"),
            )
            raw_chunks = self._fallback_split(text)

        # Apply overflow guard + filter
        final_texts: list[str] = []
        for chunk_text in raw_chunks:
            if len(chunk_text) > MAX_CHUNK_CHARS:
                # Split oversized chunks with the fallback splitter
                final_texts.extend(self._fallback_split(chunk_text))
            else:
                final_texts.append(chunk_text)

        # Filter out tiny fragments
        final_texts = [t.strip() for t in final_texts if len(t.strip()) >= MIN_CHUNK_CHARS]

        # Wrap in Chunk dataclass with metadata
        chunks = []
        for idx, chunk_text in enumerate(final_texts):
            chunks.append(Chunk(
                text=chunk_text,
                metadata={
                    **doc.metadata,
                    "chunk_index":      idx,
                    "chunk_char_count": len(chunk_text),
                    "total_chunks":     len(final_texts),
                },
            ))

        return chunks

    def _semantic_split(self, text: str) -> list[str]:
        """
        Use LangChain SemanticChunker backed by the local embedding sidecar.
        Lazy-loads the splitter on first call.
        """
        splitter = self._get_semantic_splitter()
        # SemanticChunker works on raw text, returns LangChain Documents
        lc_docs = splitter.create_documents([text])
        return [d.page_content for d in lc_docs if d.page_content.strip()]

    def _fallback_split(self, text: str) -> list[str]:
        """Recursive character splitter — always available, no network calls."""
        lc_docs = self._fallback.create_documents([text])
        return [d.page_content for d in lc_docs if d.page_content.strip()]

    def _get_semantic_splitter(self):
        """Lazy-load the semantic chunker (requires network call to sidecar on init)."""
        if self._splitter is not None:
            return self._splitter

        from langchain_experimental.text_splitter import SemanticChunker as LCSemanticChunker
        from langchain_community.embeddings import HuggingFaceEmbeddings

        # We route through our local sidecar rather than calling HuggingFace directly.
        # But LangChain's SemanticChunker needs a LangChain embeddings object.
        # We use a thin adapter that calls the sidecar via HTTP.
        embeddings = _SidecarEmbeddingsAdapter(self._embed_url)

        self._splitter = LCSemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95,  # split when cosine distance > 95th percentile
        )
        return self._splitter

    @staticmethod
    def _build_fallback_splitter():
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        return RecursiveCharacterTextSplitter(
            chunk_size=MAX_CHUNK_CHARS,
            chunk_overlap=CHUNK_OVERLAP,
            separators=FALLBACK_SEPARATORS,
            length_function=len,
        )


# ── LangChain embeddings adapter ──────────────────────────────────────────────
class _SidecarEmbeddingsAdapter:
    """
    Minimal LangChain-compatible embeddings object that calls the local
    embedding sidecar via HTTP.  Only implements embed_documents() and
    embed_query() which is all SemanticChunker needs.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import httpx
        response = httpx.post(
            f"{self._base_url}/embed",
            json={"texts": texts},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
