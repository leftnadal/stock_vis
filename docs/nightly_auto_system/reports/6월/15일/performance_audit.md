# API 성능 감사 보고서

- **일시**: 2026-06-15
- **범위**: 읽기 전용 정적 감사 (코드 미수정)
- **대상**: 뷰 17개, 모델 7개, 연관 Serializer 6개
- **방법**: 병렬 정적 분석 3트랙(stocks 뷰 / 기타 뷰 / 모델 인덱스) + 핵심 모델 정의 직접 교차검증
- **주의**: 본 보고서는 정적 분석 결과다. 실제 쿼리 카운트(`django-silk` / `assertNumQueries` / `connection.queries`)로 재현 검증 후 수정 권장. 라인 번호는 감사 시점 기준.

---

## 요약

### 심각도별 이슈 수 (오탐 정정 후)

| 심각도 | N+1 / 쿼리 | 인덱스 | Serializer | 페이지네이션 | 합계 |
|--------|-----------|--------|-----------|-------------|------|
| **HIGH** | 5 | 0 | 1 | 0 | **6** |
| **MED** | 7 | 1 | 0 | 1 | **9** |
| **LOW** | 3 | 2 | 0 | 0 | **5** |
| **합계** | 15 | 3 | 1 | 1 | **20** |

### ⚠️ 오탐 정정 (자동 감사가 잘못 보고 → 실제로는 이상 없음)

자동 트랙이 "인덱스 누락 HIGH"로 보고했으나 **직접 모델 정의를 확인한 결과 이미 인덱스가 존재하거나 Django 기본 동작으로 커버되는** 항목. 수정 불필요:

| 보고된 항목 | 실제 상태 | 근거 |
|------------|----------|------|
| `Portfolio.user` 인덱스 누락 (HIGH) | **이미 존재** | `users/models.py:91-93` — `Index(["user","stock"])` + `Index(["user","-updated_at"])` 보유. FK 자동 인덱스도 별도 존재 |
| `WatchlistItem.position_order` 인덱스 누락 (MED) | **이미 존재** | `users/models.py:243-245` — `Index(["watchlist","position_order"])` 정확히 보유 |
| `UserInterest.user` 인덱스 누락 (MED) | **불필요** | `users/models.py:291` — `unique_together("user",...)` 최좌측 프리픽스가 `filter(user=)` 커버 + FK 자동 인덱스 |
| `ScreenerAlert/InvestmentThesis/ScreenerPreset/CategoryCache.user` (HIGH×3) | **이미 존재** | `serverless/models.py` 각 Meta.indexes에 user 복합 인덱스 보유 (자동 트랙도 후속 자가정정함) |

> **핵심 교훈**: Django `ForeignKey`는 기본값 `db_index=True`다. 단일 FK `filter(user=…)`는 항상 인덱싱되어 있으므로 "FK에 db_index 없음"은 유효한 지적이 아니다. 유효한 인덱스 개선은 **`filter(A) + order_by(B)` 복합 패턴에 대한 복합 인덱스**뿐이다 (아래 §2).

---

## 상세

### 1. N+1 쿼리 / 반복 쿼리

#### [HIGH] 1-1. WatchList 직렬화 시 종목당 DailyPrice 2회 조회
- **위치**: `packages/shared/stocks/serializers.py` — `WatchListStockSerializer` `get_latest_price` / `get_chart_data`
- **난이도**: 중간
- **설명**: `SerializerMethodField` 내부에서 `DailyPrice.objects.filter(stock=obj).order_by("-date")...`를 호출. `many=True` 직렬화 시 종목 N개 × (latest + chart) = **2N 쿼리**.
- **권장**: 뷰 queryset에 `Prefetch("dailyprice_set", queryset=DailyPrice.objects.order_by("-date")[:7])` 적용 후, 메서드에서 `obj.dailyprice_set.all()` 캐시 사용.
- **검증 필요**: 이 serializer를 `many=True`로 쓰는 호출부 확인(워치리스트 목록 응답). 단건 사용이면 영향 경미.

