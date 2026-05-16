"""
app/llm/deepseek_client.py
──────────────────────────
OpenAI-compatible client for DeepSeek V4-Flash.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import LLMProviderError

logger = structlog.get_logger(__name__)


class DeepSeekClient:
    """Async chat completions against DeepSeek's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or settings.DEEPSEEK_API_KEY
        self._base_url = (base_url or settings.DEEPSEEK_BASE_URL).rstrip("/")
        self._model = model or settings.DEEPSEEK_MODEL

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> str:
        if not self._api_key:
            raise LLMProviderError(detail="DEEPSEEK_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
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
            logger.error("deepseek.request_failed", error=str(exc))
            raise LLMProviderError(detail=f"DeepSeek API error: {exc}") from exc

    def chat_sync(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> str:
        return asyncio.get_event_loop().run_until_complete(
            self.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        )
