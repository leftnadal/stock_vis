from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('dashboard/', views.AnalysisDashboard.as_view(), name='dashboard'),
    path('indicators/', views.EconomicIndicatorList.as_view(), name='indicators'),
    path('indicators/<int:pk>/', views.EconomicIndicatorDetail.as_view(), name='indicator_detail'),
    path('indicators/history/<str:indicator_name>/', views.IndicatorHistory.as_view(), name='indicator_history'),
    path('market-trends/', views.MarketTrends.as_view(), name='market_trends'),
    path('stock-comparison/', views.StockComparison.as_view(), name='stock_comparison'),
]