"""Worker task implementation - actual code execution logic."""

from celery import Task
from celery_app import app
import logging
import sys
from pathlib import Path
from typing import Any, List, Dict, Optional
import os

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))
# Add orchestrator module to path (for dog_selector)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "orchestrator" / "src"))

from config import config
from github_client import GitHubClient
from slack_utils import (
    format_task_completed,
    format_task_failed,
    format_draft_pr_created,
    format_task_cancelled,
)
from repo_manager import RepoManager
from dog import Dog
from dog_selector import DogSelector
from cancellation import CancellationManager, TaskCancelled
from dog_communication import DogCommunication
from web_tools import WebTools
from search_tools import SearchTools
from screenshot_tools import ScreenshotTools

logger = logging.getLogger(__name__)

# Initialize dog selector for marking tasks complete
dog_selector = DogSelector()

# Initialize cancellation manager for checking task cancellation
cancellation_manager = CancellationManager(config.redis_url)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Fix Pydantic V2.11 deprecation issue in litellm
# litellm accesses model_fields on instance instead of class
# This monkey-patch fixes the issue properly instead of suppressing the warning
def _patch_litellm_pydantic():
    """Patch litellm to use Pydantic V2.11+ correctly."""
    try:
        from litellm.litellm_core_utils import core_helpers

        # Store original function
        original_convert_to_model_response_object = core_helpers.convert_to_model_response_object

        def patched_convert_to_model_response_object(response_object, model_response_object):
            """Patched version that accesses model_fields from class, not instance."""
            # Get expected keys from the MODEL CLASS, not the instance
            expected_keys = set(type(model_response_object).model_fields.keys()).union({"usage"})

            # Rest of the original logic
            for key, value in response_object.items():
                if key in expected_keys:
                    setattr(model_response_object, key, value)

            return model_response_object

        # Apply the patch
        core_helpers.convert_to_model_response_object = patched_convert_to_model_response_object
        logger.info("✅ Applied Pydantic V2.11 compatibility patch to litellm")

    except ImportError:
        # litellm not installed or different version - no patch needed
        logger.debug("litellm not found or different structure - skipping patch")
    except AttributeError:
        # Function doesn't exist or structure changed - no patch needed
        logger.debug("litellm function structure different - skipping patch")
    except Exception as e:
        # Don't fail startup if patch fails
        logger.warning(f"Could not patch litellm: {e}")

# Apply the patch at module load time
_patch_litellm_pydantic()


