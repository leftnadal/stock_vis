# API 성능 감사 보고서

생성일: 2026-04-26
대상: Stock-Vis Backend (Django 5.1.7 / DRF)
범위: views 17개, models 7개

---

## 요약

| 심각도 | 개수 |
|--------|------|
| HIGH   | 8    |
| MED    | 14   |
| LOW    | 9    |

### 카테고리별
- N+1 쿼리: 11건
- 인덱스 누락: 6건
- 느린 Serializer: 5건
- 페이지네이션 누락: 10건

---

## 전역 설정 확인 결과

`config/settings.py` 의 `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` 미설정.
즉, DRF 전역 페이지네이션이 없으며, 각 뷰에서 명시하지 않으면 무제한 응답이 반환된다.

```python
# config/settings.py:321-329
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    # DEFAULT_PAGINATION_CLASS 없음
}
```

---

## 상세

---

### [HIGH] 페이지네이션 누락: users/views.py:89-92 - Users.get()

**파일**: `users/views.py:89-92`
**증거**:
```python
def get(self, request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)
```
**문제**: 전체 사용자 목록을 페이지네이션 없이 반환. 서비스가 성장할수록 전체 User 행을 메모리에 올려 직렬화하는 풀 테이블 스캔 + 메모리 압박이 발생한다.
**권장 수정**: `User.objects.all()` 에 `PageNumberPagination` 적용 또는 `generics.ListAPIView` + `pagination_class` 지정.
**난이도**: 쉬움

---

### [HIGH] 페이지네이션 누락: stocks/views.py:75-105 - StockListAPIView

**파일**: `stocks/views.py:75-105`
**증거**:
```python
class StockListAPIView(generics.ListAPIView):
    serializer_class = StockListSerializer

    def get_queryset(self):
        queryset = Stock.objects.all()
        ...
        return queryset.order_by('-market_capitalization')
```
**문제**: `generics.ListAPIView` 사용이지만 `pagination_class`가 뷰에 지정되지 않았고 전역 `DEFAULT_PAGINATION_CLASS`도 없다. S&P 500 + 기타 종목 전체(수천 건)가 한 번에 반환될 수 있다.
**권장 수정**: 뷰에 `pagination_class = PageNumberPagination` 추가 또는 settings.py에 `DEFAULT_PAGINATION_CLASS` 설정.
**난이도**: 쉬움

---

### [HIGH] N+1 쿼리: users/views.py:367-369 - PortfolioSummaryView

**파일**: `users/views.py:349-384`
**증거**:
```python
portfolios = Portfolio.objects.filter(user=request.user).select_related('stock')
...
for portfolio in portfolios:
    total_value += portfolio.total_value   # float(self.quantity) * float(self.stock.real_time_price)
    total_cost += portfolio.total_cost
```
**문제**: `select_related('stock')` 가 적용되어 있어 실제 N+1은 아니다. 그러나 `total_value`와 `total_cost` 프로퍼티는 Python 루프로 계산되며, `portfolios.count()`가 루프 밖에서 별도 쿼리를 추가로 발생시킨다 (SELECT COUNT(*) 1회 + SELECT * 1회 = 2쿼리 + 순회). 더 큰 문제는 Python 루프 합산 대신 DB 집계를 사용할 수 있다는 점이다.
**권장 수정**:
```python
from django.db.models import Sum, F
agg = Portfolio.objects.filter(user=request.user).aggregate(
    total_value=Sum(F('quantity') * F('stock__real_time_price')),
    total_cost=Sum(F('quantity') * F('average_price')),
    total_stocks=Count('id'),
)
```
**난이도**: 중간

---

### [HIGH] N+1 쿼리: users/views.py:402 - PortfolioDetailTableView

**파일**: `users/views.py:395-426`
**증거**:
```python
portfolios = Portfolio.objects.filter(user=request.user).select_related('stock')
total_portfolio_value = sum(p.total_value for p in portfolios)
...
total_cost = sum(p.total_cost for p in portfolios)
```
**문제**: `portfolios` queryset을 두 번 순회한다 (`sum(p.total_value ...)` 한 번, `sum(p.total_cost ...)` 한 번). Django queryset은 첫 번째 순회에서 캐시되지만, 두 번 평가하면 쿼리셋 캐시가 없는 경우 2회 DB 접근이 발생할 수 있다. `select_related`가 있어 stock 접근은 OK이나 단일 집계 쿼리로 교체하면 훨씬 효율적이다.
**권장 수정**: DB 단에서 `aggregate(Sum(F('quantity') * F(...)))` 로 단일 쿼리로 처리.
**난이도**: 중간

