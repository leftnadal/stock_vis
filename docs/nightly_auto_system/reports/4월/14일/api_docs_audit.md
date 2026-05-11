# API 문서 감사 보고서

> 작성일: 2026-04-14
> 대상: Stock-Vis 프로젝트 전체 REST API
> 목적: API 문서화 현황 파악 및 drf-spectacular 도입 작업량 산정

---

## 1. 현재 상태

### 1.1 API 문서 도구 설치 여부

| 항목 | 상태 |
|------|------|
| drf-spectacular | **미설치** (pyproject.toml에 없음) |
| drf-yasg | **미설치** |
| Swagger UI / ReDoc | **미설정** |
| OpenAPI 스펙 자동 생성 | **불가** |
| INSTALLED_APPS 등록 | 문서 관련 패키지 없음 |

### 1.2 수동 OpenAPI 계약서 (contracts/)

수동으로 작성된 OpenAPI YAML 스펙이 3개 존재한다:

| 파일 | 대상 앱 |
|------|---------|
| `contracts/chainsight-api.yaml` | chainsight |
| `contracts/validation-api.yaml` | validation |
| `contracts/sec-pipeline-api.yaml` | sec_pipeline |

이 파일들은 Contract-Driven Development 용도로 작성된 것이며, 자동 생성이 아닌 수동 관리 상태이다.

### 1.3 현재 문서화 수준 요약

- **자동 생성 문서**: 없음
- **수동 계약서**: 3개 앱 (chainsight, validation, sec_pipeline)
- **인라인 docstring**: 부분적 존재 (주로 news, macro 앱)
- **CLAUDE.md 엔드포인트 표**: 앱별 prefix만 기재, 개별 경로 미기재

---

## 2. 엔드포인트 목록 (앱별)

### 2.1 전체 요약

| 앱 | URL prefix | URL 패턴 수 | View 클래스/함수 수 | 비고 |
|----|-----------|-------------|-------------------|------|
| config (root) | `/`, `/health/` | 2 | 2 | 루트 + 헬스체크 |
| stocks | `/api/v1/stocks/` | 39 | 41 | 9개 views 파일에 분산 |
| users | `/api/v1/users/` | 35 | 27 | JWT + 세션 + 포트폴리오 + 워치리스트 |
| news | `/api/v1/news/` | 32 | 1 ViewSet (32 액션) | Router + 30개 @action |
| macro | `/api/v1/macro/` | 10 | 10 | 거시경제 대시보드 |
| rag_analysis | `/api/v1/rag/` | 15 | 15 | DataBasket + 세션 + 모니터링 |
| serverless | `/api/v1/serverless/` | 64 | 62 | 최대 규모, 기능 혼재 |
| thesis | `/api/v1/thesis/` | 16 | 11 (3 ViewSet + 8 APIView) | 중첩 라우터 사용 |
| validation | `/api/v1/validation/` | 6 | 6 | 계약서 존재 |
| chainsight | `/api/v1/chainsight/` | 7 | 7 | 계약서 존재 |
| sec_pipeline | `/api/v1/sec-pipeline/` | 2 | 2 | 계약서 존재 |
| api_request | `/api/v1/` (admin) | 6 | 6 | Provider 관리용 |
| **합계** | | **234** | **~199** | |

