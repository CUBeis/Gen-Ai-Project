"""
app/core/logging.py
───────────────────
Structured logging via structlog.

- Development: coloured, human-readable console output
- Production:  JSON lines (compatible with Datadog, Loki, CloudWatch)

Call configure_logging() once in main.py lifespan.
Then in any module:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("event.name", key="value", another=123)
"""
import logging
import sys

import structlog
from app.core.config import settings


def configure_logging() -> None:
    """
    Set up structlog processors chain.
    Must be called once at application startup (main.py lifespan).
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,        # request-scoped context
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENV == "production":
        # JSON output — one line per log event
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable coloured output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    # so that SQLAlchemy, Alembic, Uvicorn logs are captured
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    # Suppress noisy third-party loggers in production
    if settings.is_production:
        for noisy in ("uvicorn.access", "httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Convenience wrapper — optional, you can also call structlog.get_logger() directly.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
    """
    return structlog.get_logger(name)
