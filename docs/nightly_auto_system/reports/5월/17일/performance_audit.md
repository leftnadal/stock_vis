# API 성능 감사 보고서

- 생성일: 2026-05-17
- 모드: 읽기 전용 (코드 수정 없음)
- 대상: Stock-Vis Django 백엔드 (views 17개 + 모델 7개 + serializers 11개)
- 방법: 정적 분석 (실행/측정 미수행)

---

## 요약

| 심각도 | N+1 / 반복 쿼리 | 페이지네이션 | 인덱스 누락 | Serializer | 합계 |
|--------|----------------|--------------|--------------|------------|------|
| **HIGH** | 2 | 1 | 2 | 2 | **7** |
| **MED**  | 1 | 4 | 1 | 1 | **7** |
| **LOW**  | 0 | 0 | 0 | 1 | **1** |
| **합계** | **3** | **5** | **3** | **4** | **15** |

### HIGH 7건 (우선 처리)

1. `news/api/views.py:346` — trending API 루프 안 `.filter().distinct()` (N+1)
2. `validation/api/views.py:265` — fiscal_year별 PeerMetricBenchmark `.filter().first()` (N+1)
3. `users/views.py:92` — `User.objects.all()` 전체 직렬화 (페이지네이션 없음)
4. `stocks/serializers.py:405` — `WatchListStockSerializer.get_chart_data` 객체마다 DailyPrice 쿼리 + **`return` 누락**
5. `stocks/serializers.py:205` — `OverviewTabSerializer.get_dynamic_layers` 5~6개 OneToOne/역FK 미prefetch
6. `news/models.py:82` — `NewsArticle.category` `db_index` 없음 (대용량 + 자주 필터링)
7. `news/models.py:432` — `DailyNewsKeyword.status` `db_index` 없음 (`status='completed'` 매 요청 조회)

---

## 1. N+1 쿼리 / 반복 쿼리

### [HIGH] news/api/views.py:346-358 — Trending 종목 API

```python
trending_data = NewsEntity.objects.filter(...).values('symbol').annotate(
    news_count=Count('id'), avg_sentiment=Avg('sentiment_score')
).order_by('-news_count')[:limit]

for item in trending_data:                              # 루프
    symbol = item['symbol']
    recent_articles = NewsArticle.objects.filter(        # ← N+1
        entities__symbol=symbol, published_at__gte=from_date
    ).distinct().order_by('-published_at')[:3]
```

- 영향: `limit=10`이면 1 + 10 = 11 쿼리, limit 확장 시 더 악화
- 난이도: 중간
- 권장: `symbol__in=symbols` 단일 쿼리로 한번에 fetch 후 메모리 그룹핑(`defaultdict`)

### [HIGH] validation/api/views.py:265-276 — Peer 벤치마크 조회

```python
snaps = CompanyMetricSnapshot.objects.filter(
    symbol=stock, metric_code=md,
).order_by('fiscal_year')[:5]

for s in snaps:                                         # 루프
    peer_bench = PeerMetricBenchmark.objects.filter(    # ← N+1
        symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
    ).first()
```

- 영향: 최대 5쿼리/메트릭, 여러 메트릭 동시 호출 시 누적
- 난이도: 중간
- 권장: `fiscal_year__in=[s.fiscal_year for s in snaps]` 한 번에 가져와 `dict` 매핑

### [MED] serverless/views_admin.py:475-497 — 카테고리 목록

```python
categories = NewsCollectionCategory.objects.all()
for cat in categories:
    symbols = cat.resolve_symbols()    # ← 메서드 내부 쿼리 발생
    result.append({...})
```

- 영향: 카테고리 수 N에 비례하여 `resolve_symbols()` 내부 ORM 호출
- 난이도: 중간 (resolve_symbols 시그니처 변경 필요)
- 권장: `resolve_symbols(bulk=True)` 또는 사전에 모든 심볼을 bulk fetch

### 검토 후 False Positive 제외

