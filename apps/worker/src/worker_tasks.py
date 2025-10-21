"""Worker task implementation - actual code execution logic."""

from celery import Task
from celery_app import app
import logging
import sys
from pathlib import Path
from typing import Any
import os

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import config
from github_client import GitHubClient
from slack_utils import format_task_completed, format_task_failed, format_pr_body
from repo_manager import RepoManager
from dog import Dog

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@app.task(
    bind=True,
    name="tasks.run_coding_task",  # Must match orchestrator task name
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
    Execute a coding task with Aider.

    This is the actual implementation that runs on the worker.
    It replaces the placeholder in orchestrator/tasks.py.

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
    logger.info(f"Worker executing task {task_id} as {dog_name}")

    work_dir = Path(__file__).parent.parent.parent.parent / "workdir" / task_id
    slack_client = None
    pr_url = None

    try:
        # Initialize Slack client (for posting updates)
        from slack_bolt import App
        slack_app = App(token=config.slack_bot_token)
        slack_client = slack_app.client

        # Step 1: Clone repository and create branch
        logger.info(f"Cloning repository {config.github_repo}")

        repo_url = f"https://github.com/{config.github_repo}"
        repo_manager = RepoManager(
            repo_url=repo_url,
            work_dir=work_dir,
            dog_name=dog_name,
            dog_email=dog_email,
            github_token=config.github_token
        )

        repo_manager.clone()
        repo_manager.create_branch(branch_name, base_branch=config.base_branch)

        # Step 2: Run Aider to make code changes
        logger.info(f"Running Aider with task: {task_description}")

        dog = Dog(repo_path=work_dir)
        success = dog.run_task(task_description)

        if not success:
            raise ValueError("Aider did not produce code changes")

        # Step 3: Push branch to GitHub
        logger.info(f"Pushing branch {branch_name}")
        repo_manager.push_branch(branch_name)

        # Step 4: Create pull request
        logger.info("Creating pull request")

        github_client = GitHubClient(
            token=config.github_token,
            repo_name=config.github_repo
        )

        modified_files = repo_manager.get_modified_files()
        pr_body = format_pr_body(task_description, modified_files)

        pr_url = github_client.create_pull_request(
            branch_name=branch_name,
            title=f"[Dogwalker] {task_description[:60]}{'...' if len(task_description) > 60 else ''}",
            body=pr_body,
            base_branch=config.base_branch
        )

        if not pr_url:
            raise ValueError("Failed to create pull request")

        # Step 5: Post success to Slack
        logger.info(f"Posting success to Slack thread {thread_ts}")

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=format_task_completed(pr_url, dog_name)
        )

        logger.info(f"Task {task_id} completed successfully")

        return {
            "status": "success",
            "task_id": task_id,
            "pr_url": pr_url,
            "branch_name": branch_name,
            "dog_name": dog_name,
        }

    except Exception as exc:
        logger.exception(f"Task {task_id} failed: {exc}")

        # Post failure to Slack
        if slack_client:
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=format_task_failed(str(exc), dog_name)
                )
            except Exception as e:
                logger.error(f"Failed to post error to Slack: {e}")

        # Retry transient errors (network, git, etc.)
        if isinstance(exc, (IOError, OSError, ConnectionError)):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        # Permanent failure
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(exc),
            "dog_name": dog_name,
        }

    finally:
        # Cleanup work directory
        if work_dir.exists():
            import shutil
            try:
                shutil.rmtree(work_dir)
                logger.info(f"Cleaned up work directory {work_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup work directory: {e}")
