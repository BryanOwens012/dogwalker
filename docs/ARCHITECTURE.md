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
  - `listeners/events/message.py` - Thread message handler (bi-directional communication)
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
3. Select least-busy dog using Redis-based load balancing
4. Mark selected dog as busy with task ID
5. Create Celery task with task metadata
6. Post immediate acknowledgment to Slack
7. Store task ID for status tracking
8. Listen for thread messages posted during task execution
9. Store human feedback in Redis for workers to read
10. Add 👀 reaction to acknowledge message receipt

**Load Balancing:**
- Tracks active tasks per dog in Redis (`dogwalker:active_tasks:{dog_name}`)
- Uses least-busy algorithm: selects dog with fewest active tasks
- Falls back to round-robin if Redis unavailable
- Automatically marks dogs free when tasks complete or fail

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
- `dog_communication.py` - Bi-directional Slack communication helper
- `repo_manager.py` - Git operations (clone, branch, push)
- `celery_app.py` - Celery worker configuration

**Responsibilities:**
1. Pick up tasks from Redis queue
2. Clone target repo to ephemeral directory
3. Create feature branch from main (descriptive name with dog prefix)
4. Generate implementation plan using Aider
5. Push empty branch and create draft PR with plan
6. Post draft PR to Slack with plan preview
7. **Check for human feedback** before implementation
8. Run Aider to implement changes
9. **Check for human feedback** after implementation
10. Run self-review phase for code quality improvements
11. **Check for human feedback** after self-review
12. Write comprehensive tests and verify they pass
13. **Check for human feedback** after testing (final checkpoint)
14. Commit and push final changes
15. Collect all thread feedback for PR description
16. Update PR description with complete details and thread feedback
17. Mark PR as "Ready for Review" (exit draft state)
18. Post completion to Slack thread
19. Clean up ephemeral workspace

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

## Bi-Directional Communication

**Overview:** Dogs can read and respond to human feedback posted in Slack threads during task execution.

### Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│    Human     │         │ Orchestrator │         │    Worker    │
│   (Slack)    │         │   Message    │         │     Dog      │
│              │         │   Listener   │         │              │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │ Posts feedback         │                        │
       │ in thread             │                        │
       ├───────────────────────>│                        │
       │                        │                        │
       │                        │ Stores in Redis        │
       │                        │ (thread_messages)      │
       │                        │                        │
       │ 👀 reaction            │                        │
       │<───────────────────────┤                        │
       │                        │                        │
       │                        │                        │ Checkpoint:
       │                        │                        │ Check Redis
       │                        │<───────────────────────┤
       │                        │                        │
       │                        │ Returns new messages   │
       │                        ├───────────────────────>│
       │                        │                        │
       │                        │                        │ Incorporates
       │                        │                        │ feedback into
       │                        │                        │ work
       │                        │                        │
       │ Acknowledgment:        │                        │
       │ "I've received         │<───────────────────────┤
       │  your feedback..."     │                        │
       │<───────────────────────┴────────────────────────┘
```

### Redis Schema

**Thread-to-Task Mapping:**
```
dogwalker:thread_tasks:{thread_ts}
  Type: String
  Value: task_id
  TTL: 24 hours
  Purpose: Message listener looks up which task owns this thread
```

**Task-to-Thread Mapping:**
```
dogwalker:task_threads:{task_id}
  Type: String
  Value: thread_ts
  TTL: 24 hours
  Purpose: Worker looks up which thread to post messages to
```

**Thread Messages:**
```
dogwalker:thread_messages:{thread_ts}
  Type: List
  Values: JSON objects with {user_id, user_name, text, timestamp, message_ts}
  TTL: 24 hours
  Purpose: Store all messages posted by humans in the thread
