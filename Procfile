web: gunicorn f1predictor.wsgi --log-file -
worker: celery -A f1predictor worker --loglevel=info
beat: celery -A f1predictor beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
