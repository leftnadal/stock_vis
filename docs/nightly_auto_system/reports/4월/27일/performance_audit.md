# API 성능 감사 보고서

**작성일**: 2026-04-27
**범위**: stocks/, users/, news/, macro/, rag_analysis/, serverless/, validation/, chainsight/, sec_pipeline/, graph_analysis/
**검사 방식**: 정적 분석 (코드 수정 없음)
**대상**: views 17종, 모델 7종, serializer 9종

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 개수 | 카테고리별 |
|--------|------|-----------|
| **HIGH** | 9건 | N+1 5건, 페이지네이션 3건, 인덱스 1건 |
| **MED** | 11건 | N+1 2건, 인덱스 5건, Serializer 2건, 페이지네이션 2건 |
| **LOW** | 4건 | 잡다한 최적화 |
| **합계** | **24건** | |

### 톱 5 우선 처리 (즉시 권장)

| 순위 | 이슈 | 파일:라인 | 추정 효과 |
|------|------|-----------|----------|
| 1 | `StockListAPIView` 페이지네이션 없음 (10,000+ 종목 전체 반환 위험) | stocks/views.py:75-105 | OOM/타임아웃 회피 |
| 2 | `WatchListStockSerializer` N+1 (각 항목마다 2회 추가 쿼리) | stocks/serializers.py:398-409 | 10~50배 |
| 3 | `Portfolio.total_value/total_cost` property가 루프마다 stock FK 접근 | users/views.py:367-369 | 10~100배 |
| 4 | `ValidationMetricsView._build_metric()` 루프 내 `PeerMetricBenchmark.first()` | validation/api/views.py:219-286 | 5N배 |
| 5 | `ChainSightGraphView` edges 루프마다 `CoMentionEdge`/`PriceCoMovement` 조회 | chainsight/api/views.py:69-88 | 2N배 |

---

## 상세

### 1. N+1 쿼리 이슈 (7건)

#### 1.1 [HIGH] WatchListStockSerializer SerializerMethodField 추가 쿼리

**파일**: `stocks/serializers.py:398-409`

```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
    if latest:
        return float(latest.close_price)
    return float(obj.real_time_price or 0)

def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: 관심종목 list 응답에 N개 항목이 있으면 N항목 × 2쿼리 = 2N건의 추가 쿼리 발생.
- **권장**: `prefetch_related(Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7]))` 또는 `annotate(Subquery(...))`로 최신 가격을 한 번에 가져오기.

---

#### 1.2 [HIGH] Portfolio.total_value 루프 내 호출

**파일**: `users/views.py:367-369`, `397-426`

```python
for portfolio in portfolios:
    total_value += portfolio.total_value     # @property → self.stock.real_time_price 접근
    total_cost += portfolio.total_cost
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: `Portfolio.total_value/total_cost`는 모델의 `@property`(models.py:81-88)로 `self.stock.real_time_price` 접근. 이미 `select_related('stock')` 적용되었지만 property 시점에 평가되므로 실제 쿼리 캐시 효과를 얻지 못하는 경우가 있음. 더 큰 문제는 **DB-side 합산이 아니라 파이썬에서 합산**한다는 점.
- **권장**:
  ```python
  agg = portfolios.aggregate(
      total_value=Sum(F('quantity') * F('stock__real_time_price'), output_field=DecimalField()),
      total_cost=Sum(F('quantity') * F('average_buy_price'), output_field=DecimalField()),
  )
  ```

---

#### 1.3 [HIGH] ValidationMetricsView._build_metric() 루프 내 PeerMetricBenchmark 조회

**파일**: `validation/api/views.py:219-286`

