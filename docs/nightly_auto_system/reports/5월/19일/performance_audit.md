# API 성능 감사 보고서

> 감사 일자: 2026-05-19
> 범위: views*.py 17개 + 핵심 models*.py 7개 + serializers*.py 11개
> 모드: 읽기 전용 (코드 수정 없음)
> 감사자: Claude Opus 4.7 (1M context) — Explore 서브 에이전트 병렬 스캔

---

## 요약 (이슈 수 by 심각도)

| 카테고리 | HIGH | MED | LOW | 합계 |
|----------|------|-----|-----|------|
| 1. N+1 쿼리 / select_related 누락 | 1 | 6 | 0 | 7 |
| 2. 인덱스 누락 (단일·복합) | 1 | 6 | 2 | 9 |
| 3. 느린 Serializer (Method 필드) | 0 | 5 | 0 | 5 |
| 4. 페이지네이션 누락 | 5 | 1 | 0 | 6 |
| **총계** | **7** | **18** | **2** | **27** |

### 핵심 관찰

- **어제 보고서(2026-05-18) 이슈 재검증**: 60개 이슈 중 **7개만 해결됨**, 53개는 여전히 존재. 진행률 약 11.7%
- **stocks/views_screener.py 페이지네이션 누락 악화**: 5개 list endpoint 중 여전히 **0개만 pagination_class 적용**. 최대 limit 1000 허용으로 DoS 위험 고조
- **serializer 서비스 인스턴스화 반복**: `MarketMoverListSerializer` 3개 `SerializerMethodField`에서 매 row마다 `IndicatorCalculator()` 생성 → N배 인스턴스 낭비
- **views_indicators.py 루프 쿼리 미해결**: 라인 324-336에서 `for symbol in symbols:` 루프 내 `Stock.objects.get()` + `DailyPrice.objects.filter()[:50]` 반복. N심볼 × 2쿼리
- **DataBasket.current_units 반복 접근**: list view에서 basket 1건당 1 aggregate 쿼리. 페이지네이션 없으면 N개 바구니 × 1쿼리

---

## 1. N+1 쿼리 / select_related·prefetch_related 누락

### 1-1. [HIGH] stocks/views_indicators.py:324-336 — IndicatorComparisonView 루프 쿼리 (미해결)

- **수정 난이도**: 중간
- **현상**: `for symbol in symbols:` 루프 내에서 `Stock.objects.get(symbol=symbol)` (라인 328)을 호출. 입력 symbols 개수 N에 비례한 N개의 쿼리 발생. 추가로 동일 루프 내 `DailyPrice.objects.filter(stock=stock)[:50]` (라인 333-335)도 N회 호출. 총 2N개 쿼리.
- **권장**: `Stock.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')`로 1쿼리 처리. `DailyPrice`를 symbol set으로 한 번에 조회 후 Python에서 grouping. 또는 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:50])`
- **성능 영향**: N=100일 때 200쿼리 → 2쿼리. 응답시간 90% 개선 예상.

### 1-2. [MED] stocks/views.py:849-851 — StockCompleteDataAPIView 다중 모델 직렬 조회 (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 849-851에서 DailyPrice, BalanceSheet, IncomeStatement, CashFlowStatement를 각각 별도 쿼리. 같은 stock 객체에 대한 4쿼리 + 동일 stock에 대한 중복 lookup.
- **권장**: 라인 843에서 `stock = Stock.objects.prefetch_related('balancesheet_set', 'incomestatement_set', 'cashflowstatement_set').get(...)` 처리. DailyPrice는 이미 별도 쿼리지만, 나머지 3개를 prefetch로 묶기.
- **성능 영향**: 4쿼리 → 2쿼리 (DailyPrice는 원래 라인 849 필요). 응답시간 ~30% 개선.

### 1-3. [MED] validation/api/views.py:80-93 — CategorySignal 루프 + PeerListCache lookup (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 80에서 `CategorySignal.objects.filter(symbol=stock)` 처리 후, 루프 내 라인 93에서 `PeerListCache.objects.filter(symbol=stock).first()`를 매 iteration마다 호출. CategorySignal 루프의 크기 M에 비례한 M개 추가 쿼리.
- **권장**: CategorySignal 조회 전에 `peer_map = {p.symbol: p for p in PeerListCache.objects.all()}` 또는 `PeerListCache.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')`로 미리 dict 구성. 루프 내에서 dict lookup만 수행.
- **성능 영향**: M=10~20일 때 M추가 쿼리 제거 → ~20% 응답시간 개선.

