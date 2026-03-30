from django.urls import path
from .views import ValidationSummaryView, ValidationMetricsView, LeaderComparisonView

urlpatterns = [
    path('<str:symbol>/summary/', ValidationSummaryView.as_view(), name='validation-summary'),
    path('<str:symbol>/metrics/', ValidationMetricsView.as_view(), name='validation-metrics'),
    path('<str:symbol>/leader-comparison/', LeaderComparisonView.as_view(), name='validation-leader'),
]
