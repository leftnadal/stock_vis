# API 성능 감사 보고서

**감사 일자**: 2026-05-20
**감사 범위**: views*.py 17개, serializers*.py 핵심, models.py 7개
**모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 | 인덱스 | Serializer | 페이지네이션 | 합계 |
|--------|-----|--------|------------|--------------|------|
| HIGH   | 4   | 0      | 2          | 6            | 12   |
| MED    | 7   | 2      | 0          | 3            | 12   |
| LOW    | 3   | 1      | 0          | 2            | 6    |
| **합계** | **14** | **3** | **2** | **11** | **30** |

**최우선 처치 권장 (HIGH 12건)**
- N+1: 종목 비교/뉴스 트렌딩/Overview dynamic_layers/Watchlist latest_price
- Serializer: dynamic_layers (6 OneToOne), get_latest_price
- 페이지네이션: 스크리너 6개 뷰, 뉴스 list 3종, RAG basket/session, MVP

---

## 1. N+1 쿼리 이슈 (14건)

### 1.1 HIGH — `stocks/views_indicators.py:324-369` (IndicatorComparisonView.post)

**현상**: 요청 symbols 리스트 N개에 대해 루프 안에서 `Stock.objects.get(symbol=symbol)` (line 328) + `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50].values_list(...)` (line 333) 호출 → **2N 쿼리**.

**권장 수정** (난이도: 중간)
```python
# 1) Stock 일괄 조회
stocks_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=[s.upper() for s in symbols])}

# 2) DailyPrice를 Prefetch + 슬라이싱은 별도 처리 (Django ORM은 prefetch slice 미지원)
#    각 stock별 최근 50개를 한 번에: window function 또는 raw SQL,
#    또는 SubqueryAnnotation, 또는 stock_id IN (...) 쿼리 1번으로 가져와서 dict 분배
```

---

### 1.2 HIGH — `news/api/views.py:344-358` (NewsViewSet.trending)

**현상**: trending_data 10개에 대해 루프 안에서 `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')[:3]` (line 348) 호출 → **10 쿼리**. 또한 `NewsArticleListSerializer` 내 `entities`(NewsEntitySimpleSerializer many=True)에서 prefetch 누락 시 추가 N+1.

**권장 수정** (난이도: 중간)
```python
# symbols 일괄 추출
symbols = [item['symbol'] for item in trending_data]
# 한 번에 fetch 후 symbol별로 그루핑 (Python에서 정렬/slice)
articles_qs = NewsArticle.objects.filter(
    entities__symbol__in=symbols,
    published_at__gte=from_date,
).distinct().prefetch_related('entities').order_by('-published_at')
# 이후 symbol → article 3개씩 dict 분배
```

---

### 1.3 HIGH — `stocks/serializers.py:205-307` (OverviewTabSerializer.get_dynamic_layers)

