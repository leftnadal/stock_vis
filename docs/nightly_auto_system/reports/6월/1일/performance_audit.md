# API 성능 감사 보고서

> **감사일**: 2026-06-01
> **범위**: 읽기 전용 정적 감사 (코드 수정 없음)
> **대상**: 뷰 17개 + 모델 7개 + serializer 전체
> **방법**: views/serializers/models 정적 분석 + 앱 디렉토리 `.filter()/.order_by()` 교차 검증
> **주의**: 지시서의 경로(`stocks/`, `macro/`, `chainsight/`)는 실제 모노레포 구조(`packages/shared/stocks/`, `apps/market_pulse/`, `apps/chain_sight/`)로 매핑하여 감사함.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 위치 |
|--------|------|-----------|
| 🔴 HIGH | **5** | validation 2건, chain_sight 1건, news 1건, indicators 1건 |
| 🟡 MED | **9** | users, rag, news, serverless, validation, serializer, 인덱스 |
| 🟢 LOW | **8** | 중복 count, 데드코드, 단건 +7쿼리, DISTINCT 무캐시 등 |
| **합계** | **22** | |

### 유형별 분포

| 유형 | HIGH | MED | LOW |
|------|------|-----|-----|
| N+1 쿼리 (루프 내 FK 조회) | 5 | 4 | 1 |
| select_related/prefetch 누락 | 0 | 3 | 1 |
| 페이지네이션 누락 | 0 | 2 | 1 |
| 느린 Serializer (count/aggregate) | 0 | 1 | 2 |
| 인덱스 누락 | 0 | 1 | 1 |
| 기타 (중복 쿼리, 무제한 로드) | 0 | 1 | 3 |

### 가장 시급한 3건 (캐시 없이 매 요청 N+1 발생)

1. **validation/api/views.py `_build_metric`** — `category=all` 시 수백 쿼리, 캐시 없음
2. **validation/api/views.py `LeaderComparisonView`** — 지표 수에 비례하는 3N 쿼리, 캐시 없음
3. **chain_sight/api/views.py `ChainSightGraphView`** — depth=3 시 edge당 2쿼리 폭증, 캐시 없음

---

## 상세

### 🔴 HIGH

---

#### H-1. `IndicatorComparisonView` — 루프 내 종목당 2쿼리 + 입력 무제한 N+1

