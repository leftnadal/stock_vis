# API 성능 감사 보고서

**작성일**: 2026-05-23
**대상**: Stock-Vis 백엔드 (17개 view 파일 + 7개 모델 파일)
**모드**: 읽기 전용 감사 (코드 수정 없음)
**감사 방식**: Explore 에이전트 3개 병렬 실행 (views 영역 2개 + models 영역 1개)

---

## 요약

### 이슈 수 by 심각도

| 심각도 | 건수 | 주요 영역 |
|--------|------|----------|
| **HIGH** | **6** | validation N+1 (3), stocks serializer N+1 (1), news trending N+1 (1), 재무제표 복합 인덱스 (1) |
| **MED** | **9** | 페이지네이션 누락, prefetch 누락, count 중복, 단일 인덱스 누락 |
| **LOW** | **6** | 마이크로 최적화, 캐시 도입, 잠재 위험 |
| **합계** | **21** | — |

### 수정 난이도 분포

| 난이도 | 건수 | 비고 |
|--------|------|------|
| 쉬움 | 12 | 1줄~10줄 수정 |
| 중간 | 8 | 쿼리 재구성, prefetch 도입, 복합 인덱스 |
| 높음 | 1 | 페이지네이션 도입(스키마/계약 영향) |

### 영역별 hot spot

| 영역 | HIGH | MED | LOW | 합 |
|------|------|-----|-----|----|
| validation/api | **3** | 0 | 0 | 3 |
| stocks (views+serializers) | 1 | 3 | 3 | 7 |
| news/api | 1 | 1 | 1 | 3 |
| users | 0 | 1 | 1 | 2 |
| rag_analysis | 0 | 1 | 1 | 2 |
| serverless/admin | 0 | 1 | 1 | 2 |
| macro | 0 | 1 | 0 | 1 |
| stocks/models 복합 인덱스 | 1 | 0 | 0 | 1 |
| sec_pipeline/models | 0 | 1 | 0 | 1 |
| chainsight, sec_pipeline views | 0 | 0 | 0 | 0 (양호) |

### 🔥 즉시 조치 권장 (우선순위 1)

1. **validation/api/views.py** — `_build_category`, `LeaderComparisonView`, `_build_metric`에서 메트릭 코드 루프 내 개별 쿼리 (HIGH × 3)
2. **stocks/serializers.py** — `OverviewTabSerializer.get_dynamic_layers`에서 6개 OneToOne 개별 fetch (HIGH × 1)
3. **stocks/models.py** — `BalanceSheet/IncomeStatement/CashFlowStatement`에 `(stock, period_type, -fiscal_year)` 복합 인덱스 (HIGH × 1)

---

## 상세

### 1. N+1 쿼리 / 루프 내 개별 쿼리

#### 1-1. [HIGH] validation/api/views.py:204-208 — ValidationMetricsView._build_category

```python
metrics_data = []
for mc in metric_codes:
    md = MetricDefinition.objects.filter(pk=mc).first()  # 루프 내 쿼리
    if not md:
        continue
    metrics_data.append(self._build_metric(stock, md))
```

- **문제**: 카테고리당 메트릭 코드(10~50개)마다 MetricDefinition 개별 조회. 카테고리 N개 × 메트릭 M개 = N×M 쿼리.
- **권장**: `MetricDefinition.objects.filter(pk__in=list(metric_codes))`로 한 번에 로드 후 dict로 매핑.
- **난이도**: 쉬움

#### 1-2. [HIGH] validation/api/views.py:364-378 — LeaderComparisonView

```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()
    company_snap = CompanyMetricSnapshot.objects.filter(
        symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
    leader_snap = CompanyMetricSnapshot.objects.filter(
        symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
```

- **문제**: 메트릭별로 3개 쿼리 반복. 메트릭 30~50개 기준 90~150 쿼리.
- **권장**:
  - `MetricDefinition.objects.in_bulk(pks)` 로 일괄 로드
  - `CompanyMetricSnapshot.objects.filter(metric_code_id__in=...).filter(symbol__in=[stock, leader.symbol], fiscal_year=latest_fy, value_status='normal')` 한 번에 로드 후 `{(symbol_id, metric_code_id): snap}` 딕셔너리로 인덱싱
- **난이도**: 중간

#### 1-3. [HIGH] validation/api/views.py:263-285 — _build_metric history 루프

```python
snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('fiscal_year')[:5]
for s in snaps:
    peer_bench = PeerMetricBenchmark.objects.filter(
        symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
    ).first()  # 메트릭당 최대 5 쿼리
```