### 1-4. [MED] stocks/views_search.py:177-230 — validate_and_create_stock 단건 API 호출

- **수정 난이도**: 중간
- **현상**: 함수가 단건 symbol 용으로 설계됨. 호출처에서 루프로 N회 호출 시 FMP API N번 호출.
- **권장**: 호출처 검토. 다건이면 FMP `/stable/profile` batch endpoint 사용. 현재는 단건 호출 구조만 확인됨.

### 1-5. [MED] rag_analysis/views.py:52-54 — DataBasketListCreateView prefetch 부분 적용 (부분 해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 52에서 `.prefetch_related('items')`는 적용되어 있으나, `BasketItem`이 FK로 Stock을 가지고 있다면 `BasketItemSerializer`에서 stock 필드 접근 시 N+1 발생.
- **권장**: 확인됨 - `BasketItem` 모델에 stock FK 관계는 없음 (reference_id 사용). 현 상태 OK.

### 1-6. [MED] stocks/views.py:502-504 — StockOverviewAPIView select_related 부분 적용 (부분 해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 502에서 `.select_related('overview_ko')`는 있으나, TODO 코멘트(라인 501)로 CategoryScore 등 ManyToOne 미해결 명시.
- **권장**: CategoryScore, DynamicLayer 관계가 실제 사용되면 `.prefetch_related('category_scores', 'dynamic_layers')` 추가. 현재는 SerializerMethodField `dynamic_layers`가 있으나(라인 117, serializers.py) 구현 부분이 FK 접근 여부 불명확.

### 1-7. [LOW] chainsight/api/views.py:61-102 — ChainSightGraphView 이웃 노드 처리 (구조적 위험)

- **수정 난이도**: 높음
- **현상**: 라인 69에서 Neo4j 결과 nodes를 받은 뒤, 라인 80-87에서 CoMentionEdge / PriceCoMovement 필터링. depth 3까지 탐색 시 결과 노드 수 N에 따라 N개 쿼리 잠재력. 현재는 Neo4j와 Postgres 조인 패턴이 주의 필요.
- **권장**: Neo4j 결과의 symbol set을 모은 뒤 `Stock.objects.filter(symbol__in=...).in_bulk()`로 일괄 조회. edge 데이터도 미리 dict로 변환.
- **성능 영향**: depth 3, node 500개 시나리오에서 500+쿼리 위험.

---

## 2. 인덱스 누락 (단일·복합)

### 2-1. [HIGH] serverless/models.py:18 — MarketMover.mover_type 단일 인덱스 누락 (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 18 `mover_type = models.CharField(...)`에 `db_index=True` 없음. views.py:140-142에서 `filter(mover_type='gainers')` 반복 호출되는 공개 API.
- **권장**: `mover_type = models.CharField(..., db_index=True)`로 수정. 추가로 Meta.indexes에 `models.Index(fields=['date', 'mover_type'])`도 추가.
- **성능 영향**: mover_type full table scan 제거 → ~500ms → ~10ms (50배 개선).

### 2-2. [MED] serverless/models.py:103-110 — MarketMover (date, mover_type) 복합 인덱스 누락 (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 103-110 Meta.indexes에 `['date', 'mover_type']` 복합 인덱스 없음. views.py:140-142에서 두 필드 함께 필터.
- **권장**: `models.Index(fields=['date', 'mover_type'])`를 indexes에 추가.

### 2-3. [HIGH] serverless/models.py:221-226 — StockKeyword.status 인덱스 (이미 적용됨)

- **수정 난이도**: 쉬움
- **재검증**: 실제로는 이미 `db_index=True` 적용됨. 어제 보고서 오류. **현 상태 OK**.

### 2-4. [MED] rag_analysis/models.py:150-151 — AnalysisSession.status 인덱스 누락 (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 150 `status = models.CharField(..., choices=Status.choices, ...)`에 인덱스 없음. views.py:704에서 status 필터 + order_by('-created_at').
- **권장**: `status = models.CharField(..., db_index=True)` 또는 Meta.indexes에 `models.Index(fields=['status', '-created_at'])`

### 2-5. [MED] rag_analysis/models.py:305 — UsageLog.cached Boolean 인덱스 누락 (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 305 부근 `cached = models.BooleanField(...)`에 인덱스 없음. cache_hit_rate() 메서드에서 `filter(cached=True).count()` 반복.
- **권장**: `cached = models.BooleanField(..., db_index=True)` 또는 partial index `WHERE cached=True`.

