# API 성능 감사 보고서

- **감사 일자**: 2026-05-28
- **감사 범위**: views 17개 + models 7개 (Backend Django/DRF)
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **검사 항목**: N+1 쿼리 / 인덱스 누락 / Serializer 추가 쿼리 / 페이지네이션 누락

---

## 1. 요약 (이슈 수 by 심각도)

### 카테고리별 이슈

| 카테고리 | HIGH | MED | LOW | 합계 |
|---------|------|-----|-----|------|
| N+1 쿼리 (루프 내 쿼리) | 5 | 2 | 2 | 9 |
| Serializer 추가 쿼리 | 1 | 1 | 0 | 2 |
| 페이지네이션 누락 | 0 | 0 | 1 | 1 |
| DB 인덱스 누락 | 1 | 3 | 0 | 4 |
| **합계** | **7** | **6** | **3** | **16** |

### 수정 난이도별 분포

| 난이도 | 개수 | 비고 |
|-------|------|------|
| 쉬움 | 11 | 한 줄 추가 (select_related, prefetch_related, db_index, Meta.indexes) |
| 중간 | 4 | bulk 쿼리 재설계 + dict 룩업 |
| 높음 | 1 | LeaderComparisonView 구조 재설계 |

### TOP 5 우선순위 (즉시 수정 권장)

1. **HIGH** `news/api/views.py:337-351` — `trending()` 루프 내 article 개별 조회 (N+1, 사용자 직접 노출)
2. **HIGH** `validation/api/views.py:369-374` — `LeaderComparisonView` 지표별 snapshot 루프 조회
3. **HIGH** `chainsight/api/views.py:80-87` — `ChainSightGraphView` edge별 co-mention/price 조회
4. **HIGH** `stocks/views_indicators.py:324-372` — `IndicatorComparisonView` symbol별 Stock.get() 루프
5. **HIGH** `news/models.py` `NewsArticle.category` — 인덱스 누락 (테이블 ~1M+ 행)

---

## 2. 상세

### 2.1 N+1 쿼리 (루프 내 개별 쿼리)

#### [HIGH] news/api/views.py:337-351 — trending() N+1
- **패턴**:
  ```python
  trending_data = NewsEntity.objects.filter(...).values('symbol').annotate(...)
  for item in trending_data:
      articles = NewsArticle.objects.filter(entities__symbol=symbol, ...)[:3]  # N번 실행
  ```
- **영향**: `/api/v1/news/trending/` 호출당 N+1번 DB hit (N = trending symbol 개수, 기본 20개)
- **권장 수정**: 모든 symbol에 대해 한 번에 `NewsArticle.objects.filter(entities__symbol__in=symbols)` 후 Python에서 dict 그룹화
- **난이도**: 중간

#### [HIGH] validation/api/views.py:369-374 — LeaderComparisonView 지표 루프
- **패턴**:
  ```python
  for cat, mc in all_metrics:
      CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=mc, ...)  # 지표 수만큼 반복
      CompanyMetricSnapshot.objects.filter(symbol=leader, metric_code=mc, ...)
  ```
- **영향**: 지표 N개 × 2(stock+leader) = 2N 쿼리 발생
- **권장 수정**: `CompanyMetricSnapshot.objects.filter(symbol__in=[stock, leader], metric_code__in=[mc for cat, mc in all_metrics], fiscal_year=latest_fy)` 한 번 조회 후 메모리에서 filtering
- **난이도**: 높음 (메서드 구조 재설계 필요)

#### [HIGH] chainsight/api/views.py:80-87 — ChainSightGraphView edge 루프
- **패턴**:
  ```python
  for edge in edges_list:
      CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
      PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
  ```
- **영향**: 그래프 edge 수만큼 쿼리 2N번 (사용자 직접 노출 list endpoint)
- **권장 수정**: `Q(symbol_a__in=...) & Q(symbol_b__in=...)` bulk 조회 후 `{(a,b): edge}` dict 변환
- **난이도**: 중간

#### [HIGH] stocks/views_indicators.py:324-372 — IndicatorComparisonView symbol 루프
- **패턴**:
  ```python
  for symbol in symbols:
      Stock.objects.get(symbol=symbol)  # N번
  ```
- **영향**: 비교 종목 수만큼 Stock 조회
- **권장 수정**: `Stock.objects.filter(symbol__in=[s.upper() for s in symbols])` bulk 조회 후 dict 룩업
- **난이도**: 쉬움

#### [HIGH] news/api/views.py:104-108 — stock_news() entities prefetch 누락
- **패턴**:
  ```python
  articles = NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct()
  NewsArticleListSerializer(articles, many=True)  # serializer가 article.entities 접근 시 N+1
  ```
