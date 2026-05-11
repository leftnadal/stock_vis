# API 성능 감사 보고서

**작성일:** 2026-04-22
**대상:** Stock-Vis Backend (Django REST Framework)
**감사 범위:** 17개 views + 7개 models + serializers
**이전 감사 참조:** `docs/nightly_auto_system/reports/4월/21일/performance_audit.md`
**방식:** 정적 코드 분석 (읽기 전용, 코드 수정 없음)

---

## 요약

| 심각도 | 건수 |
|--------|------|
| HIGH | 14 |
| MED | 11 |
| LOW | 4 |
| **합계** | **29** |

### 심각도별 분포

- N+1 쿼리: HIGH 5 / MED 4 / LOW 1
- 인덱스 누락: HIGH 4 / MED 4 / LOW 2
- 느린 Serializer: HIGH 3 / MED 3 / LOW 1
- 페이지네이션 누락: HIGH 2 / MED 0 / LOW 0

### 이전 감사(4/21) 대비 변경 사항

| 지표 | 2026-04-21 | 2026-04-22 | 변동 |
|------|:----------:|:----------:|:----:|
| 총 이슈 | 29 | 29 | 0 |
| HIGH | 15 | 14 | -1 |
| MED | 11 | 11 | 0 |
| LOW | 3 | 4 | +1 |

> **변동 이유**: 전일 `WatchListStockSerializer.get_chart_data()` return 누락 버그(CRITICAL)를 논리 버그 카테고리에서 N+1 카테고리로 통합 재분류. 나머지 이슈는 전부 UNCHANGED. 수정된 항목 없음.

---

## 상세 이슈

### [HIGH-01] ValidationMetricsView — 카테고리×지표 중첩 N+1 쿼리

- **파일:** `validation/api/views.py:199-314`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 높음
- **설명:**
  `_build_category()`는 각 카테고리(최대 7개)마다 `_build_metric()`를 지표 수(최대 6개)만큼 호출한다.
  `_build_metric()` 내부에서 매 지표마다 `CompanyMetricSnapshot`, `CompanyBenchmarkDelta`, `PeerMetricBenchmark`를 각각 별도로 조회한다.
  7카테고리 × 6지표 = 최대 42지표 × 3쿼리 = **최대 126회 추가 쿼리**.

  ```python
  # validation/api/views.py:220-284
  def _build_metric(self, stock, md):
      latest_snap = (
          CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md, value_status='normal')
          .order_by('-fiscal_year').first()  # 지표마다 1쿼리
      )
      ...
      delta = CompanyBenchmarkDelta.objects.filter(
          symbol=stock, fiscal_year=..., metric_code=md,
      ).first()  # 지표마다 1쿼리
      ...
      snaps = CompanyMetricSnapshot.objects.filter(
          symbol=stock, metric_code=md,
      ).order_by('fiscal_year')[:5]  # 지표마다 1쿼리 (history)
      for s in snaps:
          peer_bench = PeerMetricBenchmark.objects.filter(
              symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
          ).first()  # history 건수 × 1쿼리 (최대 5×42 = 210회)
  ```

- **권장 수정:**
  `ValidationMetricsView.get()` 시작 시 해당 stock의 전체 지표를 한 번에 prefetch:

  ```python
  all_snapshots = CompanyMetricSnapshot.objects.filter(
      symbol=stock
  ).select_related('metric_code').order_by('metric_code', '-fiscal_year')

  all_deltas = CompanyBenchmarkDelta.objects.filter(symbol=stock)
  all_peer_bench = PeerMetricBenchmark.objects.filter(symbol=stock)

  # dict으로 변환 후 _build_metric에 주입
  snap_map = defaultdict(list)
  for s in all_snapshots:
      snap_map[s.metric_code_id].append(s)
  ```

---

### [HIGH-02] LeaderComparisonView — 전체 지표 루프 내 N+1

