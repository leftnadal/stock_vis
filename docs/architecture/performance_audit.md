# API 성능 감사 보고서

**감사일**: 2026-04-14
**브랜치**: `data_structure_remodeling_V1`
**감사 범위**: Views 17개, Models 7개, Serializers 전체, DRF 설정

---

## 요약

| 심각도 | 이슈 수 |
|--------|---------|
| **HIGH** | 10 |
| **MED** | 11 |
| **LOW** | 7 |
| **총합** | **28** |

| 카테고리 | HIGH | MED | LOW |
|----------|------|-----|-----|
| N+1 쿼리 | 4 | 1 | 1 |
| 인덱스 누락 | 2 | 6 | 0 |
| 느린 Serializer | 3 | 2 | 1 |
| 페이지네이션 누락 | 1 | 2 | 5 |

---

## 1. N+1 쿼리 탐지

### N1-01. IndicatorComparisonView — 루프 내 Stock + DailyPrice 개별 조회
- **파일**: `stocks/views_indicators.py:324-335`
- **심각도**: HIGH | **수정 난이도**: 쉬움
- **패턴**:
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol)        # 심볼당 1 쿼리
      prices = DailyPrice.objects.filter(stock=stock)  # 심볼당 1 쿼리
          .order_by('-date')[:50]
  ```
- **영향**: N개 심볼 요청 시 2N개 쿼리 발생 (10개 심볼 → 20 쿼리)
- **권장 수정**:
  ```python
  stocks_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=[s.upper() for s in symbols])}
  # DailyPrice도 bulk fetch 후 Python에서 그룹핑
  ```

### N1-02. news/api trending — 루프 내 NewsArticle 조회
- **파일**: `news/api/views.py:331-336`
- **심각도**: HIGH | **수정 난이도**: 중간
- **패턴**:
  ```python
  for item in trending_data:    # trending 종목별 루프
      symbol = item['symbol']
      recent_articles = NewsArticle.objects.filter(
          entities__symbol=symbol,
          published_at__gte=from_date
      ).distinct().order_by('-published_at')[:3]   # 종목당 1 쿼리
  ```
- **영향**: limit 기본값 10일 때 → 10 추가 쿼리
- **권장 수정**: 전체 심볼에 대해 한 번에 조회 후 Python 그룹핑. 단, 캐시(5분)가 적용되어 있어 실제 빈도는 낮음.

### N1-03. validation LeaderComparisonView — 루프 내 3중 쿼리
- **파일**: `validation/api/views.py:361-371`
- **심각도**: HIGH | **수정 난이도**: 높음
- **패턴**:
  ```python
  for cat, mc in all_metrics:                                     # 30+ metrics
      md = MetricDefinition.objects.filter(pk=mc).first()          # 쿼리 1
      company_snap = CompanyMetricSnapshot.objects.filter(...).first()  # 쿼리 2
      leader_snap = CompanyMetricSnapshot.objects.filter(...).first()   # 쿼리 3
  ```
- **영향**: 30개 지표 × 3 쿼리 = **90+ DB 히트**
- **권장 수정**:
  ```python
  metric_codes = [mc for _, mc in all_metrics]
  metrics_map = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_codes)}
  company_snaps = {s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
      symbol=stock, fiscal_year=latest_fy, metric_code_id__in=metric_codes, value_status='normal')}
  leader_snaps = {s.metric_code_id: s for s in CompanyMetricSnapshot.objects.filter(
      symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id__in=metric_codes, value_status='normal')}
  ```

### N1-04. validation MetricDetailView — 루프 내 PeerMetricBenchmark 조회
- **파일**: `validation/api/views.py:268-276`
- **심각도**: HIGH | **수정 난이도**: 중간
- **패턴**:
  ```python
  snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('fiscal_year')[:5]
  for s in snaps:
      peer_bench = PeerMetricBenchmark.objects.filter(
          symbol=stock, fiscal_year=s.fiscal_year, metric_code=md
      ).first()   # 스냅샷당 1 쿼리
  ```
- **영향**: 5개 연도 × 1 쿼리 = 5 추가 쿼리
- **권장 수정**: `fiscal_year__in=[...]` 한 번에 조회 후 dict 매핑

### N1-05. news/api DailyNewsKeyword — 풀 모델 인스턴스 반복
- **파일**: `news/api/views.py:1787-1801`
- **심각도**: MED | **수정 난이도**: 쉬움
- **패턴**: `for kw in kw_qs:` — 스칼라 필드만 사용하면서 전체 모델 인스턴스 로드
- **권장 수정**: `.values('date', 'status', 'prompt_tokens', ...)` 사용

### N1-06. StockMVPListView — 단순 루프 (FK 접근 없음)
- **파일**: `stocks/views_mvp.py:41-55`
- **심각도**: LOW | **수정 난이도**: 쉬움
- **패턴**: `Stock.objects.all()[:20]` 루프. FK 접근은 없으나 `.values()` 최적화 가능
- **참고**: 20건 제한으로 실질 영향 미미

---

## 2. 인덱스 누락

### IDX-01. NewsArticle.created_at — db_index 없음
- **파일**: `news/models.py:186`
- **심각도**: HIGH | **수정 난이도**: 쉬움
- **현재**: `created_at = models.DateTimeField(auto_now_add=True)` — 인덱스 없음
- **사용처**: `serverless/admin_status_service.py:548` `.filter(created_at__gte=last_24h).count()`
- **영향**: NewsArticle 테이블은 지속 성장하는 대용량 테이블. 시간 범위 조회에 full scan 발생
- **권장 수정**: `db_index=True` 추가 또는 `Meta.indexes`에 `models.Index(fields=['-created_at'])` 추가

### IDX-02. UserInterest — user+created_at 복합 인덱스 없음
- **파일**: `users/models.py:249-266`
- **심각도**: HIGH | **수정 난이도**: 쉬움
- **현재**: `unique_together = ('user', 'interest_type', 'value')` 만 존재, `created_at` 정렬용 인덱스 없음
- **사용처**: `users/views.py:967` `.filter(user=request.user).order_by('-created_at')`
- **권장 수정**: `Meta.indexes`에 `models.Index(fields=['user', '-created_at'])` 추가

### IDX-03. SP500Constituent — sector+is_active 복합 인덱스 없음
- **파일**: `stocks/models.py:682-686`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `indexes = [models.Index(fields=['is_active', 'symbol'])]` — sector/sub_sector 복합 없음
- **사용처**: `news/models.py:645` `.filter(sector=self.value, is_active=True)`
- **권장 수정**: `models.Index(fields=['sector', 'is_active'])`, `models.Index(fields=['sub_sector', 'is_active'])` 추가

### IDX-04. DataBasket — user+updated_at 복합 인덱스 없음
- **파일**: `rag_analysis/models.py:28-31`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `ordering = ["-updated_at"]` 설정되어 있으나 인덱스 없음
- **사용처**: `rag_analysis/views.py:73` `.filter(user=request.user)` (ordering 자동 적용)
- **권장 수정**: `models.Index(fields=['user', '-updated_at'])` 추가

### IDX-05. AnalysisSession — user+updated_at, status 인덱스 없음
- **파일**: `rag_analysis/models.py:165-168`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `ordering = ["-updated_at"]` 설정, 인덱스 없음
- **사용처**: `rag_analysis/views.py:433` `.filter(user=request.user).prefetch_related('messages')`
- **권장 수정**: `models.Index(fields=['user', '-updated_at'])`, `models.Index(fields=['status'])` 추가

### IDX-06. AnalysisMessage — session+created_at 복합 인덱스 없음
- **파일**: `rag_analysis/models.py:212-215`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `ordering = ["created_at"]` 설정, 인덱스 없음
- **사용처**: `rag_analysis/views.py:503` 세션별 메시지 조회 시 created_at 정렬
- **권장 수정**: `models.Index(fields=['session', 'created_at'])` 추가

### IDX-07. SP500Constituent.sub_sector — 단독 인덱스 없음
- **파일**: `stocks/models.py:657`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `sub_sector = models.CharField(max_length=100, blank=True, default='')` — db_index 없음
- **사용처**: `news/models.py:651` `.filter(sub_sector=self.value, is_active=True)`
- **권장 수정**: IDX-03의 복합 인덱스로 함께 해결

---

## 3. 느린 Serializer

### SER-01. WatchListStockSerializer — DailyPrice 쿼리 in SerializerMethodField
- **파일**: `stocks/serializers.py:398-409`
- **심각도**: HIGH | **수정 난이도**: 중간
- **패턴**:
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()  # 주식당 1 쿼리

  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]  # 주식당 1 쿼리
  ```
