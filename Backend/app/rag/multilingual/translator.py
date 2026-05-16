"""
app/rag/multilingual/translator.py
──────────────────────────────────
Auto-translate user input to English for RAG retrieval, then respond in the user's language.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import structlog

from app.core.config import settings
from app.llm.factory import get_chat_llm

logger = structlog.get_logger(__name__)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
_LANG_NAMES = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ur": "Urdu",
    "hi": "Hindi",
}


@dataclass
class TranslationResult:
    original_text: str
    english_text: str
    detected_language: str
    was_translated: bool


class MultilingualLayer:
    """
    Translates non-English queries to English before retrieval.
    Clinical answers are generated in the patient's language.
    """

    def __init__(self, llm=None) -> None:
        self._llm = llm or get_chat_llm()

    def detect_language(self, text: str, hint: Optional[str] = None) -> str:
        if hint and hint != "auto":
            return hint
        if _ARABIC_RE.search(text):
            return "ar"
        return "en"

    async def to_english(self, text: str, source_language: str) -> TranslationResult:
        detected = self.detect_language(text, source_language)
        if detected == "en":
            return TranslationResult(
                original_text=text,
                english_text=text,
                detected_language="en",
                was_translated=False,
            )

        lang_name = _LANG_NAMES.get(detected, detected)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a medical translation assistant. "
                    "Translate the user message to English for clinical search. "
                    "Preserve medical terms. Return ONLY the English translation."
                ),
            },
            {"role": "user", "content": f"Translate from {lang_name} to English:\n\n{text}"},
        ]

        try:
            english = await self._llm.chat(messages, temperature=0.0, max_tokens=512)
            logger.info(
                "multilingual.translated_to_english",
                source=detected,
                original_len=len(text),
            )
            return TranslationResult(
                original_text=text,
                english_text=english.strip() or text,
                detected_language=detected,
                was_translated=True,
            )
        except Exception as exc:
            logger.warning("multilingual.translate_failed", error=str(exc))
            return TranslationResult(
                original_text=text,
                english_text=text,
                detected_language=detected,
                was_translated=False,
            )