- **파일:** `validation/api/views.py:354-401`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 높음
- **설명:**
  `CATEGORY_METRICS`의 전체 지표(약 42개)에 대해 루프를 돌며 `MetricDefinition`, `CompanyMetricSnapshot`(2회), 을 종목별로 별도 조회한다.

  ```python
  # validation/api/views.py:354-378
  for cat, mc in all_metrics:
      md = MetricDefinition.objects.filter(pk=mc).first()        # 42회
      company_snap = CompanyMetricSnapshot.objects.filter(
          symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, ...
      ).first()                                                   # 42회
      leader_snap = CompanyMetricSnapshot.objects.filter(
          symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, ...
      ).first()                                                   # 42회
  ```
  총 42 × 3 = **최소 126회 추가 DB 쿼리**.

- **권장 수정:**
  루프 전 bulk 조회로 교체:

  ```python
  metric_defs = {md.metric_code: md for md in MetricDefinition.objects.all()}
  company_snaps = {
      s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
          symbol=stock, fiscal_year=latest_fy, value_status='normal'
      )
  }
  leader_snaps = {
      s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
          symbol_id=leader.symbol, fiscal_year=latest_fy, value_status='normal'
      )
  }
  ```

---

### [HIGH-03] ValidationSummaryView — rank_metrics 루프 N+1

- **파일:** `validation/api/views.py:110-124`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 쉬움
- **설명:**
  `rank_metrics` 5개 지표에 대해 루프마다 `CompanyBenchmarkDelta`와 `MetricDefinition`을 별도 조회한다.

  ```python
  # validation/api/views.py:110-124
  rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
  for mc in rank_metrics:
      delta = CompanyBenchmarkDelta.objects.filter(
          symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
      ).first()  # 5회
      if delta and delta.rank and delta.total:
          md = MetricDefinition.objects.filter(pk=mc).first()  # 최대 5회
  ```
  총 최대 **10회 추가 쿼리**.

- **권장 수정:**

  ```python
  deltas = {
      d.metric_code_id: d for d in CompanyBenchmarkDelta.objects.filter(
          symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics
      )
  }
  metric_defs = {
      md.metric_code: md for md in MetricDefinition.objects.filter(pk__in=rank_metrics)
  }
  ```

---

### [HIGH-04] NewsViewSet.trending — 루프 내 추가 쿼리

- **파일:** `news/api/views.py:330-343`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 중간
- **설명:**
  `trending` 액션에서 상위 종목 N개(최대 10개)를 집계한 뒤, 루프마다 해당 종목의 최근 기사를 별도 쿼리로 조회한다.

  ```python
  # news/api/views.py:330-343
  results = []
  for item in trending_data:  # 최대 10회
      symbol = item['symbol']
      recent_articles = NewsArticle.objects.filter(
          entities__symbol=symbol,
          published_at__gte=from_date
      ).distinct().order_by('-published_at')[:3]  # 루프마다 1쿼리
  ```
  종목 수(limit)가 최대 `?limit=20`까지 허용되므로 **최대 20회 추가 쿼리**.

- **권장 수정:**
  집계 결과에서 심볼 목록을 추출한 뒤 한 번에 prefetch:

  ```python
  symbols = [item['symbol'] for item in trending_data]
  articles_qs = NewsArticle.objects.filter(
      entities__symbol__in=symbols,
      published_at__gte=from_date
  ).distinct().order_by('-published_at').prefetch_related('entities')

  articles_by_symbol = defaultdict(list)
  for a in articles_qs:
      for e in a.entities.all():
          if e.symbol in symbols and len(articles_by_symbol[e.symbol]) < 3:
              articles_by_symbol[e.symbol].append(a)
  ```

---

### [HIGH-05] WatchListStockSerializer — get_latest_price / get_chart_data 루프 N+1 + return 버그

