# Deployment Guide

## Prerequisites

Before deploying Dogwalker, you need:

1. **Railway Account** - Sign up at https://railway.app
2. **GitHub Account** - For repository access and dog identities
3. **Slack Workspace** - With admin access to install apps
4. **Anthropic API Key** - From https://console.anthropic.com

## Environment Variables

Create a `.env` file (see `.env.example`) with these values:

```bash
# Anthropic API (required)
ANTHROPIC_API_KEY=sk-ant-...

# GitHub Repository (required)
GITHUB_REPO=owner/reponame        # e.g., "bryans-org/my-app"

# Slack (required)
SLACK_BOT_TOKEN=xoxb-...          # From Slack App settings
SLACK_APP_TOKEN=xapp-...          # For Socket Mode

# Redis (Railway provides this automatically)
REDIS_URL=redis://localhost:6379  # Local only, Railway auto-sets

# Dog Configuration (REQUIRED - Multiple Dogs with per-dog GitHub tokens)
# Each dog needs a unique GitHub account and personal access token
DOGS='[
  {"name": "Bryans-Coregi", "email": "coregi@bryanowens.dev", "github_token": "github_pat_11AAA..."},
  {"name": "Bryans-Bitbull", "email": "bitbull@bryanowens.dev", "github_token": "github_pat_11BBB..."},
  {"name": "Bryans-Poodle", "email": "poodle@bryanowens.dev", "github_token": "github_pat_11CCC..."}
]'

# GitHub Token (OPTIONAL - for orchestrator read-only operations)
# If not provided, will use first dog's token as fallback
# GITHUB_TOKEN=github_pat_...

# Legacy: Single Dog (deprecated - use DOGS instead)
# DOG_NAME=Bryans-Coregi
# DOG_EMAIL=coregi@bryanowens.dev
# DOG_GITHUB_TOKEN=github_pat_...

# Base Branch (optional, defaults to main)
BASE_BRANCH=main
```

## Local Development Setup

### 1. Install Dependencies

```bash
# Install orchestrator dependencies
cd apps/orchestrator
pip install -r requirements.txt

# Install worker dependencies
cd ../worker
pip install -r requirements.txt

# Install shared dependencies
cd ../shared
pip install -r requirements.txt
```

### 2. Start Redis

```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Linux (apt)
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. Start Orchestrator (Slack Bot)

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
```

### 4. Start Worker (Celery)

In a new terminal:

```bash
cd apps/worker
celery -A src.celery_app worker --loglevel=info
```

You should see: "celery@hostname ready."

### 5. Test in Slack

1. Go to your Slack workspace
2. In any channel where the bot is added:
   ```
   @dogwalker hello world
   ```
3. You should see: "🐕 Bryans-Coregi is taking this task!"

## Architecture Notes

