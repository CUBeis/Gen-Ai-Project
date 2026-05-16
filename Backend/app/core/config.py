"""
app/core/config.py
──────────────────
Single source of truth for every environment variable.
Uses Pydantic Settings — reads from .env automatically.

Import pattern everywhere else:
    from app.core.config import settings
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: Gen-Ai-Project/ (parent of Backend/)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_RAG_ROOT = _REPO_ROOT / "Rag"


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

    # ── Standalone Rag/ folder (synced into app/rag) ──────────────────────────
    RAG_PROJECT_PATH: str = str(_DEFAULT_RAG_ROOT)
    RAG_CHROMA_PATH: str = ""   # empty → {RAG_PROJECT_PATH}/chroma_db
    RAG_MEDICAL_COLLECTION: str = "medical_rag"
    RAG_USE_COHERE_EMBEDDINGS: bool = True
    RAG_USE_HYBRID_RETRIEVAL: bool = True
    COHERE_EMBEDDING_MODEL: str = "embed-multilingual-v3.0"
    COHERE_RERANK_MODEL: str = "rerank-multilingual-v3.0"
    RAG_HYBRID_ALPHA: float = 0.7
    RAG_MMR_LAMBDA: float = 0.5

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── LLM providers ─────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # OpenRouter — primary RAG / demo LLM (Gemini via OpenRouter)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash-lite-preview-09-2025"

    # ── Model names ───────────────────────────────────────────────────────────
    GROQ_ROUTER_MODEL: str = "llama3-70b-8192"
    GROQ_GUARDRAIL_MODEL: str = "llama3-70b-8192"
    GROQ_ONBOARDING_MODEL: str = "mixtral-8x7b-32768"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    COHERE_MODEL: str = "command-r"
    RAG_LLM_PROVIDER: str = "openrouter"   # openrouter | deepseek | gemini

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
    # Comma-separated in .env: "http://localhost:3000,http://127.0.0.1:3000,https://nerve-ai.com"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

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

    @property
    def deepseek_enabled(self) -> bool:
        return bool(self.DEEPSEEK_API_KEY)

    @property
    def openrouter_enabled(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def primary_llm_enabled(self) -> bool:
        provider = (self.RAG_LLM_PROVIDER or "").lower()
        if provider == "openrouter":
            return self.openrouter_enabled
        if provider == "deepseek":
            return self.deepseek_enabled
        if provider == "gemini":
            return bool(self.GEMINI_API_KEY)
        return self.openrouter_enabled

    @property
    def rag_chroma_path(self) -> str:
        """ChromaDB path for the medical_rag index (from Rag/ folder)."""
        if self.RAG_CHROMA_PATH:
            return self.RAG_CHROMA_PATH
        return str(Path(self.RAG_PROJECT_PATH) / "chroma_db")

    @property
    def rag_data_path(self) -> Path:
        return Path(self.RAG_PROJECT_PATH) / "data"

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
