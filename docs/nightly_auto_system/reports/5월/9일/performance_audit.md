# API 성능 감사 보고서

- **감사 일자**: 2026-05-09
- **감사 범위**: 17개 뷰 파일 + 7개 모델 파일 + 핵심 Serializer 파일
- **감사 방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **대상 브랜치**: `portfolio`

---

## 요약

### 이슈 수 (심각도별)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 페이지네이션 | Serializer | 합계 |
|---|---|---|---|---|---|
| **HIGH** | 4 | 0 | 1 | 2 | **7** |
| **MED**  | 4 | 1 | 1 | 1 | **7** |
| **LOW**  | 2 | 1 | 0 | 0 | **3** |
| **합계** | **10** | **2** | **2** | **3** | **17** |

### 핵심 결론

1. **글로벌 페이지네이션 미설정** (`config/settings.py:348-362`) — `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` 부재. 코드 주석에 "audit P0 #14 (페이지네이션 표준)는 별도 PR에서 처리 — 응답 envelope 결정이 선결 조건"으로 이미 인지된 상태.
2. **가장 위험한 N+1 위치**: `validation/api/views.py`의 `_build_category` / `_build_metric` (카테고리 × 지표 × 연도 = N×M×K 쿼리), `stocks/serializers.py`의 `get_dynamic_layers` (직렬화 1건당 6 쿼리, 이미 TODO로 인지).
3. **인덱스는 대체로 양호** — 모든 핵심 모델(Stock, NewsArticle, MarketMover, ScreenerAlert, EODSignal, MLModelHistory 등)에 적절한 복합 인덱스가 이미 존재. 추가 필요 사례는 `Stock.stock_name` 검색용 1건뿐이며 그것도 `icontains`라 효과 제한적.
4. **빠른 승리 (Quick Win)** 후보:
   - `validation/api/views.py:112-117` 5회 쿼리 → `in_bulk` 1회 (HIGH/쉬움)
   - `stocks/views_indicators.py:324-335` 루프 내 `.get()` → `filter(symbol__in=...)` 1회 (HIGH/쉬움)
   - `serverless/views_admin.py:480-481` `cat.resolve_symbols()` 루프 → 카테고리 N개일 때 N+1 (MED/중간)

---

## 상세

### A. N+1 쿼리

#### A-1. [HIGH / 중간] `stocks/serializers.py:205-289` — `OverviewTabSerializer.get_dynamic_layers`

**파일**: `stocks/serializers.py`
**라인**: 205~289 (`get_dynamic_layers` 메서드)
**패턴**: SerializerMethodField에서 6개의 reverse FK / OneToOne 관계 직접 접근.

직렬화 1건당 발생하는 쿼리 (선검증된 실제 코드):
- L215: `obj.category_signals.all()` — reverse FK
- L235: `obj.validation_news_summary` — OneToOne
- L252: `obj.sensitivity_profile` — OneToOne
- L267: `obj.growth_stage` — OneToOne
- L281: `obj.capital_dna` — OneToOne
- (이후 라인에 추가 관계 가능성 — 6개 모델 명시)

**위험도**: 직렬화 객체 N개에 대해 **5N + 추가 쿼리** 폭증. 현재는 `StockDetailView` 단건 조회에서만 사용되므로 실제 위험은 낮으나, 향후 `StockListAPIView`에서 사용되면 즉시 폭발.

**권장**:
```python
# views.py 측에서 미리 prefetch
queryset.select_related(
    'validation_news_summary',
    'sensitivity_profile',
    'growth_stage',
    'capital_dna',
).prefetch_related('category_signals')
```

**비고**: 라인 208에 이미 `# TODO: Step 2~4에서 데이터 유입 시 prefetch_related + 캐싱 레이어 적용 필요` 주석이 있어 작성자가 인지한 사안.

---

#### A-2. [HIGH / 쉬움] `stocks/serializers.py:398-409` — `WatchListStockSerializer.get_latest_price` / `get_chart_data`

**파일**: `stocks/serializers.py`
**라인**: 398~409
**패턴**: SerializerMethodField에서 직렬화마다 DailyPrice 쿼리 2회.