- `stocks/views_eod.py:72-99` — 이미 `.select_related('stock')` 적용됨
- `stocks/views_indicators.py:60/221/333` — `.values()` 호출이라 FK 영향 없음
- `stocks/views_mvp.py:41/115` — `.first()` 단건 또는 FK 없는 Stock 필드 직접 접근

---

## 2. select_related / prefetch_related 누락

### [MED] stocks/views.py:849-852 + 861-873 — StockCompleteDataAPIView

```python
recent_prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]  # 849
chart_data = ChartDataSerializer(recent_prices, many=True).data

balance_sheets = BalanceSheet.objects.filter(stock=stock, ...)[:5]             # 861
income_statements = IncomeStatement.objects.filter(stock=stock, ...)[:5]
cash_flows = CashFlowStatement.objects.filter(stock=stock, ...)[:5]
```

- 영향: serializer가 `stock.symbol` 접근 시 FK 재조회 (30 + 5*3 = 45 쿼리 가능)
- 난이도: 쉬움
- 권장: 각 쿼리셋에 `.select_related('stock')` 추가

### [MED] stocks/views.py:156-158 — 메인 차트 데이터

```python
recent_daily_prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]
context['initial_chart_data'] = ChartDataSerializer(recent_daily_prices, many=True).data
```

- 난이도: 쉬움
- 권장: `.select_related('stock')` 추가

### [MED] stocks/views.py:502-504 — Overview 탭

```python
stock = Stock.objects.select_related('overview_ko').filter(symbol=symbol).first()
```