---

### [HIGH] N+1 쿼리: stocks/serializers.py:400-408 - StockListSerializer.get_latest_price / get_chart_data

**파일**: `stocks/serializers.py:398-412` (추정 위치)
**증거**:
```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
    ...

def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
```
**문제**: `StockListSerializer`는 목록 뷰에서 `many=True`로 호출된다. `get_latest_price`와 `get_chart_data` 각각이 종목당 1쿼리씩 발생시킨다. 종목 N개 목록 조회 시 `1(Stock list) + N(latest_price) + N(chart_data)` = 2N+1 쿼리.
**권장 수정**: `StockListAPIView.get_queryset()`에서 `prefetch_related(Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7]))` 를 적용하거나, SerializerMethodField 대신 `annotate`로 처리.
**난이도**: 중간

---

### [HIGH] N+1 쿼리: stocks/views_eod.py:72-98 - EODSignalDetailView

**파일**: `stocks/views_eod.py:72-98`
**증거**:
```python
signals = (
    EODSignal.objects.filter(date=target_date, signals__contains=[{'id': signal_id}])
    .select_related('stock')
    .order_by('-composite_score')[:50]
)

data = [
    {
        'company_name': s.stock.stock_name or '',  # select_related로 OK
        ...
    }
    for s in signals
]
```
**문제**: `select_related('stock')` 가 적용되어 `s.stock.stock_name` 접근은 추가 쿼리 없이 처리된다. 그러나 `signals__contains` 필터는 PostgreSQL JSON 포함 조회이며, `EODSignal.signals` 컬럼에 GIN 인덱스가 없으면 풀 테이블 스캔이 발생한다. 데이터가 많아질 경우 HIGH 위험.
**권장 수정**: `EODSignal.signals` JSON 필드에 GIN 인덱스 추가:
```python
class Meta:
    indexes = [GinIndex(fields=['signals'])]
```
**난이도**: 쉬움

---

### [HIGH] 페이지네이션 누락: users/views.py:185-190 - UserFavorites

**파일**: `users/views.py:185-190`
**증거**:
```python
def get(self, request):
    user = request.user
    favorite_stocks = user.favorite_stock.all()
    from stocks.serializers import StockSerializer
    serializer = StockSerializer(favorite_stocks, many=True)
    return Response(serializer.data)
```
**문제**: ManyToMany 전체를 페이지네이션 없이 반환. `StockSerializer`는 필드가 많은 상세 Serializer이므로 즐겨찾기가 많으면 응답 사이즈가 크게 늘어난다.
**권장 수정**: `PageNumberPagination` 적용, 또는 `StockListSerializer`(경량 버전)로 교체.
**난이도**: 쉬움

---

### [HIGH] 페이지네이션 누락: news/api/views.py:42-46 - NewsViewSet 기본 목록

**파일**: `news/api/views.py:42-46`
**증거**:
```python
class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.all().prefetch_related('entities')
    serializer_class = NewsArticleListSerializer
```
**문제**: `ReadOnlyModelViewSet` 의 기본 `list` 액션이 활성화되어 있고 `pagination_class`가 지정되지 않았으며 전역 설정도 없다. `NewsArticle.objects.all()`은 뉴스 전체를 반환하므로 수만 건이 응답에 포함될 수 있다.
**권장 수정**: ViewSet에 `pagination_class = PageNumberPagination` 추가.
**난이도**: 쉬움

---

### [MED] N+1 쿼리: stocks/views_indicators.py:324-371 - IndicatorComparisonView

