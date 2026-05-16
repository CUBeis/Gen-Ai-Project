"""
app/db/models/conversation.py
──────────────────────────────
Conversation session log — lightweight audit record per chat session.

This is NOT the full message history (that lives in Redis).
This table records session metadata:
  - When the session started / ended
  - How many messages were exchanged
  - A summary extracted by the Memory Extractor Agent

Purpose:
  - Audit trail (HIPAA compliance — log of all AI interactions)
  - Trigger memory extraction on session close
  - Power the "Past Conversations" UI section
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    # ── Primary key ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Session identity ──────────────────────────────────────────────────────
    session_id: Mapped[str] = mapped_column(
        # VARCHAR — matches the Redis key format "sess_<hex>"
        type_=__import__("sqlalchemy").String(255),
        nullable=False,
        index=True,
        unique=True,
    )

    # ── Metrics ───────────────────────────────────────────────────────────────
    message_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # ── Content ───────────────────────────────────────────────────────────────
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="LLM-generated session summary — populated on session close"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ── Relationship ──────────────────────────────────────────────────────────
    patient: Mapped["Patient"] = relationship(   # type: ignore[name-defined]
        "Patient",
        back_populates="conversations",
    )

    # ── Convenience ───────────────────────────────────────────────────────────
    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def duration_minutes(self) -> float | None:
        if not self.ended_at:
            return None
        delta = self.ended_at - self.started_at
        return round(delta.total_seconds() / 60, 1)

    def close(self, summary: str | None = None) -> None:
        self.ended_at = datetime.now(timezone.utc)
        if summary:
            self.summary = summary

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} "
            f"session={self.session_id!r} "
            f"messages={self.message_count}>"
        )