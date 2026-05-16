"""
app/schemas/onboarding.py
─────────────────────────
Schemas for the multi-turn onboarding flow.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class OnboardingStep(BaseModel):
    """A single onboarding question."""
    step_id: str = Field(..., description="Unique step identifier")
    question: str = Field(..., description="Question text")
    question_ar: Optional[str] = Field(None, description="Question in Arabic")
    type: str = Field(..., description="'text', 'multiple_choice', 'date', 'boolean'")
    options: Optional[list[str]] = None
    required: bool = True


class OnboardingRequest(BaseModel):
    """Patient response to onboarding message."""
    session_id: str = Field(..., description="Onboarding session ID")
    message: str = Field(..., description="Patient's response text")
    step: Optional[str] = Field(None, description="Optional step identifier")


class OnboardingResponse(BaseModel):
    """Onboarding agent response."""
    completed: bool = Field(False, description="True if onboarding is complete")
    next_question: Optional[str] = Field(None, description="Next question for patient")
    profile_data: dict[str, Any] = Field(default_factory=dict, description="Accumulated profile data")
    message: Optional[str] = Field(None, description="Status message")


class OnboardingCompleteResponse(BaseModel):
    """Response when onboarding is successfully completed."""
    patient_id: str = Field(..., description="Newly created patient ID")
    message: str = Field(..., description="Completion message")
