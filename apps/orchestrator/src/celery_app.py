"""Celery application configuration for Dogwalker orchestrator."""

from celery import Celery
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import config

# Create Celery app
app = Celery(
    "dogwalker",
    broker=config.redis_url,
    backend=config.redis_url,
    include=["tasks"]  # Import tasks module
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
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
)