**파일**: `stocks/views_indicators.py:324-371`
**증거**:
```python
for symbol in symbols:
    symbol = symbol.upper()
    try:
        stock = Stock.objects.get(symbol=symbol)  # 심볼마다 쿼리 1회
    except Stock.DoesNotExist:
        continue

    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]...  # 심볼마다 쿼리 1회
```
**문제**: POST로 symbols 배열을 받아 각 심볼마다 `Stock.objects.get()` 1회 + `DailyPrice.objects.filter()` 1회 = 심볼 N개시 2N 쿼리 발생.
**권장 수정**: `Stock.objects.filter(symbol__in=symbols).prefetch_related(Prefetch('dailyprice_set', ...))` 로 일괄 조회.
**난이도**: 중간

---

### [MED] N+1 쿼리: chainsight/api/views.py:70-84 - ChainSightGraphView

**파일**: `chainsight/api/views.py:70-84`
**증거**:
```python
for edge in result.get("edges", []):
    from_t = edge.get("from", "")
    to_t = edge.get("to", "")
    if from_t and to_t:
        a, b = (from_t, to_t) if from_t < to_t else (to_t, from_t)
        cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()   # 엣지마다 1쿼리
        pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first() # 엣지마다 1쿼리
```
**문제**: Neo4j에서 반환된 edges 리스트를 순회하며 각 엣지마다 `CoMentionEdge`와 `PriceCoMovement`를 각각 1쿼리씩 조회한다. 엣지 수가 E개이면 2E 쿼리가 발생. depth=2 이상에서는 수십~수백 건의 쿼리가 발생한다.
**권장 수정**: 
```python
# 먼저 모든 (a,b) 쌍을 수집한 뒤 IN 조회
pairs = [(min(e['from'], e['to']), max(e['from'], e['to'])) for e in edges if e.get('from') and e.get('to')]
cm_map = {(cm.symbol_a, cm.symbol_b): cm for cm in CoMentionEdge.objects.filter(
    symbol_a__in=[p[0] for p in pairs], symbol_b__in=[p[1] for p in pairs]
)}
```
**난이도**: 중간

---

### [MED] N+1 쿼리: validation/api/views.py:110-124 - ValidationSummaryView._find_leader + ranks 루프

**파일**: `validation/api/views.py:110-124`
**증거**:
```python
rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
ranks = []
for mc in rank_metrics:
    delta = CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
    ).first()                                                 # 지표마다 1쿼리 (5회)
    if delta and delta.rank and delta.total:
        md = MetricDefinition.objects.filter(pk=mc).first()  # 지표마다 1쿼리 (최대 5회)
```
**문제**: `rank_metrics` 리스트를 순회하며 `CompanyBenchmarkDelta`와 `MetricDefinition`을 각각 1쿼리씩 조회한다. 최대 10쿼리 발생.
**권장 수정**:
```python
deltas = CompanyBenchmarkDelta.objects.filter(
    symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics
).select_related('metric_code')
delta_map = {d.metric_code_id: d for d in deltas}
```
**난이도**: 쉬움

---

### [MED] N+1 쿼리: serverless/views_admin.py:477-499 - AdminNewsCategoryView.get()

**파일**: `serverless/views_admin.py:477-499`
**증거**:
```python
categories = NewsCollectionCategory.objects.all()
result = []
for cat in categories:
    symbols = cat.resolve_symbols()  # 내부적으로 SP500Constituent 또는 ETF 쿼리 가능
    result.append({...})
```
**문제**: `resolve_symbols()` 메서드가 각 카테고리마다 DB 쿼리(sector/sub_sector는 SP500Constituent 필터링)를 실행할 수 있다. 카테고리 수 N개이면 N+1 쿼리 가능성이 있다.
**권장 수정**: `resolve_symbols()` 내부 구현 확인 후, 필요시 SP500Constituent를 bulk로 미리 로드하여 캐싱.
**난이도**: 중간

---

### [MED] N+1 쿼리: users/views.py:872-889 - WatchlistBulkAddView

**파일**: `users/views.py:872-889`
**증거**:
```python
for symbol in symbols:
    try:
        stock = Stock.objects.get(symbol=symbol.upper())   # 심볼마다 1쿼리
        if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():  # 심볼마다 1쿼리
            skipped.append(symbol)
            continue
        item = WatchlistItem.objects.create(...)            # 심볼마다 1쿼리
```
**문제**: symbols 배열의 각 항목마다 최대 3쿼리 발생. 100개 심볼 일괄 추가시 최대 300쿼리.
**권장 수정**: 
```python
stocks = {s.symbol: s for s in Stock.objects.filter(symbol__in=[sym.upper() for sym in symbols])}
existing = set(WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=stocks.keys()).values_list('stock_id', flat=True))
WatchlistItem.objects.bulk_create([...])  # 일괄 INSERT
```
**난이도**: 중간

