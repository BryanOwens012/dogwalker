"""Dog worker - AI coding agent using Aider."""

import logging
from pathlib import Path
from typing import Optional, Any
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
        map_tokens: int = 512,  # Reduced from 1024 to leave headroom for web/search context
        communication: Optional[Any] = None,  # DogCommunication instance for bi-directional Slack
        search_tools: Optional[Any] = None,  # SearchTools instance for proactive web searching
        screenshot_tools: Optional[Any] = None  # ScreenshotTools instance for before/after screenshots
    ):
        """
        Initialize Dog with Aider.

        Args:
            repo_path: Path to git repository
            model_name: Claude model to use (default: Sonnet 4.5)
            map_tokens: Tokens for repo map context (default: 512, reduced to prevent context overflow)
            communication: DogCommunication instance for Slack interaction (optional)
            search_tools: SearchTools instance for internet searching (optional)
            screenshot_tools: ScreenshotTools instance for visual documentation (optional)
        """
        self.repo_path = repo_path
        self.model_name = model_name
        self.map_tokens = map_tokens
        self.coder: Optional[Coder] = None
        self.communication = communication  # Bi-directional Slack communication
        self.search_tools = search_tools  # Internet search capabilities
        self.screenshot_tools = screenshot_tools  # Before/after screenshot capabilities

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

        search_note = ""
        if self.search_tools:
            search_note = """
NOTE: You have access to internet search. If you need current information (API docs,
syntax references, compatibility info, examples), you can search proactively during implementation.
"""

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

Keep the entire plan under 250 words.{search_note}"""

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

    def _determine_needed_searches(self, task_description: str) -> list[str]:
        """
        Use AI to determine what internet searches would be helpful for this task.

        Args:
            task_description: The coding task

        Returns:
            List of search queries that would be helpful
        """
        if not self.search_tools:
            return []

        logger.info("Determining if internet searches would be helpful...")

        analysis_prompt = f"""Analyze this coding task and determine if internet searches would be helpful:

Task: "{task_description}"

Consider if you would benefit from:
- Current API documentation
- Library compatibility information
- Code examples and patterns
- Best practices for this type of implementation
- Version information or changelogs
- Technical specifications

If searches would be helpful, provide 1-5 specific search queries (one per line).
If no searches are needed, respond with "NONE".

Examples of good queries:
- "Next.js 14 app router data fetching"
- "Tailwind CSS v4 container queries"
- "OpenAI GPT-4 Turbo API pricing 2025"

Provide ONLY the search queries (or "NONE"), no explanations."""

        try:
            response = self.call_claude_api(analysis_prompt, max_tokens=200, category="search_analysis")
            response = response.strip()

            if response.upper() == "NONE" or not response:
                logger.info("No searches needed for this task")
                return []

            # Parse queries (one per line)
            queries = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith('-')]

            # Limit to 5 queries max
            queries = queries[:5]

            logger.info(f"Identified {len(queries)} helpful searches: {queries}")
            return queries

        except Exception as e:
            logger.error(f"Failed to analyze search needs: {e}")
            return []

    def _perform_searches(self, queries: list[str]) -> str:
        """
        Perform multiple internet searches and format results.

        Args:
            queries: List of search queries

        Returns:
            Formatted search results context
        """
        if not queries or not self.search_tools:
            return ""

        logger.info(f"Performing {len(queries)} internet searches...")

        search_results = []
        for query in queries:
            try:
                results = self.search_tools.search_with_context(query, max_results=3)
                search_results.append((query, results))
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")

        if not search_results:
            return ""

        # Format all searches into a context block
        context = self.search_tools.format_for_ai_context(
            searches=search_results,
            title="Proactive Internet Research"
        )

        logger.info(f"Search context generated: {len(context)} characters")
        return context

    def run_task(
        self,
        task_description: str,
        image_files: Optional[list[str]] = None,
        web_context: Optional[str] = None
    ) -> bool:
        """
        Execute a coding task using Aider.

        Args:
            task_description: Natural language description of code changes
            image_files: List of image file paths for context (optional)
            web_context: Formatted context from fetched websites (optional)

        Returns:
            True if task completed successfully, False otherwise

        Raises:
            Exception: If Aider execution fails
        """
        logger.info(f"Starting Aider task: {task_description}")

        # Proactively determine and perform needed searches
        search_context = ""
        if self.search_tools:
            search_queries = self._determine_needed_searches(task_description)
            if search_queries:
                search_context = self._perform_searches(search_queries)

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

            # Include web context if present
            web_context_section = ""
            if web_context:
                web_context_section = f"\n{web_context}\n"

            # Include search results if searches were performed
            search_context_section = ""
            if search_context:
                search_context_section = f"\n{search_context}\n"

            # Run the task with commit strategy instructions
            implementation_prompt = f"""
{task_description}
{image_context}{web_context_section}{search_context_section}
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
        image_github_urls: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Generate a draft PR description using Claude API.

        Args:
            task_description: Original task description
            requester_name: Display name of requester (with optional markdown link)
            request_time_str: Formatted timestamp of request
            plan: Implementation plan
            image_files: List of image file paths (optional)
            image_github_urls: Map of local paths to GitHub URLs (optional)

        Returns:
            Complete PR description in markdown
        """
        logger.info("Generating draft PR description")

        # Convert images to markdown using GitHub URLs if available
        image_markdown = ""
        if image_files:
            for img_path in image_files:
                try:
                    img_path_obj = Path(img_path)
                    if img_path_obj.exists():
                        # Use GitHub URL if available, otherwise fall back to relative path
                        if image_github_urls and img_path in image_github_urls:
                            image_url = image_github_urls[img_path]
                            logger.info(f"Using GitHub URL for image: {image_url}")
                        else:
                            # Fallback to relative path (for backwards compatibility)
                            relative_path = img_path_obj.relative_to(self.repo_path)
                            image_url = str(relative_path)
                            logger.warning(f"No GitHub URL found for {img_path}, using relative path")

                        # Use markdown image syntax
                        image_markdown += f'\n![{img_path_obj.name}]({image_url})\n'
                except Exception as e:
                    logger.error(f"Failed to process image {img_path}: {e}")

        # Build image section for prompt if images exist
        image_section = ""
        if image_markdown:
            image_section = f"""

