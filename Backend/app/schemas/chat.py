"""
app/schemas/chat.py
───────────────────
Request/Response models for the chat API.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """POST /api/v1/chat payload."""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="Patient message")
    image_base64: Optional[str] = Field(None, description="Optional base64-encoded image")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_12345",
                "message": "I'm feeling dizzy after taking my medication",
                "image_base64": None,
            }
        }


class ChatResponse(BaseModel):
    """Response from the chat pipeline."""
    response_text: str = Field(..., description="AI-generated response")
    intent_detected: str = Field(..., description="Classified intent (router output)")
    confidence: float = Field(..., description="Router confidence [0-1]")
    language: str = Field(..., description="Detected language (en/ar)")
    sources: list[dict] = Field(default_factory=list, description="RAG sources (if applicable)")
    reformulated_query: Optional[str] = Field(None, description="Reformulated query (if RAG)")
    care_plan_updated: bool = Field(False, description="Whether care plan was modified")
    was_sanitized: bool = Field(False, description="Whether response was sanitized by guardrail")
    was_blocked: bool = Field(False, description="Whether response was blocked by guardrail")
    workflow_trace_id: Optional[str] = Field(None, description="Pipeline trace ID for professor dashboard")
    workflow_steps: list[dict] = Field(default_factory=list, description="Step-by-step pipeline log")

    class Config:
        json_schema_extra = {
            "example": {
                "response_text": "Dizziness can be a side effect of medication...",
                "intent_detected": "CLINICAL_QUESTION",
                "confidence": 0.92,
                "language": "en",
                "sources": [],
                "care_plan_updated": False,
                "was_sanitized": False,
                "was_blocked": False,
            }
        }