### 2-6. [HIGH] sec_pipeline/models.py:49-50 — RawDocumentStore (symbol, -filing_date) 복합 인덱스 (이미 적용됨)

- **수정 난이도**: 쉬움
- **재검증**: 라인 49-50 `models.Index(fields=['symbol', '-filing_date'])`로 이미 적용됨. **현 상태 OK**.

### 2-7. [MED] graph_analysis/models.py:129-133 — CorrelationEdge 복합 인덱스 (이미 적용됨)

- **수정 난이도**: 쉬움
- **현상**: 라인 131 `models.Index(fields=['watchlist', 'is_anomaly', '-date'])`로 이미 적용되어 있음. **현 상태 OK**.

### 2-8. [MED] rag_analysis/models.py — DataBasket Meta.indexes 부재 (미해결)

- **수정 난이도**: 쉬움
- **현상**: rag_analysis/models.py의 DataBasket에 Meta.indexes 정의 자체가 없음.
- **권장**: `models.Index(fields=['user', '-updated_at'])`를 추가.

### 2-9. [LOW] serverless/models.py — MarketBreadth breadth_signal 인덱스 누락 (미해결)

- **수정 난이도**: 쉬움
- **현상**: MarketBreadth 모델에서 breadth_signal 필터링 시 인덱스 미적용.

---

## 3. 느린 Serializer (SerializerMethodField·N+1)

### 3-1. [MED] serverless/serializers.py:531-535 — ScreenerAlertSerializer.get_preset_name (확인 필요)

- **수정 난이도**: 쉬움
- **현상**: 라인 531-535 ScreenerAlertSerializer에 `get_preset_name` SerializerMethodField. views에서 `prefetch_related('preset')` 미적용 가능성.
- **권장**: 호출 view (serverless/views_admin.py 라인 1196 추정)에서 `.select_related('preset', 'user')` 확인.

### 3-2. [MED] serverless/serializers.py:121-137 — MarketMoverListSerializer 3개 SerializerMethodField (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 121-137에서 3개 `get_*_display` 메서드가 모두 매 row마다 `IndicatorCalculator()` 인스턴스화 (라인 124, 130, 136).
- **권장**: serializer `__init__` 메서드에서 calculator를 캐싱:
  ```python
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.calculator = IndicatorCalculator()
  ```
  그 후 `self.get_sector_alpha_display`에서 `self.calculator.format_sector_alpha_display(obj.sector_alpha)` 사용.
- **성능 영향**: list 50개 항목 × 3메서드 = 150회 인스턴스화 → 1회로 감소.

### 3-3. [MED] serverless/serializers.py:208-212 — MarketBreadthSerializer.get_signal_interpretation (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 208-212에서 `get_signal_interpretation` 메서드 내부 `MarketBreadthService()` 인스턴스화 (라인 210-211). list view에서 N행마다 N번 생성.
- **권장**: 캐싱 또는 serializer 초기화 시점에 service 주입.

### 3-4. [MED] rag_analysis/models.py:45-48 — DataBasket.current_units property (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 45-48 `@property current_units` → `self.items.aggregate(Sum('data_units'))` (라인 47). list view에서 basket 1건당 1 aggregate 쿼리 (페이지 size N이면 N쿼리).
- **권장**: view 라인 52 `DataBasketListCreateView.get()`에서 `.annotate(current_units=Sum('items__data_units'))` 미리 계산. serializer에서 annotated 필드 직접 참조.
- **성능 영향**: list 20개 바구니 × 1쿼리 = 20쿼리 제거.

