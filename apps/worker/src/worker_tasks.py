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
# Add orchestrator module to path (for dog_selector)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "orchestrator" / "src"))

from config import config
from github_client import GitHubClient
from slack_utils import (
    format_task_completed,
    format_task_failed,
    format_draft_pr_created,
)
from repo_manager import RepoManager
from dog import Dog
from dog_selector import DogSelector

logger = logging.getLogger(__name__)

# Initialize dog selector for marking tasks complete
dog_selector = DogSelector()

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
    dog_display_name: str,
    dog_email: str,
    thread_ts: str,
    channel_id: str,
    requester_name: str,
    requester_profile_url: str,
    start_time: float,
) -> dict[str, Any]:
    """
    Execute a coding task with Aider.

    This is the actual implementation that runs on the worker.
    It replaces the placeholder in orchestrator/tasks.py.

    Args:
        task_id: Unique task identifier
        task_description: What code changes to make
        branch_name: Git branch name for the changes
        dog_name: Dog's full GitHub username (e.g., "Bryans-Coregi")
        dog_display_name: Dog's display name (e.g., "Coregi")
        dog_email: Dog's email for commits
        thread_ts: Slack thread timestamp for updates
        channel_id: Slack channel ID
        requester_name: Display name of person who requested the change
        requester_profile_url: Slack profile URL of the requester
        start_time: Unix timestamp when request was made

    Returns:
        Dictionary with task results and metadata
    """
    logger.info(f"Worker executing task {task_id} as {dog_name}")

    work_dir = Path(__file__).parent.parent.parent.parent / "workdir" / task_id
    slack_client = None
    pr_info = None

    try:
        # Initialize Slack client (for posting updates)
        from slack_bolt import App
        slack_app = App(token=config.slack_bot_token)
        slack_client = slack_app.client

        # Get dog-specific GitHub token from config
        dog_info = None
        for dog in config.dogs:
            if dog["name"] == dog_name:
                dog_info = dog
                break

        if not dog_info:
            raise ValueError(f"Dog {dog_name} not found in config")

        dog_github_token = dog_info["github_token"]

        # Initialize GitHub client with dog-specific token
        github_client = GitHubClient(
            token=dog_github_token,
            repo_name=config.github_repo
        )

        # Step 1: Clone repository and create branch
        logger.info(f"Cloning repository {config.github_repo}")

        repo_url = f"https://github.com/{config.github_repo}"
        repo_manager = RepoManager(
            repo_url=repo_url,
            work_dir=work_dir,
            dog_name=dog_name,
            dog_email=dog_email,
            github_token=dog_github_token  # Use dog-specific token
        )

        repo_manager.clone()
        repo_manager.create_branch(branch_name, base_branch=config.base_branch)

        # Step 2: Create placeholder commit so PR can be created
        logger.info("Creating placeholder commit for PR creation")
        gitkeep_path = work_dir / ".gitkeep"
        gitkeep_path.write_text("# Placeholder - work in progress\n")
        repo_manager.commit_changes("Initial commit - starting work")

        # Step 3: Push branch with placeholder commit
        logger.info("Pushing branch to enable PR creation")
        repo_manager.push_branch(branch_name)

        # Step 4: Initialize Dog and generate PR title and implementation plan
        logger.info("Initializing AI agent (Dog)")
        dog = Dog(repo_path=work_dir)

        logger.info("Generating concise PR title")
        # Generate AI-created title (max 57 chars to leave room for "[Dogwalker] " prefix)
        pr_title_text = dog.generate_pr_title(task_description, max_length=57)

        logger.info("Generating implementation plan")
        plan = dog.generate_plan(task_description)

        # Step 5: Create draft PR with plan
        logger.info("Creating draft PR with plan")

        # Construct final PR title with prefix (max 70 chars total)
        PREFIX = "[Dogwalker] "
        MAX_TITLE_LENGTH = 70

        pr_title = f"{PREFIX}{pr_title_text}"

        # Safety validation: ensure title never exceeds 70 chars
        if len(pr_title) > MAX_TITLE_LENGTH:
            logger.warning(f"PR title exceeded max length ({len(pr_title)} > {MAX_TITLE_LENGTH}), truncating")
            # Emergency truncation at word boundary
            available = MAX_TITLE_LENGTH - len(PREFIX)
            pr_title_text = pr_title_text[:available].rsplit(' ', 1)[0]
            pr_title = f"{PREFIX}{pr_title_text}"

        logger.info(f"PR title: '{pr_title}' ({len(pr_title)}/{MAX_TITLE_LENGTH} chars)")

        # Format requester name with link
        from datetime import datetime
        import pytz

        local_tz = pytz.timezone('America/Los_Angeles')
        request_time = datetime.fromtimestamp(start_time, tz=pytz.UTC).astimezone(local_tz)
        request_time_str = request_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")

        if requester_profile_url:
            requester_link = f"[{requester_name}]({requester_profile_url})"
        else:
            requester_link = requester_name

        # Generate draft PR description using Claude
        draft_pr_body = dog.generate_draft_pr_description(
            task_description=task_description,
            requester_name=requester_link,
            request_time_str=request_time_str,
            plan=plan,
        )

        pr_info = github_client.create_pull_request(
            branch_name=branch_name,
            title=pr_title,
            body=draft_pr_body,
            base_branch=config.base_branch,
            draft=True,
            assignee=dog_name,  # Assign PR to the dog
        )

        if not pr_info:
            raise ValueError("Failed to create draft PR")

        # Step 6: Post draft PR to Slack
        logger.info("Posting draft PR announcement to Slack")

        # Extract brief plan preview (max 350 chars, preserve line breaks)
        if len(plan) > 350:
            # Truncate at 347 chars to leave room for "..."
            plan_preview = plan[:347] + "..."
        else:
            plan_preview = plan

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=format_draft_pr_created(
                pr_title=pr_info["pr_title"],
                pr_url=pr_info["pr_url"],
                plan_preview=plan_preview,
                dog_name=dog_display_name,
            )
        )

        # Step 7: Run Aider to make code changes
        logger.info(f"Running Aider with task: {task_description}")
        success = dog.run_task(task_description)

        if not success:
            raise ValueError("Aider did not produce code changes")

        # Step 8: Run self-review
        logger.info("Running self-review on code changes")
        dog.run_self_review()

        # Step 9: Write and run comprehensive tests
        logger.info("Writing and running comprehensive tests")
        test_success, test_message = dog.write_and_run_tests()

        if not test_success:
            raise ValueError(f"Tests failed: {test_message}")

        logger.info(f"Tests completed successfully: {test_message}")

        # Step 10: Remove placeholder file and push final changes
        logger.info("Removing placeholder .gitkeep file")
        if gitkeep_path.exists():
            gitkeep_path.unlink()
            repo_manager.commit_changes("Remove placeholder file")

        logger.info(f"Pushing final changes to branch {branch_name}")
        repo_manager.push_branch(branch_name)

        # Step 11: Calculate duration and get modified files
        logger.info("Calculating task duration and collecting changes")

        import time as time_module
        end_time = time_module.time()
        duration_seconds = end_time - start_time

        # Format duration
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        if minutes > 0:
            duration_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
        else:
            duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"

        modified_files = repo_manager.get_modified_files(base_branch=config.base_branch)

        # Step 12: Generate final PR description with Claude
        logger.info("Generating final PR description with Claude AI")

        # Ask Claude to identify critical review points
        critical_review_prompt = """Based on the code changes that were just made, identify ONLY critical areas that need careful review.

Focus on: breaking changes, configuration changes, security-sensitive code, database migrations, API changes, critical algorithms.

Respond with a bulleted list of SPECIFIC critical areas, or "No critical areas identified" if none.
Max 3-5 bullet points."""

        try:
            critical_review_points = dog.call_claude_api(critical_review_prompt, max_tokens=500).strip()
            if "no critical" in critical_review_points.lower() and len(critical_review_points) < 100:
                critical_review_points = ""
        except Exception as e:
            logger.error(f"Failed to identify critical review points: {e}")
            critical_review_points = ""

        # Generate complete final PR description
        final_pr_body = dog.generate_final_pr_description(
            task_description=task_description,
            requester_name=requester_link,
            request_time_str=request_time_str,
            duration_str=duration_str,
            plan=plan,
            files_modified=modified_files,
            critical_review_points=critical_review_points,
        )

        github_client.update_pull_request(
            pr_number=pr_info["pr_number"],
            body=final_pr_body,
        )

        # Step 13: Mark PR as ready for review
        logger.info("Marking PR as ready for review")
        github_client.mark_pr_ready(pr_info["pr_number"])

        # Step 14: Post completion to Slack
        logger.info(f"Posting completion to Slack thread {thread_ts}")

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=format_task_completed(
                pr_title=pr_info["pr_title"],
                pr_url=pr_info["pr_url"],
                dog_name=dog_display_name,
            )
        )

        logger.info(f"Task {task_id} completed successfully")

        # Mark dog as free (for load balancing)
        dog_selector.mark_dog_free(dog_name, task_id)

        return {
            "status": "success",
            "task_id": task_id,
            "pr_url": pr_info["pr_url"],
            "branch_name": branch_name,
            "dog_name": dog_display_name,
        }

    except Exception as exc:
        logger.exception(f"Task {task_id} failed: {exc}")

        # Post failure to Slack
        if slack_client:
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=format_task_failed(str(exc), dog_display_name)
                )
            except Exception as e:
                logger.error(f"Failed to post error to Slack: {e}")

        # Mark dog as free even on failure (for load balancing)
        dog_selector.mark_dog_free(dog_name, task_id)

        # Retry transient errors (network, git, etc.)
        if isinstance(exc, (IOError, OSError, ConnectionError)):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        # Permanent failure
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(exc),
            "dog_name": dog_display_name,
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
