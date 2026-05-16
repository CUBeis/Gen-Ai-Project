"""
app/memory/short_term.py
─────────────────────────
Short-term session memory — Redis sliding window.

Stores the last N messages of an active conversation so agents have
conversational context (pronoun resolution, follow-up questions, etc.)

Key schema per session:
  session:{id}:history  → Redis list  — capped message log
  session:{id}:extra    → Redis hash  — arbitrary per-session KV store
  session:{id}:count    → Redis int   — total messages ever sent (not capped)

The :count key is separate from the list length because ltrim discards old
messages. The pipeline uses the running count to trigger memory extraction
every N messages, regardless of window size.
"""
from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class ShortTermMemory:
    """
    Redis-backed sliding window conversation memory.
    One instance shared across all sessions — each session_id is an isolated namespace.
    """

    def __init__(self) -> None:
        self._redis:  Optional[aioredis.Redis] = None
        self._window  = settings.SESSION_WINDOW_SIZE
        self._ttl     = settings.SESSION_TTL_SECONDS

    # ── Redis connection ───────────────────────────────────────────────────────
    def _r(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
        return self._redis

    # ── Key builders ───────────────────────────────────────────────────────────
    @staticmethod
    def _hkey(sid: str) -> str: return f"session:{sid}:history"
    @staticmethod
    def _ekey(sid: str) -> str: return f"session:{sid}:extra"
    @staticmethod
    def _ckey(sid: str) -> str: return f"session:{sid}:count"

    # ── History ────────────────────────────────────────────────────────────────
    async def get_history(self, session_id: str) -> list[dict]:
        """Return the sliding-window message list. Returns [] on Redis failure."""
        try:
            raw = await self._r().lrange(self._hkey(session_id), 0, -1)
            return [json.loads(m) for m in raw]
        except Exception as exc:
            logger.warning("short_term.get_history_failed",
                           session_id=session_id, error=str(exc))
            return []

    async def append(self, session_id: str, messages: list[dict]) -> None:
        """
        Append messages, cap at WINDOW_SIZE, reset TTL.
        Also increments the running message counter.
        Never raises — memory failure must not crash the pipeline.
        """
        if not messages:
            return
        try:
            r   = self._r()
            hk  = self._hkey(session_id)
            ck  = self._ckey(session_id)
            pipe = r.pipeline()
            for msg in messages:
                pipe.rpush(hk, json.dumps(msg, ensure_ascii=False))
            pipe.ltrim(hk, -self._window, -1)
            pipe.expire(hk, self._ttl)
            pipe.incrby(ck, len(messages))
            pipe.expire(ck, self._ttl)
            await pipe.execute()
        except Exception as exc:
            logger.warning("short_term.append_failed",
                           session_id=session_id, error=str(exc))

    async def length(self, session_id: str) -> int:
        """
        Return the TOTAL messages ever sent in this session (not capped by window).
        Used by the pipeline to trigger memory extraction every N messages.
        """
        try:
            val = await self._r().get(self._ckey(session_id))
            return int(val) if val else 0
        except Exception:
            return 0

    async def clear(self, session_id: str) -> None:
        """Delete all keys for a session (called on logout or explicit reset)."""
        try:
            await self._r().delete(
                self._hkey(session_id),
                self._ekey(session_id),
                self._ckey(session_id),
            )
        except Exception as exc:
            logger.warning("short_term.clear_failed",
                           session_id=session_id, error=str(exc))

    async def session_exists(self, session_id: str) -> bool:
        try:
            return bool(await self._r().exists(self._hkey(session_id)))
        except Exception:
            return False

    # ── Extra per-session data (onboarding profile, etc.) ─────────────────────
    async def get_extra(self, session_id: str, key: str) -> Optional[str]:
        """
        Read a field from the session's extra hash.
        Used by OnboardingAgent to persist accumulated profile state
        across multiple HTTP request/response cycles.
        """
        try:
            return await self._r().hget(self._ekey(session_id), key)
        except Exception as exc:
            logger.warning("short_term.get_extra_failed",
                           session_id=session_id, key=key, error=str(exc))
            return None

    async def set_extra(self, session_id: str, key: str, value: str) -> None:
        """Write a field to the session's extra hash. Value must be a string."""
        try:
            r  = self._r()
            ek = self._ekey(session_id)
            await r.hset(ek, key, value)
            await r.expire(ek, self._ttl)
        except Exception as exc:
            logger.warning("short_term.set_extra_failed",
                           session_id=session_id, key=key, error=str(exc))

    async def get_all_extra(self, session_id: str) -> dict[str, str]:
        try:
            return await self._r().hgetall(self._ekey(session_id)) or {}
        except Exception:
            return {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    async def close(self) -> None:
        """Close the connection pool (called in app shutdown lifespan)."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
