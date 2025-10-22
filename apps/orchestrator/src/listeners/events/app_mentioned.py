"""Handle @dogwalker mentions in Slack."""

import sys
from pathlib import Path
from logging import Logger
from slack_bolt import Say
from slack_sdk import WebClient

# Add shared and orchestrator modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from slack_utils import format_task_started
from dog_selector import DogSelector
from tasks import run_coding_task

# Initialize dog selector (singleton pattern)
dog_selector = DogSelector()


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

        # Select a dog for this task
        dog = dog_selector.select_dog()
        dog_name = dog["name"]
        dog_email = dog["email"]

        # Create branch name from thread timestamp
        branch_name = f"dogwalker/{thread_ts.replace('.', '-')}"

        # Create task ID
        task_id = f"{channel_id}_{thread_ts}"

        # Acknowledge immediately (Slack requires response within 3 seconds)
        say(
            text=format_task_started(dog_name, task_description),
            thread_ts=thread_ts,
        )

        logger.info(f"Creating task {task_id} for dog {dog_name}")

        # Queue task asynchronously
        result = run_coding_task.delay(
            task_id=task_id,
            task_description=task_description,
            branch_name=branch_name,
            dog_name=dog_name,
            dog_email=dog_email,
            thread_ts=thread_ts,
            channel_id=channel_id,
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
