"""
app/services/auth_service.py
────────────────────────────
Authentication service — handles registration and login.
"""
from __future__ import annotations

import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, create_access_token
from app.core.exceptions import (
    ConflictError,
    AuthError,
)
from app.db.repositories.patient_repo import AuthUserRepository
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
)

logger = structlog.get_logger(__name__)


class AuthService:
    """Handles user registration and authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.repo = AuthUserRepository(db)

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """
        Register a new user.
        Returns JWT immediately so onboarding flow can proceed.
        """
        # Check if email already exists
        exists = await self.repo.email_exists(request.email)
        if exists:
            logger.warning("auth.register.email_exists", email=request.email)
            raise ConflictError(detail="Email already registered.")

        # Hash password
        hashed = hash_password(request.password)

        # Create user
        user = await self.repo.create(
            email=request.email,
            hashed_password=hashed,
        )
        await self._db.commit()

        # Generate JWT
        token = create_access_token(subject=str(user.id))

        logger.info(
            "auth.register.success",
            user_id=str(user.id),
            email=request.email,
        )

        return RegisterResponse(
            user_id=str(user.id),
            email=user.email,
            access_token=token,
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        """
        Authenticate user with email + password.
        Returns JWT if credentials are valid.
        """
        from app.core.security import verify_password

        # Fetch user by email
        user = await self.repo.get_by_email(request.email)
        if not user:
            logger.warning("auth.login.user_not_found", email=request.email)
            raise AuthError(detail="Invalid email or password.")

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            logger.warning("auth.login.wrong_password", user_id=str(user.id))
            raise AuthError(detail="Invalid email or password.")

        if not user.is_active:
            logger.warning("auth.login.account_inactive", user_id=str(user.id))
            raise AuthError(detail="Account is deactivated.")

        # Generate JWT
        token = create_access_token(subject=str(user.id))

        logger.info(
            "auth.login.success",
            user_id=str(user.id),
            email=user.email,
        )

        return LoginResponse(
            user_id=str(user.id),
            email=user.email,
            patient_id=str(user.patient_id) if user.patient_id else None,
            access_token=token,
        )
