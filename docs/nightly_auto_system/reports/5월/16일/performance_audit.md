# API 성능 감사 보고서

- **작성일**: 2026-05-16
- **대상 프로젝트**: Stock-Vis (Django REST Framework)
- **감사 범위**: views 17개 + serializers 10개 + models 7개
- **모드**: 읽기 전용 정적 분석 (코드 수정 없음)
- **방법론**: 4개 영역 병렬 정적 분석 (N+1 ×2, 인덱스+Serializer, 페이지네이션)

---

## 1. 요약 (이슈 수 by 심각도)

| 카테고리 | HIGH/CRITICAL | MED | LOW | 합계 |
|----------|---------------|-----|-----|------|
| N+1 쿼리 (View 계층, stocks 앱) | 5 | 4 | 2 | 11 |
| N+1 쿼리 (View 계층, 외부 앱) | 4 | 1 | 0 | 5 |
| Serializer N+1 (SerializerMethodField/Nested) | 6 | 4 | 0 | 10 |
| DB 인덱스 누락 | 0 | 1 | 5 | 6 |
| 페이지네이션 누락 | 6 | 1 | 1 | 8 |
| **합계** | **21** | **11** | **8** | **40** |

### 수정 난이도 분포

| 난이도 | View N+1 | Serializer N+1 | 인덱스 | 페이지네이션 | 합계 |
|--------|----------|----------------|--------|---------------|------|
| 쉬움 | 8 | 4 | 6 | 2 | 20 |
| 중간 | 6 | 5 | 0 | 6 | 17 |
| 높음 | 2 | 1 | 0 | 0 | 3 |

### 최우선 처리 대상 (Top 5)

1. **CRITICAL** — `stocks/serializers.py:205-307` `OverviewTabSerializer.get_dynamic_layers()` 6개 OneToOne/reverse 관계 prefetch 누락 (list 100건 → 700+ 쿼리)
2. **HIGH** — `validation/api/views.py:364-374` `LeaderComparisonView` 루프 3중 쿼리 (105 튜플 × 3 = 315 쿼리)
3. **HIGH** — `stocks/views_screener.py` 6개 endpoint pagination_class 누락 + limit=1000 허용
4. **HIGH** — `stocks/serializers.py:398-409` `WatchListStockSerializer` 매 종목당 DailyPrice 2회 조회 (10종목 → 21 쿼리)
5. **HIGH** — `stocks/views_indicators.py:324-340` `IndicatorComparisonView.post()` 루프 내 `Stock.objects.get()` (10심볼 → 20 쿼리)

---

## 2. 상세 — 카테고리 A: N+1 쿼리 (View 계층)

### A-1. stocks/views.py:502-504 — StockOverviewAPIView 동적 레이어 누락 prefetch

```python
stock = Stock.objects.select_related(
    'overview_ko',
).filter(symbol=symbol).first()
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **문제**: `OverviewTabSerializer.get_dynamic_layers()` 가 obj.category_signals / obj.validation_news_summary / obj.sensitivity_profile / obj.growth_stage / obj.capital_dna / obj.narrative_tag 등 7개 관계를 추가로 조회. 단일 stock 기준 1 → 8 쿼리.
- **권장 수정**:
```python
stock = Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals').filter(symbol=symbol).first()
```

### A-2. stocks/views.py:849-883 — StockCompleteDataAPIView 순차 4 테이블 조회

- **심각도**: MED
- **수정 난이도**: 쉬움
- **문제**: DailyPrice + BalanceSheet + IncomeStatement + CashFlowStatement 를 단일 endpoint 안에서 순차로 4번 쿼리 (N+1은 아니지만 라운드트립 비효율).
- **권장 수정**: 가능한 경우 단일 prefetch_related 로 묶거나 async 병렬 조회.

### A-3. stocks/views_indicators.py:324-340 — IndicatorComparisonView 루프 내 Stock.objects.get()

```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)
    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]...
```

- **심각도**: HIGH (배치 비교 endpoint)
- **수정 난이도**: 쉬움
- **예상 쿼리**: symbols 10개 입력 시 20 쿼리 (10 + 10).
- **권장 수정**:
```python
stocks_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=[s.upper() for s in symbols])}
for symbol in symbols:
    stock = stocks_map.get(symbol.upper())
    if not stock: continue
    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]...
