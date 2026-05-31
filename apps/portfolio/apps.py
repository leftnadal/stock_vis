from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolio"
    verbose_name = "Portfolio Coach"

    def ready(self) -> None:
        # drf-spectacular 확장 등록 (coach serializer ↔ Pydantic 브릿지).
        # import만으로 OpenApiSerializerExtension 12개가 자동 등록된다.
        from portfolio.api import openapi_extensions  # noqa: F401
