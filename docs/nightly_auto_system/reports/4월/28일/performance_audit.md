# API 성능 감사 보고서

**감사일**: 2026-04-28
**브랜치**: feature/chainsight-graph-v2
**범위**: 17개 views 파일 + 7개 models 파일 + serializers + 전역 설정
**모드**: 읽기 전용 (코드 수정 없음)

---

## 요약

### 심각도별 이슈 수

| 심각도 | 개수 | 비고 |
|--------|------|------|
| **HIGH** | 13 | 즉시 조치 필요 (프로덕션 트래픽에서 OOM/슬로우 쿼리 직격) |
| **MED** | 18 | 점진적 성능 저하, 데이터 증가 시 악화 |
| **LOW** | 5 | 마이크로 최적화 또는 향후 대비 |
| **합계** | **36** | |

### 카테고리별 분포

| 카테고리 | HIGH | MED | LOW | 소계 |
|---------|------|-----|-----|------|
| N+1 쿼리 | 8 | 5 | 1 | 14 |
| 인덱스 누락 | 3 | 6 | 2 | 11 |
| 느린 Serializer | 0 | 4 | 1 | 5 |
| 페이지네이션 누락 | 2 | 3 | 1 | 6 |

### 앱별 분포

| 앱 | HIGH | MED | LOW |
|----|------|-----|-----|
| validation | 5 | 1 | 2 |
| stocks | 3 | 1 | 1 |
| users | 2 | 4 | 2 |
| news | 2 | 4 | 0 |
| rag_analysis | 1 | 4 | 0 |
| serverless | 1 | 1 | 0 |
| chainsight | 0 | 2 | 1 |
| config | 0 | 1 | 0 |

### 즉시 조치 권고 TOP 5

1. **config/settings.py** — 전역 `DEFAULT_PAGINATION_CLASS` 부재 (모든 ListAPIView가 무제한 응답 가능)
2. **validation/api/views.py:361** — `LeaderComparisonView`에서 100+ 개 N+1 쿼리
3. **stocks/views.py:75** — `StockListAPIView` pagination 누락 (전체 Stock 테이블 메모리 로드 위험)
4. **stocks/serializers.py:398** — `WatchListStockSerializer` 워치리스트당 2N+1 쿼리
5. **users/views.py:363** — `PortfolioSummaryView` 루프 내 property 호출로 FK 반복 액세스

---

## 상세

### 1. N+1 쿼리 이슈

