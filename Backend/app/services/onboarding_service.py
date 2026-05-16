"""
app/services/onboarding_service.py
──────────────────────────────────
Onboarding orchestration service.
Coordinates multi-turn onboarding flow and profile creation.
"""
from __future__ import annotations

import uuid
import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.patient import Patient, AuthUser
from app.db.repositories.patient_repo import PatientRepository, AuthUserRepository
from app.db.repositories.care_plan_repo import CarePlanRepository
from app.schemas.patient import PatientCreate
from app.core.config import settings

logger = structlog.get_logger(__name__)


class OnboardingService:
    """Orchestrates the multi-turn onboarding flow."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.patient_repo = PatientRepository(db)
        self.auth_repo = AuthUserRepository(db)
        self.care_plan_repo = CarePlanRepository(db)

    async def create_patient_from_profile(
        self,
        user_id: str,
        profile_data: dict,
    ) -> Patient:
        """
        Create a patient from accumulated onboarding profile data.

        Called when onboarding is complete.
        """
        # Validate required fields
        full_name = profile_data.get("full_name", "Patient")
        language = profile_data.get("language", "en")

        # Create patient
        patient_data = {
            "user_id": uuid.UUID(user_id),
            "full_name": full_name,
            "language": language,
            "date_of_birth": profile_data.get("date_of_birth"),
            "gender": profile_data.get("gender"),
            "allergies": profile_data.get("allergies", []),
            "chronic_conditions": profile_data.get("chronic_conditions", []),
            "emergency_contact": profile_data.get("emergency_contact"),
            "onboarding_complete": True,
        }

        patient = await self.patient_repo.create(patient_data)

        # Link auth user to patient
        await self.auth_repo.link_patient(user_id, patient.id)

        # Create empty care plan
        await self.care_plan_repo.create({
            "patient_id": patient.id,
            "activities": [],
        })

        await self._db.commit()

        logger.info(
            "onboarding_service.patient_created",
            patient_id=str(patient.id),
            user_id=user_id,
            language=language,
        )

        return patient

    async def get_patient_for_onboarding(self, user_id: str) -> Patient | None:
        """Get patient if onboarding is complete."""
        return await self.patient_repo.get_by_user_id(user_id)

    async def mark_complete(self, patient_id: str) -> None:
        """Mark onboarding as complete in database."""
        await self.patient_repo.mark_onboarding_complete(patient_id)
        await self._db.commit()

        logger.info(
            "onboarding_service.marked_complete",
            patient_id=patient_id,
        )