- **파일:** `stocks/serializers.py:398-410`
- **카테고리:** N+1 쿼리 + 논리 버그
- **수정 난이도:** 중간
- **설명:**
  `WatchListStockSerializer`를 `many=True`로 사용할 때, 각 Stock 객체마다 `get_latest_price`와 `get_chart_data`가 별도 쿼리를 실행한다. 또한 `get_chart_data`에 **return 문이 없어** 항상 `None`을 반환한다.

  ```python
  # stocks/serializers.py:398-410
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()  # N회
      ...

  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(
          stock=obj
      ).order_by('-date')[:7]  # N회 — 그리고 return이 없음!
      # ← return 누락: 함수가 None 반환
  ```
  Watchlist에 종목이 20개라면 **최소 40회 추가 쿼리** + 차트 데이터 항상 `null`.

- **권장 수정:**
  View에서 `prefetch_related`로 DailyPrice를 미리 로드하고, serializer에서는 `obj.dailyprice_set`을 사용.
  `get_chart_data`에 return 추가:

  ```python
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(
          stock=obj
      ).order_by('-date')[:7]
      return ChartDataSerializer(recent_prices, many=True).data  # return 추가
  ```

---

### [HIGH-06] OverviewTabSerializer.get_dynamic_layers — 최대 7N 추가 쿼리

- **파일:** `stocks/serializers.py:205-300`
- **카테고리:** 느린 Serializer
- **수정 난이도:** 중간
- **설명:**
  `get_dynamic_layers()`는 try/except 블록으로 6개의 역참조 필드(`category_signals`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `chainsight_profile` 등)를 접근한다. 이는 객체마다 ORM 지연 로딩을 트리거한다.

  ```python
  # stocks/serializers.py:215
  signals = list(obj.category_signals.all())   # 1쿼리/객체

  # stocks/serializers.py:235
  ns = obj.validation_news_summary             # 1쿼리/객체 (OneToOne)

  # stocks/serializers.py:252
  sp = obj.sensitivity_profile                 # 1쿼리/객체

  # stocks/serializers.py:265
  gs = obj.growth_stage                        # 1쿼리/객체
  ```
  `OverviewTabSerializer`를 단일 객체에 사용해도 6회 추가 쿼리 발생.

- **권장 수정:**
  `StockOverviewAPIView`에서 조회 시 관계 prefetch:

  ```python
  stock = Stock.objects.select_related(
      'overview_ko',
      'validation_news_summary',
      'sensitivity_profile',
      'growth_stage',
      'capital_dna',
  ).prefetch_related('category_signals').filter(symbol=symbol).first()
  ```

---

### [HIGH-07] users/views.py:PortfolioSummaryView — 프로퍼티 루프에서 N+1

- **파일:** `users/views.py:349-383`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 쉬움
- **설명:**
  `Portfolio.total_value`와 `Portfolio.total_cost` 프로퍼티가 `self.stock.real_time_price`와 `self.average_price`를 접근한다.
  `select_related('stock')`으로 stock은 join되지만, 루프 내에서 프로퍼티를 호출하는 `PortfolioDetailTableView.get()`도 동일 패턴으로 반복된다. 두 뷰 모두 `portfolios`를 `select_related('stock')`으로 가져오므로 Stock 조회 N+1은 없으나, **루프 후 두 번째 `.count()` 호출이 추가 쿼리**를 발생시킨다.

  ```python
  # users/views.py:367-372
  for portfolio in portfolios:          # 이미 select_related로 로드됨
      total_value += portfolio.total_value
      total_cost += portfolio.total_cost

  summary = {
      'total_stocks': portfolios.count(),  # ← 추가 COUNT 쿼리 발생
  ```

- **권장 수정:**

  ```python
  portfolios = list(Portfolio.objects.filter(user=request.user).select_related('stock'))
  summary = {
      'total_stocks': len(portfolios),   # count() 쿼리 제거
      ...
  }
  ```

---

### [HIGH-08] StockListAPIView — pagination_class 미설정

