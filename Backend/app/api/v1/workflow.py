"""
app/api/v1/workflow.py
──────────────────────
Professor / demo endpoints to inspect the full AI pipeline workflow.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.tracking.workflow_tracker import workflow_tracker

router = APIRouter()


@router.get(
    "/recent",
    summary="List recent workflow traces",
    description="Shows the last N pipeline runs with all steps (for professors / demos).",
)
async def list_recent_workflows(limit: int = Query(20, ge=1, le=100)):
    return {"traces": workflow_tracker.list_recent(limit=limit)}


@router.get(
    "/session/{session_id}",
    summary="Get workflow trace for a chat session",
)
async def get_session_workflow(session_id: str):
    trace = workflow_tracker.get_by_session(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail="No workflow trace for this session.")
    return trace


@router.get(
    "/trace/{trace_id}",
    summary="Get workflow trace by ID",
)
async def get_workflow_trace(trace_id: str):
    trace = workflow_tracker.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Workflow trace not found.")
    return {
        **trace,
        "steps_summary": workflow_tracker.get_workflow_summary(trace_id),
    }
