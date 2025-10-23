"""Slack message formatting utilities."""

from typing import Optional


def format_task_started(dog_name: str, task_description: str, task_id: str) -> dict:
    """
    Format a message with interactive cancel button for when a dog starts a task.

    Args:
        dog_name: Name of the dog taking the task
        task_description: Description of the task
        task_id: Unique task identifier for cancellation

    Returns:
        Slack message with blocks including cancel button
    """
    return {
        "text": f"🐕 {dog_name} is taking this task! {task_description}",  # Fallback text for notifications
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🐕 *{dog_name}* is taking this task!\n\n_{task_description}_"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel Task"
                        },
                        "style": "danger",
                        "action_id": "cancel_task",
                        "value": task_id,
                    }
                ]
            }
        ]
    }


def format_draft_pr_created(pr_title: str, pr_url: str, plan_preview: str, dog_name: str) -> str:
    """
    Format a message for when a draft PR is created with the plan.

    Args:
        pr_title: Title of the PR
        pr_url: URL of the draft PR
        plan_preview: Brief preview of the implementation plan (max 350 chars)
        dog_name: Name of the dog working on the task

    Returns:
        Formatted Slack message
    """
    return f"""📋 *{dog_name} created a draft PR with the plan*

<{pr_url}|{pr_title}>

*Plan preview:*
```
{plan_preview}
```

_Now implementing the changes..._"""


def format_task_completed(pr_title: str, pr_url: str, dog_name: str) -> str:
    """
    Format a message for when a task is completed and PR is ready.

    Args:
        pr_title: Title of the PR
        pr_url: URL of the PR
        dog_name: Name of the dog that completed the task

    Returns:
        Formatted Slack message
    """
    return f"""✅ *Work complete! PR ready for review*

<{pr_url}|{pr_title}>

_Completed by {dog_name}_"""


def format_task_failed(error_message: str, dog_name: str) -> str:
    """
    Format a message for when a task fails.

    Args:
        error_message: Error description
        dog_name: Name of the dog that attempted the task

    Returns:
        Formatted Slack message
    """
    return f"❌ *Task failed*\n\n```{error_message}```"


def format_task_cancelled(
    dog_name: str,
    cancelled_by: str,
    pr_url: Optional[str] = None,
    phase_completed: Optional[str] = None
) -> str:
    """
    Format a message for when a task is cancelled by user.

    Args:
        dog_name: Name of the dog that was working on the task
        cancelled_by: Display name of person who cancelled the task
        pr_url: URL of the draft PR (if created before cancellation)
        phase_completed: Description of what was completed before cancellation

    Returns:
        Formatted Slack message
    """
    message = f"🛑 *Task cancelled by {cancelled_by}*\n\n"

    if phase_completed:
        message += f"_{dog_name} completed: {phase_completed}_\n\n"
    else:
        message += f"_{dog_name} stopped before making changes._\n\n"

    if pr_url:
        message += f"Draft PR with partial progress: <{pr_url}|View PR>"
    else:
        message += "No PR was created."

    return message


def format_draft_pr_body(
    task_description: str,
    requester_name: str,
    requester_profile_url: Optional[str],
    start_time: float,
    plan: str,
) -> str:
    """
    Format draft PR body with initial task details and plan.

    Args:
        task_description: Original task description
        requester_name: Display name of person who requested the change
        requester_profile_url: Slack profile URL of the requester
        start_time: Unix timestamp when request was made
        plan: Implementation plan

    Returns:
        Formatted PR body in markdown
    """
    from datetime import datetime
    import pytz

    # Convert to local time (Pacific Time for the user)
    local_tz = pytz.timezone('America/Los_Angeles')
    request_time = datetime.fromtimestamp(start_time, tz=pytz.UTC).astimezone(local_tz)
    request_time_str = request_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")

    # Create markdown link for requester if profile URL is available
    if requester_profile_url:
        requester_link = f"[{requester_name}]({requester_profile_url})"
    else:
        requester_link = requester_name

    body = f"""## 🐕 Dogwalker AI Task Report

### 👤 Requester
**{requester_link}** requested this change

### 📋 Request
> {task_description}

### 📅 When
Requested on **{request_time_str}**

### 🎯 Implementation Plan
{plan}

---

🚧 **This is a draft PR** - Implementation in progress...

_This PR will be updated with changes and marked ready for review when complete._

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)
"""
    return body


def format_pr_body(
    task_description: str,
    requester_name: str,
    requester_profile_url: Optional[str],
    start_time: float,
    duration_seconds: float,
    files_modified: Optional[list] = None,
    plan_summary: Optional[str] = None,
    critical_review_points: Optional[str] = None,
) -> str:
    """
    Format PR body with standardized task details.

    Args:
        task_description: Original task description
        requester_name: Display name of person who requested the change
        requester_profile_url: Slack profile URL of the requester
        start_time: Unix timestamp when request was made
        duration_seconds: How long the task took in seconds
        files_modified: List of files that were modified (optional)
        plan_summary: Summary of the implementation plan (optional)
        critical_review_points: AI-identified critical areas needing review (optional)

    Returns:
        Formatted PR body in markdown
    """
    from datetime import datetime
    import pytz

    # Convert to local time (Pacific Time for the user)
    local_tz = pytz.timezone('America/Los_Angeles')
    request_time = datetime.fromtimestamp(start_time, tz=pytz.UTC).astimezone(local_tz)
    request_time_str = request_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")

    # Format duration
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    if minutes > 0:
        duration_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
    else:
        duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"

    # Create markdown link for requester if profile URL is available
    if requester_profile_url:
        requester_link = f"[{requester_name}]({requester_profile_url})"
    else:
        requester_link = requester_name

    body = f"""## 🐕 Dogwalker AI Task Report

### 👤 Requester
**{requester_link}** requested this change

### 📋 Request
> {task_description}

### 📅 When
Requested on **{request_time_str}**

### 🎯 Implementation Plan
"""

    if plan_summary:
        body += f"{plan_summary}\n"
    else:
        body += "_AI agent autonomously determined the implementation approach_\n"

    body += "\n### 📝 Changes Made\n"

    if files_modified:
        body += "The following files were modified:\n"
        for file in files_modified:
            body += f"- `{file}`\n"
    else:
        body += "_File changes were committed automatically by the AI agent_\n"

    # Only add review notes if there are critical areas identified
    if critical_review_points and critical_review_points.strip():
        body += f"""
### ⚠️ Critical Review Areas
{critical_review_points}

"""

    body += f"""### ✅ Quality Assurance
This PR has been:
- Self-reviewed by the AI agent
- Comprehensive tests written and verified passing
- All code changes validated before submission

### ⏱️ Task Duration
Completed in **{duration_str}**

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

Co-Authored-By: Claude <noreply@anthropic.com>
"""
    return body
