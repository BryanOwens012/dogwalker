"""Listener registration for Dogwalker Slack bot."""

from slack_bolt import App
from . import events


def register_listeners(app: App) -> None:
    """
    Register all event listeners with the Slack app.

    Args:
        app: Slack Bolt App instance
    """
    events.register(app)