### 2.2 stocks (39 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/` | DashboardView | GET | 시가총액 상위 주식 대시보드 |
| 2 | `/stock/<symbol>/` | StockDetailView | GET | 개별 주식 상세 |
| 3 | `/search/` | StockSearchAPIView | GET | 주식 검색 (자동완성) |
| 4 | `/api/chart/<symbol>/` | StockChartDataAPIView | GET | 차트 데이터 |
| 5 | `/api/overview/<symbol>/` | StockOverviewAPIView | GET | 종합 정보 |
| 6 | `/api/balance-sheet/<symbol>/` | StockBalanceSheetAPIView | GET | 대차대조표 |
| 7 | `/api/income-statement/<symbol>/` | StockIncomeStatementAPIView | GET | 손익계산서 |
| 8 | `/api/cashflow/<symbol>/` | StockCashFlowAPIView | GET | 현금흐름표 |
| 9 | `/api/sync/<symbol>/` | StockSyncAPIView | POST/GET | 데이터 동기화 |
| 10 | `/api/mvp/stocks/` | StockMVPListView | GET | MVP 주식 목록 |
| 11 | `/api/mvp/stock/<symbol>/` | StockMVPDetailView | GET | MVP 주식 상세 |
| 12 | `/api/mvp/rag/<symbol>/` | StockRAGContextView | GET | RAG 컨텍스트 |
| 13 | `/api/mvp/sectors/` | SectorListView | GET | 섹터 목록 |
| 14 | `/api/indicators/<symbol>/` | TechnicalIndicatorView | GET | 기술적 지표 |
| 15 | `/api/signal/<symbol>/` | IndicatorSignalView | GET | 매매 신호 |
| 16 | `/api/indicators/compare/` | IndicatorComparisonView | GET | 지표 비교 |
| 17 | `/api/search/symbols/` | SymbolSearchView | GET | 심볼 검색 |
| 18 | `/api/search/validate/<symbol>/` | SymbolValidateView | GET | 심볼 유효성 검증 |
| 19 | `/api/search/popular/` | PopularSymbolsView | GET | 인기 종목 |
| 20 | `/api/market-movers/` | MarketMoversView | GET | 시장 주도 종목 |
| 21 | `/api/fundamentals/key-metrics/<symbol>/` | KeyMetricsView | GET | 핵심 재무 지표 |
| 22 | `/api/fundamentals/ratios/<symbol>/` | RatiosView | GET | 재무 비율 |
| 23 | `/api/fundamentals/dcf/<symbol>/` | DCFView | GET | DCF 분석 |
| 24 | `/api/fundamentals/rating/<symbol>/` | RatingView | GET | 투자 등급 |
| 25 | `/api/fundamentals/all/<symbol>/` | AllFundamentalsView | GET | 전체 펀더멘털 |
| 26 | `/api/screener/` | StockScreenerView | GET | 조건별 종목 검색 |
| 27 | `/api/screener/large-cap/` | LargeCapStocksView | GET | 대형주 |
| 28 | `/api/screener/high-dividend/` | HighDividendStocksView | GET | 고배당주 |
| 29 | `/api/screener/sector/<sector>/` | SectorStocksView | GET | 섹터별 종목 |
| 30 | `/api/screener/low-beta/` | LowBetaStocksView | GET | 저변동성 |
| 31 | `/api/screener/exchange/<exchange>/` | ExchangeStocksView | GET | 거래소별 |
| 32 | `/api/quotes/index/` | IndexQuotesView | GET | 주요 지수 시세 |
| 33 | `/api/quotes/<symbol>/` | StockQuoteView | GET | 개별 실시간 시세 |
| 34 | `/api/quotes/batch/` | BatchQuotesView | GET | 일괄 시세 |
| 35 | `/api/quotes/major-indices/` | MajorIndicesView | GET | 3대 지수 |
| 36 | `/api/quotes/sector-performance/` | SectorPerformanceView | GET | 섹터 성과 |
| 37 | `/eod/dashboard/` | EODDashboardView | GET | EOD 대시보드 스냅샷 |
| 38 | `/eod/signal/<signal_id>/` | EODSignalDetailView | GET | 시그널 종목 목록 |
| 39 | `/eod/pipeline/status/` | EODPipelineStatusView | GET | 파이프라인 상태 |

