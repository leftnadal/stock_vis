from django.urls import path

from .views import DailyContextView, LatestTradingDateView

app_name = "iron_trading"

urlpatterns = [
    path("daily-context", DailyContextView.as_view(), name="daily-context"),
    # trailing-slash 허용
    path("daily-context/", DailyContextView.as_view()),
    path(
        "latest-trading-date",
        LatestTradingDateView.as_view(),
        name="latest-trading-date",
    ),
    path("latest-trading-date/", LatestTradingDateView.as_view()),
]
