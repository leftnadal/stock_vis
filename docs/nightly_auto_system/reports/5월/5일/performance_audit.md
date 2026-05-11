# API 성능 감사 보고서

**감사일**: 2026-05-05
**감사자**: Claude (read-only audit)
**범위**: views 17개 / serializers 10개 / models 7개
**목적**: N+1 쿼리, 인덱스 누락, 느린 Serializer, 페이지네이션 누락 탐지

---

## 요약

### 심각도별 이슈 수

| 카테고리 | HIGH | MED | LOW | 합계 |
|---------|------|-----|-----|------|
| N+1 쿼리 | 2 | 1 | 0 | 3 |
| DB 인덱스 누락 | 2 | 1 | 0 | 3 |
| 느린 Serializer | 3 | 6 | 1 | 10 |
| 페이지네이션 누락 | 5 | 37 | - | 42 |
| **합계** | **12** | **45** | **1** | **58** |

### 핵심 권장사항 (P0 - 즉시 수정)

1. **글로벌 페이지네이션 설정 누락** (`config/settings.py`) — 모든 list 엔드포인트가 영향받음. `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` + `PAGE_SIZE=20` 추가
2. **stocks/views_indicators.py:324** — 루프 내 `Stock.objects.get()` (N개 symbols = N번 쿼리)
3. **stocks/serializers.py:400, 407** — `WatchListStockSerializer`의 `get_latest_price`, `get_chart_data`가 인스턴스마다 DailyPrice 조회
4. **stocks/serializers.py:205** — `OverviewTabSerializer.get_dynamic_layers`가 6개 OneToOne/Reverse FK에 prefetch 없이 접근

### 환경/코드 컨텍스트

- 글로벌 페이지네이션: **미설정** (`config/settings.py` REST_FRAMEWORK에 `DEFAULT_PAGINATION_CLASS` 부재)
- 일부 뷰는 수동 페이지네이션 구현 (Watchlist, Usage, SignalFeed 등) → 일관성 부족

---

## 상세

### 1. N+1 쿼리 이슈

#### 1.1 [HIGH / 쉬움] stocks/views_indicators.py:324 — IndicatorComparisonView

**파일**: `stocks/views_indicators.py:324-330`

```python
for symbol in symbols:
    symbol = symbol.upper()
    try:
        stock = Stock.objects.get(symbol=symbol)  # N번 쿼리
    except Stock.DoesNotExist:
        continue
```

- **문제**: 클라이언트가 보낸 symbols 배열만큼 DB 호출
- **영향**: 100 symbols 비교 시 100번의 단건 쿼리
- **권장 수정**:
  ```python
  stocks_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=[s.upper() for s in symbols])}
  for symbol in symbols:
      stock = stocks_map.get(symbol.upper())
      if not stock:
          continue
  ```

#### 1.2 [HIGH / 중간] serverless/views_admin.py:475 — AdminNewsCategoryView.get

**파일**: `serverless/views_admin.py:475-500`

```python
categories = NewsCollectionCategory.objects.all()
for cat in categories:
    symbols = cat.resolve_symbols()  # 메서드 내부 DB 쿼리
    result.append({...})
```

- **문제**: `resolve_symbols()`이 매 카테고리마다 DB를 조회할 가능성 (메서드 본체 확인 필요)
- **영향**: 카테고리 N개 × resolve_symbols() 내부 쿼리 수
- **권장 수정**: `resolve_symbols()` 구현 검토 후, 적절한 prefetch_related 추가 또는 bulk resolve 함수로 리팩토링

#### 1.3 [MED / 쉬움] news/api/views.py:88 — NewsViewSet.stock_news

**파일**: `news/api/views.py:88-99`

```python
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).distinct().order_by('-published_at')

serializer = self.get_serializer(articles, many=True)
```

- **문제**: ViewSet의 `queryset`에 `prefetch_related('entities')`가 있어도, `filter()` 호출로 prefetch 캐시가 일부 무효화될 수 있음. 또한 serializer가 `entities__highlights`까지 접근하면 추가 N+1
- **권장 수정**: 명시적으로 `.prefetch_related('entities__highlights')` 추가

---

### 2. DB 인덱스 누락

#### 2.1 [HIGH / 쉬움] serverless/models.py — VolatilityBaseline.date