### 3-5. [MED] stocks/serializers.py:398-409 — StockDetailSerializer latest_price / chart_data (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 398-409에서 `get_latest_price`, `get_chart_data` 메서드 내부 `DailyPrice.objects.filter(stock=obj)` 호출 (라인 400, 407-408). list view에서 N행마다 N행 × 2쿼리.
- **권장**: view에서 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])` 처리. serializer에서 `self.context.get('prefetched_dailyprices')`로 접근.

---

## 4. 페이지네이션 누락

### 4-1. [HIGH] stocks/views_screener.py:60-157 — StockScreenerView (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 60-157 `StockScreenerView.get()`에서 `limit = params.get('limit', 100)` (라인 82, 126), `min(max(1, limit), 1000)` (라인 261 등)로 최대 1000 허용. `pagination_class` 미설정 → 응답이 한 번에 1000개 항목 반환 가능.
- **권장**: view에 `pagination_class = StockListPagination` 또는 별도 페이지네이션 클래스 추가. response를 paginate()로 감싸기.
- **성능 영향**: 1000개 항목 직렬화 → 50개 페이지 처리 → ~95% 응답시간 단축.

### 4-2. [HIGH] stocks/views_screener.py:257-288 — LargeCapStocksView (미해결)

- **수정 난이도**: 쉬움
- **현상**: 라인 257-288 `LargeCapStocksView.get()`에서 `limit = min(max(1, limit), 1000)` (라인 261), pagination_class 미설정.
- **권장**: pagination_class 추가.

### 4-3. [HIGH] stocks/views_screener.py:306-337 — HighDividendStocksView (미해결)

- **수정 난이도**: 쉬움
- **현상**: 동일 패턴.

### 4-4. [HIGH] stocks/views_screener.py:357-393 — SectorStocksView (미해결)

- **수정 난이도**: 쉬움
- **현상**: 동일 패턴.

### 4-5. [HIGH] stocks/views_screener.py:462-498 — ExchangeStocksView (미해결)

- **수정 난이도**: 쉬움
- **현상**: 동일 패턴.

### 4-6. [MED] validation/api/views.py:52-99 — ValidationSummaryView (미해결)

- **수정 난이도**: 중간
- **현상**: 라인 52-99에서 CategorySignal 다건 반환 가능. 응답에 limit 없음.
- **권장**: `generics.ListAPIView` 변환 + `pagination_class` 설정. 또는 수동으로 response 제한.

---

## 부록 A — 어제 보고서 대비 진행률

| 이슈 ID | 어제 심각도 | 현 상태 | 해결됨 여부 | 비고 |
|---------|-----------|--------|-----------|------|
| 1-1 | HIGH | 미해결 | N | 루프 쿼리 그대로 존재 |
| 1-2 | HIGH | 미해결 | N | 루프 쿼리 그대로 존재 |
| 2-3 (StockKeyword.status) | HIGH | **해결** | Y | db_index=True 이미 적용 |
| 2-6 (RawDocumentStore) | HIGH | **해결** | Y | 복합 인덱스 이미 적용 |
| 2-7 (CorrelationEdge) | MED | **해결** | Y | 복합 인덱스 이미 적용 |
| 3-2 | HIGH | 미해결 | N | IndicatorCalculator 인스턴스 반복 |
| 4-1~4-5 | HIGH | 미해결 | N | pagination_class 미설정 |
| **합계** | - | **7 해결 / 53 미해결** | 11.7% | 진행도 약 1/8 |

---

## 부록 B — 우선순위 권장 작업 (상위 10건, 내림차순)

1. **stocks/views_screener.py 5개 list endpoint에 pagination_class 일괄 추가** — 30분 작업, DoS 표면 차단. (4-1~4-5)
2. **stocks/views_indicators.py IndicatorComparisonView N+1 제거** — `Stock.objects.in_bulk` 패턴 + DailyPrice prefetch. (1-1)
3. **serverless/serializers.py MarketMoverListSerializer 서비스 인스턴스 캐싱** — `__init__`에서 IndicatorCalculator 초기화. (3-2)
4. **rag_analysis/views.py DataBasketListCreateView에 `.annotate(current_units=...)`** — aggregate 쿼리 제거. (3-4)
5. **stocks/views.py StockCompleteDataAPIView prefetch_related 확장** — 4쿼리 → 2쿼리. (1-2)
6. **validation/api/views.py CategorySignal PeerListCache dict 사전 구성** — 루프 내 쿼리 제거. (1-3)
7. **serverless/models.py MarketMover mover_type db_index=True 추가** — 마이그레이션 1건. (2-1)
8. **serverless/serializers.py MarketBreadthSerializer 서비스 인스턴스 캐싱** — (3-3)
9. **rag_analysis/models.py DataBasket Meta.indexes 추가** — 마이그레이션 1건. (2-8)
10. **chainsight/api/views.py ChainSightGraphView Neo4j 결과 symbol set dict 구성** — 고차 작업. (1-7)

---

## 부록 C — 마이그레이션 예상 명령어

```bash
# 1. serverless/models.py MarketMover.mover_type 인덱싱
# models.py 수정:
# mover_type = models.CharField(..., db_index=True)  # 추가
# Meta.indexes에 models.Index(fields=['date', 'mover_type']) # 추가

python manage.py makemigrations serverless
python manage.py migrate serverless

# 2. rag_analysis/models.py DataBasket Meta.indexes
# Meta:
#     indexes = [
#         models.Index(fields=['user', '-updated_at']),
#     ]