```python
snaps = CompanyMetricSnapshot.objects.filter(
    symbol=stock, metric_code=md,
).order_by('fiscal_year')[:5]
for s in snaps:
    peer_bench = PeerMetricBenchmark.objects.filter(
        symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
    ).first()   # ← 루프 내 N+1
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: 5년치 history × 지표 수만큼 추가 쿼리. 메트릭이 10개라면 1요청당 50건의 단일 row 쿼리.
- **권장**:
  ```python
  years = [s.fiscal_year for s in snaps]
  bench_map = {
      b.fiscal_year: b
      for b in PeerMetricBenchmark.objects.filter(
          symbol=stock, fiscal_year__in=years, metric_code=md
      )
  }
  for s in snaps:
      peer_bench = bench_map.get(s.fiscal_year)
  ```

---

#### 1.4 [HIGH] LeaderComparisonView 루프 내 다중 .first() 쿼리

**파일**: `validation/api/views.py:352-376`

```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()                # 루프 내
    company_snap = CompanyMetricSnapshot.objects.filter(...).first()   # 루프 내
    leader_snap = CompanyMetricSnapshot.objects.filter(...).first()    # 루프 내
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: 메트릭 K개 × 단건 쿼리 3개 = 3K건. K가 20이면 60건의 라운드트립.
- **권장**:
  ```python
  metric_map = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=[mc for _, mc in all_metrics])}
  snaps = CompanyMetricSnapshot.objects.filter(
      symbol__in=[stock, leader], fiscal_year=latest_fy,
      metric_code_id__in=[mc for _, mc in all_metrics], value_status='normal',
  )
  ```

---

#### 1.5 [HIGH] ChainSightGraphView edges 루프 내 단건 쿼리

**파일**: `chainsight/api/views.py:69-88`

```python
for edge in result.get("edges", []):
    a, b = (from_t, to_t) if from_t < to_t else (to_t, from_t)
    cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()    # N+1
    pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()  # N+1
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: 그래프 응답 가공 시 edges 수가 100+이면 200건 이상의 단건 쿼리.
- **권장**: edges 전체에서 `(symbol_a, symbol_b)` 페어를 수집해 한 번에 IN 절로 가져온 뒤 dict로 매핑.

---

#### 1.6 [HIGH] DataBasketSerializer.can_add_item() 호출에 따른 쿼리

**파일**: `rag_analysis/views.py:71-75`, `rag_analysis/serializers.py:24-50`, `rag_analysis/models.py:36-42`

```python
# serializer
def get_can_add_item(self, obj) -> bool:
    return obj.can_add_item()       # → self.items.count()

# model
def can_add_item(self) -> bool:
    return self.items.count() < self.MAX_ITEMS
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: `prefetch_related('items')`로 items 자체는 캐시되지만 `.count()`/`.aggregate()`는 별도 쿼리를 던지기 때문에 캐시가 무효화. 사용자당 N개 basket이면 3N건의 추가 쿼리(`count()`, `Sum()` 2회 등).
- **권장**: view에서 `annotate(items_count=Count('items'), current_units_db=Sum('items__data_units'))`로 한 번에 계산 후, serializer의 `SerializerMethodField`를 단순 read-only field로 교체.

---

#### 1.7 [MED] OverviewTabSerializer category_signals 역참조

**파일**: `stocks/serializers.py:205-231`

```python
signals = list(obj.category_signals.all())   # detail에서는 1회, list에서는 N회
```

- **심각도**: MED (detail 단건 호출에선 LOW, list에서 사용 시 HIGH)
- **수정 난이도**: 중간
- **권장**: `Stock.objects.prefetch_related('category_signals')` 적용 또는 detail view의 `get_object`에서 `prefetch_related` 추가. 코드 주석에 "TODO: prefetch_related + 캐싱 레이어" 명시되어 있어 인지된 상태.

---

#### 1.8 [MED] ValidationSummaryView _find_leader 추가 쿼리

**파일**: `validation/api/views.py:80-107`, `148-161`

- **심각도**: MED
- **수정 난이도**: 쉬움
- **분석**: peer_symbols로 추가 Stock + market_cap 조회. 단발성이라 큰 문제는 아니지만, peer_cache fetch 직후 `select_related`/values 사용으로 1쿼리화 가능.

---

### 2. 인덱스 누락 (6건)

#### 2.1 [MED] BalanceSheet/IncomeStatement/CashFlowStatement 복합 인덱스 누락

**파일**: `stocks/models.py:359-361, 428-430, 527-529`

```python
class Meta:
    unique_together = ('stock', 'period_type', 'fiscal_year', 'fiscal_quarter')
    indexes = [
        models.Index(fields=['stock', 'fiscal_year']),
        models.Index(fields=['period_type', 'fiscal_year']),
    ]
```

