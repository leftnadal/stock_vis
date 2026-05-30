from django.urls import path

from . import views

app_name = 'sec_pipeline'

urlpatterns = [
    path('admin/dashboard/', views.sec_pipeline_dashboard, name='dashboard'),
    path('filing/<str:symbol>/', views.FilingDataView.as_view(), name='filing-data'),
]