Images provided (include these AFTER the task description in the Request section):
{image_markdown}
"""

        prompt = f"""Generate a GitHub pull request description for a work-in-progress PR.

Context:
- Requester: {requester_name}
- Request: {task_description}
- Requested on: {request_time_str}{image_section}
- Implementation Plan:
{plan}

Format the PR description as professional markdown with these sections:
1. A header: "🐕 Dogwalker AI Task Report"
2. 👤 Requester section showing who requested this
3. 📋 Request section with the task description (as a blockquote){" - Include the images AFTER the task description blockquote" if image_markdown else ""}
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
        image_github_urls: Optional[dict[str, str]] = None,
        cost_report: Optional[dict[str, float]] = None,
        thread_feedback: Optional[str] = None,
        before_screenshots: Optional[list[dict[str, str]]] = None,
        after_screenshots: Optional[list[dict[str, str]]] = None,
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
            image_github_urls: Map of local paths to GitHub URLs (optional)
            cost_report: API cost breakdown (optional, dict with "total_cost" and "breakdown")
            thread_feedback: Markdown-formatted list of thread messages (optional)
            before_screenshots: List of before screenshot dicts (optional)
            after_screenshots: List of after screenshot dicts (optional)

        Returns:
            Complete final PR description in markdown
        """
        logger.info("Generating final PR description")

        # Convert images to markdown using GitHub URLs if available
        image_markdown = ""
        if image_files:
            for img_path in image_files:
                try:
                    img_path_obj = Path(img_path)
                    if img_path_obj.exists():
                        # Use GitHub URL if available, otherwise fall back to relative path
                        if image_github_urls and img_path in image_github_urls:
                            image_url = image_github_urls[img_path]
                            logger.info(f"Using GitHub URL for image: {image_url}")
                        else:
                            # Fallback to relative path (for backwards compatibility)
                            relative_path = img_path_obj.relative_to(self.repo_path)
                            image_url = str(relative_path)
                            logger.warning(f"No GitHub URL found for {img_path}, using relative path")

                        # Use markdown image syntax
                        image_markdown += f'\n![{img_path_obj.name}]({image_url})\n'
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

        # Format thread feedback section if available
        thread_feedback_context = ""
        if thread_feedback:
            thread_feedback_context = f"""

Thread Feedback (messages received during implementation):
{thread_feedback}"""

        # Build image section for prompt if images exist
        image_section = ""
        if image_markdown:
            image_section = f"""

Images provided (include these AFTER the task description in the Request section):
{image_markdown}
"""

        # Format before/after screenshots section if available
        screenshots_context = ""
        if before_screenshots and after_screenshots:
            screenshots_context = "\n\nBefore/After Screenshots:"
            for i, (before, after) in enumerate(zip(before_screenshots, after_screenshots), 1):
                # Use GitHub URLs if available, fall back to relative paths
                before_url = before.get('github_url') or str(Path(before['path']).relative_to(self.repo_path))
                after_url = after.get('github_url') or str(Path(after['path']).relative_to(self.repo_path))
                page_url = before.get('url', 'Unknown page')
                screenshots_context += f"""

