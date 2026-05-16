"""
app/db/models/care_plan.py
───────────────────────────
CarePlan ORM model — one row per patient (1:1 relationship).

The activities column is a JSONB array, not a separate table.
This is an intentional denormalisation: care plan activities are always
read and written as a unit (the entire schedule), never queried individually
at the SQL level. The frontend and agents always operate on the full list.

Activity object structure (enforced at the Pydantic schema layer, not SQL):
  {
    "id":             "uuid-string",
    "type":           "medication" | "exercise" | "appointment" | "measurement",
    "name":           "Metformin 500mg",
    "time":           "08:00",
    "days":           ["daily"] or ["Mon", "Wed", "Fri"],
    "notes":          "Take with food",
    "completed_today": false
  }

The completed_today flag is reset to false every midnight by a Celery beat task.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CarePlan(Base):
    __tablename__ = "care_plans"

    # ── Primary key ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Foreign key (1:1 via unique constraint) ────────────────────────────────
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Plan metadata ─────────────────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="e.g. 'Daily Health Plan — Ahmed'"
    )

    # ── Activities (denormalised JSONB array) ─────────────────────────────────
    activities: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        nullable=False,
        comment="Array of activity objects — see module docstring for schema",
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
    patient: Mapped["Patient"] = relationship(   # type: ignore[name-defined]
        "Patient",
        back_populates="care_plan",
    )

    # ── Convenience ───────────────────────────────────────────────────────────
    @property
    def activity_count(self) -> int:
        return len(self.activities or [])

    @property
    def medication_activities(self) -> list[dict]:
        return [a for a in (self.activities or []) if a.get("type") == "medication"]

    @property
    def exercise_activities(self) -> list[dict]:
        return [a for a in (self.activities or []) if a.get("type") == "exercise"]

    def get_activity_by_id(self, activity_id: str) -> dict | None:
        for activity in (self.activities or []):
            if str(activity.get("id")) == activity_id:
                return activity
        return None

    def reset_daily_completion(self) -> None:
        """
        Reset completed_today=False for all activities.
        Called by Celery beat task at midnight.
        """
        if self.activities:
            self.activities = [
                {**a, "completed_today": False}
                for a in self.activities
            ]

    def __repr__(self) -> str:
        return (
            f"<CarePlan id={self.id} "
            f"patient={self.patient_id} "
            f"activities={self.activity_count}>"
        )