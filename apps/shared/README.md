# Shared Utilities

Shared code used across Dogwalker applications.

## Modules

### `config.py`
Environment variable management with validation.

Usage:
```python
from shared.src.config import config

api_key = config.anthropic_api_key
repo = config.github_repo
```

### `github_client.py`
GitHub API wrapper for creating PRs and managing branches.

Usage:
```python
from shared.src.github_client import GitHubClient

client = GitHubClient(token=config.github_token, repo_name=config.github_repo)
pr_url = client.create_pull_request(
    branch_name="feature/add-rate-limiting",
    title="Add rate limiting to /api/login",
    body="Implementation of rate limiting..."
)
```

### `slack_utils.py`
Formatting helpers for Slack messages.

Usage:
```python
from shared.src.slack_utils import format_task_started, format_task_completed

# When dog starts work
message = format_task_started("Bryans-Coregi", "Add rate limiting")

# When task completes
message = format_task_completed(pr_url, "Bryans-Coregi")
```

## Installation

```bash
pip install -r requirements.txt
```