- **영향**: 리스트 뷰에서 N개 주식 × 2 쿼리 = 2N 추가 쿼리
- **권장 수정**: View에서 `Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7])` 또는 Subquery annotation

### SER-02. OverviewTabSerializer.get_dynamic_layers — 6개 관계 모델 개별 접근
- **파일**: `stocks/serializers.py:205-307`
- **심각도**: HIGH | **수정 난이도**: 중간
- **패턴**: `obj.category_signals.all()`, `obj.validation_news_summary`, `obj.sensitivity_profile`, `obj.growth_stage`, `obj.capital_dna`, `obj.narrative_tag` — 각각 1 쿼리
- **영향**: 객체당 최대 6 추가 쿼리. 코드 내 TODO 주석 존재 (line 208)
- **참고**: 현재 이 serializer를 사용하는 리스트 뷰가 없다면 영향 제한적

### SER-03. ThesisDetailSerializer.get_indicator_count — count() 쿼리
- **파일**: `thesis/serializers/thesis_serializers.py:56-57`
- **심각도**: HIGH | **수정 난이도**: 쉬움
- **패턴**:
  ```python
  def get_indicator_count(self, obj):
      return obj.indicators.filter(is_active=True).count()  # thesis당 1 쿼리
  ```
- **권장 수정**: View queryset에서 `.annotate(active_indicator_count=Count('indicators', filter=Q(indicators__is_active=True)))` 사용

