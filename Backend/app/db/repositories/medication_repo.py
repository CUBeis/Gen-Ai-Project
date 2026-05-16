"""
app/db/repositories/medication_repo.py
────────────────────────────────────────
Data access layer for the medications table.

Soft-delete pattern throughout:
  Medications are never hard-deleted. `deactivate()` sets is_active=False.
  All "active" queries filter is_active=True.
  The full history (including inactive) is available via get_all().

Duplicate detection:
  `find_by_name()` performs a case-insensitive name match within a patient's
  active medications. CarePlannerAgent calls this before adding a new
  medication to warn about potential duplicates.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.medication import Medication


class MedicationRepository:
    """CRUD + query operations for the medications table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Read ───────────────────────────────────────────────────────────────────
    async def get_by_id(self, medication_id: str) -> Optional[Medication]:
        result = await self._db.execute(
            select(Medication).where(
                Medication.id == uuid.UUID(medication_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, patient_id: str) -> list[Medication]:
        """Return all active medications for a patient, newest first."""
        result = await self._db.execute(
            select(Medication)
            .where(
                Medication.patient_id == uuid.UUID(patient_id),
                Medication.is_active == True,   # noqa: E712
            )
            .order_by(Medication.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self, patient_id: str) -> list[Medication]:
        """Return complete medication history (active + inactive), newest first."""
        result = await self._db.execute(
            select(Medication)
            .where(Medication.patient_id == uuid.UUID(patient_id))
            .order_by(Medication.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_name(
        self,
        patient_id: str,
        name: str,
        active_only: bool = True,
    ) -> Optional[Medication]:
        """
        Case-insensitive name search within a patient's medications.
        Used to detect duplicates before adding a new medication.
        """
        query = select(Medication).where(
            Medication.patient_id == uuid.UUID(patient_id),
            func.lower(Medication.name) == name.lower().strip(),
        )
        if active_only:
            query = query.where(Medication.is_active == True)  # noqa: E712

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    # ── Write ──────────────────────────────────────────────────────────────────
    async def add(self, patient_id: str, data: dict) -> Medication:
        """
        Insert a new medication row.

        Args:
            patient_id: UUID string of the owning patient.
            data:       Dict of Medication column values. patient_id is
                        injected here — do not pass it in data.

        Returns:
            The newly created Medication ORM instance.
        """
        med = Medication(
            patient_id=uuid.UUID(patient_id),
            **{k: v for k, v in data.items() if k != "patient_id"},
        )
        self._db.add(med)
        await self._db.flush()
        await self._db.refresh(med)
        return med

    async def update(self, medication_id: str, updates: dict) -> Optional[Medication]:
        """Partial update — only columns present in `updates` are changed."""
        if not updates:
            return await self.get_by_id(medication_id)

        await self._db.execute(
            update(Medication)
            .where(Medication.id == uuid.UUID(medication_id))
            .values(**updates)
        )
        return await self.get_by_id(medication_id)

    async def deactivate(self, medication_id: str) -> bool:
        """
        Soft-delete a medication by setting is_active=False.

        Returns:
            True if the medication existed and was deactivated.
            False if not found.
        """
        med = await self.get_by_id(medication_id)
        if not med:
            return False
        await self._db.execute(
            update(Medication)
            .where(Medication.id == uuid.UUID(medication_id))
            .values(is_active=False)
        )
        return True

    async def deactivate_by_name(self, patient_id: str, name: str) -> bool:
        """
        Soft-delete an active medication by name (case-insensitive).
        Called when the patient says "stop taking X" in the chat.
        """
        med = await self.find_by_name(patient_id, name, active_only=True)
        if not med:
            return False
        await self._db.execute(
            update(Medication)
            .where(Medication.id == med.id)
            .values(is_active=False)
        )
        return True

    async def active_count(self, patient_id: str) -> int:
        result = await self._db.execute(
            select(func.count(Medication.id)).where(
                Medication.patient_id == uuid.UUID(patient_id),
                Medication.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one() or 0