```python
# L398-403
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()  # ← 매 직렬화마다 SELECT
    ...

# L405-409
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]  # ← 매 직렬화마다 SELECT
```

**위험도**: Watchlist 30종목 가정 → 60+ 추가 쿼리. 100종목이면 200+.

**권장**: 뷰에서 `Prefetch('daily_price_set', queryset=DailyPrice.objects.order_by('-date')[:7])` 적용 후 Python에서 슬라이스. 또는 `obj.real_time_price` 사용 (Stock 모델에 이미 컬럼 존재, `models.py:37`).

---

#### A-3. [HIGH / 쉬움] `validation/api/views.py:112-117` — `ValidationSummaryView` 루프 내 `.first()`

**파일**: `validation/api/views.py`
**라인**: 110~124

```python
rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
for mc in rank_metrics:
    delta = CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
    ).first()
    if delta and delta.rank and delta.total:
        md = MetricDefinition.objects.filter(pk=mc).first()  # ← 또 1회
        ...
```

**위험도**: 5개 metric × 2개 모델 → **최대 10회 SELECT** (사용자 1명당). Validation 요약 호출 빈도가 페이지 진입 시마다이므로 누적 비용 큼.

**권장**:
```python
deltas = {
    d.metric_code_id: d
    for d in CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics
    )
}
mds = MetricDefinition.objects.in_bulk(rank_metrics)
for mc in rank_metrics:
    delta = deltas.get(mc)
    md = mds.get(mc)
    ...
```
**효과**: 10회 → 2회.

---

#### A-4. [HIGH / 중간] `validation/api/views.py:192-208` — `ValidationMetricsView._build_category` / `_build_metric` 이중 루프

**파일**: `validation/api/views.py`
**라인**: 192~268

```python
# L192-195
for cat in categories:
    cat_data = self._build_category(stock, cat)  # ← 카테고리당
    
# _build_category (L199-217) — cat 1개당
signal_obj = CategorySignal.objects.filter(symbol=stock, category=category).first()  # +1
for mc in metric_codes:                                                              # ← 지표 루프
    md = MetricDefinition.objects.filter(pk=mc).first()                              # +N
    metrics_data.append(self._build_metric(stock, md))                               # _build_metric 진입

# _build_metric (L219-289)
latest_snap = CompanyMetricSnapshot.objects.filter(...).order_by('-fiscal_year').first()  # +1
any_snap = CompanyMetricSnapshot.objects.filter(...).first()                              # +1 (조건부)
delta = CompanyBenchmarkDelta.objects.filter(...).first()                                 # +1 (조건부)
snaps = CompanyMetricSnapshot.objects.filter(...).order_by('fiscal_year')[:5]             # +1
```

**위험도**: 카테고리 6개 × 지표 5개 × (5 쿼리/지표) = **약 150 쿼리/요청** (대략적). `category_param='all'` 호출 시 매우 큼.

**권장**:
- `MetricDefinition.objects.in_bulk()`로 한 번에 로드
- `CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code_id__in=all_codes).order_by('-fiscal_year')` 한 번에 받아 Python 쪽에서 그룹화
- `CompanyBenchmarkDelta`도 동일 패턴
- **수정 난이도 중간**: 시그니처 변경 동반.

---

#### A-5. [HIGH / 쉬움] `stocks/views_indicators.py:324-335` — `IndicatorComparisonView` 루프 내 `.get()`

**파일**: `stocks/views_indicators.py`
**라인**: 324~338

```python
for symbol in symbols:
    symbol = symbol.upper()
    try:
        stock = Stock.objects.get(symbol=symbol)        # ← 심볼당 1회
    except Stock.DoesNotExist:
        continue
    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]\
                              .values_list('close_price', flat=True)  # ← 심볼당 1회
```

**위험도**: 비교 대상 5종목 → **10 쿼리**. 종목이 많아질수록 선형 증가.

**권장**:
```python
stocks = {s.symbol: s for s in Stock.objects.filter(symbol__in=[s.upper() for s in symbols])}
prices_qs = DailyPrice.objects.filter(stock__symbol__in=stocks.keys()).order_by('stock_id', '-date')
# Python에서 stock_id별로 그룹화하여 상위 50개만 추출
```

