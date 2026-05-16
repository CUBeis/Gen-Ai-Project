"""Lightweight intent classification when Groq router is unavailable."""
from __future__ import annotations

import re

from app.agents.intents import IntentType

_SCHEDULE_KEYWORDS = re.compile(
    r"\b(schedule|timetable|reminder|plan my|make me a|daily routine|when should i take|"
    r"what time|organize my|organisation)\b",
    re.I,
)
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_ARABIC_REQUEST_RE = re.compile(r"\b(arabic|in arabic|respond in arabic|reply in arabic)\b", re.I)


def detect_language_heuristic(message: str) -> str:
    if _ARABIC_RE.search(message) or _ARABIC_REQUEST_RE.search(message):
        return "ar"
    return "en"


def classify_intent_heuristic(message: str) -> tuple[str, float, str]:
    msg = message.lower()
    language = detect_language_heuristic(message)
    if _SCHEDULE_KEYWORDS.search(message):
        return IntentType.CARE_PLAN_UPDATE.value, 0.9, language
    if any(w in msg for w in ["side effect", "symptom", "what is", "drug", "medication", "diabetes"]):
        return IntentType.CLINICAL_QUESTION.value, 0.85, language
    if any(w in msg for w in ["hello", "hi", "thanks", "thank you"]):
        return IntentType.GENERAL_CHAT.value, 0.9, language
    return IntentType.CLINICAL_QUESTION.value, 0.7, language
