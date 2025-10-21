# Dogwalker - Multi-Agent AI Coding System

## Project Overview
Dogwalker is an autonomous coding system that reads customer feature requests from Slack and automates code generation all the way to PR-ready state. The system uses multiple AI "dogs" (agents) orchestrated by a "Dogwalker" (PM/coordinator) to handle coding tasks in parallel.

**Domain:** dogwalker.dev (purchased)  
**Current Status:** Pre-MVP, closed-source  
**Timeline:** 3-4 weeks to working MVP  
**Decision Point:** Month 3-4 - evaluate open-sourcing vs. staying closed based on traction

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
- **Dog Accounts:** 
  - Bryans-Coregi (coregi@bryanowens.dev)
  - Bryans-Bitbull (bitbull@bryanowens.dev)
  - (More dogs can be added later)

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
Posts to Slack thread: "🐕 Corgi is taking this task!"
        ↓
Celery worker (dog) picks up task
        ↓
Worker clones repo, creates feature branch
        ↓
Aider (with Sonnet 4.5) explores codebase and edits code
        ↓
Worker commits changes, pushes branch
        ↓
Worker creates PR via GitHub API
        ↓
Posts to Slack thread: "✅ PR ready: [link]"
        ↓
Human reviews and merges (or requests changes)
```

## Project Structure

```
dogwalker/
├── .env.example          # Template for environment variables
├── requirements.txt      # Python dependencies
├── tasks.py             # Celery task definitions (dog work)
├── slack_bot.py         # Slack listener (Dogwalker interface)
├── github_utils.py      # GitHub API helpers (PR creation, etc.)
├── config.py            # Configuration management
├── worker.py            # Celery worker entry point
├── Procfile             # Railway process definitions
├── railway.toml         # Railway configuration
└── README.md            # Setup and usage instructions
```

## Key Implementation Details

### Aider Integration
Aider provides the code editing primitives. It handles:
- Smart file editing (applies diffs correctly)
- Context management (only loads relevant files)
- Git integration (auto-commits)
- Search/grep tools for codebase exploration

Usage pattern:
```python
from aider.coders import Coder
from aider.models import Model

model = Model("claude-sonnet-4.5-20250929")
coder = Coder.create(
    model=model,
    fnames=None,  # Auto-detect relevant files
    auto_commits=True,
    map_tokens=1024  # Repo map for context
)

coder.run("Add rate limiting to /api/login endpoint")
# Aider explores codebase, edits files, commits
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
def run_coding_task(self, task_id, task_description, branch_name, dog_name):
    # 1. Clone repo and checkout branch
    # 2. Run Aider
    # 3. Push branch
    # 4. Create PR
    # 5. Update Slack
```

### Dog Selection
Simple approach (MVP): Round-robin or random selection  
Better approach: Track active tasks per dog, assign to least busy

### Error Handling
- Retry transient errors (git push failures)
- Don't retry code errors (need human intervention)
- Post all errors to Slack thread for visibility
- Max 3 retries with exponential backoff

## Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...           # For Bryans-Dogwalker account
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Configuration
GITHUB_REPO=username/reponame
SLACK_CHANNEL_ID=C123456
REDIS_URL=redis://localhost:6379

# Dog Identity (per worker)
DOG_NAME=Bryans-Coregi
DOG_EMAIL=coregi@bryanowens.dev
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

## Features to Skip Initially
- Multiple dogs (start with one)
- AI code review (human review only)
- Model routing (use Sonnet 4.5 for everything)
- Multi-repo support (single repo only)
- Advanced dog selection algorithms

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
