from django.urls import path, include
from rest_framework.routers import DefaultRouter

from thesis.views import (
    ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet,
    ConversationStartView, ConversationRespondView,
    DashboardView, AlertListView, AlertReadView,
)

router = DefaultRouter()
router.register('', ThesisViewSet, basename='thesis')

# Nested routers for premises and indicators
premise_router = DefaultRouter()
premise_router.register('', ThesisPremiseViewSet, basename='premise')

indicator_router = DefaultRouter()
indicator_router.register('', ThesisIndicatorViewSet, basename='indicator')

urlpatterns = [
    # Conversation
    path('conversation/start/', ConversationStartView.as_view(), name='conversation-start'),
    path('conversation/respond/', ConversationRespondView.as_view(), name='conversation-respond'),

    # Monitoring
    path('<uuid:thesis_id>/dashboard/', DashboardView.as_view(), name='thesis-dashboard'),

    # Alerts
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<uuid:aid>/read/', AlertReadView.as_view(), name='alert-read'),

    # Nested: premises and indicators
    path('<uuid:thesis_id>/premises/', include((premise_router.urls, 'premise'))),
    path('<uuid:thesis_id>/indicators/', include((indicator_router.urls, 'indicator'))),

    # Main router (must be last)
    path('', include(router.urls)),
]
