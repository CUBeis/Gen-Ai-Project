"""
app/agents/rag_agent.py
────────────────────────
Clinical RAG Agent — synced with Rag/ folder pipeline.

Pipeline per query:
  1. Multilingual     — translate to English for retrieval when needed
  2. Query Reformulation — primary LLM (OpenRouter / Gemini)
  3. Hybrid Retrieval — Cohere embed + BM25 + MMR + Cohere rerank (medical_rag)
  4. Patient memory   — ChromaDB episodic memory
  5. Augmented Generation — primary LLM (answer in patient language)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai
import httpx
import structlog

from app.agents.base import BaseAgent, llm_retry
from app.core.config import settings
from app.core.exceptions import RAGAgentError, EmbeddingServiceError
from app.llm.factory import get_chat_llm, primary_llm_model_name
from app.rag.multilingual.translator import MultilingualLayer
from app.rag.retrieval.hybrid_retriever import HybridClinicalRetriever
from app.rag.retrieval.retriever import ClinicalRetriever, SearchResult

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    source: str
    page: Optional[int]
    relevance_score: float
    rerank_score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class RAGResult:
    answer: str
    sources: list[dict]
    reformulated_query: str
    english_query: str = ""
    was_translated: bool = False


_ANSWER_SYSTEM = """You are a clinical medical assistant AI for Nerve AI.

STRICT RULES:
1. Answer ONLY using the retrieved medical context and the patient's medical record.
2. If the answer is NOT in the context, say you don't have sufficient clinical information.
3. NEVER fabricate drug names, dosages, or medical facts.
4. NEVER diagnose the patient.
5. End medication/symptom responses with a brief safety disclaimer in the same language as the answer.

Do not switch languages for the disclaimer."""

_REFORMULATION_PROMPT = """Given this conversation history and a follow-up question,
rewrite the question as a complete, standalone medical search query in English.
Resolve pronouns. Return ONLY the rewritten query.

Conversation:
{history}

Follow-up question: {question}

