"""
app/tasks/celery_app.py
───────────────────────
Celery application factory and configuration.
"""
from celery import Celery
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

# Create Celery instance
celery_app = Celery(
    __name__,
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 min hard limit
    task_soft_time_limit=25 * 60,  # 25 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Autodiscover tasks from all apps
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    logger.info("celery.debug_task", request=str(self.request))
