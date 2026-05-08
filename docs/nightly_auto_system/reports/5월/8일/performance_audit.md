# API 성능 감사 보고서

- 감사 대상: views 17개 + serializers 8개 + models 8개
- 일자: 2026-05-08
- 도구: 정적 분석 (Grep + Read), 코드 수정 없음

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 건수 | 분류 |
|--------|------|------|
| **HIGH** | 7 | N+1 (4) · 인덱스/페이지네이션 (3) |
| **MED** | 7 | N+1 (4) · 페이지네이션 (1) · 인덱스 (2) |
| **LOW** | 5 | 인덱스 (4) · 효율 (1) |
| **합계** | **19** | — |

**가장 시급한 결함 (한 줄 요약)**

1. `config/settings.py:348` — `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`가 비어있어 모든 list 엔드포인트가 무제한 응답 가능 (HIGH).
2. `rag_analysis/serializers.py:24-50` — `DataBasketSerializer`가 객체 1개당 4개의 추가 쿼리(`items.count()` + `aggregate(Sum)` × 2 + `count()`)를 발생시킴 (HIGH).
3. `stocks/serializers.py:205-307` — `OverviewTabSerializer.get_dynamic_layers`가 6개 OneToOne/Reverse FK를 prefetch 없이 접근, 종목 상세 페이지마다 6쿼리 추가 (HIGH).
4. `validation/api/views.py:112-285,353-371` — Validation 3개 View가 카테고리/지표별 루프 안에서 매번 `MetricDefinition`, `CompanyBenchmarkDelta`, `PeerMetricBenchmark` 등을 단건 조회 (HIGH).

---

## 상세 (각 이슈별 파일:라인, 설명, 권장 수정)

### [HIGH-1] DEFAULT_PAGINATION_CLASS 전역 미설정 — 페이지네이션 누락

- **파일**: `config/settings.py:348-362`
- **문제**:
  - `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 키가 없음.
  - 전체 view 파일 17개 grep 결과 `pagination_class` 사용 0건.
  - DRF 기본값은 "페이지네이션 없음" → list 엔드포인트가 결과 전체를 한 번에 반환.
  - `users/views.py:599,810`은 자체 `Paginator`로 처리하고 있으나, 다른 list view들은 보호 없음.
- **영향 받는 list 엔드포인트** (대표):
  - `rag_analysis/views.py:74` `DataBasketListCreateView.get` — 사용자별 바구니 전부
  - `users/views.py:262, 974` `PortfolioListCreateView.get`, `UserInterestListCreateView.get`
  - `serverless/views_admin.py:475` `AdminNewsCategoryView.get`
  - `validation/api/views.py:421` `PresetListView.get`
  - `stocks/views_eod.py:119` `EODPipelineStatusView.get` (7건 제한 있음, 안전)
  - `news/api/views.py:282` `NewsArticle.market` (limit 파라미터 제한, 안전)
- **권장 수정**:
  - `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS = 'rest_framework.pagination.PageNumberPagination'` + `PAGE_SIZE = 20` 추가.
  - 전역 적용 시 응답 스키마가 `{count, next, previous, results}`로 바뀌어 프론트엔드와 contract 변경 발생 → 점진 도입을 위해 영향 큰 view부터 `pagination_class` 명시 권장.
- **수정 난이도**: **중간** (전역 설정 + 프론트 contract 동시 변경 필요)
- **심각도**: **HIGH**

---

### [HIGH-2] DataBasketSerializer N+1 — 객체당 4개 추가 쿼리

- **파일**: `rag_analysis/serializers.py:24-50`, `rag_analysis/models.py:36-57`
- **문제**:
  - `items` (PrefetchedItems) 외에 다음 4개 속성이 매번 별도 쿼리:
    - `items_count = IntegerField(read_only=True)` → `items.count()` (model property, line 41-42)
    - `current_units = IntegerField(read_only=True)` → `items.aggregate(Sum('data_units'))` (line 44-48)
    - `remaining_units = IntegerField(read_only=True)` → 다시 `current_units` 호출 (line 50-53)
    - `get_can_add_item(obj)` → `items.count()` 중복 호출 (line 36-38)
  - `views.py:76`에서 `prefetch_related('items')`를 적용하지만, `.count()` / `aggregate`는 prefetch 캐시를 활용하지 않고 별도 SQL 발행.
  - 사용자가 바구니 N개 보유 → **4N개 쿼리**.
- **권장 수정**:
  - View에서 `annotate(items_count=Count('items'), current_units=Coalesce(Sum('items__data_units'), 0))`로 SQL 한 번에 처리.
  - `remaining_units` / `can_add_item`은 annotation 결과를 SerializerMethodField에서 산술로 계산.
- **수정 난이도**: **쉬움**
- **심각도**: **HIGH**

---

### [HIGH-3] OverviewTabSerializer.get_dynamic_layers — 6개 OneToOne/Reverse FK 미prefetch

- **파일**: `stocks/serializers.py:205-307`
- **문제**:
  - 한 Stock 객체 직렬화마다 다음 6개 관계를 차례로 lazy load:
    - `obj.category_signals.all()` (Reverse FK)
    - `obj.validation_news_summary` (OneToOne)
    - `obj.sensitivity_profile` (OneToOne)
    - `obj.growth_stage` (OneToOne)
    - `obj.capital_dna` (OneToOne)
    - `obj.narrative_tag` (OneToOne)
  - 추가로 line 190-203 `get_korean_overview`가 `obj.overview_ko` (OneToOne) 또 1쿼리.
  - 코드에 `# TODO: prefetch_related + 캐싱 레이어 적용 필요` 주석으로 본인이 인지하고 있음.
  - 단건 상세는 +7쿼리, list 사용 시 N×7 N+1.
