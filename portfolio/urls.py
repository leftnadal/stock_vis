"""Portfolio Coach URL routes."""

from __future__ import annotations

from django.urls import path

from portfolio import views

app_name = "portfolio"

urlpatterns = [
    path("coach/e1/garp/", views.coach_e1_garp, name="coach_e1_garp"),
]
