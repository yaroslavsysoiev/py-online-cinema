from celery import Celery

celery_app = Celery('myapp', broker='redis://redis:6379/0')
celery_app.config_from_object('config.celeryconfig')

from config.celeryconfig import beat_schedule
celery_app.conf.beat_schedule = beat_schedule
