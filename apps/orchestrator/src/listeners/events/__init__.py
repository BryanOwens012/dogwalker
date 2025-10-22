"""Event listener registration."""

from slack_bolt import App
from .app_mentioned import handle_app_mention
from .message import handle_message


def register(app: App) -> None:
    """
    Register all event handlers.

    Args:
        app: Slack Bolt App instance
    """
    app.event("app_mention")(handle_app_mention)
    app.event("message")(handle_message)
