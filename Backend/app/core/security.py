"""
app/core/security.py
────────────────────
JWT token lifecycle + password hashing.

Nothing in here touches the database — pure crypto utilities.
Database lookups live in dependencies.py.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthError, TokenExpiredError

# ── Password hashing ──────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of a plaintext password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      The unique identifier for the principal (auth_user.id).
        extra_claims: Optional dict merged into the token payload.
                      Typically includes {"patient_id": "..."}.
        expires_delta: Override default expiry. Falls back to settings value.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),           # standard JWT subject claim
        "iat": datetime.now(tz=timezone.utc),
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        TokenExpiredError: If the token's exp claim has passed.
        AuthError:         If the token is malformed or the signature is invalid.

    Returns:
        The full decoded payload dict.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise AuthError(detail="Invalid token type.")
        return payload
    except JWTError as exc:
        # jose raises ExpiredSignatureError (a subclass of JWTError)
        if "expired" in str(exc).lower():
            raise TokenExpiredError() from exc
        raise AuthError(detail="Invalid or tampered token.") from exc