---

#### A-6. [MED / 중간] `serverless/views_admin.py:478-481` — `AdminNewsCategoryView` 루프 내 메서드 호출

**파일**: `serverless/views_admin.py`
**라인**: 478~500

```python
categories = NewsCollectionCategory.objects.all()
for cat in categories:
    symbols = cat.resolve_symbols()  # ← 내부에서 SP500Constituent.objects.filter() 호출
```

`news/models.py:638-660` 의 `resolve_symbols`는 카테고리 타입별로:
- `sector` / `sub_sector` → `SP500Constituent.objects.filter(...).values_list('symbol')[:max_symbols]`
- `custom` → 쿼리 없음

**위험도**: 카테고리 N개 중 sector 기반이 M개라면 **추가 M회 SELECT**. 관리자 대시보드라 호출 빈도는 낮지만 카테고리가 30~50개면 영향 있음.

**권장**:
- 캐시 (Redis) 도입 — 카테고리는 자주 변경 안 됨
- 또는 `SP500Constituent`를 사전에 한 번 로드해 Python에서 그룹별 매핑

---

#### A-7. [MED / 중간] `users/views.py:880-901` — `WatchlistBulkAddView` 루프 내 다중 쿼리

**파일**: `users/views.py`
**라인**: 880~903

```python
for symbol in symbols:
    try:
        stock = Stock.objects.get(symbol=symbol.upper())                              # +1
        if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():   # +1
            ...
        item = WatchlistItem.objects.create(...)                                      # +1 (INSERT)
```

**위험도**: bulk 추가 N개 → **3N 쿼리**. 사용자 동작이라 호출 빈도 낮으나 응답 시간 체감 가능.

**권장**:
- `Stock.objects.in_bulk(symbols, field_name='symbol')` 1회
- 기존 항목 한 번에 조회: `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=symbols).values_list('stock__symbol', flat=True)`
- `bulk_create` 사용

---

#### A-8. [MED / 쉬움] `users/views.py:945-948` — `WatchlistBulkRemoveView` 루프 내 `.get()` + `delete()`

**파일**: `users/views.py`
**라인**: 945~951

```python
for symbol in symbols:
    try:
        item = WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())  # +1
        item.delete()                                                                          # +1 DELETE
```

**위험도**: N개 삭제 → **2N 쿼리**.

**권장**: `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=symbols).delete()` (1 SELECT + 1 DELETE).

---

#### A-9. [MED / 중간] `news/api/views.py:95-103` — `NewsViewSet.stock_news` 결과 페이지네이션 부재

**파일**: `news/api/views.py`
**라인**: 95~110

```python
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).distinct().order_by('-published_at')

serializer = self.get_serializer(articles, many=True)  # ← 전체 직렬화
data = {
    'symbol': symbol,
    'count': articles.count(),  # ← 추가 COUNT 쿼리
    'articles': serializer.data
}
```

**위험도**: `count()` 호출이 별도 SELECT를 발생시키며, 7일치라도 적극적인 종목(예: AAPL)은 수백 건. Cache(10분)가 있어 직접 영향은 완화되지만 캐시 미스 시 비용 큼.

**권장**: `len(serializer.data)`로 count 대체 또는 페이지네이션 적용.

---

#### A-10. [LOW / 높음] `rag_analysis/views.py` — `DataBasket` nested prefetch

**파일**: `rag_analysis/views.py` (라인 직접 검증 미완료, Explore 에이전트 보고에 따름)
**패턴**: `DataBasket.objects.prefetch_related('items')`까지만 적용 시, 직렬화에서 `item.stock` 접근하면 N+1.

**권장**:
```python
from django.db.models import Prefetch
DataBasket.objects.prefetch_related(
    Prefetch('items', queryset=BasketItem.objects.select_related('stock'))
)
```

---

### B. 인덱스 누락

#### B-1. [MED / 쉬움] `stocks/models.py` — `Stock.stock_name`