```

### A-4. stocks/views_mvp.py:44-56 — StockMVPListView 루프 내 필드 접근

- **심각도**: LOW (Stock 단일 모델만 접근, N+1 아님)
- **수정 난이도**: 쉬움
- **권장 수정**: `.values()` 로 변환해 직렬화 비용 감축. 성능 영향은 미미.

### A-5. stocks/views_mvp.py:114-126 — StockMVPDetailView 별개 쿼리

- **심각도**: MED
- **수정 난이도**: 쉬움
- **문제**: Stock 조회 후 IncomeStatement 별도 쿼리 (1 → 2). select_related 적용 불가하므로 prefetch_related 가능 여부 검토.

### A-6. validation/api/views.py:204-208 — ValidationMetricsView._build_metric() 루프 내 MetricDefinition 조회

```python
for mc in metric_codes:
    md = MetricDefinition.objects.filter(pk=mc).first()
    ...
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **예상 쿼리**: 카테고리 7 × 메트릭 15 = 최대 105 추가 쿼리/요청.
- **권장 수정**:
```python
metric_ids = set()
for cat in categories: metric_ids.update(CATEGORY_METRICS.get(cat, []))
metric_dict = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}
for mc in metric_codes:
    md = metric_dict.get(mc)
```

### A-7. validation/api/views.py:265-276 — _build_metric history 루프 내 PeerMetricBenchmark 조회

- **심각도**: HIGH
- **수정 난이도**: 중간
- **예상 쿼리**: 카테고리 × 메트릭 × snap 5건 = 최대 50 쿼리 (A-6 위에 누적).
- **권장 수정**: `fiscal_year__in=[s.fiscal_year for s in snaps]` 로 dict 매핑.

### A-8. validation/api/views.py:364-374 — LeaderComparisonView.get() 루프 3중 쿼리

```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()
    company_snap = CompanyMetricSnapshot.objects.filter(...).first()
    leader_snap  = CompanyMetricSnapshot.objects.filter(...).first()
```

- **심각도**: HIGH (감사 최우선 대상)
- **수정 난이도**: 중간
- **예상 쿼리**: 105 튜플 × 3 = **315 쿼리**.
- **권장 수정**:
```python
metric_ids = [mc for _, mc in all_metrics]
metric_dict = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}
company_snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, fiscal_year=latest_fy, metric_code_id__in=metric_ids, value_status='normal')
leader_snaps  = CompanyMetricSnapshot.objects.filter(symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id__in=metric_ids, value_status='normal')
company_map = {row.metric_code_id: row for row in company_snaps}
leader_map  = {row.metric_code_id: row for row in leader_snaps}
```

### A-9. news/api/views.py:344-358 — NewsViewSet.trending() 루프 내 NewsArticle 조회

```python
for item in trending_data:
    recent_articles = NewsArticle.objects.filter(
        entities__symbol=symbol, published_at__gte=from_date
    ).distinct().order_by('-published_at')[:3]
```

- **심각도**: HIGH (캐시 미스 시 list endpoint)
- **수정 난이도**: 중간
- **예상 쿼리**: limit=10 일 때 10 쿼리 + serializer 오버헤드.
- **권장 수정**: `entities__symbol__in=symbols` 로 한 번에 조회 후 메모리에서 종목별 그룹핑 + `[:3]` 제한.

### A-10. users/views.py:1016-1025 — UserInterestListCreateView 반복 _link_category 호출

- **심각도**: MED
- **수정 난이도**: 중간
- **문제**: N개 interest → 3N 쿼리 (get_or_create × 2 + save). 사용자 호출이지만 입력 크기 가변.
- **권장 수정**: `_link_category` 안의 `interest.save(update_fields=...)` 를 `UserInterest.objects.filter(pk__in=[...]).update(...)` 배치로 변환.

### A-11. chainsight/api/views.py:527-530 — NeighborGraphView (이미 최적화됨, 참고)

- **심각도**: NONE (`stock_map` 으로 bulk fetch 완료)
- **현재 패턴이 다른 모듈의 모범 사례임.

### A-12. 이슈 없음 — 검사 완료 파일

`stocks/views_search.py`, `stocks/views_exchange.py`, `stocks/views_market_movers.py`, `stocks/views_fundamentals.py`, `stocks/views_screener.py`(N+1 관점), `stocks/views_eod.py`(select_related 적용됨), `stocks/views_indicators.py:86`(단일 stock), `macro/views.py`, `rag_analysis/views.py`(prefetch 잘 적용됨), `serverless/views_admin.py`, `sec_pipeline/views.py`.

