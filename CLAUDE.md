# Claude Code Instructions

## Core Principles

### Never Hallucinate
- **Always verify before acting** - Don't assume files, functions, or APIs exist
- **Read first, then write** - Use Read tool to check existing code structure
- **Search when uncertain** - Use Grep/Glob to find patterns before assuming
- **Validate assumptions** - If you think something exists, verify it

### Test After Every Change
- Run the application after each modification
- Verify the specific functionality works as expected
- Check for unintended side effects or regressions
- Don't batch changes - test incrementally

### Build Before Committing
- Run `npm run build` (or equivalent) before any commit
- Fix all TypeScript errors - no bypassing with `any`
- Resolve all linter warnings
- Ensure production build succeeds

### Document Every Decision
- Log architectural choices in documentation
- Include rationale and trade-offs
- Track time spent on each feature/task
- Update README.md with significant changes

## Development Guidelines

### Code Quality Standards
- **Always test after every change** - Run the application and verify functionality works
- **Build before committing** - Ensure build passes without errors
- **Fix all TypeScript errors** - No ignoring type errors or using `any` without justification
- **Never hallucinate** - Don't assume files, functions, or APIs exist. Read and verify first
- **Read before writing** - Always use Read tool to check existing code before making changes

### JavaScript/TypeScript Style
- Use **TypeScript** for all new code with proper type definitions
- Use **arrow functions** for all function expressions: `const foo = () => {}`
- Use **modern ES6+ syntax**:
  - Destructuring: `const { foo, bar } = obj`
  - Template literals: `` `Hello ${name}` ``
  - Spread operator: `{ ...obj, newProp: value }`
  - Optional chaining: `obj?.property?.nested`
  - Nullish coalescing: `value ?? defaultValue`
- Prefer `const` over `let`, never use `var`
- Use async/await instead of promise chains
- Prefer functional array methods: `map`, `filter`, `reduce`

### Code Style Examples

```typescript
// ✅ GOOD - Arrow functions, const, modern syntax
const calculateTotal = (items: Item[]): number => {
  return items.reduce((sum, item) => sum + item.price, 0);
};

const processUser = async (userId: string) => {
  const user = await fetchUser(userId);
  return {
    ...user,
    fullName: `${user.firstName} ${user.lastName}`,
    isActive: user.status === 'active',
  };
};

// ❌ BAD - function keyword, var, old syntax
function calculateTotal(items) {
  var sum = 0;
  for (var i = 0; i < items.length; i++) {
    sum = sum + items[i].price;
  }
  return sum;
}
```

### React Best Practices
- Use **functional components** with hooks only
- Follow React Server Components patterns where possible
- Use `"use client"` directive only when necessary (client-side interactivity required)
- Properly handle loading and error states
- Clean up effects with return functions
- Use proper dependency arrays for hooks

### React Component Examples

```typescript
// ✅ GOOD - Functional component, TypeScript, arrow function
interface UserCardProps {
  name: string;
  email: string;
  onEdit?: () => void;
}

const UserCard = ({ name, email, onEdit }: UserCardProps) => {
  return (
    <div className="card">
      <h3>{name}</h3>
      <p>{email}</p>
      {onEdit && <button onClick={onEdit}>Edit</button>}
    </div>
  );
};

// ❌ BAD - Class component, no types, old patterns
class UserCard extends React.Component {
  render() {
    return (
      <div className="card">
        <h3>{this.props.name}</h3>
      </div>
    );
  }
}
```

### Component Development
- Place reusable UI components in appropriate directories
- Define TypeScript interfaces for all props
- Use descriptive, semantic names
- Keep components focused and single-purpose
- Follow accessibility best practices (ARIA labels, semantic HTML)

### Code Organization
- One component per file (except small, tightly-coupled helpers)
- Import order: React, external libraries, internal modules, types, styles
- Export components as default or named exports consistently
- Keep utility functions in separate modules

### Testing Workflow
1. Make a change
2. **Test immediately** in the browser/application
3. Verify the specific functionality works
4. Check for unintended side effects
5. Run build to catch type errors
6. Only proceed to next change after current one works

### Error Handling
- Handle errors gracefully with try/catch
- Provide meaningful error messages
- Log errors appropriately for debugging
- Don't silently swallow errors

### Performance Considerations
- Lazy load components when appropriate
- Memoize expensive computations
- Avoid unnecessary re-renders
- Optimize images and assets
- Monitor bundle size

