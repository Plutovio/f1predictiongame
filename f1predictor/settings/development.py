"""
Development settings for F1 Predictor.
Uses SQLite, debug mode enabled.
"""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Disable whitenoise manifest in dev to avoid collectstatic requirement
STORAGES = {
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Additional dev apps (uncomment if installed)
# INSTALLED_APPS += [  # noqa: F405
#     'django_browser_reload',
# ]

# MIDDLEWARE += [  # noqa: F405
#     'django_browser_reload.middleware.BrowserReloadMiddleware',
# ]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Celery - use database as broker fallback if Redis not available
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = True  # Set True if you don't want to run a worker

print("F1 Predictor -- Development Mode")