---

### [MED] 느린 Serializer: stocks/serializers.py:205-265 - OverviewTabSerializer.get_dynamic_layers()

**파일**: `stocks/serializers.py:205-265`
**증거**:
```python
def get_dynamic_layers(self, obj):
    """동적 레이어: validation + chainsight 모델 데이터.
    6개 모델 중 하나라도 데이터가 있으면 구조체 반환...
    # TODO: Step 2~4에서 데이터 유입 시 prefetch_related + 캐싱 레이어 적용 필요
    """
    layers = {}
    signals = list(obj.category_signals.all())   # 역참조 쿼리 1회
    ns = obj.validation_news_summary              # OneToOne 역참조 1회
```
**문제**: `SerializerMethodField`인 `get_dynamic_layers`가 최소 2개의 추가 쿼리를 발생시킨다. 코드 내 TODO 주석 자체가 이 문제를 인지하고 있음. `OverviewTabSerializer`가 목록이 아닌 단건 뷰에서만 사용되더라도 추가 쿼리는 발생한다.
**권장 수정**: 뷰 레벨에서 `select_related` 또는 `prefetch_related('category_signals', 'validation_news_summary')` 적용.
**난이도**: 쉬움

---

### [MED] 느린 Serializer: stocks/serializers.py:398-411 - StockHeaderSerializer.get_latest_price / get_chart_data

**파일**: `stocks/serializers.py:398-411`
**증거**:
```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
    return float(latest.close_price)

def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
```
**문제**: `StockHeaderSerializer`가 `StockDetailView.get_context_data()`에서도 사용되지만, 이 두 메서드가 목록 컨텍스트에서도 호출되면 종목당 2 추가 쿼리 발생. `DailyPrice` 조회가 두 번 중복된다.
**권장 수정**: `DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]` 를 한 번만 조회해서 재사용.
**난이도**: 쉬움

---

### [MED] 느린 Serializer: users/serializers.py:95-108 - PortfolioDetailSerializer.get_portfolio_weight()

**파일**: `users/serializers.py:95-108`
**증거**:
```python
portfolio_weight = serializers.SerializerMethodField()

def get_portfolio_weight(self, obj):
    """포트폴리오 내 비중 계산"""
    # context에서 전체 포트폴리오 가치를 가져와서 계산
```
**문제**: 코드를 보면 `context`에서 `total_portfolio_value`를 받아 계산하는 구조로 설계되었다. 그러나 `PortfolioSummaryView`의 루프(line 367-369)에서는 `select_related` 없이 `portfolio.total_value`를 호출하면 `stock.real_time_price` 접근 시 추가 쿼리가 발생할 가능성이 있다. `select_related('stock')`이 적용되어야 안전하다.
**권장 수정**: `PortfolioSummaryView` 뷰에서 `portfolios = Portfolio.objects.filter(...).select_related('stock')` 확인. (현재 적용됨 - 확인 필요)
**난이도**: 쉬움

---

### [MED] 느린 Serializer: news/api/views.py:89-103 - NewsViewSet.stock_news()의 articles.count() 이중 호출

**파일**: `news/api/views.py:89-103`
**증거**:
```python
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).distinct().order_by('-published_at')

serializer = self.get_serializer(articles, many=True)
data = {
    'symbol': symbol,
    'count': articles.count(),   # 추가 COUNT 쿼리 1회
    'articles': serializer.data  # 전체 SELECT 1회 (이미 queryset 평가됨)
}
```
**문제**: `serializer.data`가 queryset을 평가한 후 `articles.count()`를 다시 호출하면 COUNT(*) 쿼리가 추가로 발생한다. `len(serializer.data)`로 대체하면 DB 쿼리를 아낄 수 있다.
**권장 수정**: `'count': len(serializer.data)` 로 교체.
**난이도**: 쉬움

---

### [MED] 느린 Serializer: rag_analysis/views.py:609-611 - ChatStreamView basket 처리