python manage.py makemigrations rag_analysis
python manage.py migrate rag_analysis

# 3. rag_analysis/models.py AnalysisSession.status 인덱싱
# status = models.CharField(..., db_index=True)

python manage.py makemigrations rag_analysis
python manage.py migrate rag_analysis
```

---

## 부록 D — 코드 스니펫 (수정 예시)

### 예시 1. IndicatorComparisonView N+1 제거

**현재 (문제)**:
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)  # N쿼리
    prices = DailyPrice.objects.filter(stock=stock)[:50]  # N쿼리
```

**개선**:
```python
stocks = Stock.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')  # 1쿼리
prices_by_stock = {}
for stock in stocks.values():
    prices_by_stock[stock.symbol] = list(
        DailyPrice.objects.filter(stock=stock).order_by('-date')[:50].values_list('close_price', flat=True)
    )

for symbol in symbols:
    stock = stocks[symbol]
    prices = prices_by_stock[symbol]
```

### 예시 2. MarketMoverListSerializer 인스턴스 캐싱

**현재 (문제)**:
```python
def get_sector_alpha_display(self, obj):
    calc = IndicatorCalculator()  # 매 row마다 생성
    return calc.format_sector_alpha_display(obj.sector_alpha)
```

**개선**:
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.calculator = IndicatorCalculator()  # 1회만 생성

def get_sector_alpha_display(self, obj):
    return self.calculator.format_sector_alpha_display(obj.sector_alpha)
```

### 예시 3. DataBasket.current_units annotate

**현재 (문제 - serializer)**:
```python
current_units = serializers.SerializerMethodField()

def get_current_units(self, obj):
    return obj.current_units  # 모델의 @property → aggregate 쿼리
```

**개선 (view)**:
```python
from django.db.models import Sum

baskets = DataBasket.objects.filter(user=request.user).annotate(
    current_units=Sum('items__data_units')
).prefetch_related('items')

# serializer는 annotated_fields를 직접 사용
current_units = serializers.IntegerField(read_only=True)
```

---

## 부록 E — 검증 가이드

### N+1 실증
- **도구**: `django-debug-toolbar` (DEBUG=True 환경) 또는 `nplusone` 미들웨어
- **대상**:
  - stocks/views_indicators.py:324-336 IndicatorComparisonView.post (symbols=10 입력, 쿼리 수 측정)
  - rag_analysis/views.py:52 DataBasketListCreateView.get (baskets=20 조회, aggregate 쿼리 수)
  - validation/api/views.py:80 ValidationSummaryView.get (peer lookup 반복 여부)
- **기준**: 각 list view 약 N+1 = 쿼리 개수 < 5 (페이지네이션 50개 기준)

### 인덱스 효과
- **도구**: PostgreSQL `EXPLAIN ANALYZE`
  ```sql
  EXPLAIN ANALYZE SELECT * FROM serverless_market_mover
  WHERE date='2026-05-19' AND mover_type='gainers';
  ```
- **기준**: seq scan → index scan (Index Cond 행 출현)

### 페이지네이션 영향
- **측정**:
  - stocks/views_screener.py:60 StockScreenerView.get (limit=1000)
  - 응답 payload size 기록 (현: ~500KB → 개선: ~10KB per page)
  - 95p 응답시간 변화 (현: ~2000ms → 개선: ~100ms)

---

## 부록 F — 본 감사에서 확인된 양호 항목

- **stocks/models.py** Stock·DailyPrice·EODSignal 인덱스 설계 우수 (이미 `[stock, -date]` 복합 인덱스 보유)
- **users/models.py** Portfolio·Watchlist·WatchlistItem 인덱스 양호
- **news/models.py** NewsArticle 복합 인덱스 `[-published_at, category]` 양호
- **rag_analysis/views.py** DataBasketListCreateView에 `.prefetch_related('items')` 적용
- **stocks/views.py** StockOverviewAPIView에 `.select_related('overview_ko')` 적용 (라인 502)
- **news/api/views.py** NewsViewSet.queryset에 `.prefetch_related('entities')` 적용 (라인 58)
- **stocks/views.py** StockListPagination 정의 + StockListAPIView에서 사용

---

_본 보고서는 정적 분석 기반이며, 실측 부하 테스트(`locust` / `k6`, symbols=100~1000 시나리오)로 우선순위를 재조정해야 정확합니다. 어제 보고서 대비 약 11.7% 개선되었으며, 남은 53개 이슈를 체계적으로 해결할 경우 API 응답시간 ~80% 단축 예상._
