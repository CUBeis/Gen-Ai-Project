"""
app/api/websocket/chat_ws.py
─────────────────────────────
WebSocket endpoint for real-time bidirectional chat.

URL: ws://host/api/v1/ws/chat/{session_id}?token=<jwt>

Protocol (client → server):
    {
        "message": "string",
        "patient_id": "uuid",       # validated against token
        "image_base64": "string"    # optional
    }

Protocol (server → client):
    { "type": "typing_start" }
    { "type": "typing_stop" }
    { "type": "agent_response", "content": "...", "intent": "..." }
    { "type": "care_plan_update", "care_plan_patch": { ... } }
    { "type": "error", "error": "message" }
    { "type": "connected", "session_id": "..." }
"""
import json
import structlog
from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status

from app.core.dependencies import get_ws_user
from app.core.exceptions import NerveBaseException
from app.db.session import AsyncSessionLocal
from app.orchestrator.pipeline import AgentPipeline
from app.orchestrator.state import ConversationState
from app.memory.short_term import ShortTermMemory

logger = structlog.get_logger(__name__)

# One pipeline instance — stateless, safe to share across connections
_pipeline = AgentPipeline()
_short_term = ShortTermMemory()


async def websocket_chat_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    Main WebSocket handler.
    Registered in main.py via app.add_websocket_route().
    """
    # ── Auth ──────────────────────────────────────────────────────────────────
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Missing token.")
        return

    async with AsyncSessionLocal() as db:
        try:
            user = await get_ws_user(token, db)
        except WebSocketException as exc:
            await websocket.close(code=exc.code, reason=exc.reason)
            return

    await websocket.accept()
    logger.info("ws.connected", session_id=session_id, user_id=str(user.id))

    # ── Send handshake confirmation ────────────────────────────────────────────
    await _send(websocket, {"type": "connected", "session_id": session_id})

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            # ── Parse incoming message ────────────────────────────────────────
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "error": "Invalid JSON."})
                continue

            message: str = data.get("message", "").strip()
            patient_id: str = data.get("patient_id", "")
            image_base64: str | None = data.get("image_base64")

            if not message and not image_base64:
                await _send(websocket, {"type": "error", "error": "Empty message."})
                continue

            # ── Ownership check ───────────────────────────────────────────────
            if str(user.patient_id) != patient_id:
                logger.warning(
                    "ws.ownership_violation",
                    user_id=str(user.id),
                    claimed_patient=patient_id,
                )
                await _send(websocket, {"type": "error", "error": "Unauthorized."})
                continue

            logger.info(
                "ws.message.received",
                session_id=session_id,
                patient_id=patient_id,
                has_image=bool(image_base64),
            )

            # ── Signal typing to client ───────────────────────────────────────
            await _send(websocket, {"type": "typing_start"})

            # ── Load patient from DB ──────────────────────────────────────────
            async with AsyncSessionLocal() as db:
                from app.db.repositories.patient_repo import PatientRepository
                repo = PatientRepository(db)
                patient = await repo.get_by_id(patient_id)

            if not patient:
                await _send(websocket, {
                    "type": "error",
                    "error": "Patient profile not found.",
                })
                continue

            # ── Build state and run pipeline ──────────────────────────────────
            state = ConversationState(
                session_id=session_id,
                patient_id=patient_id,
                user_message=message,
                image_base64=image_base64,
                patient_context=_build_patient_context(patient),
            )

            try:
                response_text, meta = await _pipeline.run(state)
            except NerveBaseException as exc:
                await _send(websocket, {"type": "typing_stop"})
                await _send(websocket, {"type": "error", "error": exc.detail})
                continue
            except Exception as exc:
                logger.error("ws.pipeline.error", error=str(exc), session_id=session_id)
                await _send(websocket, {"type": "typing_stop"})
                await _send(websocket, {
                    "type": "error",
                    "error": "Something went wrong. Please try again.",
                })
                continue

            # ── Stop typing, send response ────────────────────────────────────
            await _send(websocket, {"type": "typing_stop"})
            await _send(websocket, {
                "type": "agent_response",
                "content": response_text,
                "session_id": session_id,
                "intent": meta.get("intent"),
                "sources": meta.get("sources", []),
                "workflow_trace_id": meta.get("workflow_trace_id"),
                "workflow_steps": meta.get("workflow_steps", []),
            })

            # ── Push care plan update if the planner changed it ───────────────
            if meta.get("care_plan_updated") and meta.get("care_plan_patch"):
                await _send(websocket, {
                    "type": "care_plan_update",
                    "care_plan_patch": meta["care_plan_patch"],
                })

            logger.info(
                "ws.message.handled",
                session_id=session_id,
                intent=meta.get("intent"),
                care_plan_updated=meta.get("care_plan_updated", False),
            )

    except WebSocketDisconnect:
        logger.info("ws.disconnected", session_id=session_id)
    except Exception as exc:
        logger.error("ws.unhandled_error", error=str(exc), session_id=session_id)
        try:
            await websocket.close(code=1011, reason="Internal server error.")
        except Exception:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _send(websocket: WebSocket, data: dict) -> None:
    """Send a JSON message. Silently drop if the socket is already closed."""
    try:
        await websocket.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass  # Connection already closed — ignore


def _build_patient_context(patient) -> dict:
    """
    Extract the fields the orchestrator needs for every turn.
    Keeps ConversationState serialisable (no ORM objects).
    """
    return {
        "name": patient.full_name,
        "age": _calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
        "conditions": patient.chronic_conditions or [],
        "medications": [
            f"{m.name} {m.dosage or ''} {m.frequency or ''}".strip()
            for m in (patient.medications or [])
            if m.is_active
        ],
        "allergies": patient.allergies or [],
        "language": patient.language or "en",
    }


def _calculate_age(date_of_birth) -> int | None:
    from datetime import date
    if not date_of_birth:
        return None
    today = date.today()
    return (
        today.year - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )
