from django.urls import path

from apps.dashboard.api.views import NewsStripView

app_name = "dashboard"

urlpatterns = [
    path("news-strip/", NewsStripView.as_view(), name="news-strip"),
]