### 2.3 users (35 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/jwt/signup/` | JWTSignUpView | POST | 회원가입 |
| 2 | `/jwt/login/` | CustomTokenObtainPairView | POST | JWT 로그인 |
| 3 | `/jwt/logout/` | JWTLogoutView | POST | JWT 로그아웃 |
| 4 | `/jwt/refresh/` | TokenRefreshView | POST | 토큰 갱신 |
| 5 | `/jwt/verify/` | JWTVerifyView | POST | 토큰 검증 |
| 6 | `/jwt/change-password/` | ChangePasswordJWTView | POST | 비밀번호 변경 |
| 7 | `/jwt/profile/` | ProfileUpdateView | GET/PATCH | 프로필 |
| 8 | `/me/` | Me | GET/PUT | 현재 사용자 (세션) |
| 9 | `/` | Users | POST | 사용자 생성 (세션) |
| 10 | `/@<user_name>/` | PublicUser | GET | 공개 프로필 |
| 11 | `/change_password/` | ChangePassword | PUT | 비밀번호 변경 (세션) |
| 12 | `/login/` | LogIn | POST | 로그인 (세션) |
| 13 | `/logout/` | LogOut | POST | 로그아웃 (세션) |
| 14 | `/favorites/` | UserFavorites | GET | 즐겨찾기 목록 |
| 15 | `/favorites/add/<stock_id>/` | AddFavorite | POST | 즐겨찾기 추가 |
| 16 | `/favorites/remove/<stock_id>/` | RemoveFavorite | DELETE | 즐겨찾기 제거 |
| 17 | `/portfolio/` | PortfolioListCreateView | GET/POST | 포트폴리오 목록/생성 |
| 18 | `/portfolio/summary/` | PortfolioSummaryView | GET | 포트폴리오 요약 |
| 19 | `/portfolio/table/` | PortfolioDetailTableView | GET | 포트폴리오 테이블 |
| 20 | `/portfolio/refresh/` | RefreshPortfolioDataView | POST | 데이터 갱신 |
| 21 | `/portfolio/<pk>/` | PortfolioDetailView | GET/PUT/DELETE | 포트폴리오 상세 |
| 22 | `/portfolio/<pk>/quick-update/` | PortfolioDetailTableView | PATCH | 빠른 수정 |
| 23 | `/portfolio/symbol/<symbol>/` | PortfolioBySymbolView | GET | 심볼별 포트폴리오 |
| 24 | `/portfolio/symbol/<symbol>/refresh/` | RefreshStockDataView | POST | 주식 데이터 갱신 |
| 25 | `/portfolio/symbol/<symbol>/status/` | StockDataStatusView | GET | 데이터 상태 |
| 26 | `/interests/` | UserInterestListCreateView | GET/POST | 관심사 목록/생성 |
| 27 | `/interests/<pk>/` | UserInterestDeleteView | DELETE | 관심사 삭제 |
| 28 | `/watchlist/` | WatchlistListCreateView | GET/POST | 워치리스트 목록/생성 |
| 29 | `/watchlist/<pk>/` | WatchlistDetailView | GET/PUT/DELETE | 워치리스트 상세 |
| 30 | `/watchlist/<pk>/add-stock/` | WatchlistItemAddView | POST | 종목 추가 |
| 31 | `/watchlist/<pk>/bulk-add/` | WatchlistBulkAddView | POST | 종목 일괄 추가 |
| 32 | `/watchlist/<pk>/bulk-remove/` | WatchlistBulkRemoveView | POST | 종목 일괄 제거 |
| 33 | `/watchlist/<pk>/stocks/` | WatchlistStocksView | GET | 워치리스트 종목 |
| 34 | `/watchlist/<pk>/stocks/<symbol>/` | WatchlistItemUpdateView | PATCH | 종목 메모 수정 |
| 35 | `/watchlist/<pk>/stocks/<symbol>/remove/` | WatchlistItemRemoveView | DELETE | 종목 제거 |

### 2.4 news (32 엔드포인트)

Router 기반 `NewsViewSet` (ReadOnlyModelViewSet) + 30개 커스텀 액션:

| # | 경로 | 메서드 | HTTP | 설명 |
|---|------|--------|------|------|
| 1 | `/` | list | GET | 뉴스 목록 |
| 2 | `/<pk>/` | retrieve | GET | 뉴스 상세 |
| 3 | `/stock/<symbol>/` | stock_news | GET | 종목별 뉴스 |
| 4 | `/stock/<symbol>/sentiment/` | stock_sentiment | GET | 종목별 감성 분석 |
| 5 | `/market/` | market | GET | 시장 전체 뉴스 |
| 6 | `/trending/` | trending | GET | 트렌딩 종목 |
| 7 | `/all/` | all_news | GET | 전체 뉴스 |
| 8 | `/sources/` | sources | GET | 뉴스 소스 목록 |
| 9 | `/daily-keywords/` | daily_keywords | GET | 일간 키워드 |
| 10 | `/daily-keywords/generate/` | generate_daily_keywords | POST | 키워드 생성 |
| 11 | `/keyword-detail/` | keyword_detail | GET | 키워드 상세 |
| 12 | `/insights/` | insights | GET | 종목 인사이트 |
| 13 | `/market-feed/` | market_feed | GET | 마켓 피드 |
| 14 | `/interest-options/` | interest_options | GET | 관심 옵션 |
| 15 | `/personalized-feed/` | personalized_feed | GET | 개인화 피드 |
| 16 | `/news-events/` | news_events | GET | 뉴스 이벤트 |
| 17 | `/news-events/impact-map/` | news_events_impact_map | GET | 이벤트 영향 맵 |
| 18 | `/ml-status/` | ml_status | GET | ML 모델 상태 |
| 19 | `/ml-shadow-report/` | ml_shadow_report | GET | Shadow 모드 리포트 |
| 20 | `/ml-weekly-report/` | ml_weekly_report | GET | 주간 리포트 |
| 21 | `/ml-lightgbm-readiness/` | ml_lightgbm_readiness | GET | LightGBM 준비도 |
| 22 | `/recommendations/` | recommendations | GET | 추천 |
| 23 | `/collection-logs/` | collection_logs | GET | 수집 로그 (Admin) |
| 24 | `/pipeline-health/` | pipeline_health | GET | 파이프라인 건강도 (Admin) |
| 25 | `/ml-trend/` | ml_trend | GET | ML 트렌드 (Admin) |
| 26 | `/llm-usage/` | llm_usage | GET | LLM 사용량 (Admin) |
| 27 | `/task-timeline/` | task_timeline | GET | 태스크 타임라인 (Admin) |
| 28 | `/neo4j-status/` | neo4j_status | GET | Neo4j 상태 (Admin) |
| 29 | `/ml-rollback-preview/` | ml_rollback_preview | GET | ML 롤백 미리보기 (Admin) |
| 30 | `/ml-rollback/` | ml_rollback | POST | ML 롤백 실행 (Admin) |
| 31 | `/alerts/` | alerts | GET | 알림 목록 (Admin) |
| 32 | `/alerts/<alert_pk>/resolve/` | alerts_resolve | POST | 알림 해결 (Admin) |

