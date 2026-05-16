"""
app/agents/rag_agent.py
────────────────────────
Clinical RAG Agent — answers medical questions with grounded retrieval.

Pipeline per query:
  1. Query Reformulation  — resolve pronouns using session context (Gemini)
  2. Parallel Retrieval   — clinical knowledge + patient episodic memory (ChromaDB)
  3. Reranking            — cross-encoder filters top-K down to top-N
  4. Augmented Generation — Gemini answers using ONLY retrieved context
  5. Source Attribution   — returns which documents were used

Model    : Gemini 1.5 Flash
Embedder : all-MiniLM-L6-v2 (local sidecar via HTTP)
Vector DB: ChromaDB (persistent local)
Reranker : cross-encoder/ms-marco-MiniLM-L-6-v2 (local CPU)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai
import httpx

from app.agents.base import BaseAgent, llm_retry
from app.core.exceptions import RAGAgentError, EmbeddingServiceError


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class RetrievedChunk:
    text:            str
    source:          str
    page:            Optional[int]
    relevance_score: float
    rerank_score:    float = 0.0


@dataclass
class RAGResult:
    answer:  str
    sources: list[dict]           # [{"source": "...", "page": N}]
    reformulated_query: str


# ── System prompt ──────────────────────────────────────────────────────────────
_ANSWER_SYSTEM = """You are a clinical medical assistant AI for Nerve AI.

STRICT RULES:
1. Answer ONLY using the retrieved medical context and the patient's own medical record provided below.
2. If the answer is NOT in the provided context, say exactly: "I don't have sufficient clinical information on this topic. Please consult your physician directly."
3. NEVER fabricate drug names, dosages, or medical facts.
4. NEVER say "you should take X mg" — dosage decisions belong to the physician.
5. NEVER diagnose the patient.
6. If information seems contradictory, present both perspectives and recommend consulting a doctor.
7. End EVERY response about medications or symptoms with the safety disclaimer provided.

RESPONSE FORMAT:
- Answer clearly in the patient's language.
- Reference the source material naturally ("According to clinical guidelines...", "Medical literature indicates...").
- Keep responses focused and not excessively long (3–5 paragraphs max).
- Always end with: ⚕️ *This information is for educational purposes only. Always consult your physician before making any medical decisions.*"""

_REFORMULATION_PROMPT = """Given this recent conversation history and a follow-up question, 
rewrite the question as a complete, standalone medical search query.
Resolve all pronouns and references. Do NOT answer the question — only rewrite it.
Return ONLY the rewritten query, nothing else.

Conversation:
{history}

Follow-up question: {question}

