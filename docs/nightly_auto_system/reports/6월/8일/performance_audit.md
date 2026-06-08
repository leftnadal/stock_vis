# API 성능 감사 보고서

- **생성일**: 2026-06-08
- **모드**: 읽기 전용 (코드 미수정)
- **범위**: 뷰 17개 + 모델 7개 + Serializer 11개
- **검사 항목**: N+1 쿼리 / 인덱스 누락 / 느린 Serializer / 페이지네이션 누락
- **구조 참고**: 실제 코드는 모노레포(`packages/shared/*`, `apps/*`, `services/*`) 구조. 지시서의 `stocks/`, `macro/`, `chainsight/` 등은 각각 `packages/shared/stocks/`, `apps/market_pulse/`, `apps/chain_sight/`로 매핑됨.

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 핵심 패턴 |
|--------|------|----------|
| **HIGH** | **8** | 루프 내 행별 ORM 쿼리(Neo4j/지표 결과 순회) + 리스트 Serializer N+1 |
| **MED** | **13** | 단건 6쿼리(OverviewTab), `created_at`/`extracted_at` 인덱스 누락, M2M/역참조 prefetch 누락 |
| **LOW** | **6** | 고정 소수 루프, count 중복 호출, 소규모 배치 테이블 |

### 카테고리별 분포

| 카테고리 | HIGH | MED | LOW |
|----------|------|-----|-----|
| N+1 쿼리 (뷰) | 3 | 4 | 1 |
| 느린 Serializer | 5 | 6 | 2 |
| 인덱스 누락 | 0 | 4 | 1 |
| 페이지네이션 누락 | 0 | 3 | 0 |

> **공통 안티패턴 1**: HIGH 8건 중 6건이 **"외부 결과(Neo4j edge / 지표 코드 / Watchlist 종목 / 뉴스 article)를 루프 돌며 행마다 Postgres 쿼리"**. 해법은 동일 — 루프 진입 전 `__in`/`Q`/`Prefetch`로 일괄 로드 후 dict 매핑.
> **공통 안티패턴 2**: 인덱스 누락 5건 전부 **`auto_now_add` DateTimeField를 배치/모니터링이 `__gte=시간윈도우`로 단독 필터**하는데 기존 복합 인덱스의 선두 컬럼이 달라 prefix 미활용.
> **거짓양성 배제**: screener/fundamentals/exchange/market-movers/search 뷰·Serializer는 ORM이 아니라 **FMP 외부 API dict 리스트**를 직렬화 → DB N+1 대상 아님.

---

## 우선순위 종합 (Top 12, 가성비 순)

| 순위 | 위치 | 이슈 | 심각도 | 난이도 |
|------|------|------|--------|--------|
| 1 | news `api/views.py` 기본 queryset / Serializer | `NewsArticleListSerializer.entities` 리스트 N+1 | HIGH | 쉬움 |
| 2 | news `api/serializers.py:73,21` | `entities__highlights` 2단 중첩 N+1 | HIGH | 쉬움 |
| 3 | stocks `serializers.py:451-460` | Watchlist 종목당 `DailyPrice` 2쿼리(+`get_chart_data` return 누락 버그) | HIGH | 중간 |
| 4 | users `serializers.py:346,284` | `WatchlistDetail.items` Stock N+1 + `stock_count` 행별 COUNT | HIGH | 쉬움 |
| 5 | validation `api/views.py:459-484` | `LeaderComparison` 지표 루프 ×3쿼리, 캐시 없음 | HIGH | 중간 |
| 6 | validation `api/views.py:339-368` | `Metrics` history 중첩 N+1(`category=all`), 캐시 없음 | HIGH | 중간 |
| 7 | chain_sight `api/views.py:78-91` | Graph edges 루프 ×2쿼리, 캐시 없음 | HIGH | 중간 |
| 8 | rag_analysis `views.py:429-433` + `serializers.py:86` | Session list `basket`/`basket__items` 미prefetch | HIGH | 쉬움 |
| 9 | stocks `views.py:545` 외 3진입점 + `serializers.py:241` | `OverviewTab` dynamic_layers 단건 6쿼리 | MED | 쉬움 |
| 10 | news `models.py:138` | `NewsArticle.created_at` 인덱스 누락 | MED | 쉬움 |
| 11 | sec_pipeline `models.py:116,47` | `extracted_at`/`collected_at` 인덱스 누락 | MED | 쉬움 |
| 12 | rag_analysis `models.py:288` | `UsageLog.created_at` 인덱스 누락 | MED | 쉬움 |

