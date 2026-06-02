# API 성능 감사 보고서

- **작성일**: 2026-06-02
- **범위**: 뷰 17개 (N+1 / 느린 Serializer / 페이지네이션) + 모델 7개 (인덱스 누락)
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음). 병렬 3분할 정독 후 종합.
- **모노레포 경로 매핑**: 지시서의 `stocks/` → `packages/shared/stocks/`, `users/` → `packages/shared/users/`, `news/api/` → `services/news/api/`, `macro/` → `apps/market_pulse/`, `rag_analysis/`·`serverless/`·`validation/`·`sec_pipeline/` → `services/*`, `chainsight/` → `apps/chain_sight/`, `graph_analysis/` → `services/_dormant/graph_analysis/`.

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 / 느린 Serializer | 페이지네이션 누락 | 인덱스 누락 | 합계 |
|--------|:---:|:---:|:---:|:---:|
| **HIGH** | 3 | (전역, 아래 별도) | 0 | 3 |
| **MED**  | 8 | 포함 | 0 | 8 |
| **LOW**  | 6 | 포함 | 0 (추측 배제) | 6 |
| **합계** | **17** | — | **0** | **17** |

### 전체를 관통하는 1건 (HIGH, 구조적)
- **전역 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 미설정** (`config/settings.py:355` `REST_FRAMEWORK`).
  → list 엔드포인트가 `pagination_class`를 명시하지 않으면 **전체 무제한 반환**. 아래 모든 "페이지네이션 누락" 이슈의 근본 원인. 전역 기본값 도입이 가장 비용 대비 효과 높은 단일 수정.

### 핵심 결론
1. **stocks 뷰 9개에는 HIGH 없음.** 대부분의 목록 엔드포인트가 외부 FMP 서비스 기반(DB ORM 미사용)이거나 명시적 슬라이스(`[:10]`/`[:20]`/`[:50]`/`[:7]`)로 보호됨. `EODSignalDetailView`는 `select_related("stock")`로 N+1을 모범적으로 차단.
2. **HIGH 3건은 모두 중첩 Serializer / 다단계 루프 N+1** — `rag_analysis` 세션 목록, `validation` 지표/리더 비교에 집중. 사용자 대면 화면에서 직접 호출되므로 우선 수정 대상.
3. **인덱스는 이미 매우 우수.** 7개 모델 모두 대용량 테이블(가격/뉴스/시그널/재무)에 적절한 단일·복합 인덱스 보유. 복합 인덱스 선행 컬럼 커버 규칙 + 실제 쿼리 대조 결과 **단정 가능한 누락 0건** (추측 기반 권고는 의도적으로 배제, 실측 EXPLAIN 권장).

---

## 상세

### A. HIGH — 중첩 Serializer / 다단계 루프 N+1

#### A-1. `services/rag_analysis/views.py:429-432` — AnalysisSession 목록: 중첩 basket Serializer 다단계 N+1 + 무제한
```python
sessions = AnalysisSession.objects.filter(...).prefetch_related("messages")
serializer = AnalysisSessionSerializer(sessions, many=True)
```
- `AnalysisSessionSerializer`(`serializers.py:86-87`)가 `basket = DataBasketSerializer(read_only=True)`를 중첩. `basket`은 `select_related`/`prefetch` 안 됨 → 세션마다 basket FK 조회 1회 + `DataBasketSerializer`의 `items`(쿼리) + `items_count`/`can_add_item`/`current_units`(COUNT/AGGREGATE 3~4회) 발생. 세션 N개면 **N×(5~6) 쿼리**. 페이지네이션도 없음.
- **권장**: `.select_related("basket").prefetch_related("messages", "basket__items")` + basket aggregate를 `.annotate()`로 끌어올림 + `pagination_class` 지정.
- **심각도 HIGH · 난이도 중간**