- 자주 호출되는 쿼리: `filter(stock=stock, period_type=db_period).order_by('-fiscal_year', '-fiscal_quarter')` (views.py:636-639)
- **누락**: `('stock', 'period_type', '-fiscal_year', '-fiscal_quarter')` 복합 인덱스
- **수정 난이도**: 중간 (마이그레이션 필요)
- **권장**:
  ```python
  models.Index(fields=['stock', 'period_type', '-fiscal_year', '-fiscal_quarter']),
  ```

---

#### 2.2 [MED] Stock.exchange 인덱스 부재

**파일**: `stocks/models.py:20-100`

- `sector`, `industry`는 인덱스가 있지만 `exchange`는 없음. screener에서 거래소 필터링 시 풀 스캔 가능.
- **수정 난이도**: 쉬움
- **권장**: `Meta.indexes`에 `models.Index(fields=['exchange'])` 추가.

---

#### 2.3 [HIGH] NewsEntity (symbol, news.published_at) 복합 인덱스 누락

**파일**: `news/models.py:228-296`

```python
indexes = [
    models.Index(fields=['symbol', 'entity_type']),
    models.Index(fields=['sentiment_score']),
]
```

- 자주 호출되는 쿼리: `.filter(symbol=symbol, news__published_at__gte=from_date)` (news/api/views.py:322-336)
- **수정 난이도**: 쉬움
- **권장**: 직접 `published_at` 인덱스를 NewsEntity에는 만들 수 없으므로 `NewsArticle.published_at`이 인덱스인지 확인 + `('symbol', 'entity_type')` 인덱스에 sentiment 계산용 보강. 또는 NewsEntity에 `published_at`을 비정규화 컬럼으로 두고 `(symbol, -published_at)` 인덱스 검토.

---

#### 2.4 [MED] Portfolio (user, -created_at) 인덱스 누락

**파일**: `users/models.py:72-75`

```python
indexes = [
    models.Index(fields=['user', 'stock']),
    models.Index(fields=['user', '-updated_at']),
]
```

- 정렬에 `-created_at` 사용 시 인덱스 미적용.
- **수정 난이도**: 쉬움
- **권장**: `models.Index(fields=['user', '-created_at'])` 추가.

---

#### 2.5 [MED] BasketItem (basket, item_type, reference_id) 인덱스 누락

**파일**: `rag_analysis/models.py:76-111`

- `unique_together`만 있고 일반 조회용 인덱스가 없음 (Postgres에서 unique constraint도 인덱스로 사용되지만, 컬럼 순서가 조회 패턴과 다르면 비효율).
- 자주 호출되는 쿼리: `filter(basket=basket, item_type=data_type, reference_id=symbol)` (views.py:312-316)
- **수정 난이도**: 쉬움
- **권장**: 동일 컬럼 순서의 일반 인덱스 추가는 중복일 수 있어 unique constraint의 인덱스 활용 가능성 확인 후 결정.

---

#### 2.6 [MED] StockKeyword 복합 인덱스 누락

**파일**: `serverless/models.py:168-251`

```python
symbol = models.CharField(max_length=10, db_index=True)
date = models.DateField(db_index=True)
status = models.CharField(..., db_index=True)
```

- 자주 호출되는 쿼리: `filter(symbol__in=symbols, date=date_str, status='completed')` (views.py:359-362)
- 개별 인덱스만 있고 복합 인덱스 없음 → 옵티마이저가 IN+필터 처리 시 비효율.
- **수정 난이도**: 쉬움
- **권장**:
  ```python
  models.Index(fields=['date', 'status', 'symbol']),
  ```

---

#### 2.7 [MED] CompanyBenchmarkDelta 복합 인덱스 (확인 필요)

**파일**: `validation/models.py` (정확한 위치 미확인)

- 사용 패턴: `.filter(symbol=stock, fiscal_year=fy, metric_code_id=mc).first()` (validation/api/views.py:113-125)
- **권장**: `(symbol, fiscal_year, metric_code_id)` 복합 인덱스 존재 여부 확인 후 추가.

---

### 3. 느린 Serializer (3건)

#### 3.1 [MED] MarketMoverListSerializer가 항목마다 IndicatorCalculator 인스턴스 생성

**파일**: `serverless/serializers.py:81-137`