- **권장 수정**:
  - `Stock.objects.select_related('overview_ko','validation_news_summary','sensitivity_profile','growth_stage','capital_dna','narrative_tag').prefetch_related('category_signals')`
  - View(`stocks/views.py:461 StockOverviewAPIView`)에서 단건 조회 시도 적용.
- **수정 난이도**: **쉬움**
- **심각도**: **HIGH**

---

### [HIGH-4] WatchListStockSerializer — get_latest_price + get_chart_data 각각 별도 쿼리

- **파일**: `stocks/serializers.py:381-411`
- **문제**:
  - `get_latest_price(obj)`: `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` — 종목당 1쿼리
  - `get_chart_data(obj)`: `DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]` — 종목당 1쿼리
  - watchlist에 종목 N개 → 2N 쿼리.
- **권장 수정**:
  - `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7], to_attr='recent_prices')`로 한 번에 조회.
  - serializer는 `obj.recent_prices` 리스트에서 슬라이스만 사용.
- **수정 난이도**: **중간** (Prefetch 객체 작성 + 슬라이스 조정)
- **심각도**: **HIGH**

---

### [HIGH-5] ValidationSummaryView/MetricsView/LeaderComparisonView 다중 N+1

- **파일**: `validation/api/views.py`
- **문제 위치 1**: `ValidationSummaryView` — `lines 112-124`
  ```python
  for mc in rank_metrics:                         # 5회
      delta = CompanyBenchmarkDelta.objects.filter(...).first()
      md    = MetricDefinition.objects.filter(pk=mc).first()
  ```
  → 지표 5개 × 2쿼리 = 10쿼리
- **문제 위치 2**: `ValidationMetricsView._build_category` — `lines 192-208`
  ```python
  for cat in categories:           # 카테고리 6개
      for mc in metric_codes:      # 카테고리당 평균 5개
          md = MetricDefinition.objects.filter(pk=mc).first()
          ...
  ```
  → 6×5 = 30+ 단건 조회 + 내부 `_build_metric`이 추가 쿼리(`CompanyMetricSnapshot`, `CompanyBenchmarkDelta`, `PeerMetricBenchmark` 각 1회)
- **문제 위치 3**: `_build_metric` — `lines 264-285` 히스토리 루프 내 `PeerMetricBenchmark.filter(...).first()` — 5년치 → 5쿼리 per metric
- **문제 위치 4**: `LeaderComparisonView` — `lines 353-371`
  ```python
  for cat, codes in CATEGORY_METRICS.items():
      for mc in codes:
          all_metrics.append(...)
  for cat, mc in all_metrics:                                    # ~30개
      md = MetricDefinition.objects.filter(pk=mc).first()
      company_snap = CompanyMetricSnapshot.objects.filter(...)
      leader_snap  = CompanyMetricSnapshot.objects.filter(...)
  ```
  → 지표당 3쿼리 × ~30 = ~90쿼리
- **권장 수정**:
  - `MetricDefinition.objects.in_bulk(metric_codes)`로 한 번에 dict 조회.
  - `CompanyBenchmarkDelta`, `CompanyMetricSnapshot`, `PeerMetricBenchmark`도 `filter(metric_code__in=[...]).select_related('metric_code')` 후 dict 그루핑.
  - `_build_metric`의 history 루프는 `PeerMetricBenchmark.objects.filter(symbol, metric_code, fiscal_year__in=[...])` 하나로.
- **수정 난이도**: **중간** (계산 로직 변경 필요)
- **심각도**: **HIGH**

