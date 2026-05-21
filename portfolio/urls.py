"""Portfolio Coach URL routes."""

from __future__ import annotations

from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    # Slice 13 #65 pilot: coach/e1/garp/ 및 view 제거. 단일화된 E1 진입점은
    # /api/v1/coach/e1/ (portfolio/api/urls.py).
    # Slice 13 #65: coach/e5/adjustment/ 및 view 제거. 단일화된 E5 진입점은
    # /api/v1/coach/e5/ (portfolio/api/urls.py).
    # Slice 13 #65: coach/e2/diagnostic-card/ 및 view 제거. 단일화된 E2 진입점은
    # /api/v1/coach/e2/ (portfolio/api/urls.py).
    path(
        "coach/e6/comparison/",
        views.coach_e6_comparison,
        name="coach_e6_comparison",
    ),
    # Slice 13 #65: coach/e3/metric-comment/ 및 view 제거. 단일화된 E3 진입점은
    # /api/v1/coach/e3/ (portfolio/api/urls.py).
]