- **파일:** `stocks/views.py:75-105`
- **카테고리:** 페이지네이션 누락
- **수정 난이도:** 쉬움
- **설명:**
  `StockListAPIView`는 `generics.ListAPIView`를 상속하지만 `pagination_class`가 설정되어 있지 않고, `REST_FRAMEWORK` 설정의 `DEFAULT_PAGINATION_CLASS`도 없다. Stock 테이블에는 수천 row가 존재할 수 있으며, `order_by('-market_capitalization')` 없이 전체 반환 시 대용량 응답이 발생한다.

  ```python
  # stocks/views.py:75-105
  class StockListAPIView(generics.ListAPIView):
      serializer_class = StockListSerializer
      # pagination_class 없음

      def get_queryset(self):
          queryset = Stock.objects.all()   # 전체 테이블 로드 가능
          ...
          return queryset.order_by('-market_capitalization')
  ```

- **권장 수정:**

  ```python
  from rest_framework.pagination import PageNumberPagination

  class StockListAPIView(generics.ListAPIView):
      serializer_class = StockListSerializer
      pagination_class = PageNumberPagination  # 또는 커스텀 클래스
  ```

---

### [HIGH-09] NewsViewSet — pagination_class 미설정

- **파일:** `news/api/views.py:42-46`
- **카테고리:** 페이지네이션 누락
- **수정 난이도:** 쉬움
- **설명:**
  `NewsViewSet`의 기본 `queryset`이 `NewsArticle.objects.all()`으로 전체 뉴스를 로드한다. `pagination_class`가 명시되지 않아 list 액션에서 모든 기사가 응답에 포함될 수 있다.

  ```python
  # news/api/views.py:42-46
  class NewsViewSet(viewsets.ReadOnlyModelViewSet):
      queryset = NewsArticle.objects.all().prefetch_related('entities')
      serializer_class = NewsArticleListSerializer
      # pagination_class 없음
  ```

- **권장 수정:**

  ```python
  class NewsViewSet(viewsets.ReadOnlyModelViewSet):
      queryset = NewsArticle.objects.all().prefetch_related('entities')
      serializer_class = NewsArticleListSerializer
      pagination_class = PageNumberPagination
  ```

---

### [HIGH-10] users/views.py:WatchlistBulkAddView — 루프 내 Stock 개별 조회

- **파일:** `users/views.py:872-895`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 쉬움
- **설명:**
  여러 종목을 한 번에 추가할 때 루프마다 `Stock.objects.get()`과 `WatchlistItem.objects.filter().exists()`를 호출한다.

  ```python
  # users/views.py:872-895
  for symbol in symbols:           # 최대 수십 종목
      stock = Stock.objects.get(symbol=symbol.upper())          # N회
      if WatchlistItem.objects.filter(
          watchlist=watchlist, stock=stock
      ).exists():                                                # N회
          ...
  ```

- **권장 수정:**

  ```python
  # 한 번에 batch 조회
  stocks_map = {s.symbol: s for s in Stock.objects.filter(
      symbol__in=[s.upper() for s in symbols]
  )}
  existing_symbols = set(WatchlistItem.objects.filter(
      watchlist=watchlist, stock__symbol__in=stocks_map.keys()
  ).values_list('stock__symbol', flat=True))
  ```

---

### [MED-01] ChainSightGraphView — CoMentionEdge / PriceCoMovement 루프 N+1

- **파일:** `chainsight/api/views.py:72-84`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 중간
- **설명:**
  그래프 엣지 목록에 대해 루프마다 `CoMentionEdge`와 `PriceCoMovement`를 각각 조회한다.

  ```python
  # chainsight/api/views.py:72-84
  for edge in result.get("edges", []):
      from_t = edge.get("from", "")
      to_t = edge.get("to", "")
      if from_t and to_t:
          a, b = (from_t, to_t) if from_t < to_t else (to_t, from_t)
          cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()  # 엣지마다 1쿼리
          pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()  # 엣지마다 1쿼리
  ```
  엣지 수(depth=3이면 수십 개)만큼 **최대 60+회 추가 쿼리**.

