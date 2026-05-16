"""
app/db/repositories/patient_repo.py
─────────────────────────────────────
Data access layer for patients and auth_users tables.

Repository pattern:
  - All SQL lives here — never in agents, services, or API routes
  - Methods are async (SQLAlchemy async session)
  - Returns ORM model instances — conversion to Pydantic happens in services
  - No business logic here — only read/write operations

Two repositories in one file because Patient and AuthUser are tightly coupled:
  PatientRepository   — CRUD for the patients table
  AuthUserRepository  — CRUD for the auth_users table
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.patient import AuthUser, Patient


# ── Patient Repository ─────────────────────────────────────────────────────────
class PatientRepository:
    """
    CRUD operations for the patients table.
    Relationships (medications, care_plan) are loaded via selectinload
    so all data is available without extra queries.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, patient_id: str) -> Optional[Patient]:
        """Fetch a patient by UUID, including active medications and care plan."""
        result = await self._db.execute(
            select(Patient)
            .options(
                selectinload(Patient.medications),
                selectinload(Patient.care_plan),
            )
            .where(Patient.id == uuid.UUID(patient_id))
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[Patient]:
        """Fetch a patient by their auth_user.id."""
        result = await self._db.execute(
            select(Patient)
            .options(
                selectinload(Patient.medications),
                selectinload(Patient.care_plan),
            )
            .where(Patient.user_id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Patient:
        """
        Insert a new patient row.

        Args:
            data: Dict of column values. Must include at least
                  full_name and user_id.

        Returns:
            The newly created Patient ORM instance.
        """
        patient = Patient(**data)
        self._db.add(patient)
        await self._db.flush()   # assign id without committing
        await self._db.refresh(patient)
        return patient

    async def update(self, patient_id: str, updates: dict) -> Optional[Patient]:
        """
        Partial update — only columns present in `updates` are changed.

        Args:
            patient_id: UUID string.
            updates   : Dict of {column_name: new_value}.

        Returns:
            Updated Patient, or None if not found.
        """
        if not updates:
            return await self.get_by_id(patient_id)

        await self._db.execute(
            update(Patient)
            .where(Patient.id == uuid.UUID(patient_id))
            .values(**updates)
        )
        return await self.get_by_id(patient_id)

    async def mark_onboarding_complete(self, patient_id: str) -> None:
        """Called by OnboardingService after all profile fields are collected."""
        await self._db.execute(
            update(Patient)
            .where(Patient.id == uuid.UUID(patient_id))
            .values(onboarding_complete=True)
        )

    async def get_patient_context(self, patient_id: str) -> dict:
        """
        Return a lightweight dict of patient data for agent prompts.
        Avoids passing full ORM objects into the pipeline.
        """
        patient = await self.get_by_id(patient_id)
        if not patient:
            return {}

        return {
            "name":       patient.full_name,
            "age":        patient.age,
            "language":   patient.language,
            "conditions": patient.chronic_conditions or [],
            "medications": [
                f"{m.name} {m.dosage or ''} {m.frequency or ''}".strip()
                for m in patient.active_medications
            ],
            "allergies":  patient.allergies or [],
            "care_plan_activities": (
                patient.care_plan.activities if patient.care_plan else []
            ),
        }

    async def exists(self, patient_id: str) -> bool:
        result = await self._db.execute(
            select(Patient.id).where(Patient.id == uuid.UUID(patient_id))
        )
        return result.scalar_one_or_none() is not None


# ── AuthUser Repository ────────────────────────────────────────────────────────
class AuthUserRepository:
    """CRUD operations for the auth_users table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: str) -> Optional[AuthUser]:
        result = await self._db.execute(
            select(AuthUser).where(AuthUser.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        result = await self._db.execute(
            select(AuthUser).where(AuthUser.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> AuthUser:
        user = AuthUser(
            email=email.lower().strip(),
            hashed_password=hashed_password,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def link_patient(self, user_id: str, patient_id: uuid.UUID) -> None:
        """Set the patient_id FK after onboarding creates the patient row."""
        await self._db.execute(
            update(AuthUser)
            .where(AuthUser.id == uuid.UUID(user_id))
            .values(patient_id=patient_id)
        )

    async def deactivate(self, user_id: str) -> None:
        await self._db.execute(
            update(AuthUser)
            .where(AuthUser.id == uuid.UUID(user_id))
            .values(is_active=False)
        )

    async def email_exists(self, email: str) -> bool:
        result = await self._db.execute(
            select(AuthUser.id).where(AuthUser.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None