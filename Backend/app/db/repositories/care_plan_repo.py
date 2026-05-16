"""
app/db/repositories/care_plan_repo.py
───────────────────────────────────────
Data access layer for the care_plans table.

The activities column is a JSONB array — the entire list is always read and
written as a unit. There are no individual activity rows in PostgreSQL.

Activity operations (add, remove, toggle) are performed in Python by
loading the current list, mutating it, and writing the whole array back.
PostgreSQL's JSONB operators could do this in SQL, but the Python approach
is simpler, easier to test, and fast enough given the small list sizes.

Upsert pattern:
  Each patient has at most one care plan. get_or_create() is the primary
  read method — it creates an empty plan if one doesn't exist yet.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.care_plan import CarePlan


class CarePlanRepository:
    """CRUD + activity operations for the care_plans table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Read ───────────────────────────────────────────────────────────────────
    async def get_by_patient(self, patient_id: str) -> Optional[CarePlan]:
        """Return the care plan for a patient, or None if not yet created."""
        result = await self._db.execute(
            select(CarePlan).where(
                CarePlan.patient_id == uuid.UUID(patient_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, patient_id: str) -> CarePlan:
        """
        Return the existing care plan, or create an empty one if missing.
        Guarantees the caller always gets a valid CarePlan instance.
        """
        plan = await self.get_by_patient(patient_id)
        if plan:
            return plan

        plan = CarePlan(
            patient_id=uuid.UUID(patient_id),
            title=None,
            activities=[],
        )
        self._db.add(plan)
        await self._db.flush()
        await self._db.refresh(plan)
        return plan

    # ── Write: full plan ───────────────────────────────────────────────────────
    async def upsert_activities(
        self,
        patient_id:  str,
        activities:  list[dict],
        title:       Optional[str] = None,
    ) -> CarePlan:
        """
        Replace the entire activities list for a patient.
        Called by CarePlannerAgent after it returns an updated full list.

        Args:
            patient_id : UUID string.
            activities : The complete new activity list.
            title      : Optional plan title update.
        """
        plan = await self.get_or_create(patient_id)

        values: dict = {"activities": activities}
        if title is not None:
            values["title"] = title

        await self._db.execute(
            update(CarePlan)
            .where(CarePlan.id == plan.id)
            .values(**values)
        )
        await self._db.refresh(plan)
        return plan

    # ── Write: single activity operations ─────────────────────────────────────
    async def add_activity(self, patient_id: str, activity: dict) -> CarePlan:
        """
        Append one activity to the list.
        Validates that an activity with the same id doesn't already exist.
        """
        plan = await self.get_or_create(patient_id)
        activities = list(plan.activities or [])

        # Prevent duplicate IDs
        existing_ids = {str(a.get("id")) for a in activities}
        if str(activity.get("id")) not in existing_ids:
            activities.append(activity)

        await self._db.execute(
            update(CarePlan)
            .where(CarePlan.id == plan.id)
            .values(activities=activities)
        )
        await self._db.refresh(plan)
        return plan

    async def remove_activity(
        self,
        patient_id:  str,
        activity_id: str,
    ) -> CarePlan:
        """
        Remove an activity from the list by its id field.
        No-op if the activity_id doesn't exist (idempotent).
        """
        plan = await self.get_by_patient(patient_id)
        if not plan:
            raise ValueError(f"No care plan found for patient {patient_id}")

        updated = [
            a for a in (plan.activities or [])
            if str(a.get("id")) != activity_id
        ]

        await self._db.execute(
            update(CarePlan)
            .where(CarePlan.id == plan.id)
            .values(activities=updated)
        )
        await self._db.refresh(plan)
        return plan

    async def toggle_activity(
        self,
        patient_id:  str,
        activity_id: str,
    ) -> tuple[CarePlan, bool]:
        """
        Flip the completed_today flag for one activity.

        Returns:
            (updated_plan, new_completed_value)
        """
        plan = await self.get_by_patient(patient_id)
        if not plan:
            raise ValueError(f"No care plan found for patient {patient_id}")

        new_completed = False
        updated_activities = []

        for activity in (plan.activities or []):
            if str(activity.get("id")) == activity_id:
                new_completed = not bool(activity.get("completed_today", False))
                updated_activities.append({**activity, "completed_today": new_completed})
            else:
                updated_activities.append(activity)

        await self._db.execute(
            update(CarePlan)
            .where(CarePlan.id == plan.id)
            .values(activities=updated_activities)
        )
        await self._db.refresh(plan)
        return plan, new_completed

    async def reset_daily_completions(self, patient_id: str) -> None:
        """
        Set completed_today=False for all activities.
        Called by Celery beat task at midnight UTC.
        """
        plan = await self.get_by_patient(patient_id)
        if not plan or not plan.activities:
            return

        reset = [{**a, "completed_today": False} for a in plan.activities]
        await self._db.execute(
            update(CarePlan)
            .where(CarePlan.id == plan.id)
            .values(activities=reset)
        )