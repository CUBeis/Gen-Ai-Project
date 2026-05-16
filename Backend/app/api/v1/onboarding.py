"""
app/api/v1/onboarding.py
─────────────────────────
Onboarding endpoints.

POST /api/v1/onboarding      — send a message in the onboarding conversation
POST /api/v1/onboarding/complete — mark onboarding done, return patient profile
"""
import structlog
from fastapi import APIRouter, status

from app.core.dependencies import DB, CurrentUser
from app.schemas.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    OnboardingCompleteResponse,
)
from app.services.onboarding_service import OnboardingService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=OnboardingResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message in the onboarding conversation",
    description=(
        "The Onboarding Profiler Agent (Mixtral 8x7B) turns this into a "
        "conversational form. Send messages iteratively until profile_complete=true."
    ),
)
async def onboarding_message(
    payload: OnboardingRequest,
    current_user: CurrentUser,
    db: DB,
) -> OnboardingResponse:
    """
    One turn in the onboarding conversation.

    The frontend should keep calling this with the user's replies
    until `profile_complete` is True in the response, then redirect
    to the dashboard.
    """
    logger.info(
        "onboarding.message",
        user_id=str(current_user.id),
        step=payload.step,
        session_id=payload.session_id,
    )

    service = OnboardingService(db)
    return await service.process_message(
        user=current_user,
        session_id=payload.session_id,
        message=payload.message,
        step=payload.step,
    )


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mark onboarding complete and persist patient profile",
)
async def complete_onboarding(
    current_user: CurrentUser,
    db: DB,
) -> OnboardingCompleteResponse:
    """
    Called once the frontend detects profile_complete=True.
    Flushes the onboarding session from Redis into PostgreSQL
    and links the patient record to the auth user.
    """
    logger.info("onboarding.complete", user_id=str(current_user.id))

    service = OnboardingService(db)
    patient = await service.complete(user=current_user)

    return OnboardingCompleteResponse(
        patient_id=str(patient.id),
        message="Profile created successfully. Welcome to Nerve AI!",
    )
