from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'F1 Predictor Core'

    def ready(self):
        import core.models  # noqa: F401 - Ensure signals are registered
