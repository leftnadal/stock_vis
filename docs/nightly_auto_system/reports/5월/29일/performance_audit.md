# API 성능 감사 보고서

- **작성일**: 2026-05-29
- **모드**: 읽기 전용 (코드 수정 없음)
- **범위**: 뷰 17개 · 모델 7개 · 관련 Serializer 11개
- **검사 항목**: ① N+1 쿼리 ② 인덱스 누락 ③ 느린 Serializer ④ 페이지네이션 누락

> 검증 메모: 자동 분석 에이전트 결과를 직접 코드 확인으로 교차검증했습니다.
> `rag_analysis/views.py`의 N+1 위치는 에이전트가 처음 보고한 `257-281`(실제로는 BasketItem 생성 코드)이 아니라
> **`237` 루프 내부 `298~338`** 임을 직접 확인하여 보정했습니다.

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 / Slow Serializer | 인덱스 누락 | 페이지네이션 | 합계 |
|--------|----------------------|------------|-------------|------|
| **HIGH** | 4 | 0 | 2 | **6** |
| **MED**  | 5 | 3 | 0 | **8** |
| **LOW**  | 4 | 3 | 0 | **7** |
| **합계** | 13 | 6 | 2 | **21** |

### 최우선 수정 권장 (HIGH 6건)

| # | 위치 | 유형 | 난이도 |
|---|------|------|--------|
| H-1 | `stocks/serializers.py:205-307` | N+1 (6개 OneToOne/역참조 × N) | 중간 |
| H-2 | `stocks/serializers.py:398-409` | N+1 (SerializerMethodField 2쿼리 × N) | 중간 |
| H-3 | `rag_analysis/views.py:237→298-338` | N+1 (data_type 루프마다 4종 조회) | 쉬움 |
| H-4 | `stocks/views_mvp.py:17-41` | 페이지네이션 누락 (수동 슬라이스 의존) | 쉬움 |
| H-5 | `users/views.py:88-94` | 페이지네이션 누락 (전체 User 반환) | 중간 |
| H-6 | `stocks/serializers.py:190-203` | N+1 (overview_ko OneToOne × N) | 쉬움 |

> ⚠️ **맥락 주의**: H-1/H-6의 동적 레이어/한글 개요는 현재 데이터 유입 전 단계(serializer 내 `TODO: prefetch 적용 필요` 주석 존재). 데이터가 채워지는 시점에 실측 임팩트가 급증하므로 **데이터 유입 전 선제 수정**을 권장합니다.

---

## 1. N+1 쿼리 / 느린 Serializer (상세)

### H-1 [HIGH·중간] OverviewTabSerializer — 6개 관계를 행마다 개별 조회
- **파일:라인**: `stocks/serializers.py:205-307` (`get_dynamic_layers`)
- **코드**:
  ```python
  signals = list(obj.category_signals.all())   # 215  역참조 (다건)
  ns = obj.validation_news_summary             # 235  OneToOne
  sp = obj.sensitivity_profile                 # 252  OneToOne
  gs = obj.growth_stage                        # 267  OneToOne
  cd = obj.capital_dna                         # 281  OneToOne
  nt = obj.narrative_tag                        # 295  OneToOne
  ```
- **설명**: 한 Stock당 최대 6개의 추가 쿼리가 발생. 목록 응답(`many=True`)에서 N개 종목이면 최대 `6×N` 쿼리. 6,000 종목 전수 시 수천 쿼리로 폭증.
- **권장 수정**: 이 Serializer를 쓰는 뷰의 queryset에 선제 로딩 적용.
  ```python
  Stock.objects.select_related(
      'validation_news_summary', 'sensitivity_profile',
      'growth_stage', 'capital_dna', 'narrative_tag', 'overview_ko',
  ).prefetch_related('category_signals')
  ```
- **참고**: serializer 내 `# TODO: prefetch_related + 캐싱 레이어 적용 필요`(208라인) 주석이 이미 동일 부채를 명시.