- **파일**: `packages/shared/stocks/views_indicators.py:371-384`
- **코드**:
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol)          # L375 — 심볼당 1쿼리
      prices = DailyPrice.objects.filter(stock=stock) \
                 .order_by("-date")[:50].values_list("close_price", flat=True)  # L381 — 심볼당 1쿼리
  ```
- **설명**: 요청 `symbols` 배열 길이만큼 루프하며 종목당 `Stock.get` + `DailyPrice` 조회 → N개 심볼이면 2N 쿼리. L361-367은 빈 배열만 검증하고 **개수 상한이 없어** 클라이언트가 임의 개수를 보낼 수 있다(쿼리 수가 입력에 선형 비례).
- **심각도**: HIGH (입력 무제한 + 종목당 2쿼리)
- **난이도**: 중간
- **권장 수정**: (1) `symbols` 개수 상한 검증 추가, (2) `Stock.objects.filter(symbol__in=upper_symbols)`로 일괄 조회 후 dict 매핑하여 Stock N+1 제거.

---

#### H-2. `trending` (news) — 종목별 쿼리 + entities 미prefetch N+1

- **파일**: `services/news/api/views.py:370-389`
- **코드**:
  ```python
  for item in trending_data:
      recent_articles = (NewsArticle.objects.filter(
          entities__symbol=symbol, ...).distinct().order_by(...)[:3])
      "recent_articles": NewsArticleListSerializer(recent_articles, many=True).data,
  ```
- **설명**: 트렌딩 종목(최대 limit개)마다 `NewsArticle` 쿼리 1회 + `NewsArticleListSerializer`의 `entities = NewsEntitySimpleSerializer(many=True)`가 미prefetch라 기사당 추가 쿼리. `limit × (1 + 기사별 entities)` 쿼리.
- **완화**: 5분 캐시 존재 → 캐시 미스 시에만 폭증.
- **심각도**: HIGH
- **난이도**: 중간
- **권장 수정**: 루프 내 쿼리에 `.prefetch_related("entities")` 추가, 가능하면 종목별 기사를 단일 쿼리로 모아 매핑.

---

#### H-3. `ValidationMetricsView._build_metric` — 중첩 N+1 (캐시 없음)

- **파일**: `services/validation/api/views.py:247-265, 276-368`
- **코드**:
  ```python
  for cat in categories:                 # 최대 7
    for mc in metric_codes:              # 카테고리당 다수
      md = MetricDefinition.objects.filter(pk=mc).first()              # 지표당 1
      latest_snap = CompanyMetricSnapshot.objects.filter(...).first()  # 지표당 1
      delta = CompanyBenchmarkDelta.objects.filter(...).first()        # 지표당 1
      snaps = CompanyMetricSnapshot.objects.filter(...)[:5]            # 지표당 1
      for s in snaps:                    # 최대 5년
          peer_bench = PeerMetricBenchmark.objects.filter(...).first() # 연도당 1
  ```
- **설명**: `category=all`이면 7개 카테고리 × 카테고리당 N개 지표 × (MetricDefinition 1 + snapshot 2 + delta 1 + 연도당 PeerMetricBenchmark 최대 5). 지표 수십 개 시 **수백 쿼리**. **캐시 없음 → 매 요청 발생.**
- **심각도**: HIGH
- **난이도**: 높음
- **권장 수정**: 모든 지표코드/연도에 대해 `CompanyMetricSnapshot`·`CompanyBenchmarkDelta`·`PeerMetricBenchmark`를 `__in` 일괄 조회 후 메모리 매핑; `MetricDefinition.objects.in_bulk()`.

---

#### H-4. `LeaderComparisonView` — 지표 루프 내 3쿼리 N+1 (캐시 없음)

- **파일**: `services/validation/api/views.py:459-475`
- **코드**:
  ```python
  for cat, mc in all_metrics:   # 전체 카테고리×지표 = 수십
      md = MetricDefinition.objects.filter(pk=mc).first()
      company_snap = CompanyMetricSnapshot.objects.filter(symbol=stock, ...).first()
      leader_snap  = CompanyMetricSnapshot.objects.filter(symbol_id=leader.symbol, ...).first()
  ```
- **설명**: 전체 지표 루프마다 MetricDefinition + 회사 snapshot + 리더 snapshot 3쿼리. 지표 40개면 **120 쿼리**. **캐시 없음.**
- **심각도**: HIGH
- **난이도**: 높음
- **권장 수정**: 회사·리더 snapshot을 각각 `metric_code_id__in=all_codes`로 단일 쿼리 조회 후 dict 매핑; `MetricDefinition.in_bulk`.

---

#### H-5. `ChainSightGraphView` — edge당 2쿼리 N+1 (캐시 없음)

- **파일**: `apps/chain_sight/api/views.py:78-91`
- **코드**:
  ```python
  for edge in result.get("edges", []):
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
  ```
- **설명**: Neo4j 결과의 모든 edge마다 `CoMentionEdge` + `PriceCoMovement`를 개별 조회. `depth=3`이면 edge 수가 수십~수백이 되어 edge당 2쿼리 N+1. **캐시 없음.**
- **심각도**: HIGH
- **난이도**: 중간
- **권장 수정**: 모든 (a,b) 페어를 모아 `Q` OR / `__in` 튜플로 일괄 조회 후 dict 매핑. (같은 파일 `SectorGraphView`/`NeighborGraphView`가 `symbol__in` bulk + dict 매핑 모범 패턴을 이미 사용 중 — 동일 패턴 적용 가능.)

---

### 🟡 MED

---

#### M-1. `StockCompleteDataAPIView` — `OverviewTabSerializer` select_related 누락

- **파일**: `packages/shared/stocks/views.py:922-932`
- **코드**:
  ```python
  stock = get_object_or_404(Stock, symbol=symbol.upper())
  overview_data = OverviewTabSerializer(stock).data
  ```
- **설명**: 동일 serializer를 쓰는 `StockOverviewAPIView`(L545-551)는 `Stock.objects.select_related("overview_ko")`를 명시(OneToOne 역참조 대비)하나, 여기선 `get_object_or_404`만 사용 → `overview_ko` 역참조 시 추가 쿼리. Header+Overview+chart+재무 3종을 한 응답에 모으는 무거운 엔드포인트라 누락이 두드러짐.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: `get_object_or_404(Stock.objects.select_related("overview_ko"), symbol=symbol.upper())` (L545-551 패턴 일치).

---

#### M-2. `TechnicalIndicatorView` — period=max 전체 일봉 무제한 로드

- **파일**: `packages/shared/stocks/views_indicators.py:64-79`
- **코드**:
  ```python
  query = DailyPrice.objects.filter(stock=stock)
  if start_date:
      query = query.filter(date__gte=start_date)
  df = pd.DataFrame(list(query.order_by("date").values(...)))
  ```
- **설명**: `period="max"`(L60-61)이면 `start_date=None`이라 종목 전체 일봉을 메모리로 로드해 DataFrame 생성. 상장 오래된 종목은 수천 행 + pandas 변환 비용. N+1은 아님(단일 쿼리). 5분 캐시 있으나 cold path 비용 큼.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: max 기간에도 합리적 상한(예: 최대 5년/N행) 적용.

---

#### M-3. `UserFavoritesView` — many=True인데 prefetch 누락

- **파일**: `packages/shared/users/views.py:197-200`
- **코드**:
  ```python
  favorite_stocks = user.favorite_stock.all()
  serializer = StockSerializer(favorite_stocks, many=True)
  ```
- **설명**: ManyToMany를 `many=True` 직렬화하나 prefetch 없음. `StockSerializer`가 FK(sector/industry 등)를 포함하면 종목 수만큼 추가 쿼리.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: StockSerializer가 참조하는 관계에 `.select_related(...)` / `.prefetch_related(...)` 부착.

---

#### M-4. `UsersView` (관리자 사용자 목록) — 페이지네이션 누락

- **파일**: `packages/shared/users/views.py:92-95`
- **코드**:
  ```python
  users = User.objects.all()
  serializer = UserSerializer(users, many=True)
  return Response(serializer.data)
  ```
- **설명**: 전체 User를 페이지네이션 없이 직렬화. 사용자 증가 시 응답 폭주. 관리자 전용이라 호출 빈도 낮음.
- **심각도**: MED · **난이도**: 중간 (APIView라 Paginator 수동 추가)
- **권장 수정**: `Paginator` 적용 (같은 파일 `WatchlistListCreateView` 패턴 재사용).

---

#### M-5. `stock_news` / `market` (news) — entities prefetch 누락

- **파일**: `services/news/api/views.py:117-123` (stock_news), `309-311` (market)
- **코드**:
  ```python
  articles = NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by(...)
  ```
- **설명**: `NewsArticleListSerializer(many=True)`가 `entities`를 직렬화하나 이 두 액션은 별도 queryset을 새로 만들어 `prefetch_related("entities")`가 빠짐(`all_news` L445·`NewsViewSet.queryset`은 적용됨). 기사 수만큼 entities N+1. 10분 캐시로 완화.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: 두 쿼리에 `.prefetch_related("entities")` 추가.

---

#### M-6. `AnalysisSessionListCreateView` GET — 페이지네이션 누락 + messages 일괄 로드

- **파일**: `services/rag_analysis/views.py:429-432`
- **코드**:
  ```python
  sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related("messages")
  serializer = AnalysisSessionSerializer(sessions, many=True)
  ```
- **설명**: `prefetch_related("messages")`로 N+1은 방지되나, 페이지네이션이 없어 세션·메시지 누적 시 **모든 메시지까지 한 번에 로드**되어 응답 폭주 가능.
- **심각도**: MED · **난이도**: 중간
- **권장 수정**: 목록 직렬화에서 messages 제외(요약 serializer) + Paginator 적용.

---

#### M-7. `AdminNewsCategoryView` GET — 루프 내 `resolve_symbols()` 호출

- **파일**: `services/serverless/views_admin.py:505-508`
- **코드**:
  ```python
  categories = NewsCollectionCategory.objects.all()
  for cat in categories:
      symbols = cat.resolve_symbols()
  ```
- **설명**: 전체 카테고리 루프마다 `resolve_symbols()` 호출. 내부가 `sector`/`sub_sector`로 `SP500Constituent`를 조회하면 카테고리 수만큼 N+1 + 페이지네이션 없음. 관리자 전용·카테고리 소수라 실무 영향 제한적.
- **심각도**: MED · **난이도**: 중간 (resolve_symbols 구현 의존)
- **권장 수정**: 심볼을 사전 일괄 로드/캐시; 카테고리 목록 페이지네이션 추가.

---

#### M-8. `WatchlistSerializer.stock_count` — 목록에서 COUNT 반복 N+1

- **파일**: `packages/shared/users/serializers.py:284` → `users/models.py:209-212`
- **코드**:
  ```python
  stock_count = serializers.ReadOnlyField()      # → @property: return self.items.count()
  ```
- **설명**: Watchlist 목록 뷰(`users/views.py:624`)는 `items`를 prefetch하지 않아, watchlist 1건마다 `items.count()` SQL 1번 추가 → 1+N 쿼리.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: 뷰 쿼리셋에 `.annotate(stock_count_db=Count("items"))` 후 serializer가 annotate 값 사용, 또는 `.prefetch_related("items")` + 모델 프로퍼티를 `len(self.items.all())`로 변경.

---

#### M-9. `DataBasketSerializer` — count/aggregate가 prefetch 캐시 무력화 N+1

- **파일**: `services/rag_analysis/serializers.py:34,38,59-60` → `rag_analysis/models.py:32-49`
- **코드**:
  ```python
  items = BasketItemSerializer(many=True, read_only=True)   # prefetch 캐시 사용
  items_count = serializers.IntegerField(read_only=True)    # → self.items.count()  ← 새 SQL
  current_units = serializers.IntegerField(read_only=True)  # → self.items.aggregate(Sum)  ← 새 SQL
  def get_can_add_item(self, obj): return obj.can_add_item() # → self.items.count()  ← 새 SQL
  ```
- **설명**: 목록 뷰(L52-53)가 `.prefetch_related("items")`를 써도 `items.count()`·`items.aggregate()`는 **prefetch 캐시를 무시하고 매번 새 SQL 실행**. basket N개면 약 3N개 추가 쿼리.
- **심각도**: MED · **난이도**: 중간
- **권장 수정**: 모델 프로퍼티를 prefetch 캐시 재사용형으로 변경 — `len(self.items.all())`, `sum(i.data_units for i in self.items.all())`. 또는 뷰에서 `Count`/`Sum` annotate.

---

#### M-10. `NewsCollectionLog.task_name` — 인덱스 누락

- **파일**: `services/news/models.py:535` (필드), `545-547` (Meta)
- **코드**:
  ```python
  task_name = models.CharField(max_length=100)     # db_index 없음
  indexes = [models.Index(fields=["provider", "-executed_at"])]   # task_name 미포함
  ```
- **설명**: `task_name` 단독 필터가 운영 모니터링 코드에 다수 존재하나, 인덱스가 없고 유일한 복합 인덱스 `(provider, -executed_at)`로는 task_name 단독 조회 불가. 근거: `news/api/views.py:1443,1447,1668,1708,1752,1757,2225,2253`, `news/tasks.py:1237,1328,1375,1405` (모두 `filter(task_name=...)` 또는 `task_name__icontains`). NewsCollectionLog는 누적되는 운영 로그 테이블.
- **심각도**: MED · **난이도**: 쉬움
- **권장 수정**: `Meta.indexes`에 `models.Index(fields=["task_name", "-executed_at"])` 추가.

---

### 🟢 LOW

---

#### L-1. `StockChartDataAPIView` — `.count()` 중복 호출

- **파일**: `packages/shared/stocks/views.py:317-323`
- **설명**: lazy QuerySet `price_data`에 `.count()`를 2회 호출 → COUNT 쿼리 2회. 직전 `serializer.data`(L314)가 이미 QuerySet을 평가하므로 `len(serializer.data)`로 재사용 가능. N+1 아님, 중복 라운드트립.
- **심각도**: LOW · **난이도**: 쉬움
- **권장 수정**: `count = len(serializer.data)`로 한 번만 계산.

---

#### L-2. `EODDashboardView` — 대형 `json_data` 통째 반환

- **파일**: `packages/shared/stocks/views_eod.py:43-50`
- **설명**: 단일 스냅샷(`.first()`)이지만 14개 시그널 전 종목 벡터를 포함하는 `json_data` JSONField를 통째 반환 → 페이로드 매우 클 수 있음. ORM N+1은 아님(페이로드 크기 주의 수준).
- **심각도**: LOW · **난이도**: 중간
- **권장 수정**: 대형이면 섹션별 분할 엔드포인트 검토(즉시 조치 불필요).

---

#### L-3. `StockMVPListView` (full 모드) — serializer prefetch 누락 가능

- **파일**: `packages/shared/stocks/views_mvp.py:41-65`
- **설명**: summary 모드는 `[:20]` 슬라이스 + Stock 자체 컬럼만 접근 → N+1 아님. full 모드는 `StockListSerializer(queryset, many=True)`를 쓰는데 해당 serializer가 FK/역참조를 참조하면 prefetch 누락 가능. 20개 상한이라 영향 제한적.
- **심각도**: LOW · **난이도**: 쉬움
- **권장 수정**: full 모드 분기에 관계 필드 있으면 `select_related`/`prefetch_related` 추가.

---

#### L-4. `SectorListView` — `sector` DISTINCT 무캐시 스캔

- **파일**: `packages/shared/stocks/views_mvp.py:221-225`
- **설명**: `sector` 컬럼 전체 DISTINCT 스캔. 단일 쿼리(N+1 아님)이나 매 호출 DB 부담 + 캐시 없음. 섹터 종류는 소수라 결과는 작음.
- **심각도**: LOW · **난이도**: 쉬움
- **권장 수정**: 결과 캐싱(섹터 목록은 거의 불변).

---

#### L-5. Favorites 멤버십 체크 — `stock in user.favorite_stock.all()`

- **파일**: `packages/shared/users/views.py:217, 248`
- **설명**: `.all()`을 전부 메모리 로드 후 Python `in`으로 멤버십 확인. `.filter(pk=stock.pk).exists()`가 단일 쿼리로 효율적. 즐겨찾기 수 적으면 영향 미미.
- **심각도**: LOW · **난이도**: 쉬움
- **권장 수정**: `if user.favorite_stock.filter(pk=stock.pk).exists():`

---

#### L-6. `DataBasketListCreateView` GET — 페이지네이션 누락

- **파일**: `services/rag_analysis/views.py:52-53`
- **설명**: 사용자별 전체 basket을 페이지네이션 없이 반환. `prefetch_related("items")`로 N+1은 방지되나 누적 시 응답 크기 증가. 사용자당 데이터라 보통 소량.
- **심각도**: LOW · **난이도**: 중간
- **권장 수정**: 데이터 규모 증가 시 Paginator 적용.

---

#### L-7. `ValidationSummaryView` — ranks 루프 내 FK 쿼리 2종 (상수 횟수)

- **파일**: `services/validation/api/views.py:147-155`
- **설명**: 고정 5개 지표 루프마다 `CompanyBenchmarkDelta` + `MetricDefinition` 쿼리 → 최대 10쿼리(상수). 단일 종목 요청이라 폭증 없으나 불필요한 라운드트립.
- **심각도**: LOW · **난이도**: 중간
- **권장 수정**: `metric_code_id__in=rank_metrics`로 delta 일괄 조회 + `MetricDefinition.objects.in_bulk(rank_metrics)`.

---

#### L-8. `WatchListStockSerializer` — N+1 (단, 데드코드) + `get_dynamic_layers` 단건 +7쿼리

- **파일**: `packages/shared/stocks/serializers.py:451-460` (데드코드), `241-353` (단건)
- **설명**:
  - `WatchListStockSerializer.get_latest_price`/`get_chart_data`는 종목마다 `DailyPrice` 2쿼리(전형적 N+1)이나 **코드베이스 어디서도 import/사용되지 않는 데드코드**(`get_chart_data`는 `return`도 없음). 런타임 영향 없음 — 활성화 시 HIGH로 격상.
  - `OverviewTabSerializer.get_dynamic_layers`는 OneToOne 역참조 5종 + 역FK 1종으로 요청당 +7쿼리이나 **항상 단일 stock에만 사용**(many=True 없음)이라 N+1 아님. 코드에 이미 `# TODO: prefetch_related + 캐싱` 주석 존재.
