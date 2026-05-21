"""Portfolio Coach URL routes."""

from __future__ import annotations

from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    # Slice 13 #65 pilot: coach/e1/garp/ 및 view 제거. 단일화된 E1 진입점은
    # /api/v1/coach/e1/ (portfolio/api/urls.py).
    path("coach/e5/adjustment/", views.coach_e5_adjustment, name="coach_e5_adjustment"),
    path(
        "coach/e2/diagnostic-card/",
        views.coach_e2_diagnostic_card,
        name="coach_e2_diagnostic_card",
    ),
    path(
        "coach/e6/comparison/",
        views.coach_e6_comparison,
        name="coach_e6_comparison",
    ),
    path(
        "coach/e3/metric-comment/",
        views.coach_e3_metric_comment,
        name="coach_e3_metric_comment",
    ),
]
