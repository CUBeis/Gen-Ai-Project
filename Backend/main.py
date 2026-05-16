"""
Nerve AI — FastAPI application entry point.
All middleware, lifespan events, and route registration live here.
"""
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.exceptions import NerveBaseException
from app.db.session import engine, Base
from app.api.v1.router import api_router
from app.api.websocket.chat_ws import websocket_chat_endpoint

# ── Logging ───────────────────────────────────────────────────────────────────
configure_logging()
logger = structlog.get_logger(__name__)

# ── Rate limiter (shared across app) ─────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: validate connections, warm up ChromaDB client, etc.
    Shutdown: dispose DB engine cleanly.
    """
    logger.info("nerve_ai.startup", env=settings.ENV, debug=settings.DEBUG)

    # Validate DB is reachable
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("nerve_ai.db.connected")
    except Exception as exc:
        logger.error("nerve_ai.db.connection_failed", error=str(exc))
        raise

    # Validate Redis is reachable
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        logger.info("nerve_ai.redis.connected")
    except Exception as exc:
        logger.warning("nerve_ai.redis.connection_failed", error=str(exc))

    # Warm up ChromaDB (creates collections if they don't exist)
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        client.get_or_create_collection(settings.CHROMA_CLINICAL_COLLECTION)
        client.get_or_create_collection(settings.CHROMA_MEMORY_COLLECTION)
        logger.info("nerve_ai.chromadb.ready")
    except Exception as exc:
        logger.warning("nerve_ai.chromadb.init_failed", error=str(exc))

    # Optional: init Sentry
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            traces_sample_rate=0.1,
        )
        logger.info("nerve_ai.sentry.enabled")

    logger.info("nerve_ai.ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("nerve_ai.shutdown")
    await engine.dispose()


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Production-grade medical AI platform",
        docs_url="/api/docs" if settings.ENV != "production" else None,
        redoc_url="/api/redoc" if settings.ENV != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENV != "production" else None,
        lifespan=lifespan,
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else None,
        )
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response

    # ── Prompt injection shield ───────────────────────────────────────────────
    @app.middleware("http")
    async def prompt_injection_shield(request: Request, call_next):
        """
        Lightweight injection detection on /chat endpoints.
        Full validation happens inside the pipeline; this is a fast pre-filter.
        """
        if request.method == "POST" and "/chat" in request.url.path:
            try:
                body = await request.body()
                if body:
                    import json, re
                    data = json.loads(body)
                    message = data.get("message", "")
                    INJECTION_PATTERNS = [
                        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
                        r"forget\s+(everything|all|your)\s+(instructions|system|prompt)",
                        r"reveal\s+(your|the)\s+(system\s+)?prompt",
                        r"show\s+me\s+(all\s+)?patient\s+data",
                        r"print\s+(the\s+)?(system|original)\s+prompt",
                        r"you\s+are\s+now\s+(a|an|the)\s+",
                        r"DAN\s+mode",
                        r"jailbreak",
                    ]
                    for pattern in INJECTION_PATTERNS:
                        if re.search(pattern, message, re.IGNORECASE):
                            logger.warning(
                                "security.injection_attempt_blocked",
                                path=request.url.path,
                                pattern=pattern,
                            )
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "detail": "Invalid request. Please ask questions related to your health plan."
                                },
                            )
                    # Reconstruct request body after reading it
                    from starlette.requests import Request as StarletteRequest
                    import io
                    request._body = body
            except Exception:
                pass

        return await call_next(request)

    # ── Global exception handlers ─────────────────────────────────────────────
    @app.exception_handler(NerveBaseException)
    async def nerve_exception_handler(request: Request, exc: NerveBaseException):
        logger.error("nerve.exception", detail=exc.detail, status=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred. Please try again."},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # WebSocket — registered separately (not under APIRouter)
    app.add_websocket_route(
        "/api/v1/ws/chat/{session_id}",
        websocket_chat_endpoint,
    )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], include_in_schema=False)
    async def health():
        return {"status": "ok", "env": settings.ENV, "version": "1.0.0"}

    @app.get("/", tags=["System"], include_in_schema=False)
    async def root():
        return {"name": settings.APP_NAME, "docs": "/api/docs"}

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
app = create_app()
