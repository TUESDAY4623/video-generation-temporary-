"""Celery beat schedule for periodic tasks."""

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cleanup-old-files": {
        "task": "workers.tasks.cleanup_old_files",
        "schedule": crontab(hour=3, minute=0),
    },
    "health-check-services": {
        "task": "workers.tasks.health_check_services",
        "schedule": crontab(minute="*/5"),
    },
}