- 이슈: OverviewTabSerializer가 `category_signals`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`, `validation_news_summary` 등 5~6개 관계 추가 접근 (serializer 이슈 #5 참조)
- 난이도: 쉬움
- 권장: `prefetch_related('category_signals')` + 각 OneToOne `select_related` 동시 적용

### [MED] chainsight/api/views.py:451-529 — NeighborGraphView

```python
stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=neighbor_symbols)}
# 이후 응답 가공 시 stock 관련 FK 접근 가능성
```

- 난이도: 중간
- 권장: 응답에서 사용하는 FK가 있다면 `select_related` / `prefetch_related` 명시. 그리고 `neighbor_symbols` 크기 제한 강화 (`min(limit, 30)`).

---

## 3. 페이지네이션 누락

### [HIGH] users/views.py:92-94 — 전체 사용자 목록

```python
def get(self, request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)
```

- 영향: 사용자 수에 비례하여 메모리/응답 시간 증가, 관리자 엔드포인트지만 무제한
- 난이도: 쉬움
- 권장: `pagination_class = PageNumberPagination` 적용 또는 `Paginator` 수동 처리

### [MED] users/views.py:188-196 — 즐겨찾기 목록

```python
favorite_stocks = user.favorite_stock.all()
serializer = StockSerializer(favorite_stocks, many=True)
```

- 영향: 일반 사용자는 적지만 상한 없음 + StockSerializer가 무거우면 누적
- 난이도: 쉬움
- 권장: `[:100]` slice 또는 페이지네이션

### [MED] chainsight/api/views.py:391-417 — SectorGraphView

- `limit=12`(기본), `limit` 쿼리 파라미터 상한 검증 일부 미흡
- 권장: `min(int(limit), 30)` 가드 + 페이지네이션 도입 고려

### [MED] chainsight/api/views.py:451-529 — NeighborGraphView

- Neo4j 결과 + Stock 매핑 모두 상한 검증 강화 필요
- 권장: `min(limit, 30)` 가드 일관 적용

### 양호 (페이지네이션 적용 확인됨)

- `stocks/views.py:81 StockListAPIView` — `StockListPagination` 적용 ✓
- `news/api/views.py` 리스트 ViewSet — DRF 기본 페이지네이션
- `rag_analysis/views.py` — prefetch 적절, 페이지네이션 적용

---

## 4. 인덱스 누락

### [HIGH] news/models.py:82 — NewsArticle.category

```python
category = models.CharField(
    max_length=20,
    choices=CATEGORY_CHOICES,
    default='general',
    help_text=_("뉴스 카테고리")
)
```

- 사용처:
  - `news/api/views.py:431` `queryset.filter(category__in=db_categories)`
  - `serverless/views.py:890` `queryset.filter(category=category)`
- 영향: NewsArticle은 대용량(일별 수백~수천 건 적재). 필터 빈도 높음
- 난이도: 쉬움 (`db_index=True` 추가 + 마이그레이션)
- 권장: `db_index=True` 또는 `Meta.indexes = [Index(fields=['category', '-published_at'])]`

### [HIGH] news/models.py:432 — DailyNewsKeyword.status

```python
status = models.CharField(
    max_length=20, choices=KEYWORD_STATUS_CHOICES,
    default='pending',
)
```

- 사용처:
  - `news/services/market_feed.py:84` `filter(date=today, status='completed').first()`
  - `news/services/market_feed.py:89` `filter(status='completed').order_by('-date').first()`
- 영향: 매 요청마다 status 필터
- 난이도: 쉬움
- 권장: `Meta.indexes = [Index(fields=['-date', 'status']), Index(fields=['status', '-date'])]`

### [MED] serverless/models.py:497 — ScreenerFilter.is_active

```python
is_active = models.BooleanField(default=True)
```

- 사용처:
  - `serverless/views.py:1054` `filter(is_active=True).order_by('category', 'display_order')`
  - `serverless/services/filter_engine.py:196` 동일 패턴
- 난이도: 쉬움
- 권장: `db_index=True` 또는 `Index(fields=['is_active', 'category', 'display_order'])` 복합

### 양호 (이미 인덱스 적용됨)

- `news/models.py:616` NewsCollectionCategory.is_active — `db_index=True` 적용 ✓
- `rag_analysis/models.py:336` UsageLog — `(user, created_at)`, `(model, created_at)` 등 충분
- `stocks/models.py` — DailyPrice/EODSignal/StockNews 자주 쓰는 조합 인덱스 존재
- `users/models.py`, `sec_pipeline/models.py`, `graph_analysis/models.py` — 충분

---

## 5. Serializer 추가 쿼리

### [HIGH] stocks/serializers.py:405-409 — WatchListStockSerializer.get_chart_data

```python
def get_chart_data(self, obj):
    """최근 7일 차트 데이터"""
    recent_prices = DailyPrice.objects.filter(
        stock=obj
    ).order_by('-date')[:7]
    # ← return 문 없음! 항상 None 반환
```

- 이중 결함:
  1. **`return` 누락** → 차트 데이터가 항상 `None`. 기능 버그.
  2. list 직렬화 시 객체마다 DailyPrice 쿼리 (N+1)
- 영향: N개 워치리스트 → N개 추가 쿼리, 결과는 빈 값
- 난이도: 중간
- 권장:
  - 우선 `return ChartDataSerializer(recent_prices, many=True).data` 추가하여 기능 복구
  - View에서 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])` 적용 후 메모리 슬라이스

### [HIGH] stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers

```python
def get_dynamic_layers(self, obj):
    signals = list(obj.category_signals.all())            # 215
    ns = obj.validation_news_summary                      # 235
    sp = obj.sensitivity_profile                          # 252
    gs = obj.growth_stage                                 # 267
    cd = obj.capital_dna                                  # 281
    nt = obj.narrative_tag                                # 295
```

- 이미 코드에 `TODO: prefetch_related + 캐싱 레이어 적용 필요` 주석(208) 존재 — 미해결
- 영향: detail 요청당 5~6개 추가 쿼리. list 호출 시 5~6 × N
- 난이도: 중간
- 권장: View(`stocks/views.py:502`)에서
  ```python
  Stock.objects.select_related(
      'overview_ko', 'validation_news_summary', 'sensitivity_profile',
      'growth_stage', 'capital_dna', 'narrative_tag'
  ).prefetch_related('category_signals')
  ```

