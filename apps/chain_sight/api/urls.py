from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.chain_sight.views.watchlist_views import WatchlistViewSet

from .centrality_views import CentralityTopView
from .ego_views import EgoGraphView
from .event_views import EventBoardView, EventRankingView
from .heat_views import ThemeHeatBarView, ThemeHeatCardView
from .mindmap_views import MindmapCardView, MindmapTreeView
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
    # PG 네이티브 ego 그래프 (⑰ S1-b, Neo4j 무의존) — 고정 프리픽스 ego/ 로 동적 경로와 분리
    path("ego/<str:symbol>/", EgoGraphView.as_view(), name="chainsight-ego"),
    # 중심성 상위 조회 (⑲ S3, S-C — 화면 노출은 ⑳)
    path("centrality/top/", CentralityTopView.as_view(), name="chainsight-centrality-top"),
    # CS-P5 마인드맵 카드 (D1·D-CARD-GATE, 고정 프리픽스 — 동적 symbol 경로와 분리)
    path("mindmap/tree/", MindmapTreeView.as_view(), name="chainsight-mindmap-tree"),
    path("mindmap/card/<str:symbol>/", MindmapCardView.as_view(), name="chainsight-mindmap-card"),
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