---

### [HIGH-6] IndicatorComparisonView — symbols 루프 내 Stock + DailyPrice 단건 조회

- **파일**: `stocks/views_indicators.py:300-371` (특히 lines 324-335)
- **문제**:
  - `for symbol in symbols:` (요청에서 N개 받음) 안에서:
    - `Stock.objects.get(symbol=symbol)` — 1쿼리
    - `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]` — 1쿼리
  - 총 2N 쿼리. symbols 길이 제한 코드도 없음.
- **권장 수정**:
  - `stocks = Stock.objects.filter(symbol__in=upper_symbols).in_bulk(field_name='symbol')` 한 번 조회.
  - `DailyPrice.objects.filter(stock__symbol__in=upper_symbols, date__gte=...)` 후 Python 측에서 그루핑.
  - symbols 길이 상한(예: 10) 설정.
- **수정 난이도**: **쉬움**
- **심각도**: **HIGH**

---

### [HIGH-7] WatchlistSerializer.stock_count — list 응답 시 N+1

- **파일**: `users/serializers.py:231-238`, `users/models.py:187-190`, `users/views.py:599`
- **문제**:
  - `WatchlistSerializer`가 `stock_count = ReadOnlyField()`로 `Watchlist.stock_count` property를 노출.
  - `stock_count` property는 `self.items.count()` (models.py:190).
  - `WatchlistListCreateView.get`은 `Watchlist.objects.filter(user=...)` (line 599)에 prefetch/annotate 없음.
  - 사용자가 watchlist N개 보유 → N쿼리 추가.
- **권장 수정**:
  - View 쿼리셋에 `.annotate(stock_count_db=Count('items'))` + serializer에서 `IntegerField(source='stock_count_db')` 사용.
- **수정 난이도**: **쉬움**
- **심각도**: **HIGH**

---

### [MED-1] NewsViewSet — class queryset의 prefetch_related가 액션 메서드에서 풀림

- **파일**: `news/api/views.py:50, 95-104, 277-282`
- **문제**:
  - `class NewsViewSet`은 `queryset = NewsArticle.objects.all().prefetch_related('entities')`로 정의.
  - 그러나 action 메서드 `stock_news`(line 95)와 `market`(line 277)이 새 쿼리셋을 직접 만들어 prefetch_related가 누락됨.
  - 응답 직렬화 시 `NewsArticleListSerializer`/`DetailSerializer`가 `entities` 접근 → 기사당 1쿼리(N+1).
- **권장 수정**:
  - 두 액션 모두 `.prefetch_related('entities')` 추가:
    ```python
    NewsArticle.objects.filter(...).prefetch_related('entities').order_by('-published_at')
    ```
- **수정 난이도**: **쉬움**
- **심각도**: **MED**

---

### [MED-2] AdminNewsCategoryView — categories 루프에서 resolve_symbols() per row

- **파일**: `serverless/views_admin.py:475-500`
- **문제**:
  - `categories = NewsCollectionCategory.objects.all()` 이후 루프에서 `cat.resolve_symbols()` 호출.
  - `resolve_symbols()`는 sector/sub_sector 타입에서 `SP500Constituent.objects.filter(...)` 쿼리 발생 가능 → N+1.
- **권장 수정**:
  - 카테고리들을 type별로 그루핑 → 각 sector 값을 `__in` 절로 일괄 조회 후 메모리 매핑.
  - 또는 캐싱(섹터→symbols 맵 5분) 적용.
- **수정 난이도**: **중간** (캐싱 도입 시)
- **심각도**: **MED**

---

### [MED-3] StockChartDataAPIView — count() 중복 호출

- **파일**: `stocks/views.py:274, 280`
- **문제**:
  - `if price_data.count() > 0:` (line 274) — count() 1회
  - `'count': price_data.count(),` (line 280) — 같은 쿼리셋 count() 또 1회
  - serializer.data 생성 시 iterate → 총 3회 DB 접근(count×2 + select).
- **권장 수정**:
  - `data_list = list(price_data)` 먼저 → `len(data_list)` 사용.
- **수정 난이도**: **쉬움**
- **심각도**: **MED**

---

### [MED-4] PortfolioSummaryView / PortfolioDetailTableView — 파이썬 측 sum/count

- **파일**: `users/views.py:374-388, 408-432`
- **문제**:
  - `select_related('stock')`은 적용되었지만 `total_value`, `total_cost`가 model property(`real_time_price` 활용)이라 DB aggregate가 아닌 Python 루프 sum.
  - `portfolios.count()` 별도 쿼리 발생 (queryset도 다시 평가됨).
  - 종목 다량 보유 시 직렬화 + 합산이 서버 메모리에서 진행 → 응답 느려짐.
