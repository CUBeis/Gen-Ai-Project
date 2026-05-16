"""
app/agents/vision_agent.py
───────────────────────────
Clinical Vision Agent — extracts structured data from medical images and documents.

Model : Gemini 1.5 Flash (multimodal vision capability)
Role  : Analyse uploaded medical images, lab results, prescriptions, or scan
        reports and return structured findings safe to display in the UI.

Accepted inputs : JPEG, PNG, WebP, GIF, PDF (as base64)
Output          : VisionResult with structured extracted data + safe summary

IMPORTANT: The Guardrail agent reviews this output before it reaches the patient.
           This agent NEVER diagnoses — it only describes and extracts.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai

from app.agents.base import BaseAgent, llm_retry
from app.core.exceptions import AgentError


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class ExtractedDocumentData:
    """Structured fields extracted from the image."""
    document_type:       str                  # "lab_result" | "prescription" | "scan" | "unknown"
    extracted_fields:    dict[str, str]       # {"HbA1c": "7.2%", "Glucose": "126 mg/dL"}
    medications_detected: list[dict]          # [{"name": "Metformin", "dosage": "500mg", "frequency": "BD"}]
    observations:        list[str]            # Plain-English observations
    recommended_action:  Optional[str]        # "Share with your endocrinologist at next visit"
    confidence:          float                # 0.0 – 1.0 overall extraction confidence


@dataclass
class VisionResult:
    analysis:         ExtractedDocumentData
    safe_summary:     str     # Short, safe summary shown in chat
    added_to_record:  bool    # Whether extracted meds were saved to DB
    raw_text:         str     # Full text extracted from the document


# ── Prompts ────────────────────────────────────────────────────────────────────
_VISION_SYSTEM = """You are a clinical document parser for Nerve AI — a medical AI platform.
Your task is to analyse the provided medical image or document and extract structured information.

STRICT SAFETY RULES:
1. NEVER provide a medical diagnosis.
2. NEVER recommend treatment changes.
3. NEVER say values are "dangerous" or "critical" — just report them objectively.
4. If the document is unclear or low quality, say so in observations.
5. Only extract what is visibly present — do not infer missing values.

DOCUMENT TYPES:
- "lab_result"   : Blood tests, urine tests, pathology reports
- "prescription" : Doctor's prescription, pharmacy label
- "scan"         : X-ray, MRI, CT, ultrasound report or image
- "unknown"      : Cannot determine type

Respond ONLY with valid JSON in this exact format:
{
  "document_type": "<type>",
  "extracted_fields": {
    "<field_name>": "<value with unit>"
  },
  "medications_detected": [
    {"name": "<>", "dosage": "<>", "frequency": "<>", "duration": "<>"}
  ],
  "observations": [
    "<plain-English observation about the document>"
  ],
  "recommended_action": "<one sentence suggestion — e.g. 'Discuss these results with your doctor'>",
  "confidence": <0.0–1.0>,
  "raw_text": "<all text you could read from the document>"
}

If no medications are detected, use an empty list.
If a field cannot be determined, omit it from extracted_fields."""

_SAFE_SUMMARY_PROMPT = """Based on this document analysis, write a SHORT (2-3 sentence), 
reassuring summary suitable for a patient to read in a chat interface.
Do NOT include specific lab values in the summary — just state what type of document it was 
and that the key information has been extracted.
Write in this language: {language}

