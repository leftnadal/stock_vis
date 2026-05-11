# API 성능 감사 보고서

생성일: 2026-05-03
대상: Stock-Vis Backend (Django/DRF)

---

## 요약

| 심각도 | 개수 |
|--------|------|
| HIGH   | 6    |
| MED    | 7    |
| LOW    | 4    |

| 카테고리          | 개수 |
|-------------------|------|
| N+1 쿼리          | 5    |
| 인덱스 누락       | 4    |
| 느린 Serializer   | 4    |
| 페이지네이션 누락 | 4    |

---

## 상세

---

### N+1 쿼리

---

### [HIGH] N+1 쿼리 — StockMVPListView summary 루프
- **파일**: `stocks/views_mvp.py:46`
- **수정 난이도**: 쉬움
- **현상**: `for stock in queryset:` 루프 안에서 `stock.real_time_price`, `stock.change`, `stock.change_percent`, `stock.market_capitalization`, `stock.sector` 등 Stock 인스턴스 필드를 직접 접근하며 딕셔너리를 구성한다. `queryset = Stock.objects.all()` (line 29) 에 대해 `queryset[:20]`로 슬라이스된 후, 루프가 20회 반복된다.
- **설명**: `queryset`은 `Stock.objects.all()` 원시 쿼리셋으로, 슬라이스 후 이터레이션 시점에 단일 SELECT 쿼리가 발행된다. 현재 구조상 Stock 필드 접근은 N+1이 아니라 1+0이지만, 동일 뷰의 `StockMVPDetailView.get()`(line 114~126)에서 `IncomeStatement.objects.filter(stock=stock, ...).first()`가 매 요청마다 발행되며, Stock 객체가 이미 메모리에 있음에도 매 detail 호출마다 별도 쿼리가 추가된다. 더 큰 문제는 `StockListAPIView`(views.py:83)가 `Stock.objects.all()`을 반환하면서 **페이지네이션 미적용**으로 전체 테이블을 메모리에 올린다는 것이다 (하단 페이지네이션 항목에서 상세 기술).
- **권장 수정**: `StockMVPListView`는 `only()` 또는 `values()`로 필요한 컬럼만 조회. `StockMVPDetailView`는 view 레벨에서 `select_related` 또는 `prefetch_related`로 IncomeStatement를 사전 로드.

---

### [HIGH] N+1 쿼리 — IndicatorComparisonView 심볼 루프
- **파일**: `stocks/views_indicators.py:324`
- **수정 난이도**: 중간
- **현상**: `for symbol in symbols:` 루프(line 324) 안에서 `Stock.objects.get(symbol=symbol)`(line 328)와 `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]`(line 333)가 각각 호출된다. symbols 개수 N에 대해 2N개의 DB 쿼리가 발행된다.
- **설명**: 요청당 최대 symbols 수가 명시적으로 제한되지 않아 대량 요청 시 DB 부하가 급증한다. 예: 20개 심볼 → 40개 쿼리.
- **권장 수정**: `Stock.objects.filter(symbol__in=symbols)` 로 1회 쿼리, `DailyPrice.objects.filter(stock__symbol__in=symbols).order_by('stock', '-date')` 로 1회 쿼리 후 Python에서 그룹화. 또는 `prefetch_related`와 `Prefetch` 객체 활용.

---

### [HIGH] N+1 쿼리 — news trending 액션 루프
- **파일**: `news/api/views.py:331`
- **수정 난이도**: 중간
- **현상**: `for item in trending_data:` 루프(line 331) 안에서 `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')[:3]`(line 333)가 심볼별로 호출된다. trending_data의 크기(최대 limit=10)만큼 추가 쿼리가 발행된다.
- **설명**: trending_data 집계(line 322) 이후 각 심볼에 대해 1개 쿼리가 추가되므로, 기본 limit=10 기준 10개의 추가 SELECT가 발행된다.
- **권장 수정**: `NewsArticle.objects.filter(entities__symbol__in=top_symbols, ...).prefetch_related('entities')` 로 1회 쿼리 후 Python에서 심볼별 그룹화. 또는 집계 결과를 재사용하는 서브쿼리 구조로 전환.

---

### [MED] N+1 쿼리 — WatchlistBulkAddView 루프
- **파일**: `users/views.py:872`
- **수정 난이도**: 쉬움
- **현상**: `for symbol in symbols:` 루프(line 872) 안에서 `Stock.objects.get(symbol=symbol.upper())`(line 875)가 호출된다. symbols 개수 N만큼 SELECT 쿼리가 발행된다.
- **설명**: bulk 추가임에도 Stock 조회가 N회 발행된다.
- **권장 수정**: 루프 진입 전 `Stock.objects.filter(symbol__in=[s.upper() for s in symbols])` 로 심볼 매핑 딕셔너리를 구성한 뒤 루프에서 딕셔너리 조회.

