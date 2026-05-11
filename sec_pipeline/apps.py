from django.apps import AppConfig


class SecPipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sec_pipeline'

    def ready(self):
        import sec_pipeline.signals  # noqa: F401
