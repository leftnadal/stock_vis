"""Monitor API 라우팅 (api/v1/monitor/, MON-P2-S3 · P3-S2 catalog)."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.monitor.api.views import (
    AlertEventViewSet,
    ClaimViewSet,
    IndicatorCatalogView,
    IndicatorReadingViewSet,
    MonitorIndicatorViewSet,
    MonitorViewSet,
    ScenarioSuggestView,
)

router = DefaultRouter()
router.register(r"monitors", MonitorViewSet, basename="monitor")
router.register(r"indicators", MonitorIndicatorViewSet, basename="monitor-indicator")
router.register(r"readings", IndicatorReadingViewSet, basename="indicator-reading")
router.register(r"claims", ClaimViewSet, basename="claim")
router.register(r"alerts", AlertEventViewSet, basename="alert")

urlpatterns = [
    path("catalog/", IndicatorCatalogView.as_view(), name="monitor-catalog"),
    path("scenario-suggest/", ScenarioSuggestView.as_view(), name="monitor-scenario-suggest"),
    *router.urls,
]
