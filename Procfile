# Procfile for Railway deployment
# Defines process types for different services

# Web process - Slack bot (orchestrator)
web: cd apps/orchestrator && python src/bot.py

# Worker process - Celery worker (dog)
worker: cd apps/worker && celery -A src.celery_app worker --loglevel=info

# Beat process - Celery Beat scheduler (periodic tasks)
beat: cd apps/worker && celery -A src.celery_app beat --loglevel=info
