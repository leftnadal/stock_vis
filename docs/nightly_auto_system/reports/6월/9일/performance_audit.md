# API 성능 감사 보고서

- **작성일**: 2026-06-09
- **유형**: 읽기 전용 감사 (코드 미수정)
- **범위**: 뷰 17개 + 모델 7개 + Serializer 다수
- **검사 항목**: ① N+1 쿼리 ② 인덱스 누락 ③ 느린 Serializer ④ 페이지네이션 누락

> **경로 참고**: 디렉토리 구조상 실제 경로는 `packages/shared/stocks/*`, `apps/chain_sight/*`, `apps/market_pulse/*`(=macro/Market Pulse), `services/*` 로 분산되어 있다. 지시서의 약식 경로를 실제 경로에 매핑하여 감사했다.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 주요 이슈 |
|--------|------|----------|
| **HIGH** | **10** | validation `_build_metric` N+1(~350쿼리), `DataBasketSerializer` aggregate 폭증, `Users.get`/screener 페이지네이션 누락, Watchlist/Overview 직렬화 N+1, `NewsEntity` 복합 인덱스 부재 |
| **MED** | **16** | chain_sight edge 루프 N+1, `IndicatorComparisonView` N+1, news prefetch 누락, `task_name`/`llm_analyzed` 인덱스, 다수 페이지네이션 누락 |
| **LOW** | **8** | icontains 풀스캔(소규모), over-fetch, JSONB GIN 인덱스, 이론적 정렬 인덱스 |

**카테고리별 분포**

| 카테고리 | HIGH | MED | LOW |
|----------|------|-----|-----|
| ① N+1 쿼리 | 5 | 6 | 2 |
| ② 인덱스 누락 | 1 | 3 | 4 |
| ③ 느린 Serializer | 3 | 4 | 0 |
| ④ 페이지네이션 누락 | 1 | 3 | 2 |

**최우선 처방 3건**
1. `validation/api/views.py` `_build_metric` / `LeaderComparison` — 루프 내 `.first()` 쿼리를 stock 단위 bulk fetch + 메모리 dict 조인으로 전환 (단일 호출 350쿼리+ → 5쿼리 미만)
2. `rag_analysis/serializers.py` `DataBasketSerializer` — `count()`/`aggregate()` 4회/객체를 뷰 `annotate()` 기반으로 전환 (세션 목록에 nested되어 곱연산 폭증)
3. `users/views.py` `Users.get` — `prefetch_related("favorite_stock")` + 페이지네이션 (N+1 + 무제한 반환 동반)

> **구조적 관찰**: stocks의 movers/fundamentals 계열과 market_pulse는 대부분 외부 FMP API dict를 직렬화하는 구조라 DB 부하가 낮다. 실제 DB 병목은 **validation / rag_analysis / users / news / chain_sight 그래프** 5개 영역에 집중된다. graph_analysis/sec_pipeline의 인덱스 설계는 양호하다.

---

## 상세

### ① N+1 쿼리

#### [HIGH] [중간] `services/validation/api/views.py:276-368` — `_build_metric` 카테고리×지표×연도 중첩 쿼리
`ValidationMetricsView`가 `category=all`이면 전 카테고리를 돌고(L247) 카테고리당 지표를 돌며 `_build_metric`을 호출. 지표 1개당:
- `MetricDefinition.filter(pk).first()` (L262)
- `CompanyMetricSnapshot` latest (L278) + 없으면 any_snap 1회 (L298)
- `CompanyBenchmarkDelta.filter().first()` (L316)
- `CompanyMetricSnapshot` history `[:5]` (L339)
- **history 루프 내** `PeerMetricBenchmark.filter(...).first()` × 최대 5회 (L349) ← 핵심 폭증점

지표당 ~9쿼리 × 40+지표 = **350쿼리+** / 1회 호출. 인덱스(`[symbol,metric_code]`, `[symbol,fiscal_year]`)는 타지만 **쿼리 횟수 자체가 N+1**이라 배칭으로 풀어야 한다.
**권장**: stock 단위로 진입 전 (a) `MetricDefinition.in_bulk(codes)`, (b) 해당 stock의 `CompanyMetricSnapshot` 전건 1쿼리, (c) `CompanyBenchmarkDelta` 전건 1쿼리, (d) `PeerMetricBenchmark` 전건 1쿼리를 받아 `(metric_code, fiscal_year)` 키 dict로 메모리 조인.

