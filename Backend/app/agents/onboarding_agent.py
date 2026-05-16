"""
app/agents/onboarding_agent.py
───────────────────────────────
Onboarding Profiler Agent — turns a registration form into a conversation.

Model : Mixtral 8x7B via Groq
Role  : Collect patient profile data through natural dialogue.
        Returns structured PatientProfileData when all required fields are gathered.

Field collection order:
  1. full_name  2. date_of_birth  3. gender
  4. chronic_conditions  5. current_medications  6. allergies
  7. emergency_contact  (optional — asked last)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from groq import AsyncGroq

from app.agents.base import BaseAgent, llm_retry
from app.core.exceptions import AgentError


# ── Structured output ──────────────────────────────────────────────────────────
@dataclass
class PatientProfileData:
    """Accumulated patient data. None = not yet collected."""
    full_name:           Optional[str]       = None
    date_of_birth:       Optional[str]       = None   # "YYYY-MM-DD"
    gender:              Optional[str]       = None
    chronic_conditions:  list[str]           = field(default_factory=list)
    current_medications: list[dict]          = field(default_factory=list)
    allergies:           list[str]           = field(default_factory=list)
    emergency_contact:   Optional[dict]      = None
    language:            str                 = "en"

    @property
    def required_fields_complete(self) -> bool:
        """Minimum viable profile — emergency contact is optional."""
        return all([
            self.full_name,
            self.date_of_birth,
            self.chronic_conditions is not None,   # empty list is fine
            self.allergies is not None,
        ])

    @property
    def missing_fields(self) -> list[str]:
        out = []
        if not self.full_name:          out.append("full_name")
        if not self.date_of_birth:      out.append("date_of_birth")
        if not self.gender:             out.append("gender")
        # conditions/meds/allergies can be empty lists — check if asked
        return out

    def to_dict(self) -> dict:
        return {
            "full_name":           self.full_name,
            "date_of_birth":       self.date_of_birth,
            "gender":              self.gender,
            "chronic_conditions":  self.chronic_conditions,
            "current_medications": self.current_medications,
            "allergies":           self.allergies,
            "emergency_contact":   self.emergency_contact,
            "language":            self.language,
        }


@dataclass
class OnboardingTurn:
    next_question:    str
    profile_complete: bool
    profile_data:     PatientProfileData
    collected_fields: list[str]
    missing_fields:   list[str]


# ── Prompts ────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a warm, professional medical AI assistant for Nerve AI — a personal health management platform.
Your current task is to onboard a new patient by collecting their medical profile through natural conversation.

LANGUAGE RULE: Detect the patient's language and respond ENTIRELY in that language. Never mix languages.

FIELDS TO COLLECT (in order):
1. full_name       — Ask naturally: "What's your full name?"
2. date_of_birth   — "What's your date of birth?" (store as YYYY-MM-DD)
3. gender          — "What gender do you identify as?"
4. chronic_conditions — "Do you have any chronic conditions like diabetes, hypertension, or asthma?"
5. current_medications — "Are you currently taking any medications? If so, what are they, and at what dosage?"
6. allergies       — "Do you have any known allergies to medications or foods?"
7. emergency_contact — "Could you share an emergency contact? (name, phone number, and their relationship to you)"

TONE: Warm, concise, one question at a time. Never make the patient feel like they're filling out a form.
IMPORTANT: After every patient reply, extract ALL data from it — even if they volunteered multiple answers.

You must ALWAYS respond with valid JSON in this exact format:
{
  "next_question": "<your next question or closing message in the patient's language>",
  "profile_complete": <true|false>,
  "extracted": {
    "full_name": "<string or null>",
    "date_of_birth": "<YYYY-MM-DD or null>",
    "gender": "<string or null>",
    "chronic_conditions": ["<condition>"],
    "current_medications": [{"name": "<>", "dosage": "<>", "frequency": "<>"}],
    "allergies": ["<allergy>"],
    "emergency_contact": {"name": "<>", "phone": "<>", "relationship": "<>"} or null
  },
  "collected_fields": ["<field1>", "<field2>"],
  "missing_fields": ["<field1>"]
}

Set profile_complete=true only when all 6 required fields have been collected (emergency_contact is optional).
Do NOT set profile_complete=true prematurely."""