### H-2 [HIGH·중간] WatchListStockSerializer — 가격 조회가 행마다 2쿼리
- **파일:라인**: `stocks/serializers.py:398-409`
- **코드**:
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
  ```
- **설명**: 종목당 2쿼리. 워치리스트 20종목이면 `2×20=40` 추가 쿼리.
- **권장 수정**: `Prefetch('dailyprice_set', DailyPrice.objects.order_by('-date'))`로 일괄 로딩 후 serializer에서 prefetch된 속성을 읽도록 변경. 또는 가격을 별도 엔드포인트로 분리.

### H-3 [HIGH·쉬움] RAG 바구니 추가 — data_type 루프마다 4종 재조회
- **파일:라인**: `rag_analysis/views.py:237`(루프) 내부 `298`, `310`, `322`, `335`, `338`
- **코드**:
  ```python
  for data_type in data_types:          # 237
      ...
      stock  = Stock.objects.filter(symbol=symbol).first()           # 298 / 310
      latest = DailyPrice.objects.filter(stock__symbol=symbol)...    # 322
      income = IncomeStatement.objects.filter(stock__symbol=symbol)  # 335
      balance= BalanceSheet.objects.filter(stock__symbol=symbol)     # 338
  ```
- **설명**: 동일 `symbol`에 대해 루프 반복마다 같은 Stock/Price/재무제표를 재조회. data_type 6종이면 동일 데이터를 최대 `4×6` 회 중복 조회.
- **권장 수정**: 루프 진입 **전에** `symbol` 기준 객체를 1회 조회해 변수화한 뒤 루프 안에서 재사용.
- **검증**: 에이전트 초기 보고의 `257-281`은 BasketItem 생성 코드로 오인용 → 직접 확인하여 실제 위치로 보정함.

### H-6 [HIGH·쉬움] OverviewTabSerializer.get_korean_overview — overview_ko 미선로딩
- **파일:라인**: `stocks/serializers.py:190-203`
- **코드**: `ko = obj.overview_ko  # 193  OneToOne`
- **설명**: `StockOverviewAPIView`는 `select_related('overview_ko')`를 적용(아래 M-3 참고)하나, `StockDetailView`·`StockCompleteDataAPIView` 경로에서는 미적용이라 행마다 1쿼리.
- **권장 수정**: 해당 serializer를 사용하는 모든 뷰 queryset에 `select_related('overview_ko')` 일관 적용.

---

