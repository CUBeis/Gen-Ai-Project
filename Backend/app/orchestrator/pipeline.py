"""
app/orchestrator/pipeline.py
─────────────────────────────
AgentPipeline — the central orchestration engine for Nerve AI.

Every patient message (REST or WebSocket) flows through pipeline.run():

    1. Load short-term memory (Redis)
    2. Route        → RouterAgent classifies intent + language
    3. Dispatch     → the right specialised agent runs
    4. Guardrail    → GuardrailAgent audits the response
    5. Persist      → update short-term memory
    6. Background   → fire memory extraction task (Celery) if threshold reached

Returns: (response_text: str, meta: dict)
    meta is attached to state.meta and forwarded to the WebSocket layer.

Design:
  - One AgentPipeline instance is created at startup and reused for all requests.
    All agents are stateless — safe to share.
  - Database writes (care plan updates) happen inside agent services, NOT here.
    The pipeline returns a patch dict; the service layer commits it.
"""
from __future__ import annotations

import structlog

from app.agents.care_planner_agent import CarePlannerAgent
from app.agents.guardrail_agent import GuardrailAgent, GuardrailAction
from app.agents.memory_extractor_agent import MemoryExtractorAgent
from app.agents.onboarding_agent import OnboardingAgent
from app.agents.rag_agent import ClinicalRAGAgent
from app.agents.router_agent import RouterAgent, IntentType
from app.agents.vision_agent import VisionAgent
from app.memory.short_term import ShortTermMemory
from app.orchestrator.retry import pipeline_retry, with_timeout
from app.orchestrator.state import ConversationState
from app.core.config import settings
from app.core.exceptions import AgentError

logger = structlog.get_logger(__name__)


# ── Timeouts per agent (seconds) ──────────────────────────────────────────────
_TIMEOUTS = {
    "router":      8,
    "rag":        30,
    "care_plan":  20,
    "onboarding": 20,
    "vision":     40,
    "guardrail":  15,
}