### SER-04. MarketMoverListSerializer — 반복적 서비스 인스턴스 생성
- **파일**: `serverless/serializers.py:121-137`
- **심각도**: MED | **수정 난이도**: 쉬움
- **패턴**:
  ```python
  def get_sector_alpha_display(self, obj):
      calc = IndicatorCalculator()  # 객체당 새 인스턴스 생성
      return calc.format_sector_alpha_display(obj.sector_alpha)
  # get_etf_sync_display, get_volatility_pct_display도 동일
  ```
- **영향**: DB 쿼리는 아니지만 불필요한 인스턴스 생성 오버헤드
- **권장 수정**: Serializer `__init__`에서 한 번 생성하거나 `@staticmethod`로 변환

### SER-05. ScreenerAlertSerializer.get_preset_name — FK 접근 without select_related
- **파일**: `serverless/serializers.py:531-535`
- **심각도**: MED | **수정 난이도**: 쉬움
- **패턴**:
  ```python
  def get_preset_name(self, obj):
      if obj.preset:
          return f"{obj.preset.icon} {obj.preset.name}"  # preset FK 접근
  ```
- **권장 수정**: View에서 `.select_related('preset')` 추가

### SER-06. DataBasketSerializer.get_can_add_item — count() 호출
- **파일**: `rag_analysis/models.py:36-38` (serializer에서 호출)
- **심각도**: LOW | **수정 난이도**: 중간
- **패턴**: `can_add_item()` → `self.items.count()` — basket당 1 쿼리
- **참고**: `items_count`, `current_units`도 동일 패턴. prefetch_related('items')가 이미 적용되어 있으면 영향 감소

---

## 4. 페이지네이션 누락

### PAG-01. REST_FRAMEWORK — 글로벌 페이지네이션 미설정
- **파일**: `config/settings.py:331-339`
- **심각도**: HIGH | **수정 난이도**: 쉬움
- **현재**: `DEFAULT_PAGINATION_CLASS`와 `PAGE_SIZE` 미설정
- **영향**: 모든 뷰에서 명시적 설정 없으면 무제한 반환
- **권장 수정**:
  ```python
  REST_FRAMEWORK = {
      ...
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 50,
  }
  ```

### PAG-02. StockListAPIView — pagination_class 없음
- **파일**: `stocks/views.py:75-105`
- **심각도**: MED | **수정 난이도**: 쉬움
- **현재**: `generics.ListAPIView` 상속하지만 글로벌 설정 없어 페이지네이션 미적용
- **영향**: `Stock.objects.all()` — 수천 건 반환 가능

### PAG-03. Users.get — 전체 유저 리스트 무제한 반환
- **파일**: `users/views.py:89-92`
- **심각도**: MED | **수정 난이도**: 쉬움
- **패턴**: `User.objects.all()` → `UserSerializer(users, many=True)` — Admin 전용이지만 페이지네이션 없음

### PAG-04. PortfolioListCreateView.get — 페이지네이션 없음
- **파일**: `users/views.py:255-259`
- **심각도**: LOW | **수정 난이도**: 쉬움
- **참고**: 개인 포트폴리오이므로 대량 데이터 가능성 낮음. `select_related('stock')`은 적용됨(좋음)

### PAG-05. NewsViewSet — 명시적 pagination_class 없음
- **파일**: `news/api/views.py:42-46`
- **심각도**: LOW | **수정 난이도**: 쉬움
- **현재**: `ReadOnlyModelViewSet` — 글로벌 설정이 없으므로 페이지네이션 미적용
- **참고**: PAG-01 수정 시 자동 해결

### PAG-06. DataBasketListCreateView — 페이지네이션 없음
- **파일**: `rag_analysis/views.py:71-75`
- **심각도**: LOW | **수정 난이도**: 쉬움
- **참고**: 개인 basket 목록이므로 대량 데이터 가능성 낮음

### PAG-07. WatchlistStocksView — 페이지네이션 없음
- **파일**: `users/views.py:811` (items 조회)
- **심각도**: LOW | **수정 난이도**: 쉬움
- **참고**: 워치리스트당 종목 수는 제한적. WatchlistListCreateView(line 591-620)는 올바르게 구현됨

