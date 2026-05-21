"""Slice 13 Part 1+ — DRF coach API 라우팅.

최종 노출 경로 prefix: `/api/v1/coach/` (Slice 13 Part 1.5에서 v1 도입).
기존 순수 view 라우팅 (`/api/coach/e1/garp/` 등, `portfolio/urls.py`)과 별개 경로.

향후 확장 (Part 2~6): E2~E6 endpoint를 본 urlpatterns에 동일 패턴으로 추가.
도메인 그룹핑 필요 시 `/api/v1/{domain}/` 로 확장 가능 (config/urls.py 측 결정).
"""

from __future__ import annotations

from django.urls import path

from portfolio.api import views

app_name = "portfolio_api"

urlpatterns = [
    path("coach/e1/", views.coach_e1, name="coach_e1"),
    path("coach/e2/", views.coach_e2, name="coach_e2"),
    # Part 3~: coach/e3/, coach/e4/, coach/e5/, coach/e6/ 추가 예정
]