#### [HIGH] [중간] `services/validation/api/views.py:459-475` — `LeaderComparison` 전 지표 루프 3쿼리/회
`all_metrics`(CATEGORY_METRICS 평탄화) 루프마다 `MetricDefinition.first()`(L460) + `CompanyMetricSnapshot.first()`(L464) + `CompanyMetricSnapshot.first()`(L470) = **3N 쿼리**(40지표면 ~120).
**권장**: `MetricDefinition.in_bulk()` + company/leader snapshot을 `metric_code_id__in=codes, symbol_id__in=[stock.symbol, leader.symbol], fiscal_year=latest, value_status="normal"`로 일괄 조회 후 `{(symbol, code): snap}` dict lookup.

#### [HIGH] [쉬움] `packages/shared/stocks/serializers.py:451-460` — `WatchListStockSerializer` 목록 N+1
`get_latest_price`(L451)가 `DailyPrice.objects.filter(stock=obj).order_by("-date").first()`로 **종목마다 1쿼리**. Watchlist는 다건(many=True)이라 N종목 → N쿼리(진성 N+1). `get_chart_data`(L458)도 동일 패턴 + **`return`문 누락으로 항상 `None` 반환(별도 버그)**.
**권장**: 뷰 queryset에서 `Prefetch`로 최신 가격 일괄 로드 또는 `Stock.real_time_price` 우선 사용. chart_data는 7일치를 `prefetch_related(Prefetch(...))`로 일괄.

#### [HIGH] [쉬움] `packages/shared/stocks/serializers.py:241-353` — `OverviewTabSerializer.get_dynamic_layers` 1+6 쿼리
단일 객체에 6개 역참조를 개별 쿼리로 접근: `category_signals.all()`(L252), `validation_news_summary`(L271), `sensitivity_profile`(L290), `growth_stage`(L305), `capital_dna`(L322), `narrative_tag`(L340). `StockOverviewAPIView`(views.py:545)는 `select_related("overview_ko")`만 적용. 코드 주석(L244)에 "TODO: prefetch_related + 캐싱" 명시. 운영상 캐시(`stock_overview_{symbol}`, views.py:536)로 완화되나, **캐시 미적용 `StockCompleteDataAPIView`(views.py:932)에서는 그대로 노출**.
**권장**: `get_queryset`에 OneToOne 5개 `select_related(...)` + `prefetch_related("category_signals")`. cache miss 시 6쿼리→1쿼리.

#### [HIGH] [중간] `packages/shared/users/views.py:92-95` — `Users.get` favorite_stock M2M N+1
`User.objects.all()` → `UserSerializer(many=True)`. `favorite_stock`이 `StockListingField(many=True)`(serializers.py:16)라 User마다 M2M 별도 조회 → 1+N. 페이지네이션도 없어 ④와 동반.
**권장**: `User.objects.prefetch_related("favorite_stock").all()` + 페이지네이션.

#### [MED] [중간] `apps/chain_sight/api/views.py:78-91` — Graph edge 루프 CoMention/PriceCoMovement 2쿼리/엣지
depth 최대 3 그래프의 **모든 edge**에 대해 `CoMentionEdge.filter(symbol_a,symbol_b).first()`(L84) + `PriceCoMovement.filter(...).first()`(L86) = **2E 쿼리**. depth=3에서 edge 수십~수백, 캐시 없는 경로.
**권장**: 전체 edge에서 (a,b) 페어 수집 후 `Q(symbol_a__in, symbol_b__in)` 1~2쿼리 bulk 조회 → `{(a,b): row}` dict lookup. (symbol_a/symbol_b 인덱스 존재해 in-clause 효율적)
> 참고: 같은 파일 `SectorGraphView`(L463)/`NeighborGraphView`(L619)는 Stock 메타를 `filter(symbol__in)` + dict map으로 **이미 bulk 처리** — 모범 패턴.

#### [MED] [중간] `packages/shared/stocks/views_indicators.py:371-434` — `IndicatorComparisonView.post` 종목당 2쿼리 + 무제한 입력
`for symbol in symbols:` 내부에서 `Stock.objects.get(symbol=symbol)`(L375) + `DailyPrice.filter(stock=stock).order_by("-date")[:50]`(L380) → **2N 쿼리**. POST 바디 심볼 개수 상한 없음.
**권장**: `Stock.objects.in_bulk(symbols)` 일괄 조회 + `len(symbols) > 20` 가드.