Standalone English query:"""


class ClinicalRAGAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        self._llm = get_chat_llm()
        self._multilingual = MultilingualLayer(self._llm)
        self._hybrid: Optional[HybridClinicalRetriever] = None
        self._legacy_retriever = ClinicalRetriever()
        self._chroma_path = settings.CHROMA_PATH
        self._memory_col = settings.CHROMA_MEMORY_COLLECTION
        self._chroma_client = None
        self._gemini = None
        if settings.RAG_LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._gemini = genai.GenerativeModel(settings.GEMINI_MODEL)

    def _get_hybrid(self) -> HybridClinicalRetriever:
        if self._hybrid is None:
            self._hybrid = HybridClinicalRetriever()
        return self._hybrid

    async def run(
        self,
        user_message: str,
        session_history: list[dict],
        patient_context: dict,
        patient_id: str,
        language: str = "en",
        workflow_trace_id: Optional[str] = None,
    ) -> RAGResult:
        from app.tracking.workflow_tracker import workflow_tracker

        t0 = self._now_ms()
        trace = self._start_trace("rag_agent", {"question": user_message[:200]})

        def _wf(name: str, **kwargs):
            if workflow_trace_id:
                workflow_tracker.step(workflow_trace_id, name, **kwargs)

        # Step 1 — Multilingual preprocessing
        t1 = self._now_ms()
        translation = await self._multilingual.to_english(user_message, language)
        english_message = translation.english_text
        _wf(
            "multilingual_translate",
            duration_ms=self._elapsed(t1),
            input_summary={"original": user_message[:120], "language": language},
            output_summary={
                "english": english_message[:120],
                "was_translated": translation.was_translated,
            },
        )

        # Step 2 — Reformulate
        t2 = self._now_ms()
        reformulated = await self._reformulate(english_message, session_history)
        _wf(
            "query_reformulation",
            duration_ms=self._elapsed(t2),
            input_summary={"query": english_message[:120]},
            output_summary={"reformulated": reformulated[:120]},
        )

        # Step 3 — Retrieve clinical knowledge
        t3 = self._now_ms()
        if settings.RAG_USE_COHERE_EMBEDDINGS and settings.RAG_USE_HYBRID_RETRIEVAL:
            try:
                clinical_results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._get_hybrid().retrieve(reformulated),
                )
            except Exception as exc:
                self.logger.warning("rag.hybrid_failed_fallback", error=str(exc))
                clinical_results = await self._legacy_retriever.search_clinical(reformulated)
        else:
            clinical_results = await self._legacy_retriever.search_clinical(reformulated)

        memory_results = await self._retrieve_patient_memory(reformulated, patient_id)
        _wf(
            "hybrid_retrieval",
            duration_ms=self._elapsed(t3),
            output_summary={
                "clinical_chunks": len(clinical_results),
                "memory_chunks": len(memory_results),
                "collection": settings.RAG_MEDICAL_COLLECTION,
            },
        )

        all_chunks = self._merge_results(clinical_results, memory_results)

        # Step 4 — Generate
        t4 = self._now_ms()
        answer = await self._generate(
            query=user_message,
            english_query=reformulated,
            chunks=all_chunks,
            patient_context=patient_context,
            language=language,
        )
        _wf(
            "llm_generation",
            duration_ms=self._elapsed(t4),
            input_summary={"model": primary_llm_model_name(), "chunks": len(all_chunks)},
            output_summary={"answer_preview": answer[:120]},
        )

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "rag_generate", primary_llm_model_name(),
            prompt=reformulated, completion=answer[:200],
            latency_ms=latency,
        )

        sources = [
            {
                "source": c.source,
                "entity_name": c.metadata.get("entity_name"),
                "entity_type": c.metadata.get("entity_type"),
                "score": c.relevance_score,
                "url": c.metadata.get("url"),
            }
            for c in all_chunks
            if c.source
        ]

        return RAGResult(
            answer=answer,
            sources=sources,
            reformulated_query=reformulated,
            english_query=english_message,
            was_translated=translation.was_translated,
        )

    @llm_retry(max_attempts=2, reraise_as=RAGAgentError)
    async def _reformulate(self, question: str, history: list[dict]) -> str:
        if not history:
            return question

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-6:]
        )
        prompt = _REFORMULATION_PROMPT.format(history=history_text, question=question)

        if settings.primary_llm_enabled:
            text = await self._llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
            )
            return text if len(text) > 5 else question

        if self._gemini:
            response = self._gemini.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, max_output_tokens=150,
                ),
            )
            reformulated = response.text.strip()
            return reformulated if len(reformulated) > 5 else question

        return question

    async def _retrieve_patient_memory(
        self, query: str, patient_id: str,
    ) -> list[RetrievedChunk]:
        try:
            results = await self._legacy_retriever.search_patient_memory(query, patient_id, top_k=5)
            return self._search_results_to_chunks(results)
        except Exception as exc:
            self.logger.warning("rag.memory_retrieval_failed", error=str(exc))
            return []

    @llm_retry(max_attempts=3, reraise_as=RAGAgentError)
    async def _generate(
        self,
        query: str,
        english_query: str,
        chunks: list[RetrievedChunk],
        patient_context: dict,
        language: str,
    ) -> str:
        context_text = "\n\n---\n\n".join(
            f"[Source: {c.source} | {c.metadata.get('entity_name', '')}]\n{c.text}"
            for c in chunks
        ) if chunks else "No specific clinical documents were retrieved."

        patient_summary = (
            f"Name: {patient_context.get('name', 'Unknown')}\n"
            f"Conditions: {', '.join(patient_context.get('conditions', [])) or 'None'}\n"
            f"Medications: {', '.join(patient_context.get('medications', [])) or 'None'}\n"
            f"Allergies: {', '.join(patient_context.get('allergies', [])) or 'None'}"
        )

        lang_instruction = _LANG_NAMES.get(language, language)
        disclaimer_instruction = (
            "End with this Arabic disclaimer: تنبيه طبي: هذه المعلومات للتثقيف فقط ولا تغني عن استشارة الطبيب قبل اتخاذ أي قرار طبي."
            if language == "ar"
            else "End with this disclaimer: ⚕️ *This information is for educational purposes only. Always consult your physician before making any medical decisions.*"
        )

        user_content = f"""{_ANSWER_SYSTEM}

## Retrieved Clinical Context:
{context_text}

## Patient Record:
{patient_summary}

## Patient Question (original language):
{query}

## Search query used (English):
{english_query}

Answer in {lang_instruction}. Use the context only.
{disclaimer_instruction}"""

        messages = [
            {"role": "system", "content": _ANSWER_SYSTEM},
            {"role": "user", "content": user_content},
        ]

        if settings.primary_llm_enabled:
            return await self._llm.chat(messages, temperature=0.2, max_tokens=1024)

        if self._gemini:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._gemini.generate_content(
                    user_content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2, max_output_tokens=1024,
                    ),
                ),
            )
            return response.text.strip()

        raise RAGAgentError(detail="No LLM configured for RAG generation.")

    @staticmethod
    def _merge_results(
        clinical: list[SearchResult],
        memory: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        chunks = ClinicalRAGAgent._search_results_to_chunks(clinical)
        chunks.extend(memory)
        return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)[: settings.RAG_RERANK_TOP_N]

    @staticmethod
    def _search_results_to_chunks(results: list[SearchResult]) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                text=r.text,
                source=r.source,
                page=r.page,
                relevance_score=r.relevance_score,
                metadata=r.metadata,
            )
            for r in results
        ]


_LANG_NAMES = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "es": "Spanish",
}
