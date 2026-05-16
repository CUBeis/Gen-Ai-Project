"""
app/api/v1/patient.py
──────────────────────
Patient profile endpoints.

GET  /api/v1/patient/{patient_id}   — full profile (medications + care plan)
PUT  /api/v1/patient/{patient_id}   — update profile fields
"""
import structlog
from fastapi import APIRouter, Depends, status

from app.core.dependencies import DB, CurrentUser, verify_patient_ownership
from app.schemas.patient import PatientResponse, PatientUpdateRequest
from app.services.patient_service import PatientService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get full patient profile",
    description=(
        "Returns the patient record including active medications and current care plan. "
        "Only the owner of the profile can access it."
    ),
)
async def get_patient(
    patient_id: str = Depends(verify_patient_ownership),
    current_user: CurrentUser = None,   # injected by verify_patient_ownership chain
    db: DB = None,
) -> PatientResponse:
    service = PatientService(db)
    return await service.get_full_profile(patient_id)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient profile fields",
    description=(
        "Partial update — only send the fields you want to change. "
        "Changing medications or conditions also triggers a care plan recalculation."
    ),
)
async def update_patient(
    payload: PatientUpdateRequest,
    patient_id: str = Depends(verify_patient_ownership),
    db: DB = None,
) -> PatientResponse:
    logger.info("patient.update", patient_id=patient_id, fields=list(payload.model_fields_set))
    service = PatientService(db)
    return await service.update(patient_id, payload)
