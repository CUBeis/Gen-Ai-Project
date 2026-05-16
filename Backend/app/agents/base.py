"""
app/agents/base.py
───────────────────
Abstract base class every agent inherits from.

Provides:
  - Structured logging bound to the agent class name
  - Langfuse span tracing (no-op when LANGFUSE keys are absent)
  - A shared retry policy factory for LLM API calls
  - A `run()` contract every agent must implement
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.core.config import settings
from app.core.exceptions import LLMProviderError

import logging
_tenacity_logger = logging.getLogger("tenacity")


# ── Langfuse tracing (optional) ────────────────────────────────────────────────
def _get_tracer():
    """
    Return a Langfuse client if credentials are present, else a no-op stub.
    Import is deferred so missing credentials never break startup.
    """
    if not settings.langfuse_enabled:
        return _NoOpTracer()
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        return _NoOpTracer()


class _NoOpTracer:
    """Silent stand-in when Langfuse is not configured."""
    def trace(self, *a, **kw):        return _NoOpSpan()
    def span(self, *a, **kw):         return _NoOpSpan()
    def generation(self, *a, **kw):   return _NoOpSpan()
    def flush(self):                   pass

class _NoOpSpan:
    def end(self, *a, **kw):          pass
    def update(self, *a, **kw):       pass
    def span(self, *a, **kw):         return _NoOpSpan()
    def generation(self, *a, **kw):   return _NoOpSpan()
    def __enter__(self):               return self
    def __exit__(self, *a):           pass


# ── Retry policy ───────────────────────────────────────────────────────────────
def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    reraise_as: type[LLMProviderError] = LLMProviderError,
):
    """
    Decorator factory: exponential backoff for any LLM API call.

    Usage:
        @llm_retry(max_attempts=3)
        async def _call_groq(self, ...): ...
    """
    import functools

    def decorator(fn):
        retrying_fn = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
            reraise=True,
        )(fn)

        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            try:
                return await retrying_fn(self, *args, **kwargs)
            except Exception as exc:
                self.logger.error(
                    "agent.llm_call.failed_after_retries",
                    agent=self.__class__.__name__,
                    error=str(exc),
                    max_attempts=max_attempts,
                )
                raise reraise_as() from exc

        return wrapper
    return decorator


# ── Base agent ────────────────────────────────────────────────────────────────
class BaseAgent(ABC):
    """
    All Nerve AI agents inherit from this class.

    Subclasses MUST implement `run()`.
    They SHOULD use `@llm_retry()` on internal LLM call methods.
    They CAN call `self._trace_generation()` to log to Langfuse.
    """

    def __init__(self) -> None:
        self.logger: structlog.BoundLogger = structlog.get_logger(
            self.__class__.__name__
        )
        self.settings = settings
        self._tracer = _get_tracer()

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Entry point for the agent.
        Signature varies per agent — see individual implementations.
        """
        ...

    # ── Tracing helpers ────────────────────────────────────────────────────────
    def _start_trace(self, name: str, input_data: Any = None) -> Any:
        """Open a Langfuse trace. Returns a span object (or no-op)."""
        return self._tracer.trace(name=name, input=input_data)

    def _log_generation(
        self,
        trace: Any,
        name: str,
        model: str,
        prompt: str | list,
        completion: str,
        latency_ms: float,
        metadata: dict | None = None,
    ) -> None:
        """Record a single LLM call inside an existing trace."""
        try:
            trace.generation(
                name=name,
                model=model,
                prompt=prompt,
                completion=completion,
                metadata=metadata or {},
                usage={"latency_ms": latency_ms},
            ).end()
        except Exception:
            pass  # tracing must never break the application

    # ── Timing helper ──────────────────────────────────────────────────────────
    @staticmethod
    def _now_ms() -> float:
        return time.perf_counter() * 1000

    def _elapsed(self, start_ms: float) -> float:
        return round(self._now_ms() - start_ms, 2)
