# API 성능 감사 보고서

- **일자**: 2026-06-19
- **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis` (모노레포)
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **검사 항목**: ① N+1 쿼리 ② 인덱스 누락 ③ 느린 Serializer ④ 페이지네이션 누락
- **분석 방법**: 6개 에이전트 병렬 정적 분석 (뷰 17개 + 모델 7개 + serializer 11개)

> ⚠️ **경로 주의**: 지시서의 앱 경로(`stocks/`, `macro/`, `chainsight/` 등)는 모노레포 마이그레이션으로 실제 위치가 다릅니다.
> `stocks → packages/shared/stocks`, `users → packages/shared/users`, `macro → apps/market_pulse`,
> `chainsight → apps/chain_sight`, `news/serverless/rag_analysis/validation/sec_pipeline → services/*`,
> `graph_analysis → services/_dormant/graph_analysis`. 본 보고서의 라인 번호는 실제 파일 기준입니다.

---

## 요약

### 심각도별 이슈 수

| 심각도 | N+1 (뷰) | 인덱스 누락 | Serializer | 페이지네이션 | 합계 |
|--------|:---:|:---:|:---:|:---:|:---:|
| **HIGH** | 4 | 2 | 3 | 0 | **9** |
| **MED**  | 2 | 12 | 2 | 7 | **23** |
| **LOW**  | 2 | 3 | 1 | 2 | **8** |
| **합계** | **8** | **17** | **6** | **9** | **40** |

### 즉시 조치 권장 TOP 5 (HIGH + 영향도 순)

| # | 위치 | 문제 | 난이도 |
|---|------|------|:---:|
| 1 | `services/validation/api/views.py:459-504` (`LeaderComparisonView`) | 메트릭(50~100개)마다 3쿼리 → 최대 150~300 쿼리 | 높음 |
| 2 | `services/validation/api/views.py:254-401` (`ValidationMetricsView`) | 카테고리×메트릭×연도 중첩 N+1 (메트릭당 ~6쿼리) | 높음 |
| 3 | `services/news/api/views.py:360-396` (`NewsViewSet.trending`) | 집계 후 심볼마다 기사 재조회 (1+N) | 중간 |
| 4 | `apps/chain_sight/api/views.py:78-91` (`ChainSightGraphView`) | edge마다 `CoMentionEdge`+`PriceCoMovement` 2쿼리 | 중간 |
| 5 | `packages/shared/stocks/serializers.py:451-460` (`WatchListStockSerializer`) | 관심종목 직렬화 시 종목마다 `DailyPrice` 2쿼리 | 쉬움/중간 |

### 검토했으나 이슈 아님 (오탐 방지 메모)

- `views_eod.py` `EODSignalDetailView` — 이미 `select_related("stock")` 적용됨 (정상).
- `apps/chain_sight/api/views.py` `SignalFeedView` — 수동 페이지네이션 구현됨 (정상).
- `views_market_movers.py`, `views_fundamentals.py`, `apps/market_pulse/views.py`, `services/sec_pipeline/views.py` — 외부 API 기반 또는 단일 객체 조회로 N+1/페이지네이션 해당 없음.
- serializer 11개 중 `serializers_fundamentals/market_movers/exchange/screener`, `rag_analysis`, `news/api`, `portfolio/api`, `market_pulse` — 포맷팅/이미 로드된 관계만 사용, 이슈 없음.

---

## 1. N+1 쿼리 (뷰)

### [HIGH] H1-1. `LeaderComparisonView` 전 지표 × 3쿼리
- **위치**: `services/validation/api/views.py:459-504`
- **설명**: `all_metrics`(카테고리×메트릭 = 50~100개) 루프 안에서 항목마다 `MetricDefinition.objects.filter(pk=mc).first()`(L460), `CompanyMetricSnapshot...first()`(L464-469, 회사), `CompanyMetricSnapshot...first()`(L470-475, 리더)를 각각 호출. 최소 150~300회 개별 쿼리 발생.
- **수정난이도**: 높음
- **권장수정**: 루프 전 `metric_code__in`으로 `MetricDefinition`/`CompanyMetricSnapshot`을 한 번에 fetch 후 dict 룩업.
  ```python
  metric_ids = [mc for _, mc in all_metrics]
  metrics_dict = {m.metric_code: m for m in MetricDefinition.objects.filter(metric_code__in=metric_ids)}
  company_snaps = {cs.metric_code_id: cs for cs in CompanyMetricSnapshot.objects.filter(
      symbol=stock, fiscal_year=latest_fy, metric_code_id__in=metric_ids, value_status="normal")}
  leader_snaps = {...}  # 동일 패턴, symbol_id=leader.symbol
  ```

### [HIGH] H1-2. `ValidationMetricsView` 중첩 N+1
- **위치**: `services/validation/api/views.py:254-265` (`_build_category`), `276-401` (`_build_metric`)
- **설명**: 카테고리 루프(L247) → `_build_category`에서 `metric_code`마다 `MetricDefinition.objects.filter(pk=mc).first()`(L262). 다시 `_build_metric`에서 latest snapshot 1쿼리(L278-283) + history 루프(L339-368)에서 연도마다 `PeerMetricBenchmark...first()`(L349-353). 메트릭당 약 6쿼리, 메트릭 10개면 60+쿼리.
- **수정난이도**: 높음
- **권장수정**: `MetricDefinition`은 `metric_code__in` 일괄 로드 후 dict 룩업. history snapshot의 연도 목록으로 `PeerMetricBenchmark`를 `fiscal_year__in` 한 번에 적재.

### [HIGH] H1-3. `NewsViewSet.trending()` 집계 후 기사 재조회
- **위치**: `services/news/api/views.py:360-396`
- **설명**: `NewsEntity`를 `values("symbol").annotate()`로 집계(상위 `limit`개) 후, **각 심볼마다** `NewsArticle.objects.filter(entities__symbol=symbol, ...)`(L373)로 기사 재조회 + `entities__symbol` JOIN 반복. `limit=20`이면 1+20 쿼리.
- **수정난이도**: 중간
- **권장수정**: 윈도우 함수(`ROW_NUMBER() OVER (PARTITION BY symbol ...)`) raw 쿼리로 심볼별 상위 N건을 단일 쿼리로 추출하거나, 대상 심볼 전체 기사를 한 번에 fetch 후 파이썬에서 그룹핑.

### [HIGH] H1-4. `ChainSightGraphView` edge별 2쿼리
- **위치**: `apps/chain_sight/api/views.py:78-91`
- **설명**: `result["edges"]` 루프에서 edge마다 `CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()`(L84) + `PriceCoMovement.objects.filter(...).first()`(L86). edge 20개면 40쿼리.
- **수정난이도**: 중간
- **권장수정**: edge 쌍 목록을 미리 모아 `CoMentionEdge`/`PriceCoMovement`를 일괄 조회 후 `(symbol_a, symbol_b)` 키 dict로 룩업.

### [HIGH] H1-5. `IndicatorComparisonView` 심볼 루프 N+1
- **위치**: `packages/shared/stocks/views_indicators.py:371-389`
- **설명**: `for symbol in symbols:` 루프 안에서 `Stock.objects.get(symbol=symbol)`(L375)와 `DailyPrice.objects.filter(stock=stock)...`(L380-384)를 매번 실행. 심볼 N개면 2N 쿼리.
- **수정난이도**: 쉬움
- **권장수정**: `Stock.objects.filter(symbol__in=symbols)`로 dict 구성, `DailyPrice.objects.filter(stock__symbol__in=symbols)`로 일괄 조회 후 심볼별 그룹핑.

### [HIGH] H1-6. `StockMVPListView` 슬라이스 후 필드 lazy 접근
- **위치**: `packages/shared/stocks/views_mvp.py:41-62`
- **설명**: `Stock.objects.all()[:20]`(L41) 후 루프(L47)에서 `stock.real_time_price`, `stock.change`, `stock.market_capitalization` 접근. 본 필드들은 동일 row라 lazy 추가 쿼리는 없으나, **페이지네이션 부재**(하드코딩 `[:20]`)와 결합되어 구조적 위험. → 페이지네이션 항목(P-9)과 연계.
- **수정난이도**: 쉬움
- **권장수정**: `pagination_class` 도입(아래 §4 참조). 필드는 `values()` 또는 `only()`로 명시 로드 권장.

### [MED] H1-7. `AdminNewsCategoryView` `resolve_symbols()` 루프 호출
- **위치**: `services/serverless/views_admin.py:502-531`
- **설명**: `NewsCollectionCategory.objects.all()`(L505) 루프(L507)에서 `cat.resolve_symbols()`(L508) 호출. 해당 메서드가 내부 쿼리를 포함하면 카테고리 수만큼 추가 쿼리.
- **수정난이도**: 중간
- **권장수정**: `resolve_symbols()` 구현 확인 후 연관 모델 `prefetch_related` 또는 bulk 조회로 전환.

### [MED] H1-8. `UserInterestListCreateView` FK 미적재
- **위치**: `packages/shared/users/views.py:1045-1060`
- **설명**: `UserInterest` 목록 직렬화 시 `auto_category_id` 등 FK가 있다면 `select_related` 부재로 항목별 추가 조회 가능 + 페이지네이션 없음(P-2와 중복).
- **수정난이도**: 쉬움
- **권장수정**: FK 존재 시 `.select_related('auto_category')`.

### [LOW] H1-9. `NewsViewSet.stock_news()` custom action prefetch 누락
- **위치**: `services/news/api/views.py:117-123`
- **설명**: 기본 ViewSet queryset은 `prefetch_related("entities")`(L71)지만 custom action에서 queryset을 새로 만들며 prefetch 누락. serializer가 `entities` 접근 시 N+1.
- **수정난이도**: 쉬움
- **권장수정**: 해당 쿼리에 `.prefetch_related("entities")` 추가.

---

## 2. 인덱스 누락

> filter/order_by에 쓰이거나 쓰일 후보 중 `db_index`·`Meta.indexes`·`unique`·FK(자동 인덱스) 어디에도 없는 필드. 실제 사용처가 grep으로 확인된 건은 "확인됨"으로 표기, 나머지는 "추정"으로 LOW~MED 처리.

### [HIGH] I-1. `NewsEntity.entity_type` — 사용 확인됨
- **위치**: `services/news/models.py:180`
- **설명**: `entity_type`(equity/index/etf...)에 단독 인덱스 없음(복합 `[symbol, entity_type]`만 존재). `news_relation_matcher.py:175`, `regulatory_service.py:661`에서 `filter(entity_type="equity")` 단독 필터 확인. NewsEntity는 NewsArticle M:N으로 대량 테이블.
- **수정난이도**: 쉬움 (마이그레이션 필요)
- **권장수정**: `models.Index(fields=["entity_type"])` 추가.

### [HIGH] I-2. `EODSignal.industry`
- **위치**: `packages/shared/stocks/models.py:1041`
- **설명**: EODSignal은 일별 aggregate 대량 테이블. `date`/`sector`는 인덱스 있으나 `industry` 없음. 산업별 필터/집계 시 풀스캔.
- **수정난이도**: 쉬움
- **권장수정**: `models.Index(fields=["date", "industry"])`.

### [MED] 인덱스 누락 (요약)

| # | 모델.필드 | 위치 | 사용 확인 | 권장 |
|---|----------|------|:---:|------|
| I-3 | `Stock.currency` | `packages/shared/stocks/models.py:154` | 추정 | `Meta.indexes` 추가 |
| I-4 | `Stock.asset_type` | `packages/shared/stocks/models.py:154` | 추정 | `Meta.indexes` 추가 |
| I-5 | `Stock.exchange` | `packages/shared/stocks/models.py:154` | 추정 | `Meta.indexes` 추가 |
| I-6 | `StockNews.sentiment` | `packages/shared/stocks/models.py:1164` | 추정 | `Index(["sentiment","-published_at"])` |
| I-7 | `UserInterest.interest_type` | `packages/shared/users/models.py:283` | 조회 보임 | `Index(["user","interest_type"])` |
| I-8 | `NewsCollectionCategory.category_type` | `services/news/models.py:483` | 확인됨(`tasks.py:373-381`) | `Index(["is_active","category_type"])` |
| I-9 | `StockSectorInfo.industry` | `services/serverless/models.py:133` | 추정 | `db_index=True` |
| I-10 | `StockKeyword.status` 단독 | `services/serverless/models.py:208` | 부분(복합만) | `Index(["status","-created_at"])` |
| I-11 | `AnalysisSession.status` | `services/rag_analysis/models.py:135` | 추정 | `Index(["user","status"])` |
| I-12 | `UsageLog.request_type` | `services/rag_analysis/models.py:256` | 확인됨 | 기존 복합 인덱스 순서 재확인 |
| I-13 | `FilingProcessLog.stage` 단독 | `services/sec_pipeline/models.py:282` | 추정 | `Index(["stage","-started_at"])` |
| I-14 | `UnmatchedCompanyQueue.source_symbol` | `services/sec_pipeline/models.py:357` | 추정 | `db_index=True` |

### [LOW] 인덱스 누락 (소규모 테이블 / 사용 미확인)

| # | 모델.필드 | 위치 | 비고 |
|---|----------|------|------|
| I-15 | `SectorETFMapping.etf_symbol` | `services/serverless/models.py:115` | 매핑 테이블 소규모 |
| I-16 | `CorporateAction.action_type` | `services/serverless/models.py:594` | 이벤트 타입별 조회 시 |
| I-17 | `CompanyAlias.ticker` | `services/sec_pipeline/models.py:315` | ticker 역조회 시 |

> `graph_analysis`(dormant): `CorrelationEdge.is_anomaly`, `CorrelationAnomaly.alerted`는 이미 `db_index=True` + 복합 인덱스 존재. 단독 조회 최적화는 선택사항, 휴면 앱이라 제외.

---

## 3. 느린 Serializer (SerializerMethodField 내 쿼리)

### [HIGH] S-1. `WatchListStockSerializer.get_latest_price()`
- **위치**: `packages/shared/stocks/serializers.py:451-456`
- **설명**: `DailyPrice.objects.filter(stock=obj).order_by("-date").first()` — `many=True`로 관심종목 N개 직렬화 시 종목당 1쿼리(1+N).
- **수정난이도**: 쉬움
- **권장수정**: 뷰에서 `annotate` 최신가 적재, 또는 `Stock.real_time_price` 직접 사용으로 메서드 제거.

### [HIGH] S-2. `WatchListStockSerializer.get_chart_data()`
- **위치**: `packages/shared/stocks/serializers.py:458-460`
- **설명**: `DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]` — 종목별 차트 쿼리(N+1). (현재 반환부 미완성으로 보이나 쿼리는 실행됨.)
- **수정난이도**: 중간
- **권장수정**: 뷰에서 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])`.

### [HIGH] S-3. `OverviewTabSerializer.get_dynamic_layers()`
- **위치**: `packages/shared/stocks/serializers.py:241-262`
- **설명**: `obj.category_signals.all()`(L251) reverse FK 접근. 리스트 직렬화 시 N+1. 코드 주석에 "Step 2~4에서 prefetch_related 필요" TODO 명시됨. (뷰 감사에서도 중복 검출됨.)
- **수정난이도**: 중간
- **권장수정**: 뷰 queryset에 `prefetch_related("category_signals")`.

### [MED] S-4. `PortfolioCreateUpdateSerializer.validate_stock()`
- **위치**: `packages/shared/users/serializers.py:203-221`
- **설명**: validator에서 `Stock.objects.get(symbol=...)`(L209). bulk create 시 항목마다 조회.
- **수정난이도**: 쉬움
- **권장수정**: 뷰에서 symbol 일괄 검증 후 검증된 객체 전달, 또는 `validate()`에서 batch 처리.

### [MED] S-5. `WatchlistItemCreateSerializer.validate_stock()`
- **위치**: `packages/shared/users/serializers.py:412-429`
- **설명**: validator에서 `Stock.objects.get(symbol=...)`(L417). 다건 추가 시 N쿼리.
- **수정난이도**: 쉬움
- **권장수정**: symbols 사전 조회 dict 캐싱 후 참조.

### [LOW] S-6. `PortfolioDetailSerializer.get_portfolio_weight()`
- **위치**: `packages/shared/users/serializers.py:133-139`
- **설명**: DB 쿼리는 아니나, `context['total_portfolio_value']` 누락 시 전 항목 weight=0. 뷰에서 1회 계산해 context 주입 필요.
- **수정난이도**: 쉬움
- **권장수정**: 뷰에서 합계 1회 산출 후 `context`로 전달.

---

## 4. 페이지네이션 누락

> list 형태(다건 반환) 엔드포인트에서 DRF `pagination_class` 또는 동등 수단 미적용. 외부 API 기반/고정 소규모/단일객체는 제외.

| # | 위치 | 엔드포인트 | 심각도 | 난이도 | 비고 |
|---|------|-----------|:---:|:---:|------|
| P-1 | `packages/shared/users/views.py:92-95` | `Users.get` 전체 사용자 | MED | 쉬움 | `User.objects.all()` 무제한 |
| P-2 | `packages/shared/users/views.py:1045-1060` | `UserInterestListCreateView.get` | MED | 쉬움 | H1-8과 연계 |
| P-3 | `services/rag_analysis/views.py:489-498` | `SessionMessagesView.get` | MED | 쉬움 | 세션 메시지 전량 |
| P-4 | `services/rag_analysis/views.py:50-54` | `DataBasketListCreateView.get` | MED | 쉬움 | prefetch는 있음 |
| P-5 | `services/rag_analysis/views.py:427-433` | `AnalysisSessionListCreateView.get` | MED | 쉬움 | `prefetch_related("messages")` 자체가 무거울 수 있음 |
| P-6 | `services/serverless/views_admin.py:502-531` | `AdminNewsCategoryView.get` | MED | 쉬움 | H1-7과 연계 |
| P-7 | `packages/shared/stocks/views_screener.py:30-538` | 6개 Screener 뷰(`StockScreenerView` 외 5종) | MED | 중간 | `APIView`+`many=True`, 최대 1000건 반환 |
| P-8 | `packages/shared/stocks/views_search.py:19-81` | `SymbolSearchView.get` | MED | 쉬움 | 수동 `[:10]`만, 의도면 문서화 |
| P-9 | `packages/shared/stocks/views_mvp.py:41-62` | `StockMVPListView.get` | MED | 쉬움 | 하드코딩 `[:20]`, H1-6 연계 |
| P-10 | `packages/shared/stocks/views_exchange.py:30-77` | `IndexQuotesView` | LOW | 쉬움 | 고정 소규모(주요 지수) — 용인 |
| P-11 | `packages/shared/stocks/views_exchange.py:248-296` | `SectorPerformanceView` | LOW | 쉬움 | 고정 ~11개 섹터 ETF — 용인 |

**공통 권장 패턴** (`APIView` 기반에 적용):
```python
from rest_framework.pagination import PageNumberPagination

class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

# get() 내부
paginator = DefaultPagination()
page = paginator.paginate_queryset(queryset, request)
serializer = SomeSerializer(page, many=True)
return paginator.get_paginated_response(serializer.data)
```

---

## 부록: 우선순위 로드맵 제안

1. **1차 (HIGH·고영향)**: validation 뷰 2건(H1-1, H1-2) → 메트릭 화면 응답 지연 최대 원인. dict 룩업 리팩토링.
2. **2차 (HIGH·중난이도)**: news trending(H1-3), chain_sight graph(H1-4), watchlist serializer(S-1/S-2/S-3) → 사용자 노출 빈도 높음.
3. **3차 (인덱스)**: 사용 확인된 I-1, I-8, I-12 + HIGH I-2 마이그레이션 1건으로 묶어 처리.
4. **4차 (페이지네이션)**: P-7(screener 1000건)·P-3·P-5 우선, 나머지 MED 일괄.
5. **상시**: validator 내 단건 조회(S-4/S-5)는 bulk 입력 도입 시 함께 정리.

> 본 보고서는 정적 분석 기반이며, "추정" 표기 인덱스 항목과 `resolve_symbols()`(H1-7) 등 일부는 런타임 쿼리 카운트(`django-debug-toolbar` / `CaptureQueriesContext`)로 실측 검증 후 착수 권장.
