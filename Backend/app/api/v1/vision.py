"""
app/api/v1/vision.py
─────────────────────
Medical image / document analysis.

POST /api/v1/vision/analyze   — upload an image or PDF, get structured analysis
"""
import structlog
from fastapi import APIRouter, File, Form, UploadFile, status

from app.core.dependencies import DB, CurrentPatient
from app.core.exceptions import FileTooLargeError, InvalidImageError
from app.schemas.vision import ImageAnalysisResponse
from app.services.vision_service import VisionService

logger = structlog.get_logger(__name__)
router = APIRouter()

# 10 MB hard limit
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}


@router.post(
    "/analyze",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a medical image or document",
    description=(
        "Accepts JPEG, PNG, WebP, or PDF. "
        "The Clinical Vision Agent (Gemini 1.5 Flash) extracts structured data: "
        "lab values, medication names, dosages, or scan observations. "
        "Extracted data is optionally saved to the patient's record."
    ),
)
async def analyze_image(
    current_patient: CurrentPatient,
    db: DB,
    file: UploadFile = File(..., description="Medical image or PDF to analyze"),
    context: str = Form(
        default="",
        description="Optional text context, e.g. 'This is my lab result from yesterday'",
    ),
    save_to_record: bool = Form(
        default=True,
        description="If true, extracted medications are added to the patient's record",
    ),
) -> ImageAnalysisResponse:
    # ── Validation ────────────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImageError(
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: JPEG, PNG, WebP, GIF, PDF."
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError()

    logger.info(
        "vision.analyze.start",
        patient_id=str(current_patient.id),
        content_type=file.content_type,
        size_kb=round(len(contents) / 1024, 1),
        has_context=bool(context),
    )

    # ── Convert to base64 ─────────────────────────────────────────────────────
    import base64
    image_base64 = base64.b64encode(contents).decode("utf-8")

    # ── Run vision agent ──────────────────────────────────────────────────────
    service = VisionService(db)
    result = await service.analyze(
        patient=current_patient,
        image_base64=image_base64,
        content_type=file.content_type,
        filename=file.filename or "upload",
        context=context,
        save_to_record=save_to_record,
    )

    logger.info(
        "vision.analyze.complete",
        patient_id=str(current_patient.id),
        doc_type=result.analysis.document_type,
        added_to_record=result.added_to_record,
    )

    return result