@app.task(
    bind=True,
    name="tasks.run_coding_task",  # Must match orchestrator task name
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
    dog_name: str,
    dog_display_name: str,
    dog_email: str,
    thread_ts: str,
    channel_id: str,
    requester_name: str,
    requester_profile_url: str,
    start_time: float,
    images: Optional[List[Dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    Execute a coding task with Aider.

    This is the actual implementation that runs on the worker.
    It replaces the placeholder in orchestrator/tasks.py.

    Args:
        task_id: Unique task identifier
        task_description: What code changes to make
        branch_name: Git branch name for the changes
        dog_name: Dog's full GitHub username (e.g., "Bryans-Coregi")
        dog_display_name: Dog's display name (e.g., "Coregi")
        dog_email: Dog's email for commits
        thread_ts: Slack thread timestamp for updates
        channel_id: Slack channel ID
        requester_name: Display name of person who requested the change
        requester_profile_url: Slack profile URL of the requester
        start_time: Unix timestamp when request was made
        images: List of images from Slack (dicts with 'filename', 'mimetype', 'data')

    Returns:
        Dictionary with task results and metadata
    """
    logger.info(f"Worker executing task {task_id} as {dog_name}")

    work_dir = Path(__file__).parent.parent.parent.parent / "workdir" / task_id
    slack_client = None
    pr_info = None
    current_phase = "initialization"  # Track which phase we're in for cancellation

    def check_cancellation(phase: str) -> None:
        """Check if task has been cancelled and raise exception if so."""
        nonlocal current_phase
        current_phase = phase

        if cancellation_manager.is_cancelled(task_id):
            cancel_info = cancellation_manager.get_cancellation_info(task_id)
            cancelled_by = cancel_info.get("cancelled_by", "Unknown User") if cancel_info else "Unknown User"
            logger.info(f"Task {task_id} cancelled by {cancelled_by} during {phase}")
            raise TaskCancelled(cancelled_by=cancelled_by, phase=phase)

    try:
        # Initialize Slack client (for posting updates)
        from slack_bolt import App
        slack_app = App(token=config.slack_bot_token)
        slack_client = slack_app.client

        # Get dog-specific GitHub token from config
        dog_info = None
        for dog in config.dogs:
            if dog["name"] == dog_name:
                dog_info = dog
                break

        if not dog_info:
            raise ValueError(f"Dog {dog_name} not found in config")

        dog_github_token = dog_info["github_token"]

        # Initialize GitHub client with dog-specific token
        github_client = GitHubClient(
            token=dog_github_token,
            repo_name=config.github_repo
        )

        # Step 1: Clone repository and create branch
        logger.info(f"Cloning repository {config.github_repo}")

        repo_url = f"https://github.com/{config.github_repo}"
        repo_manager = RepoManager(
            repo_url=repo_url,
            work_dir=work_dir,
            dog_name=dog_name,
            dog_email=dog_email,
            github_token=dog_github_token  # Use dog-specific token
        )

        repo_manager.clone()
        repo_manager.create_branch(branch_name, base_branch=config.base_branch)

        # Step 1.5: Save images to work directory and upload to GitHub
        image_files = []
        image_github_urls = {}  # Map local path to GitHub URL
        if images:
            logger.info(f"Saving and uploading {len(images)} image(s)")
            images_dir = work_dir / ".dogwalker_images"
            images_dir.mkdir(exist_ok=True)

            import base64
            import re
            for i, img in enumerate(images):
                filename = img.get("filename", f"image_{i}.png")
                data = img.get("data", "")

                # Sanitize filename: replace spaces and special chars with underscores
                # Keep extension (.png, .jpg, etc.)
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    name, ext = name_parts
                    # Replace spaces and special characters with underscores
                    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
                    sanitized_filename = f"{name}.{ext}"
                else:
                    # No extension, just sanitize the whole name
                    sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

                logger.info(f"Sanitized filename: {filename} -> {sanitized_filename}")

                # Decode base64 image data
                try:
                    image_bytes = base64.b64decode(data)
                    image_path = images_dir / sanitized_filename
                    image_path.write_bytes(image_bytes)

                    # Upload to GitHub for persistent URL (same as screenshots)
                    logger.info(f"Uploading Slack image to GitHub: {sanitized_filename}")
                    github_url = github_client.upload_image_to_github(
                        image_path=str(image_path),
                        screenshot_filename=f"slack_{sanitized_filename}"  # Prefix to distinguish from screenshots
                    )

                    if github_url:
                        image_github_urls[str(image_path)] = github_url
                        logger.info(f"✅ Slack image uploaded successfully!")
                        logger.info(f"   Local path: {image_path}")
                        logger.info(f"   GitHub URL: {github_url}")
                    else:
                        logger.error(f"❌ Failed to upload Slack image to GitHub: {filename}")
                        logger.error(f"   This image will NOT appear in PR description")
                        logger.error(f"   Check GitHub token permissions for branch creation and file writes")

                    image_files.append(str(image_path))
                    logger.info(f"Saved image: {filename} ({len(image_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"Failed to save/upload image {filename}: {e}")

            # No longer need to commit images to branch - they're uploaded to GitHub
            logger.info(f"📊 Image upload summary: {len(image_files)} total, {len(image_github_urls)} uploaded to GitHub")
            if image_github_urls:
                logger.info("GitHub URLs mapping:")
                for local, github in image_github_urls.items():
                    logger.info(f"  {local} -> {github}")

        # Step 1.6: Detect and fetch URLs from task description
        web_context = None
        web_screenshot_files = []
        urls = WebTools.extract_urls(task_description)

        if urls:
            logger.info(f"Detected {len(urls)} URL(s) in task description, fetching and screenshotting...")

            web_tools = WebTools(work_dir=work_dir)

            # Fetch and screenshot websites (limit to 5 URLs)
            fetch_results = web_tools.fetch_multiple_urls(urls, max_urls=5)

            # Get screenshot paths for successful fetches
            web_screenshot_files = web_tools.get_screenshot_paths(fetch_results)

            # Format context for AI
            web_context = web_tools.format_web_context_for_ai(fetch_results)

            # Commit screenshots to branch
            if web_screenshot_files:
                logger.info(f"Committing {len(web_screenshot_files)} website screenshot(s) to branch")
                repo_manager.commit_changes(f"Add website screenshots ({len(web_screenshot_files)} screenshot(s))")

            # Combine with image_files for PR description
            if web_screenshot_files:
                image_files.extend(web_screenshot_files)
                logger.info(f"Total visual assets: {len(image_files)} (images + screenshots)")

        # Step 2: Create placeholder commit so PR can be created
        logger.info("Creating placeholder commit for PR creation")
        gitkeep_path = work_dir / ".gitkeep"
        gitkeep_path.write_text("# Placeholder - work in progress\n")
        repo_manager.commit_changes("Initial commit - starting work")

        # Step 3: Push branch with placeholder commit
        logger.info("Pushing branch to enable PR creation")
        repo_manager.push_branch(branch_name)

        # Checkpoint: Before planning phase
        check_cancellation("initialization")

        # Step 3.5: Initialize communication helper for bi-directional Slack interaction
        logger.info("Initializing dog communication channel")
        communication = DogCommunication(
            task_id=task_id,
            thread_ts=thread_ts,
            channel_id=channel_id,
            dog_name=dog_display_name,
            slack_client=slack_client,
            redis_client=dog_selector.redis_client,
        )

        # Step 4: Initialize Dog and generate PR title and implementation plan
        logger.info("Initializing AI agent (Dog)")

        # Initialize search tools for proactive internet research
        search_tools = SearchTools()

        # Initialize screenshot tools for before/after visual documentation
        screenshot_tools = ScreenshotTools(
            repo_path=work_dir,
            work_dir=work_dir,
            github_client=github_client  # Pass GitHub client for uploading screenshots
        )

        dog = Dog(
            repo_path=work_dir,
            communication=communication,
            search_tools=search_tools,
            screenshot_tools=screenshot_tools
        )

        logger.info("Generating concise PR title")
        # Generate AI-created title (max 57 chars to leave room for "[Dogwalker] " prefix)
        pr_title_text = dog.generate_pr_title(task_description, max_length=57)

        logger.info("Generating implementation plan")
        plan = dog.generate_plan(task_description)

        # Step 5: Create draft PR with plan
        logger.info("Creating draft PR with plan")

        # Construct final PR title with prefix (max 70 chars total)
        PREFIX = "[Dogwalker] "
        MAX_TITLE_LENGTH = 70

        pr_title = f"{PREFIX}{pr_title_text}"

        # Safety validation: ensure title never exceeds 70 chars
        if len(pr_title) > MAX_TITLE_LENGTH:
            logger.warning(f"PR title exceeded max length ({len(pr_title)} > {MAX_TITLE_LENGTH}), truncating")
            # Emergency truncation at word boundary
            available = MAX_TITLE_LENGTH - len(PREFIX)
            pr_title_text = pr_title_text[:available].rsplit(' ', 1)[0]
            pr_title = f"{PREFIX}{pr_title_text}"

        logger.info(f"PR title: '{pr_title}' ({len(pr_title)}/{MAX_TITLE_LENGTH} chars)")

        # Format requester name with link
        from datetime import datetime
        import pytz

        local_tz = pytz.timezone('America/Los_Angeles')
        request_time = datetime.fromtimestamp(start_time, tz=pytz.UTC).astimezone(local_tz)
        request_time_str = request_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")

        if requester_profile_url:
            requester_link = f"[{requester_name}]({requester_profile_url})"
        else:
            requester_link = requester_name

        # Generate draft PR description using Claude
        draft_pr_body = dog.generate_draft_pr_description(
            task_description=task_description,
            requester_name=requester_link,
            request_time_str=request_time_str,
            plan=plan,
            image_files=image_files if image_files else None,
            image_github_urls=image_github_urls if image_github_urls else None,
        )

        pr_info = github_client.create_pull_request(
            branch_name=branch_name,
            title=pr_title,
            body=draft_pr_body,
            base_branch=config.base_branch,
            draft=True,
            assignee=dog_name,  # Assign PR to the dog
        )

        if not pr_info:
            raise ValueError("Failed to create draft PR")

        # Step 6: Post draft PR to Slack
        logger.info("Posting draft PR announcement to Slack")

        # Extract brief plan preview (max 350 chars, preserve line breaks)
        if len(plan) > 350:
            # Truncate at 347 chars to leave room for "..."
            plan_preview = plan[:347] + "..."
        else:
            plan_preview = plan

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=format_draft_pr_created(
                pr_title=pr_info["pr_title"],
                pr_url=pr_info["pr_url"],
                plan_preview=plan_preview,
                dog_name=dog_display_name,
            )
        )

        # Checkpoint: Before implementation phase
        check_cancellation("planning")

        # Step 6.5: Capture "before" screenshots if this is a frontend task
        logger.info("Checking if before screenshots are needed...")
        before_screenshots = dog.capture_before_screenshots(plan)

        if before_screenshots:
            logger.info(f"Captured and uploaded {len(before_screenshots)} before screenshots to GitHub")
            # Screenshots are uploaded to GitHub (dogwalker-screenshots branch), not committed to PR branch

        # Check for human feedback before starting implementation
        feedback = communication.check_for_feedback()
        if feedback:
            logger.info("Received human feedback before implementation, incorporating...")
            communication.post_update("I've received your feedback and will incorporate it into my implementation! 👍")

        # Step 7: Run Aider to make code changes
        logger.info(f"Running Aider with task: {task_description}")

        # Include feedback in task description if present
        full_task_description = task_description
        if feedback:
            full_task_description = f"{task_description}\n\n{communication.format_feedback_for_prompt(feedback)}"

        success = dog.run_task(
            full_task_description,
            image_files=image_files if image_files else None,
            web_context=web_context
        )

        if not success:
            raise ValueError("Aider did not produce code changes")

        # Checkpoint: Before self-review phase
        check_cancellation("implementation")

        # Check for feedback after implementation
        logger.info("Checking for any new feedback after implementation")
        post_impl_feedback = communication.check_for_feedback()
        if post_impl_feedback:
            logger.info("Received feedback after implementation, incorporating into self-review...")
            communication.post_update("I've received your feedback and will incorporate it during my review! 👍")

            # Run additional changes based on feedback
            feedback_prompt = f"""{communication.format_feedback_for_prompt(post_impl_feedback)}

Please make these changes now."""
            dog.run_task(feedback_prompt, web_context=web_context)

        # Step 8: Run self-review
        logger.info("Running self-review on code changes")
        dog.run_self_review()

        # Checkpoint: Before testing phase
        check_cancellation("self-review")

        # Check for feedback after self-review
        logger.info("Checking for any new feedback after self-review")
        post_review_feedback = communication.check_for_feedback()
        if post_review_feedback:
            logger.info("Received feedback after self-review, incorporating before testing...")
            communication.post_update("I've received your feedback and will incorporate it before writing tests! 👍")

            # Run additional changes based on feedback
            feedback_prompt = f"""{communication.format_feedback_for_prompt(post_review_feedback)}

Please make these changes now."""
            dog.run_task(feedback_prompt, web_context=web_context)

        # Step 9: Write and run comprehensive tests
        logger.info("Writing and running comprehensive tests")
        test_success, test_message = dog.write_and_run_tests()

        if not test_success:
            raise ValueError(f"Tests failed: {test_message}")

        logger.info(f"Tests completed successfully: {test_message}")

        # Check for final feedback before pushing
        logger.info("Checking for any final feedback before pushing changes")
        final_feedback = communication.check_for_feedback()
        if final_feedback:
            logger.info("Received final feedback before pushing, incorporating now...")
            communication.post_update("I've received your final feedback and will incorporate it before finishing! 👍")

            # Run final changes based on feedback
            feedback_prompt = f"""{communication.format_feedback_for_prompt(final_feedback)}

Please make these changes now."""
            dog.run_task(feedback_prompt, web_context=web_context)

            # Re-run tests to ensure changes didn't break anything
            logger.info("Re-running tests after incorporating final feedback")
            test_success, test_message = dog.write_and_run_tests()
            if not test_success:
                raise ValueError(f"Tests failed after final feedback: {test_message}")

        # Step 9.5: Capture "after" screenshots if we took "before" screenshots
        after_screenshots = []
        if before_screenshots:
            logger.info("Capturing after screenshots...")
            after_screenshots = dog.capture_after_screenshots(before_screenshots)

            if after_screenshots:
                logger.info(f"Captured and uploaded {len(after_screenshots)} after screenshots to GitHub")
                # Screenshots are uploaded to GitHub (dogwalker-screenshots branch), not committed to PR branch

        # Step 10: Remove placeholder file and push final changes
        logger.info("Removing placeholder .gitkeep file")
        if gitkeep_path.exists():
            gitkeep_path.unlink()
            repo_manager.commit_changes("Remove placeholder file")

        logger.info(f"Pushing final changes to branch {branch_name}")
        repo_manager.push_branch(branch_name)

        # Step 11: Calculate duration and get modified files
        logger.info("Calculating task duration and collecting changes")

        import time as time_module
        end_time = time_module.time()
        duration_seconds = end_time - start_time

        # Format duration
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        if minutes > 0:
            duration_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
        else:
            duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"

        modified_files = repo_manager.get_modified_files(base_branch=config.base_branch)

        # Step 12: Generate final PR description with Claude
        logger.info("Generating final PR description with Claude AI")

        # Ask Claude to identify critical review points
        critical_review_prompt = """Based on the code changes that were just made, identify ONLY critical areas that need careful review.

Focus on: breaking changes, configuration changes, security-sensitive code, database migrations, API changes, critical algorithms.

Respond with a bulleted list of SPECIFIC critical areas, or "No critical areas identified" if none.
Max 3-5 bullet points."""

        try:
            critical_review_points = dog.call_claude_api(
                critical_review_prompt, max_tokens=500, category="critical_review"
            ).strip()
            if "no critical" in critical_review_points.lower() and len(critical_review_points) < 100:
                critical_review_points = ""
        except Exception as e:
            logger.error(f"Failed to identify critical review points: {e}")
            critical_review_points = ""

        # Get cost report from dog
        cost_report = dog.get_cost_report()
        logger.info(f"Total API cost for task: ${cost_report['total_cost']:.4f}")

        # Collect thread feedback for PR description
        logger.info("Collecting thread feedback for PR description")
        thread_feedback = communication.format_messages_for_pr()

        # Generate complete final PR description
        final_pr_body = dog.generate_final_pr_description(
            task_description=task_description,
            requester_name=requester_link,
            request_time_str=request_time_str,
            duration_str=duration_str,
            plan=plan,
            files_modified=modified_files,
            critical_review_points=critical_review_points,
            image_files=image_files if image_files else None,
            image_github_urls=image_github_urls if image_github_urls else None,
            cost_report=cost_report,
            thread_feedback=thread_feedback,
            before_screenshots=before_screenshots if before_screenshots else None,
            after_screenshots=after_screenshots if after_screenshots else None,
        )

        github_client.update_pull_request(
            pr_number=pr_info["pr_number"],
            body=final_pr_body,
        )

        # Step 13: Mark PR as ready for review
        logger.info("Marking PR as ready for review")
        github_client.mark_pr_ready(pr_info["pr_number"])

        # Step 14: Post completion to Slack
        logger.info(f"Posting completion to Slack thread {thread_ts}")

        slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=format_task_completed(
                pr_title=pr_info["pr_title"],
                pr_url=pr_info["pr_url"],
                dog_name=dog_display_name,
            )
        )

        logger.info(f"Task {task_id} completed successfully")

        # Mark dog as free (for load balancing)
        dog_selector.mark_dog_free(dog_name, task_id)

        return {
            "status": "success",
            "task_id": task_id,
            "pr_url": pr_info["pr_url"],
            "branch_name": branch_name,
            "dog_name": dog_display_name,
        }

    except TaskCancelled as cancel_exc:
        logger.info(f"Task {task_id} was cancelled by {cancel_exc.cancelled_by} during {cancel_exc.phase}")

        # Determine what was completed
        phase_descriptions = {
            "initialization": "Repository cloned and branch created",
            "planning": "Implementation plan generated",
            "implementation": "Code changes implemented",
            "self-review": "Code changes reviewed and improved",
            "testing": "Tests written and verified"
        }
        phase_completed = phase_descriptions.get(cancel_exc.phase, "Initial setup")

        try:
            # Update PR description with cancellation note if PR was created
            if pr_info:
                logger.info("Updating PR with cancellation notice")

                # Generate cancelled PR body
                from datetime import datetime
                import pytz

                local_tz = pytz.timezone('America/Los_Angeles')
                request_time = datetime.fromtimestamp(start_time, tz=pytz.UTC).astimezone(local_tz)
                request_time_str = request_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")

                import time as time_module
                cancel_time = time_module.time()
                duration_seconds = cancel_time - start_time
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                if minutes > 0:
                    duration_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
                else:
                    duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"

                if requester_profile_url:
                    requester_link = f"[{requester_name}]({requester_profile_url})"
                else:
                    requester_link = requester_name

                cancelled_pr_body = f"""## 🐕 Dogwalker AI Task Report

### 👤 Requester
**{requester_link}** requested this change

### 📋 Request
> {task_description}

### 📅 When
Requested on **{request_time_str}**

### 🛑 Task Cancelled
**This task was cancelled by {cancel_exc.cancelled_by}** during the {cancel_exc.phase} phase.

### ✅ What Was Completed
{phase_completed}

### ❌ What Was Not Completed
The task was stopped before completion. The following phases were not executed:
"""

                # List remaining phases
                all_phases = ["initialization", "planning", "implementation", "self-review", "testing", "finalization"]
                current_phase_index = all_phases.index(cancel_exc.phase) if cancel_exc.phase in all_phases else 0
                remaining_phases = all_phases[current_phase_index + 1:]

                phase_names = {
                    "planning": "- Implementation planning",
                    "implementation": "- Code implementation",
                    "self-review": "- Self-review and improvements",
                    "testing": "- Test writing and validation",
                    "finalization": "- Final PR updates"
                }

                for phase in remaining_phases:
                    if phase in phase_names:
                        cancelled_pr_body += f"\n{phase_names[phase]}"

                cancelled_pr_body += f"""

### ⏱️ Time Before Cancellation
Worked for **{duration_str}** before cancellation.

---
🤖 Generated with [Dogwalker AI](https://dogwalker.dev)

_Note: This is a partial implementation that was cancelled mid-execution._
"""

                # Update the PR
                github_client.update_pull_request(
                    pr_number=pr_info["pr_number"],
                    body=cancelled_pr_body,
                )

            # Post cancellation message to Slack
            if slack_client:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=format_task_cancelled(
                        dog_name=dog_display_name,
                        cancelled_by=cancel_exc.cancelled_by,
                        pr_url=pr_info["pr_url"] if pr_info else None,
                        phase_completed=phase_completed
                    )
                )

        except Exception as e:
            logger.error(f"Error handling cancellation: {e}")

        # Clear cancellation signal
        cancellation_manager.clear_cancellation(task_id)

        # Mark dog as free
        dog_selector.mark_dog_free(dog_name, task_id)

        return {
            "status": "cancelled",
            "task_id": task_id,
            "cancelled_by": cancel_exc.cancelled_by,
            "phase": cancel_exc.phase,
            "pr_url": pr_info["pr_url"] if pr_info else None,
        }

    except Exception as exc:
        logger.exception(f"Task {task_id} failed: {exc}")

        # Post failure to Slack
        if slack_client:
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=format_task_failed(str(exc), dog_display_name)
                )
            except Exception as e:
                logger.error(f"Failed to post error to Slack: {e}")

        # Mark dog as free even on failure (for load balancing)
        dog_selector.mark_dog_free(dog_name, task_id)

        # Retry transient errors (network, git, etc.)
        if isinstance(exc, (IOError, OSError, ConnectionError)):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        # Permanent failure
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(exc),
            "dog_name": dog_display_name,
        }

    finally:
        # Cleanup work directory
        if work_dir.exists():
            import shutil
            try:
                shutil.rmtree(work_dir)
                logger.info(f"Cleaned up work directory {work_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup work directory: {e}")