### Git Workflow
- Make small, focused commits
- Write clear, descriptive commit messages
- Don't commit untested code
- Keep commits atomic and reversible

## Common Pitfalls to Avoid

### Don't Hallucinate
- ❌ Assuming a function exists without reading the file
- ❌ Guessing API endpoints or response structures
- ❌ Inventing configuration options
- ✅ Always verify by reading, grepping, or searching

### Don't Skip Testing
- ❌ Making multiple changes before testing any
- ❌ Assuming code works without running it
- ❌ Ignoring console errors "to fix later"
- ✅ Test each change immediately after making it

### Don't Ignore Build Errors
- ❌ Committing code with TypeScript errors
- ❌ Using `@ts-ignore` without proper justification
- ❌ Leaving broken builds for someone else
- ✅ Run build and fix all errors before committing

### Don't Use Old Syntax
- ❌ Using `var` or `function` declarations
- ❌ Using `.then()` chains instead of async/await
- ❌ Ignoring destructuring opportunities
- ✅ Use modern ES6+ syntax consistently

### General Anti-Patterns
- ❌ Don't assume code exists - always verify by reading files
- ❌ Don't skip testing after changes
- ❌ Don't ignore TypeScript errors
- ❌ Don't use outdated JavaScript syntax (var, function declarations, etc.)
- ❌ Don't make large, multi-purpose commits
- ❌ Don't commit broken builds
- ❌ Don't duplicate code - create reusable utilities instead

## Development Patterns

### Before Starting Any Task
1. **Read** CLAUDE.md for project-specific guidelines
2. **Read** README.md to understand project structure
3. **Verify** current state with `git status`
4. **Search** for existing patterns before creating new ones (use Grep/Glob)
5. **Check file structure** to understand what exists

### Feature Implementation
1. **Understand requirements** - ask clarifying questions if needed
2. **Review existing code** - find similar features to follow patterns
3. **Plan implementation** - use TodoWrite for multi-step tasks
4. **Implement incrementally** - one small change at a time
5. **Test after each step** - verify it works before proceeding
6. **Build to verify** - ensure no TypeScript errors
7. **Update documentation** - reflect new functionality

### Bug Fixes
1. **Reproduce the issue** - verify you can see the problem
2. **Identify root cause** - don't fix symptoms, fix the actual bug
3. **Read relevant code** - understand the context fully
4. **Implement fix** - make minimal, focused change
5. **Test thoroughly** - verify fix works and doesn't break anything
6. **Check for similar issues** - search for same pattern elsewhere
7. **Add preventive measures** - types, validation, etc.

### Refactoring
1. **Understand current behavior** - test before changing
2. **Plan refactoring** - know what you're improving and why
3. **Make incremental changes** - small steps with testing between
4. **Preserve functionality** - behavior shouldn't change
5. **Verify with tests** - ensure nothing broke
6. **Update types** - keep TypeScript definitions accurate

## Agent Responsibilities

### Code Development Agent
**Purpose:** Implement features, fix bugs, and refactor code

**Mandatory Workflow:**
1. **Read relevant files** to understand context - never assume structure
2. **Create todo list** for multi-step tasks (use TodoWrite)
3. **Implement ONE change at a time**
4. **Test immediately** - run application and verify it works
5. **Run build** to catch TypeScript/compilation errors
6. **Mark todo complete** only after testing confirms success
7. **Update documentation** if behavior or APIs changed

**Testing Requirements:**
- Test in development mode after each change
- Verify functionality in browser/application
- Check console for errors or warnings
- Run build command
- Only proceed after current change works

### Code Review Agent
**Purpose:** Review code quality, performance, and best practices

**Review Checklist:**
- ✅ TypeScript types properly defined (no `any` without justification)
- ✅ Arrow functions used: `const foo = () => {}`
- ✅ Modern ES6+ syntax (destructuring, spread, optional chaining)
- ✅ No `var` declarations - use `const` or `let`
- ✅ Async/await instead of promise chains
- ✅ No unused dependencies or imports
- ✅ Accessibility considerations (ARIA labels, semantic HTML)
- ✅ Performance optimizations (lazy loading, memoization where appropriate)
- ✅ Error handling is present and meaningful
- ✅ No hallucinated code - all references are verified

