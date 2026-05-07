"""Portfolio Coach URL routes."""

from __future__ import annotations

from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    path("coach/e1/garp/", views.coach_e1_garp, name="coach_e1_garp"),
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
]
