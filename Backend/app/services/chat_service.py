"""
app/services/chat_service.py
────────────────────────────
High-level chat orchestration service.
Coordinates the pipeline, repositories, and background tasks.
"""
from __future__ import annotations

import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.patient import Patient
from app.db.repositories.care_plan_repo import CarePlanRepository
from app.db.repositories.patient_repo import PatientRepository
from app.orchestrator.pipeline import AgentPipeline
from app.orchestrator.state import ConversationState
from app.schemas.chat import ChatResponse
from app.core.config import settings

logger = structlog.get_logger(__name__)


class ChatService:
    """Orchestrates incoming chat messages through the pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.pipeline = AgentPipeline()
        self.patient_repo = PatientRepository(db)
        self.care_plan_repo = CarePlanRepository(db)

    async def process(
        self,
        patient: Patient,
        session_id: str,
        message: str,
        image_base64: str | None = None,
    ) -> ChatResponse:
        """
        Process a patient message through the full pipeline.

        Returns: ChatResponse with response text and metadata.
        """
        # Build patient context for the pipeline
        patient_context = await self.patient_repo.get_patient_context(str(patient.id))

        # Create conversation state
        state = ConversationState(
            patient_id=str(patient.id),
            session_id=session_id,
            user_message=message,
            image_base64=image_base64,
            patient_context=patient_context,
        )

        logger.info(
            "chat_service.process_start",
            patient_id=str(patient.id),
            session_id=session_id,
        )

        # Run the pipeline
        response_text, meta = await self.pipeline.run(state)

        # If care plan was updated, persist the changes
        if state.care_plan_updated and state.care_plan_patch:
            await self.care_plan_repo.update(str(patient.id), state.care_plan_patch)
            await self._db.commit()

        logger.info(
            "chat_service.process_complete",
            patient_id=str(patient.id),
            intent=state.intent,
            care_plan_updated=state.care_plan_updated,
        )

        # Build response
        return ChatResponse(
            response_text=response_text,
            intent_detected=state.intent,
            confidence=state.routing_confidence,
            language=state.language,
            sources=state.sources or [],
            reformulated_query=state.reformulated_query,
            care_plan_updated=state.care_plan_updated,
            was_sanitized=state.was_sanitized,
            was_blocked=state.was_blocked,
        )
