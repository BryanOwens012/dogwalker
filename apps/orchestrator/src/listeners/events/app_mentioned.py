"""Handle @dogwalker mentions in Slack."""

import sys
from pathlib import Path
from logging import Logger
from slack_bolt import Say
from slack_sdk import WebClient
import re
import time
from datetime import datetime

# Add shared and orchestrator modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from slack_utils import format_task_started
from dog_selector import DogSelector
from tasks import run_coding_task
from github_client import GitHubClient
from config import config

# Initialize dog selector (singleton pattern)
dog_selector = DogSelector()


def generate_branch_name(
    dog_name: str,
    task_description: str,
    github_client: GitHubClient,
    max_length: int = 50
) -> str:
    """
    Generate descriptive branch name from task description with date prefix.
    Ensures the branch name doesn't conflict with existing branches.

    Args:
        dog_name: Name of the dog (e.g., "Bryans-Coregi")
        task_description: Task description to convert to slug
        github_client: GitHub client to check for existing branches
        max_length: Maximum length for the descriptive part (excluding date)

    Returns:
        Branch name like "bryans-coregi/2025-10-21-add-rate-limiting"
    """
    # Convert dog name to lowercase with hyphens
    dog_prefix = dog_name.lower().replace("_", "-")

    # Get current date in YYYY-MM-DD format
    date_prefix = datetime.now().strftime("%Y-%m-%d")

    # Convert task description to slug:
    # 1. Lowercase
    # 2. Remove special characters (keep alphanumeric and spaces)
    # 3. Replace spaces with hyphens
    # 4. Remove consecutive hyphens
    # 5. Strip leading/trailing hyphens
    slug = task_description.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')

    # Truncate if needed (leaving room for date prefix and hyphens)
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]  # Cut at word boundary

    # Construct base branch name with date prefix
    base_branch_name = f"{dog_prefix}/{date_prefix}-{slug}"

    # Check for conflicts and add suffix if needed
    branch_name = base_branch_name
    suffix = 2
    while github_client.branch_exists(branch_name):
        branch_name = f"{base_branch_name}-{suffix}"
        suffix += 1

    return branch_name


def handle_app_mention(event: dict, say: Say, client: WebClient, logger: Logger) -> None:
    """
    Handle @dogwalker mentions in Slack.

    When a user mentions @dogwalker with a task description,
    this creates a Celery task and assigns it to a dog.

    Args:
        event: Slack event data containing the mention
        say: Function to send messages back to Slack
        client: Slack WebClient for API calls
        logger: Logger instance for error tracking
    """
    try:
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("ts")  # Use event timestamp for threading

        # Record start time for accurate duration tracking
        start_time = time.time()

        # Extract task description (remove bot mention)
        # Format: "@dogwalker add rate limiting to /api/login"
        bot_user_id = client.auth_test()["user_id"]
        task_description = text.replace(f"<@{bot_user_id}>", "").strip()

        if not task_description:
            say(
                text="Please provide a task description! Example: `@dogwalker add rate limiting to /api/login`",
                thread_ts=thread_ts,
            )
            return

        # Get user information for PR description
        # Separate try/except blocks to avoid overwriting successfully fetched data
        requester_name = "Unknown User"
        requester_profile_url = None

        # Fetch user display name
        try:
            user_info = client.users_info(user=user_id)

            if not user_info.get("ok"):
                raise ValueError(f"Slack API error: {user_info.get('error', 'Unknown error')}")

            user_data = user_info.get("user", {})
            profile = user_data.get("profile", {})

            # Get display name using Slack's recommended priority
            # Use normalized versions first (they handle special characters better)
            display_name = profile.get("display_name_normalized", "").strip()
            real_name = profile.get("real_name_normalized", "").strip()

            # Fallback to non-normalized if normalized is empty
            if not display_name:
                display_name = profile.get("display_name", "").strip()
            if not real_name:
                real_name = profile.get("real_name", "").strip()

            # Choose the best name available
            requester_name = display_name or real_name or user_data.get("name", "").strip() or "Unknown User"

        except Exception as e:
            logger.error(f"Could not fetch user info: {e}")
            requester_name = "Unknown User"

        # Fetch team info for profile URL (independent of user name)
        try:
            team_info = client.team_info()

            if not team_info.get("ok"):
                raise ValueError(f"Slack API error: {team_info.get('error', 'Unknown error')}")

            team_domain = team_info["team"]["domain"]
            requester_profile_url = f"https://{team_domain}.slack.com/team/{user_id}"

        except Exception as e:
            logger.error(f"Could not fetch team info: {e}")
            requester_profile_url = None

        # Select a dog for this task
        dog = dog_selector.select_dog()
        dog_name = dog["name"]  # Full GitHub username (e.g., "Bryans-Coregi")
        dog_email = dog["email"]

        # Extract display name from GitHub username
        # "Bryans-Coregi" -> "Coregi"
        dog_display_name = dog_name.split("-")[-1] if "-" in dog_name else dog_name

        # Initialize GitHub client for branch conflict checking
        github_client = GitHubClient(
            token=config.github_token,
            repo_name=config.github_repo
        )

        # Create descriptive branch name with date prefix and conflict checking
        branch_name = generate_branch_name(dog_name, task_description, github_client)

        # Create task ID
        task_id = f"{channel_id}_{thread_ts}"

        # Mark dog as busy with this task (for load balancing)
        dog_selector.mark_dog_busy(dog_name, task_id)

        # Acknowledge immediately (Slack requires response within 3 seconds)
        say(
            text=format_task_started(dog_display_name, task_description),
            thread_ts=thread_ts,
        )

        logger.info(f"Creating task {task_id} for dog {dog_display_name} ({dog_name})")

        # Queue task asynchronously
        result = run_coding_task.delay(
            task_id=task_id,
            task_description=task_description,
            branch_name=branch_name,
            dog_name=dog_name,
            dog_display_name=dog_display_name,
            dog_email=dog_email,
            thread_ts=thread_ts,
            channel_id=channel_id,
            requester_name=requester_name,
            requester_profile_url=requester_profile_url,
            start_time=start_time,
        )

        logger.info(f"Task {task_id} queued with Celery task ID: {result.id}")

    except Exception as e:
        logger.exception(f"Unexpected error in mention handler: {e}")
        try:
            say(
                text=f":warning: Something went wrong! ({e})",
                thread_ts=thread_ts if 'thread_ts' in locals() else None,
            )
        except:
            pass  # Don't crash if we can't even send error message
