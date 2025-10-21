"""Configuration management for Dogwalker."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Load and validate environment configuration."""

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file. If not specified, searches parent directories.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Search for .env in current and parent directories
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                env_path = parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path)
                    break

        # Validate required variables
        self._validate()

    def _validate(self) -> None:
        """Validate all required environment variables are set."""
        required_vars = [
            "ANTHROPIC_API_KEY",
            "GITHUB_TOKEN",
            "SLACK_BOT_TOKEN",
            "SLACK_APP_TOKEN",
            "REDIS_URL",
            "GITHUB_REPO",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please ensure your .env file contains all required values."
            )

    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def github_token(self) -> str:
        """Get GitHub personal access token."""
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def slack_bot_token(self) -> str:
        """Get Slack bot token."""
        return os.getenv("SLACK_BOT_TOKEN", "")

    @property
    def slack_app_token(self) -> str:
        """Get Slack app token for Socket Mode."""
        return os.getenv("SLACK_APP_TOKEN", "")

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return os.getenv("REDIS_URL", "redis://localhost:6379")

    @property
    def github_repo(self) -> str:
        """Get GitHub repository (format: owner/repo)."""
        return os.getenv("GITHUB_REPO", "")

    @property
    def slack_channel_id(self) -> Optional[str]:
        """Get Slack channel ID (optional)."""
        return os.getenv("SLACK_CHANNEL_ID")

    @property
    def dog_name(self) -> str:
        """Get dog identity name."""
        return os.getenv("DOG_NAME", "Bryans-Coregi")

    @property
    def dog_email(self) -> str:
        """Get dog email for git commits."""
        return os.getenv("DOG_EMAIL", "coregi@bryanowens.dev")

    @property
    def base_branch(self) -> str:
        """Get base branch for PRs."""
        return os.getenv("BASE_BRANCH", "main")


# Global config instance
config = Config()
