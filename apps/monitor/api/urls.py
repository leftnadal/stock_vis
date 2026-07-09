"""Monitor API 라우팅 (api/v1/monitor/, MON-P2-S3)."""
from rest_framework.routers import DefaultRouter

from apps.monitor.api.views import (
    ClaimViewSet,
    IndicatorReadingViewSet,
    MonitorIndicatorViewSet,
    MonitorViewSet,
)

router = DefaultRouter()
router.register(r"monitors", MonitorViewSet, basename="monitor")
router.register(r"indicators", MonitorIndicatorViewSet, basename="monitor-indicator")
router.register(r"readings", IndicatorReadingViewSet, basename="indicator-reading")
router.register(r"claims", ClaimViewSet, basename="claim")

urlpatterns = router.urls