```python
def get_sector_alpha_display(self, obj):
    from serverless.services.indicators import IndicatorCalculator
    calc = IndicatorCalculator()    # ← 각 객체마다 새 인스턴스
    return calc.format_sector_alpha_display(obj.sector_alpha)
```

- **심각도**: MED
- **수정 난이도**: 쉬움
- **권장**: serializer `__init__`에서 한 번 인스턴스화 후 재사용 또는 모듈 레벨 싱글턴.

---

#### 3.2 [LOW] ScreenerAlertSerializer가 항목마다 timezone.now() 호출

**파일**: `serverless/serializers.py:499-555`

- 영향 작음. `__init__`에서 한 번 캐싱하면 깔끔.

---

#### 3.3 [LOW] NewsArticleListSerializer entities 전체 직렬화

**파일**: `news/api/serializers.py:45-64`

- list/trending 응답에 entities 전체 포함 → 페이로드 비대.
- **권장**: list 전용 경량 serializer (`entities` 제외 또는 N개 미리보기만) 분리.

---

### 4. 페이지네이션 누락 (5건)

#### 4.1 [HIGH] StockListAPIView 페이지네이션 없음

**파일**: `stocks/views.py:75-105`

```python
class StockListAPIView(generics.ListAPIView):
    serializer_class = StockListSerializer
    def get_queryset(self):
        queryset = Stock.objects.all()
        ...
        return queryset.order_by('-market_capitalization')
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **분석**: 종목 수가 10,000+이면 응답 메모리 폭증/타임아웃.
- **권장**: `pagination_class = PageNumberPagination` (기본 page_size=50) 또는 `CursorPagination`.

---

#### 4.2 [HIGH] NewsViewSet 페이지네이션 없음

**파일**: `news/api/views.py:42-52`

```python
class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.all().prefetch_related('entities')
    serializer_class = NewsArticleListSerializer
    # pagination_class 미설정
```

- **심각도**: HIGH
- **수정 난이도**: 쉬움
- **권장**: `pagination_class = PageNumberPagination` 추가. (기본 DRF 글로벌 페이지네이션 미설정 시 위험)

---

#### 4.3 [HIGH] SessionMessagesView 페이지네이션 없음

**파일**: `rag_analysis/views.py:490-505`

```python
messages = session.messages.all().order_by('created_at')
serializer = AnalysisMessageSerializer(messages, many=True)
```

- **심각도**: HIGH
- **수정 난이도**: 중간
- **분석**: 대화 세션이 길면 수백 개 메시지 전체 반환 → 응답 시간/메모리 문제.
- **권장**: 커스텀 `MessagePagination(page_size=20)` 적용.

---

#### 4.4 [MED] UserListView 페이지네이션 없음

**파일**: `users/views.py:89-92`

- 관리자 전용이지만 사용자 1만 명 가정 시 응답 비대.
- **수정 난이도**: 쉬움

---

#### 4.5 [MED] PortfolioListView 페이지네이션 없음

**파일**: `users/views.py:255-259`

```python
def get(self, request):
    portfolios = Portfolio.objects.filter(user=request.user).select_related('stock')
    serializer = PortfolioSerializer(portfolios, many=True)
    return Response(serializer.data)