> **재확인(미해결 잔존)**: 순위 11~12는 이전 감사(`docs/nightly_auto_system/reports/5월/31일`, `6월/6일`)에도 기록된 이슈가 여전히 미해결.

---

# 상세

## 1. N+1 쿼리 (뷰 레벨)

### [HIGH] 1-1. `validation/api/views.py:459-484` — `LeaderComparisonView.get` 지표 루프 ×3쿼리
```python
for cat, mc in all_metrics:      # 전체 카테고리×지표 (~30개)
    md = MetricDefinition.objects.filter(pk=mc).first()
    company_snap = CompanyMetricSnapshot.objects.filter(...).first()
    leader_snap = CompanyMetricSnapshot.objects.filter(...).first()
```
- **문제**: 전체 지표 수만큼 × 3쿼리. 지표 30개면 90쿼리. **캐시 없음** → 매 요청 노출.
- **권장**: company/leader snapshot을 `metric_code_id__in=[...]`로 각각 1쿼리 일괄 로드 후 dict 매핑. `MetricDefinition`도 `pk__in` 일괄 로드.

### [HIGH] 1-2. `validation/api/views.py:339-368` — `ValidationMetricsView._build_metric` history 중첩 N+1
```python
snaps = CompanyMetricSnapshot.objects.filter(...).order_by("fiscal_year")[:5]
for s in snaps:
    peer_bench = PeerMetricBenchmark.objects.filter(
        symbol=stock, fiscal_year=s.fiscal_year, metric_code=md).first()
```
- **문제**: 연도(최대 5)마다 `PeerMetricBenchmark` 1쿼리. `_build_metric`은 `_build_category`에서 metric별 반복 → `category=all`이면 카테고리 7 × metric 다수 × 연도 5 = **수백 쿼리**. 캐시 없음.
- **권장**: `fiscal_year__in=[...]` 한 번에 조회 후 dict 매핑. `_build_category` 진입 전 stock의 모든 snapshot/benchmark 일괄 로드.

### [HIGH] 1-3. `apps/chain_sight/api/views.py:78-91` — `ChainSightGraphView.get` edges 루프 ×2쿼리
```python
for edge in result.get("edges", []):
    cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
    pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
```
- **문제**: Neo4j edge마다 Postgres 2쿼리. depth=3이면 edge 수백 개 → edge수×2. 캐시 없음.
- **권장**: 모든 (a,b) 쌍을 모아 `Q` OR 또는 `__in` tuple 조건으로 `CoMentionEdge`/`PriceCoMovement`를 각 1쿼리 일괄 로드 후 dict 매핑.
- **모범 대조**: 같은 파일의 `SectorGraphView`(463), `NeighborGraphView`(619)는 `Stock.objects.filter(symbol__in=tickers)` bulk 조회 + 캐시 적용 → 정상.

### [MED] 1-4. `services/news/api/views.py:369-391` — `trending` 종목 루프 + entities N+1
```python
for item in trending_data:                       # 최대 limit(기본 10)
    recent_articles = NewsArticle.objects.filter(entities__symbol=symbol, ...)\
                        .distinct().order_by("-published_at")[:3]
    NewsArticleListSerializer(recent_articles, many=True).data
```
- **문제**: 종목마다 기사 쿼리 1회 + `entities` prefetch 없이 직렬화. 캐시 5분 + limit으로 완충, 미스 시 부담.
- **권장**: `recent_articles`에 `.prefetch_related("entities")`. 가능하면 전 symbol 기사 일괄 조회 후 in-메모리 그룹핑.

