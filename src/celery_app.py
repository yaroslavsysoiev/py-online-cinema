from celery import Celery

celery_app = Celery('myapp')
celery_app.config_from_object('config.celery')

celery_app.conf.beat_schedule = {
    'cleanup-expired-tokens-every-hour': {
        'task': 'tasks.cleanup.cleanup_expired_tokens',
        'schedule': 3600,  # каждый час
    },
}