Analysis: {analysis}"""


# ── Agent ──────────────────────────────────────────────────────────────────────
class VisionAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        self._llm = genai.GenerativeModel(self.settings.GEMINI_MODEL)

    async def run(
        self,
        image_base64:  str,
        content_type:  str,
        filename:      str,
        patient_context: dict,
        language:      str = "en",
        context_hint:  str = "",
    ) -> VisionResult:
        """
        Analyse a medical image or document.

        Args:
            image_base64    : Base64-encoded file content (no data URI prefix).
            content_type    : MIME type, e.g. "image/jpeg", "application/pdf".
            filename        : Original filename for logging.
            patient_context : Patient profile for contextual extraction.
            language        : Patient's language for the safe summary.
            context_hint    : Optional free-text context from the patient.
        """
        t0    = self._now_ms()
        trace = self._start_trace(
            "vision_agent",
            {"filename": filename, "content_type": content_type},
        )

        # Step 1 — Extract structured data from image
        extracted = await self._extract(image_base64, content_type, patient_context, context_hint)

        # Step 2 — Generate safe summary in patient's language
        safe_summary = await self._summarise(extracted, language)

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "vision_extract", self.settings.GEMINI_MODEL,
            prompt=f"image:{content_type}", completion=safe_summary[:100],
            latency_ms=latency,
            metadata={
                "doc_type": extracted.document_type,
                "meds_found": len(extracted.medications_detected),
                "confidence": extracted.confidence,
            },
        )
        self.logger.info(
            "vision.done",
            doc_type=extracted.document_type,
            meds_found=len(extracted.medications_detected),
            confidence=extracted.confidence,
            latency_ms=latency,
        )

        return VisionResult(
            analysis=extracted,
            safe_summary=safe_summary,
            added_to_record=False,    # Set to True by VisionService after DB write
            raw_text=extracted.raw_text,
        )

    @llm_retry(max_attempts=3, reraise_as=AgentError)
    async def _extract(
        self,
        image_base64: str,
        content_type: str,
        patient_context: dict,
        context_hint: str,
    ) -> ExtractedDocumentData:

        # Map MIME type to Gemini image type
        gemini_mime = self._mime_to_gemini(content_type)

        patient_note = (
            f"Patient context: {patient_context.get('name')}, "
            f"conditions: {', '.join(patient_context.get('conditions', [])) or 'none known'}, "
            f"medications: {', '.join(patient_context.get('medications', [])) or 'none known'}."
        )

        user_note = f"\nPatient's note: {context_hint}" if context_hint else ""

        prompt_parts = [
            _VISION_SYSTEM + f"\n\n{patient_note}{user_note}",
            {"mime_type": gemini_mime, "data": image_base64},
        ]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm.generate_content(
                prompt_parts,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1500,
                ),
            ),
        )

        raw = response.text.strip()

        # Strip markdown fences
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("vision.json_parse_failed", raw=raw[:200])
            return ExtractedDocumentData(
                document_type="unknown",
                extracted_fields={},
                medications_detected=[],
                observations=["Could not parse document. Please ensure the image is clear and try again."],
                recommended_action="Try re-uploading a clearer image.",
                confidence=0.0,
                raw_text=raw,
            )

        return ExtractedDocumentData(
            document_type=data.get("document_type", "unknown"),
            extracted_fields=data.get("extracted_fields", {}),
            medications_detected=data.get("medications_detected", []),
            observations=data.get("observations", []),
            recommended_action=data.get("recommended_action"),
            confidence=float(data.get("confidence", 0.5)),
            raw_text=data.get("raw_text", ""),
        )

    @llm_retry(max_attempts=2, reraise_as=AgentError)
    async def _summarise(self, extracted: ExtractedDocumentData, language: str) -> str:
        analysis_summary = (
            f"Document type: {extracted.document_type}. "
            f"Key observations: {'; '.join(extracted.observations[:3])}. "
            f"Medications found: {len(extracted.medications_detected)}."
        )

        prompt = _SAFE_SUMMARY_PROMPT.format(
            language=language,
            analysis=analysis_summary,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            ),
        )
        return response.text.strip()

    @staticmethod
    def _mime_to_gemini(content_type: str) -> str:
        mapping = {
            "image/jpeg":       "image/jpeg",
            "image/png":        "image/png",
            "image/webp":       "image/webp",
            "image/gif":        "image/gif",
            "application/pdf":  "application/pdf",
        }
        return mapping.get(content_type, "image/jpeg")
