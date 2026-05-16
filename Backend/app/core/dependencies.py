"""
app/core/dependencies.py
────────────────────────
FastAPI dependency injection providers.

These are the building blocks that route handlers declare in their signatures:

    @router.get("/patient/{id}")
    async def get_patient(
        patient_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: AuthUser = Depends(get_current_user),
    ):
        ...

Rule: dependencies only handle cross-cutting concerns (auth, DB session).
Business logic stays in services. Database queries stay in repositories.
"""
from typing import Annotated, AsyncGenerator

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthError,
    InsufficientPermissionsError,
    PatientNotFoundError,
    TokenExpiredError,
)
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)

# ── HTTP Bearer scheme ────────────────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Database session ──────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a SQLAlchemy async session, always closed after the request.
    Rolls back automatically on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias — use this in route signatures for cleaner code
DB = Annotated[AsyncSession, Depends(get_db)]


# ── Token extraction ──────────────────────────────────────────────────────────
async def _get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    Extract and validate the Bearer token from the Authorization header.
    Returns the decoded JWT payload.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# ── Auth user ─────────────────────────────────────────────────────────────────
async def get_current_user(
    payload: dict = Depends(_get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> "AuthUser":  # type: ignore — forward ref resolved at runtime
    """
    Resolve the JWT subject to a live AuthUser row from the database.
    Raises 401 if the user_id no longer exists (deleted account etc.).
    """
    from app.db.repositories.patient_repo import AuthUserRepository

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject.",
        )

    repo = AuthUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please log in again.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    return user


# Type alias
CurrentUser = Annotated["AuthUser", Depends(get_current_user)]  # type: ignore


# ── Patient from token ────────────────────────────────────────────────────────
async def get_current_patient(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> "Patient":  # type: ignore
    """
    Resolve the authenticated user's linked patient profile.
    Raises 404 if onboarding hasn't been completed yet.
    """
    from app.db.repositories.patient_repo import PatientRepository

    if not current_user.patient_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found. Please complete onboarding first.",
        )

    repo = PatientRepository(db)
    patient = await repo.get_by_id(str(current_user.patient_id))
    if not patient:
        raise PatientNotFoundError(patient_id=str(current_user.patient_id))

    return patient


# Type alias
CurrentPatient = Annotated["Patient", Depends(get_current_patient)]  # type: ignore


# ── Patient ownership guard ───────────────────────────────────────────────────
async def verify_patient_ownership(
    patient_id: str,
    current_user: CurrentUser,
) -> str:
    """
    Ensure the requesting user owns the patient_id in the URL path.
    Prevents horizontal privilege escalation (patient A accessing patient B).

    Usage:
        @router.get("/{patient_id}")
        async def handler(
            patient_id: str = Depends(verify_patient_ownership),
            ...
        ):
    """
    if str(current_user.patient_id) != patient_id:
        logger.warning(
            "security.ownership_violation",
            requesting_user=str(current_user.id),
            requested_patient=patient_id,
        )
        raise InsufficientPermissionsError()
    return patient_id


# ── WebSocket token extraction ────────────────────────────────────────────────
async def get_ws_user(token: str, db: AsyncSession) -> "AuthUser":  # type: ignore
    """
    Validate a JWT passed as a WebSocket query param (?token=...).
    Called directly from the WebSocket handler (not via Depends).

    Args:
        token: Raw JWT string from the query string.
        db:    An open AsyncSession.
    """
    from app.db.repositories.patient_repo import AuthUserRepository

    try:
        payload = decode_access_token(token)
    except (AuthError, TokenExpiredError) as exc:
        from fastapi import WebSocketException
        raise WebSocketException(code=4001, reason=exc.detail)

    user_id = payload.get("sub")
    if not user_id:
        from fastapi import WebSocketException
        raise WebSocketException(code=4001, reason="Malformed token.")

    repo = AuthUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        from fastapi import WebSocketException
        raise WebSocketException(code=4001, reason="Account not found or inactive.")

    return user
