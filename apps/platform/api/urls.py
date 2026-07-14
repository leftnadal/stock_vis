from django.urls import path

from apps.platform.api.views import ImpressionIngestView

app_name = "platform"

urlpatterns = [
    path("impressions", ImpressionIngestView.as_view(), name="impression-ingest"),
]
