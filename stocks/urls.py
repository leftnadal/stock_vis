from django.urls import path
from . import views
from . import views_mvp  # MVP용 뷰 추가
from . import views_indicators  # 기술적 지표 뷰 추가
from . import views_search  # 종목 검색 뷰 추가
from . import views_market_movers  # Market Movers 뷰 추가
from . import views_fundamentals  # Fundamentals 뷰 추가
from . import views_screener  # Stock Screener 뷰 추가
from . import views_exchange  # Exchange Quotes 뷰 추가

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

    ## 데이터 동기화 API
    # 주식 데이터 동기화 (POST: 동기화 실행, GET: 상태 조회)
    path('api/sync/<str:symbol>/', views.StockSyncAPIView.as_view(), name='stock_sync'),

    ## MVP API 엔드포인트 (간소화 버전)
    # 주식 목록 (요약)
    path('api/mvp/stocks/', views_mvp.StockMVPListView.as_view(), name='mvp_stock_list'),

    # 주식 상세 (RAG용 핵심 데이터)
    path('api/mvp/stock/<str:symbol>/', views_mvp.StockMVPDetailView.as_view(), name='mvp_stock_detail'),

    # RAG 컨텍스트 생성
    path('api/mvp/rag/<str:symbol>/', views_mvp.StockRAGContextView.as_view(), name='mvp_rag_context'),

    # 섹터 목록
    path('api/mvp/sectors/', views_mvp.SectorListView.as_view(), name='mvp_sectors'),

    ## 기술적 지표 API 엔드포인트
    # 기술적 지표 계산 (RSI, MACD, Bollinger Bands 등)
    path('api/indicators/<str:symbol>/', views_indicators.TechnicalIndicatorView.as_view(), name='technical_indicators'),

    # 매매 신호 분석
    path('api/signal/<str:symbol>/', views_indicators.IndicatorSignalView.as_view(), name='indicator_signal'),

    # 여러 종목 지표 비교
    path('api/indicators/compare/', views_indicators.IndicatorComparisonView.as_view(), name='indicator_comparison'),

    ## 종목 검색 API 엔드포인트
    # 종목 심볼 검색 (자동완성)
    path('api/search/symbols/', views_search.SymbolSearchView.as_view(), name='symbol_search'),

    # 종목 심볼 유효성 검증
    path('api/search/validate/<str:symbol>/', views_search.SymbolValidateView.as_view(), name='symbol_validate'),

    # 인기 종목 리스트
    path('api/search/popular/', views_search.PopularSymbolsView.as_view(), name='popular_symbols'),

    ## Market Movers API 엔드포인트
    # 시장 주도 종목 (상승/하락/거래량 TOP)
    path('api/market-movers/', views_market_movers.MarketMoversView.as_view(), name='market_movers'),

    ## Fundamentals API 엔드포인트
    # 핵심 재무 지표
    path('api/fundamentals/key-metrics/<str:symbol>/', views_fundamentals.KeyMetricsView.as_view(), name='key_metrics'),

    # 재무 비율
    path('api/fundamentals/ratios/<str:symbol>/', views_fundamentals.RatiosView.as_view(), name='ratios'),

    # DCF 분석
    path('api/fundamentals/dcf/<str:symbol>/', views_fundamentals.DCFView.as_view(), name='dcf'),

    # 투자 등급
    path('api/fundamentals/rating/<str:symbol>/', views_fundamentals.RatingView.as_view(), name='rating'),

    # 전체 펀더멘털 데이터 (한 번에)
    path('api/fundamentals/all/<str:symbol>/', views_fundamentals.AllFundamentalsView.as_view(), name='all_fundamentals'),

    ## Stock Screener API 엔드포인트
    # 조건별 종목 검색
    path('api/screener/', views_screener.StockScreenerView.as_view(), name='stock_screener'),

    # 대형주 스크리너
    path('api/screener/large-cap/', views_screener.LargeCapStocksView.as_view(), name='large_cap_stocks'),

    # 고배당주 스크리너
    path('api/screener/high-dividend/', views_screener.HighDividendStocksView.as_view(), name='high_dividend_stocks'),

    # 섹터별 종목 스크리너
    path('api/screener/sector/<str:sector>/', views_screener.SectorStocksView.as_view(), name='sector_stocks'),

    # 저변동성 종목 스크리너
    path('api/screener/low-beta/', views_screener.LowBetaStocksView.as_view(), name='low_beta_stocks'),

    # 거래소별 종목 스크리너
    path('api/screener/exchange/<str:exchange>/', views_screener.ExchangeStocksView.as_view(), name='exchange_stocks'),

    ## Exchange Quotes API 엔드포인트
    # 주요 지수 시세
    path('api/quotes/index/', views_exchange.IndexQuotesView.as_view(), name='index_quotes'),

    # 개별 종목 실시간 시세
    path('api/quotes/<str:symbol>/', views_exchange.StockQuoteView.as_view(), name='stock_quote'),

    # 여러 종목 일괄 시세 조회
    path('api/quotes/batch/', views_exchange.BatchQuotesView.as_view(), name='batch_quotes'),

    # 주요 3대 지수 (S&P 500, NASDAQ, Dow Jones)
    path('api/quotes/major-indices/', views_exchange.MajorIndicesView.as_view(), name='major_indices'),

    # 섹터 성과 (섹터 ETF 기반)
    path('api/quotes/sector-performance/', views_exchange.SectorPerformanceView.as_view(), name='sector_performance'),
]