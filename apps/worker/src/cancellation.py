"""Task cancellation management for workers."""

import redis
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CancellationManager:
    """Manages cancellation signals for long-running tasks."""

    def __init__(self, redis_url: str):
        """
        Initialize cancellation manager with Redis connection.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client: Optional[redis.Redis] = None
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
            logger.info("Cancellation manager connected to Redis")
        except Exception as e:
            logger.error(f"Could not connect to Redis for cancellation: {e}")

    def is_cancelled(self, task_id: str) -> bool:
        """
        Check if a task has been cancelled.

        Args:
            task_id: Unique task identifier

        Returns:
            True if task has been cancelled, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cancellation_key = f"dogwalker:cancel:{task_id}"
            return self.redis_client.exists(cancellation_key) > 0
        except Exception as e:
            logger.error(f"Error checking cancellation for task {task_id}: {e}")
            return False

    def get_cancellation_info(self, task_id: str) -> Optional[Dict[str, str]]:
        """
        Get cancellation details (who cancelled and when).

        Args:
            task_id: Unique task identifier

        Returns:
            Dict with cancelled_by, cancelled_by_id, timestamp, or None if not cancelled
        """
        if not self.redis_client:
            return None

        try:
            cancellation_key = f"dogwalker:cancel:{task_id}"
            info = self.redis_client.hgetall(cancellation_key)
            return info if info else None
        except Exception as e:
            logger.error(f"Error getting cancellation info for task {task_id}: {e}")
            return None

    def clear_cancellation(self, task_id: str) -> None:
        """
        Clear cancellation signal after processing.

        Args:
            task_id: Unique task identifier
        """
        if not self.redis_client:
            return

        try:
            cancellation_key = f"dogwalker:cancel:{task_id}"
            self.redis_client.delete(cancellation_key)
            logger.info(f"Cleared cancellation signal for task {task_id}")
        except Exception as e:
            logger.error(f"Error clearing cancellation for task {task_id}: {e}")


class TaskCancelled(Exception):
    """Exception raised when a task is cancelled by user."""

    def __init__(self, cancelled_by: str, phase: str):
        """
        Initialize exception with cancellation details.

        Args:
            cancelled_by: Display name of person who cancelled
            phase: Which phase was in progress when cancelled
        """
        self.cancelled_by = cancelled_by
        self.phase = phase
        super().__init__(f"Task cancelled by {cancelled_by} during {phase}")