- **모델**: `VolatilityBaseline`
- **문제**: `date` 필드에 `db_index=True` 없음 (단, `unique_together=(symbol, date)`가 존재 → PK 형태 인덱스로 일부 커버)
- **사용처**: `date` 단독 범위 조회 (예: 특정 날짜 이후 베이스라인 갱신) 시 풀 스캔 가능
- **권장 수정**: `date = models.DateField(db_index=True)` 또는 `Meta.indexes`에 `models.Index(fields=['date'])` 추가

#### 2.2 [HIGH / 쉬움] sec_pipeline/models.py — UnmatchedCompanyQueue.raw_company_name

- **모델**: `UnmatchedCompanyQueue`
- **문제**: `raw_company_name` 필드 인덱스 없음
- **사용처**: 미매칭 회사명 검색/매칭 (운영 도구에서 자주 호출)
- **권장 수정**: `raw_company_name = models.CharField(max_length=200, db_index=True)`. LIKE 검색이 잦으면 PostgreSQL `gin_trgm_ops` 인덱스 고려

#### 2.3 [MED / 선택] stocks/models.py — 재무제표 복합 인덱스

- **모델**: `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`
- **현재**: `(stock, period_type, fiscal_year, fiscal_quarter)` unique_together 존재
- **문제**: `filter(stock=..., period_type=...).order_by('-fiscal_year', '-fiscal_quarter')` 패턴에서 `(stock, period_type, fiscal_year, fiscal_quarter)` 인덱스가 효율적이긴 하나, prefix 매칭이므로 대체로 OK
- **권장**: 현재 충분, 필요 시에만 명시적 `Meta.indexes` 추가

#### ✅ 인덱스 충분 (확인 완료)

다음 모델들은 현재 인덱스가 충분하거나 복합 인덱스로 커버됨:
- `DailyPrice`, `WeeklyPrice` (시계열 `(stock, date)` 인덱스 OK)
- `NewsArticle`, `NewsEntity`, `SentimentHistory`, `DailyNewsKeyword`
- `MarketMover`, `StockKeyword`, `ScreenerAlert`, `ETFHolding`, `ThemeMatch`, `LLMExtractedRelation`
- `Portfolio`, `Watchlist`, `WatchlistItem`
- `UsageLog`, `RawDocumentStore`, `SupplyChainEvidence`, `BusinessModelSnapshot`
- `CorrelationMatrix`, `CorrelationEdge`, `CorrelationAnomaly`, `PriceCache`, `GraphMetadata`

---

### 3. 느린 Serializer

#### 3.1 [HIGH / 중간] stocks/serializers.py:398 — WatchListStockSerializer.get_latest_price

```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()  # N+1
    ...
```

- **문제**: list 엔드포인트(`many=True`)에서 Stock 인스턴스마다 DailyPrice 조회
- **권장 수정**: view에서 `Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date'))` 후 serializer는 `obj.daily_prices.all()[0]` 사용. 또는 `Stock.real_time_price` 컬럼 활용

#### 3.2 [HIGH / 중간] stocks/serializers.py:405 — WatchListStockSerializer.get_chart_data

```python
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
```

- **문제**: 위와 동일 패턴, 7일치 가격을 인스턴스마다 조회
- **권장 수정**: `Prefetch` 사용 후 슬라이싱은 파이썬에서 처리 (또는 view에서 7일치 미리 묶음 조회)

#### 3.3 [HIGH / 중간] stocks/serializers.py:205 — OverviewTabSerializer.get_dynamic_layers

```python
def get_dynamic_layers(self, obj):
    # CategorySignal (reverse FK)
    signals = list(obj.category_signals.all())          # 쿼리 1
    # 5개 OneToOne 관계 접근
    ns = obj.validation_news_summary                    # 쿼리 2
    sp = obj.sensitivity_profile                        # 쿼리 3
    gs = obj.growth_stage                               # 쿼리 4
    cd = obj.capital_dna                                # 쿼리 5
    nt = obj.narrative_tag                              # 쿼리 6
```

