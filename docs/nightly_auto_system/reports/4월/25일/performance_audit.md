# API 성능 감사 보고서

**감사일**: 2026-04-25
**대상**: Stock-Vis Backend (Django/DRF)
**범위**: views/serializers/models — 17개 view 파일, 7개 model 파일
**감사 모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 누락 | 합계 |
|--------|----------|-------------|-----------------|--------------------|------|
| HIGH   | 3        | 1 (전역)    | 0               | 3                  | **7** |
| MED    | 4        | -           | 2               | 6                  | **12** |
| LOW    | 2        | -           | 1               | -                  | **3** |
| **합계** | **9**    | **1**       | **3**           | **9**              | **22** |

> 가장 시급한 수정 대상은 `validation/api/views.py:219` (메트릭 빌드 N+1 350+ 쿼리)와 `config/settings.py:321` (DEFAULT_PAGINATION_CLASS 누락)입니다.

---

## 상세

### 1. N+1 쿼리

#### 1.1 [HIGH / 수정 난이도: 중간] `validation/api/views.py:219-300`
**`ValidationMetricsView._build_metric`** — 메트릭 빌드 루프 N+1
- **현상**:
  - `_build_category` 루프(메트릭 5~10개) × `_build_metric` 호출
  - 각 `_build_metric` 호출에서 발생하는 별도 쿼리:
    1. `MetricDefinition.objects.filter(pk=mc).first()` — 라인 205, 117 등 반복
    2. `CompanyMetricSnapshot.objects.filter(...).first()` — 라인 222
    3. `CompanyMetricSnapshot.objects.filter(...).order_by('-fiscal_year').first()` (any_snap) — 라인 236
    4. `CompanyBenchmarkDelta.objects.filter(...).first()` — 라인 248
    5. `CompanyMetricSnapshot.objects.filter(...).order_by('fiscal_year')[:5]` — 라인 265
  - history loop(라인 268-285): 각 snapshot마다 `PeerMetricBenchmark.objects.filter(...).first()` 추가 1회
  - 카테고리 7개 × 메트릭 평균 7개 × (지표당 5쿼리 + 5년치 PeerMetricBenchmark) = **약 350~500 쿼리/요청**
- **권장 수정**:
  - `MetricDefinition`을 `category=all` 시 한 번에 모두 가져와 `dict[metric_code -> md]`로 캐시
  - `CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code__in=all_metric_codes).order_by('-fiscal_year')`로 단일 쿼리 fetch 후 파이썬에서 그룹핑
  - `PeerMetricBenchmark.objects.filter(symbol=stock, fiscal_year__in=[...], metric_code__in=[...])`로 일괄 fetch 후 dict 매핑
  - `CompanyBenchmarkDelta`도 동일 방식

#### 1.2 [HIGH / 수정 난이도: 중간] `validation/api/views.py:317-418`
**`LeaderComparisonView.get`** — 리더 비교 메트릭별 쿼리
- **현상**: `for cat, mc in all_metrics:` 루프(라인 361-400)에서 메트릭마다
  - `MetricDefinition.objects.filter(pk=mc).first()` (라인 362)
  - `CompanyMetricSnapshot.objects.filter(...).first()` × 2 (회사 + 리더, 라인 366/369)
  - 메트릭 50개 가정 시 **150 쿼리**
- **권장 수정**: 1.1과 동일 — 모든 metric code를 한 번에 fetch 후 dict 매핑

#### 1.3 [HIGH / 수정 난이도: 쉬움] `news/api/views.py:329-343`
**`NewsViewSet.trending`** — 트렌딩 종목별 최근 뉴스 N+1
- **현상**: `for item in trending_data:` 루프(라인 331)에서 종목당
  ```python
  recent_articles = NewsArticle.objects.filter(
      entities__symbol=symbol,
      published_at__gte=from_date
  ).distinct().order_by('-published_at')[:3]
  ```
  - 종목 10개 × 1쿼리 = **10번 추가 쿼리**