#### 1.1 [HIGH] WatchListStockSerializer SerializerMethodField 2N+1
- **파일**: `stocks/serializers.py:398-409`
- **수정 난이도**: 중간
- **문제**:
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
  ```
- **설명**: 워치리스트 항목 N개당 `get_latest_price()` + `get_chart_data()` 추가 쿼리. 10개 watchlist → 최소 21개 쿼리.
- **권장 수정**: View QuerySet에 `prefetch_related(Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7]))` + Python 메모리 필터링.

#### 1.2 [HIGH] LeaderComparisonView 100+ N+1 (MetricDefinition)
- **파일**: `validation/api/views.py:361-364`
- **수정 난이도**: 중간
- **문제**:
  ```python
  for cat, mc in all_metrics:
      md = MetricDefinition.objects.filter(pk=mc).first()
  ```
- **설명**: `all_metrics`가 모든 카테고리×지표 조합(~100개)으로 카테고리당 100+ 쿼리.
- **권장 수정**: 메서드 시작 시 `MetricDefinition.objects.in_bulk(ids=all_metric_codes)` 한 번에 로딩.

#### 1.3 [HIGH] LeaderComparisonView 200+ N+1 (CompanyMetricSnapshot 양방향)
- **파일**: `validation/api/views.py:366-371`
- **수정 난이도**: 중간
- **문제**:
  ```python
  company_snap = CompanyMetricSnapshot.objects.filter(
      symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
  ).first()
  leader_snap = CompanyMetricSnapshot.objects.filter(
      symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
  ).first()
  ```
- **설명**: 메트릭당 2개 쿼리 × 100개 메트릭 = 200+ 쿼리.
- **권장 수정**: `metric_code_id__in=all_metric_codes`로 벌크 조회 후 dict 매핑.

#### 1.4 [HIGH] ValidationSummaryView N+1 (rank_metrics 루프)
- **파일**: `validation/api/views.py:112-117`
- **수정 난이도**: 쉬움
- **문제**:
  ```python
  for mc in rank_metrics:
      delta = CompanyBenchmarkDelta.objects.filter(
          symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
      ).first()
      if delta and delta.rank and delta.total:
          md = MetricDefinition.objects.filter(pk=mc).first()
  ```
- **설명**: 5개 지표 × 2 쿼리 = 10 쿼리.
- **권장 수정**: `CompanyBenchmarkDelta.objects.filter(..., metric_code_id__in=rank_metrics).select_related('metric_code')`.

#### 1.5 [HIGH] ValidationMetricsView N+1 (metric_codes 루프)
- **파일**: `validation/api/views.py:204-206`
- **수정 난이도**: 쉬움
- **문제**:
  ```python
  for mc in metric_codes:
      md = MetricDefinition.objects.filter(pk=mc).first()
  ```
- **설명**: 카테고리당 최대 20개 지표 × 1 쿼리.
- **권장 수정**: `MetricDefinition.objects.in_bulk(ids=metric_codes)`.

#### 1.6 [HIGH] ValidationMetricsView._build_metric N+1 (PeerMetricBenchmark 5년 루프)
- **파일**: `validation/api/views.py:265-276`
- **수정 난이도**: 중간
- **문제**:
  ```python
  snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('fiscal_year')[:5]
  for s in snaps:
      peer_bench = PeerMetricBenchmark.objects.filter(
          symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
      ).first()
  ```
- **설명**: 메트릭당 5년 × 1 쿼리 추가.
- **권장 수정**: `fiscal_year__in=[s.fiscal_year for s in snaps]`로 한 번에 조회 후 dict 매핑.

#### 1.7 [HIGH] PortfolioSummaryView 루프 내 property로 FK 액세스
- **파일**: `users/views.py:363-372`
- **수정 난이도**: 중간
- **문제**:
  ```python
  for portfolio in portfolios:
      total_value += portfolio.total_value  # property가 self.stock.real_time_price 액세스
      total_cost += portfolio.total_cost
  ```
- **설명**: `total_value`가 `Stock` FK를 참조하는 property → 행마다 FK 조회.
- **권장 수정**: `.aggregate(total_value=Sum(F('quantity') * F('stock__real_time_price')), total_cost=Sum(...))`.

#### 1.8 [HIGH] NewsViewSet.stock_sentiment Python 측 집계
- **파일**: `news/api/views.py:153-178`
- **수정 난이도**: 중간
- **문제**:
  ```python
  entities = NewsEntity.objects.filter(symbol=symbol, news__published_at__gte=from_date).select_related('news')
  sentiment_scores = [e.sentiment_score for e in entities if e.sentiment_score is not None]
  recent_scores = [e.sentiment_score for e in entities if ... e.news.published_at >= mid_date]
  ```
- **설명**: 전체 entities를 메모리에 로드 후 Python 필터링. 데이터 증가 시 메모리/시간 폭증.
- **권장 수정**: `aggregate(Avg('sentiment_score'), Count('id'))` + `Q()`로 DB 측 집계.

#### 1.9 [MED] AddFavorite/RemoveFavorite 멤버십 체크 시 M2M 전체 로드
- **파일**: `users/views.py:206, 234`
- **수정 난이도**: 쉬움
- **문제**:
  ```python
  if stock in user.favorite_stock.all():
  ```
- **설명**: M2M 전체를 메모리에 로드 후 `in` 체크.
- **권장 수정**: `user.favorite_stock.filter(id=stock.id).exists()`.

#### 1.10 [MED] UserFavorites M2M prefetch 누락
- **파일**: `users/views.py:185-190`
- **수정 난이도**: 쉬움
- **문제**:
  ```python
  favorite_stocks = user.favorite_stock.all()
  serializer = StockSerializer(favorite_stocks, many=True)
  ```
- **권장 수정**: `.prefetch_related('favorite_stock')`.

#### 1.11 [MED] Users.get() (Admin) M2M prefetch 누락
- **파일**: `users/views.py:89-92`
- **수정 난이도**: 쉬움
- **문제**: `User.objects.all()` 직렬화 시 `favorite_stock` 액세스마다 추가 쿼리.
- **권장 수정**: `.prefetch_related('favorite_stock')`.

#### 1.12 [MED] NewsViewSet.stock_news entities prefetch 누락
- **파일**: `news/api/views.py:89-104`
- **수정 난이도**: 쉬움
- **문제**: `NewsArticleListSerializer`가 `entities`를 직렬화하지만 prefetch 없음.
- **권장 수정**: `.prefetch_related('entities')`.

#### 1.13 [MED] OverviewTabSerializer.dynamic_layers 6개 OneToOne 미선택
- **파일**: `stocks/serializers.py:205-307`
- **수정 난이도**: 중간
- **문제**: stock당 6개 OneToOne 역참조 쿼리 (validation_news_summary, sensitivity_profile, growth_stage, capital_dna, narrative_tag, category_signals).
- **권장 수정**: View에서 `.select_related('overview_ko', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag').prefetch_related('category_signals')`.

#### 1.14 [HIGH] AdminNewsCategoryView 카테고리 루프 + resolve_symbols 쿼리
- **파일**: `serverless/views_admin.py:478-481`
- **수정 난이도**: 중간
- **문제**:
  ```python
  categories = NewsCollectionCategory.objects.all()
  for cat in categories:
      symbols = cat.resolve_symbols()
  ```
- **권장 수정**: 페이지네이션 추가 + bulk resolve 또는 결과 캐싱.

---

### 2. 인덱스 누락 이슈

#### 2.1 [HIGH] DataBasket.user FK 인덱스 없음
- **파일**: `rag_analysis/models.py:14-31`
- **수정 난이도**: 쉬움
- **문제**: `views.py:73, 433`에서 `filter(user=request.user)` + `ordering=['-updated_at']`이지만 인덱스 없음.
- **권장 수정**: `Meta.indexes = [models.Index(fields=['user', '-updated_at'])]`.

#### 2.2 [HIGH] AnalysisSession.user FK 인덱스 없음
- **파일**: `rag_analysis/models.py:138-148`
- **수정 난이도**: 쉬움
- **문제**: `views.py:433`에서 `filter(user=request.user).order_by('-updated_at')`이지만 인덱스 없음.
- **권장 수정**: `Meta.indexes = [models.Index(fields=['user', '-updated_at'])]`.

#### 2.3 [HIGH] CompanyBenchmarkDelta.fiscal_year 단독 인덱스 없음
- **파일**: `validation/models/benchmark_delta.py:58-63`
- **수정 난이도**: 중간
- **문제**: `(symbol, fiscal_year)` 복합 인덱스만 존재. fiscal_year 단독 필터 시 풀스캔.
- **권장 수정**: `models.Index(fields=['fiscal_year'])` 추가.

#### 2.4 [MED] BasketItem.basket FK 인덱스 없음
- **파일**: `rag_analysis/models.py:76-111`
- **수정 난이도**: 쉬움
- **권장 수정**: `Meta.indexes = [models.Index(fields=['basket', 'created_at'])]`.

#### 2.5 [MED] AnalysisSession.basket FK 인덱스 없음
- **파일**: `rag_analysis/models.py:143-148`
- **수정 난이도**: 쉬움
- **문제**: `select_related('basket')` 사용 중이지만 FK 인덱스 부재로 조인 비용 증가.
- **권장 수정**: `db_index=True` 또는 Meta.indexes 추가.

#### 2.6 [MED] UserInterest 복합 인덱스 부재
- **파일**: `users/models.py:249-268`
- **수정 난이도**: 쉬움
- **문제**: `unique_together`만 존재. `views.py:967`에서 `filter(user=request.user)` + `order_by('-created_at')` 사용.
- **권장 수정**: `models.Index(fields=['user', '-created_at'])`.

#### 2.7 [MED] SentimentHistory 부분 인덱스
- **파일**: `news/models.py:382-385`
- **수정 난이도**: 쉬움
- **문제**: `(symbol, avg_sentiment)` 조합 필터링 시 커버 안 됨.
- **권장 수정**: 사용 패턴 확인 후 `models.Index(fields=['symbol', 'avg_sentiment'])` 추가.

#### 2.8 [MED] Stock.exchange 인덱스 없음
- **파일**: `stocks/models.py:24`
- **수정 난이도**: 쉬움
- **문제**: `views_search.py:58-60`에서 NYSE/NASDAQ/AMEX 필터링.
- **권장 수정**: `db_index=True`.

#### 2.9 [MED] CategorySignal 복합 인덱스 부족
- **파일**: `validation/models/category_score.py:56-61`
- **수정 난이도**: 쉬움
- **문제**: symbol 단독만 있음. `views.py:80`에서 `filter(symbol=stock)` + fiscal_year 조회.
- **권장 수정**: `models.Index(fields=['symbol', 'fiscal_year'])`.

#### 2.10 [MED] CompanyMetricSnapshot value_status 미반영
- **파일**: `metrics/models/metric_snapshot.py:67-73`
- **수정 난이도**: 쉬움
- **문제**: `value_status='normal'` 필터링이 자주 사용되나 인덱스에 미포함.
- **권장 수정**: `models.Index(fields=['symbol', 'metric_code', 'value_status'])`.

#### 2.11 [MED] CoMentionEdge 정렬 인덱스 부족
- **파일**: `chainsight/models/relation_discovery.py:22-29`
- **수정 난이도**: 쉬움
- **문제**: `symbol_a/symbol_b/-co_mention_count` 단독 인덱스만 존재. union + order_by 시 비효율.
- **권장 수정**: `models.Index(fields=['symbol_a', '-co_mention_count'])`, `models.Index(fields=['symbol_b', '-co_mention_count'])`.

#### 2.12 [LOW] UserInterest.created_at 정렬 인덱스
- **파일**: `users/models.py:261`
- **수정 난이도**: 쉬움
- **권장 수정**: 2.6 항목과 통합 처리.

#### 2.13 [LOW] Portfolio.stock to_field='symbol' 인덱스 확인 필요
- **파일**: `users/models.py:27-28`
- **수정 난이도**: 쉬움
- **권장 수정**: `Stock.symbol`에 `db_index=True` 또는 unique 인덱스 확인.

---

### 3. 느린 Serializer 이슈

#### 3.1 [MED] WatchlistSerializer.stock_count property COUNT 쿼리
- **파일**: `users/models.py:187-190`, `users/serializers.py:232-233`
- **수정 난이도**: 중간
- **문제**:
  ```python
  @property
  def stock_count(self):
      return self.items.count()
  ```
- **설명**: 워치리스트 N개 직렬화 시 N개 COUNT 쿼리.
- **권장 수정**: View QuerySet에서 `.annotate(stock_count=Count('items'))` + serializer에서 property 제거.

#### 3.2 [MED] PortfolioDetailSerializer.get_portfolio_weight property 액세스
- **파일**: `users/serializers.py:95-109`
- **수정 난이도**: 중간
- **문제**: context의 total_portfolio_value 의존 + `obj.total_value` property가 FK 액세스.
- **권장 수정**: View에서 한 번 집계 후 dict로 전달, property 의존 제거.

#### 3.3 [MED] DataBasketSerializer.can_add_item COUNT 쿼리
- **파일**: `rag_analysis/serializers.py:29, 46-47`
- **수정 난이도**: 중간
- **문제**: `can_add_item()`가 `self.items.count()` 호출.
- **권장 수정**: View에서 `.annotate(item_count=Count('items'))` 추가 후 serializer에서 annotate 사용.

#### 3.4 [MED] OverviewTabSerializer 다른 view 사용 시 위험
- **파일**: `stocks/serializers.py:190-203`
- **수정 난이도**: 쉬움
- **권장 수정**: 1.13 항목과 통합. Serializer 상단에 `# Requires: select_related(...)` 주석 추가.

#### 3.5 [LOW] StockMVPListView 수동 dict 구성 비효율
- **파일**: `stocks/views_mvp.py:47-56`
- **수정 난이도**: 쉬움
- **권장 수정**: `StockListSerializer` 일관 사용으로 단순화.

---

### 4. 페이지네이션 누락 이슈

#### 4.1 [HIGH] StockListAPIView pagination_class 누락
- **파일**: `stocks/views.py:75-105`
- **수정 난이도**: 쉬움
- **문제**: 주석에는 "pagination으로 조회"라고 명시, 실제로는 미설정. 전역 `DEFAULT_PAGINATION_CLASS`도 없어 전체 Stock 테이블 응답 가능.
- **권장 수정**: `pagination_class = PageNumberPagination` 또는 전역 설정.

#### 4.2 [HIGH] NewsViewSet.stock_news 전량 직렬화
- **파일**: `news/api/views.py:89-104`
- **수정 난이도**: 중간
- **문제**: 종목당 1000+ 뉴스 가능. 무제한 직렬화.
- **권장 수정**: `pagination_class = PageNumberPagination` 또는 페이지네이터 수동 적용.

#### 4.3 [MED] config/settings.py 전역 페이지네이션 부재
- **파일**: `config/settings.py:338-353`
- **수정 난이도**: 쉬움
- **문제**: `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE` 미정의 → 모든 ListAPIView가 잠재적으로 무제한 응답.
- **권장 수정**:
  ```python
  'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
  'PAGE_SIZE': 20,
  ```

#### 4.4 [MED] NewsViewSet.market 하드코딩 limit
- **파일**: `news/api/views.py:270-274`
- **수정 난이도**: 쉬움
- **문제**: `[:limit]` 슬라이스만 있고 `has_next/total_count` 메타데이터 부재.
- **권장 수정**: DRF PageNumberPagination 도입.

#### 4.5 [MED] AdminNewsCategoryView 무제한 list
- **파일**: `serverless/views_admin.py:475-500`
- **수정 난이도**: 쉬움
- **권장 수정**: `Paginator` 또는 DRF pagination.

#### 4.6 [LOW] Users.get() (Admin) 무제한 list
- **파일**: `users/views.py:89-92`
- **수정 난이도**: 쉬움
- **권장 수정**: 4.3 전역 설정으로 자동 해결 가능.

#### 4.7 [LOW] NewsViewSet.trending 페이지네이션 부재
- **파일**: `news/api/views.py:299+`
- **수정 난이도**: 중간
- **권장 수정**: 최종 list에 pagination 적용.

#### 4.8 [LOW] UsageHistoryView page_size 하한 미보호
- **파일**: `rag_analysis/views.py:785`
- **수정 난이도**: 쉬움
- **문제**: `min(int(request.query_params.get('page_size', 20)), 100)` — 음수/0 보호 없음.
- **권장 수정**: `max(1, min(..., 100))`.

---

## 우선순위 액션 플랜

### Phase 1 — 1주 이내 (HIGH 처리)

1. `config/settings.py`에 전역 `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE=20` 추가 → 4.6, 부분적 4.1/4.2 자동 해결
2. `validation/api/views.py` Leader/ValidationSummary/ValidationMetrics에 `MetricDefinition.objects.in_bulk()` + `select_related('metric_code')` 적용 (1.2~1.6)
3. `stocks/views.py` `StockListAPIView`에 `pagination_class` 명시 (4.1)
4. `news/api/views.py` `stock_news`에 `prefetch_related('entities')` + pagination (4.2, 1.12)
5. `news/api/views.py` `stock_sentiment`을 DB `aggregate()`로 전환 (1.8)
6. `users/views.py` `PortfolioSummaryView`를 `aggregate(F())`로 전환 (1.7)
7. `stocks/serializers.py` `WatchListStockSerializer` SerializerMethodField를 prefetch 기반으로 재작성 (1.1)

### Phase 2 — 2주 이내 (MED 처리)

8. 인덱스 추가 마이그레이션 일괄 작성 (2.1~2.11)
9. `users/models.py` Watchlist `stock_count` annotate 전환 (3.1)
10. `rag_analysis/serializers.py` `can_add_item` annotate 전환 (3.3)
11. `users/views.py` favorite_stock 관련 prefetch + exists 패턴 적용 (1.9~1.11)
12. `stocks/serializers.py` OverviewTab dynamic_layers select_related 확장 (1.13)

### Phase 3 — 향후 (LOW + 리팩토링)

13. `validation/api/views.py` APIView → ListAPIView 전환 (4.3 등)
14. `stocks/views_mvp.py` 분기 단순화 (3.5)
15. 누락된 LOW 인덱스 보강 (2.12~2.13)

---

## 주의사항 (감사 한계)

- 본 보고서는 **정적 코드 분석** 기반. 실제 쿼리 카운트/실행 시간은 `django-silk` 또는 `connection.queries`로 검증 필요.
- `chainsight/api/`, `validation/api/`에 별도 `serializers.py` 파일이 없어 SerializerMethodField 분석 대상에서 제외됨 (APIView에서 dict 직접 구성).
- `prefetch_related` 추가 권장 시, 실제 view 컨텍스트에서 액세스 패턴 확인 후 적용 권장.
- 전역 페이지네이션 도입 시 기존 응답 스키마 변경 (results/count/next/previous 래핑) → 프론트엔드 호환성 검토 필요.
