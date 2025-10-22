# Dogwalker - Multi-Agent AI Coding System

## Project Overview
Dogwalker is an autonomous coding system that reads customer feature requests from Slack and automates code generation all the way to PR-ready state. The system uses multiple AI "dogs" (agents) orchestrated by a "Dogwalker" (PM/coordinator) to handle coding tasks in parallel.

**Domain:** dogwalker.dev (purchased)
**Current Status:** Pre-MVP, closed-source
**Timeline:** 3-4 weeks to working MVP
**Decision Point:** Month 3-4 - evaluate open-sourcing vs. staying closed based on traction

## How It Works

Dogwalker automates the entire software development workflow from task description to production-ready pull request:

1. **Request** - You mention `@dogwalker` in Slack with a task description
   - Example: `@dogwalker add rate limiting to the login endpoint`

2. **Planning** - AI generates an implementation plan
   - Creates a date-prefixed branch (`bryans-coregi/2025-10-21-add-rate-limiting`)
   - Generates concise PR title and structured plan
   - Posts draft PR to GitHub with the plan for early human review

3. **Implementation** - AI writes the code using Aider + Claude Sonnet 4.5
   - Explores codebase and identifies relevant files
   - Makes code changes with bite-sized commits (≤500 LOC each)
   - Follows project patterns and coding standards

4. **Quality Assurance** - Three-phase review process
   - **Self-review**: AI critiques its own work and makes improvements
   - **Testing**: Writes comprehensive tests and verifies they pass
   - **Validation**: Ensures all changes work as expected

5. **Delivery** - PR ready for human review
   - Updates PR with complete details (duration, files changed, critical review areas)
   - Marks PR as ready for review in GitHub
   - Posts completion message to Slack thread

**Total time:** 4-10 minutes for simple tasks
**Cost:** ~$0.75-$5.00 per task (API usage)
**Result:** Production-ready PR with tests, ready to merge

All updates post to the Slack thread for visibility, so you can track progress without leaving Slack.

### Task Cancellation

You can cancel in-progress tasks at any time:

