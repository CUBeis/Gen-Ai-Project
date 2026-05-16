"""
app/core/exceptions.py
──────────────────────
Custom exception classes for Nerve AI.

All domain errors inherit from NerveBaseException.
The global handler in main.py catches these and returns structured JSON.

Usage:
    raise PatientNotFoundError(patient_id="abc-123")
    raise AgentError("Router failed to classify intent")
"""
from fastapi import status


class NerveBaseException(Exception):
    """Base for all Nerve AI domain exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, **context):
        self.detail = detail or self.__class__.detail
        self.context = context  # extra info for logging
        super().__init__(self.detail)


# ── Auth ──────────────────────────────────────────────────────────────────────
class AuthError(NerveBaseException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_ERROR"
    detail = "Authentication failed."


class InvalidCredentialsError(AuthError):
    code = "INVALID_CREDENTIALS"
    detail = "Email or password is incorrect."


class TokenExpiredError(AuthError):
    code = "TOKEN_EXPIRED"
    detail = "Session expired. Please log in again."


class InsufficientPermissionsError(NerveBaseException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    detail = "You do not have permission to perform this action."


# ── Patient ───────────────────────────────────────────────────────────────────
class PatientNotFoundError(NerveBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "PATIENT_NOT_FOUND"

    def __init__(self, patient_id: str | None = None):
        detail = (
            f"Patient '{patient_id}' not found."
            if patient_id
            else "Patient not found."
        )
        super().__init__(detail=detail)


class ConflictError(NerveBaseException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    detail = "This resource already exists."


class PatientAlreadyExistsError(NerveBaseException):
    status_code = status.HTTP_409_CONFLICT
    code = "PATIENT_ALREADY_EXISTS"
    detail = "A patient profile already exists for this account."


# ── Care Plan ─────────────────────────────────────────────────────────────────
class CarePlanNotFoundError(NerveBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "CARE_PLAN_NOT_FOUND"
    detail = "No care plan found for this patient."


# ── Agent / AI ────────────────────────────────────────────────────────────────
class AgentError(NerveBaseException):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "AGENT_ERROR"
    detail = "The AI agent encountered an error. Please try again."


class RouterAgentError(AgentError):
    code = "ROUTER_ERROR"
    detail = "Failed to classify your message. Please try again."


class RAGAgentError(AgentError):
    code = "RAG_ERROR"
    detail = "Failed to retrieve medical information. Please try again."


class GuardrailBlockedError(NerveBaseException):
    """
    Raised when the Guardrail agent hard-blocks a response.
    Not a server error — it's an expected safety outcome.
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "GUARDRAIL_BLOCKED"
    detail = (
        "Your request could not be processed safely. "
        "Please consult your physician for medical advice."
    )


class LLMProviderError(AgentError):
    """Raised when an external LLM API call fails after all retries."""
    code = "LLM_PROVIDER_ERROR"
    detail = "The AI service is temporarily unavailable. Please try again shortly."


# ── RAG / Storage ─────────────────────────────────────────────────────────────
class EmbeddingServiceError(NerveBaseException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "EMBEDDING_SERVICE_ERROR"
    detail = "The embedding service is unavailable. Please try again later."


class DocumentIngestionError(NerveBaseException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "INGESTION_ERROR"
    detail = "Failed to process the uploaded document."


# ── Validation ────────────────────────────────────────────────────────────────
class InvalidImageError(NerveBaseException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "INVALID_IMAGE"
    detail = "The uploaded file is not a valid image or PDF."


class FileTooLargeError(NerveBaseException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "FILE_TOO_LARGE"
    detail = "File exceeds the 10MB size limit."


# ── Security ──────────────────────────────────────────────────────────────────
class PromptInjectionError(NerveBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "PROMPT_INJECTION"
    detail = "Invalid request content detected."
