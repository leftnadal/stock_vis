# API 성능 감사 보고서

**작성일**: 2026-05-04
**범위**: Django REST Framework 백엔드 (17개 뷰 파일 + 7개 모델 파일 + 13개 serializer 파일)
**모드**: 읽기 전용 (코드 수정 없음)

---

## 요약

### 이슈 수 by 심각도

| 영역 | HIGH | MED | LOW | 합계 |
|------|:----:|:---:|:---:|:----:|
| 1. N+1 쿼리 (뷰) | 7 | 4 | 1 | 12 |
| 2. 인덱스 누락 (모델) | 0 | 2 | 1 | 3 |
| 3. 느린 Serializer | 6 | 1 | 0 | 7 |
| 4. 페이지네이션 누락 | 3 | 1 | 1 | 5 |
| **합계** | **16** | **8** | **3** | **27** |

### 수정 난이도 분포

| 난이도 | 건수 | 대표 사례 |
|------|:----:|---------|
| 쉬움 | 11 | `db_index=True` 추가, `pagination_class` 지정, bulk fetch 맵 |
| 중간 | 13 | `prefetch_related` 추가, F 표현식 집계, Q 객체 묶음 조회 |
| 높음 | 3 | 서비스 레이어 bulk 처리, 동적 레이어 캐시 구조 변경 |

### 예상 영향이 큰 Top 5 (즉시 조치 권장)

1. `validation/api/views.py:361` — `LeaderComparisonView` 50회+ MetricDefinition 단건 조회 → bulk
2. `chainsight/api/views.py:70-78` — `ChainSightGraphView` 그래프 edge × 2배 단건 조회
3. `stocks/serializers.py:215-307` — `OverviewTabSerializer.get_dynamic_layers` 인스턴스당 6개 추가 쿼리
4. `stocks/views_indicators.py:324-330` — `IndicatorComparisonView` 루프 내 `Stock.objects.get` + `DailyPrice.filter`
5. `stocks/views.py:75` & `news/api/views.py:42` — 대용량 리스트 엔드포인트 페이지네이션 누락

---

## 1. N+1 쿼리 이슈 (12건)

### 1.1 stocks/* 영역 (5건)

| ID | 파일 | 라인 | 패턴 | 심각도 | 난이도 |
|---|------|:----:|------|:-----:|:----:|
| N1-1 | stocks/views.py | 75-105 | `StockListAPIView` — pagination 없음 + select_related 누락 | HIGH | 쉬움 |
| N1-2 | stocks/views.py | 839-863 | `StockCompleteDataAPIView` — DailyPrice/BS/IS/CF 4개 별도 쿼리 | HIGH | 중간 |
| N1-3 | stocks/views_indicators.py | 324-335 | `IndicatorComparisonView` — `for symbol in symbols: Stock.objects.get + DailyPrice.filter` | HIGH | 중간 |
| N1-4 | stocks/views_indicators.py | 59-66 | `TechnicalIndicatorView` — values()에 select_related 누락 | MED | 중간 |
| N1-5 | stocks/views_mvp.py | 44-56 | `StockMVPListView` — only() 미사용으로 모든 컬럼 SELECT | MED | 쉬움 |

#### N1-3 상세 (HIGH)

```python
# stocks/views_indicators.py:324-335
for symbol in symbols:
    symbol = symbol.upper()
    try:
        stock = Stock.objects.get(symbol=symbol)              # N+1 (1)
    except Stock.DoesNotExist:
        continue
    prices = DailyPrice.objects.filter(stock=stock)\
        .order_by('-date')[:50].values_list('close_price', flat=True)  # N+1 (2)
```

**문제**: N개 symbol → 최소 2N개 쿼리.
**권장**: `Stock.objects.filter(symbol__in=[...]).prefetch_related(Prefetch('dailyprice_set', DailyPrice.objects.order_by('-date')[:50]))` 후 dict 매핑.

#### N1-2 상세 (HIGH)

```python
# stocks/views.py:839-863
recent_prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]
balance_sheets = BalanceSheet.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
income_statements = IncomeStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
cash_flows = CashFlowStatement.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
```

**문제**: 1 Stock 조회 + 4개 재무제표 별도 쿼리 = 최소 5쿼리. 페이지 단건 호출이지만 핫패스.
**권장**: `Prefetch` 객체로 한 번에 묶거나, 각각 `select_related('stock')` 동반.

---

### 1.2 비-stocks 영역 (7건)

