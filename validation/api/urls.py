from django.urls import path
from .views import (
    ValidationSummaryView, ValidationMetricsView, LeaderComparisonView,
    PresetListView, PeerPreferenceView,
)

urlpatterns = [
    path('<str:symbol>/summary/', ValidationSummaryView.as_view(), name='validation-summary'),
    path('<str:symbol>/metrics/', ValidationMetricsView.as_view(), name='validation-metrics'),
    path('<str:symbol>/leader-comparison/', LeaderComparisonView.as_view(), name='validation-leader'),
    path('<str:symbol>/presets/', PresetListView.as_view(), name='validation-presets'),
    path('<str:symbol>/peer-preference/', PeerPreferenceView.as_view(), name='validation-peer-preference'),
]
