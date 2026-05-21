"""Slice 13 Part 1 — DRF coach API 라우팅.

새 경로 prefix: `/api/coach/`. 기존 `portfolio/urls.py`의 `coach/e1/garp/` 등과 별개.
"""

from __future__ import annotations

from django.urls import path

from portfolio.api import views

app_name = "portfolio_api"

urlpatterns = [
    path("coach/e1/", views.coach_e1, name="coach_e1"),
]