- **권장 수정**: `Subquery` + `Window` 함수로 종목당 top3를 단일 쿼리로 처리하거나, 한 번에 모든 트렌딩 종목의 최근 100개 뉴스를 fetch 후 파이썬에서 그룹핑

#### 1.4 [MED / 수정 난이도: 쉬움] `chainsight/api/views.py:70-83`
**`ChainSightGraphView.get`** — 엣지별 market_signals 보강
- **현상**: `for edge in result.get("edges", []):` 루프에서 엣지마다
  - `CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()` (라인 76)
  - `PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()` (라인 78)
  - 엣지 N개 → **2N 쿼리**
- **권장 수정**: 모든 (symbol_a, symbol_b) 페어를 수집한 뒤 `CoMentionEdge.objects.filter(...).in_bulk()` 또는 `Q` 결합으로 단일 쿼리 fetch

#### 1.5 [MED / 수정 난이도: 쉬움] `validation/api/views.py:111-124`
**`ValidationSummaryView.get`** — rank_metrics 루프 N+1
- **현상**: 5개 rank_metrics × (CompanyBenchmarkDelta + MetricDefinition) = **10 쿼리**
- **권장 수정**: 5개 metric_code에 대해 한 번에 fetch

#### 1.6 [MED / 수정 난이도: 쉬움] `users/views.py:206, 234`
**`AddFavorite.post`, `RemoveFavorite.delete`**
- **현상**: `if stock in user.favorite_stock.all()` — 모든 즐겨찾기 stock을 풀 페치 후 in 검사
- **권장 수정**: `user.favorite_stock.filter(pk=stock_id).exists()` 한 줄로 SELECT 1 쿼리

#### 1.7 [MED / 수정 난이도: 쉬움] `news/api/views.py:89-99`
**`NewsViewSet.stock_news`** — entities prefetch 누락 + count 중복
- **현상**:
  - `prefetch_related('entities')` 누락 (NewsArticleListSerializer가 entities 참조 시 N+1)
  - `articles.count()` (라인 97)와 `serializer.data` (라인 98)가 별도 평가 → COUNT 쿼리 + SELECT 쿼리 분리
- **권장 수정**: `.prefetch_related('entities')` 추가, `articles = list(qs)` 후 `len(articles)` 사용

#### 1.8 [LOW / 수정 난이도: 쉬움] `news/api/views.py:271-274`
**`NewsViewSet.market`** — entities prefetch 누락
- **현상**: `NewsArticleListSerializer`가 entities를 참조하면 N+1
- **권장 수정**: `.prefetch_related('entities')` 추가 (line 274 chain에 삽입)

#### 1.9 [LOW / 수정 난이도: 쉬움] `users/views.py:482`
**`PortfolioBySymbolView.get`** — select_related 누락
- **현상**: 단건 조회이지만 `PortfolioSerializer`가 stock을 참조하면 추가 쿼리 발생
- **권장 수정**: `Portfolio.objects.select_related('stock').get(...)`

---

### 2. 인덱스 누락

#### 2.1 [HIGH / 수정 난이도: 쉬움] `config/settings.py:321-329`
**REST_FRAMEWORK 설정에 `DEFAULT_PAGINATION_CLASS` 누락 — 전역 영향**
- **현상**: REST_FRAMEWORK dict에 다음이 모두 없음
  - `DEFAULT_PAGINATION_CLASS`
  - `PAGE_SIZE`
  - 결과적으로 모든 ListAPIView/ViewSet이 페이지네이션 없이 전체 결과 반환
- **연쇄 영향**:
  - `stocks/views.py:75` `StockListAPIView` — Stock 전체 반환
  - `news/api/views.py:42` `NewsViewSet` — 뉴스 전체 반환
  - `users/views.py:90` `Users.get` — 사용자 전체 반환
- **권장 수정**:
  ```python
  REST_FRAMEWORK = {
      ...
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 50,
  }
  ```

