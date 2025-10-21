# Dogwalker Orchestrator

The orchestrator manages the Dogwalker system - receives tasks from Slack and coordinates dog workers.

## Components

### `bot.py`
Slack bot that listens for `@dogwalker` mentions and creates coding tasks.

**Features:**
- Receives task requests via Slack mentions
- Selects available dog for task
- Creates Celery task in queue
- Posts acknowledgment to Slack thread

### `tasks.py`
Celery task definitions for code generation workflow.

**Main task:** `run_coding_task`
- Queued when user mentions @dogwalker
- Executed by worker app (dog)
- Updates Slack on completion/failure

### `dog_selector.py`
Logic for assigning tasks to available dogs.

**Current:** Single dog (Bryans-Coregi)
**Future:** Load balancing across multiple dogs

### `celery_app.py`
Celery configuration with Redis as broker/backend.

## Running Locally

1. Ensure Redis is running:
```bash
redis-server
```

2. Set environment variables in `.env` (see `.env.example`)

3. Start the Slack bot:
```bash
python src/bot.py
```

4. In another terminal, start a Celery worker (from worker app):
```bash
cd ../worker
celery -A src.celery_app worker --loglevel=info
```

## Deployment (Railway)

This app deploys as a web service that runs the Slack bot.

**Required services:**
- Redis (message broker)
- Worker app (to process tasks)

**Environment variables:** See `.env.example` in project root

## Usage

In Slack:
```
@dogwalker add rate limiting to /api/login
@dogwalker refactor the user authentication module
@dogwalker fix the bug in checkout flow where cart totals are wrong
```

The bot will:
1. Acknowledge with "🐕 Bryans-Coregi is taking this task!"
2. Queue task for worker
3. Worker creates branch, runs Aider, pushes code
4. Worker creates PR and posts link to thread
5. Human reviews and merges PR

## Future Enhancements

- Multiple dogs with intelligent load balancing
- Task prioritization
- Dog specialization (frontend dog, backend dog, etc.)
- Human-in-the-loop clarification questions
- Cost tracking per task
