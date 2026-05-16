"""
app/orchestrator/state.py
──────────────────────────
ConversationState — the single data envelope passed through the full pipeline.

Every agent receives this object and reads only the fields it needs.
The pipeline writes back metadata (intent, language, etc.) as it progresses.

Design principles:
  - Serialisable  : no ORM objects, no SQLAlchemy models, only plain Python types
  - Immutable-ish : agents should NOT mutate input fields — only pipeline.py writes back
  - Lightweight   : created per request, discarded after response
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationState:
    """
    Carries all data needed for one full pipeline execution.

    Fields populated at request ingress (by chat_ws.py or chat_service.py):
        session_id, patient_id, user_message, image_base64, patient_context

    Fields written by the pipeline as it progresses:
        intent, language, reformulated_query, sources,
        care_plan_updated, care_plan_patch
    """

    # ── Input fields (set before pipeline.run()) ──────────────────────────────
    session_id:      str
    patient_id:      str
    user_message:    str
    patient_context: dict = field(default_factory=dict)
    image_base64:    Optional[str] = None

    # ── Written by Router ─────────────────────────────────────────────────────
    intent:          Optional[str]   = None     # IntentType value
    language:        str             = "en"     # ISO 639-1
    routing_confidence: float        = 0.0

    # ── Written by the dispatched agent ───────────────────────────────────────
    reformulated_query: Optional[str]       = None     # RAG only
    sources:            list[dict]          = field(default_factory=list)  # RAG
    care_plan_updated:  bool                = False
    care_plan_patch:    Optional[dict]      = None     # sent via WebSocket

    # ── Written by Guardrail ──────────────────────────────────────────────────
    was_sanitized:  bool = False
    was_blocked:    bool = False

    # ── Workflow tracking (professor / demo visibility) ───────────────────────
    workflow_trace_id: Optional[str] = None
    workflow_steps:    list[dict]    = field(default_factory=list)

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def has_image(self) -> bool:
        return bool(self.image_base64)

    @property
    def meta(self) -> dict:
        """
        Returns the metadata dict that pipeline.run() returns alongside the text.
        chat_ws.py uses this to push additional WebSocket events.
        """
        return {
            "intent":             self.intent,
            "language":           self.language,
            "sources":            self.sources,
            "care_plan_updated":  self.care_plan_updated,
            "care_plan_patch":    self.care_plan_patch,
            "was_sanitized":      self.was_sanitized,
            "was_blocked":        self.was_blocked,
            "workflow_trace_id":  self.workflow_trace_id,
            "workflow_steps":     self.workflow_steps,
        }
