# API 성능 감사 보고서

> 생성일: 2026-06-03 · 범위: 읽기 전용 정적 분석 (코드 미수정)
> 방법: 17개 뷰 + 7개 모델 + 11개 시리얼라이저 파일 정밀 분석 → 핵심 주장 6건 실코드 교차 검증

---

## 경로 매핑 (요청서 → 실제 저장소)

요청서의 경로는 구 구조 기준이며, 현재 저장소는 `packages/shared/`, `services/`, `apps/`로 재배치되어 있습니다.

| 요청서 경로 | 실제 경로 |
|---|---|
| `stocks/*` | `packages/shared/stocks/*` |
| `users/*` | `packages/shared/users/*` |
| `news/api/views.py` | `services/news/api/views.py` |
| `macro/views.py` | `apps/market_pulse/views.py` |
| `rag_analysis/*` | `services/rag_analysis/*` |
| `serverless/*` | `services/serverless/*` |
| `validation/api/views.py` | `services/validation/api/views.py` |
| `chainsight/api/views.py` | `apps/chain_sight/api/views.py` |
| `sec_pipeline/*` | `services/sec_pipeline/*` |
| `graph_analysis/models.py` | `services/_dormant/graph_analysis/models.py` (휴면) |

---

## 요약

### 심각도별 이슈 수

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 누락 | 합계 |
|---|---|---|---|---|---|
| **HIGH** | 7 | 0 | 4 | 0 | **11** |
| **MED**  | 5 | 3 | 5 | 6 | **19** |
| **LOW**  | 4 | 6 | 1 | 0 | **11** |
| **합계** | 16 | 9 | 10 | 6 | **41** |

> 오탐 제외 1건: `ScreenerAlertSerializer.get_can_trigger()`는 순수 datetime 비교로 DB 쿼리 없음 (검증 완료).

### 검증으로 보정된 항목

| 항목 | 1차 평가 | 보정 후 | 근거 |
|---|---|---|---|
| `OverviewTabSerializer` 의 chainsight OneToOne 5종 | HIGH×5 | MED 1건 통합 | 단건 detail 조회용(`.first()` 단일 객체)이라 list N+1 아님. 호출당 ~6 추가 쿼리. `get_korean_overview`(overview_ko)는 `views.py:546` `select_related`로 이미 커버됨 |
| `ScreenerAlertSerializer.get_can_trigger` | MED | **제외(오탐)** | `models.py:722` 본문이 datetime 연산만 — 쿼리 없음 |
| `MarketMover.mover_type` 인덱스 | HIGH | MED | `Meta.indexes`에 `(date, mover_type)` 복합 인덱스 존재 → 가장 흔한 `date+mover_type` 경로는 이미 커버. `mover_type` 단독 필터만 갭 |
| `DataBasketSerializer.get_can_add_item` | "쿼리 불명확" | MED 확정 | `models.py:34` `self.items.count()` 확인 — 뷰가 `prefetch_related("items")` 해도 `.count()`는 캐시 우회하여 매 객체 COUNT 발생 |

### 우선 처리 권장 (Top 5)

1. **[HIGH]** `services/news/api/views.py:116` `stock_news` 액션 — entities N+1 + 페이지네이션 부재 (검증됨)
2. **[HIGH]** `services/validation/api/views.py:459` `LeaderComparisonView` — 이중 루프 × 3쿼리 (40~150쿼리/요청)
3. **[HIGH]** `apps/chain_sight/api/views.py:78` `ChainSightGraphView` — 엣지당 2쿼리 (엣지 100개 = 200쿼리)
4. **[HIGH]** `services/serverless/views_admin.py:502` `AdminNewsCategoryView` — 카테고리당 `resolve_symbols()` + 페이지네이션 부재
5. **[MED→쉬움]** `packages/shared/stocks/views.py:546` `select_related` 확장 — chainsight OneToOne 5종 + `category_signals` prefetch (TODO 명시되어 있음, 인프라 이미 존재)

---

## 상세

### 1. N+1 쿼리

