from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.monitor"
    label = "monitor"
    verbose_name = "Monitor 허브 (개인화 모니터링)"
