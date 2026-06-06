# API 성능 감사 보고서

- **일자**: 2026-06-06
- **모드**: 읽기 전용 (코드 수정 없음)
- **범위**: 뷰 17개 파일(N+1·페이지네이션), 모델 7개 파일(인덱스), Serializer 11개 파일(SerializerMethodField 추가 쿼리)
- **방법**: 4개 병렬 에이전트가 실제 라인 확인 후 보고. 추측 배제, 코드에서 확인된 것만 기록
- **저장소 구조 참고**: 모놀리식 → `packages/` · `apps/` · `services/` 로 재편됨. 지시서의 경로(`stocks/`, `users/` 등)는 실제 경로로 매핑하여 감사함
  - `stocks/` → `packages/shared/stocks/`, `users/` → `packages/shared/users/`
  - `macro/` → `apps/market_pulse/`, `chainsight/` → `apps/chain_sight/`
  - `news/`·`rag_analysis/`·`serverless/`·`validation/`·`sec_pipeline/` → `services/*`
  - `graph_analysis/` → `services/_dormant/graph_analysis/` (휴면, API 미구현)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 건수 | 항목 |
|--------|------|------|
| **HIGH** | 5 | N+1 #5, #6-2, #6-3, #7-1, #4-2 |
| **MED** | 7 | #1-1, #4-1, #7-3, #1-1(idx), #1-C(ser), #2-A(ser), #4-A(ser) |
| **LOW** | 다수 | 캐시/슬라이스 상한으로 완화된 잠재 이슈 + 소형 테이블 인덱스 후보 |
| **이슈 없음** | — | `market_pulse/views.py`, `sec_pipeline/views.py`, dict 기반 serializer 4종 |

### 카테고리별 핵심 결론

1. **N+1 쿼리** — 진짜 위험은 **루프 내 ORM 쿼리** 5건(HIGH). list 엔드포인트 대부분은 외부 FMP 서비스가 파이썬 list를 반환해 ORM과 무관하므로 N+1이 없음.
2. **인덱스 누락** — 대부분 모델이 이미 충실히 인덱싱됨. 확정적 HIGH 누락은 **없음**. 실질 권장 1건(`UsageLog.created_at` 선두 인덱스, MED).
3. **느린 Serializer** — serializer 코드 자체가 DB 쿼리를 일으키는 건 `WatchListStockSerializer` 2개 메서드뿐(현재 미사용). 나머지는 호출 뷰의 prefetch 누락 문제.
4. **페이지네이션** — DRF `pagination_class`는 일부만 적용하지만 나머지는 `[:N]` 슬라이스/`limit` 상한으로 무한 결과를 차단. 실질 위험 낮음.

### 최우선 조치 Top 5 (심각도순)

| 순위 | 위치 | 이슈 | 심각도 | 난이도 |
|------|------|------|--------|--------|
| 1 | `services/validation/api/views.py:247~353` | metrics(all) — 지표×연도×PeerBenchmark 중첩 N+1 (수백 쿼리) | HIGH | 높음 |
| 2 | `services/rag_analysis/views.py:429` | session 목록 — basket FK select_related 누락 + items/집계 연쇄 N+1 | HIGH | 중간 |
| 3 | `services/validation/api/views.py:459` | leader-comparison — 전 지표 루프 내 3쿼리 | HIGH | 중간 |
| 4 | `apps/chain_sight/api/views.py:78` | graph — edge마다 2쿼리, **캐시 없음** | HIGH | 중간 |
| 5 | `packages/shared/stocks/views_indicators.py:371` | IndicatorComparison — 루프 내 2N 쿼리 + 입력 무상한 | HIGH | 중간 |

---

## 상세

## 1. N+1 쿼리 (뷰)

### [HIGH] #6-2 — `ValidationMetricsView._build_metric` 지표×연도 중첩 N+1
- **위치**: `services/validation/api/views.py:247-249`(카테고리 루프) → `:261-265`(지표 루프) → `:339-353`(history 루프 내 `PeerMetricBenchmark` 조회)
- **코드**:
  ```python
  for cat in categories:                  # all → 7 카테고리
      for mc in metric_codes:             # 카테고리당 다수 지표
          md = MetricDefinition.objects.filter(pk=mc).first()        # :262
          latest_snap = CompanyMetricSnapshot.objects...first()      # :278
          snaps = CompanyMetricSnapshot.objects...[:5]               # :339
          for s in snaps:                                            # 연도 루프
              peer_bench = PeerMetricBenchmark.objects.filter(...).first()  # :349 ← 중첩 N+1
  ```