#### [HIGH] 1-2. 뉴스 trending — 종목마다 최신 기사 별도 조회
- **위치**: `services/news/api/views.py:370-391` (`NewsViewSet.trending`)
- **난이도**: 중간
- **설명**: 상위 트렌딩 종목을 `annotate`로 구한 뒤, **루프마다** `NewsArticle.objects.filter(entities__symbol=symbol, …).distinct()[:3]`를 재실행 → 종목 수만큼 추가 쿼리.
- **권장**: 트렌딩 심볼 리스트를 모은 뒤 `entities__symbol__in=symbols` 단일 쿼리로 최신 기사를 일괄 조회하고 메모리에서 심볼별 그룹핑.

#### [HIGH] 1-3. 뉴스 stock_news — entities prefetch 누락
- **위치**: `services/news/api/views.py:117-123` (`NewsViewSet.stock_news`)
- **난이도**: 쉬움
- **설명**: `NewsArticle.objects.filter(entities__symbol=symbol).distinct().order_by(...)` 후 serializer가 `article.entities`(역참조 M2M)에 접근 → 기사당 1쿼리.
- **권장**: `.prefetch_related("entities")` 추가. (`distinct()`와 병용 가능)

#### [HIGH] 1-4. 사용자 목록 — favorite_stock(M2M) prefetch 누락
- **위치**: `packages/shared/users/views.py:92-95` (`Users.get`)
- **난이도**: 쉬움
- **설명**: `User.objects.all()` 후 `UserSerializer(many=True)`가 `favorite_stock`(ManyToMany)을 직렬화 → 사용자당 1쿼리.
- **권장**: `User.objects.all().prefetch_related("favorite_stock")`. (관리자 전용 엔드포인트면 우선순위 하향 가능)

#### [HIGH] 1-5. LeaderComparison — 메트릭당 3중 쿼리
- **위치**: `services/validation/api/views.py:459-504` (`LeaderComparisonView.get`)
- **난이도**: 높음
- **설명**: `for cat, mc in all_metrics` 루프에서 `MetricDefinition.filter(pk=mc).first()` + `CompanyMetricSnapshot.filter(...).first()`(자사) + 동일(리더) = 메트릭당 3쿼리. 30개 메트릭 시 ~90쿼리.
- **권장**: `MetricDefinition`은 `pk__in`으로 맵 사전 구성, `CompanyMetricSnapshot`은 `symbol__in=[자사, 리더], metric_code_id__in=...`로 일괄 조회 후 dict 매핑.

#### [MED] 1-6. Validation 요약/카테고리 — 메트릭 정의 루프 조회
- **위치**: `services/validation/api/views.py:148-166`(`ValidationSummaryView`), `:261-265`(`_build_category`)
- **난이도**: 중간
- **설명**: 루프 안에서 `MetricDefinition.objects.filter(pk=mc).first()` / `CompanyBenchmarkDelta.filter(...).first()` 개별 조회.
- **권장**: 루프 진입 전 `pk__in` / `metric_code_id__in` 일괄 조회 후 dict 매핑.

#### [MED] 1-7. 지표 비교 — symbol 루프 내 Stock+DailyPrice 조회
- **위치**: `packages/shared/stocks/views_indicators.py:371-434` (`IndicatorComparisonView`)
- **난이도**: 중간
- **설명**: `for symbol in symbols`에서 `Stock.objects.get(symbol)` + `DailyPrice.filter(stock=stock)[:50]` 반복 → 2N 쿼리.
- **권장**: `Stock.objects.filter(symbol__in=symbols).prefetch_related(Prefetch("dailyprice_set", DailyPrice.order_by("-date")[:50]))` 후 dict 매핑.