### 2.5 macro (10 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/pulse/` | MarketPulseView | GET | 전체 대시보드 |
| 2 | `/fear-greed/` | FearGreedIndexView | GET | 공포-탐욕 지수 |
| 3 | `/interest-rates/` | InterestRatesView | GET | 금리 |
| 4 | `/inflation/` | InflationDashboardView | GET | 인플레이션 |
| 5 | `/global-markets/` | GlobalMarketsView | GET | 글로벌 마켓 |
| 6 | `/calendar/` | EconomicCalendarView | GET | 경제 캘린더 |
| 7 | `/vix/` | VIXView | GET | VIX 지수 |
| 8 | `/sectors/` | SectorPerformanceView | GET | 섹터 성과 |
| 9 | `/sync/` | DataSyncView | POST | 데이터 동기화 |
| 10 | `/sync/status/` | SyncStatusView | GET | 동기화 상태 |

### 2.6 rag_analysis (15 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/baskets/` | DataBasketListCreateView | GET/POST | 바구니 목록/생성 |
| 2 | `/baskets/<pk>/` | DataBasketDetailView | GET/PUT/DELETE | 바구니 상세 |
| 3 | `/baskets/<pk>/add-item/` | DataBasketAddItemView | POST | 아이템 추가 |
| 4 | `/baskets/<pk>/add-stock-data/` | DataBasketAddStockDataView | POST | 주식 데이터 추가 |
| 5 | `/baskets/<pk>/items/<item_id>/` | DataBasketRemoveItemView | DELETE | 아이템 제거 |
| 6 | `/baskets/<pk>/clear/` | DataBasketClearView | POST | 바구니 비우기 |
| 7 | `/sessions/` | AnalysisSessionListCreateView | GET/POST | 세션 목록/생성 |
| 8 | `/sessions/<pk>/` | AnalysisSessionDetailView | GET/DELETE | 세션 상세 |
| 9 | `/sessions/<pk>/messages/` | SessionMessagesView | GET | 메시지 목록 |
| 10 | `/sessions/<pk>/chat/stream/` | ChatStreamView | POST | 채팅 스트리밍 (SSE) |
| 11 | `/monitoring/usage/` | UsageStatsView | GET | 사용량 통계 |
| 12 | `/monitoring/cost/` | CostSummaryView | GET | 비용 요약 |
| 13 | `/monitoring/cache/` | CacheStatsView | GET | 캐시 통계 |
| 14 | `/monitoring/history/` | UsageHistoryView | GET | 사용량 히스토리 |
| 15 | `/monitoring/pricing/` | ModelPricingView | GET | 모델 가격 |

### 2.7 serverless (64 엔드포인트)

최대 규모 앱. 기능 영역별로 분류:

**Admin Dashboard (12)**

