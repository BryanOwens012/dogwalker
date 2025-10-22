"""Dog worker - AI coding agent using Aider."""

import logging
from pathlib import Path
from typing import Optional
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
import os

logger = logging.getLogger(__name__)


class Dog:
    """AI coding agent that uses Aider to make code changes."""

    # Model pricing (per million tokens) as of January 2025
    MODEL_PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    }

    def __init__(
        self,
        repo_path: Path,
        model_name: str = "anthropic/claude-sonnet-4-20250514",  # Aider requires provider prefix
        map_tokens: int = 1024
    ):
        """
        Initialize Dog with Aider.

        Args:
            repo_path: Path to git repository
            model_name: Claude model to use (default: Sonnet 4.5)
            map_tokens: Tokens for repo map context (default: 1024)
        """
        self.repo_path = repo_path
        self.model_name = model_name
        self.map_tokens = map_tokens
        self.coder: Optional[Coder] = None

        # Cost tracking
        self.total_cost = 0.0
        self.cost_breakdown = {
            "pr_title": 0.0,
            "plan_generation": 0.0,
            "draft_pr_description": 0.0,
            "implementation": 0.0,
            "self_review": 0.0,
            "testing": 0.0,
            "critical_review": 0.0,
            "final_pr_description": 0.0,
        }

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model_name: str) -> float:
        """
        Calculate API cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_name: Model name (without provider prefix)

        Returns:
            Cost in dollars
        """
        pricing = self.MODEL_PRICING.get(model_name)
        if not pricing:
            logger.warning(f"No pricing data for model {model_name}, using Sonnet 4.5 pricing")
            pricing = self.MODEL_PRICING["claude-sonnet-4-20250514"]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        logger.debug(
            f"Cost calculation: {input_tokens} input + {output_tokens} output tokens = ${total_cost:.4f}"
        )

        return total_cost

    def call_claude_api(self, prompt: str, max_tokens: int = 1000, category: str = "other") -> str:
        """
        Call Claude API directly for text generation (not code editing).

        Automatically tracks API costs.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response
            category: Cost category for tracking (e.g., "pr_title", "plan_generation")

        Returns:
            Claude's response as a string
        """
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        client = Anthropic(api_key=api_key)

        # Extract model name without provider prefix (Anthropic SDK doesn't need "anthropic/" prefix)
        model_name = self.model_name.replace("anthropic/", "")

        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Track cost
        cost = self._calculate_cost(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model_name=model_name
        )

        self.total_cost += cost
        if category in self.cost_breakdown:
            self.cost_breakdown[category] += cost
        else:
            # For unknown categories, create a new entry
            self.cost_breakdown[category] = cost

        logger.info(f"API call ({category}): ${cost:.4f} - Total cost: ${self.total_cost:.4f}")

        return response.content[0].text

    def generate_pr_title(self, task_description: str, max_length: int = 57) -> str:
        """
        Generate a concise PR title for the task using Claude API directly.

        Args:
            task_description: Natural language description of code changes
            max_length: Maximum length for the title (default: 57 to leave room for "[Dogwalker] " prefix)

        Returns:
            Concise PR title as a string
        """
        logger.info(f"Generating PR title for: {task_description}")

        title_prompt = f"""Given this task: "{task_description}"

Create a concise, descriptive pull request title that summarizes this change.

Requirements:
- Maximum {max_length} characters
- Use imperative mood (e.g., "Add feature" not "Adds feature" or "Added feature")
- Be specific about what changed
- No punctuation at the end
- Use title case for first word only

Examples:
- "Add rate limiting to login endpoint"
- "Fix authentication token expiration"
- "Refactor user service for better testability"
- "Update Node.js dependencies to latest versions"

Provide ONLY the title text in your response. No explanation, no quotes, no additional text."""

        try:
            title = self.call_claude_api(title_prompt, max_tokens=100, category="pr_title")
            # Clean up the response
            title = title.strip().strip('"').strip("'")
            # Truncate if still too long
            if len(title) > max_length:
                title = title[:max_length].rsplit(' ', 1)[0]
            return title

        except Exception as e:
            logger.exception(f"PR title generation failed: {e}")
            # Fallback: use first part of task description
            return task_description[:max_length].rsplit(' ', 1)[0]

    def generate_plan(self, task_description: str) -> str:
        """
        Generate an implementation plan for the task using Claude API directly.

        Args:
            task_description: Natural language description of code changes

        Returns:
            Implementation plan as a string
        """
        logger.info(f"Generating implementation plan for: {task_description}")

        plan_prompt = f"""Create an implementation plan for this task: "{task_description}"

Format your response as a clean, structured markdown plan with these sections:

**Architecture**
- List components/services/modules that will be affected

**Files to Modify/Create**
- List specific files

**Implementation Approach**
- High-level steps to solve the problem
- Any breaking changes or migrations needed

**Commit Strategy**
- Break into commits of ≤500 LOC each
- List commits in order

CRITICAL RULES:
- Provide ONLY the structured plan above
- NO conversational text (no "Perfect!", "Let's start", etc.)
- NO code snippets or file contents
- NO commands (no mkdir, npm install, etc.)
- Just clean markdown bullets describing WHAT will be done, not HOW

Keep the entire plan under 250 words."""

        try:
            plan = self.call_claude_api(plan_prompt, max_tokens=800, category="plan_generation")
            logger.info("Implementation plan generated")
            return plan.strip()

        except Exception as e:
            logger.exception(f"Plan generation failed: {e}")
            # Return a basic plan on failure
            return f"""**Implementation Approach**
- Implement: {task_description}
- Follow project patterns and conventions
- Add error handling and validation"""

    def run_task(self, task_description: str, image_files: Optional[list[str]] = None) -> bool:
        """
        Execute a coding task using Aider.

        Args:
            task_description: Natural language description of code changes
            image_files: List of image file paths for context (optional)

        Returns:
            True if task completed successfully, False otherwise

        Raises:
            Exception: If Aider execution fails
        """
        logger.info(f"Starting Aider task: {task_description}")

        try:
            # Change to repo directory (required by Aider)
            import os
            old_cwd = os.getcwd()
            os.chdir(self.repo_path)

            # Initialize Aider with non-interactive IO
            model = Model(self.model_name)
            io = InputOutput(yes=True)  # Non-interactive mode

            self.coder = Coder.create(
                main_model=model,
                io=io,  # Use our non-interactive IO
                fnames=None,  # Auto-detect all relevant files - full access
                read_only_fnames=None,  # No read-only restrictions
                auto_commits=True,  # Let Aider auto-commit changes
                map_tokens=self.map_tokens,  # Repo map for context
                edit_format="diff",  # Use diff format for edits
                auto_lint=False,  # Don't block on linter errors
            )

            logger.info(f"Aider initialized with model {self.model_name}")

            # Build context about images if present
            image_context = ""
            if image_files:
                image_paths = [Path(img).relative_to(self.repo_path) for img in image_files if Path(img).exists()]
                if image_paths:
                    image_list = "\n".join([f"  - {path}" for path in image_paths])
                    image_context = f"""
CONTEXT - Reference Images:
The following images have been provided as context for this task:
{image_list}

These images are located in the `.dogwalker_images/` directory and can provide visual guidance for your implementation.
"""

            # Run the task with commit strategy instructions
            implementation_prompt = f"""
{task_description}
{image_context}
IMPORTANT - Commit Strategy:
- Break your work into bite-sized commits
- Each commit should change AT MOST 500 lines of code (across all files)
- Exception: If a single file requires >500 LOC changes, that file should be its own commit (and can exceed 500 LOC)
- Make commits incrementally as you complete each logical piece
- Use descriptive commit messages that explain what changed

Follow the commit strategy you outlined in the implementation plan.
"""
            result = self.coder.run(implementation_prompt)

            # Verify Aider made changes
            if not result:
                logger.warning("Aider did not produce any changes")
                os.chdir(old_cwd)  # Restore working directory
                return False

            # Track Aider cost (Aider internally tracks total_cost)
            if hasattr(self.coder, 'total_cost') and self.coder.total_cost:
                aider_cost = self.coder.total_cost
                self.total_cost += aider_cost
                self.cost_breakdown["implementation"] += aider_cost
                logger.info(f"Aider implementation cost: ${aider_cost:.4f} - Total cost: ${self.total_cost:.4f}")

            logger.info("Aider task completed successfully")
            os.chdir(old_cwd)  # Restore working directory
            return True

        except Exception as e:
            logger.exception(f"Aider task failed: {e}")
            os.chdir(old_cwd)  # Restore working directory even on error
            raise

    def run_self_review(self) -> bool:
        """
        Run self-review on the code changes made.

        This runs after the initial task is complete and allows the AI
        to critique its own work and make improvements.

        Returns:
            True if review completed (changes made or not), False on error
        """
        logger.info("Starting self-review of code changes")

        review_prompt = """
Review the changes you just made with a critical eye. Consider:

1. **Code Quality**: Is the code clean, readable, and maintainable?
2. **Best Practices**: Does it follow the project's coding standards and patterns?
3. **Edge Cases**: Are edge cases and error conditions handled properly?
4. **Performance**: Are there any obvious performance issues?
5. **Security**: Are there any security concerns?
6. **Testing**: Would this benefit from additional test coverage?
7. **Documentation**: Are complex parts documented clearly?

If you find any issues or improvements, make those changes now.
If everything looks good, respond with "LGTM" and make no changes.

IMPORTANT - Commit Strategy:
- If you make changes, use bite-sized commits (≤500 LOC per commit across all files)
- Exception: Single files with >500 LOC changes should be their own commit
- Use descriptive commit messages
"""

        try:
            # Change to repo directory
            import os
            old_cwd = os.getcwd()
            os.chdir(self.repo_path)

            # Re-initialize Aider for review (fresh context)
            model = Model(self.model_name)
            io = InputOutput(yes=True)

            self.coder = Coder.create(
                main_model=model,
                io=io,
                fnames=None,  # Auto-detect all relevant files - full access
                read_only_fnames=None,  # No read-only restrictions
                auto_commits=True,
                map_tokens=self.map_tokens,
                edit_format="diff",
                auto_lint=False,  # Don't block on linter errors
            )

            # Run review
            result = self.coder.run(review_prompt)

            # Track Aider cost
            if hasattr(self.coder, 'total_cost') and self.coder.total_cost:
                aider_cost = self.coder.total_cost
                self.total_cost += aider_cost
                self.cost_breakdown["self_review"] += aider_cost
                logger.info(f"Aider self-review cost: ${aider_cost:.4f} - Total cost: ${self.total_cost:.4f}")

            logger.info("Self-review completed")
            os.chdir(old_cwd)
            return True

        except Exception as e:
            logger.exception(f"Self-review failed: {e}")
            os.chdir(old_cwd)
            # Don't fail the whole task if review fails
            return True

    def write_and_run_tests(self) -> tuple[bool, str]:
        """
        Write comprehensive tests and run them.

        Returns:
            Tuple of (success, output/error message)
        """
        logger.info("Writing comprehensive tests")

        test_prompt = """
Write comprehensive tests for the changes you just made. Follow these guidelines:

1. **Test Coverage**: Write tests that cover:
   - Happy path (normal expected behavior)
   - Edge cases (boundary conditions, empty inputs, etc.)
   - Error cases (invalid inputs, error handling)
   - Integration points (if applicable)

2. **Test Quality**:
   - Tests should be clear and well-documented
   - Use descriptive test names
   - Follow the project's existing test patterns
   - Include assertions that verify behavior, not just that code runs

3. **Test Framework**:
   - Use the project's existing test framework (pytest, unittest, jest, etc.)
   - Follow existing test file naming and organization
   - Place tests in the appropriate test directory

After writing tests, run them to ensure they all pass.

If any tests fail, fix the code until all tests pass.
Only respond "DONE" when all tests are written and passing.

IMPORTANT - Commit Strategy:
- Use bite-sized commits (≤500 LOC per commit across all files)
- Exception: Single test files with >500 LOC should be their own commit
- Commit test files separately from test fixes
- Use descriptive commit messages
"""

        try:
            # Change to repo directory
            import os
            old_cwd = os.getcwd()
            os.chdir(self.repo_path)

            # Re-initialize Aider for test writing
            model = Model(self.model_name)
            io = InputOutput(yes=True)

            self.coder = Coder.create(
                main_model=model,
                io=io,
                fnames=None,  # Auto-detect files
                auto_commits=True,
                map_tokens=self.map_tokens,
                edit_format="diff",
            )

            # Write and run tests
            result = self.coder.run(test_prompt)

            # Track Aider cost
            if hasattr(self.coder, 'total_cost') and self.coder.total_cost:
                aider_cost = self.coder.total_cost
                self.total_cost += aider_cost
                self.cost_breakdown["testing"] += aider_cost
                logger.info(f"Aider testing cost: ${aider_cost:.4f} - Total cost: ${self.total_cost:.4f}")

            logger.info("Tests written and validated")
            os.chdir(old_cwd)
            return True, "Tests written and passing"

        except Exception as e:
            logger.exception(f"Test writing/running failed: {e}")
            os.chdir(old_cwd)
            return False, f"Test failure: {str(e)}"

    def generate_draft_pr_description(
        self,
        task_description: str,
        requester_name: str,
        request_time_str: str,
        plan: str,
        image_files: Optional[list[str]] = None,
    ) -> str:
        """
        Generate a draft PR description using Claude API.

        Args:
            task_description: Original task description
            requester_name: Display name of requester (with optional markdown link)
            request_time_str: Formatted timestamp of request
            plan: Implementation plan
            image_files: List of image file paths (optional)

        Returns:
            Complete PR description in markdown
        """
        logger.info("Generating draft PR description")

        # Convert images to markdown with relative paths
        image_markdown = ""
        if image_files:
            for img_path in image_files:
                try:
                    img_path_obj = Path(img_path)
                    if img_path_obj.exists():
                        # Use relative path from repo root
                        relative_path = img_path_obj.relative_to(self.repo_path)
                        # Use markdown image syntax with relative path
                        image_markdown += f'\n![{img_path_obj.name}]({relative_path})\n'
                except Exception as e:
                    logger.error(f"Failed to process image {img_path}: {e}")

        prompt = f"""Generate a GitHub pull request description for a work-in-progress PR.

Context:
- Requester: {requester_name}
- Request: {task_description}
- Requested on: {request_time_str}
- Implementation Plan:
{plan}

Format the PR description as professional markdown with these sections:
1. A header: "🐕 Dogwalker AI Task Report"
2. 👤 Requester section showing who requested this
3. 📋 Request section with the task description (as a blockquote){"   - Include images if provided below the task description" if image_markdown else ""}
4. 📅 When section showing when it was requested
5. 🎯 Implementation Plan section with the plan

End with:
---
🚧 **This is a draft PR** - Implementation in progress...

_This PR will be updated with changes and marked ready for review when complete._

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

Provide ONLY the markdown PR description. No explanations, no additional text."""

        try:
            return self.call_claude_api(prompt, max_tokens=1500, category="draft_pr_description")
        except Exception as e:
            logger.exception(f"Draft PR description generation failed: {e}")
            # Fallback to basic template
            return f"""## 🐕 Dogwalker AI Task Report

### 👤 Requester
**{requester_name}** requested this change

### 📋 Request
> {task_description}

{image_markdown if image_markdown else ""}

### 📅 When
Requested on **{request_time_str}**

### 🎯 Implementation Plan
{plan}

---

🚧 **This is a draft PR** - Implementation in progress...

_This PR will be updated with changes and marked ready for review when complete._

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)"""

    def generate_final_pr_description(
        self,
        task_description: str,
        requester_name: str,
        request_time_str: str,
        duration_str: str,
        plan: str,
        files_modified: list[str],
        critical_review_points: str,
        image_files: Optional[list[str]] = None,
        cost_report: Optional[dict[str, float]] = None,
    ) -> str:
        """
        Generate final PR description using Claude API.

        Args:
            task_description: Original task description
            requester_name: Display name of requester (with optional markdown link)
            request_time_str: Formatted timestamp of request
            duration_str: Human-readable duration string
            plan: Implementation plan
            files_modified: List of modified file paths
            critical_review_points: Critical areas needing review (or empty string)
            image_files: List of image file paths (optional)
            cost_report: API cost breakdown (optional, dict with "total_cost" and "breakdown")

        Returns:
            Complete final PR description in markdown
        """
        logger.info("Generating final PR description")

        # Convert images to markdown with relative paths
        image_markdown = ""
        if image_files:
            for img_path in image_files:
                try:
                    img_path_obj = Path(img_path)
                    if img_path_obj.exists():
                        # Use relative path from repo root
                        relative_path = img_path_obj.relative_to(self.repo_path)
                        # Use markdown image syntax with relative path
                        image_markdown += f'\n![{img_path_obj.name}]({relative_path})\n'
                except Exception as e:
                    logger.error(f"Failed to process image {img_path}: {e}")

        files_list = "\n".join([f"- `{f}`" for f in files_modified]) if files_modified else "_File changes were committed automatically by the AI agent_"

        critical_section = f"""

### ⚠️ Critical Review Areas
{critical_review_points}
""" if critical_review_points else ""

        # Format cost section if available
        cost_section = ""
        if cost_report:
            total_cost = cost_report.get("total_cost", 0.0)
            breakdown = cost_report.get("breakdown", {})

            # Format breakdown
            breakdown_lines = []
            for category, cost in breakdown.items():
                if cost > 0:
                    # Format category name (convert snake_case to Title Case)
                    category_name = category.replace("_", " ").title()
                    breakdown_lines.append(f"  - {category_name}: ${cost:.4f}")

            breakdown_text = "\n".join(breakdown_lines) if breakdown_lines else "  - No breakdown available"

            cost_section = f"""

### 💰 API Cost

**Total Cost:** ${total_cost:.4f}

<details>
<summary>Cost Breakdown</summary>

{breakdown_text}

</details>
"""

        prompt = f"""Generate a professional GitHub pull request description for completed work.

Context:
- Requester: {requester_name}
- Request: {task_description}
- Requested on: {request_time_str}
- Duration: {duration_str}
- Implementation Plan:
{plan}

Files Modified:
{files_list}

Critical Review Points:
{critical_review_points if critical_review_points else "None identified"}

Format the PR description as professional markdown with these sections:
1. Header: "🐕 Dogwalker AI Task Report"
2. 👤 Requester section
3. 📋 Request section (as blockquote){"   - Include images if provided below the task description" if image_markdown else ""}
4. 📅 When section
5. 🎯 Implementation Plan section
6. 📝 Changes Made section (list the modified files)
7. ⚠️ Critical Review Areas section (ONLY if there are critical points)
8. ✅ Quality Assurance section with:
   - Self-reviewed by the AI agent
   - Comprehensive tests written and verified passing
   - All code changes validated before submission
9. ⏱️ Task Duration section
10. 💰 API Cost section{cost_section if cost_report else " (SKIP if no cost data provided)"}

End with:
---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

Co-Authored-By: Claude <noreply@anthropic.com>

Provide ONLY the markdown PR description. Be professional and concise."""

        try:
            return self.call_claude_api(prompt, max_tokens=2000, category="final_pr_description")
        except Exception as e:
            logger.exception(f"Final PR description generation failed: {e}")
            # Fallback to basic template
            return f"""## 🐕 Dogwalker AI Task Report

### 👤 Requester
**{requester_name}** requested this change

### 📋 Request
> {task_description}

{image_markdown if image_markdown else ""}

### 📅 When
Requested on **{request_time_str}**

### 🎯 Implementation Plan
{plan}

### 📝 Changes Made
{files_list}
{critical_section}

### ✅ Quality Assurance
This PR has been:
- Self-reviewed by the AI agent
- Comprehensive tests written and verified passing
- All code changes validated before submission

### ⏱️ Task Duration
Completed in **{duration_str}**
{cost_section}

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    def get_cost_report(self) -> dict[str, float]:
        """
        Get a complete cost report for this task.

        Returns:
            Dictionary with total cost and breakdown by category
        """
        return {
            "total_cost": self.total_cost,
            "breakdown": self.cost_breakdown.copy()
        }

    def cleanup(self) -> None:
        """Clean up Aider resources."""
        if self.coder:
            # Aider cleanup (if needed)
            self.coder = None
            logger.info("Dog cleaned up successfully")
