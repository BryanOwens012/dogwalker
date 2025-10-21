"""Dog worker - AI coding agent using Aider."""

import logging
from pathlib import Path
from typing import Optional
from aider.coders import Coder
from aider.models import Model

logger = logging.getLogger(__name__)


class Dog:
    """AI coding agent that uses Aider to make code changes."""

    def __init__(
        self,
        repo_path: Path,
        model_name: str = "claude-sonnet-4.5-20250929",
        map_tokens: int = 1024
    ):
        """
        Initialize Dog with Aider.

        Args:
            repo_path: Path to git repository
            model_name: Claude model to use (default: Sonnet 4.5)
            map_tokens: Tokens for repo map context (default: 1024)
        """
        self.repo_path = repo_path
        self.model_name = model_name
        self.map_tokens = map_tokens
        self.coder: Optional[Coder] = None

    def run_task(self, task_description: str) -> bool:
        """
        Execute a coding task using Aider.

        Args:
            task_description: Natural language description of code changes

        Returns:
            True if task completed successfully, False otherwise

        Raises:
            Exception: If Aider execution fails
        """
        logger.info(f"Starting Aider task: {task_description}")

        try:
            # Initialize Aider
            model = Model(self.model_name)
            self.coder = Coder.create(
                model=model,
                fnames=None,  # Auto-detect relevant files
                auto_commits=True,  # Let Aider auto-commit changes
                map_tokens=self.map_tokens,  # Repo map for context
                edit_format="diff",  # Use diff format for edits
                git_dname=str(self.repo_path),  # Git repo location
            )

            logger.info(f"Aider initialized with model {self.model_name}")

            # Run the task
            result = self.coder.run(task_description)

            # Verify Aider made changes
            if not result:
                logger.warning("Aider did not produce any changes")
                return False

            logger.info("Aider task completed successfully")
            return True

        except Exception as e:
            logger.exception(f"Aider task failed: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up Aider resources."""
        if self.coder:
            # Aider cleanup (if needed)
            self.coder = None
            logger.info("Dog cleaned up successfully")