---

### [MED] N+1 쿼리 — WatchlistBulkRemoveView 루프
- **파일**: `users/views.py:937`
- **수정 난이도**: 쉬움
- **현상**: `for symbol in symbols:` 루프(line 937) 안에서 `WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())`(line 939)가 각 심볼마다 호출된다.
- **설명**: N개의 심볼 제거 시 N개의 SELECT + N개의 DELETE가 발행된다.
- **권장 수정**: `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=[...]).delete()` 로 1회 DELETE로 처리.

---

### 인덱스 누락

---

### [HIGH] 인덱스 누락 — NewsEntity.symbol 필드
- **파일**: `news/models.py`
- **수정 난이도**: 쉬움
- **현상**: `news/api/views.py:89` 의 `NewsArticle.objects.filter(entities__symbol=symbol, ...)` 및 line 322의 `NewsEntity.objects.filter(...).values('symbol').annotate(...)` 에서 `NewsEntity.symbol` 필드가 WHERE 조건으로 빈번하게 사용된다. `NewsEntity` 모델에서 `symbol` 필드의 인덱스를 확인하려면 `news/models.py`를 추가 확인해야 하나, `NewsArticle` 모델(line 190~198)의 Meta.indexes에는 `symbol` 관련 인덱스가 없다.
- **설명**: 종목별 뉴스 조회는 가장 빈번한 API 패턴이므로 `NewsEntity.symbol` 인덱스가 없으면 full scan이 발생한다.
- **권장 수정**: `NewsEntity` 모델에 `db_index=True` 추가 또는 `Meta.indexes`에 `models.Index(fields=['symbol', '-published_at'])` 추가 (뉴스 날짜와 복합 인덱스).

---

### [MED] 인덱스 누락 — BalanceSheet, IncomeStatement, CashFlowStatement의 (stock, period_type, fiscal_year) 복합 조회
- **파일**: `stocks/views.py:635`, `stocks/views.py:710`, `stocks/views.py:782`
- **수정 난이도**: 쉬움
- **현상**: 세 재무제표 뷰 모두 `.filter(stock=stock, period_type=db_period).order_by('-fiscal_year', '-fiscal_quarter')` 패턴을 사용한다.
- **설명**: `stocks/models.py`의 `Stock` 모델에는 `sector`, `industry`, `market_capitalization` 등에 인덱스가 있으나, `BalanceSheet`, `IncomeStatement`, `CashFlowStatement` 모델의 `(stock, period_type, fiscal_year)` 복합 인덱스 여부를 확인해야 한다. 없을 경우 재무제표 조회마다 `period_type` 필터링 시 full scan이 발생할 수 있다.
- **권장 수정**: 각 재무제표 모델 `Meta.indexes`에 `models.Index(fields=['stock', 'period_type', '-fiscal_year'])` 추가.

---

### [MED] 인덱스 누락 — UserInterest 사용자별 조회
- **파일**: `users/views.py:966`
- **수정 난이도**: 쉬움
- **현상**: `UserInterest.objects.filter(user=request.user).order_by('-created_at')` 패턴이 GET/POST에서 반복 사용된다. UserInterest 모델에 `(user, created_at)` 복합 인덱스가 없으면 사용자별 조회마다 full scan이 발생한다.
- **설명**: 사용자 관심사 목록은 자주 조회되는 경로이므로 인덱스 부재 시 성능 저하가 누적된다.
- **권장 수정**: `UserInterest.Meta.indexes`에 `models.Index(fields=['user', '-created_at'])` 추가.

---

### [LOW] 인덱스 누락 — EODSignal.signals JSONField contains 조회
- **파일**: `stocks/views_eod.py:72`
- **수정 난이도**: 높음
- **현상**: `EODSignal.objects.filter(date=target_date, signals__contains=[{'id': signal_id}])` 에서 JSONField `signals`에 `__contains` 조회를 사용한다.
- **설명**: PostgreSQL의 `@>` 연산자를 사용하는 JSON contains 조회는 GIN 인덱스 없이는 full scan이 된다. 14개 신호 타입 × 날짜별 조회가 빈번할 경우 성능 문제가 될 수 있다.
- **권장 수정**: `EODSignal` 모델에 `signals` JSONField에 대한 GIN 인덱스 추가: `GinIndex(fields=['signals'])`. 또는 신호 타입을 별도 필드나 M2M으로 분리하는 구조적 개선 검토.

---

### 느린 Serializer

---

