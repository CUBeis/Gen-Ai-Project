"""Helpers to detect which LLM providers are configured."""
from __future__ import annotations

from app.core.config import settings

_PLACEHOLDER_KEYS = {"", "CHANGE_ME", "gsk_CHANGE_ME", "AIza_CHANGE_ME"}


def is_configured(key: str | None) -> bool:
    return bool(key and key.strip() not in _PLACEHOLDER_KEYS)


def groq_configured() -> bool:
    return is_configured(settings.GROQ_API_KEY)


def deepseek_configured() -> bool:
    return is_configured(settings.DEEPSEEK_API_KEY)


def openrouter_configured() -> bool:
    return is_configured(settings.OPENROUTER_API_KEY)


def primary_llm_configured() -> bool:
    provider = (settings.RAG_LLM_PROVIDER or "openrouter").lower()
    if provider == "openrouter":
        return openrouter_configured()
    if provider == "deepseek":
        return deepseek_configured()
    if provider == "gemini":
        return is_configured(settings.GEMINI_API_KEY)
    return openrouter_configured()


def cohere_configured() -> bool:
    return is_configured(settings.COHERE_API_KEY)
