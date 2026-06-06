"""
URL routing (PR-I/J).

소속: apps/market_pulse/api (app 레이어 REST API).
역할: `/api/v1/marketpulse/*` URL → views/* 라우팅 단일 진입점. config/urls.py에서
  include로 마운트(reverse('macro:...')는 옛 macro v1 호환 — namespace 보존).
주요 엔드포인트: overview / card detail (4종) / news refresh / health / i18n.
"""

from __future__ import annotations

from django.urls import path

from apps.market_pulse.api.views.cards import CardDetailView
from apps.market_pulse.api.views.health import HealthView
from apps.market_pulse.api.views.i18n import I18nView
from apps.market_pulse.api.views.news_refresh import NewsRefreshView
from apps.market_pulse.api.views.overview import OverviewView

app_name = "marketpulse_api_v2"


urlpatterns = [
    path("overview", OverviewView.as_view(), name="overview"),
    path("cards/<str:card_id>/detail", CardDetailView.as_view(), name="card-detail"),
    path("news/refresh", NewsRefreshView.as_view(), name="news-refresh"),
    path("i18n", I18nView.as_view(), name="i18n"),
    path("health", HealthView.as_view(), name="health"),
]
