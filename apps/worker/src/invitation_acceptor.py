"""Automatic GitHub invitation acceptor for dog accounts."""

from celery_app import app
import logging
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))

from config import config
from github_client import GitHubClient

logger = logging.getLogger(__name__)


@app.task(name="invitation_acceptor.accept_pending_invitations")
def accept_pending_invitations():
    """
    Periodic task to check and accept GitHub repository invitations for all dogs.

    This task runs every 5 minutes via Celery Beat and:
    1. Iterates through all configured dogs
    2. Checks each dog's pending GitHub repository invitations
    3. Automatically accepts any pending invitations
    4. Logs all acceptances for audit trail

    Returns:
        Dictionary with summary statistics
    """
    logger.info("🔍 Checking GitHub invitations for all dogs...")

    total_checked = 0
    total_accepted = 0
    total_failed = 0

    try:
        # Get all configured dogs
        dogs = config.dogs

        if not dogs:
            logger.warning("No dogs configured - skipping invitation check")
            return {
                "status": "skipped",
                "reason": "no_dogs_configured"
            }

        logger.info(f"Checking invitations for {len(dogs)} dog(s)")

        # Check each dog for pending invitations
        for dog in dogs:
            dog_name = dog.get("name", "Unknown")
            dog_token = dog.get("github_token")

            if not dog_token:
                logger.warning(f"Dog {dog_name} has no GitHub token - skipping")
                continue

            total_checked += 1

            try:
                # Create GitHub client for this dog
                # Note: We need a repo_name for GitHubClient, but we only use methods
                # that don't need it (invitations are user-level, not repo-level)
                # So we pass a dummy repo name
                github_client = GitHubClient(
                    token=dog_token,
                    repo_name="dummy/dummy"  # Not used for invitation methods
                )

                # Get pending invitations
                invitations = github_client.get_pending_invitations()

                if not invitations:
                    logger.debug(f"✅ No pending invitations for {dog_name}")
                    continue

                logger.info(f"📬 Found {len(invitations)} pending invitation(s) for {dog_name}")

                # Accept each invitation
                for invitation in invitations:
                    invitation_id = invitation.get("id")
                    repo_name = invitation.get("repository", {}).get("full_name", "unknown")
                    inviter = invitation.get("inviter", {}).get("login", "unknown")

                    logger.info(f"🤝 Accepting invitation for {dog_name} to {repo_name} from {inviter}")

                    if github_client.accept_invitation(invitation_id):
                        total_accepted += 1
                        logger.info(f"✅ {dog_name} accepted invitation to {repo_name}")
                    else:
                        total_failed += 1
                        logger.error(f"❌ Failed to accept invitation for {dog_name} to {repo_name}")

            except Exception as e:
                logger.exception(f"Error checking invitations for {dog_name}: {e}")
                total_failed += 1
                continue

        # Log summary
        logger.info(f"📊 Invitation check complete: {total_checked} dog(s) checked, "
                   f"{total_accepted} invitation(s) accepted, {total_failed} failure(s)")

        return {
            "status": "success",
            "dogs_checked": total_checked,
            "invitations_accepted": total_accepted,
            "failures": total_failed
        }

    except Exception as e:
        logger.exception(f"Failed to check invitations: {e}")
        return {
            "status": "error",
            "error": str(e),
            "dogs_checked": total_checked,
            "invitations_accepted": total_accepted,
            "failures": total_failed
        }
