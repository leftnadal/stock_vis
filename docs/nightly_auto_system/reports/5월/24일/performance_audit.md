# API 성능 감사 보고서

생성일: 2026-05-24
대상: stock_vis backend (17 views, 7 models)
감사자: @qa-architect

---

## 요약

| 심각도 | N+1 | 인덱스 | Serializer | 페이지네이션 | 합계 |
|--------|-----|--------|------------|--------------|------|
| HIGH   | 4   | 0      | 1          | 0            | 5    |
| MED    | 3   | 1      | 1          | 3            | 8    |
| LOW    | 0   | 0      | 1          | 0            | 1    |

전체 발견 이슈: **14건**

---

## 상세

### HIGH-1: ValidationMetricsView — 카테고리별 지표 반복 DB 조회
- **파일**: `validation/api/views.py:199–285` (`_build_metric`)
- **카테고리**: N+1 쿼리 + Serializer 내 추가 DB 쿼리
- **난이도**: 중간 (메서드 수정)
- **현상**: `category=all` 요청 시 34개 지표 전체를 순회하며 지표당 최대 8회 DB 쿼리 발생.
  - `CompanyMetricSnapshot.filter(...).first()` (최신 값) × 1
  - `CompanyMetricSnapshot.filter(...).first()` (fallback) × 1
  - `CompanyBenchmarkDelta.filter(...).first()` × 1
  - `CompanyMetricSnapshot.filter(...).order_by(...)[:5]` (5년 history) × 1
  - history 루프 내 `PeerMetricBenchmark.filter(...).first()` × 5 (연도별)
  - 총 34개 지표 × 8 쿼리 = **최소 272 DB 쿼리/요청**
- **권장 수정**:
  - `CompanyMetricSnapshot`을 symbol 기준 `prefetch_related` 또는 `filter(symbol=stock).values(...)` 벌크 조회 후 파이썬에서 분기 처리
  - `PeerMetricBenchmark`도 `filter(symbol=stock, fiscal_year__in=fy_list, metric_code__in=mc_list)` 단일 쿼리로 캐시 딕셔너리 구성

---

### HIGH-2: LeaderComparisonView — 34개 지표 루프 내 3중 DB 조회
- **파일**: `validation/api/views.py:364–399`
- **카테고리**: N+1 쿼리
- **난이도**: 중간 (메서드 수정)
- **현상**: `all_metrics` (34개) 순회 중 매 반복마다
  - `MetricDefinition.filter(pk=mc).first()` × 1
  - `CompanyMetricSnapshot.filter(symbol=stock, ..., metric_code_id=mc).first()` × 2 (company + leader)
  - 34 × 3 = **최소 102 DB 쿼리/요청**
- **권장 수정**:
  - `MetricDefinition.objects.filter(pk__in=all_mc_codes)` 단일 쿼리 → dict 캐시
  - `CompanyMetricSnapshot.objects.filter(symbol__in=[stock, leader], fiscal_year=fy, metric_code_id__in=all_mc_codes)` 단일 쿼리 → `(symbol, mc)` 키 dict로 매핑

---

### HIGH-3: ChainSightGraphView — 엣지 루프 내 2중 DB 조회
- **파일**: `chainsight/api/views.py:74–87`
- **카테고리**: N+1 쿼리
- **난이도**: 중간 (메서드 수정)
- **현상**: Neo4j 결과 edges 리스트를 순회하며 엣지당
  - `CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()`
  - `PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()`
  - depth=3 시 edges 수십~수백 개 가능 → **수백 DB 쿼리/요청**
- **권장 수정**:
  - 루프 전 edge 쌍 목록을 수집 → `CoMentionEdge.objects.filter(symbol_a__in=..., symbol_b__in=...)` 벌크 조회
  - `{(a, b): cm_obj}` dict 구성 후 O(1) 참조

---

### HIGH-4: NewsViewSet.stock_news / market_news 액션 — entities prefetch 누락
- **파일**: `news/api/views.py:104–107` (stock_news), `news/api/views.py:286–289` (market_news 카테고리 액션)
- **카테고리**: N+1 쿼리
- **난이도**: 쉬움 (1–2줄)
- **현상**: 두 액션 모두 `NewsArticle.objects.filter(...)` 쿼리에 `prefetch_related('entities')` 없이 `NewsArticleListSerializer`(entities 포함)로 직렬화.
  - class-level `queryset`의 prefetch는 list/retrieve 액션에만 적용되고 커스텀 액션에는 적용되지 않음.
  - 뉴스 1건당 엔티티 1쿼리 → 기본 7일 결과 수십 건이면 수십 쿼리 추가 발생.
