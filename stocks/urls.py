from django.urls import path
from . import views
from . import views_mvp  # MVP용 뷰 추가

app_name = 'stocks'

urlpatterns = [
    ## 메인 페이지들
    # 대시보드 페이지 (시가총액 상위 주식 등)
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # 개별 주식 상세 페이지 (헤더, 차트, 탭 메뉴 포함)
    path('stock/<str:symbol>/', views.StockDetailView.as_view(), name='stock_detail'),
    
    # 주식 검색 API (자동완성용)
    path('search/', views.StockSearchAPIView.as_view(), name='stock_search'),
    
    ## API 엔드포인트들 - 각 탭별로 분리
    # 차트 데이터 API (일간/주간, 다양한 기간 옵션)
    path('api/chart/<str:symbol>/', views.StockChartDataAPIView.as_view(), name='stock_chart_data'),
    
    # Overview 탭 데이터 API (종합 정보)
    path('api/overview/<str:symbol>/', views.StockOverviewAPIView.as_view(), name='stock_overview_data'),
    
    # Balance Sheet 탭 데이터 API (대차대조표)
    path('api/balance-sheet/<str:symbol>/', views.StockBalanceSheetAPIView.as_view(), name='stock_balance_sheet_data'),
    
    # Income Statement 탭 데이터 API (손익계산서)
    path('api/income-statement/<str:symbol>/', views.StockIncomeStatementAPIView.as_view(), name='stock_income_statement_data'),
    
    # Cash Flow 탭 데이터 API (현금흐름표)
    path('api/cashflow/<str:symbol>/', views.StockCashFlowAPIView.as_view(), name='stock_cashflow_data'),

    ## MVP API 엔드포인트 (간소화 버전)
    # 주식 목록 (요약)
    path('api/mvp/stocks/', views_mvp.StockMVPListView.as_view(), name='mvp_stock_list'),

    # 주식 상세 (RAG용 핵심 데이터)
    path('api/mvp/stock/<str:symbol>/', views_mvp.StockMVPDetailView.as_view(), name='mvp_stock_detail'),

    # RAG 컨텍스트 생성
    path('api/mvp/rag/<str:symbol>/', views_mvp.StockRAGContextView.as_view(), name='mvp_rag_context'),

    # 섹터 목록
    path('api/mvp/sectors/', views_mvp.SectorListView.as_view(), name='mvp_sectors'),
]