- **설명**: `category=all`이면 (7 카테고리 × 지표 수)를 순회하며 지표마다 `MetricDefinition`/`CompanyMetricSnapshot`(2~3회)/`CompanyBenchmarkDelta` 단건 쿼리 + history 5개 연도마다 `PeerMetricBenchmark` 1쿼리(중첩). 지표 30개 가정 시 수백 쿼리. **이 파일에서 가장 심각**.
- **권장 수정**: `MetricDefinition`을 루프 밖 `in_bulk()`로 일괄 로드. `CompanyMetricSnapshot`/`CompanyBenchmarkDelta`/`PeerMetricBenchmark`를 `metric_code__in=...`로 한 번에 가져와 `(metric_code, fiscal_year)` 딕셔너리로 인덱싱 후 파이썬 매칭.
- **심각도**: HIGH · **난이도**: 높음

### [HIGH] #4-2 — `AnalysisSessionListCreateView.get` 세션 목록 basket 연쇄 N+1
- **위치**: `services/rag_analysis/views.py:429-431` (+ `serializers.py:86-87`)
- **코드**:
  ```python
  sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related("messages")  # :429
  # AnalysisSessionSerializer: messages(many=True), basket=DataBasketSerializer(read_only)
  ```
- **설명**: `messages`는 prefetch되나 `basket`(FK)에 `select_related("basket")`가 없어 session당 basket 1쿼리. 각 basket은 `DataBasketSerializer`라 **items prefetch 누락 + items_count/current_units 집계 쿼리**까지 연쇄(session N개 → basket N + items N + 집계 다수). 페이지네이션 없음.
- **권장 수정**: `.select_related("basket").prefetch_related("messages", "basket__items")` + 4-1 annotation. 목록에서는 경량 serializer(basket 요약) 사용 권장.
- **심각도**: HIGH · **난이도**: 중간

### [HIGH] #6-3 — `LeaderComparisonView.get` 전 지표 루프 내 3쿼리
- **위치**: `services/validation/api/views.py:459-475`
- **코드**:
  ```python
  for cat, mc in all_metrics:                              # 전체 지표
      md = MetricDefinition.objects.filter(pk=mc).first()        # :460
      company_snap = CompanyMetricSnapshot.objects...first()     # :464
      leader_snap  = CompanyMetricSnapshot.objects...first()     # :470
  ```
- **설명**: 모든 지표(수십 개)마다 3쿼리 → 100+ 쿼리.
- **권장 수정**: company/leader snapshot을 `symbol_id__in=[stock, leader] & metric_code_id__in=all & fiscal_year=latest_fy`로 일괄 로드 후 dict 매칭. `MetricDefinition`도 `in_bulk`.
- **심각도**: HIGH · **난이도**: 중간

### [HIGH] #7-1 — `ChainSightGraphView.get` edge 루프 내 2 DB 쿼리 (캐시 없음)
- **위치**: `apps/chain_sight/api/views.py:78-91`
- **코드**:
  ```python
  for edge in result.get("edges", []):                    # :78 (edge 수만큼)
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()   # :84
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first() # :86
  ```
- **설명**: Neo4j에서 받은 edge 1개마다 PostgreSQL `CoMentionEdge` + `PriceCoMovement` 2쿼리. depth≤3 그래프의 edge가 수십~수백 개면 큰 N+1. **캐시가 없어 매 요청 노출**.
- **권장 수정**: edge 전체에서 `(a,b)` 쌍 집합을 모은 뒤 `CoMentionEdge`/`PriceCoMovement`를 각 1쿼리로 일괄 조회해 dict 매핑.
- **심각도**: HIGH · **난이도**: 중간