- **심각도**: LOW · **난이도**: 쉬움(데드코드 제거) / 중간(상세 뷰 select_related+prefetch)
- **권장 수정**: 미사용 serializer 제거. 상세 뷰 쿼리에 `select_related`(OneToOne 5종) + `prefetch_related("category_signals")` 적용으로 7→1~2 쿼리 축소(급하지 않음).

---

## 이슈 없음으로 확인된 영역

**뷰** (외부 API 결과 직렬화 — ORM N+1/페이지네이션 무관):
- `views_search.py`, `views_exchange.py`, `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py` (모두 FMP 외부 서비스 결과 직렬화 + limit 상한)
- `apps/market_pulse/views.py` (단일 dict 반환 / MacroEconomicService 결과)
- `services/sec_pipeline/views.py` (집계 stats / 단일 심볼 결과)

**모범 패턴 (이미 최적화됨)**:
- `users/views.py` Portfolio/Watchlist 계열 — `select_related("stock")` / `prefetch_related("items__stock")` + Paginator 적용
- `chain_sight` `SectorGraphView`/`NeighborGraphView` — `symbol__in` bulk 조회 + dict 매핑 (H-5 권장 패턴의 모범)
- `stocks/views_eod.py` `EODSignalDetailView` — `[:50]` 슬라이스 + `select_related("stock")`

