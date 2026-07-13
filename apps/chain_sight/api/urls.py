from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.chain_sight.views.watchlist_views import WatchlistViewSet

from .event_views import EventBoardView, EventRankingView
from .heat_views import ThemeHeatBarView, ThemeHeatCardView
from .views import (
    ChainSightGraphView,
    ChainSightSuggestionView,
    ChainSightTraceView,
    NeighborGraphView,
    SectorGraphView,
    SeedListView,
    SignalFeedView,
)

router = DefaultRouter()
router.register(r"watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = [
    # 관심도 이벤트 보드 (CS-RD2)
    path("events/", EventBoardView.as_view(), name="chainsight-events"),
    path("events/<str:theme>/stocks/", EventRankingView.as_view(), name="chainsight-event-ranking"),
    # Theme Heat API (TH-15, 고정 경로 — 동적 symbol 경로보다 먼저)
    path("theme-heat/", ThemeHeatBarView.as_view(), name="chainsight-theme-heat-bar"),
    path("theme-heat/<str:theme>/", ThemeHeatCardView.as_view(), name="chainsight-theme-heat-card"),
    # 마켓 뷰 (고정 경로 먼저)
    path("seeds/", SeedListView.as_view(), name="chainsight-seeds"),
    path(
        "sector/<str:sector>/graph/",
        SectorGraphView.as_view(),
        name="chainsight-sector-graph",
    ),
    path("signals/", SignalFeedView.as_view(), name="chainsight-signals"),
    path("trace/", ChainSightTraceView.as_view(), name="chainsight-trace"),
    # 동적 경로 (symbol 기반)
    path(
        "<str:symbol>/neighbors/",
        NeighborGraphView.as_view(),
        name="chainsight-neighbors",
    ),
    path("<str:symbol>/graph/", ChainSightGraphView.as_view(), name="chainsight-graph"),
    path(
        "<str:symbol>/suggestions/",
        ChainSightSuggestionView.as_view(),
        name="chainsight-suggestions",
    ),
] + router.urls
