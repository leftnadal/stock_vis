from django.urls import path

from .views import CreditSignalStripView

app_name = "credit_signals"

urlpatterns = [
    path("strip/", CreditSignalStripView.as_view(), name="strip"),
]
