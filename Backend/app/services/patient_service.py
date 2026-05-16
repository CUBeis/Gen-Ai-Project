"""
app/services/patient_service.py
───────────────────────────────
Patient profile read/update.
"""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.patient_repo import PatientRepository
from app.schemas.patient import PatientResponse, PatientUpdateRequest

logger = structlog.get_logger(__name__)


class PatientService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.repo = PatientRepository(db)

    async def get_full_profile(self, patient_id: str) -> PatientResponse:
        patient = await self.repo.get_by_id(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        return PatientResponse.model_validate(patient)

    async def update(
        self, patient_id: str, payload: PatientUpdateRequest
    ) -> PatientResponse:
        data = payload.model_dump(exclude_unset=True)
        patient = await self.repo.update(patient_id, data)
        await self._db.commit()
        logger.info("patient_service.updated", patient_id=patient_id, fields=list(data.keys()))
        return PatientResponse.model_validate(patient)
