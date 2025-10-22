"""Handle message events in Slack threads where dogs are working."""

import sys
from pathlib import Path
from logging import Logger
from slack_bolt import Say
from slack_sdk import WebClient
import json
import time

# Add shared and orchestrator modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import config
from dog_selector import DogSelector

# Initialize dog selector (singleton pattern)
dog_selector = DogSelector()


def handle_message(event: dict, say: Say, client: WebClient, logger: Logger) -> None:
    """
    Handle message events in Slack threads.

    When a human posts a message in a thread where a dog is working,
    this stores the message in Redis for the dog to read and respond to.

    Args:
        event: Slack event data containing the message
        say: Function to send messages back to Slack
        client: Slack WebClient for API calls
        logger: Logger instance for error tracking
    """
    try:
        # Only process messages in threads (has thread_ts)
        thread_ts = event.get("thread_ts")
        if not thread_ts:
            logger.debug("Ignoring non-threaded message")
            return

        # Ignore bot messages (including messages from dogs)
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            logger.debug("Ignoring bot message")
            return

        # Ignore message edits and deletions
        subtype = event.get("subtype")
        if subtype in ["message_changed", "message_deleted"]:
            logger.debug(f"Ignoring message with subtype: {subtype}")
            return

        # Check if this thread has an active task
        redis_client = dog_selector.redis_client
        if not redis_client:
            logger.warning("Redis unavailable, cannot track thread messages")
            return

        thread_key = f"dogwalker:thread_tasks:{thread_ts}"
        task_id = redis_client.get(thread_key)

        if not task_id:
            logger.debug(f"No active task in thread {thread_ts}, ignoring message")
            return

        # Extract message data
        user_id = event.get("user")
        text = event.get("text", "")
        message_ts = event.get("ts")

        if not text.strip():
            logger.debug("Ignoring empty message")
            return

        # Get user display name
        try:
            user_info = client.users_info(user=user_id)
            if user_info.get("ok"):
                profile = user_info["user"]["profile"]
                user_name = (
                    profile.get("display_name_normalized") or
                    profile.get("display_name") or
                    profile.get("real_name_normalized") or
                    profile.get("real_name") or
                    user_info["user"].get("name") or
                    "Unknown User"
                )
            else:
                user_name = "Unknown User"
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            user_name = "Unknown User"

        # Store message in Redis for dog to read
        message_data = {
            "user_id": user_id,
            "user_name": user_name,
            "text": text,
            "timestamp": time.time(),
            "message_ts": message_ts,
        }

        messages_key = f"dogwalker:thread_messages:{thread_ts}"
        redis_client.rpush(messages_key, json.dumps(message_data))

        # Set TTL on messages (24 hours)
        redis_client.expire(messages_key, 86400)

        logger.info(
            f"Stored message from {user_name} in thread {thread_ts} "
            f"for task {task_id}: '{text[:50]}...'"
        )

        # Optional: Acknowledge receipt with emoji reaction
        try:
            client.reactions_add(
                channel=event.get("channel"),
                timestamp=message_ts,
                name="eyes"  # 👀 emoji to show dog saw the message
            )
        except Exception as e:
            logger.debug(f"Could not add reaction: {e}")

    except Exception as e:
        logger.exception(f"Unexpected error in message handler: {e}")