**현상**: 단일 Stock 객체당 OneToOne 5개 (`overview_ko`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + ForeignKey reverse 1개 (`category_signals.all()`) 접근 → **객체당 최대 7 쿼리**.
`stocks/views.py:502` `StockOverviewAPIView`에서는 `overview_ko`만 `select_related`로 처리되고 나머지 6개는 미처리. `StockCompleteDataAPIView`(line 830)에서는 dynamic_layers 호출 시 7쿼리 모두 발생.

**권장 수정** (난이도: 쉬움)
```python
Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals').filter(symbol=symbol).first()
```
※ `views.py:502`의 주석(`TODO: Step 2~4`)이 인지 표시 — 즉시 적용 가능.

---

### 1.4 HIGH — `stocks/serializers.py:398-403` (WatchListStockSerializer.get_latest_price)

**현상**: `SerializerMethodField`로 stock당 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` 호출. `many=True` 직렬화 시 **N 쿼리**. 또한 `get_chart_data`(line 405)는 `return` 문이 누락되어 항상 `None`을 반환하지만 쿼리는 실행됨 (**+ N 쿼리, 결과 폐기**).

**권장 수정** (난이도: 중간)
```python
# View 단에서 Subquery로 latest price를 stock에 어노테이트
from django.db.models import OuterRef, Subquery
latest = DailyPrice.objects.filter(stock=OuterRef('pk')).order_by('-date').values('close_price')[:1]
qs = Stock.objects.annotate(latest_close=Subquery(latest))
```
그리고 `get_chart_data`는 `return` 추가 또는 필드 제거.

---

### 1.5 MED — `stocks/views.py:830-884` (StockCompleteDataAPIView)

**현상**: 한 요청당 Stock 1개 + DailyPrice + BalanceSheet/Income/CashFlow 각각 별도 쿼리(이건 정상) + `OverviewTabSerializer(stock).data` 호출 시 dynamic_layers의 6 쿼리(1.3 참조). select_related 없음.

**권장 수정** (난이도: 쉬움): 1.3과 동일하게 `select_related` 6개 추가.

---

### 1.6 MED — `validation/api/views.py:112-125` (ValidationSummaryView rank_metrics 루프)

**현상**: 5개 rank_metrics 루프에서 회차마다 `CompanyBenchmarkDelta.objects.filter(...).first()` + `MetricDefinition.objects.filter(pk=mc).first()` → **10 쿼리**.

**권장 수정** (난이도: 중간)
```python
deltas = {d.metric_code_id: d for d in CompanyBenchmarkDelta.objects.filter(
    symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics,
)}
mds = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=rank_metrics)}
```

---

### 1.7 MED — `validation/api/views.py:148-161` (ValidationSummaryView._find_leader)

**현상**: `peers = Stock.objects.filter(...).order_by(...)` 이후 `peers.first()` + `peers.count()` + `peers[1]` → **동일 쿼리 3회 평가**.

**권장 수정** (난이도: 쉬움)
```python
peers = list(Stock.objects.filter(symbol__in=peer_symbols).order_by('-market_capitalization'))
```

---

### 1.8 MED — `validation/api/views.py:199-314` (ValidationMetricsView._build_metric)

**현상**: `category=all` 요청 시 ~40개 metric 루프, 각 metric당:
- `MetricDefinition.filter().first()` (1)
- `CompanyMetricSnapshot.filter().first()` 최대 2회 (line 222, 236)
- `CompanyBenchmarkDelta.filter().first()` (line 248)
- history slice 5건마다 `PeerMetricBenchmark.filter().first()` (line 274)

→ metric당 **최대 9 쿼리 × 40개 = 360 쿼리**. 단일 종목 페이지 진입 시 매우 무거움.

**권장 수정** (난이도: 높음): metric_code 전체 set으로 bulk fetch 후 메모리에서 그루핑. category_signals도 bulk 조회.

---

### 1.9 MED — `validation/api/views.py:364-403` (LeaderComparisonView 루프)

**현상**: `all_metrics` (~40개) 루프, 각 회차마다 `MetricDefinition.first()` + `CompanyMetricSnapshot.first()` (회사) + `CompanyMetricSnapshot.first()` (리더) = **120 쿼리**.

**권장 수정** (난이도: 중간)
```python
metric_codes = [mc for _, mc in all_metrics]
mds = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_codes)}
company_snaps = {s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
    symbol=stock, fiscal_year=latest_fy, metric_code_id__in=metric_codes, value_status='normal',
)}
leader_snaps = {s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
    symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id__in=metric_codes, value_status='normal',
)}
```

---

### 1.10 MED — `chainsight/api/views.py:80-91` (ChainSightGraphView edges 루프)

**현상**: Neo4j 결과 edges 루프 안에서 `CoMentionEdge.objects.filter().first()` + `PriceCoMovement.objects.filter().first()` → 엣지 N × 2 쿼리. depth=3 시 수십~수백.

**권장 수정** (난이도: 중간)
```python
pairs = [(min(e['from'], e['to']), max(e['from'], e['to'])) for e in edges]
cms = {(c.symbol_a, c.symbol_b): c for c in CoMentionEdge.objects.filter(...).filter(pair_in=pairs)}
# tuple in filter는 직접 안 됨 — Q OR 또는 별도 색인 컬럼 권장
```

---

### 1.11 MED — `chainsight/api/views.py:150-159` (ChainSightSuggestionView co_mentions)

**현상**: `CoMentionEdge.objects.filter(symbol_a=symbol).union(symbol_b=symbol).order_by('-co_mention_count')[:10]` 자체는 1쿼리지만, 직후 루프(line 158)에서 `cm.symbol_a`/`symbol_b` 비교만 수행 — **OK**. 다만 `union` 후 `order_by`는 PostgreSQL에서 sort 비용 큼. 인덱스 활용 가능한 `Q(symbol_a=s)|Q(symbol_b=s)` 권장.

**권장 수정** (난이도: 쉬움): `filter(Q(symbol_a=symbol)|Q(symbol_b=symbol))`로 단일 쿼리화.

---

### 1.12 LOW — `users/views.py:188-196` (UserFavorites)

**현상**: `user.favorite_stock.all()` → StockSerializer(many=True). M2M의 prefetch 명시 없음. `request.user.favorite_stock.prefetch_related(...)` 또는 `User.objects.prefetch_related('favorite_stock').get(pk=...)` 형태 권장.

**난이도**: 쉬움

---

### 1.13 LOW — `users/views.py:404-433` (PortfolioDetailTableView)

**현상**: `select_related('stock')` 적용됨. 두 번의 list 평가(`sum(...) for p in portfolios`)는 동일 QS 2회 평가 → 캐시되지만 `list(portfolios)` 1회 변환 후 재사용이 안전.

**난이도**: 쉬움

---

### 1.14 LOW — `news/api/views.py:1500+` (pipeline_health)

**현상**: 6개 Phase 각각 별도 NewsCollectionLog/NewsArticle/MLModelHistory 쿼리 → 약 20+ 쿼리. 5분 캐시 적용되어 미스 시에만 발생.

**난이도**: 중간 (재구조화 필요). 캐싱으로 완화됨.

---

## 2. 인덱스 누락 (3건)

### 2.1 MED — `news/models.py:82` (NewsArticle.category)

**현상**: `category` 필드 `db_index=True` 없음. `filter(category__in=db_categories)` 사용 — `views.py:287, 431, 286`. 기존 composite index `(-published_at, category)`(line 193) 있어서 `published_at` 정렬 + category 필터 조합에서는 활용됨. **단독 category 필터 시 미활용**.

**권장 수정** (난이도: 쉬움): `category` 단독 인덱스가 필요한지는 쿼리 패턴 검토. 현재 코드에서는 항상 published_at 동반 — 사실상 **활용 가능** → 실제로는 LOW.

---

### 2.2 MED — `news/models.py:90, 95` (NewsArticle.finnhub_id, marketaux_uuid)

**현상**: 두 필드 모두 `unique=True`로 인덱스는 있지만 `filter(finnhub_id__isnull=False)` (line 418, 483)에서 IS NOT NULL 카운팅에 사용. NULL이 많은 컬럼은 partial index 가 유리하나 Django ORM에서 직접 지원 안 함. `sources` action은 1시간 캐시 → 우선순위 낮음.

**권장**: 현 상태 유지. 캐시로 충분.

---

### 2.3 LOW — `stocks/models.py:715` (StockOverviewKo)

**현상**: `class Meta`만 정의되어 있고 `indexes`/`db_index` 명시 없음 (primary_key가 OneToOne으로 stock_id이므로 OK). 추가 인덱스 불필요.

---

## 3. 느린 Serializer (2건)

### 3.1 HIGH — `stocks/serializers.py:205-307` (OverviewTabSerializer.get_dynamic_layers)

→ 섹션 1.3 참조 (N+1으로 분류).

---

### 3.2 HIGH — `stocks/serializers.py:398-403` (WatchListStockSerializer.get_latest_price + get_chart_data)

→ 섹션 1.4 참조. 추가로 `get_chart_data`는 `return` 누락으로 결과 폐기되는 dead query 발생.

---

## 4. 페이지네이션 누락 (11건)

### 4.1 HIGH — `stocks/views_screener.py` 6개 뷰

| 뷰 | 라인 | limit 기본/최대 |
|----|------|----------------|
| StockScreenerView | 60 | 100/1000 |
| LargeCapStocksView | 257 | 50/1000 |
| HighDividendStocksView | 306 | 50/1000 |
| SectorStocksView | 357 | 100/1000 |
| LowBetaStocksView | 411 | 50/1000 |
| ExchangeStocksView | 462 | 100/1000 |

**현상**: 모두 `pagination_class` 미설정, query param `limit`만 사용. 최대 1000개 일괄 반환. 응답 크기 폭주 + 클라이언트 측 페이지네이션 강제.

**권장 수정** (난이도: 쉬움): `PageNumberPagination` 적용. `stocks/views.py:77`의 `StockListPagination` 패턴 참고.

---

### 4.2 HIGH — `news/api/views.py:70-119` (stock_news action)

**현상**: `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')` 후 **slice 없이** serialize. 종목당 뉴스 누적 시 수백~수천 건 반환 가능.