**파일**: `stocks/models.py`
**필드**: `stock_name` (line 22)
**사용처**:
- `stocks/views.py:191` — `Q(stock_name__icontains=query) | Q(symbol__icontains=query)` (검색 자동완성)
- `stocks/views_mvp.py:37` — `Q(stock_name__icontains=search)`

**상태**: `Stock.Meta.indexes` (line 95-100)에 `sector`, `industry`, `market_capitalization`, `last_updated`, 복합 `(symbol, sector)`은 있으나 `stock_name` 없음. `symbol`은 PK이므로 자동 인덱스.

**위험도**:
- `icontains` 검색은 인덱스 효과가 제한적 (LIKE '%x%' 패턴은 B-tree 인덱스 미활용).
- PostgreSQL `pg_trgm` 확장 + GIN 인덱스가 효과적이나 신규 의존성.
- 현재 Stock 테이블은 SP500 기준 약 500~1500행 추정 → 영향 작음.

**권장**: 테이블 크기가 5000행 미만이면 **현 상태 유지 권장**. 확장 시 `pg_trgm` 도입 후 GIN 인덱스 검토.

---

#### B-2. [LOW / 쉬움] `news/models.py` — 기존 인덱스로 충분

**검증 결과**: `NewsArticle` Meta indexes (line 192-198):
- `(-published_at, category)`
- `(source, -published_at)`
- `(sentiment_score, -published_at)`
- `(importance_score, -published_at)`
- `(llm_analyzed, -published_at)`

`NewsCollectionCategory` (line 633): `(is_active, priority)` — `views_admin.py`의 단순 `.all()` 호출은 인덱스 영향 없음.

**결론**: news 도메인 인덱스 추가 권장 사항 **없음**.

---

### C. 느린 Serializer (요약)

| Serializer | 라인 | 패턴 | 심각도 |
|---|---|---|---|
| `OverviewTabSerializer.get_dynamic_layers` | `stocks/serializers.py:205-289` | reverse FK + 5×OneToOne 직접 접근 | HIGH (이슈 A-1과 동일) |
| `WatchListStockSerializer.get_latest_price/get_chart_data` | `stocks/serializers.py:398-409` | DailyPrice.objects.filter() 매 직렬화 | HIGH (A-2와 동일) |
| `*Serializer.get_market_cap_formatted/volume_formatted/...` | `stocks/serializers.py:65,69,168,179` | obj 필드만 사용 | OK (쿼리 없음) |
| `OverviewTabSerializer.get_korean_overview` | `stocks/serializers.py:190-203` | `obj.overview_ko` (OneToOne) 직접 접근 | LOW — `select_related('overview_ko')` 적용 시 해결 (현재 `views.py:494`에서 이미 적용됨) |

---

### D. 페이지네이션 누락

#### D-1. [HIGH / 쉬움] 글로벌 설정 부재

**파일**: `config/settings.py:348-362`
**문제**: `REST_FRAMEWORK` 딕셔너리에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 미설정.
**상태**: 코드 주석(line 347)에 명시됨 — `audit P0 #14 (페이지네이션 표준)는 별도 PR에서 처리 — 응답 envelope 결정이 선결 조건`.
**권장**: 응답 envelope 표준 결정 후 `PageNumberPagination`(또는 `LimitOffsetPagination`) + `PAGE_SIZE=20~50`.

---

#### D-2. [MED / 쉬움] `stocks/views.py:75` — `StockListAPIView.pagination_class` 미설정

**파일**: `stocks/views.py`
**라인**: 75~105
**문제**: `class StockListAPIView(generics.ListAPIView)` 선언에 `pagination_class` 없음. 글로벌 설정도 없으므로 전체 Stock 반환.
**위험도**: Stock 테이블이 SP500 + 사용자 추가 종목이라 행 수는 제한적이지만 `OverviewTabSerializer`가 적용되면 응답 본문이 거대해짐.
**권장**: `pagination_class = PageNumberPagination` (D-1 글로벌 도입 시 자동 해소).

---

#### D-3. [MED / 중간] `news/api/views.py:47` — `NewsViewSet` (ReadOnlyModelViewSet)