**인덱스 이상 없음** (filter/order_by 교차 검증 완료):
- `stocks.models.py` (PK=symbol, sector/market_cap 인덱스 존재, 재무제표 3종 복합 인덱스)
- `users.models.py` (전부 FK 자동 인덱스 + unique_together)
- `rag_analysis.models.py` (UsageLog 4개 인덱스 등 FK 기반)
- `sec_pipeline.models.py` (status/target_company/neo4j_dirty 인덱스, accession_no unique)
- `graph_analysis.models.py` (_dormant, watchlist+date 복합 인덱스 — 우선순위 최하)
- `news.NewsArticle` (importance/llm_analyzed 복합 인덱스로 classifier 쿼리 커버)
- `serverless.MarketMover.mover_type` — 거의 항상 date와 함께 필터되어 기존 `(date, mover_type)` 복합 인덱스로 커버됨

**Serializer 이상 없음**:
- `serializers_market_movers.py`/`serializers_screener.py`/`serializers_fundamentals.py`/`serializers_exchange.py` — `get_*`가 dict(`obj.get(...)`) 기반, DB 쿼리 없음
- `users/serializers.py` Portfolio/WatchlistItem — `source="stock.*"` FK 접근이나 모든 목록 뷰가 `select_related("stock")`로 커버
- `news/api/serializers.py` — `SerializerMethodField` 없음
- `validation/`·`apps/chain_sight/`·`sec_pipeline/` — DRF serializer 없음(views에서 직접 dict 직렬화)