#### [HIGH] 1-1. `services/news/api/views.py:116-127` — `stock_news` 액션 ✅검증
```python
articles = (
    NewsArticle.objects.filter(entities__symbol=symbol, published_at__gte=from_date)
    .distinct().order_by("-published_at")
)
serializer = self.get_serializer(articles, many=True)  # NewsArticleListSerializer
```
- **문제**: 베이스 queryset(`views.py:71`)은 `prefetch_related("entities")`를 하지만, 이 액션은 `NewsArticle.objects`를 **직접** 새로 필터링해 prefetch를 우회한다. `NewsArticleListSerializer.entities`(many=True) 직렬화 시 기사당 entities 쿼리 발생. 또한 날짜 범위 내 전건을 limit 없이 반환 → 페이지네이션 부재 중복.
- **권장**: `.prefetch_related("entities")` 재적용 + limit/offset 페이지네이션 추가.
- **난이도**: 쉬움

#### [HIGH] 1-2. `services/news/api/views.py:370-391` — `trending` 액션
```python
for item in trending_data:
    recent_articles = (NewsArticle.objects.filter(entities__symbol=item["symbol"], ...)
        .distinct().order_by("-published_at")[:3])
    results.append({..., "recent_articles": NewsArticleListSerializer(recent_articles, many=True).data})
```
- **문제**: trending 심볼(최대 10개)마다 개별 기사 쿼리 + 각 기사의 entities N+1. 심볼당 비용이 곱해진다.
- **권장**: `entities__symbol__in=symbols`로 일괄 조회 후 메모리에서 심볼별 그룹핑(최대 3개 슬라이스).
- **난이도**: 높음

#### [HIGH] 1-3. `packages/shared/stocks/views_indicators.py:375` — `IndicatorComparisonView`
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)            # N회
    prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:50]  # N회
```
- **문제**: 심볼 N개 입력 시 2N 쿼리. 100심볼 = 200쿼리.
- **권장**: `Stock.objects.filter(symbol__in=symbols)` + `Prefetch('dailyprice_set', DailyPrice.objects.order_by("-date"))`.
- **난이도**: 중간

#### [HIGH] 1-4. `services/validation/api/views.py:459-475` — `LeaderComparisonView`
```python
for cat, mc in all_metrics:                              # 40~50개 조합
    md = MetricDefinition.objects.filter(pk=mc).first()  # +1
    company_snap = CompanyMetricSnapshot.objects.filter(symbol=stock, ..., metric_code_id=mc).first()  # +1
    leader_snap  = CompanyMetricSnapshot.objects.filter(symbol_id=leader.symbol, ..., metric_code_id=mc).first()  # +1
```
- **문제**: 카테고리×메트릭 전 조합을 루프 돌며 호출당 3쿼리 → 120~150쿼리.
- **권장**: `MetricDefinition.objects.in_bulk(...)` + 두 종목 스냅샷을 `symbol__in=[stock, leader]` 단일 쿼리로 선로드 후 dict 매칭.
- **난이도**: 높음

#### [HIGH] 1-5. `apps/chain_sight/api/views.py:78-91` — `ChainSightGraphView`
```python
for edge in result.get("edges", []):
    cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()   # 엣지당 +1
    pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first() # 엣지당 +1
```
- **문제**: depth 증가 시 엣지 수십~수백 개, 엣지당 2쿼리.
- **권장**: 엣지쌍을 정규화해 모은 뒤 `Q(symbol_a__in=...) & Q(symbol_b__in=...)`로 일괄 조회 → 메모리 매칭.
- **난이도**: 중간

#### [HIGH] 1-6. `services/serverless/views_admin.py:502-531` — `AdminNewsCategoryView`
```python
categories = NewsCollectionCategory.objects.all()  # 페이지네이션 없음
for cat in categories:
    symbols = cat.resolve_symbols()  # 카테고리당 SP500Constituent 필터 쿼리
```
- **문제**: 카테고리 전건 로드 + 각 `resolve_symbols()`가 내부 DB 조회. 카테고리 수만큼 N+1.
- **권장**: 페이지네이션 추가 + `resolve_symbols` 결과 캐싱 또는 sector→symbols 일괄 prefetch.
- **난이도**: 중간

#### [HIGH] 1-7. `packages/shared/users/views.py:945-949` — `WatchlistBulkAddView`
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol.upper())  # 심볼당 +1
    if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists(): ...
```
- **문제**: 대량 심볼 추가 시 심볼당 Stock 조회 N+1.
- **권장**: `stocks = {s.symbol: s for s in Stock.objects.filter(symbol__in=upper_symbols)}` 사전 dict화.
- **난이도**: 중간

