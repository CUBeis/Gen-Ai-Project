"""Vision analysis service — wraps VisionAgent."""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.vision_agent import VisionAgent
from app.db.models.patient import Patient
from app.schemas.vision import ExtractedDocumentDataSchema, ImageAnalysisResponse

logger = structlog.get_logger(__name__)


class VisionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._agent = VisionAgent()

    async def analyze(
        self,
        patient: Patient,
        image_base64: str,
        content_type: str,
        filename: str,
        context: str = "",
        save_to_record: bool = True,
    ) -> ImageAnalysisResponse:
        from app.db.repositories.patient_repo import PatientRepository

        repo = PatientRepository(self._db)
        patient_context = await repo.get_patient_context(str(patient.id))

        result = await self._agent.run(
            image_base64=image_base64,
            content_type=content_type,
            filename=filename,
            patient_context=patient_context,
            language=patient.language or "en",
            context_hint=context,
        )

        return ImageAnalysisResponse(
            analysis=ExtractedDocumentDataSchema(
                document_type=result.analysis.document_type,
                extracted_fields=result.analysis.extracted_fields,
                medications_detected=result.analysis.medications_detected,
                observations=result.analysis.observations,
                recommended_action=result.analysis.recommended_action,
                confidence=result.analysis.confidence,
            ),
            safe_summary=result.safe_summary,
            added_to_record=result.added_to_record,
            raw_text=result.raw_text,
        )