---

## 권장 수정 우선순위

| 순위 | ID | 위치 | 근거 |
|------|-----|------|------|
| 1 | H-3 | validation `_build_metric` | 캐시 없음 + category=all 수백 쿼리 |
| 2 | H-4 | validation `LeaderComparison` | 캐시 없음 + 지표 비례 3N 쿼리 |
| 3 | H-5 | chain_sight `GraphView` | 캐시 없음 + depth=3 edge당 2쿼리 (모범 패턴 동일 파일 존재) |
| 4 | H-1 | indicators `IndicatorComparison` | 입력 무제한 — 보안/DoS 측면도 |
| 5 | H-2 | news `trending` | 캐시 미스 시 폭증 (prefetch 한 줄로 완화) |
| 6 | M-8, M-9 | serializer count/aggregate N+1 | 실사용 목록 엔드포인트, 수정 단순 |
| 7 | M-10 | NewsCollectionLog 인덱스 | 누적 로그 테이블, Migration 한 건 |

**공통 수정 패턴**: 루프 내 `.filter(...).first()` → `__in` 일괄 조회 + 메모리 dict 매핑. `many=True`로 역참조(entities/items)를 직렬화하는 QuerySet에는 `prefetch_related` 부착. 모델 프로퍼티의 `count()`/`aggregate()`는 prefetch 캐시를 무력화하므로 목록 컨텍스트에서는 `len(...)`/`sum(...)`로 전환.

---

*본 보고서는 정적 분석 기반이며 코드를 일절 수정하지 않았다. 쿼리 횟수는 코드 구조 기반 추정치로, 실제 부하는 데이터 규모·캐시 적중률에 따라 달라진다. `resolve_symbols()`(M-7) 등 일부는 구현 의존이라 별도 확인 필요.*
