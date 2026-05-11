# API 성능 감사 보고서

- 감사일: 2026-05-06
- 감사자: Claude (read-only audit)
- 대상 디렉토리: stocks/, users/, news/, macro/, rag_analysis/, serverless/, validation/, chainsight/, sec_pipeline/, graph_analysis/

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 | 인덱스 | Serializer | 페이지네이션 | 합계 |
|--------|-----|--------|------------|---------------|------|
| HIGH   | 6   | 0      | 2          | 1             | 9    |
| MED    | 5   | 2      | 1          | 4             | 12   |
| LOW    | 2   | 1      | 0          | 3             | 6    |
| **합계** | **13** | **3** | **3** | **8** | **27** |

핵심 메시지:
- **validation/api/views.py**: 단일 페이지 호출에서 카테고리 × 지표 × 연도 곱 만큼 쿼리가 발생하는 quadratic N+1이 다수 존재. 가장 큰 위험.
- **stocks/serializers.py**: `WatchListStockSerializer`가 `SerializerMethodField` 안에서 추가 쿼리를 던지는 전형적 안티패턴.
- **stocks/views.py StockListAPIView**: `pagination_class` 미설정 → 13,000+ 종목 한 번에 직렬화 위험.
- **chainsight/api/views.py**: 그래프 edge 루프에서 동기 ORM 호출 N+1.

---

## 1. N+1 쿼리

### HIGH-1. ValidationMetricsView 카테고리 × 지표 × 연도 polynomial N+1
- 파일: `validation/api/views.py:191-300` (`ValidationMetricsView._build_category` / `_build_metric`)
- 패턴:
  ```python
  for cat in categories:                                  # 7
      for mc in metric_codes:                             # 카테고리당 ~5
          MetricDefinition.objects.filter(pk=mc).first()  # +1
          # _build_metric:
          CompanyMetricSnapshot.objects.filter(...).first()        # +1 (latest_snap)
          CompanyMetricSnapshot.objects.filter(...).first()        # +1 (any_snap, fallback)
          CompanyBenchmarkDelta.objects.filter(...).first()        # +1
          for s in snaps[:5]:                                       # 최대 5
              PeerMetricBenchmark.objects.filter(...).first()      # +1
  ```
- 영향: `category=all` 호출 1회당 약 `7 × 5 × (3 + 5) = 280` 쿼리.
- 권장 수정: `metric_codes` 전체에 대해 `MetricDefinition.objects.filter(pk__in=...)`, `CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code__in=metric_codes).order_by('metric_code', '-fiscal_year')` 한 번씩 → dict 조회로 분배. `PeerMetricBenchmark`도 (metric_code, fiscal_year) 페어 단위 bulk fetch.
- 난이도: 중간

### HIGH-2. LeaderComparisonView 지표 루프 N+1
- 파일: `validation/api/views.py:351-400`
- 패턴: `for cat, mc in all_metrics:` 안에서 `MetricDefinition.first()` + `CompanyMetricSnapshot.objects.filter(...).first()` 2회(자사+leader).
- 영향: 카테고리 7 × 평균 5지표 = ~35지표 → 약 `35 × 3 = 105` 쿼리.
- 권장 수정: `MetricDefinition` 한 번에 fetch, `CompanyMetricSnapshot.objects.filter(symbol__in=[stock, leader], fiscal_year=latest_fy, metric_code_id__in=...)` 한 쿼리 → `(symbol, metric_code) → snapshot` dict 구성.
- 난이도: 중간

### HIGH-3. ValidationSummaryView 산업 내 순위 루프
- 파일: `validation/api/views.py:110-124`
- 패턴: `for mc in rank_metrics:` 안에서 `CompanyBenchmarkDelta.first()` + `MetricDefinition.first()` (5 × 2 = 10 쿼리).
- 권장 수정: `metric_code__in=rank_metrics` 한 쿼리씩.
- 난이도: 쉬움