### Documentation Agent
**Purpose:** Maintain project documentation

**Tasks:**
- Update CLAUDE.md with new patterns or guidelines
- Document new components, utilities, and APIs
- Keep README.md current with setup and usage
- Track time spent on features
- Ensure documentation reflects actual code (no hallucination)

## Framework/Library Selection

When choosing any framework, library, or tool:
1. **Research options** - Consider 2-3 viable alternatives
2. **Evaluate criteria**:
   - Familiarity (can you implement quickly?)
   - Features (does it support requirements?)
   - TypeScript support (required for JS/TS projects)
   - Community/docs (can you get help?)
   - Free tier availability (for APIs)
3. **Make decision** with clear rationale
4. **Document decision** in appropriate files
5. **Update README.md** with tech stack choices

## Tech Stack Best Practices

This project uses a Python-based stack with AI agents, task queues, and integrations. Follow these patterns:

### Python Code Style

**General Guidelines:**
- Use **type hints** for all function signatures
- Follow **PEP 8** style guidelines
- Use **descriptive variable names** (no single-letter vars except loop counters)
- Prefer **list comprehensions** over map/filter for readability
- Use **f-strings** for string formatting (not `%` or `.format()`)
- Use **pathlib** for file paths instead of os.path
- Write **docstrings** for all public functions and classes

**Code Examples:**
```python
# ✅ GOOD - Type hints, f-strings, modern Python
from typing import Optional, List
from pathlib import Path

def process_task(task_id: str, repo_path: Path, timeout: int = 300) -> dict:
    """
    Process a coding task with Aider.

    Args:
        task_id: Unique task identifier
        repo_path: Path to repository
        timeout: Max execution time in seconds

    Returns:
        Dictionary with task results and metadata
    """
    result = {
        "task_id": task_id,
        "status": "processing",
        "files_modified": [],
    }

    # Process task...
    return result

# ❌ BAD - No types, old formatting, unclear names
def process(t, r, to=300):
    res = {}
    res['id'] = t
    res['s'] = 'processing'
    return res
```

### Aider Integration Best Practices

**Usage Patterns:**
```python
from aider.coders import Coder
from aider.models import Model

# ✅ GOOD - Proper configuration and error handling
def run_aider_task(task_description: str, repo_path: Path) -> bool:
    """Run Aider on a coding task."""
    try:
        model = Model("claude-sonnet-4.5-20250929")
        coder = Coder.create(
            model=model,
            fnames=None,  # Auto-detect relevant files
            auto_commits=True,
            map_tokens=1024,  # Repo map for context
            edit_format="diff",  # Use diff format for changes
        )

        # Run the task
        result = coder.run(task_description)

        # Verify changes were made
        if not result:
            raise ValueError("Aider did not produce changes")

        return True

    except Exception as e:
        logger.error(f"Aider task failed: {e}")
        raise
```

**Key Principles:**
- Let Aider auto-detect files - don't manually specify unless needed
- Use `auto_commits=True` for automatic git commits
- Set appropriate `map_tokens` for repo context (1024-2048 typical)
- Always wrap in try/except - Aider can fail for many reasons
- Verify Aider actually made changes before considering task complete
- Use appropriate model based on task complexity (Sonnet 4.5 for complex, Haiku for simple)

### Celery Task Queue Best Practices

**Task Definition:**
```python
from celery import Task
from typing import Any

# ✅ GOOD - Proper task configuration
@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True
)
def run_coding_task(
    self: Task,
    task_id: str,
    task_description: str,
    branch_name: str,
    dog_name: str
) -> dict[str, Any]:
    """
    Execute a coding task with a dog agent.

    This is a Celery task that clones the repo, runs Aider,
    and creates a PR.
    """
    try:
        # 1. Clone repo and checkout branch
        # 2. Run Aider
        # 3. Push branch
        # 4. Create PR
        # 5. Update Slack

        return {"status": "success", "task_id": task_id}

    except Exception as exc:
        # Log error to Slack
        logger.exception(f"Task {task_id} failed")

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

**Key Principles:**
- Use `bind=True` to access task context (for retries)
- Set `max_retries` (3 is good default)
- Use `acks_late=True` to prevent message loss
- Set `reject_on_worker_lost=True` for reliability
- Always include comprehensive error handling
- Log errors before retrying
- Don't retry code errors (only transient infrastructure errors)
- Use exponential backoff: `countdown=2 ** self.request.retries`

### Redis Best Practices

**Connection Management:**
```python
import redis
from typing import Optional

