"""
app/orchestrator/retry.py
──────────────────────────
Retry utilities at the orchestrator level.

BaseAgent already has @llm_retry for individual LLM calls.
This module handles higher-level concerns:

  - Pipeline-level fallback  : if the primary agent fails, try a fallback path
  - Timeout guard            : cancel an agent call that exceeds a deadline
  - Circuit breaker          : stop calling a failing provider temporarily

Usage in pipeline.py:
    result = await with_timeout(rag_agent.run(...), timeout_seconds=20)
    result = await with_fallback(primary(), fallback())
"""
from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Awaitable, Callable, TypeVar

import structlog

from app.core.exceptions import AgentError, LLMProviderError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ── Timeout guard ─────────────────────────────────────────────────────────────
async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    fallback_value: T | None = None,
    label: str = "agent_call",
) -> T:
    """
    Run a coroutine with a timeout.

    If it exceeds `timeout_seconds`:
      - Logs a warning.
      - Returns `fallback_value` if provided.
      - Raises AgentError if no fallback is given.

    Example:
        result = await with_timeout(rag_agent.run(...), timeout_seconds=25)
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(
            "orchestrator.timeout",
            label=label,
            timeout_seconds=timeout_seconds,
        )
        if fallback_value is not None:
            return fallback_value
        raise AgentError(
            detail=f"The AI service ({label}) took too long to respond. Please try again."
        )


# ── Fallback chain ────────────────────────────────────────────────────────────
async def with_fallback(
    primary: Awaitable[T],
    fallback: Awaitable[T],
    label: str = "agent_call",
) -> T:
    """
    Try `primary`; if it raises, run `fallback` instead.
    Both failures propagate the fallback's exception.

    Example:
        result = await with_fallback(
            rag_agent.run(...),
            general_response_agent.run(...),
            label="rag_with_fallback",
        )
    """
    try:
        return await primary
    except (AgentError, LLMProviderError, Exception) as primary_exc:
        logger.warning(
            "orchestrator.primary_failed_trying_fallback",
            label=label,
            primary_error=str(primary_exc),
        )
        return await fallback


# ── Pipeline-level retry decorator ────────────────────────────────────────────
def pipeline_retry(
    max_attempts: int = 2,
    delay_seconds: float = 2.0,
    exceptions: tuple = (AgentError, LLMProviderError),
):
    """
    Decorator for full pipeline sub-steps (not individual LLM calls).
    Use this on methods in pipeline.py that call multiple agents in sequence.

    Example:
        @pipeline_retry(max_attempts=2)
        async def _run_clinical_question(self, state): ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "orchestrator.pipeline_retry",
                            fn=fn.__name__,
                            attempt=attempt,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay_seconds * attempt)
            raise last_exc  # type: ignore
        return wrapper
    return decorator


# ── Circuit breaker (simple, in-process) ─────────────────────────────────────
class CircuitBreaker:
    """
    Simple in-process circuit breaker for LLM provider calls.

    States: CLOSED (normal) → OPEN (blocking) → HALF-OPEN (testing)

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        async def call_groq():
            async with breaker:
                return await groq_client.chat(...)
    """

    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int   = 5,
        recovery_timeout:  float = 60.0,
        label:             str   = "provider",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.label             = label
        self._failures         = 0
        self._state            = self.CLOSED
        self._opened_at: float | None = None

    async def __aenter__(self):
        if self._state == self.OPEN:
            elapsed = time.monotonic() - (self._opened_at or 0)
            if elapsed >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                logger.info("circuit_breaker.half_open", label=self.label)
            else:
                raise AgentError(
                    detail=f"The AI service ({self.label}) is temporarily unavailable. "
                           f"Please try again in {int(self.recovery_timeout - elapsed)}s."
                )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._failures += 1
            if self._failures >= self.failure_threshold or self._state == self.HALF_OPEN:
                self._state     = self.OPEN
                self._opened_at = time.monotonic()
                logger.error(
                    "circuit_breaker.opened",
                    label=self.label,
                    failures=self._failures,
                )
            return False  # re-raise

        # Success
        if self._state == self.HALF_OPEN:
            logger.info("circuit_breaker.recovered", label=self.label)
        self._failures = 0
        self._state    = self.CLOSED
        return False