#### A-2. `services/validation/api/views.py:276-368` — `ValidationMetricsView._build_metric`: 지표×history×peer 중첩 N+1
- `category="all"`이면 전 카테고리(7개) × 카테고리별 지표 루프. 지표마다 `MetricDefinition.filter(pk).first()`(L262), `CompanyMetricSnapshot.filter().first()`(L278, 경우에 따라 L298 재조회), `CompanyBenchmarkDelta.filter().first()`(L316), `CompanyMetricSnapshot.filter()[:5]`(L339), 그리고 **history 5년 루프 안에서 `PeerMetricBenchmark.objects.filter().first()`(L349)** → 지표당 6+5 쿼리 중첩. 전체로 수백 쿼리 가능.
- **권장**: `MetricDefinition.objects.in_bulk()` + snapshot/delta/peer를 `symbol+fiscal_year+metric_code__in` 한 번에 bulk fetch 후 메모리 매핑.
- **심각도 HIGH · 난이도 높음**

#### A-3. `services/validation/api/views.py:451-475` — `LeaderComparisonView`: 전 지표 × 3쿼리 N+1
- `all_metrics`(전 카테고리 전 지표) 루프 안에서 지표당 `MetricDefinition.filter().first()` + `CompanyMetricSnapshot.filter()` ×2(company, leader) = **지표당 3쿼리**.
- **권장**: company+leader를 동일 fiscal_year, `metric_code__in`으로 bulk fetch 후 dict 매핑.
- **심각도 HIGH · 난이도 높음**

---

### B. MED — N+1 / 느린 Serializer / 페이지네이션 누락

#### B-1. `packages/shared/users/views.py:93-94` — User 전체 목록: 무제한 + favorite_stock N+1
```python
users = User.objects.all()
serializer = UserSerializer(users, many=True)
```
- `UserSerializer.favorite_stock = StockListingField(many=True)` → 사용자마다 M2M 역참조 쿼리. 페이지네이션 없음(관리자 전용이라 빈도는 낮음).
- **권장**: `pagination_class` + `.prefetch_related("favorite_stock")`. · **난이도 쉬움**

#### B-2. `packages/shared/users/views.py:641` — WatchlistListCreateView: `stock_count` COUNT N+1
- `WatchlistSerializer.stock_count = ReadOnlyField()` → 모델 property `self.items.count()`(`models.py:212`)가 Watchlist마다 COUNT 실행(페이지당 최대 100건).
- **권장**: queryset `.annotate(stock_count=Count("items"))` 후 serializer가 annotate 사용. · **난이도 중간**

#### B-3. `services/rag_analysis/views.py:52-53` — DataBasket 목록: count/aggregate N+1
- `DataBasketSerializer`의 `items_count`(`items.count()`), `can_add_item`(`items.count()`), `current_units`(`items.aggregate(Sum)`), `remaining_units`(재호출) → basket당 COUNT/AGGREGATE 3~4회. `prefetch_related("items")`는 nested 직렬화만 커버하고 `.count()`/`.aggregate()`는 새 쿼리 발생.
- **권장**: `.annotate(items_count=Count("items"), current_units_agg=Sum("items__data_units"))` + 페이지네이션. · **난이도 중간**

#### B-4. `services/news/api/views.py:370-391` — trending action: 기사 entities N+1
- 트렌딩 종목(최대 `limit`, 기본 10)마다 `NewsArticle.objects.filter(entities__symbol=...)` + `NewsArticleListSerializer(many=True)` 직렬화(entities prefetch 없음). 5분 캐시로 완화됨.
- **권장**: 기사 쿼리에 `.prefetch_related("entities")`. · **난이도 중간**

#### B-5. `services/news/api/views.py:117-130` — stock_news action: entities prefetch 미상속
- ViewSet `queryset`엔 `.prefetch_related("entities")`가 있으나 이 action은 별도 qs(L118)를 새로 생성하여 prefetch 미상속 → `NewsArticleListSerializer.entities` 기사별 N+1. action 자체 페이지네이션도 없음(기간 내 전체, days 기본 7). 10분 캐시.
- **권장**: `articles.prefetch_related("entities")` 추가. · **난이도 쉬움**