- **권장 수정**:
  - DB 측 `annotate(line_total=F('quantity')*F('stock__real_time_price'))` + `aggregate(Sum)` 검토 (단, `change_percent`가 문자열이라 일부는 Python 처리 불가피).
  - 최소한 `count()` 대신 `len(portfolios)` 사용 (이미 evaluation 됨).
- **수정 난이도**: **중간**
- **심각도**: **MED**

---

### [MED-5] StockScreenerView 클라이언트 사이드 필터 — 응답 후 메모리 필터

- **파일**: `stocks/views_screener.py:216-240`
- **문제**:
  - FMP API 응답을 `_apply_client_filters`로 Python 루프 필터(`change_percent_min/max`).
  - FMP가 해당 필터를 지원하지 않으니 어쩔 수 없으나, 결과 수가 큰 경우 메모리/CPU 부담.
- **권장 수정**:
  - FMP 호출 시 limit을 충분히 줄여 받거나, 클라이언트 측에서 필터링.
  - `change_percent_min/max`가 None일 때 최적 패스(이미 있음).
- **수정 난이도**: **낮음** (외부 API 종속)
- **심각도**: **MED**

---

### [MED-6] DataBasket 등 rag_analysis 모델 — 인덱스 누락

- **파일**: `rag_analysis/models.py`
- **문제**:
  - `DataBasket` (line 11): user FK + `ordering = ['-updated_at']`. `(user, -updated_at)` 복합 인덱스 없음 → 사용자별 목록 조회 시 풀스캔.
  - `BasketItem` (line 60): `(basket, item_type, reference_id)` unique이지만, 자주 쓰는 `basket` 단독 필터 인덱스만 자동 생성, ordering(`created_at`)에 따른 복합 부재.
  - `AnalysisSession` (line 130): user/basket FK + `ordering=['-updated_at']`. `(user, -updated_at)` 인덱스 없음.
  - `AnalysisMessage` (line 184): session FK + `ordering=['created_at']`. `(session, created_at)` 복합 부재.
- **권장 수정**:
  - 각 모델 Meta에 `indexes = [models.Index(fields=['user','-updated_at'])]` 등 추가. UsageLog(line 335-340)는 이미 모범 사례로 적용되어 있음.
- **수정 난이도**: **쉬움** (마이그레이션 1개)
- **심각도**: **MED**

---

### [MED-7] users/views.py WatchlistBulkAddView — 루프 내 3쿼리/심볼

- **파일**: `users/views.py:880-903, 945-952`
- **문제**:
  - `for symbol in symbols:` 안에 `Stock.objects.get(symbol=symbol.upper())` + `WatchlistItem.objects.filter(...).exists()` + `WatchlistItem.objects.create(...)` — 종목 N개에 대해 3N 쿼리.
- **권장 수정**:
  - `stocks = Stock.objects.filter(symbol__in=upper_symbols).in_bulk(field_name='symbol')`
  - 기존 `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=upper_symbols).values_list('stock__symbol', flat=True)` 한 번 호출 → set으로 중복 검사.
  - `bulk_create([...])` 사용.
- **수정 난이도**: **중간** (트랜잭션·serializer 호환 필요)
- **심각도**: **MED**

---

### [LOW-1] sec_pipeline 일부 모델 — 인덱스 누락

- **파일**: `sec_pipeline/models.py`
- **문제**:
  - `BusinessModelEvidence` (line 201): Meta `indexes` 없음. `snapshot` FK는 자동 인덱스이나 `field_name` 단독 필터 인덱스 없음.
  - `CompanyAlias` (line 273): `unique_together=('alias','context_sector')`만 있어 prefix 인덱스로 활용. `ticker` 역방향 검색 인덱스 없음.
  - `PipelineIntelligenceReport` (line 351): `report_date` 인덱스 명시 없음 (ordering이 있어 정렬은 가능하나 필터 인덱스는 별개).
- **권장 수정**:
  - 각각 `models.Index(fields=['snapshot','field_name'])`, `models.Index(fields=['ticker'])`, `models.Index(fields=['-report_date'])` 추가 (조회 패턴에 따라 선택).
- **수정 난이도**: **쉬움**
- **심각도**: **LOW**

---

### [LOW-2] users/models.py UserInterest — Meta indexes 부재

- **파일**: `users/models.py:249-268`
- **문제**:
  - `unique_together=('user','interest_type','value')`는 있지만, `views.py:975`의 정렬 키 `(user, -created_at)` 복합 인덱스 부재.