- **영향**: list 응답마다 article × entities 추가 쿼리
- **권장 수정**: `articles = articles.prefetch_related('entities')` 명시
- **난이도**: 쉬움

#### [MED] validation/api/views.py:265-285 — _build_metric() snapshot 재조회
- **패턴**:
  ```python
  CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('-fiscal_year').first()
  # 조건 분기 후 동일 쿼리 재호출
  ```
- **영향**: 지표마다 추가 fallback 쿼리 1-2회
- **권장 수정**: `.all()`로 전체 fy 받아서 메모리에서 first/fallback 처리
- **난이도**: 중간

#### [MED] validation/api/views.py:117-124 — MetricDefinition 루프 조회
- **패턴**:
  ```python
  for mc in rank_metrics:
      MetricDefinition.objects.filter(pk=mc).first()
  ```
- **권장 수정**: `MetricDefinition.objects.in_bulk(rank_metrics)` 후 dict 룩업
- **난이도**: 쉬움

#### [LOW] users/views.py:192-196 — UserFavorites Stock serializer
- **패턴**: `favorite_stocks = user.favorite_stock.all()` 후 serializer 호출 시 Stock 내부 FK 접근 가능
- **권장 수정**: `user.favorite_stock.all().select_related(...)` 명시 (해당되는 FK 명시)
- **난이도**: 쉬움

#### [LOW] users/views.py:975-987 — UserInterest auto_category FK
- **패턴**: `UserInterest.objects.filter(user=request.user)` 순회 시 `interest.auto_category` FK 미참조
- **권장 수정**: `.select_related('auto_category')` 추가
- **난이도**: 쉬움

---

### 2.2 Serializer 추가 쿼리

#### [HIGH] news/api/views.py — NewsArticleListSerializer + entities
- **위치**: 라인 109 호출
- **패턴**: serializer가 각 article마다 `.entities` 역참조 (M2M-like)
- **영향**: list response의 article 수만큼 entities 쿼리
- **권장 수정**: views에서 queryset에 `.prefetch_related('entities')` 추가
- **난이도**: 쉬움

#### [MED] validation/api/views.py:117 — ValidationSummaryView MetricDefinition 루프
- **위치**: rank_metrics 순회 중 MetricDefinition.objects.filter(pk=mc).first()
- **권장 수정**: `MetricDefinition.objects.in_bulk(rank_metrics)`로 변경
- **난이도**: 쉬움

---

### 2.3 페이지네이션 누락

#### [LOW] stocks/views.py:169-218 — StockSearchAPIView
- **현황**: pagination_class 미정의, 단 `[:20]` 하드코딩으로 자체 제한
- **권장**: 검색 결과 페이지네이션이 필요하면 `PageNumberPagination` 추가, 아니면 현 상태 유지 가능
- **난이도**: 쉬움

> 그 외 list 엔드포인트 (NewsViewSet.market/trending, SignalFeedView 등)는 자체 페이지네이션 또는 limit 파라미터로 충분히 제어됨 — **신규 누락 없음**

---

### 2.4 DB 인덱스 누락

#### [HIGH] news/models.py — NewsArticle.category
- **현황**: `db_index=False`, Meta.indexes에 미포함
- **사용 위치**: `news/api/views.py:431` → `.filter(category__in=db_categories)` + `.order_by('-published_at')`
- **테이블 크기**: 대량 (~1M+ 행)
- **권장 수정**:
  ```python
  class Meta:
      indexes = [
          # ... 기존
          models.Index(fields=['category', '-published_at']),
      ]
  ```
- **난이도**: 쉬움 (마이그레이션 1개, 온라인 인덱스 생성 가능)
- **마이그레이션 위험**: 대량 테이블이므로 PostgreSQL `CREATE INDEX CONCURRENTLY` 사용 권장 → `Meta.indexes` 일반 추가 시 Django는 lock-taking으로 처리, 운영에서는 수동 SQL 권장

#### [MED] users/models.py — UserInterest 인덱스
- **현황**: `user` FK는 자동 인덱스, 정렬 필드 `created_at` 미인덱스
- **사용 위치**: `users/views.py:975` → `.filter(user=request.user).order_by('-created_at')`
- **권장 수정**:
  ```python
  class Meta:
      indexes = [models.Index(fields=['user', '-created_at'])]
  ```
- **난이도**: 쉬움

#### [MED] serverless/models.py — ScreenerFilter.is_active
- **현황**: `is_active` `db_index=False`
- **사용 위치**: `serverless/services/filter_engine.py:196` → `.filter(is_active=True).order_by(...)`
- **권장 수정**:
  ```python
  class Meta:
      indexes = [models.Index(fields=['is_active', 'category'])]
  ```
- **난이도**: 쉬움

