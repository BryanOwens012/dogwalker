"""Git repository management for Dogwalker workers."""

import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class RepoManager:
    """Manages git operations for code changes."""

    def __init__(
        self,
        repo_url: str,
        work_dir: Path,
        dog_name: str,
        dog_email: str,
        github_token: str
    ):
        """
        Initialize repository manager.

        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo)
            work_dir: Directory to clone repo into
            dog_name: Git user name for commits
            dog_email: Git email for commits
            github_token: GitHub token for authentication
        """
        self.repo_url = repo_url
        self.work_dir = work_dir
        self.dog_name = dog_name
        self.dog_email = dog_email
        self.github_token = github_token

        # Construct authenticated clone URL
        # Format: https://TOKEN@github.com/owner/repo.git
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url.replace("https://github.com/", "")
            self.auth_url = f"https://{github_token}@github.com/{repo_path}"
            if not self.auth_url.endswith(".git"):
                self.auth_url += ".git"
        else:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

    def clone(self) -> Path:
        """
        Clone repository to work directory.

        Returns:
            Path to cloned repository

        Raises:
            subprocess.CalledProcessError: If git clone fails
        """
        logger.info(f"Cloning {self.repo_url} to {self.work_dir}")

        # Remove existing directory if present
        if self.work_dir.exists():
            import shutil
            shutil.rmtree(self.work_dir)

        self.work_dir.parent.mkdir(parents=True, exist_ok=True)

        # Clone repository
        subprocess.run(
            ["git", "clone", self.auth_url, str(self.work_dir)],
            check=True,
            capture_output=True,
            text=True
        )

        # Configure git user for this repo
        self._run_git(["config", "user.name", self.dog_name])
        self._run_git(["config", "user.email", self.dog_email])

        logger.info(f"Repository cloned successfully to {self.work_dir}")
        return self.work_dir

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """
        Create and checkout a new branch.

        Args:
            branch_name: Name of branch to create
            base_branch: Base branch to branch from (default: main)

        Raises:
            subprocess.CalledProcessError: If git operations fail
        """
        logger.info(f"Creating branch {branch_name} from {base_branch}")

        # Ensure we're on base branch
        self._run_git(["checkout", base_branch])

        # Pull latest changes
        self._run_git(["pull", "origin", base_branch])

        # Create and checkout new branch
        self._run_git(["checkout", "-b", branch_name])

        logger.info(f"Branch {branch_name} created successfully")

    def push_branch(self, branch_name: str) -> None:
        """
        Push branch to remote.

        Args:
            branch_name: Name of branch to push

        Raises:
            subprocess.CalledProcessError: If git push fails
        """
        logger.info(f"Pushing branch {branch_name} to remote")

        # Push branch with upstream tracking
        self._run_git(["push", "-u", "origin", branch_name])

        logger.info(f"Branch {branch_name} pushed successfully")

    def commit_changes(self, message: str) -> bool:
        """
        Commit any pending changes.

        Args:
            message: Commit message

        Returns:
            True if changes were committed, False if no changes

        Raises:
            subprocess.CalledProcessError: If git operations fail
        """
        # Check if there are changes to commit
        status = self._run_git(["status", "--porcelain"])
        if not status.stdout.strip():
            logger.info("No changes to commit")
            return False

        # Add all changes
        self._run_git(["add", "."])

        # Commit with AI attribution
        # Primary author is already set via git config (dog_name/dog_email)
        commit_message = f"""{message}

🤖 Generated with [Dogwalker](https://dogwalker.dev)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        self._run_git(["commit", "-m", commit_message])

        logger.info(f"Changes committed: {message}")
        return True

    def get_modified_files(self, base_branch: str = "main") -> list[str]:
        """
        Get list of files modified in current branch compared to base branch.

        Args:
            base_branch: Base branch to compare against (default: main)

        Returns:
            List of file paths that were modified (excludes .gitkeep)
        """
        # Get all files changed between base branch and current HEAD
        # Using three-dot syntax to get changes on current branch only
        result = self._run_git(["diff", "--name-only", f"origin/{base_branch}...HEAD"])
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Filter out .gitkeep (implementation detail, not relevant to PR viewer)
        files = [f for f in files if f and f != ".gitkeep"]

        return files

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess:
        """
        Run a git command in the repo directory.

        Args:
            args: Git command arguments (e.g., ["status", "--porcelain"])

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        return subprocess.run(
            ["git"] + args,
            cwd=self.work_dir,
            check=True,
            capture_output=True,
            text=True
        )