### M-1 [MED·중간] IndicatorComparisonView — 심볼 루프 내 `.get()`
- **파일:라인**: `stocks/views_indicators.py:324-335`
- **코드**:
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol)                       # 328
      prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]
  ```
- **설명**: N개 심볼이면 `2×N` 쿼리.
- **권장 수정**: `Stock.objects.filter(symbol__in=symbols)`로 일괄 조회 + `Prefetch('dailyprice_set', DailyPrice.objects.order_by('-date'))` 후 dict 매핑으로 사용.

### M-2 [MED·중간] StockCompleteDataAPIView — 재무제표 3종 개별 조회
- **파일:라인**: `stocks/views.py:861`, `866`, `871`
- **코드**: BalanceSheet / IncomeStatement / CashFlowStatement 각각 `filter(stock=stock, period_type='annual').order_by('-fiscal_year')[:5]`
- **설명**: 단건 상세이므로 즉각 위험은 낮으나, 한 Stock에 대해 분리된 3쿼리. 향후 목록화 시 `3×N` 위험.
- **권장 수정**: `prefetch_related(Prefetch(...))` 3종 묶음 또는 현 구조 유지(단건 한정 시 허용 가능).

### M-3 [MED·쉬움] StockOverviewAPIView — 부분 select_related
- **파일:라인**: `stocks/views.py:502-504`
- **코드**: `Stock.objects.select_related('overview_ko').filter(symbol=symbol).first()`
- **설명**: `overview_ko`만 선로딩, serializer가 접근하는 나머지 5개 OneToOne(H-1)은 누락 → 요청당 최대 6 추가 쿼리.
- **권장 수정**: H-1의 `select_related`/`prefetch_related` 묶음을 동일 적용.

### M-4 [MED·중간] PortfolioSummary — 루프 내 모델 속성 접근
- **파일:라인**: `users/views.py:374-377`
- **코드**:
  ```python
  for portfolio in portfolios:               # 358행 select_related('stock')는 적용됨
      total_value += portfolio.total_value   # 모델 프로퍼티 — 추가 조회 여부 확인 필요
      total_cost  += portfolio.total_cost
  ```
- **설명**: `portfolio.total_value`/`total_cost`가 `stock.real_time_price` 등 추가 쿼리를 유발하는 프로퍼티라면 N+1. 358행에서 `select_related('stock')`은 이미 적용되어 stock FK 자체는 완화됨 — 프로퍼티 내부 구현이 또 다른 관계를 타는지 확인 필요.
- **권장 수정**: 합계를 DB `aggregate()`로 위임하거나, 프로퍼티가 의존하는 관계까지 선로딩. (조건부 — 프로퍼티 구현 확인 후 확정)

### M-5 [MED·중간] ValidationMetricsView._build_category — 루프 내 벤치마크 조회
- **파일:라인**: `validation/api/views.py:265-285`
- **코드**:
  ```python
  snaps = CompanyMetricSnapshot.objects.filter(...).order_by('fiscal_year')[:5]
  for s in snaps:
      peer_bench = PeerMetricBenchmark.objects.filter(
          symbol=stock, fiscal_year=s.fiscal_year, metric_code=md).first()
  ```
- **설명**: snap당 1쿼리, 최대 5회 N+1. metric_code 수만큼 배가.
- **권장 수정**: 연도 묶음으로 `PeerMetricBenchmark`를 `filter(fiscal_year__in=[...])` 일괄 조회 후 dict 매핑.

---

### L-1 [LOW·쉬움] serverless get_sector_alpha_display — 행마다 서비스 인스턴스화
- **파일:라인**: `serverless/serializers.py:121-137`
- **설명**: `SerializerMethodField`마다 `IndicatorCalculator()` 새로 생성. 순수 포맷 함수면 DB 영향은 없으나 `many=True`에서 N회 인스턴스화 오버헤드.
- **권장 수정**: 포맷 함수를 모듈 레벨 순수 함수로 분리하거나 모델 필드 사전 저장.

### L-2 [LOW·쉬움] PortfolioSummary — exists() + count() 이중 쿼리
- **파일:라인**: `users/views.py:360`(exists) + `382`(count)
- **설명**: 동일 queryset에 대해 boolean 판정과 개수 조회를 별도 2쿼리로 수행.
- **권장 수정**: 한 번 `list()`로 평가 후 `len()` 사용하거나, 합계 루프에서 카운트 누적.

### L-3 [LOW·쉬움] 즐겨찾기 멤버십 — all() 후 파이썬 비교
- **파일:라인**: `users/views.py:212-215`
- **코드**: `if stock in user.favorite_stock.all():`
- **권장 수정**: `user.favorite_stock.filter(id=stock.id).exists()`로 DB 위임.

### L-4 [LOW·쉬움] NewsArticle by-symbol — distinct() + entities 미prefetch
- **파일:라인**: `news/api/views.py:104-107`
- **코드**: `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')`
- **설명**: M2M 역참조 조인 + `distinct()`로 DB GROUP BY 부하. 후속 entities 접근 시 N+1 가능.
- **권장 수정**: `.prefetch_related('entities')` 추가.

---

## 2. 인덱스 누락 (상세)

> 모든 항목 수정난이도 **중간** (마이그레이션 필요). ForeignKey/unique 필드는 자동 인덱스이므로 제외.

| 심각도 | 모델·필드 | 파일:라인 | 쿼리 근거 | 권장 |
|--------|----------|----------|----------|------|
| **MED** | `StockNews.created_at` | `stocks/models.py:901` | `order_by('-created_at')` 최신순 조회 | `Meta.indexes`에 `Index(fields=['-created_at'])` |
| **MED** | `StockNews.sentiment` | `stocks/models.py:899` | 감성별 필터 | `db_index=True` |
| **MED** | `NewsArticle.category` | `news/models.py:82-87` | `filter(category=...)` (news/views.py:286) | `Index(fields=['category', '-published_at'])` |
| **LOW** | `NewsEntity.entity_type` | `news/models.py:237-241` | 타입별 필터 (단독 인덱스 없음, 복합만 존재) | `Index(fields=['entity_type'])` |
| **LOW** | `MarketBreadth.breadth_signal` | `serverless/models.py:309-314` | 신호별 필터 가능성 | `db_index=True` |
| **LOW** | `UnmatchedCompanyQueue.resolved_ticker` | `sec_pipeline/models.py:331` | 해결 상태 추적 필터 | `db_index=True` |

