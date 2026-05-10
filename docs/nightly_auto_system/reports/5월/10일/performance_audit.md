# API 성능 감사 보고서

- **감사 일자**: 2026-05-10
- **대상 프로젝트**: Stock-Vis (Django REST Framework + PostgreSQL)
- **검사 범위**: 17개 view 파일 + 7개 모델 파일 + 13개 serializer 파일
- **방식**: 정적 코드 분석 (read-only, 코드 수정 없음)

---

## 요약

### 심각도별 이슈 수

| 심각도 | N+1 / select_related | 페이지네이션 | 인덱스 | Serializer 쿼리 | 합계 |
|--------|---------------------:|-------------:|-------:|----------------:|-----:|
| HIGH   | 3 | 1 | 1 | 2 | **7** |
| MED    | 2 | 0 | 2 | 4 | **8** |
| LOW    | 1 | 1 | 1 | 0 | **3** |
| **합계** | **6** | **2** | **4** | **6** | **18** |

### 핵심 결론

1. **DRF 기본 페이지네이션 미설정** — `config/settings.py:348-362` REST_FRAMEWORK에 `DEFAULT_PAGINATION_CLASS` 키 자체가 없음. `ListAPIView`도 페이지네이션 없이 전체 데이터 반환.
2. **OverviewTabSerializer.get_dynamic_layers** — Detail 호출 시 객체 1개당 6회 쿼리 (OneToOne 5 + reverse FK 1).
3. **WatchListStockSerializer** — 관심종목 N개에 대해 2N회 추가 쿼리 + `get_chart_data` 메서드는 `return` 문 누락 버그(stocks/serializers.py:405-409).
4. **stocks/views_indicators.py:324** — 루프 안에서 `Stock.objects.get(symbol=...)` 호출 → N+1 명백.
5. **NewsArticle stock_news** — `entities__symbol` 조인 + `.distinct()`인데 `prefetch_related` 없음.
6. **인덱스는 전반적으로 양호** — EODSignal, NewsArticle 복합 인덱스, UsageLog 4종 복합 인덱스, MarketMover 등 잘 설계됨. 누락은 1~2건의 LOW 수준.

---

## 1. N+1 / select_related 누락

### [HIGH-1] `stocks/views_indicators.py:324-335` — 루프 내 `Stock.objects.get()`

```python
for symbol in symbols:
    symbol = symbol.upper()
    try:
        stock = Stock.objects.get(symbol=symbol)   # ← 매 반복마다 1회 쿼리
    except Stock.DoesNotExist:
        continue
    prices = DailyPrice.objects.filter(            # ← 매 반복마다 1회 쿼리
        stock=stock
    ).order_by('-date')[:50].values_list('close_price', flat=True)
```

- **패턴**: 명백한 N+1. `symbols` 길이가 N이면 Stock 조회 N회 + DailyPrice 조회 N회 = **2N 쿼리**.
- **심각도**: HIGH (지표 비교 화면이 다종목 일괄 조회의 핵심 진입점).
- **수정 난이도**: 쉬움.
- **권장**: `Stock.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')` 으로 1회 조회 후 dict 매칭. DailyPrice는 `prefetch_related(Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:50]))` 또는 group-by 조회.

---

### [HIGH-2] `news/api/views.py:95-100` — `entities__symbol` 필터 + distinct, prefetch 없음

```python
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).distinct().order_by('-published_at')

serializer = self.get_serializer(articles, many=True)
```

- **패턴**: `NewsArticleListSerializer`(news/api/serializers.py:45-64)가 nested `entities = NewsEntitySimpleSerializer(many=True)`를 가진 것으로 분석됨. distinct 후 직렬화 시점에 entities를 다시 조회 → 기사 N개 × entities lookup = N+1.
- **참고**: 같은 파일 `news/api/views.py:401-403`의 `news_all`은 `prefetch_related('entities')`를 정상 적용 (긍정 사례).
- **심각도**: HIGH (단일 종목 뉴스 페이지의 메인 endpoint).
- **수정 난이도**: 쉬움.
- **권장**: `.prefetch_related('entities')` 추가.

---

