# API 성능 감사 보고서

> 감사일: 2026-05-02
> 범위: stocks/, users/, news/, macro/, rag_analysis/, serverless/, validation/, chainsight/, sec_pipeline/, graph_analysis/
> 모드: 읽기 전용 (코드 수정 없음)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 쿼리 | 페이지네이션 누락 | 인덱스 누락 | 느린 Serializer | 합계 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **HIGH** | 5 | 3 | 0 | 0 | **8** |
| **MED** | 7 | 5 | 1 | 3 | **16** |
| **LOW** | 1 | 1 | 2 | 0 | **4** |
| **합계** | 13 | 9 | 3 | 3 | **28** |

### 핵심 결론

1. **글로벌 페이지네이션 부재가 가장 큰 위험**: `config/settings.py:341`의 `REST_FRAMEWORK` 딕셔너리에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 둘 다 미설정. 모든 ListAPIView/list 액션이 전체 결과를 반환할 수 있어 SP500 규모(500+)에서 시작해 운영 데이터 누적 시 응답 크기·DB·메모리 모두 폭주 가능.
2. **Validation 모듈이 N+1 핫스팟**: `ValidationMetricsView`, `LeaderComparisonView`는 카테고리×메트릭×히스토리 3중 루프 안에서 단건 ORM 쿼리를 반복. 호출 한 번에 500쿼리 이상 발생 가능 — DB 사이드에서 가장 비싼 엔드포인트.
3. **OverviewTabSerializer가 캐시되더라도 위험**: `dynamic_layers` 필드가 7개 reverse relation을 접근하는데 `select_related`는 `overview_ko` 1개만. TODO 주석 본인이 인지(`stocks/views.py:491`).
4. **인덱스는 전반적으로 양호**: 13개 검사 모델 중 대부분 적절한 `db_index` / `Meta.indexes` 보유. 실제 운영 가속화 우선순위는 인덱스보다 쿼리 패턴 개선이 압도적.

---

## 상세

### 1. N+1 쿼리

#### [HIGH-1] `stocks/serializers.py:398-409` — WatchListStockSerializer.get_latest_price/get_chart_data
**파일:라인**: `stocks/serializers.py:398-409`
**난이도**: 쉬움
**설명**:
```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
    ...
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
    # ⚠️ return 문 누락 — 별개 결함이지만 동일 라인
```
Watchlist에 N개 종목이 있을 때 종목당 `DailyPrice` 쿼리 2회 → **2N 추가 쿼리**. 100개 종목이면 200 추가 쿼리.

**권장 수정**:
- View에서 `Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7])` 사용
- 또는 `EODSignal.close_price` 등 baked 필드를 써서 추가 조회 불필요
- 추가로 `get_chart_data`에 `return recent_prices` 누락 — 함수가 `None` 반환 중

---