- **권장 수정**:
  ```python
  # stock_news (line 104)
  articles = NewsArticle.objects.filter(
      entities__symbol=symbol,
      published_at__gte=from_date
  ).prefetch_related('entities').distinct().order_by('-published_at')

  # market_news 카테고리 액션 (line 286)
  articles = NewsArticle.objects.filter(
      category__in=db_categories,
      published_at__gte=from_date
  ).prefetch_related('entities').order_by('-published_at')[:limit]
  ```

---

### HIGH-5: WatchListStockSerializer — get_latest_price/get_chart_data 내 DB 쿼리
- **파일**: `stocks/serializers.py:398–410`
- **카테고리**: Serializer 내 추가 DB 쿼리
- **난이도**: 높음 (스키마 수준 개선 필요)
- **현상**: `WatchListStockSerializer.get_latest_price()`와 `get_chart_data()`가 각각 `DailyPrice.objects.filter(stock=obj)` 쿼리 실행. `WatchlistStocksView`는 `WatchlistItem`에 `select_related('stock')`은 적용했으나 `DailyPrice`는 prefetch 불가 (SerializerMethodField가 동적으로 호출).
  - Watchlist 20개 종목 기준: `DailyPrice` 쿼리 최소 40회 (latest + chart_data)
  - 단, `WatchlistStocksView`가 실제로 `WatchListStockSerializer`를 사용하는지 확인 필요 — 뷰에서는 `WatchlistItemSerializer`를 사용하며 `WatchlistItemSerializer`는 `stock.*` source 직접 접근 방식 사용. 따라서 `WatchListStockSerializer`가 실제 호출되는 경로 파악 필요.
  - 경로 확정 필요 여부: `stocks/views_mvp.py:59` `full` 모드에서 `StockListSerializer` 사용 (DailyPrice 쿼리 없음). `WatchListStockSerializer` 직접 호출 경로는 현재 17개 감사 대상 뷰에서 확인되지 않음.
- **권장 수정**: `WatchListStockSerializer` 사용 경로가 활성화되는 경우, `DailyPrice` 최신 1건을 Stock 모델 필드(real_time_price)로 대체하거나, `prefetch_related`로 DailyPrice를 미리 로드하는 방식 채택.

---

### MED-1: ValidationSummaryView — rank_metrics 5개 루프 내 이중 DB 조회
- **파일**: `validation/api/views.py:112–123`
- **카테고리**: N+1 쿼리
- **난이도**: 쉬움 (1–2줄)
- **현상**: `rank_metrics` (5개 고정값) 순회 중 매 반복마다
  - `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc).first()`
  - `MetricDefinition.objects.filter(pk=mc).first()`
  - 5 × 2 = **10 쿼리 추가** (HIGH-1/2와 별도)
- **권장 수정**:
  - `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics)` 단일 쿼리
  - `MetricDefinition.objects.filter(pk__in=rank_metrics)` 단일 쿼리 → dict 캐시

---

### MED-2: NewsViewSet.trending 액션 — 종목별 반복 쿼리 + entities N+1
- **파일**: `news/api/views.py:344–358`
- **카테고리**: N+1 쿼리
- **난이도**: 중간 (메서드 수정)
- **현상**: `trending_data` 집계 결과 종목 수(기본 `limit`개)만큼 루프 실행.
  - 매 반복: `NewsArticle.objects.filter(entities__symbol=symbol, ...)` (1쿼리)
  - `NewsArticleListSerializer(recent_articles, many=True)` → entities 미리 prefetch 없음 (1종목당 기사 3건 × entities 쿼리)
  - limit=20 기준: 20 + 60 = **80 추가 쿼리**
- **권장 수정**:
  - 루프 전 상위 종목 심볼 목록 수집 → `NewsArticle.objects.filter(entities__symbol__in=symbols)...prefetch_related('entities')` 벌크 조회
  - 파이썬에서 symbol 기준으로 그룹핑

---