### [HIGH-3] `stocks/serializers.py:205-307` (OverviewTabSerializer.get_dynamic_layers) — view에서 select_related 누락

`stocks/views.py:481-508`의 OverviewTabAPIView에서 호출되는 시리얼라이저인데, `select_related`가 6개 관계 중 일부만 적용되어 있음.

```python
# stocks/serializers.py:205-307 동적 레이어 생성 시 OneToOne 5회 + reverse FK 1회
signals = list(obj.category_signals.all())                  # reverse FK
ns = obj.validation_news_summary                            # OneToOne
sp = obj.sensitivity_profile                                # OneToOne
gs = obj.growth_stage                                       # OneToOne
cd = obj.capital_dna                                        # OneToOne
nt = obj.narrative_tag                                      # OneToOne
```

- **패턴**: Detail endpoint이지만 객체당 6회 쿼리. try/except 6중첩으로 RelatedObjectDoesNotExist 캐치 중인데, 이 자체도 쿼리를 발생시킴.
- **심각도**: HIGH (개별 종목 메인 화면).
- **수정 난이도**: 쉬움.
- **권장**:
  ```python
  Stock.objects.select_related(
      'overview_ko',
      'validation_news_summary',
      'sensitivity_profile',
      'growth_stage',
      'capital_dna',
      'narrative_tag',
  ).prefetch_related('category_signals')
  ```
- **참고**: 시리얼라이저 코드에 이미 `# TODO: prefetch_related + 캐싱 적용 필요` 주석이 있음(stocks/serializers.py:208).

---

### [MED-1] `validation/api/views.py:112-124` — 루프 내 `CompanyBenchmarkDelta` + `MetricDefinition` 조회

```python
rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
for mc in rank_metrics:
    delta = CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
    ).first()                                                          # ← 5회 쿼리
    if delta and delta.rank and delta.total:
        md = MetricDefinition.objects.filter(pk=mc).first()             # ← 추가 5회 쿼리
```

- **패턴**: 5개 metric × 2회 조회 = **10 쿼리**.
- **심각도**: MED (1차 검증 진입점, 종목 1개당 호출).
- **수정 난이도**: 중간.
- **권장**:
  ```python
  deltas = {d.metric_code_id: d for d in CompanyBenchmarkDelta.objects.filter(
      symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics,
  ).select_related('metric_code')}
  ```
  → 1회 조회 + select_related로 MetricDefinition 동시 로드.

---

### [MED-2] `stocks/views.py:820-874` (StockCompleteDataAPIView) — 4개 모델 분리 쿼리

```python
recent_prices    = DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]
balance_sheets   = BalanceSheet.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
income_statements= IncomeStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
cash_flows       = CashFlowStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
```

- **패턴**: N+1은 아님(stock 1개당 4회 쿼리). 단, `OverviewTabSerializer(stock)`까지 호출되어 [HIGH-3] 6회까지 더해지면 단일 detail 호출 1건이 **10회 쿼리** 발생.
- **심각도**: MED (각 쿼리가 인덱스로 빨라도 round-trip 비용 누적).
- **수정 난이도**: 쉬움 (별 작업 불필요, [HIGH-3] 해결만으로 6회 절감).
- **권장**: 우선 [HIGH-3] 처리. 4개 분리 쿼리는 그대로 두어도 무방.

---

### [LOW-1] `chainsight/api/views.py:391, 529` — bulk 조회 후 메모리 매칭

```python
stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=tickers)}
```

- **패턴**: bulk 조회 자체는 정상. 이후 loop에서 `stock.change_percent` 등 기본 필드만 접근 → 추가 쿼리 없음.
- **심각도**: LOW (실제로는 양호한 패턴).
- **수정 난이도**: 해당 없음.
- **참고**: 향후 stock의 OneToOne 필드를 추가로 사용하게 되면 select_related 검토 필요.

---

## 2. 페이지네이션 누락

