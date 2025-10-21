"""GitHub API client for Dogwalker."""

from typing import Optional
from github import Github, GithubException
import logging

logger = logging.getLogger(__name__)


class GitHubClient:
    """Wrapper for GitHub API operations."""

    def __init__(self, token: str, repo_name: str):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            repo_name: Repository name (format: owner/repo)
        """
        self.github = Github(token)
        self.repo_name = repo_name
        self._repo = None

    @property
    def repo(self):
        """Get repository object (cached)."""
        if self._repo is None:
            try:
                self._repo = self.github.get_repo(self.repo_name)
            except GithubException as e:
                logger.error(f"Failed to get repo {self.repo_name}: {e.status} - {e.data}")
                raise
        return self._repo

    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a GitHub pull request.

        Args:
            branch_name: Source branch name
            title: PR title
            body: PR description
            base_branch: Target branch (default: main)

        Returns:
            PR URL on success, None on failure
        """
        try:
            # Verify branch exists
            try:
                self.repo.get_branch(branch_name)
            except GithubException:
                logger.error(f"Branch {branch_name} not found in {self.repo_name}")
                return None

            # Create PR
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=base_branch,
            )

            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            return pr.html_url

        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e.status} - {e.data}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error creating PR: {e}")
            return None

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch exists.

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch exists, False otherwise
        """
        try:
            self.repo.get_branch(branch_name)
            return True
        except GithubException:
            return False

    def get_default_branch(self) -> str:
        """
        Get the default branch name.

        Returns:
            Default branch name (e.g., 'main' or 'master')
        """
        return self.repo.default_branch