| ID | 파일 | 라인 | 패턴 | 심각도 | 난이도 |
|---|------|:----:|------|:-----:|:----:|
| N1-6 | validation/api/views.py | 112-124 | `ValidationSummaryView` — `for mc in rank_metrics: MetricDefinition.objects.filter(pk=mc).first()` | HIGH | 중간 |
| N1-7 | validation/api/views.py | 199-217 | `ValidationMetricsView._build_category` — 카테고리당 5-20회 단건 조회 (`category=='all'` 시 40-150회) | HIGH | 중간 |
| N1-8 | validation/api/views.py | 361-365 | `LeaderComparisonView` — `for cat, mc in all_metrics(50+): MetricDefinition.filter(pk=mc).first()` | HIGH | 중간 |
| N1-9 | chainsight/api/views.py | 70-78 | `ChainSightGraphView` — edge별 `CoMentionEdge` + `PriceCoMovement` 2회씩 단건 조회 | HIGH | 쉬움 |
| N1-10 | rag_analysis/views.py | 312-336 | `DataBasketAddStockDataView` — 루프 내 `BasketItem.filter(...).first()` + `_get_data_snapshot` | MED | 쉬움 |
| N1-11 | serverless/views_admin.py | 478-500 | `AdminNewsCategoryView` — `for cat: cat.resolve_symbols()` (메서드 내부 DB 쿼리) | MED | 쉬움 |
| N1-12 | users/views.py | 367-414 | `PortfolioDetailTableView` — Python 루프에서 `portfolio.total_value` 등 @property 반복 계산 | MED | 쉬움 |

#### N1-6/7/8 상세 (validation, HIGH)

같은 안티패턴이 3곳 반복:
```python
# validation/api/views.py:361-365
for cat, mc in all_metrics:                              # 50개+
    md = MetricDefinition.objects.filter(pk=mc).first()   # 매 회 단건 조회
    if not md: continue
```

**권장**:
```python
codes = [mc for cat, mc in all_metrics]
metric_map = {m.metric_code: m for m in MetricDefinition.objects.filter(metric_code__in=codes)}
for cat, mc in all_metrics:
    md = metric_map.get(mc)
```
세 위치 모두 동일 패턴이라 공통 헬퍼화도 고려.

#### N1-9 상세 (chainsight, HIGH)

```python
# chainsight/api/views.py:70-78
for edge in result.get("edges", []):
    a, b = (from_t, to_t) if from_t < to_t else (to_t, from_t)
    cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()       # 2 × N
    pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
```

**권장**: edge pair 리스트 추출 → `Q` 객체 OR 결합 → 한 번에 fetch 후 `(a,b)` 키 dict.

#### N1-12 상세 (users, MED)

```python
# users/views.py:367-369
for portfolio in portfolios:
    total_value += portfolio.total_value      # @property: quantity * price
    total_cost += portfolio.total_cost
```

**권장**: DB 집계로 이전 — `aggregate(total_value=Sum(F('quantity')*F('stock__real_time_price')))`.

---

## 2. 인덱스 누락 이슈 (3건)

> ForeignKey/unique/PK는 자동 인덱스이므로 제외. 검사 결과 대부분의 모델은 이미 잘 인덱싱되어 있음 (`stocks.DailyPrice`, `news.NewsEntity`, `rag_analysis.UsageLog`, `sec_pipeline.RawDocumentStore` 모두 적절한 단일/복합 인덱스 보유).

| ID | 모델 | 필드 | 파일 | 라인 | 사용처 | 심각도 | 난이도 |
|---|------|------|------|:----:|------|:-----:|:----:|
| IDX-1 | news.NewsArticle | category | news/models.py | 82-87 | `.filter(category=...)` 단독 호출 발생 | MED | 쉬움 |
| IDX-2 | serverless.StockKeyword | (date, status) 복합 | serverless/models.py | 183, 225 | 일일 배치 `.filter(date=..., status=...)` 패턴 | MED | 쉬움 |
| IDX-3 | serverless.MarketMover | industry | serverless/models.py | 30 | `.filter(industry=...)` (드물게) | LOW | 쉬움 |

#### IDX-1 상세

```python
# news/models.py:82-87
category = models.CharField(
    max_length=20, choices=CATEGORY_CHOICES, default='general',
    help_text=_("뉴스 카테고리"),
    # db_index=True 누락
)
```
- `Meta.indexes`에 `['-published_at', 'category']` 복합 인덱스가 있어 정렬+카테고리는 커버되지만, **카테고리 단일 필터**(특히 `count()`, `distinct`)는 풀 스캔 위험.
- **권장**: `db_index=True` 추가 + makemigrations.

#### IDX-2 상세

`date`, `status` 각각 `db_index=True`는 있지만 `(date, status)` 복합 인덱스는 없음. 일일 배치(`expires_at` 정리 + 신규 생성)에서 복합 조건이 흔함.