### MED-3: SP500Constituent.sub_sector — 인덱스 누락
- **파일**: `stocks/models.py:657`
- **카테고리**: 인덱스 누락
- **난이도**: 높음 (migration 필요)
- **현상**: `SP500Constituent.sub_sector = CharField(max_length=100, blank=True, default='')` — `db_index=True` 없음.
  - 사용 경로:
    - `news/models.py:648`: `SP500Constituent.objects.filter(sub_sector=value, is_active=True)`
    - `serverless/views_admin.py:529`: `SP500Constituent.objects.filter(sub_sector=value, is_active=True).exists()`
    - `serverless/views_admin.py:610`: 동일
  - SP500Constituent는 503개 이상의 행을 갖는 테이블로, full scan 발생.
- **권장 수정**:
  ```python
  # stocks/models.py SP500Constituent.Meta.indexes에 추가
  models.Index(fields=['sub_sector', 'is_active']),
  ```
  - migration 파일 생성 필요.

---

### MED-4: AdminNewsCategoryView — 카테고리 루프 내 resolve_symbols() DB 쿼리
- **파일**: `serverless/views_admin.py:475–496`
- **카테고리**: N+1 쿼리
- **난이도**: 중간 (캐싱 또는 벌크 처리)
- **현상**: `NewsCollectionCategory.objects.all()` 결과를 루프하며 각 카테고리에 대해 `cat.resolve_symbols()` 호출.
  - `resolve_symbols()`는 `sector` 또는 `sub_sector` 타입이면 `SP500Constituent.objects.filter(...)` 실행.
  - 카테고리 N개 중 sector/sub_sector 타입 M개이면 **M 추가 DB 쿼리**.
  - Admin 뷰이므로 호출 빈도는 낮으나 카테고리 증가 시 누적.
- **권장 수정**:
  - sector/sub_sector 타입 카테고리 값들을 집계 후 SP500Constituent를 단일 `values_list` 조회
  - 또는 `last_symbol_count` 캐시 필드로 미리 저장된 값 사용

---

### MED-5: AnalysisSessionListCreateView / DataBasketListCreateView — 페이지네이션 누락
- **파일**: `rag_analysis/views.py:377–381`, `rag_analysis/views.py:50–54`
- **카테고리**: 페이지네이션 누락
- **난이도**: 중간 (메서드 수정)
- **현상**: 두 뷰 모두 사용자 범위의 unbounded 리스트를 반환.
  - `AnalysisSession`: 대화형 분석 세션 — messages prefetch 포함 → 세션 증가 시 메모리·직렬화 부담 큼.
  - `DataBasket`: 분석 바구니 — items prefetch 포함.
  - DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정(settings.py에 없음) → 명시적 `pagination_class` 없으면 자동 페이지네이션 없음.
- **권장 수정**: 각 뷰에 `pagination_class = PageNumberPagination` (또는 커스텀 클래스) 추가, 또는 응답에 `[:50]` 슬라이스 + 페이지네이션 메타 추가.

---

### MED-6: PortfolioListCreateView — 페이지네이션 누락
- **파일**: `users/views.py:254–266`
- **카테고리**: 페이지네이션 누락
- **난이도**: 쉬움 (1–2줄)
- **현상**: `Portfolio.objects.filter(user=request.user).select_related('stock')` 결과를 `PortfolioSerializer(portfolios, many=True)` 전체 직렬화. 페이지네이션 없음. 포트폴리오 수 많으면 전량 응답.
- **권장 수정**: `Paginator` 또는 DRF `pagination_class` 적용. `WatchlistStocksView`와 동일한 수동 paginator 패턴 참고.

---

### MED-7: UserInterestListCreateView — 페이지네이션 누락
- **파일**: `users/views.py:967–987`
- **카테고리**: 페이지네이션 누락
- **난이도**: 쉬움 (1–2줄)
- **현상**: `UserInterest.objects.filter(user=request.user).order_by('-created_at')` 전체를 리스트 컴프리헨션으로 응답. 관심사 항목 수 제한 없음.
  - 단, 실용적으로 관심사 수는 소규모이므로 실 영향은 낮음.
- **권장 수정**: 최대 반환 수 제한(`[:100]`) 또는 페이지네이션 적용.

---