### [MED] serverless/serializers.py:121-137 — MarketMoverListSerializer 3종 display

```python
def get_sector_alpha_display(self, obj):
    from serverless.services.indicators import IndicatorCalculator
    calc = IndicatorCalculator()      # 객체마다 인스턴스화
    return calc.format_sector_alpha_display(obj.sector_alpha)
```

- 영향: DB 쿼리 아님, CPU/메모리 낭비. 100건 × 3 메서드 = 300 인스턴스
- 난이도: 쉬움
- 권장: 모듈 레벨 싱글톤 또는 `__init__`에서 캐시
  ```python
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self._calc = IndicatorCalculator()
  ```

### [LOW] users/serializers.py:103-109 — PortfolioDetailSerializer.get_portfolio_weight

```python
total_portfolio_value = self.context.get('total_portfolio_value', 0)
if total_portfolio_value > 0:
    return (obj.total_value / total_portfolio_value) * 100
return 0
```

- 이슈: 컨텍스트 의존(없으면 silent fail). 패턴 자체는 정상
- 난이도: 쉬움 (문서화 또는 가드)
- 권장: docstring로 view 측 책임 명시

### Serializer 양호

- `rag_analysis/serializers.py` — nested `many=True` 명시
- `config/serializers.py` — 스키마용 (ORM 없음)
- `stocks/serializers_fundamentals.py`, `_market_movers.py`, `_exchange.py`, `_screener.py` — 외부 API 응답용
- `macro/serializers.py`, `news/api/serializers.py` — `source=` 명시 + nested

---

## 6. 우선순위별 처리 권고

### 즉시 (HIGH, 쉬움)
1. `stocks/serializers.py:405` `WatchListStockSerializer.get_chart_data` **return 누락 수정** — 기능 버그
2. `users/views.py:92` 사용자 목록 페이지네이션 추가
3. `news/models.py:82` `NewsArticle.category` `db_index=True`
4. `news/models.py:432` `DailyNewsKeyword.status` 복합 인덱스

### 단기 (HIGH, 중간)
5. `news/api/views.py:346` trending API N+1 → `symbol__in` 단일 쿼리
6. `validation/api/views.py:265` Peer 벤치마크 → `fiscal_year__in` 단일 쿼리
7. `stocks/serializers.py:205` `OverviewTabSerializer` prefetch_related 적용

### 중기 (MED)
8. `stocks/views.py:156/502/849/861` select_related 보강
9. `serverless/models.py:497` `ScreenerFilter.is_active` 인덱스
10. `serverless/serializers.py:121` IndicatorCalculator 캐시
11. `users/views.py:188`, `chainsight/api/views.py:391/451` 페이지네이션/limit 가드

### 장기 (LOW)
12. `users/serializers.py:103` 컨텍스트 의존 문서화

---

## 7. 검사 범위 및 한계

### 검사한 파일
- Views (17): stocks/* 8개, users, news/api, macro, rag_analysis, serverless/views_admin, validation/api, chainsight/api, sec_pipeline
- Models (7): stocks, users, news, serverless, rag_analysis, sec_pipeline, graph_analysis
- Serializers (11): stocks/* 6개, users, news/api, macro, rag_analysis, config, serverless

### 한계
- **정적 분석 only**: `django-silk`/`django-debug-toolbar`로 실제 쿼리 카운트 검증 권장
- **실행 측정 없음**: 위 추정 영향(쿼리 수)은 코드 패턴 기반 추론
- **외부 호출**: `resolve_symbols()`, Neo4j repo 내부 쿼리는 본 감사 범위 외
- **`stocks/views.py`** 일부 라인은 serializer 정의를 함께 봐야 정확 — OverviewTabSerializer는 별도 확인 완료

### 추가 권고
- 운영 환경에서 `EXPLAIN ANALYZE`로 인덱스 효과 검증
- pgBadger / pg_stat_statements로 실측 핫 쿼리 식별 후 인덱스 우선순위 재조정