#### [MED] 1-8. `services/validation/api/views.py:148-166 / 261-265 / 339-353`
루프 내 `MetricDefinition.objects.filter(pk=mc).first()` 반복(`_build_category`, `_build_metric`, `ValidationSummaryView`) 및 스냅샷당 `PeerMetricBenchmark` 조회.
- **권장**: `MetricDefinition.objects.in_bulk(metric_codes)` 한 번, peer benchmark도 `(symbol, metric_code)` 범위 일괄 로드.
- **난이도**: 쉬움~중간

#### [MED] 1-9. `services/rag_analysis/views.py:306-412` — `_get_data_snapshot`
`data_type`별로 Stock / DailyPrice / IncomeStatement / BalanceSheet를 각각 `stock__symbol=symbol`로 재조회. 반복 호출 시 Stock 중복 조회.
- **권장**: 상위에서 Stock 1회 로드 후 인자로 전달, 가격/재무는 `select_related("stock")`.
- **난이도**: 중간

#### [MED] 1-10. `packages/shared/users/views.py:365-376, 419-435` — Portfolio 집계
```python
for portfolio in portfolios:
    total_value += portfolio.total_value   # 모델 property, 객체당 연산
```
- **문제**: `select_related("stock")`은 적용되어 FK는 안전하나, 합산을 Python 루프로 수행.
- **권장**: `aggregate(Sum(F("quantity") * F("stock__real_time_price")))`로 DB 단일 연산.
- **난이도**: 중간

#### [LOW] 1-11. `packages/shared/users/views.py:217-252` — favorite `in qs.all()`
`if stock in user.favorite_stock.all():` → 전체 M2M 로드 후 메모리 검사. `.filter(id=stock.id).exists()`로 대체.

#### [LOW] 1-12. `services/validation/api/views.py:194-211` — `peers.count()`
`leader` 판정 시 `peers.count()`가 별도 COUNT 쿼리. 이미 평가하는 queryset이면 `len(list(peers))` 또는 `exists()`로 통합.

#### [LOW] 1-13. `services/serverless/views_admin.py:758-792` — 중복 aggregate
`SP500Constituent.objects.filter(is_active=True)` 동일 필터를 sector/sub_sector용으로 2회 실행. 1회 조회 후 메모리 그룹핑 또는 캐싱.

#### [LOW] 1-14. `apps/chain_sight/api/views.py:174-193` — `union()[:10]` 후 재순회
`values_list("symbol_a", "symbol_b")`로 직접 추출하면 객체 재접근 불필요.

> **참고 (이슈 아님)**: `views_eod.py:81`은 `select_related("stock")` 적용, `apps/market_pulse/views.py`·`services/sec_pipeline/views.py`는 서비스 위임/단순 상태 조회로 뷰 레벨 N+1 없음. `packages/shared/stocks/views.py:108` `StockListAPIView`는 `StockListPagination`(기본 50, 최대 200) 적용됨.

---

### 2. 인덱스 누락

> 본 섹션은 모델 정의의 `db_index`/`Meta.indexes`와 동일 앱 필터 패턴의 정적 분석 기반입니다. 대부분의 복합 인덱스가 흔한 접근 경로를 이미 커버하므로, 아래는 **단독 필드 필터 시의 이론적 갭** 위주입니다. 적용 전 실제 쿼리 플랜(`EXPLAIN`) 확인을 권장합니다. 모두 migration 필요(난이도 쉬움).

