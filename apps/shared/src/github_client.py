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
        base_branch: str = "main",
        draft: bool = False,
        assignee: Optional[str] = None
    ) -> Optional[dict]:
        """
        Create a GitHub pull request.

        Args:
            branch_name: Source branch name
            title: PR title
            body: PR description
            base_branch: Target branch (default: main)
            draft: Create as draft PR (default: False)
            assignee: GitHub username to assign PR to (optional)

        Returns:
            Dictionary with pr_url and pr_number on success, None on failure
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
                draft=draft,
            )

            # Add assignee if provided
            if assignee:
                try:
                    pr.add_to_assignees(assignee)
                    logger.info(f"Assigned PR #{pr.number} to {assignee}")
                except GithubException as e:
                    logger.warning(f"Could not assign PR to {assignee}: {e.status} - {e.data}")
                    # Don't fail PR creation if assignment fails

            logger.info(f"Created {'draft ' if draft else ''}PR #{pr.number}: {pr.html_url}")
            return {
                "pr_url": pr.html_url,
                "pr_number": pr.number,
                "pr_title": pr.title,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e.status} - {e.data}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error creating PR: {e}")
            return None

    def update_pull_request(
        self,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> bool:
        """
        Update an existing pull request.

        Args:
            pr_number: PR number to update
            title: New title (optional)
            body: New description (optional)

        Returns:
            True on success, False on failure
        """
        try:
            pr = self.repo.get_pull(pr_number)

            # Build update parameters (only include non-None values)
            update_params = {}
            if title is not None:
                update_params["title"] = title
            if body is not None:
                update_params["body"] = body

            # Make a single API call to update the PR (replaces entire description)
            if update_params:
                pr.edit(**update_params)
                logger.info(f"Updated PR #{pr_number}")
            else:
                logger.warning(f"No updates provided for PR #{pr_number}")

            return True

        except GithubException as e:
            logger.error(f"GitHub API error updating PR: {e.status} - {e.data}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error updating PR: {e}")
            return False

    def mark_pr_ready(self, pr_number: int) -> bool:
        """
        Mark a draft PR as ready for review.

        Args:
            pr_number: PR number to mark ready

        Returns:
            True on success, False on failure
        """
        try:
            pr = self.repo.get_pull(pr_number)

            # Mark as ready by editing the PR to set draft=False
            # Note: PyGithub doesn't directly support this via REST API
            # We need to use the GraphQL API, but for now we'll use edit
            # This requires the PR to already be in draft state

            # Using GraphQL through PyGithub
            mutation = """
            mutation MarkPullRequestReadyForReview($pullRequestId: ID!) {
              markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
                pullRequest {
                  id
                  isDraft
                }
              }
            }
            """

            # Get the PR's GraphQL node ID
            pr_node_id = pr.raw_data.get("node_id")

            if pr_node_id:
                # Execute GraphQL mutation
                headers = {"Authorization": f"token {self.github._Github__requester.auth.token}"}
                import requests
                response = requests.post(
                    "https://api.github.com/graphql",
                    headers=headers,
                    json={
                        "query": mutation,
                        "variables": {"pullRequestId": pr_node_id}
                    }
                )

                if response.status_code == 200:
                    logger.info(f"Marked PR #{pr_number} as ready for review")
                    return True
                else:
                    logger.error(f"GraphQL API error: {response.status_code} - {response.text}")
                    return False
            else:
                logger.error("Could not get PR node ID")
                return False

        except GithubException as e:
            logger.error(f"GitHub API error marking PR ready: {e.status} - {e.data}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error marking PR ready: {e}")
            return False

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