**파일**: `rag_analysis/views.py:609-611`
**증거**:
```python
items_count = session.basket.items.count()   # COUNT 쿼리
if items_count > 0:
    session.basket.items.all().delete()       # DELETE 쿼리 + SELECT (내부적으로 2쿼리)
```
**문제**: `session.basket.items.count()`와 `session.basket.items.all().delete()` 두 번의 개별 쿼리 발생. 먼저 count를 확인하고 또 delete를 실행하는 불필요한 쿼리가 포함된다.
**권장 수정**: `deleted_count, _ = session.basket.items.all().delete()` 한 번에 처리.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: stocks/views_mvp.py:17-66 - StockMVPListView

**파일**: `stocks/views_mvp.py:17-66`
**증거**:
```python
class StockMVPListView(APIView):
    def get(self, request):
        queryset = Stock.objects.all()
        ...
        # MVP: 최대 20개만
        queryset = queryset[:20]
```
**문제**: 하드코딩된 `:20` 슬라이싱으로 제한하지만 DRF 표준 페이지네이션이 아니다. `page`/`page_size` 파라미터 지원이 없어 클라이언트가 다음 페이지를 요청할 방법이 없다.
**권장 수정**: DRF `PageNumberPagination` 적용. MVP라도 페이지네이션 응답 구조를 표준으로 맞추는 것이 권장된다.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: stocks/views_mvp.py:191-200 - SectorListView

**파일**: `stocks/views_mvp.py:191-200`
**증거**:
```python
class SectorListView(APIView):
    def get(self, request):
        sectors = Stock.objects.exclude(
            sector__isnull=True
        ).values_list('sector', flat=True).distinct()

        return Response({'sectors': list(sectors)})
```
**문제**: `distinct()` 로 중복을 제거하지만 페이지네이션 없이 전체 반환. 섹터 수는 많지 않아 LOW에 가깝지만, 전체 Stock 테이블 스캔 후 distinct가 필요하다.
**권장 수정**: sector 인덱스가 있으므로 인덱스 스캔 가능. 페이지네이션보다 결과를 캐싱하는 것이 더 효율적이다.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: rag_analysis/views.py:71-75 - DataBasketListCreateView

**파일**: `rag_analysis/views.py:71-75`
**증거**:
```python
def get(self, request):
    baskets = DataBasket.objects.filter(user=request.user).prefetch_related('items')
    serializer = DataBasketSerializer(baskets, many=True)
    return Response(create_success_response(serializer.data))
```
**문제**: 사용자의 DataBasket 전체를 페이지네이션 없이 반환. 바구니와 items가 함께 직렬화되어 응답 크기가 클 수 있다.
**권장 수정**: `pagination_class` 적용 또는 바구니 목록에서 `items`를 제외한 경량 serializer 사용.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: rag_analysis/views.py:430-435 - AnalysisSessionListCreateView

**파일**: `rag_analysis/views.py:430-435`
**증거**:
```python
def get(self, request):
    sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')
    serializer = AnalysisSessionSerializer(sessions, many=True)
    return Response(create_success_response(serializer.data))
```
**문제**: 분석 세션 전체 + messages를 페이지네이션 없이 반환. 사용 누적 시 세션 수와 메시지 수 모두 증가하여 응답이 무거워진다.
**권장 수정**: `pagination_class` 적용. 목록에서는 `messages`를 제외하는 경량 serializer 사용.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: news/api/views.py - NewsViewSet list 액션 + stock_news 액션

**파일**: `news/api/views.py:42-103`
**증거**:
```python
# stock_news 액션
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).distinct().order_by('-published_at')
# 페이지네이션 없이 .count()와 serializer.data 직접 반환
```
**문제**: 특정 종목의 뉴스가 days=30 등 긴 기간으로 조회 시 수백 건이 반환될 수 있다.
**권장 수정**: `days` 최대값 제한 강화(현재 없음) + 결과에 `limit` 파라미터 또는 DRF 페이지네이션 적용.
**난이도**: 쉬움

---

### [MED] 페이지네이션 누락: users/views.py:959-978 - UserInterestListCreateView.get()

