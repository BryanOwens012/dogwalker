"""Dogwalker Slack bot - main entry point."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import Config
from listeners import register_listeners

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load and validate configuration
try:
    config = Config()
    logger.info("Configuration loaded successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    logger.error("Please ensure your .env file contains all required variables.")
    sys.exit(1)

# Initialize Slack app
app = App(
    token=config.slack_bot_token,
    client=WebClient(
        base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
        token=config.slack_bot_token,
    ),
)

# Register all event listeners
register_listeners(app)

logger.info("Slack bot initialized successfully")


def start_bot() -> None:
    """Start the Slack bot in Socket Mode."""
    try:
        logger.info("Starting Dogwalker Slack bot...")
        logger.info(f"Connecting with app token: {config.slack_app_token[:20]}...")

        handler = SocketModeHandler(app, config.slack_app_token)

        logger.info("Connected to Slack! Bot is ready to receive events.")
        logger.info("Try mentioning @dogwalker in a Slack channel to test.")

        handler.start()
    except Exception as e:
        logger.exception(f"Failed to start Slack bot: {e}")
        raise


if __name__ == "__main__":
    start_bot()