#### [MED] [쉬움] `services/news/api/views.py:117-123` `stock_news` / `:309-311` `market` — entities prefetch 누락
두 액션 모두 새 queryset을 만들면서 `.prefetch_related("entities")`를 빠뜨려, `NewsArticleListSerializer`가 기사 수만큼 entities 추가 쿼리. 캐시로 완화되나 cold/refresh 시 폭증.
**권장**: 두 queryset에 `.prefetch_related("entities")` 추가.

#### [MED] [쉬움] `services/news/api/views.py:362-396` — `NewsViewSet.trending` 루프 내 쿼리 + 중첩 N+1
집계는 1쿼리지만 루프(L370)에서 종목별 `NewsArticle.filter(entities__symbol=...)` 반복(limit 상한 없음, L335). 결과를 다시 `entities` prefetch 없이 직렬화(L387).
**권장**: 루프 쿼리에 `.prefetch_related("entities")`, `limit = min(limit, 50)`.

#### [MED] [쉬움] `services/serverless/views_admin.py:502-531` — `AdminNewsCategoryView.get` resolve_symbols N+1
루프 내 `cat.resolve_symbols()`가 카테고리마다 `SP500Constituent.filter().values_list()` 쿼리(news/models.py:514) → 1+N. ④ 페이지네이션 누락과 동반.
**권장**: 전 카테고리 sector/sub_sector를 모아 단일 `SP500Constituent` 쿼리로 prefetch 후 매핑, 또는 목록 응답에서 심볼 카운트 제외하고 상세에서만 계산.

#### [MED] [쉬움] `services/rag_analysis/serializers.py:86-87` (`AnalysisSessionSerializer`) + `views.py:429` — basket prefetch 누락
세션 직렬화 시 nested `messages`(L86) + `basket`(L87, 그 안의 items/units)을 전개하나, `AnalysisSessionListCreateView.get`은 `prefetch_related("messages")`만 함 → 세션마다 basket 조회 + units aggregate 폭증.
**권장**: `.select_related("basket").prefetch_related("messages", "basket__items")`.

#### [MED] [쉬움] `services/serverless/serializers.py:574-577` `ScreenerAlertSerializer.get_preset_name` / `:649` `AlertHistorySerializer.alert_name` — FK select_related 누락 위험
`obj.preset.icon/name`(L574), `source="alert.name"`(L649) 역참조. 목록 직렬화 시 행마다 FK 조회. 목록 뷰 쿼리셋에 `select_related("preset")`/`select_related("alert")` 보장 필요.

#### [LOW] [쉬움] `packages/shared/stocks/views_mvp.py:47-62` — `StockMVPListView` over-fetch
루프가 Stock 자체 컬럼만 접근해 진성 N+1은 아니나, `queryset[:20]`을 `.only()` 없이 60+컬럼 전체 로드.
**권장**: `.only("symbol","stock_name","sector","real_time_price","change","change_percent","market_capitalization")`.

#### [LOW] `apps/chain_sight/api/views.py:809-920` — `SignalFeed` 시드 페어별 Neo4j shortestPath 루프
페어마다 `repo.run_query(shortestPath)` 개별 실행(L816). `max_candidates = page_size*3` 상한 + 결과 캐시(L767)라 LOW. 개선 시 `UNWIND $pairs` 단일 쿼리화 가능.

---

### ② 인덱스 누락

#### [HIGH] [쉬움] `services/news/models.py:178` (`NewsEntity.symbol`) — symbol+news 복합 인덱스 부재
`symbol`은 단일 `db_index=True`지만 핵심 쿼리는 **`news__published_at` 조인 + `symbol` 필터** 조합(views.py:119 stock_news, 162 stock_sentiment, 362 trending, 757 keyword fallback). 단일 인덱스로는 시간범위 조인을 못 좁힘. 현 인덱스는 `["symbol","entity_type"]`, `["sentiment_score"]`뿐(L222-225).
**권장**: `models.Index(fields=["news", "symbol"])` 또는 `["symbol","news"]` 추가.

#### [MED] [쉬움] `services/news/models.py:535-536` (`NewsCollectionLog.task_name`) — 인덱스 부재
`task_name` 단독 인덱스 없음. `pipeline_health`(views.py:1616~1757의 6개 Phase가 각각 `task_name=`/`task_name__in` 필터), `collection_logs`(L1447), `task_timeline`이 빈번히 필터. 현 인덱스는 `["provider","-executed_at"]`(L547)뿐 → **admin 대시보드 호출당 수십 쿼리 전부 풀스캔 위험**.
**권장**: `models.Index(fields=["task_name", "-executed_at"])`.