#### B-6. `services/serverless/views_admin.py:505-530` — AdminNewsCategoryView: `resolve_symbols()` 루프 N+1
```python
for cat in categories:
    symbols = cat.resolve_symbols()
```
- 카테고리마다 `resolve_symbols()`(sector/sub_sector는 `SP500Constituent` 등 DB 조회)가 호출 → 카테고리당 1+ 쿼리. 페이지네이션 없음(`all()`). 카테고리 수가 보통 수십 개라 영향 제한적, admin 전용.
- **권장**: bulk resolve 또는 결과 캐싱. · **난이도 중간**

#### B-7. `apps/chain_sight/api/views.py:78-91` — ChainSightGraphView: edge별 2쿼리 N+1 (캐시 없음)
```python
for edge in result.get("edges", []):
    CoMentionEdge.objects.filter(...).first()
    PriceCoMovement.objects.filter(...).first()
```
- edge마다 PostgreSQL 2쿼리. depth=3이면 edge 수가 커짐. 이 뷰는 캐시 없이 매 요청 실행.
- **권장**: edge 쌍 목록을 모아 `CoMentionEdge.objects.filter(symbol_a__in, symbol_b__in)` bulk 조회 후 dict 매핑. · **난이도 중간**

#### B-8. `apps/chain_sight/api/views.py:809-920` — SignalFeedView: 시드 페어별 Neo4j shortestPath 루프
- `for s1, s2 in pairs:` 안에서 Neo4j `shortestPath` 쿼리 1회씩. `pairs[:page_size*3]`(기본 15) 상한 + 1시간 캐시로 완화되나 외부 그래프 왕복 다수. (PostgreSQL N+1과 성격 다름)
- **권장**: 배치 Cypher 쿼리로 통합. · **난이도 높음**

#### (참고) `packages/shared/stocks/views.py:932` — StockCompleteDataAPIView: Overview 관계 lookup 6+개 무캐시
- `OverviewTabSerializer(stock).data`가 `get_korean_overview`(역참조 1) + `get_dynamic_layers`(reverse-FK 1 + OneToOne 5) lookup 수행. 단일 종목이라 고정 비용(N+1 아님)이나 `select_related` 미적용 + 캐시 없음.
- **권장**: `Stock.objects.select_related("overview_ko","sensitivity_profile","growth_stage","capital_dna","narrative_tag","validation_news_summary").get(...)`. · **MED · 난이도 쉬움**
- ⚠️ `OverviewTabSerializer.get_dynamic_layers`(`serializers.py:241-353`)는 종목당 OneToOne 5 + reverse-FK 1을 수행하는 무거운 MethodField. 현재 단일 종목 직렬화에만 쓰여 안전하나 **향후 `many=True` 목록에 적용되면 즉시 HIGH N+1**.

#### (참고) `packages/shared/stocks/views_indicators.py:375` + `:361` — IndicatorComparisonView: 루프 내 Stock 단건 조회 N+1 + 입력 상한 없음
- `for symbol in symbols: Stock.objects.get(symbol=symbol)`(L375) + symbol마다 DailyPrice 쿼리(L380). `symbols` 입력 개수 상한 검증 없음(L361) → 대량 시 HIGH로 격상.
- **권장**: `{s.symbol: s for s in Stock.objects.filter(symbol__in=...)}` 사전 조회 + 입력 개수 상한(예: 20~50). · **MED · 난이도 중간**

---

### C. LOW