| # | 경로 | View | HTTP |
|---|------|------|------|
| 1 | `/admin/dashboard/overview/` | AdminOverviewView | GET |
| 2 | `/admin/dashboard/stocks/` | AdminStocksView | GET |
| 3 | `/admin/dashboard/screener/` | AdminScreenerView | GET |
| 4 | `/admin/dashboard/market-pulse/` | AdminMarketPulseView | GET |
| 5 | `/admin/dashboard/news/` | AdminNewsView | GET |
| 6 | `/admin/dashboard/system/` | AdminSystemView | GET |
| 7 | `/admin/dashboard/tasks/` | AdminTaskLogsView | GET |
| 8 | `/admin/dashboard/actions/` | AdminActionView | GET/POST |
| 9 | `/admin/dashboard/actions/status/<task_id>/` | AdminTaskStatusView | GET |
| 10 | `/admin/dashboard/news/categories/` | AdminNewsCategoryView | GET/POST |
| 11 | `/admin/dashboard/news/categories/<id>/` | AdminNewsCategoryDetailView | GET/PUT/DELETE |
| 12 | `/admin/dashboard/news/sector-options/` | AdminNewsSectorOptionsView | GET |

**Market Movers (2)**: `movers`, `movers/<symbol>`
**Sync (2)**: `sync`, `sync-now`
**Keywords (4)**: `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`
**Market Breadth (3)**: `breadth`, `breadth/history`, `breadth/sync`
**Sector Heatmap (3)**: `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
**Screener Presets (7)**: `presets`, `presets/trending`, `presets/shared/<code>`, `presets/import/<code>`, `presets/<id>`, `presets/<id>/execute`, `presets/<id>/share`
**Screener Filters (1)**: `filters`
**Advanced Screener (1)**: `screener`
**Alerts (6)**: `alerts`, `alerts/history`, `alerts/history/<id>/read`, `alerts/history/<id>/dismiss`, `alerts/<id>`, `alerts/<id>/toggle`
**Investment Thesis (4)**: `thesis/generate`, `thesis/shared/<code>`, `thesis/<id>`, `thesis`
**ETF Holdings (9)**: `etf/status`, `etf/sync`, `etf/resolve-url`, `etf/<symbol>/holdings`, `etf/stock/<symbol>/themes`, `etf/stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<id>/stocks`
**LLM Relations (4)**: `llm-relations/extract`, `llm-relations/sync`, `llm-relations/stats`, `llm-relations/<symbol>`
**Institutional (3)**: `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`
**Regulatory/Patent (2)**: `regulatory/<symbol>`, `patent-network/<symbol>`
**Health (1)**: `health`

### 2.8 thesis (16 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/conversation/start/` | ConversationStartView | POST | 대화 시작 |
| 2 | `/conversation/respond/` | ConversationRespondView | POST | 대화 응답 |
| 3 | `/conversation/news-issues/` | NewsIssuesView | GET | 뉴스 이슈 조회 |
| 4 | `/conversation/suggest/` | SuggestThesesView | POST | 가설 제안 |
| 5 | `/<thesis_id>/dashboard/` | DashboardView | GET | 관제실 대시보드 |
| 6 | `/<thesis_id>/indicators/<ind_id>/readings/` | IndicatorReadingsView | GET | 지표 리딩 |
| 7 | `/alerts/` | AlertListView | GET | 알림 목록 |
| 8 | `/alerts/<aid>/read/` | AlertReadView | POST | 알림 읽음 |
| 9-11 | `/` (ThesisViewSet) | ThesisViewSet | CRUD | 가설 CRUD + close 액션 |
| 12-13 | `/<thesis_id>/premises/` | ThesisPremiseViewSet | CRUD | 전제 CRUD |
| 14-16 | `/<thesis_id>/indicators/` | ThesisIndicatorViewSet | CRUD | 지표 CRUD + auto 액션 |

### 2.9 validation (6 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/<symbol>/summary/` | ValidationSummaryView | GET | 검증 요약 |
| 2 | `/<symbol>/metrics/` | ValidationMetricsView | GET | 검증 지표 |
| 3 | `/<symbol>/leader-comparison/` | LeaderComparisonView | GET | 리더 비교 |
| 4 | `/<symbol>/presets/` | PresetListView | GET/POST/DELETE | 프리셋 관리 |
| 5 | `/<symbol>/peer-preference/` | PeerPreferenceView | GET/POST/DELETE | Peer 설정 |
| 6 | `/<symbol>/llm-filter/` | LLMPeerFilterView | POST | LLM 필터 |

