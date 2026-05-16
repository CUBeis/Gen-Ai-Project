"""
app/tracking/workflow_tracker.py
────────────────────────────────
In-memory workflow trace store for professor / demo visibility.
Records every pipeline step: router → translate → retrieve → generate → guardrail.
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_MAX_TRACES = 200


@dataclass
class WorkflowStep:
    name: str
    status: str  # started | completed | failed | skipped
    started_at: str
    duration_ms: float = 0.0
    input_summary: dict = field(default_factory=dict)
    output_summary: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class WorkflowTrace:
    trace_id: str
    session_id: str
    user_message: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"  # running | completed | failed
    intent: Optional[str] = None
    language: str = "en"
    steps: list[WorkflowStep] = field(default_factory=list)
    final_response_preview: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class WorkflowTracker:
    def __init__(self) -> None:
        self._by_session: dict[str, str] = {}
        self._traces: dict[str, WorkflowTrace] = {}
        self._recent: deque[str] = deque(maxlen=_MAX_TRACES)

    def start(self, session_id: str, user_message: str) -> str:
        trace_id = str(uuid.uuid4())
        trace = WorkflowTrace(
            trace_id=trace_id,
            session_id=session_id,
            user_message=user_message[:500],
            started_at=_now_iso(),
        )
        self._traces[trace_id] = trace
        self._by_session[session_id] = trace_id
        self._recent.append(trace_id)
        logger.info("workflow.started", trace_id=trace_id, session_id=session_id)
        return trace_id

    def step(
        self,
        trace_id: str,
        name: str,
        *,
        status: str = "completed",
        input_summary: Optional[dict] = None,
        output_summary: Optional[dict] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        trace = self._traces.get(trace_id)
        if not trace:
            return
        trace.steps.append(WorkflowStep(
            name=name,
            status=status,
            started_at=_now_iso(),
            duration_ms=round(duration_ms, 2),
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            error=error,
        ))

    def update_meta(
        self,
        trace_id: str,
        *,
        intent: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        trace = self._traces.get(trace_id)
        if not trace:
            return
        if intent:
            trace.intent = intent
        if language:
            trace.language = language

    def complete(
        self,
        trace_id: str,
        response_preview: str = "",
        status: str = "completed",
    ) -> None:
        trace = self._traces.get(trace_id)
        if not trace:
            return
        trace.status = status
        trace.completed_at = _now_iso()
        trace.final_response_preview = response_preview[:300]
        logger.info("workflow.completed", trace_id=trace_id, status=status)

    def fail(self, trace_id: str, error: str) -> None:
        self.complete(trace_id, status="failed")
        self.step(trace_id, "pipeline_error", status="failed", error=error)

    def get_trace(self, trace_id: str) -> Optional[dict]:
        trace = self._traces.get(trace_id)
        return trace.to_dict() if trace else None

    def get_by_session(self, session_id: str) -> Optional[dict]:
        trace_id = self._by_session.get(session_id)
        return self.get_trace(trace_id) if trace_id else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        ids = list(self._recent)[-limit:]
        ids.reverse()
        return [
            self._traces[tid].to_dict()
            for tid in ids
            if tid in self._traces
        ]

    def get_workflow_summary(self, trace_id: str) -> list[dict]:
        trace = self._traces.get(trace_id)
        if not trace:
            return []
        return [
            {
                "step": s.name,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "input": s.input_summary,
                "output": s.output_summary,
            }
            for s in trace.steps
        ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


workflow_tracker = WorkflowTracker()