### PAG-08. stocks/views_mvp.py StockMVPListView — 하드코딩 [:20] 제한
- **파일**: `stocks/views_mvp.py:41`
- **심각도**: LOW | **수정 난이도**: 쉬움
- **참고**: 하드코딩 20건 제한으로 실질 문제는 적으나, 표준 페이지네이션 패턴이 아님

---

## 잘 구현된 패턴 (참고)

| 파일 | 라인 | 패턴 | 비고 |
|------|------|------|------|
| `users/views.py` | 257 | `Portfolio.objects.filter(...).select_related('stock')` | 올바른 FK 최적화 |
| `users/views.py` | 647 | `Watchlist.objects.prefetch_related('items__stock')` | 올바른 중첩 prefetch |
| `users/views.py` | 811 | `WatchlistItem.objects.filter(...).select_related('stock')` | 올바른 FK 최적화 |
| `users/views.py` | 591-620 | `WatchlistListCreateView` 수동 Paginator | 올바른 페이지네이션 구현 |
| `news/api/views.py` | 45 | `NewsArticle.objects.all().prefetch_related('entities')` | M2M 최적화 |
| `stocks/views_eod.py` | 77 | `EODSignal.objects.filter(...).select_related('stock')` | 올바른 FK 최적화 |
| `news/models.py` | 192-198 | 5개 복합 인덱스 | 충분한 인덱스 커버리지 |
| `stocks/models.py` | 185-189 | DailyPrice 3개 복합 인덱스 | 핵심 테이블 인덱스 충분 |

---

## 수정 우선순위 로드맵

### Phase 1: 즉시 (영향 큰 쉬운 수정)
1. **PAG-01**: `config/settings.py`에 글로벌 페이지네이션 설정 → 6개 이슈 일괄 해결
2. **IDX-01**: `NewsArticle.created_at`에 `db_index=True` 추가
3. **IDX-02**: `UserInterest`에 `(user, -created_at)` 복합 인덱스 추가
4. **SER-03**: `ThesisDetailSerializer` → View annotate로 전환

### Phase 2: 단기 (중간 난이도)
5. **N1-01**: `IndicatorComparisonView` bulk fetch 리팩토링
6. **N1-04**: `validation MetricDetailView` PeerMetricBenchmark bulk fetch
7. **SER-01**: `WatchListStockSerializer` DailyPrice prefetch 전략
8. **IDX-03~07**: rag_analysis, SP500Constituent 인덱스 일괄 추가 (migration 1개로)

### Phase 3: 중기 (높은 난이도)
9. **N1-03**: `LeaderComparisonView` 3중 쿼리 → bulk fetch 대규모 리팩토링
10. **SER-02**: `OverviewTabSerializer` dynamic_layers prefetch (TODO 이미 존재)
11. **N1-02**: `news trending` 루프 최적화 (캐시 있으나 구조 개선)

---

## 부록: 검사 대상 파일 목록

### Views (17개)
| 파일 | N+1 이슈 | 페이지네이션 | 비고 |
|------|----------|-------------|------|
| stocks/views.py | - | PAG-02 | StockListAPIView |
| stocks/views_search.py | - | - | StockService 사용 |
| stocks/views_exchange.py | - | - | FMP API 전용 |
| stocks/views_eod.py | - | - | select_related 올바름 |
| stocks/views_screener.py | - | - | FMP API 전용 |
| stocks/views_market_movers.py | - | - | FMP API 전용 |
| stocks/views_fundamentals.py | - | - | FMP API 전용 |
| stocks/views_indicators.py | N1-01 | - | 루프 내 개별 조회 |
| stocks/views_mvp.py | N1-06 | PAG-08 | 경미 |
| users/views.py | - | PAG-03,04 | select_related 양호 |
| news/api/views.py | N1-02 | PAG-05 | trending 루프 |
| macro/views.py | - | - | 이슈 없음 |
| rag_analysis/views.py | - | PAG-06 | prefetch 양호 |
| serverless/views_admin.py | - | - | Admin 전용 |
| validation/api/views.py | N1-03,04 | - | 루프 내 다중 쿼리 |
| chainsight/api/views.py | - | - | 이슈 없음 |
| sec_pipeline/views.py | - | - | 이슈 없음 |

### Models (7개)
| 파일 | 인덱스 상태 | 이슈 |
|------|------------|------|
| stocks/models.py | 양호 | IDX-03 (SP500Constituent) |
| users/models.py | 부분 양호 | IDX-02 (UserInterest) |
| news/models.py | 양호 | IDX-01 (created_at) |
| serverless/models.py | 양호 | 이슈 없음 |
| rag_analysis/models.py | 미흡 | IDX-04,05,06 |
| sec_pipeline/models.py | 양호 | 이슈 없음 |
| graph_analysis/models.py | 양호 | 이슈 없음 |