- **문제**: 각 history 항목(최대 5개)마다 PeerMetricBenchmark 조회. 메트릭 N개 × 5 fiscal_year = 5N 쿼리.
- **권장**: `PeerMetricBenchmark.objects.filter(symbol=stock, metric_code=md, fiscal_year__in=fiscal_years)`로 한 번에 fetch 후 dict 매핑.
- **난이도**: 중간

#### 1-4. [HIGH] stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers

```python
def get_dynamic_layers(self, obj):
    signals = list(obj.category_signals.all())          # 1
    ns = obj.validation_news_summary                     # 2
    sp = obj.sensitivity_profile                          # 3
    gs = obj.growth_stage                                 # 4
    cd = obj.capital_dna                                  # 5
    nt = obj.narrative_tag                                # 6
```

- **문제**: OneToOne/reverse FK 6개를 매 직렬화마다 개별 쿼리. 목록 모드(many=True)에서는 객체 N개 × 6+ 쿼리.
- **권장 (StockOverviewAPIView.get)**:
  ```python
  Stock.objects.select_related(
      'overview_ko', 'validation_news_summary', 'sensitivity_profile',
      'growth_stage', 'capital_dna', 'narrative_tag'
  ).prefetch_related('category_signals').get(symbol=symbol)
  ```
- **난이도**: 중간 (단건 detail이면 즉시 효과, 목록 사용 여부에 따라 영향 큼)

#### 1-5. [HIGH] news/api/views.py:344-358 — trending() 루프

```python
for item in trending_data:
    recent_articles = NewsArticle.objects.filter(
        entities__symbol=item['symbol'],
        published_at__gte=from_date,
    ).distinct().order_by('-published_at')[:3]
```

- **문제**: trending limit(예: 10~20) 행마다 NewsArticle 추가 조회.
- **권장**:
  ```python
  symbols = [it['symbol'] for it in trending_data]
  articles = NewsArticle.objects.filter(
      entities__symbol__in=symbols, published_at__gte=from_date
  ).order_by('-published_at')
  # Python에서 symbol별 그룹화 + 상위 3개 슬라이스
  ```
- **난이도**: 중간

#### 1-6. [MED] news/api/views.py:144-194 — stock_sentiment 루프 평균 계산

```python
entities = NewsEntity.objects.filter(symbol=symbol, news__published_at__gte=from_date).select_related('news')
sentiment_scores = [e.sentiment_score for e in entities if e.sentiment_score is not None]
```

- **문제**: 전체 entity를 메모리로 로드 후 파이썬 평균. select_related로 N+1은 막혔으나 데이터 크기가 클 경우 메모리 사용량 큼.
- **권장**: `entities.filter(sentiment_score__isnull=False).aggregate(avg=Avg('sentiment_score'), n=Count('id'))`. 시간대별 비교는 `Case/When` 사용.
- **난이도**: 쉬움

#### 1-7. [MED] serverless/views_admin.py:472-497 — AdminNewsCategoryView resolve_symbols 루프

```python
for cat in categories:
    symbols = cat.resolve_symbols()
```

- **문제**: 카테고리 객체마다 `resolve_symbols()` 내부에서 DB 조회 가능 (SP500Constituent 필터 등).
- **권장**: 카테고리 리스트의 모든 sector/sub_sector를 모아서 한 번의 `SP500Constituent.objects.filter(...).values('symbol','sector','sub_sector')`로 로드 → 파이썬에서 분류. 또는 결과를 단기 캐시.
- **난이도**: 중간

#### 1-8. [LOW] users/views.py:462-471 — PortfolioDetailTableView.patch 재집계

```python
total_portfolio_value = Portfolio.objects.filter(user=request.user).aggregate(
    total=Sum(F('quantity') * F('stock__real_time_price'))
)['total'] or 0
```

- **문제**: 상단에서 로드한 `portfolios` 쿼리셋을 재활용하지 않고 JOIN 집계 재실행.
- **권장**: 위에서 select_related된 결과를 파이썬 합으로 처리. 단일 PATCH 요청 영향은 작음.
- **난이도**: 쉬움

---

### 2. 페이지네이션 누락 / 비표준 페이지네이션

#### 2-1. [MED] news/api/views.py:408-435 — all_news() 수동 offset/limit

```python
total_count = queryset.count()
articles = queryset.order_by('-published_at')[offset:offset + limit]
```

- **문제**: DRF `pagination_class` 미적용. 표준 응답 포맷(next/previous) 부재.
- **권장**: `PageNumberPagination` 또는 `LimitOffsetPagination`을 ViewSet에 부여.
- **난이도**: 쉬움

#### 2-2. [MED] macro/views.py:25-73 — 전체 dashboard 일괄 반환

```python
class MarketPulseView(APIView):
    def get(self, request):
        data = service.get_market_pulse_dashboard()
        return Response(MarketPulseResponseSerializer(data).data)
```