| # | 파일:라인 | 내용 | 난이도 |
|---|-----------|------|--------|
| C-1 | `packages/shared/stocks/views.py:317,323` | `StockChartDataAPIView`: 동일 lazy QuerySet `.count()` 2회 호출(캐시 미스 시 COUNT 중복). `len()` 재사용 권장 | 쉬움 |
| C-2 | `packages/shared/stocks/views_mvp.py:221` | `SectorListView`: `.distinct()` 무제한 반환(페이지네이션 누락). 섹터 카디널리티 고정(~11) | 쉬움 |
| C-3 | `packages/shared/users/views.py:419,429` | `PortfolioDetailTableView`: 페이지네이션 없음. `select_related("stock")` 적용되어 N+1은 아님. 보유 종목 소수 | 중간 |
| C-4 | `packages/shared/users/views.py:1046-1059` | `UserInterestListCreateView`: 페이지네이션 없음. 사용자별 소규모, 관계 접근 없음 | 쉬움 |
| C-5 | `services/news/api/views.py:309-317` | `market` action: `[:limit]` 제한 있으나 entities prefetch 누락. 캐시 있음 | 쉬움 |
| C-6 | `services/validation/api/views.py:148-166` | `ValidationSummaryView`: rank_metrics 루프 내 delta/definition 조회(고정 5개 → 10쿼리) | 중간 |

추가 LOW(영향 미미): `rag_analysis/views.py:463-465`(단건 basket prefetch 누락), `:496-497`(SessionMessages 페이지네이션 없음, 세션당 소규모).

---

### D. 인덱스 누락 (모델 7개)

**결론: HIGH/MED 급 명확한 누락 0건.** 복합 인덱스 선행 컬럼 커버 규칙 + 실제 `filter`/`order_by` 위치 대조 결과, 단정 가능한 누락 없음. 추측 기반 권고는 추측 금지 원칙에 따라 배제.

기존 인덱스가 실사용 쿼리를 커버하는 대표 사례:
- `SignalAccuracy.filter(signal_date__lte=)` (`eod_pipeline.py:437`) → `Index(signal_date, signal_tag)` 선행 커버
- `InstitutionalHolding.filter(report_date=)` (`institutional_holdings_service.py:404`) → `Index(report_date, institution_cik)` 선행 커버
- `StockNews.filter(symbol=, published_at__date__gte=)` (`eod_news_enricher.py:107-160`) → `Index(symbol, -published_at)` 커버
- `NewsArticle.filter(published_at__gte=, importance_score__isnull=)` → `Index(importance_score, -published_at)` 커버
- `SupplyChainEvidence.filter(neo4j_dirty=True, ...)` (`tasks.py:429`) → `Index(neo4j_dirty)` 커버
- `MarketMover.filter(date=, mover_type=)` → `Index(date, mover_type)` 커버
- `rag_analysis`의 `AnalysisSession`/`AnalysisMessage`는 `Meta.indexes`가 없으나 실사용 필터가 모두 FK(`user`, `session`) 기반 → FK 자동 인덱스로 커버.

**근거 약한 LOW 후보(보류)**: `serverless/models.py:148` `VolatilityBaseline.date` 단독 인덱스 없음(`unique_together(symbol,date)` 선행이 symbol). 단 `date` 단독 필터 사용 근거를 코드에서 찾지 못함 → 보류.

> 정밀 검증이 필요하면 운영 DB `pg_stat_user_tables`의 `seq_scan` 상위 테이블을 지목해 EXPLAIN ANALYZE 기반으로 재분석 권장.

---

## 우선순위 권장 (수정 시)

1. **전역 `DEFAULT_PAGINATION_CLASS` 도입** (`config/settings.py:355`) — 모든 페이지네이션 누락의 근본 해결, 난이도 쉬움, 영향 광범위.
2. **A-1 rag_analysis 세션 목록** — 사용자 대면 + 다단계 N+1, `select_related`/`prefetch`/`annotate`로 즉시 개선 가능.
3. **A-2 / A-3 validation 지표·리더 비교** — bulk fetch 리팩토링(난이도 높음), `category=all` 경로 쿼리 수백 건 → 수 건.
4. **B-7 ChainSightGraphView** — 캐시 없는 edge별 N+1, bulk 조회로 개선.

---

*본 보고서는 정적 분석 기반이며 실제 쿼리 수는 데이터 분포·캐시 적중률에 따라 달라질 수 있습니다. HIGH 항목은 `django-debug-toolbar` 또는 `assertNumQueries`로 실측 후 수정 권장.*