### HIGH-4. ChainSightGraphView 엣지 루프 N+1
- 파일: `chainsight/api/views.py:70-83`
- 패턴:
  ```python
  for edge in result.get("edges", []):
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
  ```
- 영향: depth=3까지 허용 → edges가 수백 개일 때 수백 쿼리.
- 권장 수정: 정렬된 `(a,b)` 페어 리스트를 만들어 `CoMentionEdge.objects.filter(Q(symbol_a__in=...) & Q(symbol_b__in=...))` 한 번에 fetch → `(a,b) → row` dict로 매핑.
- 난이도: 중간

### HIGH-5. WatchListStockSerializer Method Field 내부 쿼리
- 파일: `stocks/serializers.py:381-409`
- 패턴: `get_latest_price`와 `get_chart_data`가 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()`/`[:7]`을 매 객체마다 실행. `many=True`일 때 N+1.
- 권장 수정:
  - 호출 측에서 `Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date'))`로 한 번에 fetch.
  - 또는 `.annotate(latest_close=Subquery(...))`로 `latest_price`만 미리 계산.
- 난이도: 중간 (annotate 또는 prefetch + 슬라이싱 처리)

### HIGH-6. IndicatorComparisonView 심볼 루프
- 파일: `stocks/views_indicators.py:324-336`
- 패턴: `for symbol in symbols:` 안에서 `Stock.objects.get(symbol=...)` + `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]`.
- 영향: 비교 대상 N개 → `2N` 쿼리. 사용자가 임의로 N을 지정 가능 (상한 미설정).
- 권장 수정:
  - `Stock.objects.filter(symbol__in=[s.upper() for s in symbols])` 1회.
  - `DailyPrice.objects.filter(stock_id__in=stock_ids).order_by('stock_id','-date')` + Python에서 그룹핑.
  - symbols 길이 상한 추가(예: 20).
- 난이도: 쉬움

### MED-1. StocksOverview dynamic_layers 6 reverse-lookup
- 파일: `stocks/serializers.py:205-307` (`OverviewTabSerializer.get_dynamic_layers`)
- 패턴: `obj.category_signals.all()`, `obj.validation_news_summary`, `obj.sensitivity_profile`, `obj.growth_stage`, `obj.capital_dna`, `obj.narrative_tag` 등 7개 reverse 접근. 뷰(`stocks/views.py:492`)는 `select_related('overview_ko')`만 적용.
- 코드 자체에 `# TODO: prefetch_related` 주석 존재.
- 영향: 단일 종목 페이지 호출당 +6쿼리. 만약 향후 list 응답에서 `OverviewTabSerializer`를 `many=True`로 쓰면 즉시 N+1.
- 권장 수정: 뷰 queryset에 `select_related('overview_ko','validation_news_summary','sensitivity_profile','growth_stage','capital_dna','narrative_tag').prefetch_related('category_signals')` 추가.
- 난이도: 쉬움

### MED-2. NewsViewSet.trending() 종목별 최근 기사 루프
- 파일: `news/api/views.py:331-336`
- 패턴: 집계 결과 각 항목마다 `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')[:3]`.
- 영향: limit=10 → 10 추가 쿼리 (5분 캐시로 완화되지만 첫 호출 비용은 큼).
- 권장 수정: 한 번의 쿼리로 `NewsArticle.objects.filter(entities__symbol__in=symbols, ...).order_by('-published_at')` 후 Python에서 심볼별 상위 3개 자르기. 또는 PostgreSQL `ROW_NUMBER() OVER (PARTITION BY entity_symbol ORDER BY published_at DESC)` window function.
- 난이도: 중간

