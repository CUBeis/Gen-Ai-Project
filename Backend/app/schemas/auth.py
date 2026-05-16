"""
app/schemas/auth.py
───────────────────
Pydantic models for authentication.
"""
from typing import Optional
import uuid
from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")


class RegisterResponse(BaseModel):
    """Registration response with JWT."""
    user_id: str = Field(..., description="New user ID")
    email: str
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT."""
    user_id: str
    email: str
    patient_id: Optional[str] = None
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "patient_id": None,
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }


class MeResponse(BaseModel):
    """Current authenticated user info."""
    id: str
    email: str
    patient_id: Optional[str] = None