| # | 위치 | 필드 | 심각도 | 비고 |
|---|---|---|---|---|
| 2-1 | `services/serverless/models.py:19` | `MarketMover.mover_type` | MED | `(date, mover_type)` 복합 인덱스 존재 → date 동반 조회는 커버됨. mover_type 단독 필터만 갭 |
| 2-2 | `services/news/models.py:56` | `NewsArticle.category` | MED | `(-published_at, category)` 복합만 존재. category 단독 필터 시 미활용 |
| 2-3 | `packages/shared/stocks/models.py:238` | `DailyPrice.currency` | MED | 대량 테이블이나 currency 필터 빈도는 낮음 |
| 2-4 | `services/sec_pipeline/models.py:31` | `RawDocumentStore.filing_date` | MED | `(symbol, -filing_date)` 복합만 존재. 날짜 단독 조회 갭 |
| 2-5 | `services/news/models.py:55` | `NewsArticle.language` | LOW | 다국어 필터 빈도 낮음 |
| 2-6 | `services/serverless/models.py:682` | `ScreenerAlert.is_active` | LOW | 보통 `(user, is_active)` 복합으로 조회 |
| 2-7 | `services/serverless/models.py:761` | `AlertHistory.status` | LOW | 보조 필터 |
| 2-8 | `services/sec_pipeline/models.py:107` | `SupplyChainEvidence.confidence_grade` | LOW | 분석 단계 선택 필터 |
| 2-9 | `services/_dormant/graph_analysis/models.py:110` | `CorrelationEdge.correlation_change` | LOW | 휴면 서비스 |

**정상 확인(인덱스 충분)**: `Stock`(sector/industry/market_cap/real_time_price/symbol), `StockKeyword.status`(이미 `db_index=True`), `EODSignal`, `DailyPrice`(stock·date·복합), 재무제표 3종(stock·fiscal_year 복합).

---

### 3. 느린 Serializer (SerializerMethod 추가 쿼리)

#### [HIGH] 3-1. `services/serverless/serializers.py:299-316` — `ScreenerPresetSerializer.get_owner_email / get_is_owner`
`obj.user.email`, `obj.user == request.user`에서 FK lazy load. list 직렬화 시 프리셋당 User 조회 N+1.
- **권장**: 뷰 queryset에 `select_related("user")`. **난이도**: 쉬움

#### [HIGH] 3-2. `services/serverless/serializers.py:574-578` — `ScreenerAlertSerializer.get_preset_name`
`obj.preset.icon/name` FK lazy load → 알림당 ScreenerPreset 조회.
- **권장**: `select_related("preset")`. **난이도**: 쉬움

#### [HIGH] 3-3. `services/serverless/serializers.py:738-742` — `InvestmentThesisSerializer.get_is_owner`
`obj.user` 비교에서 FK lazy load.
- **권장**: `select_related("user")`. **난이도**: 쉬움

#### [HIGH] 3-4. `services/news/api/serializers.py:50, 73` — 중첩 `entities`(many=True)
list용 `NewsArticleListSerializer.entities`는 베이스 queryset `prefetch_related("entities")`로 커버되나, **prefetch를 우회하는 커스텀 액션**(1-1 `stock_news`, 1-2 `trending`)에서 N+1. detail용 `NewsArticleDetailSerializer.entities → highlights`(`serializers.py:21`)는 베이스가 `entities`만 prefetch하고 `entities__highlights`는 미포함 → 단건이라 영향은 제한적(MED 성격).
- **권장**: 커스텀 액션에 `prefetch_related("entities")` 재적용, detail은 `prefetch_related("entities__highlights")`.
- **난이도**: 중간

#### [MED] 3-5. `packages/shared/stocks/serializers.py` `OverviewTabSerializer.get_dynamic_layers` (대략 251~351)
뷰(`views.py:546`)는 `select_related("overview_ko")`만 적용. chainsight OneToOne 5종(`validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`)과 ManyToOne `category_signals.all()`은 미적용 → 단건 detail 호출당 ~6 추가 쿼리. (`get_korean_overview`는 이미 커버됨, list N+1 아님)
- **권장**: `select_related`에 5종 OneToOne 추가, `category_signals`는 `prefetch_related` (코드에 TODO로 명시되어 있음).
- **난이도**: 쉬움

#### [MED] 3-6. `services/rag_analysis/serializers.py:59` — `DataBasketSerializer.get_can_add_item` ✅검증
`models.py:34` `self.items.count()` 호출. list 뷰가 `prefetch_related("items")` 해도 `.count()`는 prefetch 캐시를 쓰지 않고 매번 COUNT 발생 → 바구니당 N+1. (`get_max_units`는 상수 반환, 안전)
- **권장**: 뷰에서 `annotate(items_count=Count("items"))` 후 해당 값 사용, 또는 serializer가 `len(obj.items.all())`로 prefetch 캐시 활용.
- **난이도**: 중간