### LOW-1: StockSerializer 존재하지 않는 심볼 임포트
- **파일**: `users/views.py:194`, `users/views.py:220`
- **카테고리**: 코드 위생 (성능 직접 영향 없음)
- **난이도**: 쉬움 (1–2줄)
- **현상**: `from stocks.serializers import StockSerializer` — `stocks/serializers.py`에 `StockSerializer` 클래스가 정의되어 있지 않음. `StockListSerializer`만 존재. 런타임 `ImportError` 발생 경로.
  - `UserFavorites.get()` 및 `AddFavorite.post()` 호출 시 즉시 500 에러.
- **권장 수정**: `StockSerializer` → `StockListSerializer`로 교체, 또는 `StockSerializer = StockListSerializer` 별칭 추가.

---

## 미발견 항목

| 카테고리 | 파일 범위 | 결과 |
|----------|-----------|------|
| N+1 쿼리 | `stocks/views_eod.py` | 특이사항 없음. `select_related('stock')` 적용됨 (line 77). |
| N+1 쿼리 | `stocks/views_fundamentals.py` | 단건 symbol 기준 조회. 루프 없음. |
| N+1 쿼리 | `stocks/views_indicators.py` | 단건 조회. 루프 없음. |
| N+1 쿼리 | `macro/views.py` | Redis 캐싱 레이어 사용. DB 루프 없음. |
| N+1 쿼리 | `rag_analysis/views.py` (DataBasketAddStockDataView) | 단건 symbol 조회 루프이나 최대 1건 처리 구조. |
| N+1 쿼리 | `sec_pipeline/views.py` | 단건 symbol 조회만. 루프 없음. |
| 인덱스 누락 | `stocks/models.py` (Stock) | `sector`, `industry`, `market_capitalization` 모두 `Meta.indexes` 포함. 이상 없음. |
| 인덱스 누락 | `news/models.py` | `published_at`, `symbol`, `is_processed` 등 주요 필드 인덱스 정상. |
| 인덱스 누락 | `rag_analysis/models.py` | `Meta.ordering` 외 주요 FK 자동 인덱스. 이상 없음. |
| 인덱스 누락 | `sec_pipeline/models.py` | 주요 날짜/symbol 필드 `Meta.indexes` 포함. 이상 없음. |
| 인덱스 누락 | `graph_analysis/models.py` | `symbol_a`, `symbol_b` 등 조회 필드 인덱스 정상. |
| 페이지네이션 | `stocks/views.py:StockListAPIView` | `pagination_class = StockListPagination` 적용됨. |
| 페이지네이션 | `news/api/views.py:NewsViewSet` | `pagination_class = NewsArticlePagination` 적용됨. |
| 페이지네이션 | 스크리너 계열 뷰 (`views_screener.py`) | `limit` 파라미터로 최대 1,000건 제한. |
| DEFAULT_PAGINATION_CLASS | `config/settings.py` | 미설정 확인. 전역 페이지네이션 없음. 뷰별 명시 필요. |

---

## 액션 아이템 요약

| 우선순위 | 이슈 | 파일 | 담당 |
|---------|------|------|------|
| HIGH | HIGH-1: ValidationMetricsView 272+ 쿼리 | `validation/api/views.py:199` | @backend |
| HIGH | HIGH-2: LeaderComparisonView 102+ 쿼리 | `validation/api/views.py:364` | @backend |
| HIGH | HIGH-3: ChainSightGraphView 엣지 N+1 | `chainsight/api/views.py:74` | @backend |
| HIGH | HIGH-4: stock_news / market_news prefetch 누락 | `news/api/views.py:104,286` | @backend |
| HIGH | HIGH-5: WatchListStockSerializer DailyPrice 쿼리 | `stocks/serializers.py:398` | @backend |
| MED | MED-1: ValidationSummaryView 10 쿼리 | `validation/api/views.py:112` | @backend |
| MED | MED-2: trending 액션 N+1 | `news/api/views.py:344` | @backend |
| MED | MED-3: SP500Constituent.sub_sector 인덱스 | `stocks/models.py:657` | @backend |
| MED | MED-4: AdminNewsCategoryView resolve_symbols N+1 | `serverless/views_admin.py:475` | @backend |
| MED | MED-5: AnalysisSession / DataBasket 페이지네이션 | `rag_analysis/views.py:50,377` | @backend |
| MED | MED-6: PortfolioListCreateView 페이지네이션 | `users/views.py:254` | @backend |
| MED | MED-7: UserInterestListCreateView 페이지네이션 | `users/views.py:967` | @backend |
| LOW | LOW-1: StockSerializer ImportError | `users/views.py:194,220` | @backend |