### [HIGH-4] `config/settings.py:348-362` — DRF DEFAULT_PAGINATION_CLASS 미설정

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_THROTTLE_RATES': {...},
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ❌ DEFAULT_PAGINATION_CLASS / PAGE_SIZE 없음
}
```

- **패턴**: 전역 페이지네이션이 비활성. `generics.ListAPIView`가 자동 페이지네이션을 하지 않음.
- **직접 영향 endpoint**: `stocks/views.py:75 StockListAPIView` — `Stock.objects.all().order_by('-market_capitalization')`을 그대로 반환. 종목 수에 따라 응답 페이로드가 무한 증가.
- **심각도**: HIGH (전역 설정 결함, 모든 ListAPIView가 영향).
- **수정 난이도**: 쉬움.
- **권장**:
  ```python
  REST_FRAMEWORK = {
      ...
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 50,
  }
  ```
- **부수 위험**: 기존 클라이언트가 `response.results` 없이 list 자체를 기대할 가능성 → 도입 시 마이그레이션 가이드 필요.

---

### [LOW-2] `users/views.py:597-628` (WatchlistListCreateView) — 수동 페이지네이션

```python
watchlists = Watchlist.objects.filter(user=request.user).order_by('-updated_at')
paginator = Paginator(watchlists, page_size)
page_obj = paginator.page(page_number)
serializer = WatchlistSerializer(page_obj.object_list, many=True)
```

- **패턴**: Django `Paginator`로 수동 처리. 동작은 정상이나 표준 DRF 페이지네이션 미사용.
- **심각도**: LOW (현재 무한 응답 위험 없음, 단지 일관성 부족).
- **수정 난이도**: 중간 (DRF PaginatedResponse 형식으로 마이그레이션 시 클라이언트 호환 영향).
- **권장**: HIGH-4 적용 후 일관성 정리(선택사항).

---

## 3. Serializer 추가 쿼리 (SerializerMethodField)

### [HIGH-5] `stocks/serializers.py:398-409` — WatchListStockSerializer

```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
    if latest:
        return float(latest.close_price)
    return float(obj.real_time_price or 0)

def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(
        stock=obj
    ).order_by('-date')[:7]
    # ← return 문 누락! 항상 None 반환
```

- **패턴 1 (성능)**: 관심종목 N개 × 2회 쿼리 = **2N 쿼리**. List endpoint(`users/views.py:819 WatchlistStocksView`)에서 사용된다면 직접 영향.
- **패턴 2 (버그)**: `get_chart_data`에 `return` 문이 없음 → 항상 `None` 반환. 클라이언트에 차트 미니프리뷰가 안 보일 가능성.
- **심각도**: HIGH (성능 + 기능 결함 동시).
- **수정 난이도**: 쉬움.
- **권장**:
  - View에서 `prefetch_related(Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7], to_attr='recent_prices'))`.
  - serializer는 `obj.recent_prices` 메모리 접근으로 변경.
  - `get_chart_data`에 `return ChartDataSerializer(recent_prices, many=True).data` 추가.

---

### [HIGH-6] `stocks/serializers.py:205-307` — OverviewTabSerializer.get_dynamic_layers

[HIGH-3]과 동일 사례 (view 단 select_related로 해결). 객체당 6회 쿼리.

---

### [MED-3] `serverless/serializers.py:121-137` — MarketMoverListSerializer 인스턴스화 오버헤드

```python
def get_sector_alpha_display(self, obj):
    from serverless.services.indicators import IndicatorCalculator
    calc = IndicatorCalculator()                # 매 호출마다 import + 인스턴스 생성
    return calc.format_sector_alpha_display(obj.sector_alpha)
# 동일 패턴 3회 (sector_alpha, etf_sync, volatility_pct)
```

- **패턴**: DB 쿼리는 없으나 객체 N개 × 3회 객체 생성 = **3N 인스턴스화**.
- **심각도**: MED (Market Movers 메인 화면, 종목 수 100~500).
- **수정 난이도**: 쉬움.
- **권장**: 모듈 상단에서 `from serverless.services.indicators import IndicatorCalculator` 후 모듈 레벨 싱글톤(`_calculator = IndicatorCalculator()`) 또는 정적 메서드화.

---

### [MED-4] `serverless/serializers.py:208-212` — MarketBreadthSerializer.get_signal_interpretation

```python
def get_signal_interpretation(self, obj):
    from serverless.services.market_breadth_service import MarketBreadthService
    service = MarketBreadthService()
    return service.get_signal_interpretation(obj.breadth_signal)