- **문제**: 서비스에서 만든 데이터를 통째 반환. 캘린더 등 대량 항목이 들어오면 응답 폭주.
- **권장**: 큰 리스트는 `limit/offset` 파라미터 + 페이지네이션. 또는 섹션 단위 GET (`?section=calendar`).
- **난이도**: 중간 ~ 높음 (스펙 영향)

#### 2-3. [MED] stocks/views_search.py:200-212 — len(stocks) 사용

```python
stocks = Stock.objects.filter(...).order_by('symbol')[:20]
return Response({'results': serializer.data, 'count': len(stocks), ...})
```

- **문제**: 슬라이스 후 `len()`은 결과 fetch 강제. 표준 페이지네이션 미사용.
- **권장**: 별도 `Stock.objects.filter(...).count()` 또는 페이지네이션 클래스 부여.
- **난이도**: 쉬움

---

### 3. SerializerMethodField / Serializer 비효율

#### 3-1. [MED] rag_analysis/views.py:52, 379 — DataBasket/AnalysisSession 목록 prefetch

- 현재 `prefetch_related('items')`, `prefetch_related('messages')` 적용 중이나, `DataBasketSerializer.get_can_add_item()` 등이 `basket.items.count()`를 호출하면 prefetch 캐시 활용 가능. `SerializerMethodField`가 `.filter().count()`처럼 새 쿼리를 일으키지 않도록 점검 필요.
- **권장**: `annotate(items_count=Count('items'))` 후 method에서 사용. 메소드 내 추가 필터 쿼리는 prefetch와 호환되도록 Python에서 처리.
- **난이도**: 쉬움 ~ 중간

#### 3-2. [MED] stocks/views.py:837-884 — StockCompleteDataAPIView

- BalanceSheet/IncomeStatement/CashFlowStatement 각각 5개씩 fetch. 현재 직접적 N+1은 없으나 향후 serializer에 `stock` FK 접근 메서드 필드 추가 시 즉시 N+1.
- **권장**: 쿼리 시 `.select_related('stock')` 명시. 동일한 stock 객체이므로 사실상 1행 fetch.
- **난이도**: 쉬움

---

### 4. 인덱스 누락 / 복합 인덱스 권고

#### 4-1. [HIGH] stocks/models.py:359-431 — 재무제표 복합 인덱스

대상: `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`

```python
# 현재
Meta.indexes = [..., models.Index(fields=['stock', '-fiscal_year']), ...]

# 빈번 쿼리 (stocks/views.py:646 등)
.objects.filter(stock=stock, period_type=db_period).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
```

- **권장**: `models.Index(fields=['stock', 'period_type', '-fiscal_year'])` 추가.
- **난이도**: 중간 (3개 모델 × 1 migration)

#### 4-2. [MED] sec_pipeline/models.py:283 — CompanyAlias.ticker

- 현재 ticker 단일 인덱스 없음 (alias+context_sector unique만 존재).
- ticker로 역조회하는 배치/뷰에서 풀스캔 가능성.
- **권장**: `models.Index(fields=['ticker'])`.
- **난이도**: 쉬움

#### 4-3. [LOW] stocks/models.py:24-25 — Stock.exchange / Stock.currency

- 현재 `sector`, `industry`는 인덱싱. `exchange`, `currency` 필터 사용 시 풀스캔.
- **권장**: 필터링 빈도 측정 후 `db_index=True` 부여.
- **난이도**: 쉬움

#### 4-4. [LOW] stocks/models.py:30 — RawDocumentStore.fiscal_year

- `(symbol, -filing_date)` 복합 인덱스로 대부분 커버. fiscal_year 단독 필터가 자주 쓰이면 검토.
- **난이도**: 쉬움

#### 4-5. 검토 결과 양호 (인덱싱 완료)

- **users/models.py**: Portfolio/Watchlist/WatchlistItem 모두 적절한 복합 인덱스 보유.
- **news/models.py**: NewsArticle `(-published_at, category)`, NewsEntity `(symbol, entity_type)`+`sentiment_score`, DailyNewsKeyword `(-date, status)`, NewsCollectionLog `(provider, -executed_at)` 모두 OK.
- **serverless/models.py**: MarketMover, ScreenerPreset, ScreenerAlert, AlertHistory, CategoryCache 모두 인덱싱 양호.
- **rag_analysis/models.py**: UsageLog 4종 복합 인덱스 적용.
- **graph_analysis/models.py**: 모든 모델 인덱스 양호.
- **sec_pipeline/models.py**: SupplyChainEvidence.neo4j_dirty, UnmatchedCompanyQueue.status 인덱싱 OK.

---

### 5. 쿼리 효율 (count, list 중복)

#### 5-1. [LOW] stocks/views.py:284, 290 — price_data.count() 중복 호출

