"""Dog communication helper for bi-directional Slack interaction."""

import time
import json
import logging
import redis
from typing import List, Dict, Optional
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


class DogCommunication:
    """
    Handles bi-directional communication between dogs and humans in Slack.

    Enables dogs to:
    - Post questions to Slack threads
    - Read human responses from Redis
    - Incorporate human feedback during execution
    """

    def __init__(
        self,
        task_id: str,
        thread_ts: str,
        channel_id: str,
        dog_name: str,
        slack_client: WebClient,
        redis_client: redis.Redis,
    ):
        """
        Initialize communication helper.

        Args:
            task_id: Unique task identifier
            thread_ts: Slack thread timestamp
            channel_id: Slack channel ID
            dog_name: Display name of the dog (e.g., "Coregi")
            slack_client: Slack WebClient for posting messages
            redis_client: Redis client for reading messages
        """
        self.task_id = task_id
        self.thread_ts = thread_ts
        self.channel_id = channel_id
        self.dog_name = dog_name
        self.slack_client = slack_client
        self.redis_client = redis_client
        self.message_pointer = 0  # Track which messages we've read

    def post_message(self, text: str, emoji: str = "🐕") -> bool:
        """
        Post a message to the Slack thread.

        Args:
            text: Message text to post
            emoji: Emoji to prefix message with

        Returns:
            True if successful, False otherwise
        """
        try:
            self.slack_client.chat_postMessage(
                channel=self.channel_id,
                thread_ts=self.thread_ts,
                text=f"{emoji} **{self.dog_name}:** {text}"
            )
            logger.info(f"Posted message to Slack: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to post message to Slack: {e}")
            return False

    def post_question(self, question: str) -> bool:
        """
        Post a question to the Slack thread and indicate waiting for response.

        Args:
            question: Question to ask

        Returns:
            True if successful, False otherwise
        """
        return self.post_message(
            f"❓ **Question:** {question}\n\n_Please reply in this thread. I'll check back shortly._",
            emoji="🐕"
        )

    def post_update(self, message: str) -> bool:
        """
        Post a status update to the Slack thread.

        Args:
            message: Status update message

        Returns:
            True if successful, False otherwise
        """
        return self.post_message(message, emoji="🔄")

    def get_new_messages(self) -> List[Dict[str, str]]:
        """
        Get new messages from the Slack thread since last check.

        Reads messages from Redis and updates the message pointer.

        Returns:
            List of message dicts with keys: user_id, user_name, text, timestamp, message_ts
        """
        if not self.redis_client:
            logger.warning("Redis unavailable, cannot read messages")
            return []

        try:
            messages_key = f"dogwalker:thread_messages:{self.thread_ts}"

            # Get all messages
            all_messages = self.redis_client.lrange(messages_key, 0, -1)

            # Parse messages starting from our pointer
            new_messages = []
            for i in range(self.message_pointer, len(all_messages)):
                try:
                    message_data = json.loads(all_messages[i])
                    new_messages.append(message_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message at index {i}: {e}")
                    continue

            # Update pointer
            if new_messages:
                self.message_pointer = len(all_messages)
                logger.info(f"Read {len(new_messages)} new message(s) from thread")

            return new_messages

        except Exception as e:
            logger.error(f"Failed to read messages from Redis: {e}")
            return []

    def wait_for_response(
        self,
        timeout: int = 600,
        poll_interval: int = 10,
        min_messages: int = 1
    ) -> List[Dict[str, str]]:
        """
        Wait for human responses in the Slack thread.

        Polls Redis for new messages until timeout or messages received.

        Args:
            timeout: Maximum time to wait in seconds (default: 10 minutes)
            poll_interval: How often to check for messages in seconds (default: 10s)
            min_messages: Minimum number of messages to wait for (default: 1)

        Returns:
            List of message dicts received during wait period
        """
        logger.info(
            f"Waiting for response (timeout: {timeout}s, "
            f"poll interval: {poll_interval}s)"
        )

        start_time = time.time()
        all_responses = []

        while (time.time() - start_time) < timeout:
            # Check for new messages
            new_messages = self.get_new_messages()

            if new_messages:
                all_responses.extend(new_messages)
                logger.info(f"Received {len(new_messages)} message(s)")

                # If we have enough messages, return immediately
                if len(all_responses) >= min_messages:
                    logger.info(
                        f"Received {len(all_responses)} message(s), "
                        f"stopping wait"
                    )
                    return all_responses

            # Sleep before next poll
            time.sleep(poll_interval)

        if all_responses:
            logger.info(
                f"Timeout reached, returning {len(all_responses)} message(s)"
            )
        else:
            logger.warning("Timeout reached with no responses")

        return all_responses

    def check_for_feedback(self) -> Optional[str]:
        """
        Check for human feedback/change requests without blocking.

        Returns:
            Combined text of all new messages, or None if no new messages
        """
        new_messages = self.get_new_messages()

        if not new_messages:
            return None

        # Combine all message texts
        combined_text = "\n\n".join(
            f"{msg['user_name']}: {msg['text']}"
            for msg in new_messages
        )

        logger.info(
            f"Received feedback from {len(new_messages)} message(s): "
            f"{combined_text[:100]}..."
        )

        return combined_text

    def format_feedback_for_prompt(self, feedback: str) -> str:
        """
        Format human feedback for inclusion in AI prompts.

        Args:
            feedback: Raw feedback text

        Returns:
            Formatted feedback for prompt injection
        """
        return f"""
IMPORTANT - HUMAN FEEDBACK:
The human has provided the following feedback/change request in the Slack thread:

{feedback}

Please incorporate this feedback into your current work. Adjust your implementation
to match the human's request while maintaining code quality and best practices.
"""

    def get_all_messages(self) -> List[Dict[str, str]]:
        """
        Get ALL messages from the thread (not just new ones).

        Used for generating PR description summary of all feedback received.

        Returns:
            List of all message dicts from the thread
        """
        if not self.redis_client:
            logger.warning("Redis unavailable, cannot read messages")
            return []

        try:
            messages_key = f"dogwalker:thread_messages:{self.thread_ts}"
            all_messages = self.redis_client.lrange(messages_key, 0, -1)

            parsed_messages = []
            for msg_json in all_messages:
                try:
                    message_data = json.loads(msg_json)
                    parsed_messages.append(message_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    continue

            return parsed_messages

        except Exception as e:
            logger.error(f"Failed to read all messages from Redis: {e}")
            return []

    def format_messages_for_pr(self) -> Optional[str]:
        """
        Format all thread messages as markdown for PR description.

        Returns:
            Markdown formatted list of messages, or None if no messages
        """
        messages = self.get_all_messages()

        if not messages:
            return None

        # Format as markdown bullet list
        formatted_lines = []
        for msg in messages:
            user_name = msg.get("user_name", "Unknown User")
            text = msg.get("text", "")
            # Escape any markdown in the text
            text = text.replace("*", "\\*").replace("_", "\\_")
            formatted_lines.append(f"- **{user_name}:** {text}")

        return "\n".join(formatted_lines)
