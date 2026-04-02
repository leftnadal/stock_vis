from django.urls import path
from .views import ChainSightGraphView, ChainSightSuggestionView, ChainSightTraceView

urlpatterns = [
    path('<str:symbol>/graph/', ChainSightGraphView.as_view(), name='chainsight-graph'),
    path('<str:symbol>/suggestions/', ChainSightSuggestionView.as_view(), name='chainsight-suggestions'),
    path('trace/', ChainSightTraceView.as_view(), name='chainsight-trace'),
]
