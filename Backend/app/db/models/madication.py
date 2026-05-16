"""
app/db/models/medication.py
────────────────────────────
Medication ORM model — one row per prescribed medication per patient.

Soft-delete pattern: medications are never hard-deleted.
Setting is_active=False preserves medication history for:
  - Drug interaction checks against past medications
  - Audit trail (when was a medication stopped)
  - RAG context building

The times JSONB column stores scheduled administration times:
  ["08:00", "14:00", "20:00"]
This is read directly by the frontend to populate the daily schedule.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Medication(Base):
    __tablename__ = "medications"

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

    # ── Medication details ────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="e.g. '500mg', '10mg/5ml'"
    )
    frequency: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="e.g. 'twice daily', 'every 8 hours'"
    )
    times: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False,
        comment='Scheduled times: ["08:00", "20:00"]'
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date:   Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Prescriber info ───────────────────────────────────────────────────────
    prescribing_doctor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Soft-delete flag ──────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
        index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    patient: Mapped["Patient"] = relationship(  # type: ignore[name-defined]
        "Patient",
        back_populates="medications",
    )

    # ── Convenience ───────────────────────────────────────────────────────────
    @property
    def display_name(self) -> str:
        """e.g. 'Metformin 500mg — twice daily'"""
        parts = [self.name]
        if self.dosage:
            parts.append(self.dosage)
        if self.frequency:
            parts.append(f"— {self.frequency}")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"<Medication id={self.id} name={self.name!r} "
            f"patient={self.patient_id} active={self.is_active}>"
        )