- **문제**: detail 엔드포인트 단건 호출 시에도 6개 추가 쿼리. 코드에 `# TODO: prefetch_related` 코멘트 존재
- **권장 수정**: view에서
  ```python
  Stock.objects.select_related(
      'validation_news_summary', 'sensitivity_profile',
      'growth_stage', 'capital_dna', 'narrative_tag'
  ).prefetch_related('category_signals')
  ```

#### 3.4 [MED / 쉬움] serverless/serializers.py:121, 127, 133 — MarketMoverListSerializer 표시 메서드

```python
def get_sector_alpha_display(self, obj):
    from serverless.services.indicators import IndicatorCalculator
    calc = IndicatorCalculator()  # 매 인스턴스마다 객체 생성
    return calc.format_sector_alpha_display(obj.sector_alpha)
```

- **문제**: list 응답 N개 × 3개 메서드 = 3N번 IndicatorCalculator 인스턴스화
- **권장 수정**: 클래스 변수로 단일 인스턴스 캐싱 또는 모듈 레벨 함수로 변경
  ```python
  _calc = IndicatorCalculator()
  class MarketMoverListSerializer(...):
      def get_sector_alpha_display(self, obj):
          return _calc.format_sector_alpha_display(obj.sector_alpha)
  ```

#### 3.5 [MED / 쉬움] serverless/serializers.py:208 — MarketBreadthSerializer.get_signal_interpretation

- 위와 동일 패턴 (`MarketBreadthService` 인스턴스 매번 생성)
- **권장 수정**: 모듈 레벨 인스턴스 또는 staticmethod 사용

#### 3.6 [MED / 쉬움] stocks/serializers.py:190 — OverviewTabSerializer.get_korean_overview

```python
def get_korean_overview(self, obj):
    try:
        ko = obj.overview_ko  # OneToOne reverse → 추가 쿼리
```

- **권장 수정**: view에서 `select_related('overview_ko')`

#### 3.7 [MED / 중간] users/serializers.py:15 — PrivateUserSerializer.favorite_stock

```python
favorite_stock = StockListingField(many=True, read_only=True)
```

- **문제**: User 직렬화 시 favorite_stock M2M reverse가 prefetch 없이 로드됨
- **권장 수정**: User 조회 시 `prefetch_related('favorite_stock')` 추가

#### 3.8 [MED / 쉬움] news/api/serializers.py:19 — NewsEntitySerializer.highlights

```python
highlights = EntityHighlightSerializer(many=True, read_only=True)
```

- **문제**: NewsArticle → entities (prefetch OK) → highlights (prefetch 누락 의심)
- **권장 수정**: view에서 `prefetch_related('entities__highlights')`로 체인 확장

#### ✅ Serializer Prefetch 적용 확인 완료

- `rag_analysis/serializers.py:27` (DataBasket.items) — view에서 prefetch OK
- `rag_analysis/serializers.py:68-73` (AnalysisSession.messages, basket) — view에서 prefetch + select_related OK
- `users/serializers.py:278` (Watchlist.items) — view에서 `prefetch_related('items__stock')` OK
- `news/api/serializers.py:69` (NewsArticle.entities) — view에서 prefetch OK
- `users/serializers.py:103` (PortfolioDetail.portfolio_weight) — context로 사전 계산 OK

---

### 4. 페이지네이션 누락

#### 4.1 [HIGH] 글로벌 설정 부재

**파일**: `config/settings.py:341-349` REST_FRAMEWORK
- **문제**: `DEFAULT_PAGINATION_CLASS` 미설정 → 모든 list 응답이 한번에 전체 반환 가능
- **권장 수정**:
  ```python
  REST_FRAMEWORK = {
      ...
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 20,
  }
  ```

#### 4.2 [HIGH] 주요 list 엔드포인트 (5개)

| # | 파일:라인 | 클래스 | 문제 | 수정 난이도 |
|---|----------|--------|------|-------------|
| 1 | stocks/views.py:75 | `StockListAPIView` | ListAPIView 상속, `pagination_class` 미설정 | 쉬움 |
| 2 | stocks/views_exchange.py:247 | `SectorPerformanceView` | 배열 직접 반환, 제한 없음 | 중간 |
| 3 | stocks/views_screener.py:27 | `StockScreenerView` | FMP 결과 직접 반환, limit 무제한 | 중간 |
| 4 | news/api/views.py:42 | `NewsViewSet` | ViewSet `pagination_class` 미설정 | 쉬움 |
| 5 | news/api/views.py:54 | `stock_news()` 액션 | 종목별 articles 무제한 반환 | 쉬움 |

