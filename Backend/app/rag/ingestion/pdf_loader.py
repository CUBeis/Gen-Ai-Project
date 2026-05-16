"""
app/rag/ingestion/pdf_loader.py
────────────────────────────────
Medical PDF loader — extracts clean text from PDFs for the RAG pipeline.

Uses PyMuPDF (fitz) — the fastest Python PDF library, handles scanned PDFs,
tables, multi-column layouts, and embedded images gracefully.

What this does:
  - Extracts text page-by-page
  - Filters out garbage pages (too little text, mostly whitespace)
  - Preserves page number metadata for citation ("Source: drug_guide.pdf, p.14")
  - Returns a list of Document objects ready for the chunker

What this does NOT do:
  - OCR on scanned images (would require tesseract — add if needed)
  - Table extraction as structured data (plain text representation is sufficient for RAG)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Minimum characters on a page to consider it meaningful content
_MIN_PAGE_CHARS = 80

# Pages that are likely covers, ToC, or blank — skip them
_SKIP_PATTERNS = [
    r"^table\s+of\s+contents",
    r"^copyright",
    r"^all\s+rights\s+reserved",
    r"^\s*$",
]


@dataclass
class Document:
    """
    A single unit of text with metadata, produced by any loader.
    Passed directly into the chunker.
    """
    content:  str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # Normalise whitespace
        self.content = re.sub(r"\n{3,}", "\n\n", self.content).strip()


class MedicalPDFLoader:
    """
    Loads a PDF file and returns one Document per meaningful page.

    Usage:
        loader = MedicalPDFLoader()
        docs = loader.load("/path/to/drug_guide.pdf", source_name="WHO Drug Guide")
    """

    def load(
        self,
        file_path: str | Path,
        source_name: Optional[str] = None,
        doc_type: str = "clinical_guideline",
        language: str = "en",
    ) -> list[Document]:
        """
        Load a PDF and return a Document per page (filtered).

        Args:
            file_path  : Absolute path to the PDF.
            source_name: Human-readable name used in RAG citations.
            doc_type   : Metadata tag — "clinical_guideline" | "drug_interactions"
                         | "patient_leaflet" | "lab_reference"
            language   : ISO 639-1 language code of the document.

        Returns:
            List of Document objects, one per non-empty page.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError("PyMuPDF is required: pip install pymupdf") from exc

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        filename = source_name or path.name
        documents: list[Document] = []

        logger.info("pdf_loader.start", filename=filename, path=str(path))

        try:
            pdf = fitz.open(str(path))
        except Exception as exc:
            logger.error("pdf_loader.open_failed", filename=filename, error=str(exc))
            raise

        total_pages = pdf.page_count
        skipped = 0

        for page_num in range(total_pages):
            page = pdf[page_num]

            # Extract text — "text" mode gives plain text, "blocks" gives positional data
            raw_text = page.get_text("text")

            # Skip pages with too little content
            if len(raw_text.strip()) < _MIN_PAGE_CHARS:
                skipped += 1
                continue

            # Skip pages matching garbage patterns
            first_line = raw_text.strip().lower().split("\n")[0]
            if any(re.match(p, first_line) for p in _SKIP_PATTERNS):
                skipped += 1
                continue

            # Clean extracted text
            cleaned = self._clean_text(raw_text)
            if len(cleaned) < _MIN_PAGE_CHARS:
                skipped += 1
                continue

            documents.append(Document(
                content=cleaned,
                metadata={
                    "source":    filename,
                    "page":      page_num + 1,    # 1-indexed for citations
                    "doc_type":  doc_type,
                    "language":  language,
                    "total_pages": total_pages,
                },
            ))

        pdf.close()

        logger.info(
            "pdf_loader.done",
            filename=filename,
            total_pages=total_pages,
            loaded=len(documents),
            skipped=skipped,
        )
        return documents

    def load_bytes(
        self,
        data: bytes,
        source_name: str = "uploaded_document",
        doc_type: str = "clinical_guideline",
        language: str = "en",
    ) -> list[Document]:
        """
        Load a PDF from raw bytes (e.g., from an HTTP upload).
        Writes to a temp file then delegates to load().
        """
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            return self.load(tmp_path, source_name, doc_type, language)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ── Text cleaning ──────────────────────────────────────────────────────────
    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean extracted PDF text:
          - Collapse excessive newlines
          - Remove soft hyphens (line-break artifacts in PDFs)
          - Strip header/footer-like repeated short lines
          - Normalise Unicode whitespace
        """
        # Remove soft hyphens (word-wrap artifacts)
        text = text.replace("\xad", "")
        # Normalise Unicode whitespace variants
        text = re.sub(r"[\u00a0\u200b\u202f\u2009]", " ", text)
        # Collapse 3+ consecutive newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove lines that are just page numbers: "- 14 -" or "14" alone
        text = re.sub(r"^\s*[-–]\s*\d+\s*[-–]\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()
