"""
app/tasks/memory_tasks.py
─────────────────────────
Background tasks for memory extraction and long-term storage.
"""
import structlog
from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.agents.memory_extractor_agent import MemoryExtractorAgent
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="memory.extract",
    bind=True,
    max_retries=3,
)
def memory_extraction_task(self, session_id: str, patient_id: str):
    """
    Background task: Extract key memories from session and store in long-term DB.

    Called periodically (every N messages) to offload memory management.
    """
    import asyncio

    try:
        asyncio.run(_extract_memory_impl(session_id, patient_id))
    except Exception as exc:
        logger.error(
            "memory.extraction_failed",
            session_id=session_id,
            patient_id=patient_id,
            error=str(exc),
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60)


async def _extract_memory_impl(session_id: str, patient_id: str) -> None:
    """Extract and store long-term memories (async implementation)."""
    short_term = ShortTermMemory()
    long_term = LongTermMemory()
    extractor = MemoryExtractorAgent()

    # Fetch session history
    history = await short_term.get_history(session_id)
    if not history:
        logger.info("memory.extraction_skipped.empty_history", session_id=session_id)
        return

    logger.info(
        "memory.extraction_start",
        session_id=session_id,
        patient_id=patient_id,
        history_len=len(history),
    )

    # Extract key memories
    try:
        memories = await extractor.run(
            session_history=history,
            patient_id=patient_id,
        )

        # Store in long-term DB
        for memory in memories.extracted_memories:
            await long_term.store(
                patient_id=patient_id,
                memory_type=memory.get("type", "general"),
                content=memory.get("content"),
                metadata=memory.get("metadata", {}),
            )

        logger.info(
            "memory.extraction_complete",
            session_id=session_id,
            patient_id=patient_id,
            memories_stored=len(memories.extracted_memories),
        )

    except Exception as exc:
        logger.error(
            "memory.extraction_failed",
            session_id=session_id,
            error=str(exc),
        )
        raise


@celery_app.task(name="memory.cleanup")
def memory_cleanup_task():
    """Periodic task: Remove expired short-term memory from Redis."""
    import asyncio

    async def _cleanup():
        short_term = ShortTermMemory()
        expired_count = await short_term.cleanup_expired(
            ttl_seconds=settings.SESSION_TTL_SECONDS
        )
        logger.info("memory.cleanup_complete", expired_sessions=expired_count)

    asyncio.run(_cleanup())
