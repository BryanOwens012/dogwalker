"""Celery worker configuration for Dogwalker worker."""

from celery import Celery
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))
# Add worker src directory to path (for worker_tasks import)
sys.path.insert(0, str(Path(__file__).parent))

from config import config

# Create Celery app (must match orchestrator config)
app = Celery(
    "dogwalker",
    broker=config.redis_url,
    backend=config.redis_url,
    include=["worker_tasks"]  # Tell Celery where to find tasks
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Only take one task at a time
)