#### [MED] 1-8. RAG 바스켓 추가 — data_type 루프 개별 조회
- **위치**: `services/rag_analysis/views.py:250-293` (`DataBasketAddStockDataView.post`)
- **난이도**: 중간
- **설명**: `for data_type in data_types`에서 `BasketItem.filter(...).first()` 개별 중복 확인.
- **권장**: `BasketItem.filter(basket=basket, reference_id=symbol)`를 한 번 조회해 `(item_type, reference_id)` 키 dict로 메모리 매핑.

#### [MED] 1-9. 워치리스트 일괄 추가 — 루프 내 개별 INSERT
- **위치**: `packages/shared/users/views.py:939-965` (`WatchlistBulkAddView.post`)
- **난이도**: 중간
- **설명**: `for symbol in symbols: WatchlistItem.objects.create(...)` → N회 INSERT.
- **권장**: `WatchlistItem(...)` 리스트 구성 후 `bulk_create(batch_size=100)`. 단, `unique_together` 충돌 처리(`ignore_conflicts` 또는 사전 존재 조회) 필요.

#### [MED] 1-10. 관리자 뉴스 카테고리 — 카테고리당 resolve_symbols()
- **위치**: `services/serverless/views_admin.py:507-530` (`AdminNewsCategoryView.get`)
- **난이도**: 중간
- **설명**: `for cat in categories: cat.resolve_symbols()` — 메서드 내부에서 `SP500Constituent` 조회 → 카테고리당 쿼리.
- **권장**: `SP500Constituent`를 한 번 로드한 뒤 카테고리별 매칭을 메모리에서 수행.