### 2.10 chainsight (7 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/seeds/` | SeedListView | GET | 시드 목록 |
| 2 | `/sector/<sector>/graph/` | SectorGraphView | GET | 섹터 그래프 |
| 3 | `/signals/` | SignalFeedView | GET | 시그널 피드 |
| 4 | `/trace/` | ChainSightTraceView | GET | 연쇄 추적 |
| 5 | `/<symbol>/neighbors/` | NeighborGraphView | GET | 이웃 그래프 |
| 6 | `/<symbol>/graph/` | ChainSightGraphView | GET | 기업 그래프 |
| 7 | `/<symbol>/suggestions/` | ChainSightSuggestionView | GET | 추천 |

### 2.11 sec_pipeline (2 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/admin/dashboard/` | sec_pipeline_dashboard | GET | 파이프라인 대시보드 |
| 2 | `/filing/<symbol>/` | FilingDataView | GET | Filing 데이터 조회 |

### 2.12 api_request (6 엔드포인트)

| # | 경로 | View | HTTP | 설명 |
|---|------|------|------|------|
| 1 | `/health/` | HealthCheckView | GET | 헬스체크 |
| 2 | `/admin/providers/status/` | ProviderStatusView | GET | 프로바이더 상태 |
| 3 | `/admin/providers/rate-limits/` | RateLimitStatusView | GET/POST | Rate Limit 상태/리셋 |
| 4 | `/admin/providers/cache/` | CacheManagementView | GET/DELETE | 캐시 관리 |
| 5 | `/admin/providers/test/` | ProviderTestView | POST | 프로바이더 테스트 |
| 6 | `/admin/providers/config/` | ProviderConfigView | GET | 프로바이더 설정 |

---

## 3. 문서화 도입 시 필요 작업 목록

### 3.1 drf-spectacular 설치 + 설정

```
# 1단계: 패키지 설치
poetry add drf-spectacular

# 2단계: INSTALLED_APPS 추가
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

# 3단계: REST_FRAMEWORK 설정에 스키마 클래스 지정
REST_FRAMEWORK = {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# 4단계: drf-spectacular 설정
SPECTACULAR_SETTINGS = {
    'TITLE': 'Stock-Vis API',
    'DESCRIPTION': 'AI 기반 투자 분석 플랫폼 API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# 5단계: URL에 Swagger UI / ReDoc 추가
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

### 3.2 @extend_schema 데코레이터 추가 범위

drf-spectacular는 ViewSet과 APIView에서 기본 스키마를 자동 추론하지만, **정확한 문서**를 위해 `@extend_schema`가 필요한 영역:

| 우선순위 | 대상 | 파일 수 | View/함수 수 | 이유 |
|---------|------|---------|-------------|------|
| **P0 (필수)** | @api_view 함수형 뷰 | 1 | ~50 | serverless/views.py — 자동 추론 불가, 수동 스키마 필수 |
| **P1 (권장)** | request body가 복잡한 APIView | 8+ | ~30 | POST/PUT 엔드포인트의 입력 스키마 명시 |
| **P2 (선택)** | ViewSet @action | 1 | 30 | news ViewSet 커스텀 액션의 파라미터/응답 명시 |
| **P3 (나중)** | 단순 GET APIView | 15+ | ~90 | 응답 serializer만 연결하면 자동 추론 가능 |

**앱별 @extend_schema 예상 작업량:**

| 앱 | 클래스/함수 수 | 자동 추론 가능 | @extend_schema 필요 | 난이도 |
|----|--------------|---------------|-------------------|--------|
| stocks | 41 | ~30 (APIView + serializer) | ~11 (GET-only는 간단) | 중 |
| users | 27 | ~20 (표준 CRUD) | ~7 (커스텀 로직) | 하 |
| news | 32 | 2 (list/retrieve) | 30 (모든 @action) | **상** |
| macro | 10 | ~8 | ~2 | 하 |
| rag_analysis | 15 | ~10 | ~5 | 중 |
| serverless | 62 | 0 (전부 함수형 뷰) | **62** | **최상** |
| thesis | 11 | ~6 (ViewSet CRUD) | ~5 | 중 |
| validation | 6 | ~4 | ~2 | 하 |
| chainsight | 7 | ~5 | ~2 | 하 |
| sec_pipeline | 2 | ~1 | ~1 | 하 |
| api_request | 6 | ~4 | ~2 | 하 |
| **합계** | **~199** | **~90** | **~129** | |

### 3.3 추가 필요 작업

| 작업 | 설명 | 예상 규모 |
|------|------|----------|
| Serializer 정비 | 일부 뷰는 Serializer 없이 dict 직접 반환 → inline_serializer 또는 Serializer 생성 필요 | serverless 앱 중심 30+ |
| 인증 스키마 명시 | JWT/세션 혼합 사용 → `@extend_schema(auth=[])` 또는 security scheme 설정 | 전역 설정 + 예외 15개 |
| 에러 응답 스키마 | 400/401/403/404/500 공통 에러 응답 타입 정의 | 1개 공통 스키마 |
| 태그(Tag) 구성 | 앱/기능별 태그 그룹핑 (Swagger UI 가독성) | `SPECTACULAR_SETTINGS['TAGS']` |
| 기존 contracts/ 통합 | chainsight, validation, sec_pipeline의 수동 스펙과 자동 생성 스펙 일치 검증 | 3개 파일 비교 |
| Query Parameter 문서화 | `?days=7`, `?period=1M` 등 쿼리 파라미터 명시 | 전체 GET 엔드포인트 ~150개 |
| SSE 엔드포인트 | `chat/stream/` — OpenAPI에서 SSE 스트리밍 표현 한계 → 별도 문서 또는 주석 | 1개 |

### 3.4 권장 도입 순서

```
Phase 1 — 기반 설정 (1일)
├── drf-spectacular 설치 + 기본 설정
├── Swagger UI / ReDoc URL 추가
├── 전역 인증 스키마 설정
└── 기본 자동 추론으로 첫 스펙 생성 확인