### [MED] 1-5. `services/serverless/views_admin.py:505-530` — `AdminNewsCategoryView.get` `resolve_symbols()` 루프
```python
categories = NewsCollectionCategory.objects.all()
for cat in categories:
    symbols = cat.resolve_symbols()   # sector/sub_sector 시 SP500Constituent 조회 가능
```
- **문제**: 카테고리 N개마다 `resolve_symbols()` 내부 DB 쿼리 ≥1. 페이지네이션 없음. 관리자 전용 + 카테고리 수 제한적.
- **권장**: `resolve_symbols` 내부 쿼리 배치화/캐시. 최소 페이지네이션.

### [MED] 1-6. `packages/shared/stocks/views_indicators.py:371-384` — `IndicatorComparisonView` 종목당 2쿼리
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)            # 종목당 1쿼리
    prices = DailyPrice.objects.filter(stock=stock)...  # 종목당 1쿼리
```
- **문제**: symbols 수만큼 2N 쿼리. symbols 상한 없음 → 대량 입력 시 증폭.
- **권장**: `Stock.objects.filter(symbol__in=symbols)` 일괄 조회 후 dict 매핑 + symbols 길이 상한(예: 10~20).

### [MED] 1-7. `packages/shared/users/views.py:92-95` — `Users.get` 페이지네이션 + M2M prefetch 누락
```python
users = User.objects.all()
serializer = UserSerializer(users, many=True)   # favorite_stock M2M → user당 1쿼리
```
- **문제**: 전체 반환(페이지네이션 없음) + `favorite_stock` M2M N+1. 관리자 전용.
- **권장**: `User.objects.prefetch_related("favorite_stock")` + DRF pagination.

### [LOW] 1-8. `packages/shared/stocks/views.py:317,323` — `StockChartDataAPIView` count() 중복
```python
if price_data.count() > 0:                       # 쿼리 1
    response_data = {..., "count": price_data.count(), ...}  # 쿼리 2