```python
if price_data.count() > 0:
    response_data = {'count': price_data.count(), ...}  # 동일 쿼리 2회
```

- **권장**: 변수 캐시: `count = price_data.count()`.
- **난이도**: 쉬움

#### 5-2. [LOW] news/api/views.py:481-495 — sources() 3회 count

```python
finnhub_count = NewsArticle.objects.filter(published_at__gte=from_date, finnhub_id__isnull=False).count()
marketaux_count = NewsArticle.objects.filter(published_at__gte=from_date, marketaux_uuid__isnull=False).count()
total_count = NewsArticle.objects.filter(published_at__gte=from_date).count()
```

- **권장**:
  ```python
  qs = NewsArticle.objects.filter(published_at__gte=from_date)
  agg = qs.aggregate(
      total=Count('id'),
      finnhub=Count('id', filter=Q(finnhub_id__isnull=False)),
      marketaux=Count('id', filter=Q(marketaux_uuid__isnull=False)),
  )
  ```
- **난이도**: 쉬움

#### 5-3. [LOW] serverless/views_admin.py:663-691 — AdminNewsSectorOptionsView

- 동일 `is_active=True` 필터를 두 번 적용해 sectors/sub_sectors 각각 집계. 큰 비용은 아니나 캐시 또는 한 번의 group-by로 묶을 수 있음.
- **난이도**: 쉬움

#### 5-4. [LOW] rag_analysis/views.py:256-261 — add_item .first()

- unique 제약 보유 시 `.exists()` 또는 `try: create except IntegrityError`로 단순화 가능.
- **난이도**: 쉬움

#### 5-5. [LOW] stocks/views_indicators.py:333-340 — list(reversed(...))

- `[:50]` 슬라이스 + values_list라서 메모리 영향 작음. 종목 수가 많아질 경우 주의.
- **난이도**: 쉬움

---

### 6. 양호 (이슈 없음)

| 영역 | 비고 |
|------|------|
| stocks/views_exchange.py | 외부 API(FMP) 호출만, DB 쿼리 없음 |
| stocks/views_screener.py | 메모리/외부 처리 위주 |
| stocks/views_market_movers.py | 외부 API 호출만 |
| stocks/views_fundamentals.py | 외부 API 호출만 |
| stocks/views_eod.py | `select_related('stock')` 적용, 정렬 인덱싱 OK |
| stocks/views_mvp.py | 페이지네이션/select_related 적정 |
| users/views.py (Watchlist/Portfolio) | prefetch+select_related, 페이지네이션 모두 적용 |
| chainsight/api/views.py | Stock bulk map 적용, N+1 회피 |
| sec_pipeline/views.py | template view (API 아님) |
| users/models.py, graph_analysis/models.py | 인덱스 적정 |

---

## 우선순위 로드맵

### Phase 1 — 1~2주 내 (HIGH 6건)

| # | 이슈 | 파일 | 난이도 |
|---|------|------|-------|
| 1 | ValidationMetricsView `_build_category` 루프 | validation/api/views.py:204 | 쉬움 |
| 2 | LeaderComparisonView 3중 쿼리 루프 | validation/api/views.py:364 | 중간 |
| 3 | _build_metric history 루프 | validation/api/views.py:263 | 중간 |
| 4 | OverviewTabSerializer N+1 | stocks/serializers.py:205 + stocks/views.py | 중간 |
| 5 | news/api trending 루프 | news/api/views.py:344 | 중간 |
| 6 | 재무제표 복합 인덱스 | stocks/models.py:359-431 + migration | 중간 |

### Phase 2 — 2~4주 내 (MED 9건)

- 페이지네이션 정비 (news.all_news, macro, search)
- DataBasket/AnalysisSession serializer annotate
- StockCompleteData select_related 보강
- AdminNewsCategoryView resolve_symbols bulk화
- CompanyAlias.ticker 인덱스
- stock_sentiment 집계 DB 이전
- Portfolio PATCH 재집계 제거

### Phase 3 — 4주+ (LOW 6건)

- count 중복 제거, aggregate 통합, exchange/currency 인덱스 검토, list() 메모리 최적화 등

---

## 부록 — 감사 메모

- chainsight/sec_pipeline의 grouping/bulk-map 패턴은 다른 영역(validation, news trending)에 동일하게 적용 가능한 참조 모델.
- 외부 API 호출 view(stocks/views_exchange, market_movers, fundamentals, screener)는 DB 성능 관점에서 이슈 없음. 별도의 외부 API rate-limit/캐시 감사가 필요할 수 있음 (본 보고서 범위 외).
- 본 보고서는 정적 분석 기반. 실제 우선순위는 슬로우 쿼리 로그(`django-debug-toolbar`/`pg_stat_statements`)로 재확인 권장.
