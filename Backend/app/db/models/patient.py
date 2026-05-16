"""
app/db/models/patient.py
─────────────────────────
SQLAlchemy ORM models for patients and auth_users tables.

Both tables are defined here because they have a tight 1:1 relationship
and are always queried together (auth user → patient profile).

Column design notes:
  - allergies / chronic_conditions : JSONB arrays — fast PostgreSQL indexing,
    flexible schema without extra join tables
  - emergency_contact : JSONB object — low query frequency, no indexing needed
  - patient_id on AuthUser is nullable until the patient completes onboarding
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Patient(Base):
    __tablename__ = "patients"

    # ── Primary key ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        comment="FK to auth_users.id — enforced at app layer to avoid circular FK",
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # ── Medical profile (JSONB arrays) ─────────────────────────────────────────
    allergies: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    chronic_conditions: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    emergency_contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
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

    # ── Relationships ─────────────────────────────────────────────────────────
    medications: Mapped[list["Medication"]] = relationship(
        "Medication",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",          # always load with patient
    )
    care_plan: Mapped["CarePlan | None"] = relationship(
        "CarePlan",
        back_populates="patient",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="noload",            # load explicitly when needed
    )

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def active_medications(self) -> list["Medication"]:
        return [m for m in self.medications if m.is_active]

    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name={self.full_name!r}>"


class AuthUser(Base):
    __tablename__ = "auth_users"

    # ── Primary key ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Credentials ───────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # ── Link to patient profile (nullable until onboarding completes) ─────────
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuthUser id={self.id} email={self.email!r}>"