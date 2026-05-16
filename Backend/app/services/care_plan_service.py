"""
app/services/care_plan_service.py
─────────────────────────────────
Care plan management service.
"""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.care_plan import CarePlan
from app.db.models.patient import Patient
from app.db.repositories.care_plan_repo import CarePlanRepository
from app.schemas.care_plan import (
    ActivityToggleResponse,
    CarePlanResponse,
    CarePlanUpdateRequest,
    CarePlanUpdateResponse,
)

logger = structlog.get_logger(__name__)


def _to_response(plan: CarePlan) -> CarePlanResponse:
    return CarePlanResponse.model_validate(plan)


class CarePlanService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.repo = CarePlanRepository(db)

    async def get(self, patient_id: str) -> CarePlanResponse:
        plan = await self.repo.get_or_create(patient_id)
        await self._db.commit()
        return _to_response(plan)

    async def get_or_create(self, patient_id: str) -> CarePlanResponse:
        return await self.get(patient_id)

    async def update(
        self,
        patient: Patient,
        request: CarePlanUpdateRequest,
    ) -> CarePlanUpdateResponse:
        patient_id = str(patient.id)
        action = request.action

        if action == "remove_activity" and request.activity:
            await self.repo.remove_activity(patient_id, str(request.activity.get("id", "")))
        elif action == "full_rebuild" and request.activities is not None:
            activities = [a.model_dump() for a in request.activities]
            await self.repo.upsert_activities(patient_id, activities, title=request.title)
        elif request.activity:
            activity = dict(request.activity)
            if not activity.get("id"):
                activity["id"] = str(uuid.uuid4())
            await self.repo.add_activity(patient_id, activity)
        elif request.activities is not None:
            activities = [a.model_dump() for a in request.activities]
            await self.repo.upsert_activities(patient_id, activities, title=request.title)

        await self._db.commit()
        plan = await self.repo.get_or_create(patient_id)
        return CarePlanUpdateResponse(
            care_plan=_to_response(plan),
            message=f"Care plan updated ({action})",
        )

    async def toggle_activity(
        self, patient_id: str, activity_id: str
    ) -> ActivityToggleResponse:
        plan, completed = await self.repo.toggle_activity(patient_id, activity_id)
        await self._db.commit()
        return ActivityToggleResponse(
            activity_id=activity_id,
            completed_today=completed,
            care_plan=_to_response(plan),
        )

    async def remove_activity(self, patient_id: str, activity_id: str) -> None:
        await self.repo.remove_activity(patient_id, activity_id)
        await self._db.commit()
