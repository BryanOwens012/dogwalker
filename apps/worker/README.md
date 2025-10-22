# Dogwalker Worker

The worker is the AI coding agent (dog) that executes tasks using Aider.

## Components

### `dog.py`
AI coding agent that uses Aider to make code changes.

**Features:**
- Initializes Aider with Claude Sonnet 4
- Auto-detects relevant files using repo map
- Executes natural language coding tasks in multiple phases:
  - **Plan generation**: Analyzes codebase and creates implementation plan
  - **Implementation**: Makes code changes based on task
  - **Self-review**: Critiques and improves code quality
  - **Test writing**: Writes comprehensive tests and verifies they pass
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
2. Create feature branch (descriptive name with dog prefix)
3. Generate implementation plan with Aider
4. Push empty branch and create draft PR with plan
5. Post draft PR announcement to Slack with plan preview
6. Run Aider to implement code changes
7. Run self-review phase for quality improvements
8. Write comprehensive tests and verify they pass
9. Commit and push all changes
10. Update PR description with complete details
11. Mark PR as "Ready for Review" (exit draft state)
12. Post completion announcement to Slack

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

1. Orchestrator creates task in Redis queue with full metadata
2. Worker picks up task from queue
3. Worker clones repo to ephemeral `workdir/`
4. Worker generates implementation plan using Aider
5. Worker creates draft PR with plan (early visibility)
6. Worker posts draft PR to Slack with plan preview
7. Aider implements code changes using Claude Sonnet 4
8. Aider runs self-review and makes improvements
9. Aider writes comprehensive tests and verifies they pass
10. Worker pushes all changes
11. Worker updates PR with complete description
12. Worker marks PR as "Ready for Review"
13. Worker posts completion to Slack
14. Worker cleans up work directory

## Configuration

### Model Selection
Default: `anthropic/claude-sonnet-4-20250514` (best for complex tasks)

To use a different model, modify `dog.py`:
```python
dog = Dog(repo_path=work_dir, model_name="anthropic/claude-haiku-3.5")
```

Note: Model names must include the provider prefix when using Aider.

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
