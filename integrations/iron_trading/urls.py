from django.urls import path

from .views import DailyContextView

app_name = "iron_trading"

urlpatterns = [
    path("daily-context", DailyContextView.as_view(), name="daily-context"),
    # trailing-slash 허용
    path("daily-context/", DailyContextView.as_view()),
]