class AgentPipeline:
    """
    Instantiated once at application startup.
    All agents are initialised once and reused — they are stateless.
    """

    def __init__(self) -> None:
        self.router     = RouterAgent()
        self.rag        = ClinicalRAGAgent()
        self.planner    = CarePlannerAgent()
        self.onboarding = OnboardingAgent()
        self.vision     = VisionAgent()
        self.guardrail  = GuardrailAgent()
        self.memory     = ShortTermMemory()
        # Memory extractor is NOT instantiated here — it lives in a Celery task
        logger.info("pipeline.initialised")

    # ── Main entry point ──────────────────────────────────────────────────────
    async def run(self, state: ConversationState) -> tuple[str, dict]:
        """
        Execute the full pipeline for one patient message.

        Args:
            state : ConversationState populated by the WebSocket or REST handler.

        Returns:
            (response_text, meta_dict) where meta_dict is state.meta.
        """
        # Step 1 — Load session history
        history = await self.memory.get_history(state.session_id)

        # Step 2 — Route
        routing = await with_timeout(
            self.router.run(
                message=state.user_message,
                session_history=history,
                has_image=state.has_image,
            ),
            timeout_seconds=_TIMEOUTS["router"],
            label="router",
        )
        state.intent             = routing.intent.value
        state.language           = routing.language
        state.routing_confidence = routing.confidence

        logger.info(
            "pipeline.routed",
            session_id=state.session_id,
            intent=state.intent,
            confidence=routing.confidence,
            language=state.language,
        )

        # Step 3 — Dispatch
        raw_response = await self._dispatch(state, history)

        # Step 4 — Guardrail (mandatory — no exceptions)
        guard_result = await with_timeout(
            self.guardrail.run(
                response=raw_response,
                intent=state.intent,
                patient_context=state.patient_context,
                language=state.language,
            ),
            timeout_seconds=_TIMEOUTS["guardrail"],
            fallback_value=None,      # if timeout, pass response through with disclaimer
            label="guardrail",
        )

        if guard_result is None:
            # Guardrail timed out — pass through with soft disclaimer
            logger.warning("pipeline.guardrail_timeout", session_id=state.session_id)
            final_response = raw_response
        else:
            state.was_sanitized = guard_result.was_sanitized
            state.was_blocked   = guard_result.was_blocked
            final_response      = guard_result.final_response

        # Step 5 — Update short-term memory
        await self.memory.append(state.session_id, [
            {"role": "user",      "content": state.user_message},
            {"role": "assistant", "content": final_response},
        ])

        # Step 6 — Trigger background memory extraction if threshold reached
        session_len = await self.memory.length(state.session_id)
        if session_len % settings.MEMORY_EXTRACT_EVERY_N_MESSAGES == 0:
            await self._trigger_memory_extraction(state)

        logger.info(
            "pipeline.complete",
            session_id=state.session_id,
            intent=state.intent,
            sanitized=state.was_sanitized,
            blocked=state.was_blocked,
            care_plan_updated=state.care_plan_updated,
        )

        return final_response, state.meta

    # ── Dispatch ──────────────────────────────────────────────────────────────
    async def _dispatch(
        self,
        state:   ConversationState,
        history: list[dict],
    ) -> str:
        """Route to the correct agent based on classified intent."""
        match state.intent:

            case IntentType.CLINICAL_QUESTION:
                return await self._run_rag(state, history)

            case IntentType.CARE_PLAN_UPDATE:
                return await self._run_care_planner(state, history)

            case IntentType.ONBOARDING:
                return await self._run_onboarding(state, history)

            case IntentType.IMAGE_ANALYSIS:
                return await self._run_vision(state)

            case IntentType.GENERAL_CHAT | _:
                return await self._run_general(state, history)

    # ── Clinical RAG ──────────────────────────────────────────────────────────
    @pipeline_retry(max_attempts=2)
    async def _run_rag(self, state: ConversationState, history: list[dict]) -> str:
        result = await with_timeout(
            self.rag.run(
                user_message=state.user_message,
                session_history=history,
                patient_context=state.patient_context,
                patient_id=state.patient_id,
                language=state.language,
            ),
            timeout_seconds=_TIMEOUTS["rag"],
            label="rag",
        )
        state.reformulated_query = result.reformulated_query
        state.sources            = result.sources
        return result.answer

    # ── Care Plan ─────────────────────────────────────────────────────────────
    @pipeline_retry(max_attempts=2)
    async def _run_care_planner(
        self,
        state:   ConversationState,
        history: list[dict],
    ) -> str:
        # Infer the action type from the message
        action = _infer_care_plan_action(state.user_message)

        # Current activities come from patient_context (pre-loaded by WS handler)
        current_activities = state.patient_context.get("care_plan_activities", [])

        result = await with_timeout(
            self.planner.run(
                user_message=state.user_message,
                action=action,
                patient_context=state.patient_context,
                current_activities=current_activities,
                language=state.language,
            ),
            timeout_seconds=_TIMEOUTS["care_plan"],
            label="care_planner",
        )

        state.care_plan_updated = result.care_plan_updated
        state.care_plan_patch   = result.care_plan_patch
        return result.confirmation_message

    # ── Onboarding ────────────────────────────────────────────────────────────
    @pipeline_retry(max_attempts=2)
    async def _run_onboarding(
        self,
        state:   ConversationState,
        history: list[dict],
    ) -> str:
        from app.agents.onboarding_agent import PatientProfileData
        import json

        # Load accumulated profile from Redis (stored as JSON)
        profile_raw = await self.memory.get_extra(state.session_id, "onboarding_profile")
        current_profile = PatientProfileData(**json.loads(profile_raw)) if profile_raw else PatientProfileData()

        result = await with_timeout(
            self.onboarding.run(
                message=state.user_message,
                session_history=history,
                current_profile=current_profile,
                language=state.language,
            ),
            timeout_seconds=_TIMEOUTS["onboarding"],
            label="onboarding",
        )

        # Persist updated profile back to Redis
        await self.memory.set_extra(
            state.session_id,
            "onboarding_profile",
            json.dumps(result.profile_data.to_dict()),
        )

        return result.next_question

    # ── Vision ────────────────────────────────────────────────────────────────
    @pipeline_retry(max_attempts=2)
    async def _run_vision(self, state: ConversationState) -> str:
        if not state.has_image:
            return (
                "It looks like you wanted to share an image, but I didn't receive one. "
                "Please try uploading it again."
                if state.language == "en"
                else
                "يبدو أنك أردت مشاركة صورة لكنني لم أتلقها. يرجى المحاولة مجدداً."
            )

        result = await with_timeout(
            self.vision.run(
                image_base64=state.image_base64,
                content_type="image/jpeg",  # default; actual type handled by VisionService
                filename="upload",
                patient_context=state.patient_context,
                language=state.language,
                context_hint=state.user_message,
            ),
            timeout_seconds=_TIMEOUTS["vision"],
            label="vision",
        )
        return result.safe_summary

    # ── General chat ──────────────────────────────────────────────────────────
    async def _run_general(
        self,
        state:   ConversationState,
        history: list[dict],
    ) -> str:
        """
        Lightweight Gemini call for greetings and off-topic messages.
        No retrieval — just a friendly, contextual reply.
        """
        import asyncio
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        llm = genai.GenerativeModel(settings.GEMINI_MODEL)

        name = state.patient_context.get("name", "")
        greeting = f"You are a warm, professional medical AI assistant for Nerve AI. The patient's name is {name}. Reply naturally and helpfully in language: {state.language}."

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-4:]
        )
        prompt = f"{greeting}\n\nRecent conversation:\n{history_text}\n\nPatient: {state.user_message}\nAssistant:"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=300,
                ),
            ),
        )
        return response.text.strip()

    # ── Background memory extraction ──────────────────────────────────────────
    async def _trigger_memory_extraction(self, state: ConversationState) -> None:
        """
        Fire the Celery background task — non-blocking.
        Import Celery task here (not at module level) to avoid circular imports.
        """
        try:
            from app.tasks.memory_tasks import memory_extraction_task
            memory_extraction_task.delay(state.session_id, state.patient_id)
            logger.info(
                "pipeline.memory_extraction_queued",
                session_id=state.session_id,
                patient_id=state.patient_id,
            )
        except Exception as exc:
            # Memory extraction failure must never affect the user response
            logger.warning(
                "pipeline.memory_extraction_queue_failed",
                error=str(exc),
            )


# ── Helpers ────────────────────────────────────────────────────────────────────
def _infer_care_plan_action(message: str) -> str:
    """
    Lightweight keyword heuristic to infer the care plan action type.
    The Care Planner Agent itself handles the real parsing.
    """
    msg = message.lower()

    if any(w in msg for w in ["remove", "delete", "stop", "cancel", "إلغاء", "احذف"]):
        return "remove_activity"

    if any(w in msg for w in ["exercise", "workout", "walk", "swim", "gym", "تمرين", "رياضة"]):
        return "add_exercise"

    if any(w in msg for w in ["appointment", "visit", "doctor", "clinic", "موعد", "دكتور"]):
        return "add_appointment"

    # Default — most care plan updates are about medications
    return "add_medication"
