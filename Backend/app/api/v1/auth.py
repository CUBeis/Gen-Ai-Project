"""
app/api/v1/auth.py
───────────────────
Auth endpoints — register and login only.
No business logic here: validation → service → response.
"""
import structlog
from fastapi import APIRouter, status

from app.core.dependencies import DB, CurrentUser
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    MeResponse,
)
from app.services.auth_service import AuthService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(payload: RegisterRequest, db: DB) -> RegisterResponse:
    """
    Create a new auth_user row.
    A patient profile is NOT created here — that happens during onboarding.
    Returns a JWT so the user is immediately authenticated.
    """
    service = AuthService(db)
    return await service.register(payload)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
async def login(payload: LoginRequest, db: DB) -> LoginResponse:
    """
    Validate credentials and return a JWT access token.
    """
    service = AuthService(db)
    return await service.login(payload)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current authenticated user",
)
async def me(current_user: CurrentUser) -> MeResponse:
    """
    Returns the auth user from the JWT — no DB hit beyond what's in Depends.
    Useful for the frontend to confirm the session is still valid.
    """
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        patient_id=str(current_user.patient_id) if current_user.patient_id else None,
    )