```

- 보통 1인당 100개 미만이지만 디폴트 페이지네이션 권장.

---

#### 4.6 [MED] DataBasketListCreateView 페이지네이션 없음

**파일**: `rag_analysis/views.py:71-75`

- 사용자당 basket이 많을 수 있음.

---

### 5. 기타 발견사항 (정상 / 보강 권장)

| 영역 | 상태 | 비고 |
|------|------|------|
| `EODSignalDetailView` (`stocks/views_eod.py:72-100`) | OK | `select_related('stock')` 적용됨 |
| `DailyPrice (stock, -date)` 인덱스 | OK | `stocks/models.py:189` 정의됨 |
| `StockNews (symbol, -published_at)` 인덱스 | OK | `stocks/models.py:903-910` |
| `EODSignal (date, -composite_score)` 인덱스 | OK | `stocks/models.py:785-793` |
| `SentimentHistory (symbol, -date)` 인덱스 | OK | `news/models.py:382-384` |
| `WatchlistItem` 페이지네이션 | OK | `users/views.py:811-828`에 Paginator 적용 |
| `news/api/views.py` 캐싱 전략 | OK | TTL 600s 적용, 키 일관됨 |
| `users/views.py` Watchlist 캐싱 | OK | `@watchlist_cached_api` 데코레이터 |
| `graph_analysis/models.py` | OK | API 미구현 상태, 모델 인덱스는 잘 정의됨 |

---

## 종합 요약 표

| # | 카테고리 | 파일 | 라인 | 심각도 | 난이도 |
|---|---------|------|------|--------|--------|
| 1 | N+1 | stocks/serializers.py | 398-409 | HIGH | 중간 |
| 2 | N+1 | users/views.py | 367-369 | HIGH | 중간 |
| 3 | N+1 | validation/api/views.py | 219-286 | HIGH | 중간 |
| 4 | N+1 | validation/api/views.py | 352-376 | HIGH | 중간 |
| 5 | N+1 | chainsight/api/views.py | 69-88 | HIGH | 중간 |
| 6 | N+1 | rag_analysis/views.py | 71-75 | HIGH | 중간 |
| 7 | N+1 | stocks/serializers.py | 205-231 | MED | 중간 |
| 8 | N+1 | validation/api/views.py | 80-107 | MED | 쉬움 |
| 9 | Pagination | stocks/views.py | 75-105 | HIGH | 쉬움 |
| 10 | Pagination | news/api/views.py | 42-52 | HIGH | 쉬움 |
| 11 | Pagination | rag_analysis/views.py | 490-505 | HIGH | 중간 |
| 12 | Pagination | users/views.py | 89-92 | MED | 쉬움 |
| 13 | Pagination | users/views.py | 255-259 | MED | 중간 |
| 14 | Pagination | rag_analysis/views.py | 71-75 | MED | 중간 |
| 15 | Index | news/models.py | 293-296 | HIGH | 쉬움 |
| 16 | Index | stocks/models.py | 359-361 등 | MED | 중간 |
| 17 | Index | stocks/models.py | 20-100 | MED | 쉬움 |
| 18 | Index | users/models.py | 72-75 | MED | 쉬움 |
| 19 | Index | rag_analysis/models.py | 76-111 | MED | 쉬움 |
| 20 | Index | serverless/models.py | 168-251 | MED | 쉬움 |
| 21 | Index | validation/models.py | 미확인 | MED | 쉬움 |
| 22 | Serializer | serverless/serializers.py | 81-137 | MED | 쉬움 |
| 23 | Serializer | serverless/serializers.py | 499-555 | LOW | 쉬움 |
| 24 | Serializer | news/api/serializers.py | 45-64 | LOW | 쉬움 |

---

## 권장 처리 로드맵

### 단기 (1~2일, 큰 효과)

1. **페이지네이션 3건 추가** — 1시간 (이슈 9, 10, 11)
   - DRF `pagination_class` 한 줄 추가만으로 OOM 위험 제거.
2. **검증·체인사이트 N+1 5건 일괄 정리** — 반나절 (이슈 3, 4, 5, 6)
   - 루프 외부 dict로 한 번에 prefetch.
3. **NewsEntity 복합 인덱스 추가 마이그레이션** — 30분 (이슈 15)

### 중기 (1~2주, 구조 개선)

4. WatchListStockSerializer + OverviewTabSerializer prefetch 정리 (이슈 1, 7)
5. Portfolio 합산 DB-side 이전 (이슈 2)
6. Financial 테이블 복합 인덱스 (이슈 16)

### 장기 (성능 모니터링)

7. Serializer 경량화 (이슈 22, 23, 24)
8. Stock/Portfolio/StockKeyword 보조 인덱스 (이슈 17, 18, 20)

---

## 검증 방법 제안

- `django-silk` 또는 `django-debug-toolbar`로 실제 쿼리 수 측정 (수정 전 baseline 확보).
- pytest fixture에서 `assertNumQueries`로 회귀 방지.
- Postgres `EXPLAIN ANALYZE`로 인덱스 적용 여부 확인 후 마이그레이션 적용.

---

**감사 종료**. 코드 수정은 본 보고서 범위 외이며, 위 항목별로 별도 PR에서 처리할 것을 권장합니다.