**권장 수정**: limit 추가 or `NewsArticlePagination` 적용 (이미 정의됨, line 45).

---

### 4.3 HIGH — `news/api/views.py:303-363` (market, trending actions)

**현상**: `articles[:limit]` 하드코딩. limit max 검증 없음 (`int(...) or 20`). DoS surface.

**권장**: limit upper bound (예: 100) 적용.

---

### 4.4 HIGH — `rag_analysis/views.py:50, 377` (DataBasketListCreateView, AnalysisSessionListCreateView)

**현상**: `.filter(user=request.user)` 그대로 반환. 사용자당 basket/session 누적 시 응답 크기 증가. `prefetch_related('items'/'messages')`까지 함께 — 메모리 부담.

**권장**: PageNumberPagination 적용 (난이도: 쉬움).

---

### 4.5 HIGH — `stocks/views_mvp.py:17, 142` (StockMVPListView, StockRAGContextView)

**현상**: `queryset[:20]` 하드코딩, page param 없음. `StockRAGContextView`는 단일 객체라 OK.

**권장**: limit query param + PageNumberPagination (MED 우선).

---

### 4.6 MED — `users/views.py:262, 974` (PortfolioListCreateView, UserInterestListCreateView)

**현상**: `Portfolio.objects.filter(user=...).select_related('stock')` 그대로 반환. 사용자당 포트폴리오 보통 < 50개이지만 상한 없음.