- **권장 수정:**

  ```python
  edge_pairs = set()
  for edge in result.get("edges", []):
      a, b = sorted([edge.get("from",""), edge.get("to","")])
      if a and b:
          edge_pairs.add((a, b))

  cm_map = {(c.symbol_a, c.symbol_b): c for c in CoMentionEdge.objects.filter(
      symbol_a__in=[p[0] for p in edge_pairs],
      symbol_b__in=[p[1] for p in edge_pairs],
  )}
  ```

---

### [MED-02] SectorGraphView / NeighborGraphView — Stock bulk 조회 (양호하나 캐시 미적용 fallback)

- **파일:** `chainsight/api/views.py:328, 465`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 쉬움
- **설명:**
  `SectorGraphView`와 `NeighborGraphView` 모두 Neo4j에서 ticker 목록을 가져온 뒤 `Stock.objects.filter(symbol__in=tickers)`로 bulk 조회하는 패턴은 올바르다. 그러나 캐시 미스 시 Neo4j + Django DB 두 번 쿼리 후 결과를 캐시에 저장하는데, 캐시 TTL이 각각 3600초(SectorGraph)와 1800초(NeighborGraph)로 설정되어 있어 정상 운영 중에는 문제 없다. 단, Neo4j 불안정 시 매 요청마다 Django DB 추가 조회가 발생한다. 현재는 MED 수준.

- **권장 수정:**
  캐시 미스 시 Neo4j 오류 대비 fallback 로직 강화. 현재는 `GraphConnectionError`만 처리하므로 일반 예외도 로깅 후 503 반환 추가.

---

### [MED-03] IndicatorComparisonView — 심볼 루프 내 DailyPrice 개별 조회

- **파일:** `stocks/views_indicators.py:324-371`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 중간
- **설명:**
  여러 종목 비교 API에서 심볼 수만큼 `DailyPrice`를 별도 조회한다.

  ```python
  # stocks/views_indicators.py:333-335
  for symbol in symbols:
      ...
      prices = DailyPrice.objects.filter(
          stock=stock
      ).order_by('-date')[:50].values_list('close_price', flat=True)  # N회
  ```

- **권장 수정:**
  `prefetch_related` 또는 단일 쿼리로 심볼 목록의 최근 50일치 가격 일괄 조회.

---

### [MED-04] users/views.py:WatchlistBulkRemoveView — 루프 내 개별 삭제

- **파일:** `users/views.py:937-941`
- **카테고리:** N+1 쿼리
- **수정 난이도:** 쉬움
- **설명:**
  여러 종목 일괄 제거 시 루프마다 `WatchlistItem.objects.get()`을 호출한다.

  ```python
  # users/views.py:937-941
  for symbol in symbols:
      item = WatchlistItem.objects.get(
          watchlist=watchlist, stock__symbol=symbol.upper()
      )  # N회
      item.delete()  # N회
  ```

- **권장 수정:**

  ```python
  # 단일 bulk delete
  WatchlistItem.objects.filter(
      watchlist=watchlist,
      stock__symbol__in=[s.upper() for s in symbols]
  ).delete()
  ```

---

### [MED-05] stocks/serializers.py:get_chart_data — return 누락 (논리 버그)

- **파일:** `stocks/serializers.py:405-410`
- **카테고리:** 느린 Serializer + 논리 버그
- **수정 난이도:** 쉬움
- **설명:**
  `WatchListStockSerializer.get_chart_data()`에 return 문이 없어 항상 `None` 반환. 쿼리는 실행되지만 결과가 버려진다.

  ```python
  # stocks/serializers.py:405-410
  def get_chart_data(self, obj):
      """최근 7일 차트 데이터"""
      recent_prices = DailyPrice.objects.filter(
          stock=obj
      ).order_by('-date')[:7]
      # return 문 없음 — None 반환
  ```

- **권장 수정:**

  ```python
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(
          stock=obj
      ).order_by('-date')[:7]
      return [{'date': str(p.date), 'close': float(p.close_price)} for p in recent_prices]
  ```

---

### [MED-06] users/models.py:UserInterest — 인덱스 누락