#### [MED] [쉬움] `services/news/models.py:104,116` (`importance_score`, `llm_analyzed`) — 복합/updated_at 인덱스 부재
둘 다 단일 인덱스이나 `llm_usage`/`pipeline_health`에서 `llm_analyzed=True` + `updated_at__gte`(views.py:1713,1876,2078), `importance_score__isnull=False` + `llm_analyzed=False`(L1717,2082) 복합 조건 반복. `updated_at` 인덱스 없음.
**권장**: `updated_at` db_index 또는 `["llm_analyzed","updated_at"]` 복합. (Tier 필터 `llm_analysis__tier`는 JSONField라 LOW.)

#### [MED] [쉬움] `services/rag_analysis/models.py:177-179` (`AnalysisMessage`) + `:128-133` (`AnalysisSession`) — 정렬 복합 인덱스 부재
- `SessionMessagesView`(views.py:496)가 `session.messages.all().order_by("created_at")` → `(session, created_at)` 복합 인덱스 없어 정렬 비용.
- `AnalysisSessionListCreateView`(views.py:429)가 `filter(user=...)` + `ordering=["-updated_at"]`(Meta L149) → `(user, -updated_at)` 인덱스 없음. `DataBasket`(models.py:14)도 동일.
**권장**: `Index(["session","created_at"])`, `Index(["user","-updated_at"])`.

#### [LOW] [쉬움] `packages/shared/stocks/models.py` — `stock_name` icontains 풀스캔
`StockSearchAPIView`(views.py:223) `Q(stock_name__icontains) | Q(symbol__icontains)` + `StockMVPListView`(views_mvp.py:36) 동일. `icontains`(LIKE '%x%')는 선행 와일드카드라 B-tree 무효 → stock_name 풀스캔. 단 `[:20]`/`[:10]` 슬라이스 + 현 종목 규모(~500여)라 영향 제한적.
**권장(선택)**: 규모 확대 시 `pg_trgm` GIN 인덱스(`GinIndex(fields=["stock_name"], opclasses=["gin_trgm_ops"])`) 또는 `istartswith` 전환.

#### [LOW] [쉬움] `packages/shared/stocks/models.py:1015` — `EODSignal.signals` JSONB contains GIN 부재
`EODSignalDetailView`(views_eod.py:76) `signals__contains=[{"id": signal_id}]` + `date` 필터. `(date,-composite_score)` 복합 인덱스(L1050)는 있으나 JSONB 멤버십은 순차 스캔.
**권장(선택)**: `GinIndex(fields=["signals"])`.

#### [LOW] [높음] `packages/shared/stocks/models.py:156` — `sector__icontains` 풀스캔
`StockListAPIView`(views.py:122)의 `sector__icontains`는 sector 인덱스(L156)를 못 탐(LIKE). 페이지네이션 적용으로 일부 완화.
**권장(선택)**: 정확 매칭(`iexact`) 또는 pg_trgm.

#### [LOW] [쉬움] `services/sec_pipeline/models.py:391-427` (`PipelineIntelligenceReport.report_date`) — 정렬 인덱스 부재(이론적)
`ordering=["-report_date"]` + `get_latest_by="report_date"`인데 인덱스 없음. 단 하루 1행 수준 배치 리포트라 실무 영향 없음.

> **인덱스 양호 확인**: `graph_analysis`(전 조회 패턴 복합 인덱스 완비, 게다가 `_dormant`로 런타임 영향 0), `sec_pipeline`(symbol+filing_date, source_company+relationship_type, neo4j_dirty 등 완비), DailyPrice/재무제표(stock+date, stock+period_type+fiscal_year), users Portfolio/Watchlist, serverless MarketMover/Breadth/SectorPerformance/관계 테이블 모두 사용 패턴에 맞는 인덱스 존재 → **해당 없음**.

---

### ③ 느린 Serializer (SerializerMethodField/property 내 추가 쿼리)

#### [HIGH] [쉬움] `services/rag_analysis/serializers.py:34-60` (`DataBasketSerializer`) — 객체당 aggregate/count ×4
`can_add_item`(→ models.py:34 `.count()`), `items_count`(→ models.py:38 `.count()`), `current_units`(→ models.py:43 `aggregate(Sum)`), `remaining_units`(→ current_units 재호출, aggregate 또 1회). **prefetch_related("items")는 `.all()` 캐시만 채우고 `count()`/`aggregate()`는 캐시 우회** → 바구니당 최대 4쿼리. `AnalysisSessionSerializer`에 nested(L87)되어 **세션 목록에서 곱연산 폭증**.
**권장**: 뷰에서 `annotate(items_count=Count("items"), current_units_agg=Sum("items__data_units"))` 후 serializer가 annotate 값 참조. `can_add_item`/`remaining_units`도 annotate 기반 계산.