```

### DogCommunication Helper

**Purpose:** Abstraction layer for bi-directional Slack communication

**Key Methods:**
- `post_message(text, emoji)` - Send updates to Slack thread
- `post_question(question)` - Ask questions and wait for response
- `post_update(message)` - Post status updates
- `get_new_messages()` - Read new messages since last check (non-blocking)
- `wait_for_response(timeout)` - Block and poll for responses (blocking)
- `check_for_feedback()` - Quick check for feedback (non-blocking)
- `format_feedback_for_prompt(feedback)` - Format for AI injection
- `get_all_messages()` - Retrieve all thread messages
- `format_messages_for_pr()` - Format as markdown for PR description

**Message Pointer Tracking:**
```python
self.message_pointer = 0  # Track last read position
new_messages = all_messages[self.message_pointer:]
self.message_pointer = len(all_messages)
```

### Feedback Checkpoints

Workers check for new feedback at **4 key points** during execution:

1. **Before Implementation** - Check for pre-existing feedback posted early
2. **After Implementation** - Incorporate feedback before self-review
3. **After Self-Review** - Incorporate feedback before testing
4. **After Testing** - Final chance to incorporate feedback before pushing

At each checkpoint:
1. Call `communication.check_for_feedback()`
2. If feedback exists:
   - Post acknowledgment: "I've received your feedback..."
   - Format for AI: `communication.format_feedback_for_prompt(feedback)`
   - Re-run Aider with feedback incorporated: `dog.run_task(feedback_prompt)`
3. Continue to next phase

### Use Cases

**Mid-Task Corrections:**
```
User: @dogwalker implement a login form
Dog: [starts working]
User: Make sure to use Tailwind for styling
Dog: I've received your feedback and will incorporate it!
```

**Iterative Refinement:**
```
User: @dogwalker add dark mode
Dog: [implements basic dark mode]
User: Also add system preference detection
Dog: I've received your feedback and will incorporate it during my review!
```

**Critical Clarifications (Future):**
```
Dog: Should I use Redux or Context API for state management?
User: Use Context API
Dog: Thanks! Proceeding with Context API...
```

### Thread Feedback in PR Descriptions

All human messages are collected and included in the final PR description:

```markdown
### 💬 Thread Feedback

The following feedback was provided during implementation:

- **Bryan Owens:** Make sure that the buttons are all Tailwind cursor-pointer
- **Jane Smith:** Also add hover states for better UX
```

**Benefits:**
- Transparency for PR reviewers
- Context for why certain decisions were made
- Audit trail of human involvement

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

### Current (Implemented)
- 1-N dog workers (configurable via DOGS env var)
- Parallel task processing with load balancing
- Single Redis instance for queue + task tracking
- ~10-30 tasks/day capacity (depends on dog count)

### Near-term (Month 2-3)
- Auto-scaling workers based on queue depth
- Dog specialization (frontend/backend)
- Priority queues for urgent tasks
- ~50-100 tasks/day capacity

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

## Implemented Enhancements

### Multi-Dog Coordination ✅
- ✅ Track active tasks per dog in Redis
- ✅ Assign to least busy dog (load balancing)
- ⏳ Dog specialization (frontend, backend, tests, docs) - Future

### Bi-Directional Communication ✅
- ✅ Dogs read human messages posted in Slack threads
- ✅ Multiple feedback checkpoints during task execution
- ✅ Automatic message acknowledgment with 👀 emoji
- ✅ Thread feedback included in PR descriptions
- ✅ Dogs can ask clarifying questions (implementation complete, usage optional)
- ⏳ Dog-initiated questions for critical decisions - Future (framework ready)

## Future Enhancements

### Advanced Human-in-the-Loop
- Proactive question asking by dogs (framework exists, needs usage patterns)
- Multi-turn conversations in threads
- Feedback-driven PR re-opening

### Advanced Features
- Multi-step tasks (split into sub-tasks)
- Code review by separate AI agent
- Automated testing before PR
- Cost optimization (use Haiku for simple tasks)
- Multi-repo orchestration
- Integration tests in isolated environments