```

- **패턴**: MED-3와 동일. `MarketBreadthService` 인스턴스 매번 생성.
- **심각도**: MED.
- **수정 난이도**: 쉬움.
- **권장**: 클래스 메서드화 또는 모듈 싱글톤.

---

### [MED-5] `serverless/serializers.py:275-285` — ScreenerPresetSerializer.get_owner_email

```python
def get_owner_email(self, obj):
    if obj.user:
        email = obj.user.email   # ← FK 트래버스
        ...
```

- **패턴**: List endpoint에서 사용 시(serverless의 preset list), view가 `select_related('user')` 미적용이면 N+1.
- **심각도**: MED.
- **수정 난이도**: 쉬움.
- **권장**: 해당 list view의 queryset에 `.select_related('user')` 추가.

---

### [MED-6] `serverless/serializers.py:531-554` — ScreenerAlertSerializer.get_preset_name

```python
def get_preset_name(self, obj):
    if obj.preset:
        return f"{obj.preset.icon} {obj.preset.name}"   # ← FK 트래버스
```

- **패턴**: `obj.can_trigger()` 메서드 내부의 추가 쿼리 가능성도 별도 검증 필요.
- **심각도**: MED.
- **수정 난이도**: 쉬움.
- **권장**: list view에서 `.select_related('preset')` 추가, `can_trigger()` 메서드에 추가 쿼리가 있다면 캐싱.

---

## 4. 인덱스 누락

전반적으로 인덱스 설계는 양호. 누락은 LOW~MED 수준.

### [MED-7] `news/models.py:19-209` — NewsArticle.sentiment_source 단독 인덱스

```python
sentiment_source = models.CharField(max_length=20, choices=..., default='none')
# Meta.indexes에 sentiment_source 단독 또는 복합 없음
```

- **사용처**: 뉴스 분류 / 통계 쿼리에서 단독 필터 가능성. 직접 사용처는 grep 추가 검증 필요.
- **심각도**: MED (테이블 크기 큼, 패턴 빈도는 미확인).
- **수정 난이도**: 쉬움 (db_index=True + makemigrations).
- **권장**: 사용 빈도 우선 측정 후 결정. 빈번하면 `Meta.indexes`에 `('-published_at', 'sentiment_source')` 복합 인덱스 추가.

---

### [MED-8] `stocks/models.py:799-831` — SignalAccuracy.signal_date 단독

```python
signal_date = models.DateField()                     # db_index 없음
class Meta:
    indexes = [models.Index(fields=['signal_date', 'signal_tag'])]
```

- **분석**: 복합 인덱스는 leftmost prefix `signal_date` 단독 쿼리에도 사용 가능. **실제로는 기존 인덱스로 충분**.
- **심각도**: MED → 재분류 후 **불필요** (오탐).
- **권장**: 조치 불필요.

---

### [LOW-3] `stocks/models.py` — DailyPrice.created_at 인덱스 (예방적)

```python
class DailyPrice(BasePriceData):
    # BasePriceData의 created_at에 db_index 미설정 (auto_now_add)