**권장**:
```python
class Meta:
    indexes = [
        models.Index(fields=['date', 'status']),
        models.Index(fields=['symbol', '-date']),
        models.Index(fields=['expires_at']),
    ]
```

---

## 3. 느린 Serializer 이슈 (7건)

| ID | 파일 | 라인 | 패턴 | 심각도 | 난이도 |
|---|------|:----:|------|:-----:|:----:|
| SER-1 | stocks/serializers.py | 205-307 | `OverviewTabSerializer.get_dynamic_layers` — 인스턴스당 6개 OneToOne/reverse FK 조회 | HIGH | 높음 |
| SER-2 | stocks/serializers.py | 398-403 | `WatchListStockSerializer.get_latest_price` — 매 인스턴스 `DailyPrice.filter(stock=obj).first()` | HIGH | 중간 |
| SER-3 | stocks/serializers.py | 405-409 | `WatchListStockSerializer.get_chart_data` — 매 인스턴스 `DailyPrice.filter(...)[:7]` | HIGH | 중간 |
| SER-4 | news/api/serializers.py | 19, 47 | `NewsArticleListSerializer.entities` — nested many=True, 호출 측 `prefetch_related('entities')` 필수 | HIGH | 쉬움 |
| SER-5 | rag_analysis/serializers.py | 24-51, 68 | `DataBasketSerializer.items`, `AnalysisSessionSerializer.messages` — nested many=True 프리페치 의존 | HIGH | 쉬움 |
| SER-6 | users/serializers.py | 15 | `UserSerializer` — `favorite_stock` nested many=True 프리페치 의존 | HIGH | 쉬움 |
| SER-7 | serverless/serializers.py | 121-137 | `MarketMoverListSerializer.get_sector_alpha_display` — 매 호출마다 `IndicatorCalculator()` 인스턴스 생성 | MED | 쉬움 |

#### SER-1 상세 (HIGH, 난이도 높음)

```python
# stocks/serializers.py:205-307
def get_dynamic_layers(self, obj):
    signals = list(obj.category_signals.all())   # 215
    ns = obj.validation_news_summary             # 235 (OneToOne reverse)
    sp = obj.sensitivity_profile                 # 252
    # ... 추가 reverse FK/OneToOne 4개
```
- 단일 종목 OverviewTab은 1회 호출이지만, 만약 리스트 컨텍스트에서 재사용되면 N×6 폭발.
- **권장**: `prefetch_related('category_signals')` + `select_related('validation_news_summary', 'sensitivity_profile', ...)` 호출 측에서 일괄 적용. 동적 레이어 카탈로그 자체를 단순화 검토.

#### SER-4/5/6 상세

nested `many=True` 자체가 N+1을 만드는 게 아니라, **호출 측 view가 `prefetch_related`를 호출하지 않으면** 직렬화 시 N+1이 발생. 다음 view에서 prefetch 누락 추정:
- `news/api/views.py` `NewsViewSet.list/stock_news`
- `rag_analysis/views.py` 의 BasketDetail/Session 관련
- `users/views.py:182-190` `UserFavorites.get` (`user.favorite_stock.all()` 반환)

**권장**: 각 뷰의 `get_queryset`에서 `.prefetch_related('entities')`, `.prefetch_related('items')`, `.prefetch_related('favorite_stock')` 명시.

#### SER-7 상세

```python
# serverless/serializers.py:121
def get_sector_alpha_display(self, obj):
    from serverless.services.indicators import IndicatorCalculator
    calc = IndicatorCalculator()                  # 매 인스턴스마다 생성
    return calc.format_sector_alpha_display(obj.sector_alpha)
```
- 500개 항목 직렬화 = 500번 객체 생성 (DB 쿼리는 아니지만 GC/import 오버헤드).
- **권장**: 모듈 레벨 싱글톤, 또는 함수형 헬퍼로 변경.

---

## 4. 페이지네이션 누락 이슈 (5건)