Page: {page_url}
Before: ![]({before_url})
After: ![]({after_url})
"""

        prompt = f"""Generate a professional GitHub pull request description for completed work.

Context:
- Requester: {requester_name}
- Request: {task_description}
- Requested on: {request_time_str}{image_section}
- Duration: {duration_str}
- Implementation Plan:
{plan}{thread_feedback_context}{screenshots_context}

Files Modified:
{files_list}

Critical Review Points:
{critical_review_points if critical_review_points else "None identified"}

Format the PR description as professional markdown with these sections:
1. Header: "🐕 Dogwalker AI Task Report"
2. 👤 Requester section
3. 📋 Request section (as blockquote){" - Include the images AFTER the task description blockquote" if image_markdown else ""}
4. 📅 When section
5. 🎯 Implementation Plan section
6. 📝 Changes Made section (list the modified files)
7. 📸 Visual Changes section {"- Use the before/after screenshots provided in the context above, formatted as a comparison table" if screenshots_context else "(ONLY if before/after screenshots were provided)"}
8. 💬 Thread Feedback section (ONLY if thread feedback was provided during implementation)
9. ⚠️ Critical Review Areas section (ONLY if there are critical points)
10. ✅ Quality Assurance section with:
   - Self-reviewed by the AI agent
   - Comprehensive tests written and verified passing
   - All code changes validated before submission
11. ⏱️ Task Duration section
12. 💰 API Cost section{cost_section if cost_report else " (SKIP if no cost data provided)"}

End with:
---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

Co-Authored-By: Claude <noreply@anthropic.com>

Provide ONLY the markdown PR description. Be professional and concise."""

        try:
            return self.call_claude_api(prompt, max_tokens=2000, category="final_pr_description")
        except Exception as e:
            logger.exception(f"Final PR description generation failed: {e}")

            # Format thread feedback section for fallback template
            thread_feedback_section = ""
            if thread_feedback:
                thread_feedback_section = f"""

### 💬 Thread Feedback

The following feedback was provided during implementation:

{thread_feedback}
"""

            # Format before/after screenshots section for fallback template
            screenshots_section = ""
            if before_screenshots and after_screenshots:
                screenshots_section = "\n\n### 📸 Visual Changes\n\n"
                for i, (before, after) in enumerate(zip(before_screenshots, after_screenshots), 1):
                    # Use GitHub URLs if available, fall back to relative paths
                    before_url = before.get('github_url') or str(Path(before['path']).relative_to(self.repo_path))
                    after_url = after.get('github_url') or str(Path(after['path']).relative_to(self.repo_path))
                    page_url = before.get('url', 'Unknown page')
                    screenshots_section += f"""
**Page: {page_url}**

| Before | After |
|--------|-------|
| ![]({before_url}) | ![]({after_url}) |