### MED-3. WatchlistBulkAddView 심볼 루프
- 파일: `users/views.py:872-895`
- 패턴: `for symbol in symbols: Stock.objects.get(symbol=symbol.upper())` + `WatchlistItem.objects.filter(...).exists()` + `WatchlistItem.objects.create(...)`.
- 영향: 50종목 bulk add → 약 150쿼리 + transaction 안에서 직렬 실행.
- 권장 수정: `Stock.objects.filter(symbol__in=upper_syms)` 1회, `WatchlistItem.objects.filter(watchlist=watchlist, stock_id__in=stock_ids).values_list('stock_id', flat=True)`로 중복 set 추출, `WatchlistItem.objects.bulk_create([...])`.
- 난이도: 중간

### MED-4. WatchlistBulkRemoveView 심볼 루프
- 파일: `users/views.py:937-944`
- 패턴: `for symbol in symbols: WatchlistItem.objects.get(watchlist=..., stock__symbol=symbol.upper())`로 개별 삭제.
- 권장 수정: `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=upper_syms).delete()` 한 번 + 사전 `values_list`로 found set 비교하여 not_found 계산.
- 난이도: 쉬움

### MED-5. PortfolioSummaryView 중복 쿼리
- 파일: `users/views.py:349-380`
- 패턴: `portfolios.exists()` + 루프 안에서 `total_value`/`total_cost` 프로퍼티 사용 + `portfolios.count()`. select_related로 stock은 묶였지만, `exists()`+`count()`+계산 루프 = 3 라운드트립.
- 권장 수정: `aggregate(Sum(F('quantity') * F('stock__real_time_price')), Sum(F('quantity') * F('average_price')), Count('id'))`로 단일 SQL.
- 난이도: 쉬움

### LOW-1. PortfolioDetailTableView sum 두 번 + count
- 파일: `users/views.py:395-426`
- 패턴: `sum(p.total_value for p in portfolios)` + `sum(p.total_cost for p in portfolios)` + `.count()`.
- 영향: portfolios queryset이 cache되더라도 count()는 별도 쿼리.
- 권장: `aggregate`로 합산.
- 난이도: 쉬움

### LOW-2. ChainSightSuggestionView co_mentions UNION
- 파일: `chainsight/api/views.py:145-149`
- 패턴: `CoMentionEdge.objects.filter(symbol_a=symbol).union(CoMentionEdge.objects.filter(symbol_b=symbol)).order_by('-co_mention_count')[:10]`. UNION 결과는 정렬 인덱스를 잃고 재정렬 필요.
- 권장: `CoMentionEdge.objects.filter(Q(symbol_a=symbol) | Q(symbol_b=symbol)).order_by('-co_mention_count')[:10]`.
- 난이도: 쉬움

---

## 2. 인덱스 누락

전체적으로 인덱스 커버리지는 양호. 다만 다음 항목은 빈번한 필터에 비해 인덱스가 약함.

### MED-1. NewsArticle 텍스트 검색 인덱스 부재
- 파일: `news/models.py:189-197`
- 현재 인덱스: `published_at`, `category`, `source`, `sentiment_score`, `importance_score`, `llm_analyzed` 등 정렬/필터용.
- `news/api/views.py:730` `NewsArticle.objects.filter(title_q, ...)` `Q(title__icontains=term)` 사용. `title`에 대한 trigram/GIN 인덱스 없음.
- 영향: 키워드 fallback 경로 (legacy daily keyword) 호출 시 sequential scan. 캐시 히트로 평소엔 가려져 있음.
- 권장: PostgreSQL `pg_trgm` 확장 + `GinIndex(fields=['title'], opclasses=['gin_trgm_ops'])` 마이그레이션.
- 난이도: 중간

### MED-2. EODSignal JSONB 컨테인먼트 검색
- 파일: `stocks/views_eod.py:73-78`, `stocks/models.py:785-792`
- 패턴: `EODSignal.objects.filter(date=target_date, signals__contains=[{'id': signal_id}])`. `signals`가 JSONB.
- 현재 인덱스: 일반 b-tree만 존재. JSONB GIN 인덱스 없음.
- 영향: signal_id가 다양해지면 sequential scan 비용 증가.
- 권장: `GinIndex(fields=['signals'])` 추가. 단, 데이터셋이 작을 경우(EOD 일별 ~3000행) 우선순위 낮음.
- 난이도: 쉬움

