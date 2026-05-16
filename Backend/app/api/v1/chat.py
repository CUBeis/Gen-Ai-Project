"""
app/api/v1/chat.py
───────────────────
REST chat endpoint — fallback when WebSocket is unavailable.

POST /api/v1/chat
POST /api/v1/chat/demo  — local UI without auth (OpenRouter + RAG)
"""
import structlog
from fastapi import APIRouter, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import DB, CurrentPatient
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.demo_pipeline import run_demo_chat
from app.memory.short_term import ShortTermMemory

logger = structlog.get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
_demo_memory = ShortTermMemory()


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI pipeline (REST fallback)",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    current_patient: CurrentPatient,
    db: DB,
) -> ChatResponse:
    logger.info(
        "chat.rest.request",
        patient_id=str(current_patient.id),
        session_id=payload.session_id,
    )

    service = ChatService(db)
    return await service.process(
        patient=current_patient,
        session_id=payload.session_id,
        message=payload.message,
        image_base64=payload.image_base64,
    )


@router.post(
    "/demo",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Demo chat for local UI (no auth, OpenRouter + medical RAG)",
)
async def demo_chat(payload: ChatRequest) -> ChatResponse:
    logger.info("chat.demo.request", session_id=payload.session_id)

    patient_context = {
        "name": "Demo Patient",
        "age": 42,
        "conditions": ["type 2 diabetes", "hypertension"],
        "medications": [
            "Metformin 500mg twice daily",
            "Lisinopril 10mg once daily",
            "Atorvastatin 20mg once daily",
        ],
        "allergies": [],
        "language": "en",
    }

    history = await _demo_memory.get_history(payload.session_id)

    response_text, meta = await run_demo_chat(
        session_id=payload.session_id,
        message=payload.message,
        patient_context=patient_context,
        history=history,
    )

    await _demo_memory.append(payload.session_id, [
        {"role": "user", "content": payload.message},
        {"role": "assistant", "content": response_text},
    ])

    return ChatResponse(
        response_text=response_text,
        intent_detected=str(meta.get("intent", "clinical_question")),
        confidence=0.9,
        language=str(meta.get("language", "en")),
        sources=meta.get("sources", []),
        workflow_trace_id=meta.get("workflow_trace_id"),
        workflow_steps=meta.get("workflow_steps", []),
    )