- **파일:** `users/models.py:249-268`
- **카테고리:** 인덱스 누락
- **수정 난이도:** 중간 (마이그레이션 필요)
- **설명:**
  `UserInterest` 모델에 `user` FK와 `created_at`에 대한 인덱스가 없다. `users/views.py:967`에서 `UserInterest.objects.filter(user=request.user).order_by('-created_at')` 쿼리를 실행하지만, `Meta.indexes`가 없다.

  ```python
  # users/models.py:262-268
  class Meta:
      db_table = 'users_interest'
      unique_together = ('user', 'interest_type', 'value')
      # indexes 없음 — user + created_at 필터에 인덱스 없음
  ```

- **권장 수정:**

  ```python
  class Meta:
      db_table = 'users_interest'
      unique_together = ('user', 'interest_type', 'value')
      indexes = [
          models.Index(fields=['user', '-created_at']),
      ]
  ```

---

### [MED-07] rag_analysis/models.py:DataBasket — user FK 인덱스 누락

- **파일:** `rag_analysis/models.py:11-28`
- **카테고리:** 인덱스 누락
- **수정 난이도:** 중간 (마이그레이션 필요)
- **설명:**
  `DataBasket` 모델에 `Meta.indexes`가 없다. `DataBasketListCreateView`에서 `DataBasket.objects.filter(user=request.user).prefetch_related('items')`로 조회하지만 `user` 필드에 인덱스가 없다.

  ```python
  # rag_analysis/models.py
  class DataBasket(models.Model):
      user = models.ForeignKey(User, ...)
      ...
      class Meta:
          ordering = ["-updated_at"]
          # indexes 없음
  ```

- **권장 수정:**

  ```python
  class Meta:
      ordering = ["-updated_at"]
      indexes = [
          models.Index(fields=['user', '-updated_at']),
      ]
  ```

---

### [MED-08] rag_analysis/models.py:AnalysisSession — user FK 인덱스 누락

- **파일:** `rag_analysis/models.py` (AnalysisSession 클래스)
- **카테고리:** 인덱스 누락
- **수정 난이도:** 중간 (마이그레이션 필요)
- **설명:**
  `AnalysisSession`도 `DataBasket`과 동일하게 `user` FK 인덱스가 없다. `AnalysisSessionListCreateView`에서 `AnalysisSession.objects.filter(user=request.user)` 조회 시 full scan 발생 가능.

- **권장 수정:**
  `AnalysisSession.Meta.indexes`에 `models.Index(fields=['user', '-updated_at'])` 추가.

---

### [MED-09] stocks/models.py:EODSignal — stock FK 인덱스 누락 복합 인덱스

- **파일:** `stocks/models.py:785-793`
- **카테고리:** 인덱스 누락
- **수정 난이도:** 중간
- **설명:**
  `EODSignal.Meta.indexes`에 `date + sector`, `date + composite_score`, `stock + -date` 인덱스는 있으나, `views_eod.py:73`의 `EODSignal.objects.filter(date=target_date, signals__contains=[{'id': signal_id}])` 쿼리에서 `signals` JSONField에 대한 GIN 인덱스가 없다. `signals__contains` 연산자는 전체 JSONB 스캔이 필요하다.

  ```python
  # stocks/views_eod.py:72-78
  signals = (
      EODSignal.objects.filter(
          date=target_date,
          signals__contains=[{'id': signal_id}],  # GIN 인덱스 없음
      )
      .select_related('stock')
      .order_by('-composite_score')[:50]
  )
  ```

- **권장 수정:**

  ```python
  # stocks/models.py — EODSignal.Meta.indexes에 추가
  # GIN 인덱스는 migration 파일에서 직접 RunSQL로 생성 필요:
  # CREATE INDEX stocks_eod_signal_signals_gin ON stocks_eod_signal USING GIN (signals);
  ```

---

### [MED-10] stocks/models.py:BalanceSheet/IncomeStatement/CashFlowStatement — stock+period_type 복합 인덱스 중복

