"""Schemas for vision / document analysis API."""
from typing import Optional

from pydantic import BaseModel, Field


class ExtractedDocumentDataSchema(BaseModel):
    document_type: str
    extracted_fields: dict[str, str] = Field(default_factory=dict)
    medications_detected: list[dict] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    confidence: float = 0.0


class ImageAnalysisResponse(BaseModel):
    analysis: ExtractedDocumentDataSchema
    safe_summary: str
    added_to_record: bool = False
    raw_text: str = ""