#### [MED] 1-11. StockOverview / CompleteData — 다중 OneToOne/역참조 순차 조회
- **위치**: `packages/shared/stocks/views.py` — `StockOverviewAPIView`(≈546), `StockCompleteDataAPIView`(≈922-950)
- **난이도**: 쉬움
- **설명**: `OverviewTabSerializer`가 `overview_ko`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`, `validation_news_summary`(OneToOne) + `category_signals`(역참조)에 try-except로 개별 접근. 단건 응답이라 폭발은 아니나 1요청에 6~10 쿼리.
- **권장**: 뷰 queryset에 해당 OneToOne들을 `select_related(...)`, `category_signals`는 `prefetch_related`. CompleteData는 재무 3종을 `Prefetch`로 일괄.
- **검증 필요**: serializer가 실제 접근하는 관계명과 모델의 `related_name` 일치 여부 확인 후 적용.

#### [MED] 1-12. 포트폴리오 합계 — Python 루프 집계
- **위치**: `packages/shared/users/views.py:383-385`, `:419/429` (`PortfolioSummaryView`, `PortfolioDetailTableView`)
- **난이도**: 중간
- **설명**: `sum(p.total_value for p in portfolios)` — `total_value`는 `@property`(`stock.real_time_price` 접근). `select_related("stock")` 되어 있으면 추가 쿼리는 없으나 DB 집계 미활용.
- **권장**: `aggregate(Sum(F("quantity") * F("stock__real_time_price")))`로 DB 위임. (대형 포트폴리오에서만 체감)

#### [LOW] 1-13. 지표 차트 — values() 후 list() 전체 적재
- **위치**: `packages/shared/stocks/views_indicators.py:68-70`, `261-265`
- **난이도**: 쉬움
- **설명**: `pd.DataFrame(list(query.values(...)))` — 기간 길면 메모리 적재 증가. 단일 종목이라 영향 제한적.
- **권장**: `pd.DataFrame.from_records(query.values(...))` + 기간 상한 가드.

#### [LOW] 1-14. validate_and_create_stock — get 후 create 분기
- **위치**: `packages/shared/stocks/views_search.py:197-233`
- **난이도**: 중간
- **설명**: `get()` 실패 시 외부 API 후 `create()`. 동시 요청 시 중복 생성/조회 가능성.
- **권장**: `get_or_create(symbol=…, defaults=…)`로 원자화.

#### [LOW] 1-15. Chain Sight neighbor — Neo4j 결과 크면 메모리 적재
- **위치**: `apps/chain_sight/api/views.py:617-686` (`NeighborGraphView`)
- **난이도**: 중간
- **설명**: 이웃 심볼 집합으로 `Stock.objects.filter(symbol__in=...)` dict 매핑 — 패턴 자체는 양호. Neo4j 반환 규모가 크면 메모리 부담.
- **권장**: 이웃 수 상한(top-N) 명시 + 로깅.

---

### 2. 인덱스 누락 (오탐 정정 후 — 유효 항목만)

> §요약의 오탐 표 참조. 아래는 직접 확인 결과 **실제로 인덱스가 없고** 쿼리 패턴이 이를 요구하는 항목.

#### [MED] 2-1. MarketMover — mover_type 단독/선두 필터 인덱스 부재
- **위치**: `services/serverless/models.py` — `MarketMover.Meta.indexes` (≈103: `["date","mover_type"]`만 존재)
- **모델.필드**: `MarketMover.mover_type`
- **난이도**: 쉬움
- **설명**: 지배적 쿼리가 `filter(date=…, mover_type=…)`이면 기존 `["date","mover_type"]`로 충분. 그러나 `mover_type` 기준 기간 스캔(`filter(mover_type=…).order_by("-date")`)이 있으면 미커버.
- **권장**: 해당 쿼리 패턴 존재 시에만 `Index(["mover_type","-date"])` 추가. **쿼리 로그 확인 후 결정** (없으면 추가 불필요).

#### [LOW] 2-2. DataBasket — (user, -updated_at) 복합 인덱스 부재
- **위치**: `services/rag_analysis/models.py:24-27` (`Meta`에 `indexes` 없음, `ordering=["-updated_at"]`)
- **모델.필드**: `DataBasket.(user, updated_at)`
- **난이도**: 쉬움
- **설명**: `filter(user=request.user)`(views.py:52 등)는 **FK 자동 인덱스로 이미 커버**. 다만 뒤따르는 `order_by("-updated_at")`까지 한 인덱스로 처리하려면 복합 인덱스가 유리. 사용자별 바스켓 수가 적어 실익은 작음.
- **권장**: `Meta.indexes = [Index(fields=["user","-updated_at"])]`. 우선순위 낮음.

#### [LOW] 2-3. AnalysisSession — (user, -updated_at) 복합 인덱스 부재
- **위치**: `services/rag_analysis/models.py:148-151` (`Meta`에 `indexes` 없음, `ordering=["-updated_at"]`)
- **모델.필드**: `AnalysisSession.(user, updated_at)`
- **난이도**: 쉬움
- **설명**: 2-2와 동일 구조. `filter(user=…).order_by("-updated_at")`(views.py:429). 단일 FK 필터는 이미 인덱싱.
- **권장**: `Index(fields=["user","-updated_at"])`. 우선순위 낮음.

> **검토했으나 이상 없음**: `news/models.py`(NewsArticle 복합 인덱스 다수 + `-published_at` 커버), `sec_pipeline/models.py`(symbol+filing_date, source_company+relationship_type 보유), `graph_analysis/models.py`(전 모델 인덱스 적정). NewsArticle `category` 단독 인덱스는 분류 배치(`news_classifier`)에서 쓰이나 대부분 `category + -published_at` 복합으로 커버됨 — 단독 카테고리 풀스캔 쿼리 발견 시에만 검토.

---

### 3. 느린 Serializer (SerializerMethodField 추가 쿼리)

#### [HIGH] 3-1. WatchListStockSerializer
- **위치**: `packages/shared/stocks/serializers.py` — `get_latest_price`, `get_chart_data`
- 위 **1-1과 동일 항목**(N+1의 근본 원인이 serializer에 있어 양 축에서 동시 집계). 중복 카운트 아님 — 합계에서는 Serializer 1건으로만 계상.
- **권장**: 뷰 prefetch + 메서드에서 캐시 접근. (§1-1 참조)

> 그 외 점검한 serializer(`OverviewTabSerializer`, `validation`/`news`/`rag` 직렬화)는 메서드 내 쿼리가 있어도 **단건 응답**이거나 뷰단 prefetch로 흡수 가능 → §1-11 등 뷰 수정으로 해소.

---

### 4. 페이지네이션 누락

#### [MED] 4-1. NewsViewSet.all_news — 수동 슬라이싱(준-페이지네이션)
- **위치**: `services/news/api/views.py:443-468`
- **난이도**: 쉬움
- **설명**: `pagination_class`는 선언돼 있으나 `all_news`는 DRF 페이지네이터 대신 `offset:offset+limit` 수동 슬라이싱으로 응답. 동작은 하지만 `count`/`next`/`previous` 표준 메타 부재, 상한 미가드 시 대량 limit 위험.
- **권장**: limit 상한 클램프(예: `min(limit, 100)`) 추가, 또는 DRF `LimitOffsetPagination` 일원화.

> **점검 결과 양호**: `stocks/views_eod.py`(`select_related("stock")` 적용), `market_pulse/views.py`(캐시/서비스 호출 위주, list 폭발 없음), `sec_pipeline/views.py`(대량 직렬화 없음), `serverless/views_admin.py`의 `AdminNewsSectorOptionsView`(`values().annotate()` 집계). FMP 외부 API 기반 뷰(`views_exchange/screener/market_movers/fundamentals`)는 DB N+1 무관.

---

## 권장 처리 순서 (영향 대비 비용)

| 순위 | 항목 | 심각도 | 난이도 | 한 줄 조치 |
|------|------|--------|--------|-----------|
| 1 | 1-3 뉴스 stock_news entities | HIGH | 쉬움 | `.prefetch_related("entities")` 1줄 |
| 2 | 1-4 사용자 favorite_stock | HIGH | 쉬움 | `.prefetch_related("favorite_stock")` 1줄 |
| 3 | 1-2 뉴스 trending 루프 | HIGH | 중간 | symbol__in 일괄 조회로 재구성 |
| 4 | 1-5 LeaderComparison 3중 | HIGH | 높음 | pk__in/symbol__in dict 매핑 |
| 5 | 1-1/3-1 WatchList serializer | HIGH | 중간 | 뷰 Prefetch + 메서드 캐시 |
| 6 | 1-6~1-11 Validation/RAG/Admin 루프 | MED | 중간 | 루프 전 일괄 조회 패턴 |
| 7 | 4-1 all_news limit 가드 | MED | 쉬움 | limit 상한 클램프 |
| 8 | 2-2/2-3 RAG 복합 인덱스 | LOW | 쉬움 | 쿼리 로그 확인 후 선택 적용 |

---

## 방법론 한계 (정직성 고지)

- 본 감사는 **정적 코드 분석**이며 실제 쿼리 수를 실행 측정하지 않았다. N+1 항목은 `assertNumQueries` 또는 `django-silk`로 재현 후 수정 권장.
- 일부 라인 번호는 자동 분석 트랙이 보고한 값으로, §2 인덱스 항목과 §요약 오탐 표는 모델 정의를 **직접 확인**해 정정했으나, §1의 일부 뷰 라인은 직접 재확인하지 않았다(파일·함수명은 신뢰 가능, 라인은 ±이동 가능).
- 인덱스 추가는 읽기 성능과 쓰기 비용·디스크의 트레이드오프다. 실제 테이블 규모와 쿼리 빈도를 보고 결정할 것 — 특히 §2 전 항목은 "선택적".
- **본 보고서는 읽기 전용 산출물이며 어떤 코드도 수정하지 않았다.**
