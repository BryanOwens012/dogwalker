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
        self.token = token
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
                headers = {"Authorization": f"token {self.token}"}
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

    def upload_image_to_github(
        self,
        image_path: str,
        screenshot_filename: str
    ) -> Optional[str]:
        """
        Upload an image to GitHub screenshots branch and get a permanent URL.

        Uploads to a dedicated 'dogwalker-screenshots' branch and returns a
        GitHub blob URL that works for both public and private repos.

        Args:
            image_path: Path to the image file
            screenshot_filename: Filename to use in the screenshots branch

        Returns:
            Permanent GitHub blob URL, or None on failure
        """
        try:
            from pathlib import Path

            image_file = Path(image_path)
            if not image_file.exists():
                logger.error(f"Image file not found: {image_path}")
                return None

            # Read image data (PyGithub will handle base64 encoding)
            with open(image_file, 'rb') as f:
                image_data = f.read()

            screenshots_branch = "dogwalker-screenshots"
            screenshot_path = screenshot_filename  # Store in root of screenshots branch

            # Check if screenshots branch exists, create if not
            try:
                branch = self.repo.get_branch(screenshots_branch)
                logger.info(f"✅ Screenshots branch '{screenshots_branch}' exists (SHA: {branch.commit.sha[:7]})")
            except GithubException as e:
                # Create screenshots branch from default branch
                logger.info(f"📝 Creating screenshots branch '{screenshots_branch}' (branch not found)")
                try:
                    default_branch = self.repo.get_branch(self.repo.default_branch)
                    self.repo.create_git_ref(
                        ref=f"refs/heads/{screenshots_branch}",
                        sha=default_branch.commit.sha
                    )
                    logger.info(f"✅ Created screenshots branch '{screenshots_branch}'")
                except GithubException as create_error:
                    logger.error(f"❌ Failed to create screenshots branch: {create_error.status} - {create_error.data}")
                    return None

            # Upload image to screenshots branch
            # Extract and log extension to verify it's preserved
            ext = screenshot_filename.rsplit('.', 1)[-1] if '.' in screenshot_filename else 'unknown'
            logger.info(f"📤 Uploading '{screenshot_path}' to branch '{screenshots_branch}'...")
            logger.info(f"   File extension: .{ext}")
            try:
                existing_file = self.repo.get_contents(screenshot_path, ref=screenshots_branch)
                # Update existing file (PyGithub handles base64 encoding internally)
                result = self.repo.update_file(
                    path=screenshot_path,
                    message=f"Update screenshot: {screenshot_filename}",
                    content=image_data,
                    sha=existing_file.sha,
                    branch=screenshots_branch
                )
                logger.info(f"✅ Updated existing screenshot: {screenshot_path} (commit: {result['commit'].sha[:7]})")
            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist, create it
                    logger.info(f"📝 File doesn't exist, creating new file: {screenshot_path}")
                    try:
                        result = self.repo.create_file(
                            path=screenshot_path,
                            message=f"Add screenshot: {screenshot_filename}",
                            content=image_data,
                            branch=screenshots_branch
                        )
                        logger.info(f"✅ Created new screenshot: {screenshot_path} (commit: {result['commit'].sha[:7]})")
                    except GithubException as create_error:
                        logger.error(f"❌ Failed to create file: {create_error.status} - {create_error.data}")
                        return None
                else:
                    logger.error(f"❌ GitHub API error checking file: {e.status} - {e.data}")
                    return None

            # Generate GitHub blob URL with ?raw=true (works for private repos in PR descriptions)
            blob_url = f"https://github.com/{self.repo_name}/blob/{screenshots_branch}/{screenshot_path}?raw=true"

            logger.info(f"✅ Successfully uploaded image to GitHub")
            logger.info(f"🔗 Blob URL: {blob_url}")
            return blob_url

        except Exception as e:
            logger.exception(f"Failed to upload image to GitHub: {e}")
            return None

    def get_pending_invitations(self) -> list[dict]:
        """
        Get pending repository collaboration invitations for the authenticated user.

        Returns:
            List of invitation dictionaries with:
                - id: Invitation ID (used for acceptance)
                - repository: Dict with full_name, html_url
                - inviter: Dict with login, html_url
                - created_at: Invitation timestamp
        """
        try:
            import requests

            headers = {"Authorization": f"token {self.token}"}
            response = requests.get(
                "https://api.github.com/user/repository_invitations",
                headers=headers
            )

            if response.status_code == 200:
                invitations = response.json()
                logger.debug(f"Found {len(invitations)} pending invitation(s)")
                return invitations
            elif response.status_code == 401:
                logger.error("Authentication failed - check GitHub token permissions")
                return []
            elif response.status_code == 403:
                logger.error("Rate limit exceeded or insufficient permissions")
                return []
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.exception(f"Failed to get pending invitations: {e}")
            return []

    def accept_invitation(self, invitation_id: int) -> bool:
        """
        Accept a repository collaboration invitation.

        Args:
            invitation_id: The invitation ID to accept

        Returns:
            True if invitation was accepted successfully, False otherwise
        """
        try:
            import requests

            headers = {"Authorization": f"token {self.token}"}
            response = requests.patch(
                f"https://api.github.com/user/repository_invitations/{invitation_id}",
                headers=headers
            )

            if response.status_code == 204:
                logger.info(f"Successfully accepted invitation {invitation_id}")
                return True
            elif response.status_code == 404:
                logger.error(f"Invitation {invitation_id} not found or already accepted")
                return False
            elif response.status_code == 403:
                logger.error(f"Permission denied or rate limit exceeded for invitation {invitation_id}")
                return False
            else:
                logger.error(f"Failed to accept invitation {invitation_id}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.exception(f"Failed to accept invitation {invitation_id}: {e}")
            return False