# ✅ GOOD - Connection pooling and error handling
class RedisClient:
    def __init__(self, url: str):
        self.pool = redis.ConnectionPool.from_url(
            url,
            max_connections=10,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

    def get_client(self) -> redis.Redis:
        """Get Redis client from pool."""
        return redis.Redis(connection_pool=self.pool)

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task status from Redis."""
        client = self.get_client()
        try:
            data = client.get(f"task:{task_id}")
            return json.loads(data) if data else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis error: {e}")
            return None
```

**Key Principles:**
- Use connection pooling (don't create connections per request)
- Set reasonable timeouts (5 seconds is good default)
- Always handle `redis.RedisError` exceptions
- Use key prefixes for namespacing (`task:`, `dog:`, etc.)
- Set TTL on temporary data to prevent memory bloat
- Don't store large objects - use references instead

### Slack Bot Best Practices

**Event Handling:**
```python
from slack_bolt import App
from slack_sdk.errors import SlackApiError

app = App(token=os.environ["SLACK_BOT_TOKEN"])

# ✅ GOOD - Proper event handling and error recovery
@app.event("app_mention")
def handle_mention(event: dict, say, logger):
    """Handle @dogwalker mentions."""
    try:
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("ts")  # Use for threading

        # Acknowledge immediately
        say(
            text="🐕 I'm on it!",
            thread_ts=thread_ts,  # Reply in thread
        )

        # Queue task asynchronously
        task_description = text.replace("<@BOTID>", "").strip()
        result = run_coding_task.delay(
            task_id=f"{channel_id}_{thread_ts}",
            task_description=task_description,
            branch_name=f"dogwalker/{thread_ts}",
            dog_name="Bryans-Coregi",
        )

        # Store task ID for later updates
        store_task_mapping(thread_ts, result.id)

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        # Don't crash - Slack will retry if needed
    except Exception as e:
        logger.exception("Unexpected error in mention handler")
```

**Key Principles:**
- Always acknowledge Slack events quickly (3 seconds timeout)
- Use `thread_ts` to keep conversations organized
- Queue long-running tasks asynchronously (don't block event handler)
- Handle `SlackApiError` separately from other exceptions
- Don't let exceptions crash the bot - log and continue
- Use emoji for visual feedback (🐕 ✅ ❌ 🔄)
- Store thread_ts to task_id mappings for status updates
- Test with error injection (simulate API failures)

### GitHub API Best Practices

**Using PyGithub:**
```python
from github import Github, GithubException
from typing import Optional

# ✅ GOOD - Proper error handling and resource management
def create_pull_request(
    token: str,
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main"
) -> Optional[str]:
    """
    Create a GitHub pull request.

    Returns PR URL on success, None on failure.
    """
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)

        # Verify branch exists
        try:
            repo.get_branch(branch_name)
        except GithubException:
            logger.error(f"Branch {branch_name} not found")
            return None

        # Create PR
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )

        logger.info(f"Created PR: {pr.html_url}")
        return pr.html_url

    except GithubException as e:
        logger.error(f"GitHub API error: {e.status} - {e.data}")
        return None
    except Exception as e:
        logger.exception("Unexpected error creating PR")
        return None
```

**Key Principles:**
- Handle `GithubException` for API errors (rate limits, auth, etc.)
- Check `e.status` and `e.data` for debugging
- Verify resources exist before operating on them
- Mind rate limits (5000 requests/hour per token)
- Use different GitHub accounts for different dogs
- Set meaningful commit messages and PR descriptions
- Include co-author attribution for AI commits
- Don't force push unless explicitly needed
- Always verify branch exists before creating PR

### Claude API Best Practices

**Direct API Usage (when not using Aider):**
```python
from anthropic import Anthropic
import os

# ✅ GOOD - Proper streaming and error handling
def generate_with_claude(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 4000
) -> str:
    """Generate text with Claude API."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        response = client.messages.create(
            model="claude-sonnet-4.5-20250929",
            max_tokens=max_tokens,
            system=system_prompt or "You are a helpful coding assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise
```

**Key Principles:**
- Use environment variables for API keys (never hardcode)
- Choose appropriate model: Sonnet 4.5 for complex, Haiku for simple
- Set reasonable `max_tokens` (4000 is good for most tasks)
- Include system prompts to guide behavior
- Handle API errors gracefully (rate limits, timeouts)
- Track API costs per task
- Consider streaming for long responses
- Use Aider for code editing (it handles context better)

### Environment Variable Management

**Using python-dotenv:**
```python
from dotenv import load_dotenv
import os
from pathlib import Path

# ✅ GOOD - Explicit loading and validation
def load_config() -> dict:
    """Load and validate environment configuration."""
    # Load from .env file
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    # Validate required variables
    required_vars = [
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "REDIS_URL",
        "GITHUB_REPO",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required env vars: {missing}")

    return {
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY"),
        "github_token": os.getenv("GITHUB_TOKEN"),
        "slack_bot_token": os.getenv("SLACK_BOT_TOKEN"),
        "slack_app_token": os.getenv("SLACK_APP_TOKEN"),
        "redis_url": os.getenv("REDIS_URL"),
        "github_repo": os.getenv("GITHUB_REPO"),
        "dog_name": os.getenv("DOG_NAME", "Bryans-Coregi"),
        "dog_email": os.getenv("DOG_EMAIL", "coregi@bryanowens.dev"),
    }
```

**Key Principles:**
- Always use `.env` files (never commit secrets to git)
- Validate all required variables at startup
- Provide sensible defaults for optional variables
- Use `.env.example` as template (commit this)
- Document all environment variables in README
- Never log or print sensitive values
- Use different `.env` files for different environments

### Error Handling and Logging

**Proper Error Handling:**
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ✅ GOOD - Comprehensive error handling
def execute_dog_task(task_id: str) -> Optional[str]:
    """Execute a dog coding task."""
    try:
        logger.info(f"Starting task {task_id}")

        # Clone repo
        repo_path = clone_repository()
        logger.debug(f"Cloned to {repo_path}")

        # Run Aider
        success = run_aider_task(task_description, repo_path)
        if not success:
            raise ValueError("Aider failed to complete task")

        # Push changes
        push_result = push_branch()
        logger.info(f"Pushed branch: {push_result}")

        # Create PR
        pr_url = create_pull_request()
        logger.info(f"Created PR: {pr_url}")

        return pr_url

    except ValueError as e:
        # Business logic errors - don't retry
        logger.error(f"Task validation error: {e}")
        return None

    except (IOError, OSError) as e:
        # File/network errors - could retry
        logger.error(f"IO error: {e}", exc_info=True)
        raise  # Let Celery retry

    except Exception as e:
        # Unexpected errors - log full traceback
        logger.exception(f"Unexpected error in task {task_id}")
        raise
```

**Key Principles:**
- Use different log levels appropriately (DEBUG, INFO, ERROR)
- Include context in log messages (task IDs, file paths, etc.)
- Use `exc_info=True` or `logger.exception()` for tracebacks
- Distinguish retriable errors from permanent failures
- Don't log sensitive data (API keys, tokens, user data)
- Configure logging format with timestamps and levels
- Consider structured logging (JSON) for production

## Verification Checklist

Before marking any task as complete:
- [ ] Code verified by reading actual files (not assumed)
- [ ] Change tested in running application
- [ ] Functionality confirmed to work as expected
- [ ] Build passes successfully
- [ ] No TypeScript errors or warnings
- [ ] No console errors when testing
- [ ] Code follows style guidelines (arrow functions, modern syntax)
- [ ] Types properly defined
- [ ] Error cases handled
- [ ] Documentation updated if needed
- [ ] No unused imports or variables
- [ ] Todo list updated to reflect completion

## Best Practices Summary

### Always Do
- ✅ Verify code exists before modifying (Read tool)
- ✅ Test after every single change
- ✅ Run build before committing
- ✅ Use TypeScript with proper types
- ✅ Use arrow functions and modern ES6+ syntax
- ✅ Handle errors gracefully
- ✅ Write clear, focused commits
- ✅ Document architectural decisions
- ✅ Ask questions when requirements are unclear

### Never Do
- ❌ Assume files or functions exist
- ❌ Skip testing after changes
- ❌ Ignore build or TypeScript errors
- ❌ Use `var` or old function syntax
- ❌ Commit broken or untested code
- ❌ Duplicate code instead of creating utilities
- ❌ Make large, unfocused commits
- ❌ Use `any` type without justification
