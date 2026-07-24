from django.urls import path

from apps.platform.api.views import CoverageView, ImpressionIngestView

app_name = "platform"

urlpatterns = [
    path("impressions", ImpressionIngestView.as_view(), name="impression-ingest"),
    path("coverage", CoverageView.as_view(), name="coverage"),
]
