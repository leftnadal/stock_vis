from django.urls import path
from .views import (
    ChainSightGraphView, ChainSightSuggestionView, ChainSightTraceView,
    SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView,
)

urlpatterns = [
    # 마켓 뷰 (고정 경로 먼저)
    path('seeds/', SeedListView.as_view(), name='chainsight-seeds'),
    path('sector/<str:sector>/graph/', SectorGraphView.as_view(), name='chainsight-sector-graph'),
    path('signals/', SignalFeedView.as_view(), name='chainsight-signals'),
    path('trace/', ChainSightTraceView.as_view(), name='chainsight-trace'),

    # 동적 경로 (symbol 기반)
    path('<str:symbol>/neighbors/', NeighborGraphView.as_view(), name='chainsight-neighbors'),
    path('<str:symbol>/graph/', ChainSightGraphView.as_view(), name='chainsight-graph'),
    path('<str:symbol>/suggestions/', ChainSightSuggestionView.as_view(), name='chainsight-suggestions'),
]