The orchestrator (`apps/orchestrator`) uses a **modular listener pattern** inspired by [bolt-python-assistant-template](https://github.com/slack-samples/bolt-python-assistant-template):

- **Clean entry point**: `bot.py` handles initialization and startup
- **Modular event handlers**: Each event type has its own file in `listeners/events/`
- **Easy extensibility**: Add new listeners without modifying core bot code
- **Type-safe**: Proper type hints on all handler functions

**Key files:**
- `src/bot.py` - Main entry point
- `src/listeners/__init__.py` - Registers all listeners with the Slack app
- `src/listeners/events/app_mentioned.py` - Handles @dogwalker mentions
- `src/dog_selector.py` - Selects which dog handles each task
- `src/tasks.py` - Celery task definitions (contract)

This pattern makes it easy to add new event handlers (reactions, buttons, etc.) without touching the core bot logic.

## Setting Up Slack App

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Dogwalker"
4. Choose your workspace

### 2. Configure Bot Token Scopes

Go to "OAuth & Permissions" and add these scopes:

**Bot Token Scopes:**
- `app_mentions:read` - Receive @mentions
- `chat:write` - Post messages
- `channels:history` - Read channel messages
- `groups:history` - Read private channel messages
- `users:read` - Read user display names and profile info
- `team:read` - Read workspace info (for profile URLs)

### 3. Enable Socket Mode

1. Go to "Socket Mode" in sidebar
2. Enable Socket Mode
3. Create an app-level token with `connections:write` scope
4. Copy token → This is your `SLACK_APP_TOKEN`

### 4. Subscribe to Events

1. Go to "Event Subscriptions"
2. Enable Events
3. Subscribe to bot events:
   - `app_mention` - When someone @mentions the bot

### 5. Install App to Workspace

1. Go to "Install App"
2. Click "Install to Workspace"
3. Authorize the app
4. Copy "Bot User OAuth Token" → This is your `SLACK_BOT_TOKEN`

### 6. Invite Bot to Channel

In Slack:
```
/invite @dogwalker
```

## Setting Up GitHub

### 1. Create Dog GitHub Accounts

Create separate GitHub accounts for each dog:

**Example:**
- Username: `Bryans-Coregi`
- Email: `coregi@bryanowens.dev`
- Display Name: `Coregi (Dogwalker AI)`

### 2. Create Fine-Grained Personal Access Token

**Important:** Use fine-grained tokens (not classic tokens, which are deprecated)

For the dog account:

1. Go to https://github.com/settings/tokens
2. Click **"Fine-grained tokens"** tab
3. Click **"Generate new token"**
4. Configure:
   - **Token name**: `Dogwalker - [DogName]`
   - **Expiration**: 90 days or custom (max 1 year)
   - **Resource owner**: Your account or organization
   - **Repository access**: Select specific repositories or all
5. Set **Repository permissions**:
   - **Contents**: Read and write (push commits)
   - **Pull requests**: Read and write (create PRs)
   - **Metadata**: Read-only (auto-selected)
   - **Workflows**: Read and write (optional - only if modifying CI/CD)
6. Click **"Generate token"**
7. **Copy token immediately** → This is your `GITHUB_TOKEN`
   - Format: `github_pat_11AAAAAA...`
   - You won't see it again!

### 3. Add Dog as Collaborator

Add the dog GitHub account to your target repository:

1. Go to repository settings
2. Collaborators → Add people
3. Add dog account (e.g., `Bryans-Coregi`)
4. Grant "Write" access

## Railway Deployment

### 1. Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Choose "Empty Project"
4. Name: "dogwalker"

### 2. Add Redis Service

1. Click "New" → "Database" → "Add Redis"
2. Railway automatically sets `REDIS_URL` environment variable

### 3. Deploy Orchestrator

1. Click "New" → "GitHub Repo"
2. Select your dogwalker repo
3. Root Directory: `/apps/orchestrator`
4. Name: "orchestrator"
5. Add environment variables (see list above)
6. Deploy

Railway will:
- Build: `pip install -r requirements.txt`
- Start: `python src/bot.py` (from railway.json)

### 4. Deploy Worker

1. Click "New" → "GitHub Repo" (same repo)
2. Root Directory: `/apps/worker`
3. Name: "worker"
4. Add same environment variables as orchestrator
5. Deploy

Railway will:
- Build: `pip install -r requirements.txt`
- Start: `celery -A src.celery_app worker --loglevel=info`

### 5. Set Environment Variables

For both orchestrator and worker services:

1. Go to service → Variables
2. Add all required variables from `.env.example`
3. Use `${{REDIS_URL}}` for Redis (Railway provides this)

**Important:** Each service needs the same environment variables!

### 6. Verify Deployment

Check logs for each service:

**Orchestrator logs should show:**
```
Configuration loaded successfully
Slack bot initialized successfully
Starting Dogwalker Slack bot...
Connected to Slack! Bot is ready to receive events.
```

The orchestrator uses a modular listener pattern where event handlers are organized in `listeners/events/` directory.

**Worker logs should show:**
```
celery@worker ready.
```

## Testing End-to-End

1. In Slack, mention the bot:
   ```
   @dogwalker add a hello world function to README.md
   ```

2. Check orchestrator logs:
   ```
   Creating task C123_1234567890.123456 for dog Coregi (Bryans-Coregi)
   Task queued with Celery task ID: abc123
   ```

3. Check worker logs:
   ```
   Worker executing task C123_1234567890.123456 as Bryans-Coregi
   Cloning repository...
   Generating implementation plan...
   Creating draft PR...
   Running Aider...
   Running self-review...
   Writing tests...
   Pushing changes...
   Updating PR description...
   Marking PR as ready for review...
   Task completed successfully
   ```

4. Check Slack thread (you'll see 3 messages):
   ```
   Message 1: 🐕 Coregi is taking this task!

   Message 2: 📋 Coregi created a draft PR with the plan
              [Dogwalker] Add a hello world function to README
              Plan preview: **Proposed Implementation:** Analyze the codebase...
              Now implementing the changes...

   Message 3: ✅ Work complete! PR ready for review
              [Dogwalker] Add a hello world function to README
              Completed by Coregi
   ```

5. Check GitHub:
   - New branch: `bryans-coregi/add-a-hello-world-function-to-readme`
   - PR initially shows as "Draft" with plan
   - PR automatically marked as "Ready for review" when complete
   - PR description includes:
     - Requester (hyperlinked to Slack profile)
     - Request timestamp (exact Pacific Time)
     - Implementation plan
     - Files modified
     - Quality assurance checklist
     - Task duration

## Troubleshooting

### Bot doesn't respond in Slack

**Check:**
- Orchestrator service is running (Railway logs)
- `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are correct
- Socket Mode is enabled
- Bot is invited to channel (`/invite @dogwalker`)

**Fix:**
```bash
# Test locally first
cd apps/orchestrator
python src/bot.py
# Should show "Connected to Slack"
```

### Worker doesn't process tasks

**Check:**
- Worker service is running (Railway logs)
- `REDIS_URL` is set correctly
- Worker can connect to Redis

**Fix:**
```bash
# Test worker locally
cd apps/worker
celery -A src.celery_app worker --loglevel=info
# Should show "celery@hostname ready."
```

### Git push fails

**Check:**
- `GITHUB_TOKEN` is valid and not expired
- Dog account has write access to repo
- `GITHUB_REPO` format is correct (`owner/repo`)

**Fix:**
```bash
# Test token manually
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
# Should return dog account info
```

### Aider fails to make changes

**Check:**
- `ANTHROPIC_API_KEY` is valid
- Task description is clear and specific
- Repository files are readable

**Fix:**
```bash
# Test Aider locally
cd scripts/tests
python test_aider.py
```

### PR creation fails

**Check:**
- Branch was pushed successfully
- GitHub token has PR permissions
- Base branch (main) exists

**Fix:**
- Check worker logs for specific error
- Verify branch exists: `git ls-remote origin dogwalker/*`

## Monitoring

### Railway Dashboard

Monitor services in Railway dashboard:

1. **Metrics** - CPU, memory, network usage
2. **Logs** - Real-time logs for debugging
3. **Deploys** - Deployment history

### Slack Monitoring

All task updates post to Slack threads. You'll see 3 messages for successful tasks (or 4 if errors occur):

1. **Task Started**: "🐕 Coregi is taking this task!"
2. **Draft PR Created**: "📋 Coregi created a draft PR with the plan [link + preview]"
3. **Task Completed**: "✅ Work complete! PR ready for review [link]"

If errors occur, you'll see instead:
- **Task Failed**: "❌ Task failed: [error]"

Each message appears in the same Slack thread for easy tracking.

### Cost Tracking

Monitor costs:
1. **Railway:** ~$20-40/month (infrastructure)
2. **Anthropic API:** ~$3-10/task (depends on complexity)
3. **GitHub:** Free (under 2000 API requests/hour)
4. **Slack:** Free (under 10K messages/month)

## Updating Deployment

### Push Updates

Railway auto-deploys on git push:

```bash
git add .
git commit -m "Update worker logic"
git push origin main
```

Railway will:
1. Detect changes
2. Rebuild affected services
3. Deploy with zero downtime

### Manual Deploy

Force redeploy in Railway dashboard:
1. Go to service
2. Click "Deploy" → "Redeploy"

## Scaling

### Add More Workers

In Railway:
1. Click "New" → "GitHub Repo"
2. Root Directory: `/apps/worker`
3. Name: "worker-2"
4. Same environment variables
5. Deploy

Now you have 2 workers processing tasks in parallel!

### Add More Dogs

Update `DOGS` environment variable in Railway:

```json
[
  {"name": "Bryans-Coregi", "email": "coregi@bryanowens.dev", "github_token": "github_pat_11AAA..."},
  {"name": "Bryans-Bitbull", "email": "bitbull@bryanowens.dev", "github_token": "github_pat_11BBB..."},
  {"name": "Bryans-Poodle", "email": "poodle@bryanowens.dev", "github_token": "github_pat_11CCC..."}
]
```

**Steps:**
1. Create GitHub accounts for each new dog
2. Generate fine-grained GitHub PAT for each dog with:
   - Contents: Read and write
   - Pull requests: Read and write
   - Metadata: Read-only
3. Add each dog as collaborator to target repo
4. Update `DOGS` env var in Railway (both orchestrator and worker)
5. Redeploy both orchestrator and worker services

The system will automatically load balance tasks across all configured dogs using least-busy algorithm.

## Security Best Practices

1. **Rotate tokens regularly** (every 3-6 months)
2. **Use fine-grained GitHub tokens** (limit to specific repos)
3. **Enable 2FA** on all accounts
4. **Monitor API usage** (set up alerts for anomalies)
5. **Review PRs carefully** (AI can make mistakes)
6. **Limit Slack channels** (only invite bot to relevant channels)

## Backup & Recovery

### Configuration Backup

Keep `.env.example` updated with latest required variables.

### Token Recovery

If tokens are lost:
1. GitHub: Generate new personal access token
2. Slack: Regenerate tokens in app settings
3. Anthropic: Get from console.anthropic.com

### Service Recovery

If Railway services fail:
1. Check logs for errors
2. Verify environment variables
3. Redeploy service
4. Test end-to-end workflow

## Next Steps

After successful deployment:

1. **Invite beta users** to Slack workspace
2. **Monitor task success rate** (target: >80%)
3. **Track costs** per task
4. **Gather feedback** on code quality
5. **Iterate** on prompt engineering for better results

## Support

For issues:
1. Check Railway logs first
2. Test components locally
3. Verify all environment variables
4. Review this deployment guide
5. Open GitHub issue with logs
