"""Dog selection logic for task assignment with load balancing."""

import logging
import sys
from pathlib import Path
from typing import List, Optional
import redis

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import config

logger = logging.getLogger(__name__)


class DogSelector:
    """Selects which dog should handle a task using least-busy load balancing."""

    def __init__(self):
        """
        Initialize dog selector with available dogs from config.

        Dogs are loaded from DOGS environment variable (or legacy DOG_NAME/DOG_EMAIL).
        Uses Redis to track active tasks per dog for intelligent load balancing.
        """
        # Load dogs from config
        self.available_dogs = config.dogs
        logger.info(f"Initialized dog selector with {len(self.available_dogs)} dog(s)")

        # Initialize Redis connection for task tracking
        self.redis_client: Optional[redis.Redis] = None
        self._connect_redis()

    def _connect_redis(self) -> None:
        """Connect to Redis for active task tracking."""
        try:
            self.redis_client = redis.from_url(
                config.redis_url,
                decode_responses=True,  # Return strings instead of bytes
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for dog task tracking")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def select_dog(self) -> dict:
        """
        Select a dog for the next task using least-busy load balancing.

        Algorithm:
        1. Get active task count for each dog from Redis
        2. Select dog with fewest active tasks
        3. If Redis unavailable, use round-robin

        Returns:
            Dog configuration dict with name and email
        """
        if not self.available_dogs:
            raise ValueError("No dogs available for task assignment")

        # Single dog: just return it
        if len(self.available_dogs) == 1:
            return self.available_dogs[0]

        # Multiple dogs: use load balancing
        if self.redis_client:
            try:
                # Get active task count for each dog
                dog_loads = []
                for dog in self.available_dogs:
                    active_count = self.get_active_task_count(dog["name"])
                    dog_loads.append((dog, active_count))
                    logger.debug(f"Dog {dog['name']}: {active_count} active tasks")

                # Sort by load (ascending) - least busy first
                dog_loads.sort(key=lambda x: x[1])

                selected_dog = dog_loads[0][0]
                logger.info(
                    f"Selected dog {selected_dog['name']} "
                    f"({dog_loads[0][1]} active tasks)"
                )
                return selected_dog

            except Exception as e:
                logger.error(f"Redis load balancing failed: {e}, falling back to round-robin")

        # Fallback: simple round-robin (return first dog)
        # In production, we'd track round-robin state
        logger.warning("Using fallback round-robin selection")
        return self.available_dogs[0]

    def mark_dog_busy(self, dog_name: str, task_id: str) -> None:
        """
        Mark a dog as busy with a task.

        Adds task_id to the dog's active task set in Redis.

        Args:
            dog_name: Dog's GitHub username
            task_id: Unique task identifier
        """
        if not self.redis_client:
            logger.warning("Redis unavailable, cannot track dog busy state")
            return

        try:
            key = f"dogwalker:active_tasks:{dog_name}"
            self.redis_client.sadd(key, task_id)
            count = self.redis_client.scard(key)
            logger.info(f"Marked dog {dog_name} busy with task {task_id} ({count} active)")
        except Exception as e:
            logger.error(f"Failed to mark dog {dog_name} busy: {e}")

    def mark_dog_free(self, dog_name: str, task_id: str) -> None:
        """
        Mark a dog as free from a task.

        Removes task_id from the dog's active task set in Redis.

        Args:
            dog_name: Dog's GitHub username
            task_id: Unique task identifier
        """
        if not self.redis_client:
            logger.warning("Redis unavailable, cannot track dog free state")
            return

        try:
            key = f"dogwalker:active_tasks:{dog_name}"
            removed = self.redis_client.srem(key, task_id)
            if removed:
                count = self.redis_client.scard(key)
                logger.info(f"Marked dog {dog_name} free from task {task_id} ({count} active)")
            else:
                logger.warning(
                    f"Task {task_id} was not in active set for dog {dog_name}"
                )
        except Exception as e:
            logger.error(f"Failed to mark dog {dog_name} free: {e}")

    def get_active_task_count(self, dog_name: str) -> int:
        """
        Get number of active tasks for a dog.

        Args:
            dog_name: Dog's GitHub username

        Returns:
            Number of active tasks (0 if Redis unavailable)
        """
        if not self.redis_client:
            return 0

        try:
            key = f"dogwalker:active_tasks:{dog_name}"
            return self.redis_client.scard(key) or 0
        except Exception as e:
            logger.error(f"Failed to get active task count for {dog_name}: {e}")
            return 0

    def get_available_dogs(self) -> List[dict]:
        """Get list of all available dogs."""
        return self.available_dogs.copy()

    def get_dog_status(self) -> List[dict]:
        """
        Get status of all dogs (name, email, active task count).

        Returns:
            List of dicts with dog info and active task count
        """
        status = []
        for dog in self.available_dogs:
            status.append({
                "name": dog["name"],
                "email": dog["email"],
                "active_tasks": self.get_active_task_count(dog["name"]),
            })
        return status