#### [HIGH] [쉬움] `packages/shared/stocks/serializers.py:451-460` (`WatchListStockSerializer`) — ①과 동일 근원
`get_latest_price`/`get_chart_data`가 SerializerMethodField 내부에서 `DailyPrice.filter()` 실행. many=True 직렬화 시 종목당 2쿼리. (상세는 ① HIGH 참조)

#### [HIGH] [쉬움] `packages/shared/stocks/serializers.py:241-353` (`get_dynamic_layers`) — ①과 동일 근원
6개 관계를 SerializerMethodField에서 미prefetch 접근. 캐시 미적용 `StockCompleteDataAPIView`에서 노출. (상세는 ① HIGH 참조)

#### [MED] [중간] `packages/shared/users/serializers.py:284,347` (`WatchlistSerializer.stock_count`) — property `.count()` N+1
`stock_count = ReadOnlyField()` → 모델 property `self.items.count()`(models.py:212). `WatchlistListCreateView.get`(views.py:624)이 페이지당 20개 직렬화 시 각 항목 COUNT 쿼리. 캐시(300s)로 완화.
**권장**: 뷰에서 `.annotate(item_count=Count("items"))` 후 serializer가 annotate 사용.

#### [MED] [중간] `services/serverless/serializers.py:125-144` (`MarketMoverListSerializer`) — 행마다 `IndicatorCalculator()` 인스턴스화
`get_sector_alpha_display`/`get_etf_sync_display`/`get_volatility_pct_display`가 각 행에서 `IndicatorCalculator()`를 새로 생성(L129,135,141). DB 쿼리는 없으나 수십~수백 행 × 3회 생성 오버헤드.
**권장**: 모듈/클래스 레벨 싱글톤 또는 `to_representation`에서 1회 생성.

#### [MED] [쉬움] `services/serverless/serializers.py:221-226` (`MarketBreadthSerializer.get_signal_interpretation`) — 행마다 서비스 인스턴스화
히스토리 직렬화(views.py:695 다건)에서 행마다 `MarketBreadthService()` 생성(L225). 정적 매핑이면 불필요.
**권장**: 모듈 레벨 캐싱.

> **Serializer 양호 확인**: stocks movers/fundamentals serializer(FMP dict 입력 `serializers.Serializer`, `.get()`만 호출 — 구조적으로 N+1 불가), market_pulse(plain Serializer), news(entities/highlights는 nested지만 prefetch 처리), chain_sight `path_watchlist.py`(JSONField 읽기, 쿼리 없음), validation(serializer 미사용, 수동 dict) → **해당 없음**.

---

### ④ 페이지네이션 누락

#### [HIGH] [쉬움] `packages/shared/users/views.py:92-95` (`Users.get`) — 관리자 사용자 목록 전건
`User.objects.all()` 전건 직렬화, pagination 없음. 사용자 증가 비례 폭증 + ① favorite_stock N+1 동반.
**권장**: `PageNumberPagination`.

#### [HIGH] [중간] `packages/shared/stocks/views_screener.py:30` (`StockScreenerView`) 외 5개 뷰 — limit max 1000 무페이징
`limit` 최대 **1000**(serializers_screener.py:201)까지 허용하며 `stocks` 배열 전체 반환(L142). `enrich_with_quotes`(L136)로 외부 호출까지 증폭. 동일 패턴: `LargeCapStocksView`(L264), `HighDividendStocksView`(L317), `SectorStocksView`(L371), `LowBetaStocksView`(L430), `ExchangeStocksView`(L482).
**권장**: FMP 응답 기반이라 DRF pagination 직접 적용은 어려우므로 limit 상한을 100~200으로 축소 또는 cursor/offset 페이징 도입.

#### [HIGH] [중간] `services/rag_analysis/views.py:482-498` (`SessionMessagesView`) — 메시지 전건
`session.messages.all()`(L496) 전건 직렬화. 대화가 길어지면 수백~수천 건. ② `(session, created_at)` 인덱스 부재와 동반.
**권장**: 페이지네이션 또는 최근 N건 슬라이싱.

