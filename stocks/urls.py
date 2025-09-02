from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    # 메인 페이지들
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('stock/<str:symbol>/', views.StockDetailView.as_view(), name='stock_detail'),
    path('search/', views.StockSearchAPIView.as_view(), name='stock_search'),
    
    # API 엔드포인트들 - 각 탭별로 분리
    path('api/chart/<str:symbol>/', views.StockChartDataAPIView.as_view(), name='stock_chart_data'),
    path('api/overview/<str:symbol>/', views.StockOverviewAPIView.as_view(), name='stock_overview_data'),
    path('api/balance-sheet/<str:symbol>/', views.StockBalanceSheetAPIView.as_view(), name='stock_balance_sheet_data'),
    path('api/income-statement/<str:symbol>/', views.StockIncomeStatementAPIView.as_view(), name='stock_income_statement_data'),
    path('api/cashflow/<str:symbol>/', views.StockCashFlowAPIView.as_view(), name='stock_cashflow_data'),
]