### [HIGH] #5 — `IndicatorComparisonView` 루프 내 종목별 쿼리 + 입력 무상한
- **위치**: `packages/shared/stocks/views_indicators.py:371-384`
- **코드**:
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol)             # :375 심볼당 1쿼리
      prices = (DailyPrice.objects.filter(stock=stock)
          .order_by("-date")[:50]
          .values_list("close_price", flat=True))          # :380 심볼당 1쿼리
  ```
- **설명**: POST body의 `symbols`를 순회하며 심볼당 Stock get + DailyPrice 조회 = **2N 쿼리**. 입력 심볼 개수 상한이 없어(L361 빈 체크만) DoS 표면.
- **권장 수정**: ① Stock 일괄 조회 `{s.symbol: s for s in Stock.objects.filter(symbol__in=[...])}`(1쿼리) ② 심볼 개수 상한(예: 50) 추가 ③ 가격은 종목별 최신 50건이라 최소 Stock fetch만이라도 일괄화.
- **심각도**: HIGH · **난이도**: 중간

### [MED] #1-1 — `WatchlistListCreateView.get` stock_count per-row COUNT
- **위치**: `packages/shared/users/views.py:624` (+ `serializers.py:284` → `models.py:212`)
- **코드**:
  ```python
  watchlists = Watchlist.objects.filter(user=request.user).order_by("-updated_at")  # :624
  # WatchlistSerializer.stock_count = ReadOnlyField() → models: return self.items.count()
  ```
- **설명**: `stock_count`(= `self.items.count()`)를 직렬화하면 watchlist 1건마다 별도 COUNT 쿼리. 페이지네이션이 폭주는 막으나 페이지 크기만큼 N+1.
- **권장 수정**: `.annotate(stock_count_anno=Count("items"))` 후 serializer 필드를 `IntegerField(source="stock_count_anno")`로 교체.
- **심각도**: MED · **난이도**: 중간

### [MED] #4-1 — `DataBasketListCreateView.get` items_count/current_units per-row 집계
- **위치**: `services/rag_analysis/views.py:52` (+ `serializers.py:33-40` → `models.py:34,38,43`)
- **코드**:
  ```python
  baskets = DataBasket.objects.filter(user=request.user).prefetch_related("items")  # :52
  # items_count → self.items.count(); current_units/remaining_units → self.items.aggregate(Sum(...))
  ```
- **설명**: `prefetch_related("items")`로 중첩 items는 해결되나 `items_count`(새 COUNT)·`current_units`/`remaining_units`(새 aggregate Sum)는 prefetch 캐시를 안 쓰고 basket 1건마다 실행. basket N개 → 약 3N 추가 쿼리. 페이지네이션 없음.
- **권장 수정**: `.annotate(items_count_anno=Count("items"), current_units_anno=Sum("items__data_units"))` 후 serializer가 annotation 참조. (prefetch는 중첩 items 직렬화용 유지)
- **심각도**: MED · **난이도**: 중간

### [MED] #7-3 — `SignalFeedView._build_chain_signals` 시드 페어 루프 내 Neo4j 쿼리
- **위치**: `apps/chain_sight/api/views.py:809-831`
- **코드**:
  ```python
  for s1, s2 in pairs:                                     # 최대 page_size*3 = 15쌍
      result = repo.run_query(shortestPath...)             # :816 쌍마다 Neo4j 1쿼리
  ```
- **설명**: 시드 페어마다 개별 `shortestPath` Neo4j 호출. `max_candidates=page_size*3`(기본 15) 상한 + 1시간 캐시로 폭주는 제한적이나 캐시 미스 시 그래프 쿼리 15회.
- **권장 수정**: 단일 Cypher로 다중 페어 경로 배치 처리(`UNWIND $pairs`).
- **심각도**: MED · **난이도**: 높음

### [LOW] N+1·페이지네이션 (완화됨 / 경미)

| 위치 | 이슈 | 완화 요인 |
|------|------|-----------|
| `packages/shared/stocks/views.py:922,932` | `StockCompleteDataAPIView` — `OverviewTabSerializer`에 7개 역참조 prefetch 누락(통합 핫패스, 단일 객체) | 단일 객체 → row-N+1 아님. 무캐싱이라 MED 후보 |
| `packages/shared/stocks/views.py:545-551` | `StockOverviewAPIView` — 동적레이어 prefetch 부분 누락 | `stock_overview_{symbol}` 캐시로 빈도 낮음 |
| `packages/shared/stocks/views.py:317,323` | `.count()` 2회 + 직렬화 fetch = 3 DB 왕복 | 단일 종목, 1분 캐시 |
| `packages/shared/stocks/views_indicators.py:60-70` | `period="max"`일 때 전체 가격 이력 fetch | 단일 종목 + 5분 캐시 |
| `services/news/api/views.py:370-378` | `trending` — 종목 루프 내 기사 조회 | 5분 캐시, limit 10 |
| `services/news/api/views.py:1476-1479` | `collection_logs` — provider별 추가 COUNT | provider 2~4개, IsAdminUser, 캐시 |
| `services/news/api/views.py:1614~1900` | `pipeline_health` — 수십 개 순차 단발 쿼리 | 고정 개수(루프 아님), 5분 캐시 |
| `services/serverless/views_admin.py:505-508` | `AdminNewsCategoryView` — 카테고리 루프 내 `resolve_symbols()` | 관리자용, 카테고리 소량 |
| `services/serverless/views_admin.py:318-321` | `AdminActionView` — 루프 내 `cache.get` N회 | 고정 ~15개. `get_many()` 권장 |
| `services/validation/api/views.py:148-155` | `ValidationSummaryView` — rank 5개 루프 내 2쿼리 | 고정 5개 |
| `services/validation/api/views.py:536` | `PresetListView` — 페이지네이션 없음 | 종목당 6종 소수 |
| `packages/shared/users/views.py:383-385,419,429,441` | portfolio 루프 집계 + `portfolios.count()` 추가 COUNT | `select_related("stock")` 적용됨, `len()`으로 대체 가능 |
| `packages/shared/users/views.py:92-95` | `Users.get` — 페이지네이션 없음 | IsAdminUser 제한 |
| `packages/shared/users/views.py:197` | `UserFavorites.get` — M2M prefetch 누락 + 페이지네이션 없음 | 단건 경로 위주 |

### 양호 사례 (올바른 패턴 — 참고)
- `EODSignalDetailView`(`views_eod.py:81`): `.select_related("stock")` 후 루프 접근 → N+1 방지됨
- `NewsViewSet.queryset`(`news/api/views.py:71`), `all_news`(`:445`): `prefetch_related("entities")` 적용
- `SectorGraphView`/`NeighborGraphView`(`chain_sight/api/views.py:463,619`): `Stock.objects.filter(symbol__in=...)` bulk 후 dict 매핑
- `WatchlistDetailView`(`:687`), `WatchlistStocksView`(`:869`), `PortfolioListCreateView`(`:271`): select/prefetch 적절
- `StockListAPIView`(`views.py:100`): DRF `StockListPagination`(page_size 50/max 200) 적용
- **이슈 없음**: `apps/market_pulse/views.py`(서비스 패스스루), `services/sec_pipeline/views.py`(단일 심볼 위임)

---

## 2. 인덱스 누락 (모델)

> 대부분 모델이 `Meta.indexes`/`unique_together`/`db_index` 광범위 적용으로 **충실히 인덱싱**됨. HIGH 후보 대용량 테이블(`DailyPrice`, `EODSignal`, `StockNews`, `NewsArticle`)은 핵심 조회 패턴이 모두 커버됨. **확정적 HIGH 누락 없음.**

### [MED] `UsageLog.created_at` 선두 인덱스 부재
- **위치**: `services/rag_analysis/models.py:288` (`UsageLog`)
- **설명**: 기존 복합 인덱스 4개가 모두 `user`/`model`/`request_type`/`cached` 선두라 `get_usage_stats(user=None)`(전체 사용자 24h 집계, `created_at__gte`만 필터)는 어느 인덱스도 활용 못 함. UsageLog는 LLM 호출마다 적재되어 빠르게 누적.
- **권장 수정**: `models.Index(fields=["-created_at"])` 추가.
- **심각도**: MED(단 user=None 집계는 관리자 대시보드 한정으로 빈도 낮음) · **난이도**: 쉬움

### [LOW] 검토 후보 (소형 테이블 → 풀스캔 무해, 즉시 조치 불필요)

| 위치 | 필드 | 근거 |
|------|------|------|
| `packages/shared/stocks/models.py:900` `SP500Constituent` | `sub_sector` | `NewsCollectionCategory.resolve_symbols()`의 `filter(sub_sector=, is_active=)`(news/models.py:521). ~500행 |
| `services/serverless/models.py:447` `ScreenerFilter` | `category`/`is_active` | 필터 UI 렌더 시 active 필터링 + category 정렬. ~50행 메타 |
| `services/sec_pipeline/models.py:315` `CompanyAlias` | `ticker` | ticker 역조회 시. 소형 별칭 테이블 |
| `packages/shared/stocks/models.py:1064` `SignalAccuracy` | `return_*__isnull` 배치 | 정확도 배치 미도래분 스캔 가능성. 시계열 누적 시 증가 |

### 오탐 회피 확인 결과
- `change_percent`(Stock, CharField), ordering-only 필드(`DataBasket.updated_at`, `AnalysisMessage.created_at`, `EntityHighlight.sentiment` 등)는 모두 FK/PK 자동 인덱스 또는 `unique_together` prefix로 부모 기준 조회가 선행되므로 **인덱스 누락 아님**.
- 모든 ForeignKey/OneToOne은 Django 자동 인덱스가 있어 제외.
- `services/_dormant/graph_analysis/models.py`: 휴면 앱(API 미구현). 인덱스 설계도 양호 — **이슈 없음**.

---

## 3. 느린 Serializer (SerializerMethodField 추가 쿼리)

> serializer 코드 자체가 DB 쿼리를 일으키는 건 `WatchListStockSerializer` 2개 메서드뿐. 나머지는 **호출 뷰의 select_related/prefetch_related 누락**에 좌우되는 nested/FK 접근.

### [HIGH] #1-A/#1-B — `WatchListStockSerializer` 객체당 DailyPrice 쿼리
- **위치**: `packages/shared/stocks/serializers.py:451-456`(`get_latest_price`), `:458-460`(`get_chart_data`)
- **코드**:
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by("-date").first()   # :452
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by("-date")[:7] # :460 (+ return 누락)
  ```
