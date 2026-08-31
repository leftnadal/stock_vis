from django.urls import path

from apps.dashboard.api.views import EventStripView, NewsStripView

app_name = "dashboard"

urlpatterns = [
    path("news-strip/", NewsStripView.as_view(), name="news-strip"),
    path("event-strip/", EventStripView.as_view(), name="event-strip"),
]
