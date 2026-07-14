from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.chain_sight.views.watchlist_views import WatchlistViewSet

from .ego_views import EgoGraphView
from .event_views import EventBoardView, EventRankingView
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
    # 마켓 뷰 (고정 경로 먼저)
    path("seeds/", SeedListView.as_view(), name="chainsight-seeds"),
    path(
        "sector/<str:sector>/graph/",
        SectorGraphView.as_view(),
        name="chainsight-sector-graph",
    ),
    path("signals/", SignalFeedView.as_view(), name="chainsight-signals"),
    path("trace/", ChainSightTraceView.as_view(), name="chainsight-trace"),
    # PG 네이티브 ego 그래프 (⑰ S1-b, Neo4j 무의존) — 고정 프리픽스 ego/ 로 동적 경로와 분리
    path("ego/<str:symbol>/", EgoGraphView.as_view(), name="chainsight-ego"),
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
