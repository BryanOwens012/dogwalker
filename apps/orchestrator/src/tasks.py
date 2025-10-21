"""Celery tasks for Dogwalker orchestration."""

from celery import Task
from celery_app import app
import logging
import sys
from pathlib import Path
from typing import Any

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from slack_utils import format_task_completed, format_task_failed

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True
)
def run_coding_task(
    self: Task,
    task_id: str,
    task_description: str,
    branch_name: str,
    dog_name: str,
    dog_email: str,
    thread_ts: str,
    channel_id: str
) -> dict[str, Any]:
    """
    Execute a coding task with a dog agent.

    This task is picked up by a Celery worker (dog) which:
    1. Clones the repo and checks out a new branch
    2. Runs Aider to make code changes
    3. Commits and pushes the branch
    4. Creates a PR
    5. Posts update to Slack thread

    Args:
        task_id: Unique task identifier
        task_description: What code changes to make
        branch_name: Git branch name for the changes
        dog_name: Dog's GitHub username
        dog_email: Dog's email for commits
        thread_ts: Slack thread timestamp for updates
        channel_id: Slack channel ID

    Returns:
        Dictionary with task results and metadata
    """
    logger.info(f"Task {task_id} started by {dog_name}")

    try:
        # NOTE: The actual work is done by the worker app
        # This task definition is just the contract
        # Worker app implements the execution logic

        # For now, this is a placeholder
        # The worker will override this with actual implementation
        raise NotImplementedError(
            "This task must be executed by a Dogwalker worker. "
            "Make sure the worker app is running."
        )

    except Exception as exc:
        logger.exception(f"Task {task_id} failed")

        # Retry with exponential backoff for transient errors
        # Don't retry for code errors (NotImplementedError, ValueError, etc.)
        if isinstance(exc, (IOError, OSError, ConnectionError)):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        else:
            # Permanent failure - notify Slack
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(exc),
            }