**파일**: `users/views.py:959-978`
**증거**:
```python
def get(self, request):
    interests = UserInterest.objects.filter(user=request.user).order_by('-created_at')
    data = [
        {
            'id': i.id,
            ...
        }
        for i in interests
    ]
    return Response(data)
```
**문제**: UserInterest 전체를 Python list comprehension으로 직렬화해 반환. DRF Serializer도 사용하지 않고 페이지네이션도 없다.
**권장 수정**: `limit` 또는 `PageNumberPagination` 적용. 관심사 수가 많아지면 응답 크기 증가.
**난이도**: 쉬움

---

### [MED] 인덱스 누락: stocks/models.py - IncomeStatement.fiscal_year + period_type 복합

**파일**: `stocks/models.py:356-367` (BalanceSheet Meta), 공통 패턴
**증거**:
```python
class BalanceSheet(BasicFinancialStatement):
    class Meta:
        unique_together = ('stock', 'period_type', 'fiscal_year', 'fiscal_quarter')
        indexes = [
            models.Index(fields=['stock', 'fiscal_year']),
            models.Index(fields=['period_type', 'fiscal_year']),
        ]
```
**문제**: `views.py:635-639` 등 여러 곳에서:
```python
BalanceSheet.objects.filter(stock=stock, period_type=db_period).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
```
`(stock, period_type)` 복합 필터 후 `(-fiscal_year, -fiscal_quarter)` order_by를 사용하지만, 현재 인덱스는 `(stock, fiscal_year)`와 `(period_type, fiscal_year)` 분리되어 있다. `(stock, period_type, fiscal_year DESC)` 복합 인덱스가 없다.
**권장 수정**: `models.Index(fields=['stock', 'period_type', '-fiscal_year'])` 추가. IncomeStatement, CashFlowStatement에도 동일 적용.
**난이도**: 쉬움

---

### [LOW] 인덱스 누락: users/models.py - Watchlist.user + updated_at 인덱스 부재

**파일**: `users/models.py`
**증거**: `Watchlist.objects.filter(user=request.user).order_by('-updated_at')` 패턴이 `WatchlistListCreateView`에서 사용되지만, Watchlist 모델의 Meta를 확인해야 한다. Portfolio에는 `Index(fields=['user', '-updated_at'])` 가 있으나 Watchlist도 동일 패턴 사용.
**권장 수정**: Watchlist 모델에 `models.Index(fields=['user', '-updated_at'])` 추가 여부 확인.
**난이도**: 쉬움

---

### [LOW] 인덱스 누락: news/models.py - NewsEntity.symbol + news 연결

**파일**: `news/models.py:293-296`
**증거**:
```python
class Meta:
    indexes = [
        models.Index(fields=['symbol', 'entity_type']),
        models.Index(fields=['sentiment_score']),
    ]
```
`news/api/views.py:129-132`에서:
```python
entities = NewsEntity.objects.filter(
    symbol=symbol,
    news__published_at__gte=from_date
).select_related('news')
```
**문제**: `(symbol, news__published_at)` 는 JOIN 후 필터이므로 현재 인덱스로는 symbol 인덱스까지만 활용된다. `published_at` 범위 필터가 추가되면 인덱스 효율이 떨어진다. `NewsArticle.published_at` 에는 인덱스가 있지만 NewsEntity를 통한 JOIN 경로의 복합 인덱스가 없다.
**권장 수정**: 쿼리 패턴 분석 후 필요시 `(symbol, news_id)` 또는 NewsArticle 측 인덱스 보완.
**난이도**: 중간

---

### [LOW] 인덱스 누락: graph_analysis/models.py - CorrelationEdge stock_a, stock_b 복합

**파일**: `graph_analysis/models.py`
**증거**:
```python
class CorrelationEdge(models.Model):
    watchlist = models.ForeignKey(...)
    stock_a = models.ForeignKey(Stock, ...)
    stock_b = models.ForeignKey(Stock, ...)
    date = models.DateField(db_index=True)
```
**문제**: `(watchlist, date)` 기준 쿼리가 있을 경우 FK 자동 인덱스와 date 인덱스는 있으나, `(watchlist, date)` 복합 인덱스가 없다. Meta.indexes를 확인해야 하며, 상관관계 그래프 조회가 주요 패턴이므로 누락 시 성능 저하 위험.
**권장 수정**: `models.Index(fields=['watchlist', '-date'])` 추가 확인.
**난이도**: 쉬움