**우선순위**: ① `StockNews.created_at` ② `StockNews.sentiment` ③ `NewsArticle.category` (행이 많은 뉴스/시계열 테이블의 정렬·필터 필드).

### 인덱스 적정(문제 없음 — 확인 완료)
- `serverless.StockKeyword.status/symbol` → 복합 인덱스 `['date','status']`, `['symbol','-date']` 존재 ✓
- `news.NewsArticle.is_archived` → `db_index=True` ✓
- `rag_analysis.UsageLog.cached/request_type` → 복합 인덱스 존재 ✓
- `graph_analysis.CorrelationEdge.is_anomaly` → 복합 인덱스 존재 ✓

---

## 3. 페이지네이션 누락 (상세)

### H-4 [HIGH·쉬움] StockMVPListView — 수동 슬라이스 의존
- **파일:라인**: `stocks/views_mvp.py:17-41`
- **코드**:
  ```python
  class StockMVPListView(APIView):       # 17
      queryset = Stock.objects.all()     # 29
      ...
      queryset = queryset[:20]           # 41  수동 슬라이스, pagination_class 없음
  ```
- **설명**: `APIView`라 `pagination_class` 미적용. 현재 `[:20]` 수동 슬라이스로 막혀 있으나, 슬라이스가 제거/이동되면 전체 반환. 클라이언트에 페이지 메타데이터 부재.
- **권장 수정**: `PageNumberPagination` 클래스 도입 또는 `ListAPIView` + `pagination_class`로 전환.

### H-5 [HIGH·중간] User 목록 — 전체 반환
- **파일:라인**: `users/views.py:88-94`
- **코드**:
  ```python
  def get(self, request):
      users = User.objects.all()
      serializer = UserSerializer(users, many=True)
      return Response(serializer.data)
  ```
- **설명**: 페이지네이션 없이 전체 User 직렬화. 사용자 수 증가 시 응답 폭주.
- **권장 수정**: DRF `PageNumberPagination` 또는 관리자 전용이면 접근 제어 + 페이지네이션 병행.

### 페이지네이션 적정(문제 없음 — 확인 완료)
- `news/api/views.py:58-60` `NewsViewSet` → `pagination_class = NewsArticlePagination` ✓
- `chainsight/api/views.py` 그래프 쿼리 → Neo4j `limit` 파라미터 + 상한선(30) 관리 ✓

---

## 부록 — 긍정적 패턴 (이미 적용됨)

- `users/views.py:358` Portfolio 조회 `select_related('stock')` 적용
- `rag_analysis/views.py` 바스켓/메시지 `prefetch_related('items'/'messages')` 적용
- `news/api/views.py` NewsViewSet `prefetch_related('entities')` + 전용 페이지네이션
- 다수 시계열/상태 모델에 복합 인덱스 선제 정의

---

## 권장 조치 순서

1. **데이터 유입 전 선제 수정** (H-1·H-6·M-3): Overview 관계 6종 `select_related`/`prefetch_related` 일괄 적용 — 데이터 채워지기 전이 비용 최저 시점.
2. **루프 N+1 즉시 수정** (H-3·M-1·M-5): 루프 진입 전 일괄 조회로 전환 (난이도 낮음, 효과 큼).
3. **페이지네이션 보강** (H-4·H-5): 노출 엔드포인트 폭주 방지.
4. **인덱스 마이그레이션** (MED 3종): `StockNews.created_at/sentiment`, `NewsArticle.category` — 저트래픽 시간대 적용.
5. **워치리스트 가격 N+1** (H-2): Prefetch 또는 가격 분리 엔드포인트.

> 본 보고서는 정적 코드 분석 기반입니다. 실제 쿼리 수는 `django-debug-toolbar` 또는
> `CaptureQueriesContext`로 엔드포인트별 실측 후 확정하시길 권장합니다.
