"""
app/services/care_plan_service.py
─────────────────────────────────
Care plan management service.
Handles creation, updates, and activity tracking.
"""
from __future__ import annotations

import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.patient import Patient
from app.db.repositories.care_plan_repo import CarePlanRepository
from app.db.repositories.patient_repo import PatientRepository
from app.schemas.care_plan import CarePlanCreate, CarePlanUpdate, CarePlanResponse

logger = structlog.get_logger(__name__)


class CarePlanService:
    """CRUD and business logic for care plans."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.repo = CarePlanRepository(db)
        self.patient_repo = PatientRepository(db)

    async def get_or_create(self, patient_id: str) -> CarePlanResponse:
        """Get existing care plan or create an empty one."""
        plan = await self.repo.get_by_patient_id(patient_id)

        if not plan:
            # Create empty care plan
            data = {"patient_id": uuid.UUID(patient_id), "activities": []}
            plan = await self.repo.create(data)
            await self._db.commit()
            logger.info("care_plan_service.created", patient_id=patient_id)

        return CarePlanResponse.from_orm(plan)

    async def update_activities(
        self, patient_id: str, activities: list[dict]
    ) -> CarePlanResponse:
        """Replace care plan activities."""
        updates = {"activities": activities}
        plan = await self.repo.update(patient_id, updates)
        await self._db.commit()

        logger.info(
            "care_plan_service.activities_updated",
            patient_id=patient_id,
            count=len(activities),
        )

        return CarePlanResponse.from_orm(plan)

    async def add_activity(
        self, patient_id: str, activity: dict
    ) -> CarePlanResponse:
        """Add a single activity to the care plan."""
        plan = await self.repo.get_by_patient_id(patient_id)

        if not plan:
            await self.get_or_create(patient_id)
            plan = await self.repo.get_by_patient_id(patient_id)

        if not plan.activities:
            plan.activities = []

        plan.activities.append(activity)
        await self._db.commit()

        logger.info(
            "care_plan_service.activity_added",
            patient_id=patient_id,
            activity_type=activity.get("type"),
        )

        return CarePlanResponse.from_orm(plan)

    async def remove_activity(
        self, patient_id: str, activity_id: str
    ) -> CarePlanResponse:
        """Remove an activity by ID."""
        plan = await self.repo.get_by_patient_id(patient_id)

        if plan and plan.activities:
            plan.activities = [
                a for a in plan.activities if str(a.get("id")) != activity_id
            ]
            await self._db.commit()

        logger.info(
            "care_plan_service.activity_removed",
            patient_id=patient_id,
            activity_id=activity_id,
        )

        return CarePlanResponse.from_orm(plan) if plan else None

    async def reset_daily_completion(self, patient_id: str) -> None:
        """Reset completed_today flag for all activities (midnight task)."""
        plan = await self.repo.get_by_patient_id(patient_id)

        if plan:
            plan.reset_daily_completion()
            await self._db.commit()

        logger.info(
            "care_plan_service.daily_reset",
            patient_id=patient_id,
        )