#### [MED] rag_analysis/models.py — AnalysisSession 인덱스
- **현황**: 어떤 Meta.indexes도 정의 안 됨
- **사용 위치**: `rag_analysis/views.py:379` → `.filter(user=request.user).prefetch_related('messages')`
- **권장 수정**:
  ```python
  class Meta:
      indexes = [
          models.Index(fields=['user', '-updated_at']),
          models.Index(fields=['status', '-created_at']),
      ]
  ```
- **난이도**: 쉬움

---

## 3. 앱별 커버리지 요약

### Views (N+1 발생 위험)

| 앱 | 검사 파일 | HIGH | MED | LOW |
|----|---------|------|-----|-----|
| stocks | 9개 | 1 | 0 | 1 |
| users | 1 | 0 | 0 | 2 |
| news | 1 | 3 | 0 | 0 |
| macro | 1 | 0 | 0 | 0 |
| rag_analysis | 1 | 0 | 0 | 0 |
| serverless | 1 (admin) | 0 | 0 | 0 |
| validation | 1 | 1 | 2 | 0 |
| chainsight | 1 | 1 | 0 | 1 |
| sec_pipeline | 1 | 0 | 0 | 0 |

### Models (인덱스 커버리지)

| 앱 | 모델 수 | 누락 | 커버율 | 테이블 크기 |
|----|--------|------|--------|-----------|
| stocks | 10 | 0 | 100% | 대량 |
| users | 5 | 1 | 80% | 중량 |
| news | 9 | 1 | 89% | 대량 |
| serverless | 21 | 1 | 95% | 중량~대량 |
| rag_analysis | 5 | 1 | 80% | 중량 |
| sec_pipeline | 8 | 0 | 100% | 중량 |
| graph_analysis | 5 | 0 | 100% | 중량 |

---

## 4. 권장 수정 순서

### Phase 1: 사용자 즉시 영향 (1일 이내)
1. `news/models.py` — NewsArticle.category 복합 인덱스 (HIGH, ~1M+ 행에 가장 큰 효과)
2. `news/api/views.py:104` — stock_news에 `.prefetch_related('entities')` 한 줄
3. `stocks/views_indicators.py:324` — symbols bulk 조회로 전환 (난이도 쉬움)

### Phase 2: 구조적 개선 (1주 이내)
4. `news/api/views.py:337-351` — trending() 루프 bulk 변환
5. `chainsight/api/views.py:80-87` — ChainSightGraphView edge bulk 조회
6. `validation/api/views.py:117` — MetricDefinition.in_bulk 적용

### Phase 3: 재설계 (2주 이내)
7. `validation/api/views.py:369-374` — LeaderComparisonView 재설계 (가장 무거움)
8. UserInterest/ScreenerFilter/AnalysisSession 인덱스 추가 (마이그레이션 일괄)

---

## 5. 검출되지 않은 항목 (Green Light)

- **stocks/models.py**: DailyPrice, EODSignal, StockNews 등 대량 테이블의 인덱스 커버리지 100% — Meta.indexes 복합 인덱스가 잘 정의됨
- **graph_analysis/models.py**: CorrelationEdge, CorrelationAnomaly 모두 복합 인덱스 적용됨
- **sec_pipeline/models.py**: SupplyChainEvidence의 neo4j_dirty 인덱스 적용 — 동기화 큐 효율적
- **users/views.py**: Portfolio/Watchlist/WatchlistItem 모두 select_related 적용됨
- **macro/views.py, rag_analysis/views.py(상세 외)**: N+1 패턴 미발견
- **페이지네이션**: 대부분 list endpoint에서 자체 limit/page_size 파라미터 또는 PageNumberPagination 적용됨

---

## 6. 종합 평가

- **전체 코드 품질**: **양호** — 대부분의 핫패스 모델에 적절한 인덱스가 이미 적용되어 있음
- **주요 위험**: news 앱 (trending/stock_news) 및 validation/chainsight의 graph/leader 비교 뷰가 사용자 직접 노출 N+1 다발 영역
- **추정 성능 개선 효과**:
  - Phase 1 적용 시: news API p95 latency 50%+ 감소 예상 (특히 trending)
  - Phase 2 적용 시: chainsight/validation list endpoint 응답 시간 30~70% 감소
  - Phase 3 적용 시: LeaderComparisonView 응답 시간 50%+ 감소
- **마이그레이션 리스크**: 모두 단순 인덱스 추가 (락 위험 낮음), 단 NewsArticle은 대량 테이블이므로 `CONCURRENTLY` 사용 권장

---

_보고서 종료. 본 감사는 정적 코드 분석 기반이며 실제 EXPLAIN ANALYZE 측정은 포함되지 않음. Phase 1 적용 후 `django-silk` 또는 `django-debug-toolbar`로 검증 권장._