- **설명**: 객체마다 `DailyPrice` 별도 쿼리 → `many=True` 시 종목 N개 = N 쿼리. `get_chart_data`는 `return` 문이 없어 항상 `None` 반환(미완성). **단, 이 serializer는 현재 어느 뷰에서도 import/사용되지 않음**(정의만 존재) — 활성화 즉시 핫패스 N+1.
- **권장 수정**: `get_latest_price`는 `obj.real_time_price` fallback으로 메서드 제거. `get_chart_data`는 메서드 제거 또는 뷰에서 `Prefetch(queryset=DailyPrice.objects.order_by("-date"))` 적재.
- **심각도**: HIGH(미사용이라 현재 우선순위는 낮음) · **난이도**: 쉬움

### [MED] #1-C — `OverviewTabSerializer.get_dynamic_layers` 7개 역참조
- **위치**: `packages/shared/stocks/serializers.py:241-353`
- **코드**:
  ```python
  signals = list(obj.category_signals.all())   # reverse FK
  ns = obj.validation_news_summary             # OneToOne
  sp = obj.sensitivity_profile; gs = obj.growth_stage; cd = obj.capital_dna; nt = obj.narrative_tag
  ```
- **설명**: reverse FK 1개 + OneToOne 6개 접근 → 객체당 최대 7개 추가 쿼리. 현재 단건(`many=True` 아님) 상세용이라 폭발은 없으나 코드 TODO에 prefetch 필요 명시. 리스트 재사용 시 HIGH 승격.
- **권장 수정**: 상세 뷰에서 `select_related`(O2O 6개) + `prefetch_related("category_signals")`. (= 1절 #1-1 LOW와 동일 대상)
- **심각도**: MED · **난이도**: 중간

### [MED] #2-A — news trending/detail 뷰의 entities prefetch 누락
- **위치**: `services/news/api/views.py:373`(trending), `:445`(detail) (+ `serializers.py` nested)
- **설명**: 메인 list 뷰는 `prefetch_related("entities")` 보장(정상). 그러나 trending은 루프 내 `recent_articles` 쿼리(`:372`)에 prefetch 없이 `NewsArticleListSerializer(many=True)` 호출 → 종목 N × 기사 3 × entities = N+1. 또 `NewsEntitySerializer.highlights`(detail, many=True)는 `entities__highlights` 미적재 → entity 수만큼 N+1. **원인은 serializer가 아니라 호출 뷰의 prefetch 누락**.
- **권장 수정**: trending `recent_articles`에 `.prefetch_related("entities")`, detail 뷰에 `.prefetch_related("entities__highlights")`.
- **심각도**: MED · **난이도**: 쉬움

### [MED] #4-A — rag 세션 list nested(messages + basket.items)
- **위치**: `services/rag_analysis/serializers.py:86-87` (호출: `views.py:429`)
- **설명**: 세션 list(`many=True`)에서 뷰가 `prefetch_related("messages", "basket__items")` 안 하면 세션당 다중 쿼리. `DataBasketSerializer.get_can_add_item`(`:59`)이 items 카운트면 추가 쿼리. (= 1절 #4-2 HIGH와 동일 근본 원인)
- **권장 수정**: 세션 list 뷰에서 `prefetch_related("messages", "basket__items")`.
- **심각도**: MED · **난이도**: 쉬움

### [LOW] serverless FK serializer들 (select_related 의존)

| 위치 | 메서드/필드 | 권장 |
|------|-------------|------|
| `services/serverless/serializers.py:299-316` | `ScreenerPresetSerializer.get_owner_email` (`obj.user.email`) | 뷰에서 `.select_related("user")` |
| `:649,681` | `AlertHistorySerializer` `source="alert.name"` | `.select_related("alert")` |
| `:574-578` | `ScreenerAlertSerializer.get_preset_name` (`obj.preset.*`) | `.select_related("preset")` |
| `:125-144` | `MarketMoverListSerializer` display 3종 — 객체마다 `IndicatorCalculator()` 인스턴스화 | DB 쿼리 아님(순수 포맷). context 주입 또는 `@staticmethod`화 |
| `:221-226` | `MarketBreadthSerializer.get_signal_interpretation` — 객체마다 서비스 인스턴스화 | 쿼리 없으면 무해 |
| `packages/shared/users/serializers.py:16,26` | `UserSerializer.favorite_stock`(M2M nested) | user list 경로 시 `.prefetch_related("favorite_stock")` |

### 이슈 없음 (6개 파일)
| 파일 | 사유 |
|------|------|
| `stocks/serializers_fundamentals.py` | dict 입력(FMP 응답) `Serializer`. SerializerMethodField는 `obj.get(...)` dict 접근만 |
| `stocks/serializers_market_movers.py` | dict 기반, 순수 계산 |
| `stocks/serializers_exchange.py` | dict 기반, `obj.get(...)` 산술 |
| `stocks/serializers_screener.py` | dict 기반(FMP) + 요청 검증 |
| `apps/portfolio/api/serializers.py` | E1~E6 Pydantic 어댑터, DB 접근 전무 |
| `apps/market_pulse/serializers.py` | 단순 FK `source` 단건 응답, nested 역참조 없음 |

---

## 4. 페이지네이션 누락 (종합)

| 위치 | 상태 | 비고 |
|------|------|------|
| `packages/shared/stocks/views.py:100` `StockListAPIView` | ✅ `StockListPagination`(50/max 200) | 양호 |
| `services/rag_analysis/views.py:429` 세션 목록 | ❌ 없음 | HIGH #4-2와 결합 — 우선 조치 |
| `services/rag_analysis/views.py:52` basket 목록 | ❌ 없음 | MED #4-1과 결합 |
| `packages/shared/users/views.py:92` `Users` | ❌ 없음 | IsAdminUser, LOW |
| `packages/shared/users/views.py:197` `UserFavorites` | ❌ 없음 | LOW |
| `services/validation/api/views.py:536` `PresetListView` | ❌ 없음 | 6종 소수, LOW |
| `services/serverless/views_admin.py:505` 카테고리 | ❌ 없음 | 관리자, LOW |
| 기타 stocks 뷰(`views_eod`, `views_mvp`, `views_screener` 등) | ⚠️ DRF 미적용이나 `[:N]` 슬라이스/`limit` 상한 존재 | 무한 결과 위험 없음 |

대부분 list 엔드포인트는 외부 FMP `limit` 또는 `[:N]` 하드 상한으로 무한 결과를 차단. DRF `pagination_class` 부재 자체가 곧 위험은 아님.

---

## 부록: 방법론·한계

- 본 감사는 **정적 코드 분석**(라인 확인) 기반. 실제 쿼리 수는 `django-silk`/`assertNumQueries`로 런타임 측정 시 확정 가능.
- "HIGH N+1"의 폭발 규모는 입력 크기(심볼 수, 지표 수, edge 수)에 비례하므로, 운영 데이터 분포에 따라 체감 영향이 달라짐.
- serializer 이슈의 다수는 **호출 뷰의 prefetch 누락**이 근본 원인이므로, 1절(뷰)과 3절(serializer)의 동일 대상은 한 번의 뷰 수정으로 함께 해소됨(예: #4-2 ≡ #4-A, #1-C ≡ views.py:545 LOW).
- 코드는 일절 수정하지 않음. 본 문서는 감사 결과만 기록함.