#### [MED] [쉬움] `packages/shared/users/views.py:269-273` (`PortfolioListCreateView.get`) — 포트폴리오 전건
사용자 포트폴리오 전건 반환, pagination 없음. 보통 수십개라 MED.

#### [MED] [쉬움] `services/news/api/views.py:1452-1465` (`collection_logs`) / `:2162-2186` (`task_timeline`) — 로그 전건
`collection_logs`는 30일치 `qs.values()` 전건(수백~수천), `task_timeline`은 72시간치 전건 루프 직렬화. 둘 다 pagination 없음.
**권장**: limit/offset 또는 PageNumberPagination.

#### [MED] [중간] `services/rag_analysis/views.py:418-433` (`AnalysisSessionListCreateView.get`) — 세션 전건 + nested 전개
사용자 세션 전건 반환 + 각 세션 nested messages/basket 전개. ① basket prefetch 누락과 동반.

#### [MED] [중간] `packages/shared/stocks/views_indicators.py:348-436` (`IndicatorComparisonView`) — 입력 심볼 무제한
`symbols` 배열 전체를 무제한으로 받아 누적 후 일괄 반환. pagination + 입력 상한 모두 없음.
**권장**: `len(symbols) > 20` 가드(페이지네이션보다 입력 상한이 적합).

#### [LOW] `services/serverless/views_admin.py:502-531` (`AdminNewsCategoryView`) — 카테고리 전건
무제한 반환 + ① resolve_symbols N+1 동반. 카테고리 수가 적어 실무 영향은 작음.

#### [LOW] `packages/shared/stocks/views_mvp.py:17-68` (`StockMVPListView`) — `[:20]` 상한으로 실질 안전
pagination 미설정이나 하드 상한으로 폭증 차단. 의도된 MVP 제약.

> **페이지네이션 양호 확인**: `StockListAPIView`(StockListPagination 50/max200), `NewsViewSet` 기본 list(NewsArticlePagination), `all_news`/`market`(수동 offset/max100), `WatchlistListCreateView`/`WatchlistStocksView`(수동 Paginator), rag `UsageHistoryView`(Django Paginator), chain_sight `SectorGraphView`/`NeighborGraphView`(limit≤30)/`SignalFeedView`(자체 page/page_size), 검색/배치 뷰(`[:N]` 슬라이스 상한) → **해당 없음**.

---

## 부록: 영역별 우선순위 종합

| 순위 | 위치 | 카테고리 | 심각도 | 한 줄 |
|------|------|----------|--------|-------|
| 1 | `validation/api/views.py:276-368` `_build_metric` | N+1 | HIGH | history×peer band ~350쿼리 → bulk + dict 조인 |
| 2 | `rag_analysis/serializers.py:34-60` `DataBasketSerializer` | Serializer | HIGH | count/aggregate ×4/객체, 세션 nested 곱폭증 → annotate |
| 3 | `validation/api/views.py:459-475` `LeaderComparison` | N+1 | HIGH | 지표 루프 3N쿼리 → in_bulk |
| 4 | `users/views.py:92-95` `Users.get` | N+1 + 페이징 | HIGH | favorite_stock prefetch + 페이지네이션 |
| 5 | `stocks/serializers.py:451-460` `WatchListStockSerializer` | N+1 + Serializer | HIGH | 종목당 2쿼리 + get_chart_data return 누락 버그 |
| 6 | `stocks/serializers.py:241-353` `get_dynamic_layers` | N+1 + Serializer | HIGH | 1+6 관계, complete_data에서 무캐시 노출 |
| 7 | `news/models.py:178` `NewsEntity` | 인덱스 | HIGH | symbol+news 복합 인덱스 |
| 8 | `stocks/views_screener.py` 6개 뷰 | 페이징 | HIGH | limit max 1000 → 상한 축소 |
| 9 | `rag_analysis/views.py:496` `SessionMessagesView` | 페이징 + 인덱스 | HIGH | 메시지 전건 + (session,created_at) 인덱스 |
| 10 | `chain_sight/api/views.py:78-91` edge 루프 | N+1 | MED | CoMention/Price 2E쿼리 → bulk |
| 11 | `news/models.py:535` `NewsCollectionLog.task_name` | 인덱스 | MED | pipeline_health 다발 필터 풀스캔 |
| 12 | `news/api/views.py:117,309` `stock_news`/`market` | N+1 | MED | entities prefetch 누락 |

---

*본 보고서는 읽기 전용 정적 분석 결과이며, 어떤 소스 파일도 수정하지 않았다. 라인 번호는 감사 시점(2026-06-09) 기준이다.*