# ── Agent ──────────────────────────────────────────────────────────────────────
class OnboardingAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        self._client = AsyncGroq(api_key=self.settings.GROQ_API_KEY)
        self._model  = self.settings.GROQ_ONBOARDING_MODEL

    async def run(
        self,
        message: str,
        session_history: list[dict],
        current_profile: PatientProfileData,
        language: str = "en",
    ) -> OnboardingTurn:
        """
        Process one patient message in the onboarding conversation.

        Args:
            message         : The patient's latest reply.
            session_history : Full onboarding conversation history.
            current_profile : The profile accumulated so far (passed in from Redis).
            language        : Language detected by the Router agent.
        """
        t0    = self._now_ms()
        trace = self._start_trace("onboarding_agent", {"message": message[:200]})

        turn = await self._process_turn(message, session_history, current_profile, language)

        self._log_generation(
            trace, "onboarding_turn", self._model,
            prompt=message, completion=turn.next_question,
            latency_ms=self._elapsed(t0),
            metadata={"profile_complete": turn.profile_complete},
        )
        self.logger.info(
            "onboarding.turn",
            profile_complete=turn.profile_complete,
            collected=turn.collected_fields,
            missing=turn.missing_fields,
            latency_ms=self._elapsed(t0),
        )
        return turn

    @llm_retry(max_attempts=3, reraise_as=AgentError)
    async def _process_turn(
        self,
        message: str,
        history: list[dict],
        profile: PatientProfileData,
        language: str,
    ) -> OnboardingTurn:
        # Inject current profile state into system context
        profile_state_note = (
            f"\nCURRENT PROFILE STATE:\n{json.dumps(profile.to_dict(), ensure_ascii=False)}\n"
            f"Language detected: {language}\n"
            f"Missing required fields: {profile.missing_fields or 'none — consider completing'}"
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT + profile_state_note},
            *history,
            {"role": "user", "content": message},
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.4,
            max_tokens=600,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Graceful fallback — ask the last unanswered question again
            self.logger.warning("onboarding.json_parse_failed", raw=raw[:200])
            return OnboardingTurn(
                next_question="I'm sorry, I didn't catch that. Could you repeat?",
                profile_complete=False,
                profile_data=profile,
                collected_fields=list(profile.missing_fields),
                missing_fields=profile.missing_fields,
            )

        # Merge extracted fields into existing profile
        extracted = data.get("extracted", {})
        updated   = self._merge_profile(profile, extracted)
        updated.language = language

        return OnboardingTurn(
            next_question=data.get("next_question", "Could you continue?"),
            profile_complete=bool(data.get("profile_complete", False)),
            profile_data=updated,
            collected_fields=data.get("collected_fields", []),
            missing_fields=data.get("missing_fields", updated.missing_fields),
        )

    # ── Helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _merge_profile(
        current: PatientProfileData,
        extracted: dict,
    ) -> PatientProfileData:
        """
        Merge newly extracted fields into the accumulated profile.
        Never overwrites a field that already has a value with None.
        Lists are merged (deduped).
        """
        def _pick(new_val, old_val):
            """Use new if non-empty, keep old otherwise."""
            if new_val is None or new_val == "" or new_val == []:
                return old_val
            return new_val

        updated = PatientProfileData(
            full_name=_pick(extracted.get("full_name"), current.full_name),
            date_of_birth=_pick(extracted.get("date_of_birth"), current.date_of_birth),
            gender=_pick(extracted.get("gender"), current.gender),
            chronic_conditions=_merge_list(
                current.chronic_conditions, extracted.get("chronic_conditions", [])
            ),
            current_medications=_merge_medications(
                current.current_medications, extracted.get("current_medications", [])
            ),
            allergies=_merge_list(
                current.allergies, extracted.get("allergies", [])
            ),
            emergency_contact=_pick(
                extracted.get("emergency_contact"), current.emergency_contact
            ),
            language=current.language,
        )
        return updated


def _merge_list(existing: list, new_items: list) -> list:
    """Union of two lists, case-insensitive dedup."""
    combined = list(existing)
    existing_lower = {str(i).lower() for i in existing}
    for item in new_items:
        if item and str(item).lower() not in existing_lower:
            combined.append(item)
            existing_lower.add(str(item).lower())
    return combined


def _merge_medications(existing: list[dict], new_items: list[dict]) -> list[dict]:
    """Merge medication lists, dedup by name (case-insensitive)."""
    combined = list(existing)
    existing_names = {m.get("name", "").lower() for m in existing}
    for med in new_items:
        if isinstance(med, dict) and med.get("name", "").lower() not in existing_names:
            combined.append(med)
            existing_names.add(med.get("name", "").lower())
    return combined