```

- **사용처**: 현재 코드에서 `created_at`을 `filter`/`order_by`에 사용하는 패턴은 명확히 발견되지 않음.
- **심각도**: LOW (사용처 미확인).
- **권장**: 배치 작업이 `created_at`으로 신규 데이터를 식별한다면 추가 검토. 그렇지 않으면 현 상태 유지.

---

### [HIGH-7] (재분류 결과) — 발견된 HIGH 인덱스 누락 없음

당초 후보였던 NewsArticle.category, DailyNewsKeyword.status 등은 **이미 복합 인덱스 또는 단독 db_index가 설정**되어 있음. 모델 파일을 직접 확인한 긍정 사례:

- `news/models.py` NewsArticle — `('-published_at', 'category')`, `('source', '-published_at')`, `llm_analyzed`/`is_archived` 단독 인덱스 ✓
- `news/models.py` DailyNewsKeyword — `('-date', 'status')` 복합 ✓
- `serverless/models.py` StockKeyword — `status db_index=True` + `('date', 'status')` 복합 ✓
- `rag_analysis/models.py` UsageLog — 4개 복합 인덱스 ✓
- `graph_analysis/models.py` CorrelationEdge — 3개 복합 인덱스 ✓
- `stocks/models.py` EODSignal — 시계열 인덱스 완비 ✓

→ 이 영역의 HIGH 이슈는 사실상 **0건**.

---

## 5. 권장 조치 우선순위

### Phase 1 — 즉시 (HIGH, 수정 난이도 쉬움)

1. **`config/settings.py:362`** — REST_FRAMEWORK에 `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 추가. (단, 기존 클라이언트 호환성 사전 점검 필요)
2. **`stocks/views_indicators.py:324-335`** — 루프 내 `Stock.objects.get()` → `Stock.objects.filter(symbol__in=symbols)` 일괄 조회.
3. **`news/api/views.py:95-100`** — `.prefetch_related('entities')` 추가.
4. **`stocks/serializers.py:405-409`** — `get_chart_data`에 `return ChartDataSerializer(recent_prices, many=True).data` 추가 (return 누락 버그).

### Phase 2 — 단기 (HIGH, 수정 난이도 중간)

5. **OverviewTab/StockComplete 통합** — Stock 조회에 `select_related` 6개 + `prefetch_related('category_signals')` 적용. View 레벨 한 줄로 6회 쿼리 절감.
6. **WatchListStockSerializer** — `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])`로 N+1 → 1쿼리.

### Phase 3 — 중기 (MED)

7. **`validation/api/views.py:112-124`** — `metric_code_id__in` bulk 쿼리 + `select_related('metric_code')`.
8. **Serializer 인스턴스화 오버헤드** — `IndicatorCalculator`, `MarketBreadthService`, `SectorHeatmapService` 모듈 싱글톤화.
9. **ScreenerPreset/Alert** — list view queryset에 `select_related('user')`, `select_related('preset')`.

### Phase 4 — 측정 후 결정 (MED-LOW)

10. NewsArticle.sentiment_source 인덱스 — 사용 빈도 측정 후 추가.
11. WatchlistListCreateView 페이지네이션 표준화 — Phase 1 적용 후.

---

## 6. 검증 메모 (직접 확인한 사항)

- `config/settings.py:348-362` — `DEFAULT_PAGINATION_CLASS` 부재 직접 확인.
- `stocks/views.py:75-105` — `StockListAPIView`에 `pagination_class` 미설정 직접 확인.
- `stocks/views.py:820-874` — `StockCompleteDataAPIView` 4개 분리 쿼리 직접 확인.
- `stocks/views_indicators.py:300-371` — 루프 내 `Stock.objects.get()` 직접 확인.
- `news/api/views.py:80-110` — `entities__symbol` 필터 + distinct, prefetch 없음 직접 확인.
- `news/api/views.py:399-403` — `prefetch_related('entities')` 정상 적용된 긍정 사례 직접 확인.
- `validation/api/views.py:90-146` — 5종 metric 루프 쿼리 직접 확인.
- `users/views.py:262-266` — `select_related('stock')` 정상 적용 직접 확인 (긍정 사례).
- `stocks/serializers.py:398-409` — WatchListStockSerializer 메서드 직접 확인 (return 누락 포함).
- `stocks/serializers.py:205-307` — OverviewTabSerializer.get_dynamic_layers 6회 쿼리 직접 확인.

---

## 7. 추가 권장: 측정 도구 도입

정적 분석만으로는 실제 부하 분포를 확신할 수 없음. Phase 1 진행 전에 다음을 권장:

- **django-silk** 또는 **django-debug-toolbar** 으로 핵심 endpoint(/stocks/{symbol}/, /watchlist/, /news/stock/{symbol}/)의 쿼리 수 실측.
- N+1 자동 탐지 라이브러리 **nplusone** 적용으로 회귀 방지.
- 운영 환경에서는 **PostgreSQL pg_stat_statements** 로 실제 slow query 캡처.

이 측정 결과로 본 보고서의 우선순위(특히 MED 항목들)를 재조정하는 것이 권장됩니다.