#### 2.2 [참고 / 미확인] `stocks/models.py`, `news/models.py` 등 — 모델 파일 직접 읽기 불가
- 감사 도중 파일 시스템 접근이 일시 차단되어 모델 인덱스 정의를 직접 확인하지 못함
- 코드 사용 패턴 기준으로 인덱스가 필요할 가능성이 높은 필드:
  - `Stock.market_capitalization` (DESC 정렬, `stocks/views.py:68, 105` 등)
  - `Stock.symbol` (자주 unique 조회 — 이미 `db_index=True` 또는 `unique=True` 가능성 높음)
  - `Stock.sector` (필터)
  - `DailyPrice (stock_id, date DESC)` 복합 인덱스 — 차트/Overview에서 반복 사용
  - `BalanceSheet/IncomeStatement/CashFlowStatement (stock_id, period_type, fiscal_year DESC, fiscal_quarter DESC)` 복합 인덱스
  - `NewsArticle.published_at` (필터+정렬 매우 빈번)
  - `NewsArticle (category, published_at DESC)` 복합 인덱스
  - `NewsEntity (symbol, news_id)` 복합 인덱스
  - `DailyNewsKeyword.date` (`unique=True` 또는 `db_index=True` 권장)
  - `NewsCollectionLog (task_name, executed_at DESC)` 복합 인덱스
  - `MLModelHistory (deployment_status, trained_at DESC)` 복합 인덱스
  - `CompanyMetricSnapshot (symbol_id, metric_code_id, fiscal_year DESC)` 복합 인덱스
  - `CompanyBenchmarkDelta (symbol_id, fiscal_year, metric_code_id)` 복합 인덱스
  - `PeerListCache.symbol_id` (단건 조회)
  - `UserPeerPreference (user_id, symbol_id)` 복합 인덱스
  - `Portfolio (user_id, stock_id)`, `WatchlistItem (watchlist_id, stock_id)`
  - `UserInterest (user_id, created_at DESC)`
  - `UsageLog (user_id, created_at DESC)`
- **권장 후속 작업**: 위 필드별 `Meta.indexes` 정의 여부를 후속 감사에서 확인할 것

---

### 3. 느린 Serializer (SerializerMethodField)

#### 3.1 [MED / 수정 난이도: 중간] `users/serializers.py:95`
**`portfolio_weight = SerializerMethodField()`** — 포트폴리오 비중 계산
- **추정 패턴**: 비중 계산 시 전체 포트폴리오 가치를 매 row마다 다시 쿼리할 가능성
- **권장 수정**: 뷰에서 `total_portfolio_value`를 미리 계산해 `context`로 전달 (이미 `users/views.py:407, 463`에서 일부 적용됨 — 다른 호출 경로 점검 필요)

#### 3.2 [MED / 수정 난이도: 중간] `serverless/serializers.py:242-244, 327, 501-503`
**`is_owner`, `is_system`, `preset_name`, `can_trigger`, `cooldown_remaining_hours`** 등 다수 SerializerMethodField
- **추정 패턴**: 메서드 내부에서 외부 모델/캐시 조회 시 `many=True` 직렬화에서 N+1
- **권장 수정**: 직렬화 컨텍스트로 사전 계산값 전달, 또는 `annotate`로 쿼리셋 단계에서 컬럼 추가

#### 3.3 [LOW / 수정 난이도: 쉬움] `stocks/serializers.py:381-382`
**`latest_price`, `chart_data` SerializerMethodField**
- **추정 패턴**: 단건 직렬화에는 무해하나, `many=True` 사용 시 종목당 별도 쿼리 → N+1
- **권장 수정**: 호출 컨텍스트(단건 vs 다건)에 따라 `select_related`/`prefetch_related` 보장 또는 `annotate`로 최신값 미리 계산

> **참고**: serializer 파일 본문을 직접 읽지 못한 상태에서 필드 시그니처만 확인했으므로, 구체적 N+1 여부는 메서드 본문 검사 필요.

