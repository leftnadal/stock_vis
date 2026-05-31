from django.apps import AppConfig


class SecPipelineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.sec_pipeline"
    label = "sec_pipeline"

    def ready(self):
        import services.sec_pipeline.signals  # noqa: F401