---

## 3. 상세 — 카테고리 B: Serializer 성능 (N+1)

### B-1. stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers() (CRITICAL)

- **심각도**: CRITICAL
- **수정 난이도**: 높음 (아키텍처 변경)
- **문제**: 6개 OneToOne/reverse 관계를 method field 안에서 직접 접근 (코드에 TODO 주석 존재: line 208).
- **예상 쿼리**: list 100 stocks → 1 + 6×100 = **601 쿼리**.
- **권장 수정**: view 단에서 `prefetch_related('category_signals', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')` 적용.

### B-2. stocks/serializers.py:190-203 — OverviewTabSerializer.get_korean_overview()

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **문제**: `obj.overview_ko` 직접 접근. view 에 `select_related('overview_ko')` 가 항상 적용되는지 확인 필요.
- **권장 수정**: `Stock.objects.select_related('overview_ko')` 보장.

### B-3. stocks/serializers.py:338-356 — DailyPriceSerializer.stock_symbol

```python
stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **예상 쿼리**: DailyPrice 30건 → 31 쿼리.
- **권장 수정**: 모든 DailyPrice list 호출처에서 `select_related('stock')` 적용 또는 SerializerField 를 `source='stock_id'` 로 변경(symbol = stock_id 동일).

### B-4. stocks/serializers.py:398-409 — WatchListStockSerializer.get_latest_price / get_chart_data

- **심각도**: HIGH
- **수정 난이도**: 중간
- **문제**: 각 Stock 마다 `DailyPrice.filter().order_by().first()` + `[:7]`. 10 종목 → 21 쿼리.
- **권장 수정**: View 에서 Subquery annotate 로 latest_price 미리 계산 + `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])` 활용.

### B-5. users/serializers.py:31-62 — PortfolioSerializer FK 접근

```python
stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
stock_name   = serializers.CharField(source='stock.stock_name', read_only=True)
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **권장 수정**: 모든 Portfolio list view 에서 `select_related('stock')` 보장.

### B-6. users/serializers.py:65-154 — PortfolioDetailSerializer 20+ FK 접근

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **문제**: `source='stock.*'` 가 20+ 필드에 분포. select_related 누락 시 모두 동일 row 재조회.
- **권장 수정**: `select_related('stock')` 1줄로 해결.

### B-7. users/serializers.py:276-284 — WatchlistDetailSerializer.items (Nested)

```python
items = WatchlistItemSerializer(many=True, read_only=True)
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **권장 수정**:
```python
Prefetch('items', queryset=WatchlistItem.objects.select_related('stock'))
```

### B-8. news/api/serializers.py:45-91 — NewsArticleListSerializer.entities (일관성 부족)

- **심각도**: MED
- **수정 난이도**: 쉬움
- **문제**: 일부 view 는 `prefetch_related('entities')` 적용 (예: `regulatory_service.py:12`), 일부는 누락 가능.
- **권장 수정**: 모든 NewsArticle list view 에 일관 prefetch 적용 (검증 필요).

### B-9. news/api/serializers.py:9-34 — EntityHighlightSerializer (이중 Nested)

- **심각도**: MED
- **수정 난이도**: 중간
- **문제**: NewsArticle → Entities → Highlights 3중 nested. list view 에서 사용 시 폭발.
- **권장 수정**: list view 에서는 `NewsEntitySimpleSerializer` (line 37-42) 사용, detail view 에서만 풀 serializer.

### B-10. serverless/serializers.py:88-137 — MarketMoverListSerializer 인스턴스 재생성

```python
def get_sector_alpha_display(self, obj):
    calc = IndicatorCalculator()
    return calc.format_sector_alpha_display(obj.sector_alpha)