"""

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
{screenshots_section}{thread_feedback_section}{critical_section}

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

    def ask_human(self, question: str, timeout: int = 600) -> Optional[str]:
        """
        Ask a clarifying question to the human via Slack and wait for response.

        This should be used SPARINGLY - only when truly necessary for making
        important product or architecture decisions that can't be inferred
        from existing patterns.

        Args:
            question: The question to ask
            timeout: Maximum time to wait for response in seconds (default: 10 minutes)

        Returns:
            Human's response as a string, or None if no response received
        """
        if not self.communication:
            logger.warning("Cannot ask human - no communication channel available")
            return None

        logger.info(f"Asking human: {question[:100]}...")

        # Post question to Slack
        self.communication.post_question(question)

        # Wait for response
        messages = self.communication.wait_for_response(timeout=timeout, min_messages=1)

        if not messages:
            logger.warning("No response received from human")
            return None

        # Combine all responses
        response = "\n\n".join(
            f"{msg['user_name']}: {msg['text']}"
            for msg in messages
        )

        logger.info(f"Received human response: {response[:100]}...")
        return response

    def check_for_feedback(self) -> Optional[str]:
        """
        Check for human feedback without blocking.

        Returns:
            Feedback text if available, None otherwise
        """
        if not self.communication:
            return None

        return self.communication.check_for_feedback()

    def search_web(self, query: str, max_results: int = 5) -> Optional[str]:
        """
        Proactively search the internet for information.

        Dogs can call this method whenever they need current information,
        documentation, examples, or context that isn't in the codebase.

        Args:
            query: Search query (be specific for better results)
            max_results: Number of search results to retrieve (default: 5)

        Returns:
            Formatted search results as text, or None if search tools unavailable

        Example usage (within dog's decision-making):
            - Need API documentation: search_web("OpenAI API rate limits 2025")
            - Check current syntax: search_web("React 18 useEffect cleanup pattern")
            - Find examples: search_web("Tailwind CSS responsive navbar example")
            - Verify compatibility: search_web("Python 3.12 asyncio changes")
        """
        if not self.search_tools:
            logger.warning("Cannot search web - no search tools available")
            return None

        logger.info(f"Dog searching internet: {query}")

        try:
            results = self.search_tools.search_with_context(
                query=query,
                max_results=max_results,
                include_quick_answer=True
            )

            logger.info(f"Search completed: {len(results)} characters of context")
            return results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return None

    def capture_before_screenshots(self, plan: str) -> list[dict[str, str]]:
        """
        Capture "before" screenshots of frontend pages before implementation.

        Args:
            plan: Implementation plan

        Returns:
            List of screenshot info dicts with url, filename, path, github_url
        """
        if not self.screenshot_tools:
            logger.warning("Cannot capture screenshots - no screenshot tools available")
            return []

        # Check if this is a frontend task
        if not self.screenshot_tools.is_frontend_task(plan):
            logger.info("Not a frontend task, skipping before screenshots")
            return []

        logger.info("✅ Frontend task detected - attempting to capture before screenshots")

        # Start dev server
        logger.info("Starting dev server...")
        if not self.screenshot_tools.start_dev_server():
            logger.error("❌ Failed to start dev server - skipping screenshots")
            logger.error("Possible reasons: no package.json, no dev script, server crash, port in use")
            return []

        logger.info("✅ Dev server started successfully")

        # Extract URLs from plan
        logger.info("Extracting page URLs from plan...")
        urls = self.screenshot_tools.extract_urls_from_plan(plan)
        logger.info(f"Extracted URLs to screenshot: {urls}")

        if not urls:
            logger.warning("❌ No URLs extracted from plan - cannot capture screenshots")
            self.screenshot_tools.stop_dev_server()
            return []

        # Capture screenshots
        logger.info(f"Capturing screenshots for {len(urls)} URLs...")
        screenshots = self.screenshot_tools.capture_multiple_screenshots(urls, prefix="before_")

        if screenshots:
            logger.info(f"✅ Successfully captured {len(screenshots)} before screenshots")
            # Log GitHub URLs for verification
            for shot in screenshots:
                github_url = shot.get('github_url')
                if github_url:
                    logger.info(f"  - {shot['url']}: {github_url}")
                else:
                    logger.warning(f"  - {shot['url']}: GitHub upload failed, no URL available")
        else:
            logger.error("❌ Failed to capture any screenshots")

        return screenshots

    def capture_after_screenshots(self, before_screenshots: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        Capture "after" screenshots of the same URLs as before screenshots.

        Args:
            before_screenshots: List of before screenshot info (used to get URLs)

        Returns:
            List of after screenshot info dicts with url, filename, path, github_url
        """
        if not self.screenshot_tools or not before_screenshots:
            if not before_screenshots:
                logger.info("No before screenshots to match - skipping after screenshots")
            return []

        logger.info("Capturing after screenshots to compare with before...")

        # Restart dev server to ensure latest code is running
        logger.info("Stopping dev server...")
        self.screenshot_tools.stop_dev_server()

        logger.info("Restarting dev server with new code...")
        if not self.screenshot_tools.start_dev_server():
            logger.error("❌ Failed to restart dev server - skipping after screenshots")
            return []

        logger.info("✅ Dev server restarted with new code")

        # Capture same URLs as before
        urls = [shot['url'] for shot in before_screenshots]
        logger.info(f"Capturing after screenshots for {len(urls)} URLs: {urls}")
        screenshots = self.screenshot_tools.capture_multiple_screenshots(urls, prefix="after_")

        if screenshots:
            logger.info(f"✅ Successfully captured {len(screenshots)} after screenshots")
            # Log GitHub URLs for verification
            for shot in screenshots:
                github_url = shot.get('github_url')
                if github_url:
                    logger.info(f"  - {shot['url']}: {github_url}")
                else:
                    logger.warning(f"  - {shot['url']}: GitHub upload failed, no URL available")
        else:
            logger.error("❌ Failed to capture any after screenshots")

        return screenshots

    def cleanup(self) -> None:
        """Clean up Aider resources."""
        if self.coder:
            # Aider cleanup (if needed)
            self.coder = None
            logger.info("Dog cleaned up successfully")

        # Stop dev server if running
        if self.screenshot_tools:
            self.screenshot_tools.cleanup()