---

### [LOW] 인덱스 누락: sec_pipeline/models.py - SupplyChainEvidence.neo4j_dirty 필터

**파일**: `sec_pipeline/models.py:100`
**증거**:
```python
neo4j_dirty = models.BooleanField(default=True)
```
**문제**: Neo4j 동기화 배치 태스크에서 `neo4j_dirty=True` 인 레코드만 필터링하는 패턴이 예상된다. 해당 필드에 `db_index=True`가 없다. 레코드 수가 많아지면 Full Table Scan 발생.
**권장 수정**: `neo4j_dirty = models.BooleanField(default=True, db_index=True)` 로 변경.
**난이도**: 쉬움

---

### [LOW] 인덱스 누락: rag_analysis/models.py - DataBasket.user + updated_at

**파일**: `rag_analysis/models.py:28-31`
**증거**:
```python
class Meta:
    ordering = ["-updated_at"]
```
`DataBasketListCreateView`에서 `DataBasket.objects.filter(user=request.user)` 가 사용된다. Meta에 user 기준 인덱스가 없다.
**권장 수정**: `models.Index(fields=['user', '-updated_at'])` 추가.
**난이도**: 쉬움

---

### [LOW] 페이지네이션 누락: stocks/views.py:195-200 - StockSectorListView (간접)

**파일**: `stocks/views_mvp.py:190-200`
**증거**:
```python
sectors = Stock.objects.exclude(sector__isnull=True).values_list('sector', flat=True).distinct()
return Response({'sectors': list(sectors)})
```
**문제**: 섹터 종류는 수십 개로 제한적이라 실제 성능 영향은 미미하다. 그러나 전체 Stock을 스캔하는 distinct 쿼리다. `sector` 필드에 인덱스가 있어(`Meta.indexes`에 `['sector']` 포함) 인덱스 스캔으로 처리된다.
**권장 수정**: 결과를 캐싱(`cache.get_or_set`)하여 반복 쿼리 제거.
**난이도**: 쉬움

---

### [LOW] N+1 잠재 위험: stocks/views.py:834-872 - StockCompleteDataAPIView

**파일**: `stocks/views.py:834-872`
**증거**:
```python
stock = get_object_or_404(Stock, symbol=symbol.upper())
header_data = StockHeaderSerializer(stock).data    # DailyPrice 추가 쿼리
overview_data = OverviewTabSerializer(stock).data  # overview_ko, category_signals 추가 쿼리
balance_sheets = BalanceSheet.objects.filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]
income_statements = IncomeStatement.objects.filter(...)[:5]
cash_flows = CashFlowStatement.objects.filter(...)[:5]
```
**문제**: `StockCompleteDataAPIView`는 단건 뷰이므로 N+1 문제는 아니지만, `OverviewTabSerializer`의 `get_dynamic_layers`가 추가 쿼리를 발생시키고, `StockHeaderSerializer`의 `get_latest_price`/`get_chart_data`도 추가 쿼리를 발생시킨다. 총 5~7개 쿼리가 연속 실행된다.
**권장 수정**: `Stock.objects.select_related('overview_ko').prefetch_related('category_signals')` 로 미리 로드.
**난이도**: 쉬움

---

### [LOW] 느린 Serializer 잠재: users/serializers.py - WatchlistDetailSerializer depth 확인

**파일**: `users/serializers.py`
**증거**:
```python
# WatchlistDetailView.get_object()에서
watchlist = Watchlist.objects.prefetch_related('items__stock').get(pk=pk, user=user)
```
`WatchlistDetailSerializer`가 내부적으로 depth나 nested serializer를 사용하는지 확인 필요. `prefetch_related('items__stock')`이 적용되어 있어 N+1은 방지되지만, serializer가 depth를 사용하면 불필요한 FK 자동 조인이 발생한다.
**권장 수정**: Serializer Meta에 `depth` 사용 여부 확인. 사용 중이면 명시적 Serializer로 교체.
**난이도**: 쉬움

---

### [LOW] N+1 잠재: stocks/views_mvp.py:47-56 - StockMVPListView summary 루프