### LOW-1. Stock.is_actively_trading
- 파일: `stocks/models.py` 및 `stocks/views_screener.py`
- 패턴: 스크리너에서 `is_actively_trading=True` 필터.
- 현재 인덱스: 미발견 (`SP500Constituent.is_active`는 인덱스 있음).
- 영향: 일반적으로 대부분 True이므로 카디널리티 낮아 영향 작음.
- 난이도: 쉬움

---

## 3. Serializer 추가 쿼리

### HIGH-1. WatchListStockSerializer (재기재) — N+1
- 파일: `stocks/serializers.py:398-409`
- N+1 절 HIGH-5와 동일. 별도 항목으로 명시.

### HIGH-2. OverviewTabSerializer.get_dynamic_layers — 6+1 reverse 접근
- 파일: `stocks/serializers.py:205-307`
- N+1 절 MED-1과 동일. Method field 안 reverse 접근 패턴.

### MED-1. PortfolioSerializer source='stock.symbol' 등
- 파일: `users/serializers.py:31-62`, `65-153`
- `current_price = serializers.DecimalField(source='stock.real_time_price', ...)` 등 `stock.*` source. select_related('stock')이 들어있는 모든 뷰에서는 안전. 하지만 **`PortfolioBySymbolView`(line 477) 등 1건 직접 조회는** select_related 없이 동작 → 단일 객체라 추가 1쿼리만 발생, 영향 작음.
- 권장: 모든 Portfolio 조회에 `.select_related('stock')` 일관 적용.
- 난이도: 쉬움

---

## 4. 페이지네이션 누락

전체 코드베이스에서 `pagination_class`, `PageNumberPagination`, `LimitOffsetPagination` grep 결과 **0건**. 즉 DRF 전역/뷰 레벨 페이지네이션이 설정되지 않았으며, 일부 뷰는 수동 Paginator로 구현, 일부는 미구현.

### HIGH-1. StockListAPIView (전체 종목 목록)
- 파일: `stocks/views.py:75-105`
- `generics.ListAPIView` + `pagination_class` 없음. queryset은 `Stock.objects.all().order_by('-market_capitalization')` 전체 반환 (S&P 500 + 비S&P 합쳐 13,000+ 가능).
- 권장: `pagination_class = PageNumberPagination` (page_size=20~50). 전역 `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` 설정 권장.
- 난이도: 쉬움

### MED-1. DataBasketListCreateView
- 파일: `rag_analysis/views.py:71-75`
- `DataBasket.objects.filter(user=request.user).prefetch_related('items')` 전체 반환.
- 권장: `Paginator` 또는 LimitOffset 도입. 사용자별 baskets는 보통 적지만 봇/이상 사용자 보호.
- 난이도: 쉬움

### MED-2. AnalysisSessionListCreateView
- 파일: `rag_analysis/views.py:431-435`
- 동일 패턴. `AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')`.
- 권장: 페이지네이션 + `messages`는 별도 엔드포인트로 분리하거나 last_message만 annotate.
- 난이도: 쉬움

### MED-3. PortfolioListCreateView / PortfolioDetailTableView
- 파일: `users/views.py:255-259`, `395-426`
- 사용자별이라 통상 작지만 상한 없음.
- 권장: page_size=50 고정 페이지네이션.
- 난이도: 쉬움

### MED-4. NewsViewSet (ViewSet에 pagination 미설정)
- 파일: `news/api/views.py:42`
- `viewsets.ReadOnlyModelViewSet` + `queryset = NewsArticle.objects.all().prefetch_related('entities')`. DRF 전역 설정이 없으므로 list 응답은 모든 기사 직렬화.
- `all_news` 액션은 수동 offset/limit 지원하지만 retrieve list 자체는 미보호.
- 권장: 전역 `DEFAULT_PAGINATION_CLASS` 설정 또는 `pagination_class` 명시.
- 난이도: 쉬움

