"""Validate environment variables are properly configured."""

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "shared" / "src"))

try:
    from config import Config

    print("Validating environment configuration...")
    print()

    config = Config()

    # Check all required variables
    checks = [
        ("ANTHROPIC_API_KEY", config.anthropic_api_key, "starts with 'sk-ant-'"),
        ("GITHUB_TOKEN", config.github_token, "starts with 'ghp_' or 'github_pat_'"),
        ("SLACK_BOT_TOKEN", config.slack_bot_token, "starts with 'xoxb-'"),
        ("SLACK_APP_TOKEN", config.slack_app_token, "starts with 'xapp-'"),
        ("REDIS_URL", config.redis_url, "redis://..."),
        ("GITHUB_REPO", config.github_repo, "owner/repo format"),
    ]

    all_valid = True

    for name, value, expected_format in checks:
        if value:
            print(f"✅ {name}: {value[:20]}...")
        else:
            print(f"❌ {name}: MISSING")
            all_valid = False

    print()
    print("Optional variables:")
    print(f"  DOG_NAME: {config.dog_name}")
    print(f"  DOG_EMAIL: {config.dog_email}")
    print(f"  BASE_BRANCH: {config.base_branch}")
    print()

    if all_valid:
        print("✅ All required environment variables are set!")
        print()
        print("Next steps:")
        print("  1. Start Redis: redis-server")
        print("  2. Start orchestrator: cd apps/orchestrator && python src/bot.py")
        print("  3. Start worker: cd apps/worker && celery -A src.celery_app worker --loglevel=info")
    else:
        print("❌ Some required environment variables are missing.")
        print("Please check your .env file and ensure all required values are set.")
        sys.exit(1)

except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print()
    print("Please ensure your .env file contains all required variables.")
    print("See .env.example for a template.")
    sys.exit(1)

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