- **Cancel Button** - Click the "Cancel Task" button in the initial Slack message
- **Graceful Shutdown** - The dog finishes its current operation (won't leave work half-done)
- **Partial PR** - Draft PR is updated with what was completed vs. what was planned
- **Clear Status** - Cancellation message shows who cancelled and what was done

**Checkpoints:**
- Before planning phase
- Before implementation
- Before self-review
- Before testing

When cancelled, the PR description is updated to show:
- What was completed before cancellation
- What was not completed
- Who cancelled the task and when
- Time worked before cancellation

This gives you control without losing partial progress.

## Architecture

### Components
1. **Dogwalker** (Orchestrator/PM)
   - Receives tasks from Slack
   - Creates branches off main
   - Assigns tasks to available dogs
   - Manages task queue
   - Reports status back to humans

2. **Dogs** (Code Workers)
   - Individual AI agents that write code
   - Each has distinct GitHub identity
   - Work on separate branches
   - Report completion back to Dogwalker

3. **Infrastructure**
   - Task queue: Celery + Redis
   - Code editing: Aider (wraps Claude Sonnet 4.5)
   - Communication: Slack (for human visibility)
   - Version control: GitHub
   - Deployment: Railway (containerized)

### Named Agents
- **Dogwalker Account:** Bryans-Dogwalker (orchestrator)
- **Dog Accounts** (configurable via DOGS env var):
  - Bryans-Coregi (coregi@bryanowens.dev)
  - Bryans-Bitbull (bitbull@bryanowens.dev)
  - Bryans-Poodle (poodle@bryanowens.dev)
  - (Add more dogs as needed for parallel processing)

## Tech Stack

### Core Dependencies
- aider-chat - Code editing engine (wraps Claude API)
- celery - Distributed task queue
- redis - Message broker for Celery
- slack-bolt - Slack integration
- PyGithub - GitHub API client
- python-dotenv - Environment variable management
- anthropic - Claude API (used by Aider)

### Models
- **Dogwalker (orchestration):** Claude Sonnet 4.5 or cheaper (Haiku, GPT-4o-mini)
- **Dogs (code generation):** Claude Sonnet 4.5 (primary), with option to use cheaper models for simple tasks

### Deployment
- **Platform:** Railway
- **Services:**
  - Web process: Slack bot listener
  - Worker process: Celery workers (dogs)
  - Redis: Task queue + state management
- **Estimated Cost:** $20-40/month (infrastructure) + API costs (~$3-10/task)

## Data Flow

```
Human types in Slack: "@dogwalker add rate limiting to /api/login"
        ↓
Slack bot receives message, creates task in Celery queue
        ↓
Posts to Slack thread: "🐕 Coregi is taking this task!"
        ↓
Celery worker (dog) picks up task
        ↓
Worker clones repo, creates feature branch
        ↓
Dog generates implementation plan using Aider
        ↓
Worker pushes empty branch, creates DRAFT PR with plan
        ↓
Posts to Slack: "📋 Coregi created draft PR with plan [link + preview]"
        ↓
Aider (with Sonnet 4.5) explores codebase and edits code
        ↓
Dog runs self-review, makes improvements
        ↓
Dog writes comprehensive tests, verifies they pass
        ↓
Worker commits changes, pushes to branch
        ↓
Worker updates PR description with full details
        ↓
Worker marks PR as "Ready for Review" (exits draft)
        ↓
Posts to Slack thread: "✅ Work complete! PR ready for review [link]"
        ↓
Human reviews and merges (or requests changes)
```

## Project Structure

Monorepo structure with separate apps for orchestrator, worker, and shared utilities:

```
dogwalker/
├── apps/
│   ├── orchestrator/         # Slack bot + Celery task queue
│   │   ├── src/
│   │   │   ├── bot.py            # Main entry point
│   │   │   ├── celery_app.py     # Celery configuration
│   │   │   ├── dog_selector.py   # Dog assignment logic
│   │   │   ├── tasks.py          # Celery task definitions
│   │   │   └── listeners/        # Event listeners (modular)
│   │   │       ├── __init__.py
│   │   │       ├── events/
│   │   │       │   ├── __init__.py
│   │   │       │   └── app_mentioned.py  # @mention handler
│   │   │       └── actions/
│   │   │           ├── __init__.py
│   │   │           └── cancel_task.py     # Cancel button handler
│   │   ├── requirements.txt
│   │   ├── railway.json
│   │   └── README.md
│   │
│   ├── worker/               # Celery worker (Dogs)
│   │   ├── src/
│   │   │   ├── worker_tasks.py  # Task implementation
│   │   │   ├── dog.py           # Aider wrapper
│   │   │   ├── repo_manager.py  # Git operations
│   │   │   ├── cancellation.py  # Cancellation management
│   │   │   └── celery_app.py    # Worker configuration
│   │   ├── requirements.txt
│   │   ├── railway.json
│   │   └── README.md
│   │
│   ├── shared/               # Common utilities
│   │   ├── src/
│   │   │   ├── config.py        # Environment management
│   │   │   ├── github_client.py # GitHub API wrapper
│   │   │   └── slack_utils.py   # Message formatting
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── api/                  # Future HTTP API (placeholder)
│       ├── src/
│       │   └── server.py
│       ├── requirements.txt
│       └── README.md
│
├── docs/
│   ├── ARCHITECTURE.md       # System design & data flow
│   ├── DEPLOYMENT.md         # Railway deployment guide
│   └── AGENTS_APPENDLOG.md   # Audit log of changes
│
├── scripts/
│   ├── setup/
│   │   └── validate_env.py   # Environment validation
│   └── tests/
│       └── test_aider.py     # Aider integration test
│
├── workdir/                  # Temp workspace (gitignored)
├── .env.example              # Environment variable template
├── requirements.txt          # Root dependencies
├── Procfile                  # Railway process definitions
└── README.md                 # This file
```

## Key Implementation Details

### Modular Listener Pattern

The orchestrator uses a modular listener pattern inspired by [Slack's bolt-python-assistant-template](https://github.com/slack-samples/bolt-python-assistant-template):

- **Separation of concerns**: Each event type has its own file
- **Easy extensibility**: Add new listeners without touching core code
- **Clean entry point**: `bot.py` is just initialization and startup
- **Type-safe handlers**: Proper type hints on all functions

Example structure:
```python
# listeners/events/app_mentioned.py
def handle_app_mention(event: dict, say: Say, client: WebClient, logger: Logger):
    # Handle @dogwalker mentions

# listeners/events/__init__.py
def register(app: App):
    app.event("app_mention")(handle_app_mention)
```

This makes it trivial to add new event handlers, action handlers (buttons), or Slack interactions.

### Aider Integration
Aider provides the code editing primitives. It handles:
- Smart file editing (applies diffs correctly)
- Context management (only loads relevant files)
- Git integration (auto-commits)
- Search/grep tools for codebase exploration
- Multi-phase workflow (plan, implement, review, test)

Usage pattern:
```python
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput

model = Model("anthropic/claude-sonnet-4-20250514")
io = InputOutput(yes=True)  # Non-interactive mode

coder = Coder.create(
    main_model=model,
    io=io,
    fnames=None,  # Auto-detect relevant files
    auto_commits=True,
    map_tokens=1024  # Repo map for context
)

# Phase 1: Generate plan
coder.run("Create implementation plan for: add rate limiting")

# Phase 2: Implement
coder.run("Add rate limiting to /api/login endpoint")

# Phase 3: Self-review
coder.run("Review changes for code quality, edge cases, and security")

# Phase 4: Test
coder.run("Write comprehensive tests and verify they pass")
```

### Context Management
Dogs don't read entire codebase. Instead:
1. Use Aider's built-in repo map (compressed view of structure)
2. Search for relevant files with grep/ripgrep
3. Read files iteratively as dependencies are discovered
4. Keep token usage manageable (5k-15k input tokens per task typical)

### Task Queue (Celery)
```python
@app.task(bind=True, max_retries=3)
def run_coding_task(self, task_id, task_description, branch_name, dog_name, dog_display_name):
    # 1. Clone repo and checkout branch
    # 2. Generate implementation plan
    # 3. Push empty branch
    # 4. Create draft PR with plan
    # 5. Post draft PR to Slack (with plan preview)
    # 6. Run Aider to implement changes
    # 7. Run self-review and improvements
    # 8. Write comprehensive tests and verify they pass
    # 9. Push final changes
    # 10. Update PR with complete details
    # 11. Mark PR as ready for review
    # 12. Post completion to Slack
```

### Dog Selection
**Current Implementation:** Least-busy load balancing
- Tracks active tasks per dog in Redis
- Assigns tasks to dog with fewest active tasks
- Enables parallel processing with multiple dogs
- Falls back to round-robin if Redis unavailable

### Error Handling
- Retry transient errors (git push failures)
- Don't retry code errors (need human intervention)
- Post all errors to Slack thread for visibility
- Max 3 retries with exponential backoff

## Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Configuration
GITHUB_REPO=username/reponame
REDIS_URL=redis://localhost:6379

# Dog Configuration (Multiple Dogs - JSON array)
# Each dog needs a unique GitHub account and personal access token
DOGS='[
  {"name": "Bryans-Coregi", "email": "coregi@bryanowens.dev", "github_token": "github_pat_11AAA..."},
  {"name": "Bryans-Bitbull", "email": "bitbull@bryanowens.dev", "github_token": "github_pat_11BBB..."},
  {"name": "Bryans-Poodle", "email": "poodle@bryanowens.dev", "github_token": "github_pat_11CCC..."}
]'

# Optional: Separate GitHub token for orchestrator (read-only)
# If not provided, uses first dog's token as fallback
# GITHUB_TOKEN=github_pat_...

# Legacy: Single Dog (deprecated - use DOGS instead)
# DOG_NAME=Bryans-Coregi
# DOG_EMAIL=coregi@bryanowens.dev
# DOG_GITHUB_TOKEN=github_pat_...
```

## MVP Scope (Weeks 1-3)

### Week 1: Core Infrastructure
- Local Celery + Redis setup
- Aider integration and testing
- Basic task: clone repo → run Aider → push branch

### Week 2: Integrations
- GitHub PR creation via API
- Slack bot (receive commands, post updates)
- Connect Slack → Celery queue

### Week 3: Deployment
- Railway setup (worker + bot + Redis)
- End-to-end test: Slack → code → PR
- Error handling and logging

### Week 4: Polish
- Documentation
- First external beta tester
- Cost tracking per task

## Features Implemented
- ✅ **Multiple dogs** - Configure 1-N dogs via DOGS env var
- ✅ **Load balancing** - Least-busy algorithm distributes tasks evenly
- ✅ **Parallel processing** - Multiple dogs work simultaneously
- ✅ **Task cancellation** - Cancel in-progress tasks with Slack button, graceful shutdown with partial PR

## Features to Skip Initially
- AI code review (human review only)
- Model routing (use Sonnet 4.5 for everything)
- Multi-repo support (single repo only)
- Dog specialization (frontend/backend/tests)

## Longer-Term Vision

As the system matures, enable bi-directional collaboration between AI agents and humans:

**Human-in-the-Loop Product Decisions:**
- Dogwalker or dogs can ask clarifying questions in Slack threads when requirements are ambiguous
- Example: "Should the rate limit be per-user or per-IP? React with 👤 for per-user or 🌐 for per-IP"
- Example: "I found two ways to implement this - A) faster but less maintainable, B) cleaner but more files. Which do you prefer?"
- Agents pause work and wait for human input before proceeding
- This transforms the system from "autonomous executor" to "intelligent collaborator"

**Benefits:**
- Reduces failed PRs from misunderstood requirements
- Allows dogs to handle more complex/ambiguous tasks
- Keeps humans in control without requiring them to specify every detail upfront
- Creates a conversational development workflow

**Implementation:**
- Dogs detect uncertainty (via prompt engineering or confidence scores)
- Post question to Slack thread with reaction options or text reply
- Celery task pauses (with timeout)
- Human responds via Slack
- Dog resumes with clarified context

This evolution positions Dogwalker as a collaborative coding partner rather than a simple automation tool.

## Metrics to Track

From day 1:
- API costs per task
- Task success rate (% that result in PRs)
- Time per task (minutes from Slack → PR)
- PR merge rate (% of AI PRs that get merged)
- Weekly active users
- Revenue (once charging)

## Decision Points

### Month 3-4: Open-Source vs. Closed
Evaluate based on:
- Revenue: $0-500/mo → open-source; $500-5k/mo → stay closed; $5k+ → go big
- Active users: <10 → open-source; 10-50 → iterate; 50+ → real business
- Your interest level: waning → open-source as portfolio; high → double down

### Pricing (When Ready)
- Free tier: 10 tasks/month (for evaluation)
- Starter: $49/month, 100 tasks
- Team: $149/month, 500 tasks
- Enterprise: Custom pricing

## Competitive Landscape

Existing solutions:
- Sweep AI: $480/month, GitHub issues → PRs (acquired by Roblox)
- Devin: $500/month (estimated), full AI engineer (waitlist only)
- Factory AI: Enterprise pricing, multi-agent coding
- GitHub Copilot Workspace: $10-19/month (limited preview)

**Differentiation:**
- Slack integration for non-technical visibility
- Multiple specialized agents (vs. single bot)
- Cheaper (mix of model tiers)
- Self-hostable (future option)

## Technical Constraints

- No localStorage/sessionStorage in artifacts (not supported in Claude.ai)
- Each task = fresh container (ephemeral, clone repo each time)
- Railway free tier limits (budget $20-50/month for realistic usage)
- GitHub API rate limits (5000 requests/hour per account)
- Context window limits (manage with Aider's lazy loading)

## Development Philosophy

- **Ship fast, iterate:** 3 weeks to MVP, not 3 months
- **Closed source initially:** Preserve optionality to open-source later
- **Real validation:** Revenue > GitHub stars for proving demand
- **Manual first, automate second:** Test flows manually before automating
- **Single dog before multi-dog:** Prove one works before scaling

## Next Immediate Actions

1. Set up local Python environment
2. Test Aider on a sample repo
3. Implement basic Celery task
4. Create GitHub bot account
5. Set up Slack app
6. Deploy to Railway
7. End-to-end test
8. Invite first beta user

## References

- Aider: https://github.com/paul-gauthier/aider
- Celery: https://docs.celeryq.dev/
- Slack Bolt: https://slack.dev/bolt-python/
- PyGithub: https://pygithub.readthedocs.io/
- Railway: https://railway.app/

## Project Goal

Build autonomous coding system that handles Slack → code → PR flow reliably enough to charge $49-149/month within 3 months.