#### [HIGH-2] `stocks/serializers.py:205-307` — OverviewTabSerializer.get_dynamic_layers
**파일:라인**: `stocks/serializers.py:205-307`
**호출 뷰**: `stocks/views.py:492` (StockOverviewAPIView)
**난이도**: 중간
**설명**:
6개 OneToOne reverse(`overview_ko`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + 1개 ForeignKey reverse(`category_signals.all()`) 접근. 그러나 호출 뷰의 `select_related`는 `overview_ko`만 적용:
```python
# stocks/views.py:492
stock = Stock.objects.select_related('overview_ko').filter(symbol=symbol).first()
# TODO 주석도 코드에 명시되어 있음 (line 491)
```
단일 상세 페이지에서는 6개 추가 + 1개 ForeignKey reverse = **7개 쿼리**. 캐시 1회 미스 시 7회 그대로 발생.

**권장 수정**:
```python
Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals').filter(symbol=symbol).first()
```
이 쿼리는 코드에 이미 TODO로 적혀 있음(`stocks/views.py:491`).

---

#### [HIGH-3] `validation/api/views.py:192-300` — ValidationMetricsView (3중 루프 N+1)
**파일:라인**: `validation/api/views.py:192-208, 219-285`
**난이도**: 중간
**설명**:
```python
for cat in categories:                    # 7개 카테고리
    for mc in metric_codes:               # 카테고리당 ~10 메트릭
        md = MetricDefinition.objects.filter(pk=mc).first()        # 쿼리 1
        latest_snap = CompanyMetricSnapshot.objects.filter(...)    # 쿼리 2
        delta = CompanyBenchmarkDelta.objects.filter(...)          # 쿼리 3
        snaps = CompanyMetricSnapshot.objects.filter(...)[:5]      # 쿼리 4
        for s in snaps:                                            # 5개 history
            peer_bench = PeerMetricBenchmark.objects.filter(...)   # 쿼리 5..9
```
Worst case: **7 × 10 × 9 ≈ 630 쿼리** per request.

**권장 수정**:
- `MetricDefinition`을 dict로 일괄 prefetch (`{m.pk: m for m in MetricDefinition.objects.filter(pk__in=all_metric_codes)}`)
- `CompanyMetricSnapshot`을 `(symbol, fiscal_year)` 단위로 한번에 가져오기
- `PeerMetricBenchmark`도 `(symbol, metric_code__in=…, fiscal_year__in=…)`로 단일 쿼리 후 dict 룩업

---

#### [HIGH-4] `validation/api/views.py:351-396` — LeaderComparisonView (메트릭 루프 내 단건 쿼리)
**파일:라인**: `validation/api/views.py:353-371`
**난이도**: 중간
**설명**:
```python
for cat, codes in CATEGORY_METRICS.items():  # 7
    for mc in codes:                          # 카테고리당 ~10 = total ~50
        all_metrics.append((cat, mc))

for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()       # 쿼리 1
    company_snap = CompanyMetricSnapshot.objects.filter(...)  # 쿼리 2
    leader_snap = CompanyMetricSnapshot.objects.filter(...)   # 쿼리 3
```
**~150 쿼리** per request.

**권장 수정**:
- `MetricDefinition` 한 번에 `pk__in` bulk fetch
- `CompanyMetricSnapshot`도 `symbol__in=[stock, leader], metric_code_id__in=…, fiscal_year=latest_fy` 한 쿼리로

---

#### [HIGH-5] `chainsight/api/views.py:70-83` — ChainSightGraphView (각 edge별 N+1)
**파일:라인**: `chainsight/api/views.py:70-83`
**난이도**: 중간
**설명**:
```python
for edge in result.get("edges", []):
    cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
    pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
```
depth=3 그래프는 edge 50~200개 가능 → **2N (100~400) 쿼리**.

**권장 수정**:
- 모든 (a, b) 쌍을 모은 뒤 `CoMentionEdge.objects.filter(symbol_a__in=..., symbol_b__in=...)`로 일괄 fetch → dict로 룩업
- 또는 Q 객체로 OR 묶음 + 단일 쿼리

---

#### [MED-6] `news/api/views.py:331-348` — NewsViewSet.trending (집계 결과별 추가 쿼리)
**파일:라인**: `news/api/views.py:322-343`
**난이도**: 쉬움
**설명**:
trending top N(`limit`) 집계 후 종목별로 `NewsArticle.objects.filter(entities__symbol=symbol, ...)` 추가 쿼리 → **N+1**. limit=20이면 20 추가 쿼리. 5분 캐시가 있어 영향은 완화되지만 cold cache 시 영향 큼.

**권장 수정**:
- 하나의 쿼리로 `NewsArticle.filter(entities__symbol__in=top_symbols, published_at__gte=...).prefetch_related('entities')` 후 Python에서 그룹화

---

#### [MED-7] `validation/api/views.py:110-124` — ValidationSummaryView rank_metrics 루프
**파일:라인**: `validation/api/views.py:110-124`
**난이도**: 쉬움
**설명**:
```python
rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
for mc in rank_metrics:
    delta = CompanyBenchmarkDelta.objects.filter(...).first()  # 5번
    md = MetricDefinition.objects.filter(pk=mc).first()         # 5번
```
**10 쿼리 → 2 쿼리로 줄일 수 있음**.

**권장 수정**:
- `CompanyBenchmarkDelta.objects.filter(metric_code_id__in=rank_metrics, ...)` 한 번
- `MetricDefinition.objects.filter(pk__in=rank_metrics)` 한 번 → dict 변환

---

#### [MED-8] `users/views.py:872-895` — WatchlistBulkAddView (심볼당 3 쿼리)
**파일:라인**: `users/views.py:872-895`
**난이도**: 중간
**설명**:
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol.upper())           # 쿼리 1
    if WatchlistItem.objects.filter(...).exists(): continue    # 쿼리 2
    WatchlistItem.objects.create(...)                          # 쿼리 3
