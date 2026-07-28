from django.apps import AppConfig


class PlatformConfig(AppConfig):
    """제3범주 교차관심 서비스 홈 (D-P2-S2-PLATFORM, 소유권 지도 v2 AMEND-3).

    telemetry·알림·플래그 서빙 등의 중립 홈. 의존은 platform → shared 정방향만.
    모델 없음 — 데이터 모델은 shared(packages/shared/stocks.ImpressionLog)를 소비만 한다.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform"
    label = "platform"
