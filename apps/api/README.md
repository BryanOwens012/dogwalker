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

## MVP Approach

For initial MVP (Weeks 1-3), use Slack bot only:
- Slack provides UI for free
- No need to build auth/frontend
- Faster to ship

Add API later when:
- Have paying customers needing programmatic access
- Want to support non-Slack workflows
- Need public-facing task monitoring

## Development Timeline

- **Week 1-3:** MVP with Slack only (skip API)
- **Week 4-6:** If traction, add basic HTTP endpoints
- **Month 2-3:** Add web dashboard if needed
- **Month 3+:** Full-featured API based on customer needs

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

- Don't build this until you have validated demand
- Slack bot is sufficient for MVP
- Focus on core value (code generation quality) first