```
100개 symbol POST 시 **300+ 쿼리**.

**권장 수정**:
- `Stock.objects.in_bulk(symbols, field_name='symbol')`로 한 번에 조회
- 기존 항목도 `WatchlistItem.objects.filter(watchlist=watchlist, stock_id__in=symbols).values_list('stock_id', flat=True)` 한 번
- `bulk_create(ignore_conflicts=True)` 사용

---

#### [MED-9] `users/views.py:937-944` — WatchlistBulkRemoveView
**파일:라인**: `users/views.py:937-944`
**난이도**: 쉬움
**설명**: 심볼당 `get` + `delete` = 2N. 
**권장 수정**: `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=upper_symbols).delete()` 한 번으로 변경.

---

#### [MED-10] `stocks/views_indicators.py:324-371` — Indicator comparison
**파일:라인**: `stocks/views_indicators.py:324-371`
**난이도**: 쉬움
**설명**:
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)                    # N
    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]  # N
```
20 종목 비교 시 **40 쿼리**.

**권장 수정**:
- `Stock.objects.in_bulk(...)` + `DailyPrice.filter(stock__in=stocks, date__gte=cutoff).order_by('stock','-date')` 후 Python에서 그룹화

---

#### [MED-11] `serverless/serializers.py:208-219` — MarketBreadthSerializer.get_signal_interpretation
**파일:라인**: `serverless/serializers.py:208-219`
**난이도**: 쉬움
**설명**: 각 obj마다 `MarketBreadthService()` 인스턴스화 + `get_signal_interpretation()` 호출. 서비스 내부 동작에 따라 DB 쿼리/캐시 조회 추가 가능. 매 row마다 인스턴스화 자체가 GC 부담.

**권장 수정**: serializer `__init__`에서 `self._service = MarketBreadthService()` 한 번만 생성하고 재사용. 또는 `to_representation`에서 lookup table을 한 번 만들어서 사용.

---

#### [MED-12] `serverless/serializers.py:275-292` — ScreenerPresetSerializer.get_owner_email/get_is_owner
**파일:라인**: `serverless/serializers.py:275-292`
**난이도**: 쉬움
**설명**: `obj.user.email` 접근. 호출 뷰가 `select_related('user')`를 안 쓰면 preset N개에 대해 N개 추가 user 쿼리 발생.

**권장 수정**: 프리셋 list 뷰의 queryset에 `.select_related('user')` 명시. 직렬화 측에서는 변경 불필요.

---

#### [LOW-13] `users/views.py:1000-1041` — UserInterestListCreateView.post (get_or_create 루프)
**파일:라인**: `users/views.py:1000-1041`
**난이도**: 쉬움
**설명**: `interests` 리스트 길이 N에 대해 N개의 `get_or_create` 호출. 사용자가 한 번에 등록하는 관심사 수가 적어 영향 작지만 패턴은 N+1.

**권장 수정**: 트래픽이 늘면 `bulk_create(ignore_conflicts=True)`로 통합.

---

### 2. 페이지네이션 누락