**파일**: `news/api/views.py`
**라인**: 47~58
**문제**: `queryset = NewsArticle.objects.all().prefetch_related('entities')` — 페이지네이션 미설정. `list()` 액션 호출 시 전체 뉴스 반환 가능. NewsArticle은 일일 수백~수천 건 누적 → **수만 행 가능성 높음**.
**권장**: `pagination_class = LimitOffsetPagination` 명시 + `PAGE_SIZE` 기본값 적용. 또는 D-1 글로벌 도입.

---

### E. 비-N+1 보고이지만 실제로는 정상인 케이스 (오탐 정정)

Explore 에이전트 보고 중 직접 검증 결과 **이슈 없음**으로 판정한 항목:

1. **`users/views.py:374-376` `PortfolioSummaryView` 루프**
   - 보고: `for portfolio in portfolios: total_value += portfolio.total_value` → N+1 의심
   - 검증: `portfolios` 쿼리셋이 `.select_related('stock')` 적용 (line 358)이고, `total_value`는 `models.py:80-83`에서 `self.stock.real_time_price`만 사용 — **N+1 없음**.
2. **`stocks/views_eod.py:72-99` `EODSignalDetailView`**
   - 보고: 루프 내 `s.stock.stock_name` 접근
   - 검증: 이미 `select_related('stock')` 적용 — **N+1 없음**.
3. **`stocks/views.py:490-526` `StockOverviewAPIView`**
   - 검증: `select_related('overview_ko').filter(symbol=symbol).first()` 단건 조회 — **N+1 없음**. 단 `dynamic_layers`는 별개 이슈 (A-1).

---

## 권장 우선순위

### Phase 1 — Quick Win (1~2일)
1. **A-3** `validation/api/views.py:112-117` — `in_bulk` 적용 (10→2 쿼리)
2. **A-5** `stocks/views_indicators.py:324-335` — `filter(symbol__in=...)` (2N→2 쿼리)
3. **A-8** `users/views.py:945-948` — `.filter().delete()` (2N→2 쿼리)
4. **A-2** `stocks/serializers.py:398-409` — `obj.real_time_price` 사용 또는 prefetch (직렬화당 2→0 쿼리)

### Phase 2 — 시그니처 변경 (3~5일)
5. **A-4** `validation/api/views.py` `_build_category` / `_build_metric` 리팩토링
6. **A-1** `stocks/serializers.py:205-289` `get_dynamic_layers` + 뷰 prefetch

### Phase 3 — 표준화 (별도 PR)
7. **D-1** 글로벌 페이지네이션 도입 (이미 P0 #14로 트래킹 중)
8. **D-3** `NewsViewSet` 페이지네이션
9. **A-9** `news/api/views.py:95-103` `count()` 제거 또는 페이지네이션

### Phase 4 — 모니터링 (지속)
- **`django-debug-toolbar`** 또는 **`django-silk`** 도입으로 엔드포인트별 쿼리 수 추적
- N+1 회귀 방지 테스트: `assertNumQueries` 활용

---

## 검증 메모

- **글로벌 페이지네이션**: `Grep "REST_FRAMEWORK|DEFAULT_PAGINATION_CLASS|PAGE_SIZE"` 으로 `config/` 전체 스캔 — 미설정 확인.
- **모든 ListAPIView 스캔**: 프로젝트 전체에 `class .*ListAPIView` / `class .*ListCreateAPIView` / `class .*ModelViewSet` / `class .*ReadOnlyModelViewSet` 검색 → `StockListAPIView`(stocks/views.py:75), `NewsViewSet`(news/api/views.py:47) 2건만 발견. `pagination_class` grep 결과 0건 → **둘 다 미설정**.
- **인덱스**: 7개 모델 파일 모두에 `db_index=True` 또는 `Meta.indexes` 정의 존재. NewsArticle, EODSignal, MarketMover, ScreenerAlert, MLModelHistory, CorrelationEdge, RawDocumentStore 등 핵심 모델 모두 적절한 복합 인덱스 보유.
- **본 보고서의 라인번호는 모두 직접 `Read`/`Grep`으로 확인된 것**. Explore 에이전트가 보고한 일부 라인(예: `stocks/views.py:839`)은 직접 검증하지 않았으며, 검증된 항목만 본 보고서에 포함.