```

- **심각도**: MED (DB 이슈 아님, CPU/메모리)
- **수정 난이도**: 중간
- **권장 수정**: 모듈 레벨 인스턴스 캐싱 또는 클래스 메서드 변환.

### B-11. rag_analysis/serializers.py:65-83 — AnalysisSessionSerializer 다중 nested

- **심각도**: MED
- **수정 난이도**: 중간
- **권장 수정**:
```python
queryset.prefetch_related('messages', Prefetch('basket', queryset=DataBasket.objects.prefetch_related('items')))
```

---

## 4. 상세 — 카테고리 C: DB 인덱스 누락

### C-1. news/models.py:186 — NewsArticle.created_at db_index 누락

- **심각도**: MED
- **수정 난이도**: 쉬움
- **현재**: `created_at = models.DateTimeField(auto_now_add=True)` (인덱스 없음)
- **사용처**: `serverless/services/admin_status_service.py` `created_at__gte=last_24h`.
- **권장 수정**: `created_at = models.DateTimeField(auto_now_add=True, db_index=True)` + migration.

### C-2. rag_analysis/models.py:60-114 — BasketItem 인덱스 누락

- **심각도**: LOW (작은 테이블)
- **수정 난이도**: 쉬움
- **권장 수정**:
```python
class Meta:
    indexes = [models.Index(fields=['basket', 'item_type'])]
```

### C-3. sec_pipeline/models.py:15-55 — RawDocumentStore.fiscal_year 인덱스 누락

- **심각도**: LOW
- **수정 난이도**: 쉬움
- **권장 수정**:
```python
indexes = [
    models.Index(fields=['symbol', '-filing_date']),
    models.Index(fields=['symbol', 'fiscal_year']),
]
```

### C-4. sec_pipeline/models.py:61-116 — SupplyChainEvidence.relationship_type 단독 인덱스 누락

- **심각도**: LOW
- **수정 난이도**: 쉬움
- **권장 수정**: 필드에 `db_index=True` 또는 `models.Index(fields=['relationship_type'])`.

### C-5. stocks/models.py:886-914 — StockNews.symbol 중복 (설계 이슈)

- **심각도**: LOW (의도된 비정규화일 가능성 높음)
- **수정 난이도**: 평가만, 변경 비추천.
- **현재 인덱스**: `['symbol', '-published_at']` 존재 → 현 상태 유지 권장.

### C-6. stocks/models.py / users/models.py 등 — ✅ 정상 검증

- `DailyPrice`: `['stock', 'date']`, `['date', 'volume']`, `['stock', '-date']` 존재.
- `Portfolio`: `['user', 'stock']`, `['user', '-updated_at']` 존재.
- `EODSignal`, `StockKeyword`: 충분한 인덱스 구성.
- **결론**: 인덱스 관점에서는 큰 문제 없음. 인덱스보다 N+1 쪽이 훨씬 큰 이슈.

---

## 5. 상세 — 카테고리 D: 페이지네이션 누락

### 글로벌 설정

- **파일**: `config/settings.py:348-367`
- **결론**: `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` **명시되지 않음** → 모든 list endpoint 가 명시적 `pagination_class` 또는 `[:N]` 슬라이싱을 해야 안전.

### D-1 ~ D-6. stocks/views_screener.py — 6개 endpoint pagination 누락

| 라인 | 클래스 | 엔드포인트 |
|------|--------|-----------|
| 60-157 | StockScreenerView | `/stocks/screener/` |
| 243-289 | LargeCapStocksView | `/stocks/screener/large-cap/` |
| 291-338 | HighDividendStocksView | `/stocks/screener/high-dividend/` |
| 340-394 | SectorStocksView | `/stocks/screener/sector/{sector}/` |
| 396-443 | LowBetaStocksView | `/stocks/screener/low-beta/` |
| 445-499 | ExchangeStocksView | `/stocks/screener/exchange/{exchange}/` |

- **심각도**: HIGH (6개 동일 패턴)
- **수정 난이도**: 중간 (응답 envelope 변경 필요 → 클라이언트 영향)
- **문제**:
  - `limit` 파라미터로 1~1000 허용
  - `pagination_class` 명시 없음
  - 최악의 경우 1000건 단일 응답 → 직렬화 시간/네트워크 폭증
- **권장 수정**:
```python
class ScreenerResponsePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200