#### [MED] 3-7. `services/serverless/serializers.py:125-144, 221-226` — display 메서드 내 서비스 인스턴스화
`get_sector_alpha_display` 등에서 매 객체마다 `IndicatorCalculator()` / `MarketBreadthService()` 생성(내부 DB 조회 가능성). many=True 시 객체당 반복.
- **권장**: 서비스 싱글톤화 또는 순수 함수/lookup dict로 전환.
- **난이도**: 중간

#### [LOW] 3-8. `services/serverless/serializers.py:450` — `SectorPerformanceSerializer.get_name_ko`
객체당 `SectorHeatmapService` import 반복(dict lookup 자체는 O(1)). 모듈 레벨 상수로 이동.

> **제외(오탐)**: `services/serverless/serializers.py:580` `ScreenerAlertSerializer.get_can_trigger` — `models.py:722` 본문이 `last_triggered_at + cooldown` datetime 비교만, DB 쿼리 없음. **안전**(순수 연산): `PortfolioDetailSerializer.get_portfolio_weight`(context 값 사용), `AlertHistoryListSerializer.get_is_read`(속성 접근).

#### [참고] 3-9. `WatchListStockSerializer.get_latest_price`(`serializers.py:451`) / `get_chart_data`(`:458`)
객체당 `DailyPrice.objects.filter(stock=obj)` 조회 → many=True 시 N+1 패턴. 단, 코드베이스 내 `.py` 호출처를 찾지 못함(미사용/동적 호출 의심) → **신뢰도 낮음, 실사용 확인 필요**. 사용 중이라면 HIGH.

---

### 4. 페이지네이션 누락

전건/무제한 반환 가능 list 엔드포인트. 모두 **난이도 쉬움**(DRF `pagination_class` 또는 limit/offset 추가).

| # | 위치 | 엔드포인트 | 심각도 | 비고 |
|---|---|---|---|---|
| 4-1 | `services/news/api/views.py:116` | `stock_news` | MED | 날짜 범위 내 전건 + entities N+1 (1-1과 동일) |
| 4-2 | `services/news/api/views.py:309` | `market` | MED | `[:limit]`만, offset 불가 → 페이지 이동 불가 |
| 4-3 | `services/serverless/views_admin.py:502` | `AdminNewsCategoryView` | MED | 카테고리 전건 (1-6과 동일) |
| 4-4 | `services/rag_analysis/views.py:50` | `DataBasketListCreateView` | MED | 사용자 바구니 전건 + items 중첩 |
| 4-5 | `services/rag_analysis/views.py:427` | `AnalysisSessionListCreateView` | MED | 세션 전건 + messages 중첩 → 데이터 급증 |
| 4-6 | `packages/shared/users/views.py:1045` | `UserInterestListView` | MED | 관심사 전건 |

> `services/news/api/views.py:443` `all_news`는 수동 offset/limit 슬라이싱 적용됨(개선 여지: `count()` 별도 쿼리). `packages/shared/users/views.py:92` 전체 User 목록은 관리용으로 보이나 페이지네이션 부재 — 노출 시 MED.

---

## 부록: 권장 적용 순서

1. **즉효·저위험 (select_related/prefetch 추가)**: 3-1·3-2·3-3(serverless serializer FK), 3-5(OverviewTab select_related 확장), 1-1(news stock_news prefetch 재적용)
2. **일괄조회 리팩토링 (루프→in_bulk/`__in`)**: 1-4·1-5·1-6·1-7·1-8·1-3
3. **페이지네이션 일괄 도입**: 4-1~4-6
4. **인덱스 migration**: 2-1~2-4 (MED) — 적용 전 `EXPLAIN`으로 복합 인덱스 커버 여부 재확인
5. **구조 개선 (서비스 싱글톤/aggregate)**: 3-7, 1-10, 3-6

*본 보고서는 정적 분석 기반이며 실제 쿼리 수는 데이터량·요청 파라미터에 따라 달라집니다. 적용 시 `django-debug-toolbar` 또는 `CaptureQueriesContext`로 before/after 쿼리 수 측정을 권장합니다.*
