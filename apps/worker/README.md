# Dogwalker Worker

The worker is the AI coding agent (dog) that executes tasks using Aider.

## Components

### `dog.py`
AI coding agent that uses Aider to make code changes.

**Features:**
- Initializes Aider with Claude Sonnet 4.5
- Auto-detects relevant files using repo map
- Executes natural language coding tasks
- Verifies changes were made

### `repo_manager.py`
Git repository operations (clone, branch, commit, push).

**Features:**
- Authenticated GitHub cloning
- Branch creation from base branch
- Commit with AI attribution
- Push to remote with upstream tracking

### `worker_tasks.py`
Celery task implementation - actual execution logic.

**Workflow:**
1. Clone repository
2. Create feature branch
3. Run Aider to make code changes
4. Commit and push changes
5. Create pull request
6. Post PR link to Slack thread

### `celery_app.py`
Celery worker configuration.

## Running Locally

1. Ensure Redis is running:
```bash
redis-server
```

2. Set environment variables in `.env` (see `.env.example`)

3. Start the Celery worker:
```bash
celery -A src.celery_app worker --loglevel=info
```

4. In another terminal, start the orchestrator bot:
```bash
cd ../orchestrator
python src/bot.py
```

## Testing Aider Integration

Test Aider on a sample repo before running full workflow:

```bash
cd ../../scripts/tests
python test_aider.py
```

## Deployment (Railway)

This app deploys as a worker service that processes Celery tasks.

**Required services:**
- Redis (message broker)
- Orchestrator app (to create tasks)

**Environment variables:** See `.env.example` in project root

## How It Works

1. Orchestrator creates task in Redis queue
2. Worker picks up task from queue
3. Worker clones repo to ephemeral `workdir/`
4. Worker runs Aider with task description
5. Aider edits code using Claude Sonnet 4.5
6. Worker commits, pushes, and creates PR
7. Worker posts PR link to Slack
8. Worker cleans up work directory

## Configuration

### Model Selection
Default: `claude-sonnet-4.5-20250929` (best for complex tasks)

To use a different model, modify `dog.py`:
```python
dog = Dog(repo_path=work_dir, model_name="claude-haiku-3.5")
```

### Repo Map Tokens
Default: 1024 tokens (good for most projects)

For larger codebases, increase in `dog.py`:
```python
dog = Dog(repo_path=work_dir, map_tokens=2048)
```

## Troubleshooting

### Aider fails to make changes
- Check task description is clear and specific
- Verify Anthropic API key is valid
- Check repo has write permissions

### Git push fails
- Verify GitHub token has `repo` scope
- Check branch doesn't already exist
- Ensure base branch (main) exists

### PR creation fails
- Verify branch was pushed successfully
- Check GitHub token has `repo` scope
- Ensure branch name is valid

## Future Enhancements

- Multiple models per complexity (Sonnet for hard, Haiku for easy)
- Better error recovery (retry with clarification)
- Cost tracking per task
- Time estimation
- Dog specialization (frontend, backend, testing, etc.)
