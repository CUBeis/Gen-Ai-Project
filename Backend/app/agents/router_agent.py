"""
app/agents/router_agent.py
───────────────────────────
Orchestrator / Router Agent — the first stop for every patient message.

Model : Llama-3 70B via Groq
Role  : Classify intent + detect language → determines which agent handles next

Returns a RouterResult with:
  - intent    : one of the IntentType enum values
  - confidence: 0.0 – 1.0
  - language  : ISO 639-1 code detected in the message ("ar", "en", "de", …)
"""
from __future__ import annotations

import json

from groq import AsyncGroq

from app.agents.base import BaseAgent, llm_retry
from app.agents.intents import IntentType
from app.core.exceptions import RouterAgentError
from app.llm.provider_utils import groq_configured
from app.orchestrator.intent_heuristics import classify_intent_heuristic


# ── Prompt ─────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a medical AI router. Your only job is to classify the patient's message into exactly one intent and detect the language.

INTENT DEFINITIONS:
- "onboarding"        : Patient is sharing personal/medical history for the first time (name, age, conditions, medications, allergies).
- "care_plan_update"  : Patient mentions adding/changing/removing a medication, appointment, exercise routine, or schedule item.
- "clinical_question" : Patient asks about symptoms, drug interactions, side effects, dosages, or medical advice.
- "image_analysis"    : Patient has uploaded or is referencing a medical image, lab result, prescription, or scan.
- "general_chat"      : Greetings, thanks, off-topic, or anything that doesn't fit above.

RULES:
- If the message contains BOTH a clinical question and a care plan update, classify as "care_plan_update".
- If an image is attached (indicated by [IMAGE_ATTACHED]), always classify as "image_analysis".
- Detect the language from the message text. Use ISO 639-1 codes: "en", "ar", "de", "fr", "es", etc.
- Confidence must reflect how certain you are (0.95+ for obvious cases, 0.6-0.8 for ambiguous).

Return ONLY this JSON object — no explanation, no markdown:
{"intent": "<intent>", "confidence": <float>, "language": "<iso_code>"}"""


# ── Data classes ───────────────────────────────────────────────────────────────
from dataclasses import dataclass

@dataclass
class RouterResult:
    intent: IntentType
    confidence: float
    language: str          # ISO 639-1: "ar", "en", "de", …

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.65


# ── Agent ──────────────────────────────────────────────────────────────────────
class RouterAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        self._use_groq = groq_configured()
        self._client = AsyncGroq(api_key=self.settings.GROQ_API_KEY) if self._use_groq else None
        self._model  = self.settings.GROQ_ROUTER_MODEL

    async def run(
        self,
        message: str,
        session_history: list[dict],
        has_image: bool = False,
    ) -> RouterResult:
        """
        Classify a patient message.

        Args:
            message        : The raw user message text.
            session_history: Last N messages from short-term memory (for context).
            has_image      : Whether the request carries an image payload.
        """
        t0 = self._now_ms()
        trace = self._start_trace("router_agent", input_data={"message": message[:200]})

        # Append an image marker so the model knows an attachment is present
        augmented_message = message
        if has_image:
            augmented_message = "[IMAGE_ATTACHED] " + message

        result = await self._classify(augmented_message, session_history)

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "router_classify", self._model,
            prompt=augmented_message, completion=json.dumps(result.__dict__),
            latency_ms=latency,
        )
        self.logger.info(
            "router.classified",
            intent=result.intent,
            confidence=result.confidence,
            language=result.language,
            latency_ms=latency,
        )
        return result

    @llm_retry(max_attempts=3, reraise_as=RouterAgentError)
    async def _classify(
        self,
        message: str,
        history: list[dict],
    ) -> RouterResult:
        if not self._use_groq:
            intent, confidence, language = classify_intent_heuristic(message)
            return RouterResult(
                intent=IntentType(intent),
                confidence=confidence,
                language=language,
            )

        # Use the last 3 exchanges for routing context (cheap + effective)
        context = history[-6:] if len(history) >= 6 else history

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *context,
            {"role": "user", "content": message},
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.0,         # deterministic
            max_tokens=80,           # tiny — we only need the JSON object
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.warning("router.json_parse_failed", raw=raw)
            raise exc

        # Validate intent
        intent_str = data.get("intent", "general_chat")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            self.logger.warning("router.unknown_intent", raw_intent=intent_str)
            intent = IntentType.GENERAL_CHAT

        return RouterResult(
            intent=intent,
            confidence=float(data.get("confidence", 0.5)),
            language=str(data.get("language", "en")).lower()[:5],
        )