---

### 4. 페이지네이션 누락

| # | 위치 | 엔드포인트 | 심각도 | 난이도 |
|---|------|------------|--------|--------|
| 4.1 | `config/settings.py:321` | **전역 DEFAULT_PAGINATION_CLASS 누락** | HIGH | 쉬움 |
| 4.2 | `stocks/views.py:75` | `GET /api/v1/stocks/` (`StockListAPIView`) | HIGH | 쉬움 |
| 4.3 | `users/views.py:90` | `GET /api/v1/users/` (`Users.get`) | HIGH | 쉬움 |
| 4.4 | `news/api/views.py:42` | `GET /api/v1/news/` (`NewsViewSet` 기본 list) | MED | 쉬움 |
| 4.5 | `news/api/views.py:89` | `GET /api/v1/news/stock/{symbol}/` (`stock_news`) | MED | 쉬움 |
| 4.6 | `users/views.py:187` | `GET /api/v1/users/favorites/` (`UserFavorites.get`) | MED | 쉬움 |
| 4.7 | `users/views.py:967` | `GET /api/v1/users/interests/` (`UserInterestListCreateView.get`) | MED | 쉬움 |
| 4.8 | `rag_analysis/views.py:71` | `GET /api/v1/rag/baskets/` (`DataBasketListCreateView.get`) | MED | 쉬움 |
| 4.9 | `rag_analysis/views.py:431` | `GET /api/v1/rag/sessions/` (`AnalysisSessionListCreateView.get`) | MED | 쉬움 |

> **참고**: `users/views.py:580` `WatchlistListCreateView`, `users/views.py:792` `WatchlistStocksView`, `rag_analysis/views.py:764` `UsageHistoryView`, `news/api/views.py:351` `all_news`는 **자체 페이지네이션을 구현**하여 양호.

---

## 권장 수정 우선순위 (Top 5)

| 순위 | 항목 | 효과 | 난이도 |
|------|------|------|--------|
| 1 | `config/settings.py` — `DEFAULT_PAGINATION_CLASS` 추가 | 다수 list 엔드포인트 응답 크기 폭주 방지 (전역) | 쉬움 |
| 2 | `validation/api/views.py:219-300` — `_build_metric` 일괄 fetch 리팩터링 | 350+ 쿼리 → 5개 이하 (수십 배 응답 단축) | 중간 |
| 3 | `validation/api/views.py:361-400` — `LeaderComparisonView` 메트릭 일괄 fetch | 150 쿼리 → 5개 이하 | 중간 |
| 4 | `news/api/views.py:329-343` — `trending` 종목별 최근 뉴스 단일 쿼리화 | 11 쿼리 → 2 쿼리 | 쉬움 |
| 5 | `chainsight/api/views.py:70-83` — `ChainSightGraphView` market_signals 일괄 fetch | 2N 쿼리 → 2 쿼리 | 쉬움 |

---

## 한계 (Disclosure)

- **모델 인덱스 직접 감사 미완료**: 감사 후반에 working directory 일시 접근 차단으로 `stocks/models.py` 등 모델 파일 본문을 직접 확인하지 못함. 인덱스 누락 항목(2.2)은 view에서 관찰된 사용 패턴 기반 **권장 후속 점검** 형태로 기록.
- **Serializer 본문 일부 미확인**: `users/serializers.py`, `serverless/serializers.py`, `stocks/serializers*.py`의 SerializerMethodField 시그니처는 식별했으나, 일부 메서드 본문을 직접 검사하지 못해 N+1 여부는 **추정**으로 기록.
- **`serverless/views.py` 함수 기반 view 3,400줄 중 캐시-우선 패턴이 다수 — 본 보고서는 핵심 클래스 기반 view에 우선순위를 두고 분석함. 후속 감사 시 `serverless/views.py` 캐시 미스 경로의 쿼리 패턴 별도 점검 권장.**
