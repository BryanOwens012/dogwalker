"""Action handler registration for Dogwalker Slack bot."""

from slack_bolt import App
from .cancel_task import handle_cancel_task


def register(app: App) -> None:
    """
    Register all action handlers with the Slack app.

    Action handlers respond to interactive components like buttons,
    select menus, and other user interactions.

    Args:
        app: Slack Bolt App instance
    """
    # Register cancel task button handler
    app.action("cancel_task")(handle_cancel_task)
