from celery.schedules import crontab

beat_schedule = {
    "delete-expired-tokens-every-hour": {
        "task": "tasks.cleanup.delete_expired_tokens",
        "schedule": crontab(minute=0, hour="*"),
    },
}