> 전제: `config/settings.py:341-349`에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE` 미설정. 각 ListView가 명시하지 않으면 무제한 응답.

| ID | 파일 | 라인 | 클래스 | 데이터 규모 | 심각도 | 난이도 |
|---|------|:----:|------|------|:-----:|:----:|
| PG-1 | config/settings.py | 341-349 | (전역) `REST_FRAMEWORK` — `DEFAULT_PAGINATION_CLASS` 누락 | 모든 ListAPIView 영향 | HIGH | 쉬움 |
| PG-2 | stocks/views.py | 75-105 | `StockListAPIView` (ListAPIView) — pagination_class 미설정 | Stock 수천 건 | HIGH | 쉬움 |
| PG-3 | news/api/views.py | 42-100 | `NewsViewSet` (ReadOnlyModelViewSet) — list/stock_news에 pagination 미설정, `.distinct().order_by()` 그대로 반환 | News 수만 건 | HIGH | 쉬움 |
| PG-4 | users/views.py | 89-92 | `Users.get` — `User.objects.all()` + `Response(serializer.data)` | 사용자 전체 (관리자용) | MED | 쉬움 |
| PG-5 | users/views.py | 182-190 | `UserFavorites.get` — `user.favorite_stock.all()` 직접 반환 | 보통 수십 개 | LOW | 쉬움 |

#### PG-1 권장 수정

```python
# config/settings.py
REST_FRAMEWORK = {
    ...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```
- 한 번에 PG-2~PG-5 대부분 자동 해결됨. 단, `Response(...)` 직접 반환하는 APIView는 별도 처리 필요.

#### 페이지네이션 미설정이지만 위험도 낮은 케이스 (참고)
- `stocks/views_screener.py:27` `StockScreenerView` — APIView, 필터 결과 자체가 작음
- `stocks/views_screener.py:243` `LargeCapStocksView` — pre-filtered
- `stocks/views_market_movers.py:22` `MarketMoversView` — `limit=20` 하드코딩

---

## 부록 A: 우선순위 액션 아이템

### Sprint 1 (즉시, 1주)
- [ ] PG-1: `DEFAULT_PAGINATION_CLASS` 전역 설정 (PG-2~PG-5 일괄 완화)
- [ ] N1-6/7/8: validation MetricDefinition bulk 패턴 적용 (3곳 동일)
- [ ] N1-9: chainsight edge bulk Q 조회
- [ ] IDX-1: `news.NewsArticle.category db_index=True` + 마이그레이션

### Sprint 2 (1~2주)
- [ ] N1-3: `IndicatorComparisonView` Prefetch 묶음 적용
- [ ] N1-2: `StockCompleteDataAPIView` Prefetch 적용
- [ ] SER-2/3: `WatchListStockSerializer` 호출 측에 Prefetch 적용
- [ ] SER-4/5/6: nested serializer 사용 view에 `prefetch_related` 명시
- [ ] SER-7: `IndicatorCalculator` 싱글톤화

### Sprint 3 (1개월)
- [ ] N1-12: `PortfolioDetailTableView` F 표현식 집계 전환
- [ ] N1-11: `AdminNewsCategoryView` 서비스 레이어 bulk 처리
- [ ] N1-10: `DataBasketAddStockDataView` BasketItem 사전 로드
- [ ] SER-1: `OverviewTabSerializer.get_dynamic_layers` 구조 재검토
- [ ] IDX-2: `serverless.StockKeyword (date, status)` 복합 인덱스
- [ ] N+1 회귀 방지: `assertNumQueries` 또는 django-silk 도입

---

## 부록 B: 분석 커버리지

### 검사한 파일

**뷰 (17)**: stocks/views.py, stocks/views_search.py, stocks/views_exchange.py, stocks/views_eod.py, stocks/views_screener.py, stocks/views_market_movers.py, stocks/views_fundamentals.py, stocks/views_indicators.py, stocks/views_mvp.py, users/views.py, news/api/views.py, macro/views.py, rag_analysis/views.py, serverless/views_admin.py, validation/api/views.py, chainsight/api/views.py, sec_pipeline/views.py

**모델 (7)**: stocks/models.py, users/models.py, news/models.py, serverless/models.py, rag_analysis/models.py, sec_pipeline/models.py, graph_analysis/models.py

**Serializer (10+)**: stocks/serializers.py(+fundamentals/market_movers/exchange/screener), rag_analysis/serializers.py, serverless/serializers.py, macro/serializers.py, news/api/serializers.py, users/serializers.py

### 이슈가 발견되지 않은 파일 (참고)

- stocks/views_search.py, stocks/views_exchange.py, stocks/views_fundamentals.py, stocks/views_eod.py — `select_related('stock')` 적절히 사용
- macro/views.py — 비교적 단순 구조, N+1 패턴 없음
- sec_pipeline/views.py — 적절한 prefetch 사용
- stocks/models.py `DailyPrice` — 다중 복합 인덱스 잘 정의됨
- rag_analysis/models.py `UsageLog` — `[user, created_at]`, `[model, created_at]`, `[request_type, created_at]`, `[cached, created_at]` 4종 복합 인덱스 보유

---

**감사 종료**. 모든 분석은 읽기 전용. 코드/마이그레이션은 변경되지 않았습니다.