Standalone query:"""


# ── Agent ──────────────────────────────────────────────────────────────────────
class ClinicalRAGAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        self._llm            = genai.GenerativeModel(self.settings.GEMINI_MODEL)
        self._embed_url      = self.settings.EMBEDDING_SERVICE_URL
        self._chroma_path    = self.settings.CHROMA_PATH
        self._clinical_col   = self.settings.CHROMA_CLINICAL_COLLECTION
        self._memory_col     = self.settings.CHROMA_MEMORY_COLLECTION
        self._top_k          = self.settings.RAG_TOP_K
        self._rerank_top_n   = self.settings.RAG_RERANK_TOP_N
        self._reranker       = None   # lazy-loaded (heavy import)
        self._chroma_client  = None   # lazy-loaded

    async def run(
        self,
        user_message:    str,
        session_history: list[dict],
        patient_context: dict,
        patient_id:      str,
        language:        str = "en",
    ) -> RAGResult:
        """
        Full RAG pipeline for a clinical question.

        Args:
            user_message    : Raw patient question.
            session_history : Short-term memory for reformulation context.
            patient_context : Structured patient data from PostgreSQL.
            patient_id      : Used to filter patient-specific memories in ChromaDB.
            language        : Response language from Router agent.
        """
        t0    = self._now_ms()
        trace = self._start_trace("rag_agent", {"question": user_message[:200]})

        # Step 1 — Reformulate query
        reformulated = await self._reformulate(user_message, session_history)
        self.logger.debug("rag.reformulated", original=user_message[:100], reformulated=reformulated[:100])

        # Step 2 — Embed reformulated query
        query_embedding = await self._embed(reformulated)

        # Step 3 — Parallel retrieval from both collections
        clinical_chunks, memory_chunks = await asyncio.gather(
            self._retrieve_clinical(query_embedding),
            self._retrieve_patient_memory(query_embedding, patient_id),
        )
        all_chunks = clinical_chunks + memory_chunks
        self.logger.debug("rag.retrieved", clinical=len(clinical_chunks), memory=len(memory_chunks))

        # Step 4 — Rerank
        reranked = self._rerank(reformulated, all_chunks)
        self.logger.debug("rag.reranked", kept=len(reranked))

        # Step 5 — Generate grounded answer
        answer = await self._generate(reformulated, reranked, patient_context, language)

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "rag_generate", self.settings.GEMINI_MODEL,
            prompt=reformulated, completion=answer[:200],
            latency_ms=latency,
        )
        self.logger.info("rag.done", latency_ms=latency, sources=len(reranked))

        sources = [
            {"source": c.source, "page": c.page}
            for c in reranked if c.source
        ]

        return RAGResult(
            answer=answer,
            sources=sources,
            reformulated_query=reformulated,
        )

    # ── Step 1: Reformulation ─────────────────────────────────────────────────
    @llm_retry(max_attempts=2, reraise_as=RAGAgentError)
    async def _reformulate(self, question: str, history: list[dict]) -> str:
        if not history:
            return question

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-6:]   # last 3 turns
        )

        prompt = _REFORMULATION_PROMPT.format(
            history=history_text,
            question=question,
        )

        response = self._llm.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=150,
            ),
        )
        reformulated = response.text.strip()
        # Sanity check — if model returned something weird, fall back
        return reformulated if len(reformulated) > 5 else question

    # ── Step 2: Embedding ─────────────────────────────────────────────────────
    async def _embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._embed_url}/embed",
                    json={"texts": [text]},
                )
                resp.raise_for_status()
                return resp.json()["embeddings"][0]
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError() from exc

    # ── Step 3a: Clinical knowledge retrieval ─────────────────────────────────
    async def _retrieve_clinical(self, embedding: list[float]) -> list[RetrievedChunk]:
        client = self._get_chroma()
        try:
            collection = client.get_or_create_collection(self._clinical_col)
            results = collection.query(
                query_embeddings=[embedding],
                n_results=self._top_k,
                include=["documents", "metadatas", "distances"],
            )
            return self._parse_results(results)
        except Exception as exc:
            self.logger.warning("rag.clinical_retrieval_failed", error=str(exc))
            return []

    # ── Step 3b: Patient episodic memory retrieval ────────────────────────────
    async def _retrieve_patient_memory(
        self,
        embedding: list[float],
        patient_id: str,
    ) -> list[RetrievedChunk]:
        client = self._get_chroma()
        try:
            collection = client.get_or_create_collection(self._memory_col)
            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(5, self._top_k // 2),
                where={"patient_id": patient_id},    # CRITICAL: patient isolation
                include=["documents", "metadatas", "distances"],
            )
            return self._parse_results(results)
        except Exception as exc:
            self.logger.warning("rag.memory_retrieval_failed", error=str(exc))
            return []

    # ── Step 4: Reranking ─────────────────────────────────────────────────────
    def _rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []

        reranker = self._get_reranker()
        pairs = [(query, c.text) for c in chunks]

        try:
            scores = reranker.predict(pairs)
            for chunk, score in zip(chunks, scores):
                chunk.rerank_score = float(score)
            ranked = sorted(chunks, key=lambda c: c.rerank_score, reverse=True)
            return ranked[: self._rerank_top_n]
        except Exception as exc:
            self.logger.warning("rag.rerank_failed", error=str(exc))
            # Fall back to relevance score ordering
            return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)[: self._rerank_top_n]

    # ── Step 5: Augmented generation ──────────────────────────────────────────
    @llm_retry(max_attempts=3, reraise_as=RAGAgentError)
    async def _generate(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        patient_context: dict,
        language: str,
    ) -> str:
        context_text = "\n\n---\n\n".join(
            f"[Source: {c.source}, page {c.page}]\n{c.text}"
            for c in chunks
        ) if chunks else "No specific clinical documents were retrieved for this query."

        patient_summary = (
            f"Name: {patient_context.get('name', 'Unknown')}\n"
            f"Age: {patient_context.get('age', 'Unknown')}\n"
            f"Conditions: {', '.join(patient_context.get('conditions', [])) or 'None reported'}\n"
            f"Medications: {', '.join(patient_context.get('medications', [])) or 'None reported'}\n"
            f"Allergies: {', '.join(patient_context.get('allergies', [])) or 'None reported'}"
        )

        full_prompt = f"""{_ANSWER_SYSTEM}

## Retrieved Clinical Context:
{context_text}

## Patient Medical Record:
{patient_summary}

## Patient Question:
{query}

## Instructions:
- Answer in language code: {language}
- Base your answer strictly on the context above.
- Reference sources naturally.
- End with the ⚕️ disclaimer."""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            ),
        )
        return response.text.strip()

    # ── Lazy-loaded singletons ─────────────────────────────────────────────────
    def _get_chroma(self):
        if self._chroma_client is None:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=self._chroma_path)
        return self._chroma_client

    def _get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._reranker

    # ── Helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_results(results: dict) -> list[RetrievedChunk]:
        chunks = []
        docs      = results.get("documents", [[]])[0]
        metas     = results.get("metadatas", [[]])[0]
        distances = results.get("distances",  [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            chunks.append(RetrievedChunk(
                text=doc,
                source=meta.get("source", "unknown"),
                page=meta.get("page"),
                relevance_score=float(1.0 - dist),   # cosine distance → similarity
            ))
        return chunks