- **권장 수정**:
  - `Meta.indexes = [models.Index(fields=['user','-created_at'])]`
- **수정 난이도**: **쉬움**
- **심각도**: **LOW**

---

### [LOW-3] graph_analysis/models.py CorrelationEdge — stock 페어 인덱스 검토

- **파일**: `graph_analysis/models.py:75-100`
- **상황**:
  - `CorrelationMatrix`는 `(watchlist, -date)` 복합 인덱스가 있어 양호.
  - `CorrelationEdge`는 stock_a, stock_b 두 FK가 있고 페어 조회 가능성 → `(stock_a, stock_b, date)` 복합 인덱스 검토 필요.
- **수정 난이도**: **쉬움**
- **심각도**: **LOW** (현재 graph_analysis API 미구현이라 영향 작음)

---

### [LOW-4] StockMVPListView — 사이즈 20 고정

- **파일**: `stocks/views_mvp.py:41, 113-125`
- **문제**:
  - `queryset = queryset[:20]` 하드코딩. limit 파라미터 미지원.
  - Detail에서 `IncomeStatement.objects.filter(stock=stock,period_type='annual').order_by('-fiscal_year').first()` 단건 추가 — N+1은 아니지만 select_related 가능.
- **권장 수정**:
  - `request.GET.get('limit', 20)` + 상한 보호.
  - Detail은 단건 호출이므로 큰 영향 없으나, prefetch가 깔끔.
- **수정 난이도**: **쉬움**
- **심각도**: **LOW**

---

### [LOW-5] StockListAPIView — sector __icontains

- **파일**: `stocks/views.py:95`
- **문제**:
  - `queryset.filter(sector__icontains=sector)` — `sector` 필드에 인덱스가 있으나(`stocks/models.py:96`) `__icontains`는 인덱스를 활용하지 못해 풀스캔.
  - Stock 테이블 규모가 크지 않아 영향은 제한적.
- **권장 수정**:
  - 정확 일치(`filter(sector__iexact=sector)`)로 변경하거나 PostgreSQL `pg_trgm` GIN 인덱스 도입(현재 규모로는 불필요).
- **수정 난이도**: **쉬움**
- **심각도**: **LOW**

---

## 모범 사례 (잘 된 부분)

참고용으로 양호한 패턴들 — 동일 패턴을 다른 view로 확장 권장:

- `users/views.py:264, 358, 404, 819` — `select_related('stock')` 일관 적용
- `users/views.py:655` — `prefetch_related('items__stock')` 깊이 prefetch
- `stocks/views_eod.py:77, 99` — `select_related('stock')` + 슬라이스 + 1회 직렬화
- `chainsight/api/views.py:391, 529` — `Stock.objects.filter(symbol__in=tickers)` 후 dict 매핑(전형적 in_bulk 패턴)
- `news/models.py` — db_index와 복합 indexes가 풍부
- `rag_analysis/models.py UsageLog:335-340` — `(user, created_at)` 등 4개 복합 인덱스 모범

---

## 권장 우선순위 (배포 전 시급 → 점진 개선)

1. **즉시 (배포 차단급)**:
   - HIGH-1 페이지네이션 전역 도입 (settings + 영향 큰 list view부터 점진 contract 변경)
   - HIGH-3 `OverviewTabSerializer` prefetch — 종목 상세 페이지가 사이트 메인 동선
2. **이번 스프린트**:
   - HIGH-2 (DataBasket annotate)
   - HIGH-4 (WatchListStockSerializer Prefetch)
   - HIGH-5 (Validation N+1 — 30~100쿼리/req → 5쿼리 가능)
   - HIGH-7 (WatchlistSerializer Count annotation)
3. **다음 스프린트**:
   - HIGH-6, MED-1~7 점진 개선
4. **백로그**:
   - LOW-1~5 인덱스 정리 + sector __icontains 검토

---

## 비고

- `stocks/views_fundamentals.py`와 `stocks/views_market_movers.py`는 외부 FMP API 호출 위주로 DB N+1 위험이 낮아 본 감사에서 깊이 다루지 않음 (캐싱·Rate limit 이슈는 별도 audit 영역).
- `macro/views.py`는 모두 service 레이어에 위임, view 자체는 단순 → DB 패턴은 service 감사 대상.
- `sec_pipeline/views.py:36-51`은 단일 endpoint(`FilingDataView`)만 존재하여 본 감사 범위 작음.
- 본 보고서는 정적 분석 기반이므로 실제 응답 시간/쿼리 수 측정은 `django-debug-toolbar` 또는 `silk`로 추가 검증 권장.
