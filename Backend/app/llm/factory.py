"""Factory for the primary chat LLM used by RAG and demo pipeline."""
from __future__ import annotations

from app.core.config import settings
from app.llm.deepseek_client import DeepSeekClient
from app.llm.openrouter_client import OpenRouterClient


def get_chat_llm():
    """Return the configured primary LLM client (duck-typed: async .chat(messages))."""
    provider = (settings.RAG_LLM_PROVIDER or "openrouter").lower()
    if provider == "openrouter":
        return OpenRouterClient()
    if provider == "deepseek":
        return DeepSeekClient()
    return OpenRouterClient()


def primary_llm_model_name() -> str:
    provider = (settings.RAG_LLM_PROVIDER or "openrouter").lower()
    if provider == "openrouter":
        return settings.OPENROUTER_MODEL
    if provider == "deepseek":
        return settings.DEEPSEEK_MODEL
    return settings.GEMINI_MODEL
