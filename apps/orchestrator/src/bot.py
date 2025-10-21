"""Slack bot for Dogwalker orchestrator."""

import os
import sys
import logging
from pathlib import Path
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from dog_selector import DogSelector
from tasks import run_coding_task

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import config
from slack_utils import format_task_started

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=config.slack_bot_token)

# Initialize dog selector
dog_selector = DogSelector()


@app.event("app_mention")
def handle_mention(event: dict, say, logger):
    """
    Handle @dogwalker mentions in Slack.

    When a user mentions @dogwalker with a task description,
    this creates a Celery task and assigns it to a dog.

    Args:
        event: Slack event data
        say: Function to send messages back to Slack
        logger: Logger instance
    """
    try:
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("ts")  # Use event timestamp for threading

        # Extract task description (remove bot mention)
        # Format: "@dogwalker add rate limiting to /api/login"
        bot_user_id = app.client.auth_test()["user_id"]
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

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        # Don't crash - Slack will retry if needed
    except Exception as e:
        logger.exception(f"Unexpected error in mention handler: {e}")


@app.event("message")
def handle_message(event: dict, logger):
    """
    Handle regular messages (for future expansion).

    Args:
        event: Slack event data
        logger: Logger instance
    """
    # For now, we only respond to @mentions
    # Future: Could handle DMs or other message patterns
    pass


def start_bot():
    """Start the Slack bot in Socket Mode."""
    try:
        logger.info("Starting Dogwalker Slack bot...")
        handler = SocketModeHandler(app, config.slack_app_token)
        handler.start()
    except Exception as e:
        logger.exception(f"Failed to start Slack bot: {e}")
        raise


if __name__ == "__main__":
    start_bot()
