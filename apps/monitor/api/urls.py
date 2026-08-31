"""Monitor API 라우팅 (api/v1/monitor/, MON-P2-S3 · P3-S2 catalog)."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.monitor.api.calendar_views import CalendarFeedView
from apps.monitor.api.views import (
    AlertEventViewSet,
    ClaimEvidenceViewSet,
    ClaimViewSet,
    DecisionJournalEntryViewSet,
    IndicatorCatalogView,
    IndicatorReadingViewSet,
    MonitorIndicatorViewSet,
    MonitorViewSet,
    ScenarioSuggestView,
    SwapHoldLogViewSet,
)

router = DefaultRouter()
router.register(r"monitors", MonitorViewSet, basename="monitor")
router.register(r"indicators", MonitorIndicatorViewSet, basename="monitor-indicator")
router.register(r"readings", IndicatorReadingViewSet, basename="indicator-reading")
router.register(r"claims", ClaimViewSet, basename="claim")
router.register(r"claim-evidences", ClaimEvidenceViewSet, basename="claim-evidence")
router.register(r"swap-hold-logs", SwapHoldLogViewSet, basename="swap-hold-log")
router.register(
    r"decision-journal-entries", DecisionJournalEntryViewSet, basename="decision-journal-entry"
)
router.register(r"alerts", AlertEventViewSet, basename="alert")

urlpatterns = [
    path("catalog/", IndicatorCatalogView.as_view(), name="monitor-catalog"),
    path("scenario-suggest/", ScenarioSuggestView.as_view(), name="monitor-scenario-suggest"),
    path("calendar/", CalendarFeedView.as_view(), name="monitor-calendar"),
    *router.urls,
]
