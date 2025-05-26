from django.urls import path
from . import views
from . import api_views

app_name = 'stocks'

urlpatterns = [
    # Existing URL patterns
    path('', views.StockList.as_view(), name='stock_list'),
    path('<int:pk>/', views.StockDetail.as_view(), name='stock_detail'),
    path('<int:stock_id>/prices/', views.StockPriceHistory.as_view(), name='price_history'),
    path('<int:stock_id>/balance-sheet/', views.StockBalanceSheet.as_view(), name='balance_sheet'),
    path('<int:stock_id>/income-statement/', views.StockIncomeStatement.as_view(), name='income_statement'),
    path('<int:stock_id>/cash-flow/', views.StockCashFlow.as_view(), name='cash_flow'),
    
    # Alpha Vantage data update API
    path('api/update-data/', api_views.StockDataUpdateView.as_view(), name='update_stock_data'),
]