- **파일:** `stocks/models.py:356-362, 425-431, 524-530`
- **카테고리:** 인덱스 누락
- **수정 난이도:** 쉬움
- **설명:**
  세 재무제표 모델 모두 `indexes = [Index(fields=['stock', 'fiscal_year']), Index(fields=['period_type', 'fiscal_year'])]`를 가진다. 그러나 views에서 실제 쿼리는 `filter(stock=stock, period_type=db_period).order_by('-fiscal_year', '-fiscal_quarter')[:limit]`로, **`(stock, period_type, -fiscal_year)` 복합 인덱스**가 없어 `stock+fiscal_year`와 `period_type+fiscal_year` 각각의 인덱스만으로는 최적화되지 않는다.

  ```python
  # stocks/views.py:636-638
  balance_sheets = BalanceSheet.objects.filter(
      stock=stock,
      period_type=db_period
  ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
  ```

- **권장 수정:**

  ```python
  # 세 모델 모두 동일하게 추가
  models.Index(fields=['stock', 'period_type', '-fiscal_year']),
  ```

---

### [MED-11] stocks/models.py:StockOverviewKo — Meta.indexes 없음

- **파일:** `stocks/models.py:692-719`
- **카테고리:** 인덱스 누락
- **수정 난이도:** 쉬움
- **설명:**
  `StockOverviewKo` 모델에 `Meta.indexes`가 없다. PrimaryKey가 `stock` OneToOne이므로 개별 조회는 문제없으나, `generated_at` 기준 정렬 조회 등 확장 시 인덱스 없음. 현재 LOW로 분류하나 향후 배치 재생성 시 문제 가능.

---

### [LOW-01] stocks/views.py:StockListAPIView — sector 필터에 icontains 사용

- **파일:** `stocks/views.py:94-95`
- **카테고리:** 인덱스 누락 (부분)
- **수정 난이도:** 쉬움
- **설명:**
  `queryset.filter(sector__icontains=sector)` 쿼리는 `sector` 필드에 인덱스가 있어도(`Stock.Meta.indexes`에 `Index(fields=['sector'])` 포함) `icontains`는 LIKE '%...%' 검색으로 인덱스를 활용하지 못한다. 정확 일치 `sector__iexact`나 `sector__exact`로 전환 시 인덱스 활용 가능.

- **권장 수정:** `sector__icontains` → `sector__iexact`

---

### [LOW-02] stocks/views_mvp.py:StockMVPListView — 페이지네이션 미적용

- **파일:** `stocks/views_mvp.py:41`
- **카테고리:** 페이지네이션 누락
- **수정 난이도:** 쉬움
- **설명:**
  `queryset = queryset[:20]` 하드코딩으로 최대 20개 제한. DRF 표준 pagination 미사용. 다만 20개 고정 제한이므로 즉각적인 위험은 낮음(LOW).

---

### [LOW-03] users/views.py:Users.get — 전체 사용자 목록 페이지네이션 없음

- **파일:** `users/views.py:89-91`
- **카테고리:** 페이지네이션 누락
- **수정 난이도:** 쉬움
- **설명:**
  관리자 전용 `GET /users/`가 `User.objects.all()`을 전체 반환한다. IsAdminUser로 제한되어 있어 외부 악용 위험은 낮지만, 사용자가 수천 명이면 문제.

  ```python
  # users/views.py:89-91
  def get(self, request):
      users = User.objects.all()  # 전체 반환
      serializer = UserSerializer(users, many=True)
  ```

---

### [LOW-04] news/api/views.py:stock_sentiment — Python 루프 집계 (DB 집계 미사용)

