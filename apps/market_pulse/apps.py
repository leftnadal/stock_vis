from django.apps import AppConfig


class MarketpulseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.market_pulse"
    label = "marketpulse"
    verbose_name = "Market Pulse v2"

    def ready(self) -> None:
        from apps.market_pulse.services.macro_vix_provider import MacroVIXProvider
        from packages.shared.stocks.services.vix_provider import (
            register_vix_provider,
        )

        register_vix_provider(MacroVIXProvider())
