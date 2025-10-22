# Dogwalker Architecture

## System Overview

Dogwalker is a multi-agent AI coding system that automates the path from Slack feature request to PR-ready code.

```
┌─────────────────────────────────────────────────────────────┐
│                         User (Slack)                         │
│                  "@dogwalker add rate limiting"              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator (Slack Bot)                    │
│  - Receives @mentions                                        │
│  - Selects available dog                                     │
│  - Creates Celery task                                       │
│  - Posts acknowledgment                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│                     Redis (Task Queue)                       │
│  - Stores pending tasks                                      │
│  - Enables async processing                                  │
│  - Tracks task status                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│                    Worker (Dog Agent)                        │
│  1. Clones repo to ephemeral workdir                         │
│  2. Creates feature branch                                   │
│  3. Generates implementation plan with Aider                 │
│  4. Creates DRAFT PR with plan                               │
│  5. Posts draft PR to Slack (with plan preview)             │
│  6. Runs Aider to implement changes                         │
│  7. Runs self-review and improvements                       │
│  8. Writes comprehensive tests and verifies they pass       │
│  9. Commits and pushes changes                              │
│  10. Updates PR with complete details                       │
│  11. Marks PR as "Ready for Review"                         │
│  12. Posts completion to Slack thread                       │
│  13. Cleans up workdir                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│                   GitHub (Pull Request)                      │
│  - Human reviews PR                                          │
│  - Merges or requests changes                               │
│  - Dogwalker can retry on feedback                          │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Orchestrator (apps/orchestrator)

**Purpose:** Slack interface and task coordination

**Tech Stack:**
- Slack Bolt (Python SDK for Slack apps)
- Socket Mode (WebSocket connection, no public webhooks needed)
- Celery (task queue client)

**Key Files:**
- `bot.py` - Main entry point, initialization
- `celery_app.py` - Celery configuration
- `dog_selector.py` - Assigns tasks to available dogs
- `tasks.py` - Celery task definitions (contract)
- `listeners/` - Modular event handlers
  - `listeners/events/app_mentioned.py` - @mention handler
  - `listeners/__init__.py` - Register all listeners

**Architecture Pattern:**
Uses modular listener pattern (inspired by [bolt-python-assistant-template](https://github.com/slack-samples/bolt-python-assistant-template)):
- Clean separation: Each event type in its own file
- Easy extensibility: Add new listeners without touching core code
- Type-safe: Proper type hints on all handlers
- Testable: Each handler independently testable

**Responsibilities:**
1. Listen for `@dogwalker` mentions via Slack Socket Mode
2. Parse task description from message
3. Select least-busy dog (MVP: round-robin)
4. Create Celery task with task metadata
5. Post immediate acknowledgment to Slack
6. Store task ID for status tracking

### Worker (apps/worker)

**Purpose:** Execute code changes using AI

**Tech Stack:**
- Aider (AI pair programming CLI)
- Claude Sonnet 4.5 (via Anthropic API)
- Celery (task queue worker)
- GitPython / subprocess (git operations)

**Key Files:**
- `worker_tasks.py` - Actual task implementation
- `dog.py` - Aider wrapper for code editing
- `repo_manager.py` - Git operations (clone, branch, push)
- `celery_app.py` - Celery worker configuration

**Responsibilities:**
1. Pick up tasks from Redis queue
2. Clone target repo to ephemeral directory
3. Create feature branch from main (descriptive name with dog prefix)
4. Generate implementation plan using Aider
5. Push empty branch and create draft PR with plan
6. Post draft PR to Slack with plan preview
7. Run Aider to implement changes
8. Run self-review phase for code quality improvements
9. Write comprehensive tests and verify they pass
10. Commit and push final changes
11. Update PR description with complete details
12. Mark PR as "Ready for Review" (exit draft state)
13. Post completion to Slack thread
14. Clean up ephemeral workspace

### Shared (apps/shared)

**Purpose:** Common utilities used by orchestrator and worker

**Key Files:**
- `config.py` - Environment variable management
- `github_client.py` - GitHub API wrapper (PRs, branches)
- `slack_utils.py` - Message formatting helpers

**Benefits:**
- Single source of truth for config
- DRY principle (don't repeat code)
- Easier testing and maintenance

### API (apps/api)

**Purpose:** Future HTTP endpoints and web dashboard

**Status:** Placeholder (not implemented in MVP)

**Future Features:**
- REST API for task status
- Web dashboard for monitoring
- GitHub webhooks
- Programmatic task creation

## Data Flow

### Task Creation Flow

```
1. User: "@dogwalker add rate limiting to /api/login"
   ↓
2. Slack sends event to bot via Socket Mode
   ↓
3. Bot extracts task: "add rate limiting to /api/login"
   ↓
4. Bot selects dog: Bryans-Coregi
   ↓
5. Bot creates Celery task with metadata:
   {
     task_id: "C123_1234567890.123456",
     task_description: "add rate limiting to /api/login",
     branch_name: "bryans-coregi/add-rate-limiting-to-api-login",
     dog_name: "Bryans-Coregi",
     dog_display_name: "Coregi",
     dog_email: "coregi@bryanowens.dev",
     thread_ts: "1234567890.123456",
     channel_id: "C123",
     requester_name: "Bryan Owens",
     requester_profile_url: "https://workspace.slack.com/team/U123",
     start_time: 1234567890.123
   }
   ↓
6. Bot posts to Slack: "🐕 Coregi is taking this task!"
   ↓
7. Task queued in Redis
```

### Task Execution Flow

```
1. Worker picks up task from Redis queue
   ↓
