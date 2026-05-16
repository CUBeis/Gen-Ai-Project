"""
app/api/v1/chat.py
───────────────────
REST chat endpoint — fallback when WebSocket is unavailable.
The primary real-time path is WebSocket (chat_ws.py).

POST /api/v1/chat
"""
import structlog
from fastapi import APIRouter, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import DB, CurrentPatient
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

logger = structlog.get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI pipeline (REST fallback)",
    description=(
        "Processes a patient message through the full multi-agent pipeline: "
        "Router → Agent → Guardrail. "
        "For real-time chat, prefer the WebSocket endpoint at /api/v1/ws/chat/{session_id}."
    ),
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat(
    request: Request,           # required by slowapi for rate limiting
    payload: ChatRequest,
    current_patient: CurrentPatient,
    db: DB,
) -> ChatResponse:
    """
    Full pipeline execution — synchronous (waits for the full response).

    The WebSocket endpoint does the same thing but streams back events
    (typing_start, agent_response, care_plan_update) as they happen.
    """
    logger.info(
        "chat.rest.request",
        patient_id=str(current_patient.id),
        session_id=payload.session_id,
        has_image=bool(payload.image_base64),
    )

    service = ChatService(db)
    response = await service.process(
        patient=current_patient,
        session_id=payload.session_id,
        message=payload.message,
        image_base64=payload.image_base64,
    )

    logger.info(
        "chat.rest.response",
        patient_id=str(current_patient.id),
        intent=response.intent_detected,
        care_plan_updated=response.care_plan_updated,
    )

    return response