### LOW-1. UserInterestListCreateView
- 파일: `users/views.py:966-979`
- 사용자별 interests, 데이터셋 매우 작음.
- 난이도: 쉬움

### LOW-2. AdminNewsCategoryView
- 파일: `serverless/views_admin.py:475-500`
- 카테고리 수십개 수준. 페이지네이션 없어도 무방.
- 난이도: 쉬움

### LOW-3. SeedListView, ChainSightSuggestionView
- 데이터셋 자체가 시드/카테고리 수십 개로 제한됨. 우선순위 낮음.

---

## 5. 부수적 관찰 (참고)

다음은 N+1/인덱스/페이지네이션 4축에는 직접 들어가지 않지만, 같은 감사 중 발견한 사항. 수정 여부 판단은 별도 트랙.

- `users/views.py:281-283` Portfolio 생성 시 `threading.Thread(target=background_fetch, daemon=True)` — Celery 대신 raw thread 사용. 인프라 표준(`@infra` 담당)과 충돌 가능. **DECISIONS.md 검토 권장**.
- `macro/views.py:373` 동일하게 `threading.Thread`로 동기화 트리거. 위와 동일.
- `stocks/views_indicators.py:60-66` `prices_data = query.order_by('date').values(...)` 후 `pd.DataFrame(list(prices_data))` — 메모리 스파이크 가능. 인덱스 영향 아님.
- `stocks/views.py:822-874` `StockCompleteDataAPIView`는 `get_object_or_404`로 단일 stock fetch 후 4개의 별도 queryset (DailyPrice + 3 financial). select_related/prefetch로 단일 round-trip이 아닌 병렬 5쿼리. 이것은 여러 다른 모델에 분산된 데이터라 N+1보다는 "불필요한 라운드트립" 카테고리.

---

## 권장 우선순위

수정 ROI 순:

1. **stocks/views.py:75-105** `StockListAPIView pagination_class` 추가 (난이도 쉬움 / 영향 HIGH).
2. **stocks/serializers.py:381-409** `WatchListStockSerializer` annotate/prefetch 전환 (난이도 중간 / 영향 HIGH).
3. **validation/api/views.py:191-300, 351-400** Validation 뷰 N+1 정리 (난이도 중간 / 영향 HIGH, 사용자 체감 주요).
4. **chainsight/api/views.py:70-83** edge 루프 bulk fetch (난이도 중간 / 영향 HIGH).
5. **stocks/views.py:492-494** OverviewTabSerializer가 쓰는 6 reverse 관계 select_related 보강 (난이도 쉬움 / 영향 MED).
6. **users/views.py:872-895, 937-944** Watchlist bulk 작업 단일 쿼리화 (난이도 중간 / 영향 MED).
7. **rag_analysis/views.py, news/api/views.py** 페이지네이션 일관 적용 — 전역 `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` 설정으로 한 번에 해결 가능.
8. **인덱스**: NewsArticle.title trigram GIN, EODSignal.signals JSONB GIN — 데이터 성장 시 추가.

---

## 부록: 감사한 파일

뷰 (17개): stocks/views.py, stocks/views_search.py, stocks/views_exchange.py, stocks/views_eod.py, stocks/views_screener.py, stocks/views_market_movers.py, stocks/views_fundamentals.py, stocks/views_indicators.py, stocks/views_mvp.py, users/views.py, news/api/views.py, macro/views.py, rag_analysis/views.py, serverless/views_admin.py, validation/api/views.py, chainsight/api/views.py, sec_pipeline/views.py.

직렬화 (10개): stocks/serializers.py, stocks/serializers_*.py, users/serializers.py, news/api/serializers.py, macro/serializers.py, rag_analysis/serializers.py, serverless/serializers.py.

모델 (7개): stocks/models.py, users/models.py, news/models.py, serverless/models.py, rag_analysis/models.py, sec_pipeline/models.py, graph_analysis/models.py.