```
- **권장**: `len(serializer.data)` 재사용 또는 count 1회 캐싱.

> **이슈 없음(서비스 위임/외부 API)**: `apps/market_pulse/views.py`(macro), `services/sec_pipeline/views.py`, `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`, `views_exchange.py`, `views_search.py`, `views_eod.py`(이미 `select_related("stock")` 적용).

---

## 2. 인덱스 누락

> 5건 전부 동일 유형: **`auto_now_add` DateTimeField를 배치/모니터링이 `__gte=시간윈도우`로 단독 필터**하는데, 기존 복합 인덱스의 선두 컬럼이 달라 prefix 미활용. 모두 사용자 실시간 경로가 아닌 운영/배치 경로 → HIGH 없음. 모두 `db_index=True` 또는 단일 `models.Index` 추가로 해결(난이도 쉬움 + migration 1건).

### [MED] 2-1. `services/news/models.py:138` — `NewsArticle.created_at`
- **근거(filter)**: `daily_report.py:174~230`(일일 배치), `admin_status_service.py:114,599,600`, `news/tasks.py:1280` 모두 `created_at__gte=cutoff`.
- **문제**: `NewsArticle`는 수집마다 빠르게 누적되는 대량 테이블. 기존 복합 인덱스 5개는 선두가 `published_at`/`source`/`sentiment_score`/`importance_score`/`llm_analyzed` → `created_at` 단독 필터는 full scan.
- **권장**: `created_at = DateTimeField(auto_now_add=True, db_index=True)`. (정밀 최적화 시 `Index(["created_at","llm_analyzed"])` 복합 고려)

### [MED] 2-2. `services/rag_analysis/models.py:288` — `UsageLog.created_at` *(이전 감사 6/6 재확인)*
- **근거(filter)**: `models.py:343,350,363` `get_usage_stats(user=None)` 등 `created_at__gte=since` 단독. (`views.py:778`의 `user+created_at`은 `Index(["user","created_at"])`로 커버됨)
- **문제**: 복합 인덱스 4개 모두 선두가 user/model/request_type/cached → 전체 집계 경로는 prefix 미활용. LLM 호출마다 적재되어 누적.
- **권장**: Meta.indexes에 `models.Index(fields=["-created_at"])` 추가(ordering `-created_at`과 부호 일치).

### [MED] 2-3. `services/sec_pipeline/models.py:116` — `SupplyChainEvidence.extracted_at` *(이전 감사 5/31 재확인)*
- **근거(filter)**: `quality_checks.py:70`, `intelligence.py:84` `extracted_at__gte=since`.
- **문제**: 기존 인덱스 `["source_company","relationship_type"]`/`["target_company"]`/`["neo4j_dirty"]`만 → 시간윈도우 미커버.
- **권장**: `extracted_at = DateTimeField(auto_now_add=True, db_index=True)`.

### [MED] 2-4. `services/sec_pipeline/models.py:47` — `RawDocumentStore.collected_at`
- **근거(filter)**: `quality_checks.py:39`, `intelligence.py:78` `collected_at__gte=since`.
- **문제**: 기존 인덱스 `["symbol","-filing_date"]`만 → `collected_at` 단독 미커버. 테이블 규모는 SEC filing 수라 NewsArticle보다 작음.
- **권장**: `collected_at`에 `db_index=True`.

### [LOW] 2-5. `services/sec_pipeline/models.py:210` — `BusinessModelSnapshot.created_at`
- **근거**: `quality_checks.py:50`, `intelligence.py:112` `created_at__gte=since`. 종목당 스냅샷이라 소규모 + 배치 한정 → 인덱스 추가 가치 낮음(참고).

> **인덱스 누락 없음 확인**: `packages/shared/stocks/models.py`(후보 `SignalAccuracy.signal_date`는 `unique_together`+`Index(["signal_date","signal_tag"])` prefix로 커버), `packages/shared/users/models.py`, `services/serverless/models.py`, `services/_dormant/graph_analysis/models.py`(dormant).

---

## 3. 느린 Serializer (SerializerMethodField / property N+1)

### [HIGH] 3-1. `services/news/api/serializers.py:50` — `NewsArticleListSerializer.entities`
- `entities = NewsEntitySimpleSerializer(many=True)` — `NewsEntity.article` reverse FK. 뉴스 **리스트** 직렬화가 주용도 → article마다 entities 1쿼리.
- **권장**: 뷰 queryset에 `prefetch_related("entities")`. (한 줄로 해결)

### [HIGH] 3-2. `services/news/api/serializers.py:73,21` — `NewsArticleDetailSerializer.entities` + `NewsEntitySerializer.highlights`
- `entities`(reverse FK) 안에서 다시 `highlights`(reverse FK) 직렬화 → entity마다 highlights 쿼리(2단 중첩). `TrendingStockSerializer.recent_articles`(133)도 동일.
- **권장**: `prefetch_related("entities", "entities__highlights")`.

### [HIGH] 3-3. `packages/shared/stocks/serializers.py:451-460` — `WatchListStockSerializer.get_latest_price` + `get_chart_data`
```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by("-date").first()
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]
    # ← return 문 없음! 항상 None 반환(쿼리 낭비 + 기능 미동작 버그)
```
- **문제**: Watchlist `many=True` 직렬화 시 종목당 2쿼리. **`get_chart_data`는 `return` 누락**(CLAUDE.md "Processor return 필수" 정신 위반) — 쿼리는 돌지만 결과 폐기.
- **권장**: 뷰에서 `Prefetch("daily_prices", queryset=DailyPrice.objects.order_by("-date"))` 후 메모리 슬라이싱, 또는 `Subquery`로 `latest_close` annotate. 동시에 `return` 추가.

### [HIGH] 3-4. `packages/shared/users/serializers.py:346,284` — `WatchlistDetailSerializer.items` + `stock_count`
- `items = WatchlistItemSerializer(many=True)`(reverse FK)가 item마다 `source="stock.*"` 접근 → prefetch 없으면 item당 Stock 1쿼리. `stock_count = ReadOnlyField`(property `self.items.count()`)는 리스트 직렬화 시 행별 COUNT.
- **권장**: 뷰에서 `prefetch_related(Prefetch("items", queryset=WatchlistItem.objects.select_related("stock")))`. `stock_count`는 `.annotate(Count("items"))` 또는 prefetch된 `len()` 재사용.

### [MED] 3-5. `packages/shared/stocks/serializers.py:241-353` — `OverviewTabSerializer.get_dynamic_layers` (단건 6쿼리)
- OneToOne reverse 5건(`validation_news_summary`/`sensitivity_profile`/`growth_stage`/`capital_dna`/`narrative_tag`) + FK reverse `category_signals` + `overview_ko` → 객체당 ~6쿼리. **뷰 3진입점**(`views.py:545` Overview, `views.py:171/932` Detail/Complete, `views_mvp.py:158` full)에서 호출. 코드에 이미 `# TODO: prefetch_related` 주석.
- **단건 사용이라 queryset N+1은 아니나 요청당 고정 6쿼리.** 비교/목록 컨텍스트로 확장 시 HIGH 격상.
- **권장**: detail 뷰 queryset에 `select_related("overview_ko","validation_news_summary","sensitivity_profile","growth_stage","capital_dna","narrative_tag")` + `prefetch_related("category_signals")`. (OneToOne reverse는 select_related 가능 → 6쿼리→1쿼리)