### [HIGH] 느린 Serializer — OverviewTabSerializer.get_dynamic_layers 다중 쿼리
- **파일**: `stocks/serializers.py:205`
- **수정 난이도**: 중간
- **현상**: `get_dynamic_layers` 메서드(line 205)가 `obj.category_signals.all()`(lazy FK reverse, line 215), `obj.validation_news_summary`(OneToOne 접근, line 234), `obj.sensitivity_profile`(line 251), `obj.growth_stage`(line 266), `obj.capital_dna`(line 279), `obj.narrative_tag`(line 293)를 각각 개별 접근한다. 각 접근마다 별도 DB 쿼리가 발행된다.
- **설명**: `StockOverviewAPIView`에서 `Stock.objects.select_related('overview_ko')` 만 수행하고(views.py:493), `category_signals` prefetch 없이 Overview 직렬화를 호출하면 한 번의 Overview API 요청당 최대 6개의 추가 쿼리가 발행된다. 코드 주석(serializers.py:208)에도 `# TODO: Step 2~4에서 데이터 유입 시 prefetch_related + 캐싱 레이어 적용 필요`로 명시되어 있다.
- **권장 수정**: `StockOverviewAPIView.get()`에서 `Stock.objects.select_related('overview_ko', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag').prefetch_related('category_signals')` 로 변경. 캐시 TTL 내에서는 이미 캐시로 보호되지만 cache miss 시 문제가 발생한다.

---

### [MED] 느린 Serializer — DataBasketSerializer.get_can_add_item 추가 쿼리
- **파일**: `rag_analysis/serializers.py:46`
- **수정 난이도**: 쉬움
- **현상**: `get_can_add_item`(line 46)이 `obj.can_add_item()`을 호출하고, `can_add_item`(models.py:37)은 `self.items.count()`를 실행한다. `DataBasketListCreateView`(views.py:73)에서 `DataBasket.objects.filter(user=request.user).prefetch_related('items')`를 사용하지만, `.count()`는 prefetch 캐시를 우회하여 별도 COUNT 쿼리를 발행한다.
- **설명**: 바구니 목록 조회 시 바구니 N개에 대해 N개의 추가 COUNT 쿼리가 발행된다.
- **권장 수정**: `can_add_item` 메서드를 `self.items.all()` prefetch 결과를 활용하도록 변경하거나, serializer에서 `len(obj.items.all()) < obj.MAX_ITEMS` 로 직접 계산 (prefetch 캐시 활용).

---

### [MED] 느린 Serializer — PortfolioSummaryView Python 루프 집계
- **파일**: `users/views.py:367`
- **수정 난이도**: 쉬움
- **현상**: `for portfolio in portfolios:` 루프(line 367)에서 `portfolio.total_value`와 `portfolio.total_cost`를 합산한다. `total_value`는 `float(self.quantity) * float(self.stock.real_time_price)`(models.py:83)이므로 `stock.real_time_price` 접근이 루프마다 발생한다. `select_related('stock')`(line 351)이 적용되어 N+1은 아니지만, DB 집계 가능한 연산을 Python에서 수행한다.
- **설명**: `Sum(F('quantity') * F('stock__real_time_price'))` 단일 집계 쿼리로 처리 가능한 연산을 Python 루프로 처리한다.
- **권장 수정**: `Portfolio.objects.filter(user=request.user).aggregate(total_value=Sum(F('quantity') * F('stock__real_time_price')), total_cost=Sum(F('quantity') * F('average_price')))` 로 DB 집계 쿼리 1회로 처리.

---

### [LOW] 느린 Serializer — OverviewTabSerializer.get_korean_overview try/except 방어코드 과다
- **파일**: `stocks/serializers.py:190`
- **수정 난이도**: 쉬움
- **현상**: `get_korean_overview`(line 190)가 `obj.overview_ko`(OneToOne 역참조)를 `try/except` 블록 안에서 접근한다. `select_related('overview_ko')`가 적용되어 있어 쿼리 문제는 없으나, `overview_ko`가 없을 때 `DoesNotExist` 예외를 `Exception`으로 전부 묻는다.
- **설명**: 직접적인 성능 이슈는 아니나, 예외를 통한 제어 흐름이 성능 프로파일링을 어렵게 하고, `getattr(obj, 'overview_ko', None)` 패턴이 더 명확하다.
- **권장 수정**: `if hasattr(obj, 'overview_ko') and obj.overview_ko is not None:` 분기 또는 `getattr(obj, 'overview_ko', None)` 사용.

---

### 페이지네이션 누락

---

