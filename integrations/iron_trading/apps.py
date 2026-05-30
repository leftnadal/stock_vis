from django.apps import AppConfig


class IronTradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations.iron_trading"
    label = "iron_trading"
    verbose_name = "Iron Trading Read-only API"
