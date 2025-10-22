"""Handle cancel task button clicks in Slack."""

import sys
from pathlib import Path
from logging import Logger
from slack_bolt import Ack
from slack_sdk import WebClient
import redis

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "src"))

from config import config

# Redis connection for cancellation signals
redis_client = None
try:
    redis_client = redis.from_url(
        config.redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    redis_client.ping()
except Exception as e:
    print(f"Warning: Could not connect to Redis for cancellation: {e}")


def handle_cancel_task(ack: Ack, body: dict, client: WebClient, logger: Logger) -> None:
    """
    Handle cancel task button clicks.

    When a user clicks the "Cancel Task" button, this sets a cancellation
    signal in Redis that the worker will check between phases.

    Args:
        ack: Function to acknowledge the action
        body: Action payload containing button value and user info
        client: Slack WebClient for API calls
        logger: Logger instance for error tracking
    """
    # Acknowledge the action immediately (Slack requires response within 3 seconds)
    ack()

    try:
        # Extract data from the action
        action = body.get("actions", [{}])[0]
        task_id = action.get("value")
        user_id = body.get("user", {}).get("id")
        container = body.get("container", {})
        channel_id = container.get("channel_id")
        message_ts = container.get("message_ts")

        if not task_id:
            logger.error("No task_id in cancel button action")
            return

        # Get user's display name
        cancelled_by = "Unknown User"
        try:
            user_info = client.users_info(user=user_id)
            if user_info.get("ok"):
                user_data = user_info.get("user", {})
                profile = user_data.get("profile", {})
                cancelled_by = (
                    profile.get("display_name_normalized", "").strip() or
                    profile.get("real_name_normalized", "").strip() or
                    profile.get("display_name", "").strip() or
                    profile.get("real_name", "").strip() or
                    user_data.get("name", "").strip() or
                    "Unknown User"
                )
        except Exception as e:
            logger.error(f"Could not fetch user info for cancellation: {e}")

        # Set cancellation signal in Redis
        if redis_client:
            try:
                cancellation_key = f"dogwalker:cancel:{task_id}"
                # Store who cancelled and when
                redis_client.hset(cancellation_key, mapping={
                    "cancelled_by": cancelled_by,
                    "cancelled_by_id": user_id,
                    "timestamp": str(int(redis_client.time()[0]))
                })
                # Set TTL to 1 hour (task should complete or fail within that time)
                redis_client.expire(cancellation_key, 3600)
                logger.info(f"Set cancellation signal for task {task_id} by {cancelled_by}")

                # Update the message to remove the cancel button and show cancellation is in progress
                try:
                    client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text=f"🛑 Cancellation requested by {cancelled_by}...",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"🛑 *Cancellation requested by {cancelled_by}*\n\n_The dog will stop at the next safe checkpoint..._"
                                }
                            }
                        ]
                    )
                except Exception as e:
                    logger.error(f"Failed to update message with cancellation status: {e}")

            except Exception as e:
                logger.error(f"Failed to set cancellation signal in Redis: {e}")
                # Post error message to thread
                try:
                    client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=task_id.split("_")[1],  # Extract thread_ts from task_id
                        text=f"⚠️ Could not cancel task: Redis error ({e})"
                    )
                except Exception as post_error:
                    logger.error(f"Failed to post cancellation error to Slack: {post_error}")
        else:
            logger.error("Redis not available, cannot process cancellation")
            # Post error to thread
            try:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=task_id.split("_")[1],  # Extract thread_ts from task_id
                    text="⚠️ Could not cancel task: Redis connection unavailable"
                )
            except Exception as e:
                logger.error(f"Failed to post error to Slack: {e}")

    except Exception as e:
        logger.exception(f"Unexpected error in cancel task handler: {e}")