#### [HIGH-14] `config/settings.py:341` — DRF 글로벌 페이지네이션 부재
**파일:라인**: `config/settings.py:341-349`
**난이도**: 쉬움
**설명**:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    # ❌ DEFAULT_PAGINATION_CLASS 없음
    # ❌ PAGE_SIZE 없음
}
```
모든 `ListAPIView` / `ReadOnlyModelViewSet`이 명시적 `pagination_class` 없으면 전체 반환. SP500 만 종목이라도 운영 누적 시(예: NewsArticle, AlertHistory, UsageLog) 응답 크기 폭증.

**권장 수정**:
```python
REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'] = 'rest_framework.pagination.PageNumberPagination'
REST_FRAMEWORK['PAGE_SIZE'] = 50
```
프런트 호환성은 페이지네이션 응답 형태 변화 → 단계적 도입 필요(개별 뷰별 적용도 가능).

---

#### [HIGH-15] `stocks/views.py:75` — StockListAPIView
**파일:라인**: `stocks/views.py:75`
**난이도**: 쉬움
**설명**: docstring에 "pagination으로 조회"라 적혀 있으나 `pagination_class` 미지정 + 글로벌 페이지네이션 없음 → `Stock.objects.all().order_by(-market_capitalization)`이 모든 종목(SP500+α) 반환.

**권장 수정**: 뷰에 `pagination_class = PageNumberPagination` 명시 또는 글로벌 설정.

---

#### [HIGH-16] `stocks/views_mvp.py:17` — StockMVPListView
**파일:라인**: `stocks/views_mvp.py:41`
**난이도**: 쉬움
**설명**: `queryset = queryset[:20]`로 20개 하드코딩. limit/offset 파라미터 없음. 검색 결과가 20을 넘는 케이스 처리 불가.

**권장 수정**: `?limit=`, `?offset=` 또는 `?page=` 파라미터 도입.

---

#### [MED-17] `stocks/views_eod.py:51` — EODSignalDetailView (50개 하드 limit)
**파일:라인**: `stocks/views_eod.py:78`
**난이도**: 쉬움
**설명**: `[:50]`로 자른 후 반환. 시그널이 50개 이상인 종목/날짜는 잘림 안내 없음.

**권장 수정**: `truncated`/`total_count` 필드 추가하거나 페이지네이션 도입.

---

#### [MED-18] `news/api/views.py:42` — NewsViewSet (전체 모델뷰셋, 글로벌 페이지네이션 의존)
**파일:라인**: `news/api/views.py:42-46`
**난이도**: 쉬움
**설명**: `queryset = NewsArticle.objects.all().prefetch_related('entities')` — DRF 기본 페이지네이션이 없으면 list 액션이 모든 article 반환. NewsArticle 누적 수가 늘면 치명적. 단 일부 액션(`all_news`, `stock_news`)은 수동 limit/offset 사용 → 표준 페이지네이션과 응답 포맷 불일치.

**권장 수정**: `pagination_class = PageNumberPagination` 명시 + 수동 페이지네이션 액션과 응답 포맷 정렬.

---

#### [MED-19] `stocks/views_eod.py:118` — EODPipelineStatusView
**파일:라인**: `stocks/views_eod.py:119`
**난이도**: 쉬움
**설명**: `[:7]` 하드코딩. 7일 초과 조회 불가. admin 전용이라 영향 작음.

**권장 수정**: `?days=` 파라미터 도입.

---

#### [MED-20] `validation/api/views.py:421` — PresetListView
**파일:라인**: `validation/api/views.py:426-453`
**난이도**: 쉬움
**설명**: `PeerPreset.objects.filter(symbol_id=symbol).order_by('preset_key')` 후 전체 직렬화. 종목당 프리셋 수 적어(6종) 영향 적지만 페이지네이션 없음.

**권장 수정**: 프리셋 수가 늘 가능성 적으면 그대로 두고, 명시적 limit만 추가.

---

#### [MED-21] `chainsight/api/views.py:302, 310` — SeedListView, SectorGraphView
**파일:라인**: `chainsight/api/views.py:302, 310`
**난이도**: 중간
**설명**:
- `SeedListView`: `_get_today_seeds()` 결과 전체(seeds 100~500개 가능) 반환
- `SectorGraphView`: limit 파라미터(최대 30) 있으나 응답 자체에 페이지네이션 메타 없음

**권장 수정**: SeedListView에 `?limit=`, `?offset=` 추가. SectorGraphView는 현재 limit≤30 강제로 위험 적음.

---

#### [LOW-22] `stocks/views_search.py:146` — PopularSymbolsView
**파일:라인**: `stocks/views_search.py:153`
**난이도**: 해당 없음
**설명**: 15개 하드코딩 인기 종목 반환. 페이지네이션 불필요.
**권장 수정**: 변경 없음 (False positive).

---

### 3. 인덱스 누락

> **종합 평가**: stocks/, users/, news/, serverless/, sec_pipeline/, graph_analysis/, rag_analysis/ 모두 `db_index` / `Meta.indexes`가 적절히 설정되어 있음. 누락은 우선순위 낮음.

#### [MED-23] `users/models.py:249-265` — UserInterest
**파일:라인**: `users/models.py:265`
**난이도**: 쉬움
**설명**: `unique_together = ('user', 'interest_type', 'value')`로 (user, interest_type, value) 인덱스는 자동 생성되지만, `(interest_type, value)` 단독 조회나 `(value)` 단독 조회는 인덱스 미스. 다만 현재 코드는 user별 조회만 사용해 영향 작음.

**권장 수정**: 사용 패턴 변화 시 `models.Index(fields=['interest_type', 'value'])` 추가.

---

#### [LOW-24] `serverless/models.py:148-165` — VolatilityBaseline
**파일:라인**: `serverless/models.py:159`
**난이도**: 쉬움
**설명**: `unique_together = [['symbol', 'date']]`만 있음. `Meta.indexes` 없음. `(symbol, -date)` 패턴 조회 시 unique 인덱스로 커버되지만 정렬 방향 mismatch 가능. 단 `symbol` 단독 인덱스(`db_index=True`)는 있어 대부분 케이스 양호.

**권장 수정**: 변경 불필요(사용 빈도 낮음).

---

#### [LOW-25] `rag_analysis/models.py:11-218` — DataBasket / AnalysisSession / AnalysisMessage
**파일:라인**: `rag_analysis/models.py:28, 165, 212`
**난이도**: 쉬움
**설명**: `Meta.indexes` 없음. user/basket/session FK 자동 인덱스만 있음. ordering이 `-updated_at` 또는 `-created_at`인데 `(user, -updated_at)` 같은 복합 인덱스 누락. 사용량 적은 한 영향 미미.

**권장 수정**: 사용량 증가 시 `models.Index(fields=['user', '-updated_at'])` 추가 고려.

---

### 4. 느린 Serializer (SerializerMethodField에서 추가 작업)

#### [MED-26] `serverless/serializers.py:121-137` — MarketMoverListSerializer
**파일:라인**: `serverless/serializers.py:121-137`
**난이도**: 쉬움
**설명**: 3개 SerializerMethodField(`get_sector_alpha_display`, `get_etf_sync_display`, `get_volatility_pct_display`) 모두 매 row마다 `IndicatorCalculator()` 인스턴스 생성. DB 쿼리는 없지만 객체 생성 비용 ×N. 30 rows라면 90회 인스턴스 생성.

**권장 수정**: `IndicatorCalculator`를 모듈 레벨 싱글톤이나 serializer 클래스 변수로 한 번만 생성.

---

#### [MED-27] `serverless/serializers.py:208-219` — MarketBreadthSerializer.get_signal_interpretation
설명/수정 권장은 N+1 섹션의 [MED-11]과 동일.

---

#### [MED-28] `serverless/serializers.py:275-292` — ScreenerPresetSerializer.get_owner_email
설명/수정 권장은 N+1 섹션의 [MED-12]와 동일.

---

## 우선순위 제안

| 순위 | 작업 | 영향 | 비용 |
|:---:|---|:---:|:---:|
| 1 | **글로벌 페이지네이션 도입** ([HIGH-14, 15, 16]) | 매우 큼 | 낮음 |
| 2 | **OverviewTabSerializer prefetch 보강** ([HIGH-2]) | 큼 | 낮음 |
| 3 | **Validation 모듈 N+1 일괄 정리** ([HIGH-3, 4], [MED-7]) | 큼 | 중간 |
| 4 | **WatchlistBulk 일괄 처리화** ([MED-8, 9]) | 중간 | 낮음 |
| 5 | **ChainSightGraphView edge 일괄 lookup** ([HIGH-5]) | 중간 | 낮음 |
| 6 | **WatchListStockSerializer return 누락 수정** ([HIGH-1]) | 중간 | 낮음 |
| 7 | trending 엔드포인트 N+1 정리 ([MED-6]) | 중간 | 낮음 |
| 8 | Serializer 캐싱 / select_related 보강 ([MED-11, 12, 26]) | 작음 | 낮음 |
| 9 | 인덱스 보강 ([MED-23], [LOW-24, 25]) | 작음 | 낮음 |

---

## 검사 범위 메타

- 검사 뷰 파일 (17개): `stocks/views.py`, `stocks/views_search.py`, `stocks/views_exchange.py`, `stocks/views_eod.py`, `stocks/views_screener.py`, `stocks/views_market_movers.py`, `stocks/views_fundamentals.py`, `stocks/views_indicators.py`, `stocks/views_mvp.py`, `users/views.py`, `news/api/views.py`, `macro/views.py`, `rag_analysis/views.py`, `serverless/views_admin.py`, `validation/api/views.py`, `chainsight/api/views.py`, `sec_pipeline/views.py`
- 검사 모델 파일 (7개): `stocks/models.py`, `users/models.py`, `news/models.py`, `serverless/models.py`, `rag_analysis/models.py`, `sec_pipeline/models.py`, `graph_analysis/models.py`
- 검사 Serializer 파일: `stocks/serializers.py`, `users/serializers.py`, `serverless/serializers.py`, `news/api/serializers.py`, `rag_analysis/serializers.py`, `stocks/serializers_*.py` (4종)
- macro/views.py, sec_pipeline/views.py: 외부 service 위임 또는 짧은 뷰로 ORM N+1 없음
- chainsight Neo4j 호출은 별개 데이터베이스 — 본 감사에서는 ORM 패턴만 평가