Phase 2 — 핵심 앱 문서화 (3~5일)
├── users (JWT 인증 플로우 — 프론트엔드 연동 핵심)
├── stocks (가장 많은 외부 사용)
├── thesis (ViewSet 기반 — 자동 추론 높음)
└── macro, validation, chainsight, sec_pipeline (소규모)

Phase 3 — 대형 앱 문서화 (5~7일)
├── serverless (62개 함수형 뷰 — 최대 작업량)
├── news (30개 @action 메서드)
└── rag_analysis

Phase 4 — 마무리 (2~3일)
├── 에러 응답 스키마 통일
├── 태그 구성 + Swagger UI 최적화
├── contracts/ 수동 스펙과 자동 생성 스펙 일치 검증
└── CI에 스펙 검증 추가 (spectactular validate)
```

**총 예상 작업량: 11~16일** (1인 기준, 풀타임)

### 3.5 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| serverless/views.py 함수형 뷰 50+ | Serializer 없이 dict 반환 → 자동 추론 불가 | inline_serializer 대량 생성 또는 응답 Serializer 신규 작성 |
| 인증 방식 혼재 (JWT + 세션) | 스키마 생성 시 인증 정보 혼란 | `@extend_schema(auth=[...])` 명시적 지정 |
| news ViewSet 30개 @action | 각 액션의 커스텀 파라미터 문서화 필요 | @extend_schema_view 또는 개별 데코레이터 |
| SSE 스트리밍 (chat/stream) | OpenAPI 3.0에서 표준 표현 한계 | 별도 문서 또는 x-extension 활용 |

---

## 부록: 파일 위치 요약

### urls.py 파일 (12개)
```
config/urls.py                  # 루트 라우터
stocks/urls.py                  # 39 패턴
users/urls.py                   # 35 패턴
news/api/urls.py                # Router 기반
macro/urls.py                   # 10 패턴
rag_analysis/urls.py            # 15 패턴
serverless/urls.py              # 64 패턴
thesis/urls.py                  # 16 패턴 (중첩 라우터)
validation/api/urls.py          # 6 패턴
chainsight/api/urls.py          # 7 패턴
sec_pipeline/urls.py            # 2 패턴
api_request/urls.py             # 6 패턴
```

### views 파일 (24개)
```
config/views.py
stocks/views.py, views_mvp.py, views_indicators.py, views_search.py,
       views_market_movers.py, views_fundamentals.py, views_screener.py,
       views_exchange.py, views_eod.py
users/views.py
news/api/views.py
macro/views.py
rag_analysis/views.py
serverless/views.py, views_admin.py
thesis/views/thesis_views.py, monitoring_views.py, conversation_views.py
validation/api/views.py
chainsight/api/views.py
sec_pipeline/views.py
api_request/admin_views.py
```
