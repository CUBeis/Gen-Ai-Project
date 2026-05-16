"""
app/agents/memory_extractor_agent.py
──────────────────────────────────────
Memory Extractor Agent — runs in the background after conversations.

Model : Gemini 1.5 Flash
Role  : Parse a completed conversation, extract medically significant facts
        about the patient, and store them as vector embeddings in ChromaDB
        (patient_memory collection) for future RAG retrieval.

IMPORTANT: This agent is invoked by a Celery background task — NOT during
the live request/response cycle. It never blocks a patient interaction.

What gets extracted (examples):
  - "Patient reported knee pain preventing extended walking since April 2026"
  - "Patient is allergic to penicillin (self-reported)"
  - "Patient expressed anxiety about starting insulin therapy"
  - "Patient mentioned difficulty sleeping for the past two weeks"

What does NOT get extracted:
  - Generic greetings or small talk
  - Questions the AI answered (only patient-stated facts)
  - Duplicate facts already in memory (handled by similarity threshold)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import google.generativeai as genai
import httpx

from app.agents.base import BaseAgent, llm_retry
from app.core.exceptions import AgentError, EmbeddingServiceError


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class ExtractedMemory:
    fact:        str       # Normalised English fact sentence
    category:    str       # "symptom" | "allergy" | "emotion" | "lifestyle" | "medication" | "other"
    confidence:  float     # 0.0 – 1.0
    source_turn: int       # Approximate message index in the conversation


@dataclass
class ExtractionResult:
    patient_id:   str
    session_id:   str
    facts:        list[ExtractedMemory]
    stored_count: int      # How many facts were actually written to ChromaDB


# ── Extraction prompt ─────────────────────────────────────────────────────────
_EXTRACTION_PROMPT = """You are a medical memory extraction system.
Given a conversation between a patient and an AI medical assistant, 
extract all medically or psychologically significant facts stated by the PATIENT (not the AI).

RULES:
1. Extract ONLY facts the patient explicitly stated — never infer.
2. Each fact must be a complete, self-contained sentence in ENGLISH regardless of the conversation language.
3. Be specific: include body parts, durations, quantities, and dates when mentioned.
4. Do NOT extract questions the patient asked.
5. Do NOT extract things the AI said.
6. Assign a category: "symptom" | "allergy" | "medication" | "lifestyle" | "emotion" | "appointment" | "other"
7. Assign confidence (0.0–1.0) — lower for vague statements.
8. Omit trivial facts (greetings, thanks, "ok", "yes/no" with no context).

Return ONLY valid JSON — no markdown, no explanation:
{
  "facts": [
    {
      "fact": "<complete sentence in English>",
      "category": "<category>",
      "confidence": <float>,
      "source_turn": <message_index_int>
    }
  ]
}

