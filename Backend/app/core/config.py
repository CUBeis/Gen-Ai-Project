"""
app/core/config.py
──────────────────
Single source of truth for every environment variable.
Uses Pydantic Settings — reads from .env automatically.

Import pattern everywhere else:
    from app.core.config import settings
"""
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",            # silently ignore unrecognised env vars
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENV: str = "development"
    APP_NAME: str = "Nerve AI"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Embedding sidecar ─────────────────────────────────────────────────────
    EMBEDDING_SERVICE_URL: str = "http://localhost:8001"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_PATH: str = "./data/chromadb"
    CHROMA_CLINICAL_COLLECTION: str = "clinical_knowledge"
    CHROMA_MEMORY_COLLECTION: str = "patient_memory"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── LLM providers ─────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str

    # ── Model names ───────────────────────────────────────────────────────────
    GROQ_ROUTER_MODEL: str = "llama3-70b-8192"
    GROQ_GUARDRAIL_MODEL: str = "llama3-70b-8192"
    GROQ_ONBOARDING_MODEL: str = "mixtral-8x7b-32768"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    COHERE_MODEL: str = "command-r"

    # ── RAG ───────────────────────────────────────────────────────────────────
    RAG_TOP_K: int = 10
    RAG_RERANK_TOP_N: int = 5

    # ── Memory ────────────────────────────────────────────────────────────────
    SESSION_WINDOW_SIZE: int = 20
    SESSION_TTL_SECONDS: int = 7200
    MEMORY_EXTRACT_EVERY_N_MESSAGES: int = 10

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated in .env: "http://localhost:3000,https://nerve-ai.com"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> List[str]:
        """Split comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    # ── Validation ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Enforce that production environments have real secrets."""
        if self.ENV == "production":
            weak_secrets = {"dev_secret_replace_in_production", "CHANGE_ME", ""}
            if self.JWT_SECRET_KEY in weak_secrets:
                raise ValueError("JWT_SECRET_KEY must be set to a strong value in production.")
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters.")
        return self


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance — instantiated once at startup.
    Use this in Depends() chains if you want testable overrides.
    """
    return Settings()


# Module-level singleton — import this everywhere
settings: Settings = get_settings()