### [HIGH] 페이지네이션 누락 — StockListAPIView
- **파일**: `stocks/views.py:75`
- **수정 난이도**: 쉬움
- **현상**: `StockListAPIView(generics.ListAPIView)`에 `pagination_class`가 설정되지 않았고, `settings.py`의 `REST_FRAMEWORK`에도 `DEFAULT_PAGINATION_CLASS`가 없다. `get_queryset()`(line 83)이 `Stock.objects.all()` 전체를 반환하므로, 현재 Stock 레코드 수만큼 전체 행이 API 응답으로 직렬화된다.
- **설명**: S&P 500 등 수백~수천 건의 Stock 레코드가 있을 경우 단일 요청으로 전체 테이블이 직렬화되어 응답 크기와 처리 시간이 선형 증가한다.
- **권장 수정**: `StockListAPIView`에 `pagination_class = PageNumberPagination` (또는 커스텀 페이지네이터) 추가. 또는 `settings.REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`와 `PAGE_SIZE` 전역 설정.

---

### [HIGH] 페이지네이션 누락 — Users.get (관리자 사용자 목록)
- **파일**: `users/views.py:90`
- **수정 난이도**: 쉬움
- **현상**: `Users.get()`(line 90)이 `User.objects.all()`을 반환하며 페이지네이션이 없다.
- **설명**: 관리자 전용이지만 사용자 수가 증가할 경우 전체 목록이 반환된다.
- **권장 수정**: 페이지네이터 적용 또는 `[:limit]` 슬라이스 추가.

---

### [MED] 페이지네이션 누락 — NewsViewSet 기본 queryset
- **파일**: `news/api/views.py:45`
- **수정 난이도**: 쉬움
- **현상**: `NewsViewSet`의 기본 `queryset = NewsArticle.objects.all().prefetch_related('entities')`(line 45)에 페이지네이션이 명시적으로 설정되어 있지 않다. DRF ViewSet의 `list` 액션은 `DEFAULT_PAGINATION_CLASS` 설정이 없으면 전체 레코드를 반환한다. `settings.py`에 `DEFAULT_PAGINATION_CLASS`가 없다.
- **설명**: 뉴스 데이터는 지속적으로 누적되므로 시간이 지날수록 `/api/v1/news/` list 엔드포인트의 부하가 증가한다.
- **권장 수정**: `NewsViewSet`에 `pagination_class` 명시 또는 전역 `DEFAULT_PAGINATION_CLASS` 설정.

---

### [MED] 페이지네이션 누락 — ValidationSummaryView 관련 쿼리셋 노출
- **파일**: `validation/api/views.py:80`
- **수정 난이도**: 중간
- **현상**: `CategorySignal.objects.filter(symbol=stock).order_by('category')` (line 80)는 단일 종목의 카테고리 신호를 조회하므로 레코드 수가 제한적이다. 그러나 `CompanyBenchmarkDelta.objects.filter(symbol=stock, ...)` (line 113) 루프에서 `rank_metrics` 5개에 대해 각각 개별 쿼리가 발행된다.
- **설명**: 5개의 지표에 대해 5개의 개별 SELECT가 발행된다. 직접적인 페이지네이션 이슈는 아니나, 루프 내 개별 쿼리는 N+1에 해당한다.
- **권장 수정**: `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics)` 로 1회 쿼리 후 Python에서 딕셔너리 매핑.

---

## 우선순위 액션 아이템

| 우선순위 | 항목 | 파일 | 담당 |
|---------|------|------|------|
| HIGH | StockListAPIView 페이지네이션 추가 | `stocks/views.py:75` | @backend |
| HIGH | OverviewTabSerializer get_dynamic_layers select_related/prefetch 적용 | `stocks/serializers.py:205`, `stocks/views.py:493` | @backend |
| HIGH | IndicatorComparisonView 심볼 루프 N+1 수정 | `stocks/views_indicators.py:324` | @backend |
| HIGH | news trending 루프 N+1 수정 | `news/api/views.py:331` | @backend |
| HIGH | NewsViewSet 페이지네이션 추가 | `news/api/views.py:45` | @backend |
| MED | WatchlistBulkAddView/RemoveView 루프 N+1 수정 | `users/views.py:872`, `users/views.py:937` | @backend |
| MED | PortfolioSummaryView DB 집계로 전환 | `users/views.py:367` | @backend |
| MED | ValidationSummaryView rank 쿼리 1회로 통합 | `validation/api/views.py:113` | @backend |
| MED | 재무제표 모델 (stock, period_type, fiscal_year) 복합 인덱스 추가 | `stocks/models.py` | @backend |
| LOW | EODSignal.signals JSONField GIN 인덱스 추가 | `stocks/models.py` | @backend |
| LOW | UserInterest (user, created_at) 인덱스 추가 | `users/models.py` | @backend |