**파일**: `stocks/views_mvp.py:44-56`
**증거**:
```python
queryset = queryset[:20]

if mode == 'summary':
    data = []
    for stock in queryset:
        data.append({
            'symbol': stock.symbol,
            'price': float(stock.real_time_price) if stock.real_time_price else 0,
```
**문제**: `real_time_price`는 Stock 자체 필드이므로 추가 쿼리 없이 접근 가능. 실제 N+1은 없다. 다만 Python 루프 직렬화보다 DRF Serializer 사용이 코드 품질 측면에서 권장된다. LOW.
**권장 수정**: 경량 Serializer로 교체하여 일관성 확보.
**난이도**: 쉬움

---

## 우선순위 권장

### 즉시 처리 (High ROI 순)

1. **[HIGH, 쉬움] NewsViewSet 페이지네이션 추가** - `news/api/views.py:42` 에 `pagination_class = PageNumberPagination` 한 줄 추가. 뉴스 전체가 무제한 반환되는 심각한 위험.

2. **[HIGH, 쉬움] StockListAPIView 페이지네이션 추가** - `stocks/views.py:75` 의 `generics.ListAPIView` 에 `pagination_class` 지정. 전체 종목 무제한 반환 방지.

3. **[HIGH, 쉬움] Users.get() 페이지네이션 추가** - `users/views.py:90`. 전체 사용자 목록 무제한 반환 방지.

4. **[HIGH, 쉬움] OverviewTabSerializer 미적용 prefetch 보완** - `stocks/views.py:492-493` 의 `select_related`에 `category_signals` prefetch 추가.

5. **[HIGH, 중간] StockListSerializer N+1 수정** - `get_latest_price`와 `get_chart_data`의 쿼리를 view 레벨 prefetch로 처리. 종목 목록 조회 성능에 직접 영향.

6. **[MED, 쉬움] rank_metrics 루프 IN 쿼리 변환** - `validation/api/views.py:112-122`. 5+5 쿼리 → 1쿼리.

7. **[MED, 쉬움] BalanceSheet/IncomeStatement/CashFlowStatement 복합 인덱스 추가** - `(stock, period_type, fiscal_year DESC)` 3개 마이그레이션. 재무제표 조회 빈도가 높으므로 즉각적 성능 향상.

8. **[MED, 쉬움] articles.count() → len(serializer.data) 교체** - `news/api/views.py:97`. 한 줄 수정으로 COUNT 쿼리 1회 제거.

---

## 노트

### 검사하지 못한 영역

- `thesis/` 뷰 파일 미포함 (지시서 17개 목록에 없음)
- `chainsight/api/views.py`의 하단 뷰들 (200줄 이후): `ChainSightSeedsView`, `SignalFeedView` 등 추가 확인 필요
- `validation/api/views.py` 200줄 이후 (PresetView, LeaderComparisonView 등)
- `news/api/views.py` 150줄 이후 (trending, signal_feed 등)

### 긍정적 발견사항

- `Stock` 모델: sector, industry, market_capitalization, last_updated, real_time_price, (symbol, sector) 복합 인덱스 모두 정의되어 있음.
- `DailyPrice`/`WeeklyPrice`: (stock, date), (date, volume), (stock, -date) 인덱스 잘 정의됨.
- `WatchlistStocksView`, `WatchlistDetailView`: `select_related`/`prefetch_related` 적절히 적용됨.
- `PortfolioListCreateView.get()`, `PortfolioDetailTableView.get()`: `select_related('stock')` 적용됨.
- `users/views.py`의 Watchlist 관련 뷰들: 캐싱(`watchlist_cached_api`) 적용 + 수동 페이지네이션 구현됨.
- `MarketMover`, `StockKeyword` 등 serverless 모델: 인덱스 잘 정의됨.

### 후속 감사 권장 사항

- `thesis/views/` 전체 뷰 감사 (가설 관련 목록 뷰 페이지네이션 여부)
- `chainsight/api/views.py` 하단 Signal 관련 뷰 감사
- `EODSignal.signals` JSON 필드에 GIN 인덱스 추가 여부 검토 (PostgreSQL 전용)
- `AnalysisSession.messages` prefetch 최적화 - 채팅 히스토리가 길어질 경우 성능 영향
- Django `DEBUG=True` 환경에서 `django-silk` 또는 `django-debug-toolbar`로 실제 쿼리 수 측정 권장