If no significant facts exist, return: {"facts": []}"""


# ── Agent ──────────────────────────────────────────────────────────────────────
class MemoryExtractorAgent(BaseAgent):

    # Minimum confidence to store a fact
    MIN_CONFIDENCE = 0.60
    # Minimum cosine similarity to consider a fact a duplicate (skip storing)
    DUPLICATE_THRESHOLD = 0.92

    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        self._llm         = genai.GenerativeModel(self.settings.GEMINI_MODEL)
        self._embed_url   = self.settings.EMBEDDING_SERVICE_URL
        self._chroma_path = self.settings.CHROMA_PATH
        self._memory_col  = self.settings.CHROMA_MEMORY_COLLECTION
        self._chroma      = None   # lazy-loaded

    async def run(
        self,
        conversation_history: list[dict],
        patient_id: str,
        session_id: str,
    ) -> ExtractionResult:
        """
        Extract facts from a conversation and persist them to ChromaDB.

        Args:
            conversation_history : Full message list from Redis short-term memory.
            patient_id           : ChromaDB metadata filter key.
            session_id           : For audit trail in metadata.
        """
        t0    = self._now_ms()
        trace = self._start_trace(
            "memory_extractor",
            {"session_id": session_id, "turns": len(conversation_history)},
        )

        if len(conversation_history) < 4:
            self.logger.info("memory_extractor.skipped", reason="too_few_turns")
            return ExtractionResult(patient_id, session_id, [], 0)

        # Step 1 — Extract facts from conversation
        memories = await self._extract(conversation_history)
        self.logger.info("memory_extractor.extracted", raw_count=len(memories))

        # Step 2 — Filter low-confidence facts
        confident = [m for m in memories if m.confidence >= self.MIN_CONFIDENCE]

        # Step 3 — Embed and store (deduplicated)
        stored_count = await self._store(confident, patient_id, session_id)

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "extraction", self.settings.GEMINI_MODEL,
            prompt=f"{len(conversation_history)} messages",
            completion=f"{len(confident)} facts",
            latency_ms=latency,
        )
        self.logger.info(
            "memory_extractor.done",
            extracted=len(memories),
            confident=len(confident),
            stored=stored_count,
            latency_ms=latency,
        )
        return ExtractionResult(patient_id, session_id, confident, stored_count)

    @llm_retry(max_attempts=3, reraise_as=AgentError)
    async def _extract(self, history: list[dict]) -> list[ExtractedMemory]:
        # Format conversation for the prompt
        formatted = "\n".join(
            f"[{i}] {msg['role'].upper()}: {msg['content']}"
            for i, msg in enumerate(history)
        )

        prompt = f"{_EXTRACTION_PROMPT}\n\nCONVERSATION:\n{formatted}"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1000,
                ),
            ),
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("memory_extractor.json_parse_failed", raw=raw[:200])
            return []

        memories = []
        for item in data.get("facts", []):
            try:
                memories.append(ExtractedMemory(
                    fact=str(item["fact"]).strip(),
                    category=str(item.get("category", "other")),
                    confidence=float(item.get("confidence", 0.5)),
                    source_turn=int(item.get("source_turn", 0)),
                ))
            except (KeyError, ValueError, TypeError):
                continue

        return memories

    async def _store(
        self,
        memories: list[ExtractedMemory],
        patient_id: str,
        session_id: str,
    ) -> int:
        if not memories:
            return 0

        # Embed all facts in one batch call
        texts = [m.fact for m in memories]
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._embed_url}/embed",
                    json={"texts": texts},
                )
                resp.raise_for_status()
                embeddings = resp.json()["embeddings"]
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError() from exc

        chroma = self._get_chroma()
        collection = chroma.get_or_create_collection(
            self._memory_col,
            metadata={"hnsw:space": "cosine"},
        )

        stored = 0
        now = datetime.now(timezone.utc).isoformat()

        for memory, embedding in zip(memories, embeddings):
            # Duplicate check — skip if very similar fact already exists
            if await self._is_duplicate(collection, embedding, patient_id):
                self.logger.debug(
                    "memory_extractor.duplicate_skipped",
                    fact=memory.fact[:80],
                )
                continue

            try:
                collection.add(
                    ids=[str(uuid.uuid4())],
                    embeddings=[embedding],
                    documents=[memory.fact],
                    metadatas=[{
                        "patient_id":  patient_id,
                        "session_id":  session_id,
                        "category":    memory.category,
                        "confidence":  str(memory.confidence),
                        "stored_at":   now,
                        "type":        "episodic_memory",
                    }],
                )
                stored += 1
            except Exception as exc:
                self.logger.warning("memory_extractor.store_failed", error=str(exc))

        return stored

    async def _is_duplicate(
        self,
        collection,
        embedding: list[float],
        patient_id: str,
    ) -> bool:
        """Return True if a very similar fact already exists for this patient."""
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=1,
                where={"patient_id": patient_id},
                include=["distances"],
            )
            distances = results.get("distances", [[]])[0]
            if distances:
                similarity = 1.0 - distances[0]  # cosine distance → similarity
                return similarity >= self.DUPLICATE_THRESHOLD
        except Exception:
            pass
        return False

    def _get_chroma(self):
        if self._chroma is None:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=self._chroma_path)
        return self._chroma
