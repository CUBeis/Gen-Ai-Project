"""
app/api/v1/care_plan.py
────────────────────────
Care plan endpoints.

GET  /api/v1/care-plan/{patient_id}         — fetch current care plan
POST /api/v1/care-plan                      — add/remove/update activities
DELETE /api/v1/care-plan/{patient_id}/activity/{activity_id}
"""
import structlog
from fastapi import APIRouter, Depends, status

from app.core.dependencies import DB, CurrentPatient, verify_patient_ownership
from app.schemas.care_plan import (
    CarePlanResponse,
    CarePlanUpdateRequest,
    CarePlanUpdateResponse,
    ActivityToggleResponse,
)
from app.services.care_plan_service import CarePlanService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/{patient_id}",
    response_model=CarePlanResponse,
    summary="Get the current care plan",
)
async def get_care_plan(
    patient_id: str = Depends(verify_patient_ownership),
    db: DB = None,
) -> CarePlanResponse:
    service = CarePlanService(db)
    return await service.get(patient_id)


@router.post(
    "/",
    response_model=CarePlanUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Add, remove, or update a care plan activity",
    description=(
        "Actions: add_medication | add_exercise | add_appointment | "
        "remove_activity | full_rebuild. "
        "On success, a WebSocket event is pushed to the patient's active session."
    ),
)
async def update_care_plan(
    payload: CarePlanUpdateRequest,
    current_patient: CurrentPatient,
    db: DB,
) -> CarePlanUpdateResponse:
    logger.info(
        "care_plan.update",
        patient_id=str(current_patient.id),
        action=payload.action,
    )
    service = CarePlanService(db)
    return await service.update(patient=current_patient, request=payload)


@router.patch(
    "/{patient_id}/activity/{activity_id}/toggle",
    response_model=ActivityToggleResponse,
    summary="Mark an activity as completed or uncompleted for today",
)
async def toggle_activity(
    activity_id: str,
    patient_id: str = Depends(verify_patient_ownership),
    db: DB = None,
) -> ActivityToggleResponse:
    service = CarePlanService(db)
    return await service.toggle_activity(patient_id, activity_id)


@router.delete(
    "/{patient_id}/activity/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an activity from the care plan",
)
async def delete_activity(
    activity_id: str,
    patient_id: str = Depends(verify_patient_ownership),
    db: DB = None,
) -> None:
    service = CarePlanService(db)
    await service.remove_activity(patient_id, activity_id)