**권장**: PageNumberPagination + max 100 (난이도: 쉬움).

---

### 4.7 MED — `news/api/views.py:1693+` (ml_trend, llm_usage admin actions)

**현상**: weeks/days 파라미터로 범위 제어, 1시간 캐시. 페이지네이션 없이도 안전 (행 수 적음).

**권장**: 현 상태 유지.

---

### 4.8 LOW — `validation/api/views.py:427` (PresetListView)

**현상**: 종목당 preset 수 6종으로 고정 — 페이지네이션 불필요.

---

### 4.9 LOW — `chainsight/api/views.py` 그래프 뷰들

**현상**: `limit` cap (30, page_size 20) 잘 적용됨.

---

## 5. 잘 처리된 사례 (참고)

- `users/views.py:599` WatchlistListCreateView — Django Paginator 적용
- `users/views.py:819` WatchlistStocksView — `select_related('stock')` + Paginator
- `stocks/views.py:84` StockListAPIView — `PageNumberPagination` 적용
- `news/api/views.py:55` NewsViewSet — `NewsArticlePagination` 클래스 적용 (단, 일부 action에서는 우회됨)
- `stocks/models.py BasicFinancialStatement` — 3종 statement에 composite index `(stock, period_type, fiscal_year)` 적용

---

## 6. 우선순위 패치 권장 순서

1. **stocks/serializers.py OverviewTabSerializer** + `stocks/views.py:502` — select_related 6개 추가 (난이도 쉬움, 영향 큼: 상세 페이지 로딩)
2. **stocks/views_indicators.py IndicatorComparisonView** — symbols bulk fetch
3. **stocks/views_screener.py 6개 뷰** — PageNumberPagination 일괄 적용
4. **validation/api/views.py** — bulk fetch 패턴 (3개 뷰 동시 수정)
5. **stocks/serializers.py WatchListStockSerializer** — Subquery 또는 view 단 prefetch
6. **rag_analysis/views.py basket/session list** — 페이지네이션
7. **news/api/views.py stock_news/market/trending** — limit cap + 페이지네이션

---

**감사 종료**. 코드 수정 없이 발견 사항만 기록함.
