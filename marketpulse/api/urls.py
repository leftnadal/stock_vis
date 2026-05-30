"""Market Pulse v2 URL routing (PR-I/J)."""
from __future__ import annotations

from django.urls import path

from marketpulse.api.views.cards import CardDetailView
from marketpulse.api.views.health import HealthView
from marketpulse.api.views.i18n import I18nView
from marketpulse.api.views.news_refresh import NewsRefreshView
from marketpulse.api.views.overview import OverviewView

app_name = 'marketpulse_api_v2'


urlpatterns = [
    path('overview', OverviewView.as_view(), name='overview'),
    path('cards/<str:card_id>/detail', CardDetailView.as_view(), name='card-detail'),
    path('news/refresh', NewsRefreshView.as_view(), name='news-refresh'),
    path('i18n', I18nView.as_view(), name='i18n'),
    path('health', HealthView.as_view(), name='health'),
]