### [MED] 3-6. `services/rag_analysis/serializers.py:33,59,38-49` — `DataBasketSerializer` items + property 집계
- `items`(reverse FK) prefetch 없으면 basket당 1쿼리. 추가로 `can_add_item()`→`self.items.count()`, `current_units`/`remaining_units` property→`self.items.aggregate(Sum)` 2회 → basket당 3~4 추가 쿼리. **주의: `.count()`/`.aggregate()`는 prefetch 캐시를 무시하고 DB 재조회** → prefetch만으론 미해결.
- **권장**: 모델 property를 `len(self.items.all())`/Python sum으로 변경하거나, 뷰에서 `annotate(_items_count=Count("items"), _units_total=Sum("items__data_units"))` 후 serializer가 annotate 참조.

### [MED] 3-7. `services/rag_analysis/serializers.py:86-87` — `AnalysisSessionSerializer.messages` + `basket`
- `messages`(reverse FK, list view에서 `views.py:429`는 prefetch됨) + **`basket`(FK) 미prefetch** + basket 내부 items까지 → 세션당 basket + items 쿼리. list view 페이지네이션도 없음.
- **권장**: 뷰에서 `.select_related("basket").prefetch_related("messages","basket__items")` + 페이지네이션.

### [MED] 3-8. `services/serverless/serializers.py:574-578` — `ScreenerAlertSerializer.get_preset_name`
```python
if obj.preset:
    return f"{obj.preset.icon} {obj.preset.name}"   # preset FK, prefetch 없으면 alert당 1쿼리
```
- **권장**: 뷰 queryset에 `select_related("preset")`. (`get_owner_email`의 `obj.user.email`도 `select_related("user")` 권장)

### [MED] 3-9. `packages/shared/users/serializers.py:16,26` — `UserSerializer/PrivateUserSerializer.favorite_stock`
- `favorite_stock = StockListingField(many=True)` M2M → prefetch 없으면 user당 쿼리. 사용자 목록 직렬화 시 HIGH 격상(뷰 1-7과 연동).
- **권장**: `prefetch_related("favorite_stock")`.

### [LOW] 3-10. `serializers.py` FK 체인 잠재 케이스
- `PortfolioSerializer`/`PortfolioDetailSerializer`의 `source="stock.*"`, `AlertHistoryListSerializer.alert_name`(`source="alert.name"`) — 표준 `select_related("stock"/"alert")`로 해결되는 일반 케이스. 뷰 queryset 적용 여부 점검 권장.

> **이슈 없음**: `serializers_fundamentals.py`, `serializers_market_movers.py`, `serializers_exchange.py`, `serializers_screener.py`(전부 FMP API dict 직렬화), `apps/market_pulse/serializers.py`(응답 dict), `apps/portfolio/api/serializers.py`(Pydantic 어댑터, DB 무관).

---

## 4. 페이지네이션 누락

