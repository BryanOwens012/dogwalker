"""Dog selection logic for task assignment."""

import random
from typing import List


class DogSelector:
    """Selects which dog should handle a task."""

    def __init__(self):
        """Initialize dog selector with available dogs."""
        # MVP: Single dog, will expand to multiple later
        self.available_dogs = [
            {
                "name": "Bryans-Coregi",
                "email": "coregi@bryanowens.dev",
            }
        ]

    def select_dog(self) -> dict:
        """
        Select a dog for the next task.

        For MVP, we use simple round-robin/random selection.
        Future: Track active tasks per dog and assign to least busy.

        Returns:
            Dog configuration dict with name and email
        """
        # MVP: Just return the first (only) dog
        # Future: Implement proper load balancing
        return self.available_dogs[0]

    def add_dog(self, name: str, email: str) -> None:
        """
        Add a new dog to the available pool.

        Args:
            name: Dog's GitHub username
            email: Dog's email for git commits
        """
        self.available_dogs.append({
            "name": name,
            "email": email,
        })

    def get_available_dogs(self) -> List[dict]:
        """Get list of all available dogs."""
        return self.available_dogs.copy()