**권장 수정 예시 (StockListAPIView)**:
```python
from rest_framework.pagination import PageNumberPagination

class StockListAPIView(ListAPIView):
    pagination_class = PageNumberPagination
    ...
```

#### 4.3 [MED] 중간 우선순위 (37개)

대표 사례:
- `stocks/views_screener.py`: LargeCap, HighDividend, Sector, LowBeta, Exchange (5개)
- `stocks/views_fundamentals.py`: KeyMetrics, Ratios, AllFundamentals (3개)
- `stocks/views_indicators.py`: TechnicalIndicator, IndicatorComparison (2개)
- `users/views.py`: Users.get(), PortfolioListCreate, PortfolioDetailTable, UserInterestList (4개)
- `rag_analysis/views.py`: DataBasketListCreate, AnalysisSessionListCreate, SessionMessages (3개)
- `chainsight/api/views.py`: SeedList, SectorGraph, NeighborGraph (3개)
- `validation/api/views.py`: ValidationMetrics, LeaderComparison (2개)
- `macro/views.py`: EconomicCalendar, SectorPerformance (2개)
- `serverless/views_admin.py`: AdminTaskLogs, AdminNewsCategory (2개)
- 기타 11개

전체 목록은 위 페이지네이션 감사 섹션 참조.

#### ✅ 페이지네이션 구현 완료 (수동)

- `users/views.py:580` (WatchlistListCreateView) — 수동 Paginator
- `users/views.py:792` (WatchlistStocksView) — 수동 Paginator
- `rag_analysis/views.py:764` (UsageHistoryView) — 수동 Paginator
- `chainsight/api/views.py:618` (SignalFeedView) — 수동 페이지네이션

> **주의**: 글로벌 설정 추가 시 위 4개 수동 구현과 충돌 가능성 검토 필요 (대부분 view-level이 글로벌보다 우선이라 문제 없음)

---

## 권장 수정 우선순위

### P0 (즉시 — 1~2시간)
1. `config/settings.py`에 글로벌 페이지네이션 설정
2. `stocks/views_indicators.py:324` IndicatorComparisonView bulk 조회로 변경
3. `news/api/views.py` NewsViewSet에 `pagination_class` 추가

### P1 (단기 — 1일)
4. `stocks/serializers.py:398, 405` — view에서 Prefetch 적용
5. `stocks/serializers.py:205` — view에서 select_related 6개 + prefetch_related 1개 추가
6. `stocks/views.py:75` `StockListAPIView`에 pagination_class 추가
7. `serverless/serializers.py:121-137` — IndicatorCalculator 모듈 레벨 캐싱
8. `serverless/models.py:VolatilityBaseline.date`, `sec_pipeline/models.py:UnmatchedCompanyQueue.raw_company_name` — db_index 추가 + migration

### P2 (중기 — 1주)
9. MED 페이지네이션 37개 일괄 적용 (글로벌 설정으로 자동 커버되는 것이 다수)
10. `serverless/views_admin.py:475` resolve_symbols() 패턴 검토
11. `news/api/serializers.py:19` highlights 체인 prefetch
12. `users/serializers.py:15` favorite_stock prefetch

### P3 (장기 — 유지보수)
13. 재무제표 복합 인덱스 검토
14. UsageLog, AlertLog 등 인덱스 추가 검토
15. APIView vs ViewSet 일관성 통일 (수동 페이지네이션 → DRF 표준)

---

## 보고 한계

- **메서드 본체 미확인**: `cat.resolve_symbols()` 등 일부 모델 메서드의 내부 쿼리는 추가 검토 필요
- **실제 트래픽 데이터 부재**: HIGH/MED 분류는 코드 패턴 기반 추정. APM(예: Django Debug Toolbar, silk)으로 실측 권장
- **마이그레이션 영향**: 인덱스 추가 시 큰 테이블(NewsArticle, DailyPrice 등)은 잠금 시간 고려 필요

---

**Stop / Pause 지점**: P0 항목 완료 후 실측 (Silk 또는 Debug Toolbar)로 효과 검증 → P1 진행 여부 결정 권장