2. Worker clones repo to workdir/task_id/
   ↓
3. Worker creates branch "bryans-coregi/add-rate-limiting-to-api-login"
   ↓
4. Worker initializes Aider to generate implementation plan
   ↓
5. Aider analyzes codebase and creates plan:
   - What architecture will be affected
   - Which files will be modified
   - Implementation approach
   ↓
6. Worker pushes empty branch to GitHub
   ↓
7. Worker creates DRAFT PR with plan in description
   ↓
8. Worker posts to Slack: "📋 Coregi created draft PR with plan [link]"
   ↓
9. Worker runs Aider to implement changes
   ↓
10. Aider searches for relevant files (e.g., api/login.py)
    ↓
11. Aider edits files to add rate limiting
    ↓
12. Aider auto-commits changes
    ↓
13. Worker runs self-review phase
    ↓
14. Aider critiques code quality, security, edge cases
    ↓
15. Aider makes improvements and commits
    ↓
16. Worker runs test writing phase
    ↓
17. Aider writes comprehensive tests (happy path, edge cases, errors)
    ↓
18. Aider runs tests and verifies they pass
    ↓
19. Aider commits tests
    ↓
20. Worker pushes all changes to branch
    ↓
21. Worker updates PR description with:
    - Requester (hyperlinked to Slack profile)
    - Request timestamp (exact Pacific Time)
    - Implementation plan
    - Files modified
    - Test status
    - Duration
    ↓
22. Worker marks PR as "Ready for Review" (exits draft state)
    ↓
23. Worker posts to Slack: "✅ Work complete! PR ready for review [link]"
    ↓
24. Worker cleans up workdir/task_id/
```

## Context Management

**Challenge:** Claude has token limits (200K for Sonnet 4.5)

**Solution:** Aider's intelligent context management

1. **Repo Map** - Compressed view of entire codebase structure
   - Uses tree-sitter to parse code
   - Shows function/class signatures
   - ~1-2K tokens for typical project

2. **Lazy File Loading** - Only read files as needed
   - Start with repo map
   - Search for relevant files
   - Read only what's necessary
   - Typical task uses 5-15K input tokens

3. **Incremental Updates** - Track changes efficiently
   - Only send diffs, not full files
   - Maintains conversation context
   - Stays within token budget

## Error Handling

### Retriable Errors
Network, git, GitHub API failures → Retry with exponential backoff
- Max 3 retries
- Delay: 60s, 120s, 240s
- Post to Slack if all retries fail

### Non-Retriable Errors
Code errors, validation failures, Aider failures → Fail immediately
- Post error to Slack thread
- Include error message for debugging
- Human intervention required

### Error Categories

| Error Type | Retry? | Action |
|-----------|--------|---------|
| Network timeout | Yes | Retry with backoff |
| Git push failure | Yes | Retry (might be transient) |
| GitHub API rate limit | Yes | Wait and retry |
| Aider made no changes | No | Post to Slack, needs clarification |
| Invalid branch name | No | Post to Slack, fix task |
| Auth failure | No | Post to Slack, check credentials |

## Scalability

### Current (MVP)
- Single dog worker
- Sequential task processing
- Single Redis instance
- ~10 tasks/day capacity

### Near-term (Month 2-3)
- 3-5 dog workers
- Parallel task processing
- Dog specialization (frontend/backend)
- ~50 tasks/day capacity

### Long-term (Month 6+)
- Auto-scaling workers
- Multi-repo support
- Intelligent task routing
- Model selection per complexity
- ~500+ tasks/day capacity

## Security Considerations

1. **GitHub Tokens**
   - Use fine-grained personal access tokens
   - Limit to specific repos
   - Rotate regularly

2. **API Keys**
   - Store in environment variables
   - Never commit to git
   - Use Railway secrets in production

3. **Code Isolation**
   - Each task gets ephemeral directory
   - Cleaned up after completion
   - No persistent code storage

4. **Slack Security**
   - Use Socket Mode (no public webhooks)
   - Verify event signatures
   - Limit to specific channels

## Deployment Architecture (Railway)

```
┌─────────────────────────────────────────────────────┐
│                   Railway Project                    │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Orchestrator │  │    Worker    │  │   Redis   │ │
│  │   Service    │  │   Service    │  │  Service  │ │
│  │              │  │              │  │           │ │
│  │ bot.py       │  │ celery worker│  │ (managed) │ │
│  │ Socket Mode  │  │ Aider + Git  │  │           │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                 │       │
│         └─────────────────┴─────────────────┘       │
│                        Redis URL                    │
└─────────────────────────────────────────────────────┘
         │                      │
         v                      v
   Slack API              GitHub API
   (Socket Mode)          (REST)
```

**Services:**
1. **Orchestrator** - Web service running Slack bot
2. **Worker** - Worker service running Celery
3. **Redis** - Managed Redis instance (task queue + results)

**Environment Variables:** Shared across services via Railway project settings

**Cost:** ~$20-40/month (3 services + Redis)

## Future Enhancements

### Multi-Dog Coordination
- Track active tasks per dog
- Assign to least busy dog
- Dog specialization (frontend, backend, tests, docs)

### Human-in-the-Loop
- Dogs can ask clarifying questions
- Pause task until human responds
- Post questions with reaction options
- Resume with clarified context

### Advanced Features
- Multi-step tasks (split into sub-tasks)
- Code review by separate AI agent
- Automated testing before PR
- Cost optimization (use Haiku for simple tasks)
- Multi-repo orchestration
- Integration tests in isolated environments
