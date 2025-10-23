# Dogwalker API (Future)

**Status:** Not implemented in MVP

This directory is a placeholder for future HTTP API and web dashboard.

## Planned Features

### HTTP Endpoints
- `GET /tasks` - List all tasks and their status
- `GET /tasks/:id` - Get task details
- `POST /tasks` - Create new task (alternative to Slack)
- `GET /dogs` - List available dogs and their status
- `GET /metrics` - System metrics (cost, success rate, etc.)

### Webhooks
- GitHub webhook receiver for PR events
- Slack webhook for non-Socket Mode deployments

### Web Dashboard
- Real-time task monitoring
- Dog status and availability
- Cost tracking and analytics
- Manual task creation UI
- PR review interface

## Technology Stack (Proposed)

- **Framework:** FastAPI (async, modern, OpenAPI docs)
- **Server:** Uvicorn (ASGI server)
- **Frontend:** React + Next.js (if dashboard needed)
- **Auth:** GitHub OAuth or API keys

## Current Status

Initial implementation focuses on Slack bot:
- Slack provides built-in UI and authentication
- Faster to ship and validate core functionality
- No need to build custom frontend initially

API will be added when:
- Community requests programmatic access
- Users want to support non-Slack workflows (Discord, Teams, etc.)
- Need for public-facing task monitoring emerges

## Development Roadmap

- **Phase 1 (Current):** Slack-only interface
- **Phase 2:** Basic HTTP endpoints for task management
- **Phase 3:** Web dashboard for monitoring and analytics
- **Phase 4:** Full REST API with webhook support

Community contributions welcome at any phase!

## Quick Start (Future)

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.server:app --reload

# Access API docs
open http://localhost:8000/docs
```

## Notes

- Slack bot is sufficient for current needs
- API will be built based on community feedback and use cases
- Focus remains on core value: high-quality code generation
- Contributions welcome - if you need API features, please open an issue or PR!
