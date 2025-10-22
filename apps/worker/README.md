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
- Bi-directional Slack communication:
  - `ask_human()`: Ask clarifying questions and wait for responses
  - `check_for_feedback()`: Check for human feedback without blocking
- Verifies changes were made

### `dog_communication.py`
Bi-directional Slack communication helper.

**Features:**
- Post messages, questions, and updates to Slack threads
- Read human messages from Redis (non-blocking)
- Wait for human responses with timeout (blocking)
- Format feedback for AI prompt injection
- Collect and format all thread messages for PR descriptions
- Message pointer tracking to avoid re-reading messages

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
6. **Check for human feedback** (checkpoint 1)
7. Run Aider to implement code changes
8. **Check for human feedback** (checkpoint 2)
9. Run self-review phase for quality improvements
10. **Check for human feedback** (checkpoint 3)
11. Write comprehensive tests and verify they pass
12. **Check for human feedback** (checkpoint 4 - final)
13. Commit and push all changes
14. Collect all thread feedback for PR description
15. Update PR description with complete details and thread feedback
16. Mark PR as "Ready for Review" (exit draft state)
17. Post completion announcement to Slack

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

## Bi-Directional Communication

Dogs can read and respond to human feedback during task execution:

### How It Works

1. **Human posts feedback** in Slack thread while dog is working
2. **Orchestrator stores message** in Redis (`dogwalker:thread_messages:{thread_ts}`)
3. **Orchestrator adds 👀 reaction** to acknowledge receipt
4. **Worker checks for feedback** at 4 key checkpoints:
   - Before implementation
   - After implementation
   - After self-review
   - After testing (final checkpoint)
5. **Worker incorporates feedback** by re-running Aider with feedback prompt
6. **Worker posts acknowledgment** to Slack: "I've received your feedback..."
7. **PR description includes thread feedback** in "💬 Thread Feedback" section

### Feedback Checkpoints

Each checkpoint follows this pattern:
```python
feedback = communication.check_for_feedback()
if feedback:
    communication.post_update("I've received your feedback and will incorporate it!")
    feedback_prompt = communication.format_feedback_for_prompt(feedback)
    dog.run_task(feedback_prompt)  # Re-run Aider with feedback
```

### DogCommunication Methods

**Non-blocking (used at checkpoints):**
- `check_for_feedback()` - Quick check, returns None if no new messages

**Blocking (future use for questions):**
- `ask_human(question, timeout=600)` - Ask question and wait for response
- `wait_for_response(timeout=600)` - Poll for messages until timeout

**Posting to Slack:**
- `post_message(text, emoji)` - Send message to thread
- `post_question(question)` - Ask question and indicate waiting
- `post_update(message)` - Send status update

**PR Description:**
- `get_all_messages()` - Retrieve all thread messages
- `format_messages_for_pr()` - Format as markdown bullet list

## Implemented Features

- ✅ **Bi-directional communication** - Dogs read and respond to feedback
- ✅ **Multiple feedback checkpoints** - 4 checkpoints during task lifecycle
- ✅ **Thread feedback in PRs** - All messages included in PR description
- ✅ **Dog helper methods** - `ask_human()` and `check_for_feedback()`

## Future Enhancements

- Multiple models per complexity (Sonnet for hard, Haiku for easy)
- Better error recovery (retry with clarification)
- **Proactive dog questions** - Dogs ask clarifying questions when needed
- Cost tracking per task
- Time estimation
- Dog specialization (frontend, backend, testing, etc.)
