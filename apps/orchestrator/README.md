# Dogwalker Orchestrator

The orchestrator manages the Dogwalker system - receives tasks from Slack and coordinates dog workers.

## Structure

```
src/
├── bot.py                  # Main entry point
├── celery_app.py          # Celery configuration
├── dog_selector.py        # Dog assignment logic
├── tasks.py               # Celery task definitions
└── listeners/             # Event listeners (modular)
    ├── __init__.py        # Register all listeners
    ├── events/
    │   ├── __init__.py    # Register event handlers
    │   └── app_mentioned.py  # Handle @dogwalker mentions
    └── actions/           # Future: button clicks, etc.
```

## Features

### Modular Listener Pattern

Following Slack Bolt best practices (inspired by bolt-python-assistant-template):

- **Clean separation**: Each event type has its own file
- **Easy to extend**: Add new listeners without touching core code
- **Testable**: Each handler is independently testable
- **Type-safe**: Uses proper type hints

### Event Handlers

**`@app_mention`** - Handle @dogwalker mentions
- Extracts task description from message
- Selects available dog
- Creates Celery task
- Posts acknowledgment to Slack thread

## Running Locally

### Prerequisites

1. **Environment variables** (see `.env.example` in project root):
   ```bash
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ANTHROPIC_API_KEY=sk-ant-...
   GITHUB_TOKEN=ghp_...
   GITHUB_REPO=owner/repo
   REDIS_URL=redis://localhost:6379
   DOG_NAME=Bryans-Coregi
   DOG_EMAIL=coregi@bryanowens.dev
   ```

2. **Redis running**:
   ```bash
   redis-server
   ```

3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

### Start the Bot

```bash
cd apps/orchestrator
python src/bot.py
```

You should see:
```
Configuration loaded successfully
Slack bot initialized successfully
Starting Dogwalker Slack bot...
Connected to Slack! Bot is ready to receive events.
Try mentioning @dogwalker in a Slack channel to test.
```

### Start Celery Worker (Required)

In another terminal:
```bash
cd apps/worker
celery -A src.celery_app worker --loglevel=info
```

## Testing

### Test Slack Connection

1. Invite bot to a Slack channel: `/invite @dogwalker`
2. Mention bot: `@dogwalker hello`
3. Check logs for:
   - Bot receives mention
   - Task is created and queued
   - Dog is selected

### Test Task Creation

```
@dogwalker add a comment to README.md saying "hello from dogwalker"
```

Expected flow:
1. Bot responds: "🐕 Bryans-Coregi is taking this task!"
2. Worker picks up task
3. Worker clones repo, runs Aider, creates PR
4. Bot posts: "✅ PR ready: [link]"

## Architecture

### Data Flow

```
Slack mention → bot.py
              ↓
         register_listeners()
              ↓
    listeners/events/app_mentioned.py
              ↓
         dog_selector.select_dog()
              ↓
       tasks.run_coding_task.delay()
              ↓
         Celery → Redis queue
              ↓
         Worker picks up task
```

### Adding New Event Listeners

1. **Create handler file**:
   ```python
   # listeners/events/reaction_added.py
   def handle_reaction_added(event: dict, say, logger):
       logger.info(f"Reaction added: {event}")
   ```

2. **Register in `listeners/events/__init__.py`**:
   ```python
   from .reaction_added import handle_reaction_added

   def register(app: App):
       app.event("app_mention")(handle_app_mention)
       app.event("reaction_added")(handle_reaction_added)  # ← Add this
   ```

3. **Add required scopes** in Slack app settings:
   - Go to OAuth & Permissions
   - Add scope: `reactions:read`
   - Reinstall app

### Adding Action Listeners

For buttons, menus, etc.:

1. **Create handler file**:
   ```python
   # listeners/actions/approve_pr.py
   def handle_approve_pr(ack, body, logger):
       ack()  # Acknowledge immediately
       logger.info(f"PR approved: {body}")
   ```

2. **Register in `listeners/actions/__init__.py`**:
   ```python
   from slack_bolt import App
   from .approve_pr import handle_approve_pr

   def register(app: App):
       app.action("approve_pr_button")(handle_approve_pr)
   ```

3. **Update `listeners/__init__.py`**:
   ```python
   from . import events, actions

   def register_listeners(app: App):
       events.register(app)
       actions.register(app)  # ← Add this
   ```

## Deployment (Railway)

This app deploys as a **web service** that runs the Slack bot.

### Railway Configuration

**Service name**: `orchestrator`
**Build command**: `pip install -r requirements.txt`
**Start command**: `python src/bot.py` (defined in railway.json)

### Required Environment Variables

Set in Railway project settings (same as local `.env`):
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_REPO`
- `REDIS_URL` (automatically provided by Railway)
- `DOG_NAME`
- `DOG_EMAIL`

### Health Checks

The bot logs connection status:
- ✅ "Connected to Slack! Bot is ready to receive events."
- ❌ "Failed to start Slack bot: [error]"

Monitor Railway logs to ensure bot stays connected.

## Troubleshooting

### Bot doesn't respond to mentions

1. **Check bot is invited to channel**:
   ```
   /invite @dogwalker
   ```

2. **Check logs for connection**:
   ```
   Connected to Slack! Bot is ready to receive events.
   ```

3. **Verify tokens**:
   ```bash
   python ../../scripts/setup/validate_env.py
   ```

### "Configuration error"

Missing or invalid environment variables:
```bash
# Check .env file exists
ls -la ../../../../.env

# Validate all required vars
python ../../scripts/setup/validate_env.py
```

### Import errors

Path issues with shared modules:
```bash
# Test imports
python -c "import sys; sys.path.insert(0, '../shared/src'); from config import Config; print('✅ Imports work')"
```

### Redis connection failed

```bash
# Start Redis
redis-server

# Test connection
redis-cli ping  # Should return "PONG"
```

## Future Enhancements

- **Multiple dogs** with intelligent load balancing
- **Task prioritization** (urgent vs. normal)
- **Human-in-the-loop** clarification questions
- **Task status updates** in threads
- **Dog specialization** (frontend dog, backend dog, etc.)
- **Cost tracking** per task
- **Task history** and analytics

## References

- [Slack Bolt for Python](https://slack.dev/bolt-python/)
- [Socket Mode](https://api.slack.com/apis/connections/socket)
- [Celery Documentation](https://docs.celeryq.dev/)
