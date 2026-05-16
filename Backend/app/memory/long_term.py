"""
app/memory/long_term.py
────────────────────────
Long-term episodic memory — ChromaDB vector store per patient.

Stores structured facts extracted from past conversations by MemoryExtractorAgent.
These facts persist indefinitely (until explicitly deleted) and are retrieved
by the RAG pipeline to give the system contextual awareness across sessions.

Examples of stored facts:
  "Patient reported knee pain preventing extended walking since April 2026"
  "Patient is allergic to penicillin (self-reported)"
  "Patient expressed anxiety about starting insulin therapy in March 2026"

Collection: patient_memory  (separate from clinical_knowledge)

Key guarantee — patient isolation:
  All reads and writes include `{"patient_id": patient_id}` in the ChromaDB
  where filter. Facts from one patient are NEVER retrievable by another.

Also provides:
  - get_all_facts(patient_id) — full memory dump for UI display
  - delete_patient(patient_id) — GDPR right-to-erasure
  - fact_count(patient_id) — used by admin dashboard
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.core.config import settings
from app.core.exceptions import EmbeddingServiceError
from app.rag.embeddings.local_embedder import LocalEmbedder

logger = structlog.get_logger(__name__)

# Cosine similarity above this → considered a duplicate, skip storing
_DUPLICATE_THRESHOLD = 0.92


@dataclass
class MemoryFact:
    """A single retrieved patient memory fact."""
    id:         str
    text:       str
    category:   str             # "symptom" | "allergy" | "medication" | etc.
    confidence: float
    stored_at:  str
    session_id: str
    metadata:   dict = field(default_factory=dict)


@dataclass
class StorageResult:
    stored:    int
    skipped:   int             # duplicates
    errors:    int


class LongTermMemory:
    """
    ChromaDB-backed episodic memory for persistent patient facts.

    Used by:
      - MemoryExtractorAgent  → store() after extracting facts
      - ClinicalRAGAgent      → retrieve() at query time
      - Admin endpoints       → get_all_facts(), delete_patient()
    """

    def __init__(self, embedder: Optional[LocalEmbedder] = None) -> None:
        self._embedder    = embedder or LocalEmbedder()
        self._chroma_path = settings.CHROMA_PATH
        self._col_name    = settings.CHROMA_MEMORY_COLLECTION
        self._client      = None   # lazy-loaded

    # ── Write ──────────────────────────────────────────────────────────────────
    async def store(
        self,
        patient_id: str,
        session_id: str,
        facts:      list[dict],
    ) -> StorageResult:
        """
        Embed and store extracted facts for a patient.

        Args:
            patient_id: Partition key — ALL stored metadata includes this.
            session_id: Audit trail — which session produced these facts.
            facts     : List of dicts from MemoryExtractorAgent.
                        Each must have: {"fact": str, "category": str, "confidence": float}

        Returns:
            StorageResult with counts of stored, skipped, and errored facts.
        """
        if not facts:
            return StorageResult(stored=0, skipped=0, errors=0)

        texts = [f["fact"] for f in facts]

        # Embed all facts in one batch
        try:
            embeddings = self._embedder.embed_batch(texts)
        except EmbeddingServiceError as exc:
            logger.error("long_term.embed_failed",
                         patient_id=patient_id, error=str(exc))
            return StorageResult(stored=0, skipped=0, errors=len(facts))

        collection = self._get_collection()
        now        = datetime.now(timezone.utc).isoformat()
        stored = skipped = errors = 0

        for fact_dict, embedding in zip(facts, embeddings):
            text       = fact_dict["fact"].strip()
            category   = fact_dict.get("category", "other")
            confidence = float(fact_dict.get("confidence", 0.5))

            # Duplicate guard — skip if a very similar fact already exists
            if self._is_duplicate(collection, embedding, patient_id):
                logger.debug("long_term.duplicate_skipped",
                             patient_id=patient_id, fact=text[:60])
                skipped += 1
                continue

            try:
                collection.add(
                    ids=[str(uuid.uuid4())],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[{
                        "patient_id": patient_id,
                        "session_id": session_id,
                        "category":   category,
                        "confidence": str(confidence),
                        "stored_at":  now,
                        "type":       "episodic_memory",
                    }],
                )
                stored += 1
            except Exception as exc:
                logger.warning("long_term.store_fact_failed",
                               patient_id=patient_id, error=str(exc))
                errors += 1

        logger.info("long_term.stored",
                    patient_id=patient_id, stored=stored,
                    skipped=skipped, errors=errors)
        return StorageResult(stored=stored, skipped=skipped, errors=errors)

    # ── Read ───────────────────────────────────────────────────────────────────
    async def retrieve(
        self,
        query_embedding: list[float],
        patient_id:      str,
        top_k:           int = 5,
    ) -> list[MemoryFact]:
        """
        Retrieve the most relevant memory facts for a given query embedding.
        Called by ClinicalRAGAgent alongside clinical knowledge retrieval.

        Args:
            query_embedding: Pre-computed query vector (avoids re-embedding).
            patient_id      : MANDATORY — isolates to this patient's facts only.
            top_k           : Maximum number of facts to return.

        Returns:
            List of MemoryFact sorted by relevance (highest first).
        """
        try:
            col   = self._get_collection()
            count = self._patient_fact_count(col, patient_id)
            if count == 0:
                return []

            results = col.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count),
                where={"patient_id": patient_id},   # ← patient isolation
                include=["documents", "metadatas", "distances"],
            )
            return self._parse_results(results)

        except Exception as exc:
            logger.warning("long_term.retrieve_failed",
                           patient_id=patient_id, error=str(exc))
            return []

    async def get_all_facts(
        self,
        patient_id: str,
        category:   Optional[str] = None,
    ) -> list[MemoryFact]:
        """
        Return all stored facts for a patient (for UI display / audit).

        Args:
            patient_id: Patient to query.
            category  : Optional filter — "symptom" | "allergy" | "medication" etc.

        Returns:
            All MemoryFact records for this patient, sorted newest first.
        """
        try:
            col   = self._get_collection()
            where: dict = {"patient_id": patient_id}
            if category:
                where = {"$and": [
                    {"patient_id": patient_id},
                    {"category":   category},
                ]}

            results = col.get(
                where=where,
                include=["documents", "metadatas"],
            )
            return self._parse_get_results(results)

        except Exception as exc:
            logger.warning("long_term.get_all_failed",
                           patient_id=patient_id, error=str(exc))
            return []

    # ── Delete ─────────────────────────────────────────────────────────────────
    def delete_patient(self, patient_id: str) -> int:
        """
        Permanently delete all memory facts for a patient.
        Used for GDPR right-to-erasure requests.

        Returns:
            Number of records deleted.
        """
        try:
            col     = self._get_collection()
            results = col.get(where={"patient_id": patient_id})
            ids     = results.get("ids", [])
            if ids:
                col.delete(ids=ids)
            logger.info("long_term.patient_deleted",
                        patient_id=patient_id, count=len(ids))
            return len(ids)
        except Exception as exc:
            logger.error("long_term.delete_failed",
                         patient_id=patient_id, error=str(exc))
            return 0

    def delete_session_facts(self, patient_id: str, session_id: str) -> int:
        """Delete facts from a specific session (e.g., after a bad extraction)."""
        try:
            col = self._get_collection()
            results = col.get(where={
                "$and": [
                    {"patient_id": patient_id},
                    {"session_id": session_id},
                ]
            })
            ids = results.get("ids", [])
            if ids:
                col.delete(ids=ids)
            return len(ids)
        except Exception as exc:
            logger.warning("long_term.delete_session_failed",
                           session_id=session_id, error=str(exc))
            return 0

    # ── Stats ──────────────────────────────────────────────────────────────────
    def fact_count(self, patient_id: str) -> int:
        """Return the number of stored facts for a patient."""
        try:
            return self._patient_fact_count(self._get_collection(), patient_id)
        except Exception:
            return 0

    def total_count(self) -> int:
        """Return total facts across all patients (admin dashboard)."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    # ── Internals ──────────────────────────────────────────────────────────────
    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._chroma_path)
        return self._client

    def _get_collection(self):
        return self._get_client().get_or_create_collection(
            name=self._col_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _is_duplicate(
        self,
        collection,
        embedding:  list[float],
        patient_id: str,
    ) -> bool:
        """Return True if a near-identical fact already exists for this patient."""
        try:
            count = self._patient_fact_count(collection, patient_id)
            if count == 0:
                return False

            results   = collection.query(
                query_embeddings=[embedding],
                n_results=1,
                where={"patient_id": patient_id},
                include=["distances"],
            )
            distances = results.get("distances", [[]])[0]
            if distances:
                similarity = 1.0 - distances[0]
                return similarity >= _DUPLICATE_THRESHOLD
        except Exception:
            pass
        return False

    @staticmethod
    def _patient_fact_count(collection, patient_id: str) -> int:
        try:
            results = collection.get(
                where={"patient_id": patient_id},
                limit=10_000,
            )
            return len(results.get("ids", []))
        except Exception:
            return 0

    @staticmethod
    def _parse_results(results: dict) -> list[MemoryFact]:
        facts:    list[MemoryFact] = []
        docs      = results.get("documents", [[]])[0]
        metas     = results.get("metadatas",  [[]])[0]
        distances = results.get("distances",  [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            if not doc:
                continue
            facts.append(MemoryFact(
                id=meta.get("id", str(uuid.uuid4())),
                text=doc.strip(),
                category=meta.get("category", "other"),
                confidence=float(meta.get("confidence", "0.5")),
                stored_at=meta.get("stored_at", ""),
                session_id=meta.get("session_id", ""),
                metadata=meta,
            ))
        return facts

    @staticmethod
    def _parse_get_results(results: dict) -> list[MemoryFact]:
        facts: list[MemoryFact] = []
        docs  = results.get("documents", [])
        metas = results.get("metadatas",  [])
        ids   = results.get("ids",        [])

        combined = sorted(
            zip(ids, docs, metas),
            key=lambda x: x[2].get("stored_at", ""),
            reverse=True,   # newest first
        )

        for fact_id, doc, meta in combined:
            if not doc:
                continue
            facts.append(MemoryFact(
                id=fact_id,
                text=doc.strip(),
                category=meta.get("category", "other"),
                confidence=float(meta.get("confidence", "0.5")),
                stored_at=meta.get("stored_at", ""),
                session_id=meta.get("session_id", ""),
                metadata=meta,
            ))
        return facts
