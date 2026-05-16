"""
app/llm/openrouter_client.py
────────────────────────────
OpenAI-compatible chat client for OpenRouter (Gemini, DeepSeek, etc.).
"""
from __future__ import annotations

from typing import Optional

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import LLMProviderError

logger = structlog.get_logger(__name__)


class OpenRouterClient:
    """Async chat completions via OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or settings.OPENROUTER_API_KEY
        self._base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        if self._base_url.endswith("/chat/completions"):
            self._base_url = self._base_url.rsplit("/chat/completions", 1)[0]
        self._model = model or settings.OPENROUTER_MODEL

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout: float = 120.0,
    ) -> str:
        if not self._api_key:
            raise LLMProviderError(detail="OPENROUTER_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": settings.APP_NAME,
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            logger.error("openrouter.request_failed", error=str(exc), model=self._model)
            raise LLMProviderError(detail=f"OpenRouter API error: {exc}") from exc