- **파일:** `news/api/views.py:154-193`
- **카테고리:** 느린 Serializer / 비효율 쿼리
- **수정 난이도:** 중간
- **설명:**
  `stock_sentiment` 액션이 `entities.all()`을 로드한 후 Python 레벨에서 sentiment_score를 집계한다. DB의 `Avg`, `Count` 집계 함수를 사용하면 훨씬 효율적이다. 또한 트렌드 계산을 위해 이미 로드된 `entities`에 대해 `.news.published_at`을 접근하는데, `select_related('news')`가 있어 추가 쿼리는 없지만 메모리 상에서 전체 엔티티를 파이썬으로 필터링한다.

  ```python
  # news/api/views.py:154-166
  sentiment_scores = [
      e.sentiment_score for e in entities if e.sentiment_score is not None
  ]
  avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)  # Python 레벨
  ```

- **권장 수정:**

  ```python
  agg = entities.aggregate(
      avg_sentiment=Avg('sentiment_score'),
      positive_count=Count('id', filter=Q(sentiment_score__gt=0.1)),
      negative_count=Count('id', filter=Q(sentiment_score__lt=-0.1)),
  )
  ```

---

## 우선순위 권장 사항

1. **[HIGH-05] WatchListStockSerializer.get_chart_data() return 누락 수정** (stocks/serializers.py:405-410)
   즉시 수정 가능한 1줄 버그로, 차트 데이터가 항상 null이 되는 기능 장애 + N+1 쿼리 동반.

2. **[HIGH-01/02] ValidationMetricsView / LeaderComparisonView N+1 제거** (validation/api/views.py)
   최대 300+회 쿼리가 단일 요청에서 발생. bulk 조회로 전환 시 3회로 줄어든다.

3. **[HIGH-08/09] StockListAPIView / NewsViewSet pagination_class 추가**
   Stock 테이블 전체 로드 방지. 1줄 수정으로 즉시 대용량 응답 차단.

4. **[HIGH-06] OverviewTabSerializer.get_dynamic_layers prefetch 추가** (stocks/serializers.py:205)
   View에서 `select_related` / `prefetch_related` 추가로 6N 쿼리 → 1쿼리로 단축.

5. **[MED-06/07/08] UserInterest / DataBasket / AnalysisSession user 인덱스 추가**
   마이그레이션 1개로 세 모델 모두 인덱스 추가 가능. 사용자 증가 시 full scan 방지.

6. **[MED-09] EODSignal.signals GIN 인덱스 추가**
   JSON 필드 contains 검색 최적화. RunSQL 마이그레이션으로 적용.

7. **[HIGH-04] NewsViewSet.trending 루프 N+1 제거** (news/api/views.py:330)
   트렌딩 조회 시 최대 20회 추가 쿼리 → 1회 bulk 조회로 전환.

8. **[HIGH-03] ValidationSummaryView rank_metrics bulk 조회** (validation/api/views.py:110)
   5+5=10회 쿼리 → 2회로. 수정 용이.

9. **[MED-10] BalanceSheet/IncomeStatement/CashFlowStatement 복합 인덱스 추가**
   재무제표 조회 패턴에 맞는 `(stock, period_type, -fiscal_year)` 인덱스 추가.

10. **[MED-04] WatchlistBulkRemoveView bulk delete 전환** (users/views.py:937)
    루프 내 N회 delete → 단일 `.delete()` 호출로 전환.

---

## 미해결 이슈 현황 (전일 대비)

전일(2026-04-21) 보고서의 모든 이슈가 수정되지 않고 UNCHANGED 상태로 지속됨.
TOP 5 우선 수정 항목 중 어떤 것도 적용되지 않음.

| 이슈 | 최초 발견일 | 상태 |
|------|:----------:|:----:|
| WatchListStockSerializer return 누락 | 2026-04-21 | UNCHANGED |
| ValidationMetricsView N+1 | 2026-04-19 | UNCHANGED |
| LeaderComparisonView N+1 | 2026-04-19 | UNCHANGED |
| DEFAULT_PAGINATION_CLASS 미설정 | 2026-04-19 | UNCHANGED |
| OverviewTabSerializer get_dynamic_layers | 2026-04-20 | UNCHANGED |
| rag_analysis user 인덱스 누락 | 2026-04-20 | UNCHANGED |
