"""Configuration management for Dogwalker."""

import os
import json
from pathlib import Path
from typing import Optional, List
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
            # GITHUB_TOKEN is optional (falls back to first dog's token)
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
        """
        Get GitHub personal access token.

        Falls back to first dog's token if GITHUB_TOKEN not set.
        This is used by orchestrator for read-only operations (checking branches).
        """
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # Fallback: use first dog's token
        dogs = self.dogs
        if dogs and len(dogs) > 0:
            return dogs[0]["github_token"]

        return ""

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
    def dogs(self) -> List[dict]:
        """
        Get list of available dog configurations.

        Returns list of dogs from DOGS env var (JSON array).
        Falls back to DOG_NAME/DOG_EMAIL for backward compatibility.

        Returns:
            List of dicts with 'name' and 'email' keys

        Raises:
            ValueError: If no dogs are configured or JSON is invalid
        """
        dogs_json = os.getenv("DOGS")

        if dogs_json:
            # Parse DOGS JSON array
            try:
                dogs_list = json.loads(dogs_json)

                # Validate format
                if not isinstance(dogs_list, list):
                    raise ValueError("DOGS must be a JSON array")

                if len(dogs_list) == 0:
                    raise ValueError("DOGS array cannot be empty")

                # Validate each dog has name, email, and github_token
                for i, dog in enumerate(dogs_list):
                    if not isinstance(dog, dict):
                        raise ValueError(f"Dog {i} must be a dictionary")
                    if "name" not in dog or "email" not in dog or "github_token" not in dog:
                        raise ValueError(f"Dog {i} must have 'name', 'email', and 'github_token' keys")
                    if not dog["name"] or not dog["email"] or not dog["github_token"]:
                        raise ValueError(f"Dog {i} name, email, and github_token cannot be empty")

                return dogs_list

            except json.JSONDecodeError as e:
                raise ValueError(f"DOGS env var is not valid JSON: {e}")

        # Backward compatibility: Fall back to DOG_NAME/DOG_EMAIL/DOG_GITHUB_TOKEN
        dog_name = os.getenv("DOG_NAME")
        dog_email = os.getenv("DOG_EMAIL")
        dog_github_token = os.getenv("DOG_GITHUB_TOKEN")

        if dog_name and dog_email and dog_github_token:
            return [{"name": dog_name, "email": dog_email, "github_token": dog_github_token}]

        # No dogs configured at all
        raise ValueError(
            "No dogs configured. Please set either:\n"
            "  - DOGS environment variable (JSON array with name, email, github_token), or\n"
            "  - DOG_NAME, DOG_EMAIL, and DOG_GITHUB_TOKEN for backward compatibility"
        )

    @property
    def dog_name(self) -> str:
        """
        Get dog identity name (legacy, for backward compatibility).

        Returns the first dog's name from the dogs list.
        """
        return self.dogs[0]["name"]

    @property
    def dog_email(self) -> str:
        """
        Get dog email for git commits (legacy, for backward compatibility).

        Returns the first dog's email from the dogs list.
        """
        return self.dogs[0]["email"]

    @property
    def base_branch(self) -> str:
        """Get base branch for PRs."""
        return os.getenv("BASE_BRANCH", "main")


# Global config instance
config = Config()
