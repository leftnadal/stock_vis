from django.apps import AppConfig


class AlertingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "packages.shared.alerting"
    label = "alerting"
    verbose_name = "Alerting"

    def ready(self) -> None:
        # 내장 email delivery provider 등록(shared→shared, 앱 무지 유지).
        from packages.shared.alerting.delivery.base import register_provider
        from packages.shared.alerting.delivery.email import EmailProvider

        register_provider("email", EmailProvider())