| 위치 | 엔드포인트 | 현재 | 심각도 | 권장 |
|------|-----------|------|--------|------|
| `users/views.py:92` | `Users.get` | `User.objects.all()` 전체 반환 | MED | DRF pagination + `prefetch_related("favorite_stock")` |
| `rag_analysis/views.py:429` | `AnalysisSessionListCreateView.get` | 사용자 세션 전체 반환 | MED | PageNumberPagination |
| `rag_analysis/views.py:496` | `SessionMessagesView.get` | `session.messages.all()` 전체 | MED | PageNumberPagination (긴 대화 시 응답 폭주) |
| `serverless/views_admin.py:505` | `AdminNewsCategoryView.get` | 카테고리 전체 + `resolve_symbols` 루프 | MED | pagination(N+1 1-5와 동반 해결) |
| `rag_analysis/views.py:52` | `DataBasketListCreateView.get` | basket 전체(prefetch는 양호) | LOW | 필요 시 pagination |

> **정상(페이지네이션/슬라이스 적용)**: `StockListAPIView`(`StockListPagination` page_size 50/max 200), `StockSearchAPIView`(`[:20]`), `EODSignalDetailView`(`[:50]`), `UsageHistoryView`(pagination). 외부 API 뷰(screener/movers/exchange)는 `limit` 상한으로 제어.

---

## 부록 A — 거짓양성으로 배제한 항목 (검증 근거)

1. **screener/fundamentals/exchange/market-movers/search 뷰·Serializer**: 입력이 ORM queryset이 아니라 **FMP 외부 API dict 리스트**. `Serializer(..., many=True)`여도 `obj.get(...)`만 호출 → DB N+1 불가능. (grep으로 입력 타입 확인)
2. **`OverviewTabSerializer`**: 전 호출처에서 `many=True` 없이 단일 객체로만 사용 → queryset 차원 진짜 N+1이 아닌 "요청당 고정 6쿼리"(이슈 3-5로 MED 분류).
3. **`SignalAccuracy.signal_date`**: `unique_together(stock,signal_date,signal_tag)` + `Index(["signal_date","signal_tag"])` prefix로 커버 → 인덱스 누락 아님.
4. **`apps/portfolio/api/serializers.py`**: Pydantic 어댑터 기반(Portfolio Coach), DB 직렬화 아님.
5. **`apps/market_pulse/views.py`(macro), `sec_pipeline/views.py`**: 서비스 레이어 위임, 뷰 레벨 ORM 루프 없음.

## 부록 B — 이전 감사 대비 (미해결 잔존)

- `UsageLog.created_at` 인덱스(이슈 2-2): `6월/6일/performance_audit.md:181` 기록 → **미해결 잔존**.
- `SupplyChainEvidence.extracted_at` 인덱스(이슈 2-3): `5월/31일/performance_audit.md:262` 기록 → **미해결 잔존**.

---

## 권장 실행 순서 (수정 시)

> 본 보고서는 읽기 전용 감사이며 코드를 수정하지 않았습니다. 아래는 수정 착수 시 권장 순서입니다.

1. **1차(쉬움/효과 큼)**: news 2건(3-1/3-2, `prefetch_related` 한 줄), users Watchlist(3-4), rag_analysis Session(3-7) — 뷰 queryset의 `select_related`/`prefetch_related` 추가만으로 HIGH 다수 해결. Serializer 수정 불필요.
2. **2차(중간/캐시 없는 HIGH)**: validation 2건(1-1/1-2), chain_sight(1-3) — 루프 진입 전 `__in`/`Q` 일괄 로드 + dict 매핑. 동일 안티패턴 공통 리팩터링.
3. **3차(인덱스, migration 동반)**: news/rag_analysis/sec_pipeline의 `auto_now_add` 필드 `db_index=True` 추가 — migration 묶음 1건으로 일괄.
4. **별도(버그)**: `WatchListStockSerializer.get_chart_data` `return` 누락(3-3)은 N+1과 무관한 **기능 미동작 버그** — 우선 처리 권장.
5. **구조 검토**: rag_analysis `DataBasket` property 집계(3-6)는 `.count()`/`.aggregate()`가 prefetch 캐시를 무시하므로 모델 property 재설계 필요.
