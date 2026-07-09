from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """dashboard 트랙 표면 전용 BFF 앱 (D-DASH-BFF). 모델 없음 — read 응축 통로."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Dashboard BFF"
