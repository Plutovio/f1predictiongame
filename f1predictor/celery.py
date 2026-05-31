import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'f1predictor.settings.development')

app = Celery('f1predictor')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat schedule for automatic F1 data syncing
app.conf.beat_schedule = {
    'sync-f1-schedule-daily': {
        'task': 'core.tasks.sync_season_schedule',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM UTC
        'args': (2026,),
    },
    'sync-f1-results-hourly': {
        'task': 'core.tasks.sync_latest_results',
        'schedule': crontab(minute=0),  # Every hour
    },
    'sync-standings-daily': {
        'task': 'core.tasks.sync_standings',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM UTC
        'args': (2026,),
    },
    'lock-predictions': {
        'task': 'core.tasks.lock_expired_predictions',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'score-predictions-after-race': {
        'task': 'core.tasks.score_all_pending',
        'schedule': crontab(hour='*/2', minute=30),  # Every 2 hours at :30
    },
}
