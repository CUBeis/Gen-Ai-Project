"""
app/schemas/patient.py
──────────────────────
Pydantic models for patient profile data.
"""
import uuid
from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class MedicationSchema(BaseModel):
    """Medication information."""
    id: Optional[uuid.UUID] = None
    name: str = Field(..., description="Medication name")
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    is_active: bool = True


class PatientBase(BaseModel):
    """Base fields for patient."""
    full_name: str = Field(..., description="Patient's full name")
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, description="'M', 'F', or other")
    language: str = Field(default="en", description="Preferred language")
    allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    emergency_contact: Optional[dict[str, Any]] = None


class PatientCreate(PatientBase):
    """Create patient during onboarding."""
    user_id: uuid.UUID


class PatientUpdateRequest(BaseModel):
    """Partial patient profile update."""
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    language: Optional[str] = None
    allergies: Optional[list[str]] = None
    chronic_conditions: Optional[list[str]] = None
    emergency_contact: Optional[dict[str, Any]] = None
    onboarding_complete: Optional[bool] = None


# Backward-compatible alias
PatientUpdate = PatientUpdateRequest


class PatientResponse(PatientBase):
    """Full patient profile response."""
    id: uuid.UUID
    user_id: uuid.UUID
    age: Optional[int] = None
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime
    medications: list[MedicationSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True