# 6개 view 모두에
pagination_class = ScreenerResponsePagination
# 응답 envelope: {results, pagination} 으로 통일
```

### D-7. users/views.py:91-94 — Users.get() (admin list)

```python
def get(self, request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)
```

- **심각도**: MED (관리자 전용, User 통상 < 500)
- **수정 난이도**: 쉬움
- **권장 수정**: 전용 PageNumberPagination 적용.

### D-8. rag_analysis/views.py:50-54 — DataBasketListCreateView.get()

- **심각도**: LOW (DataBasket.MAX_ITEMS = 5 제약)
- **수정 난이도**: 쉬움
- **권장 수정**: 일관성 차원에서 추가 권장이지만 기능적 영향 없음.

### 검사 완료 (페이지네이션 OK)

- `stocks/views.py` (StockListPagination 명시), `stocks/views_search.py`, `stocks/views_exchange.py` (BatchQuotes 100 제한), `stocks/views_eod.py` (`[:50]`, `[:7]`), `stocks/views_market_movers.py` (limit 1~20), `stocks/views_fundamentals.py` (limit max 40), `stocks/views_indicators.py`, `stocks/views_mvp.py` (`[:20]`), `users/views.py` (Watchlist/WatchlistStocks 수동 Paginator), `news/api/views.py` (NewsArticlePagination + `[:limit]`), `macro/views.py`, `serverless/views_admin.py`, `validation/api/views.py` (단일 종목), `chainsight/api/views.py` (depth/[:10] 제한), `sec_pipeline/views.py`.

---

## 6. 우선순위 로드맵

### P0 (즉시 — 1~2일, HIGH/CRITICAL)

1. **B-1** `OverviewTabSerializer.get_dynamic_layers()` — view 에 prefetch_related 추가 (코드 내 TODO 해결)
2. **A-8** `LeaderComparisonView` 루프 3중 쿼리 → bulk IN + dict 매핑 (315 쿼리 → 3 쿼리)
3. **A-3** `IndicatorComparisonView.post()` 루프 내 `Stock.objects.get()` → `filter(symbol__in=...)`
4. **B-4** `WatchListStockSerializer` price 계산 → Subquery annotate 또는 Prefetch
5. **D-1~D-6** Screener 6개 endpoint pagination_class 추가 (응답 envelope 변경 협의 필요)

### P1 (1주 — HIGH/MED 보강)

6. **A-1** `StockOverviewAPIView` select_related/prefetch_related 통합
7. **A-6 + A-7** `ValidationMetricsView` MetricDefinition + PeerMetricBenchmark dict 매핑
8. **A-9** `NewsViewSet.trending()` 종목별 article bulk fetch
9. **B-5, B-6, B-7** Portfolio/Watchlist serializer 쪽 select_related/Prefetch 보장
10. **B-3** DailyPriceSerializer 호출처 select_related 또는 source='stock_id' 변환

### P2 (다음 스프린트 — MED/LOW)

11. **A-10** UserInterestListCreateView 배치 update 적용
12. **A-2, A-5** 다중 테이블 순차 조회 묶기
13. **B-8, B-9, B-11** Nested serializer Prefetch 일관화
14. **C-1** NewsArticle.created_at db_index 추가 + migration
15. **D-7** users.Users.get() pagination 추가

### P3 (백로그 — LOW)

16. **B-10** MarketMoverListSerializer 인스턴스 캐싱
17. **C-2, C-3, C-4** BasketItem / RawDocumentStore / SupplyChainEvidence 인덱스 보강
18. **D-8** DataBasket list pagination (일관성)
19. **A-4** MVP list values() 최적화

---

## 7. 부록 — 모니터링/회귀 방지 권장

- **django-debug-toolbar**: 개발 환경 쿼리 카운트 가시화
- **django-silk** 또는 **django-querycount**: 자동 N+1 감지
- **테스트**: 핵심 list endpoint 에 `assertNumQueries()` 회귀 테스트 추가 (예: WatchlistList, ScreenerList, ValidationMetrics)
- **CI gate**: PR 별 쿼리 수 임계치 (예: list endpoint 5쿼리 이내) 자동 검증

---

## 8. 부록 — 본 감사에서 제외된 항목

- **서비스 계층 / processor 계층**: 본 감사는 `views*.py` + `serializers*.py` + `models.py` 한정. service 내부 루프 쿼리는 별도 감사 필요.
- **Celery tasks**: `*/tasks.py` 는 @infra 담당 영역으로 본 감사 제외.
- **외부 API rate limit / 캐시 적중률**: 별도 캐시 감사에서 다룰 항목.
- **쿼리 실행 시간(EXPLAIN ANALYZE)**: 정적 분석 한계로 측정 불가. 운영 DB 로 별도 측정 권장.
- **graph_analysis/models.py 인덱스**: 모델/서비스만 존재하고 API 미구현이라 영향 LOW, 본 감사 우선순위 밖.

---

**감사 종료. 코드 수정 없음. 본 보고서는 읽기 전용 정적 분석 결과만 포함.**
