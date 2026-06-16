# API 성능 감사 보고서

- **작성일**: 2026-06-16
- **범위**: 17개 뷰 파일 + 7개 모델 파일 (+ 관련 serializer)
- **방식**: 정적 코드 분석 (읽기 전용, 코드 미수정)
- **검사 항목**: N+1 쿼리 / 인덱스 누락 / 느린 Serializer / 페이지네이션 누락

> **참고**: CLAUDE.md에 기재된 경로(`stocks/views.py` 등)는 현재 monorepo 구조로 이전되어 있음.
> 실제 경로 매핑: `stocks/*` → `packages/shared/stocks/*`, `users/*` → `packages/shared/users/*`,
> `macro/*` → `apps/market_pulse/*`, `chainsight/*` → `apps/chain_sight/*`,
> `news/api/*` → `services/news/api/*`, `rag_analysis/*`·`serverless/*`·`validation/*`·`sec_pipeline/*` → `services/*`,
> `graph_analysis/*` → `services/_dormant/graph_analysis/*` (휴면 상태).

---

## 요약 (심각도별 이슈 수)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 누락 | 합계 |
|--------|:---:|:---:|:---:|:---:|:---:|
| **HIGH** | 5 | 2 | 0 | 2 | **9** |
| **MED** | 4 | 4 | 2 | 3 | **13** |
| **LOW** | 0 | 3 | 2 | 4 | **9** |
| **합계** | **9** | **9** | **4** | **9** | **31** |

> 추가로 "양호 확인" 항목(이미 페이지네이션·select_related 적용됨) 5건이 검증되었으며 본문 말미에 별도 기록.

### HIGH 이슈 한눈에 보기

| # | 파일:라인 | 유형 | 난이도 |
|---|-----------|------|:---:|
| H1 | `packages/shared/stocks/serializers.py:241-353` (OverviewTab) | N+1 | 높음 |
| H2 | `packages/shared/stocks/serializers.py:451-460` (WatchListStock) | N+1 | 중간 |
| H3 | `packages/shared/users/views.py:383-385` (PortfolioSummary) | N+1 | 쉬움 |
| H4 | `packages/shared/users/views.py:419,429` (PortfolioDetailTable) | N+1 | 쉬움 |
| H5 | `services/news/api/views.py:370-391` (trending) | N+1 | 중간 |
| H6 | `services/validation/api/views.py:196-202,426-431` | N+1 | 중간 |
| H7 | `apps/chain_sight/api/views.py:78-91` (ChainSightGraph) | N+1 | 중간 |
| H8 | `apps/chain_sight/models/relation_discovery.py:64-163` (RelationConfidence) | 인덱스 | 중간 |
| H9 | `packages/shared/users/views.py:92-95` (Users 목록) | 페이지네이션 | 중간 |

---

## 상세

## 1. N+1 쿼리

### [H1] OverviewTabSerializer — 6개 OneToOne 역참조 미선로딩
- **파일**: `packages/shared/stocks/serializers.py:241-353`
- **연관 뷰**: `packages/shared/stocks/views.py:545-551` (`StockOverviewAPIView`)
- **심각도**: HIGH | **수정난이도**: 높음
- **설명**: serializer의 `dynamic_layers` 계산에서 `obj.validation_news_summary`(271), `obj.sensitivity_profile`, `obj.growth_stage`, `obj.capital_dna`, `obj.narrative_tag`(271-286) 등 6개 OneToOne/역참조에 접근. 뷰에서는 `select_related("overview_ko")`만 적용되어 나머지는 객체당 추가 쿼리 발생. `category_signals.all()`(251)도 prefetch 미적용.
- **권장 수정**:
  ```python
  Stock.objects.select_related(
      "overview_ko", "validation_news_summary", "sensitivity_profile",
      "growth_stage", "capital_dna", "narrative_tag",
  ).prefetch_related("category_signals").filter(symbol=symbol).first()
  ```

### [H2] WatchListStockSerializer — 종목당 DailyPrice 재조회
- **파일**: `packages/shared/stocks/serializers.py:451-460`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: `get_latest_price()`가 종목마다 `DailyPrice.objects.filter(stock=obj).order_by("-date").first()` 실행. `many=True` 직렬화 시 watchlist 종목 수만큼 N+1. (`get_chart_data()`도 7건 조회 — [S1]에서 별도 지적)
- **권장 수정**: 뷰에서 `Prefetch` 객체로 정렬된 최근 가격을 prefetch하거나, 최신 가격을 별도 집계해 serializer context로 전달.

### [H3] PortfolioSummaryView — 프로퍼티 루프 내 FK 접근
- **파일**: `packages/shared/users/views.py:383-385`
- **심각도**: HIGH | **수정난이도**: 쉬움
- **설명**: `for portfolio in portfolios: total_value += portfolio.total_value`. `total_value`/`total_cost` 프로퍼티가 내부에서 `self.stock.real_time_price` 등 FK 필드 접근(models.py:100-107). `select_related("stock")`은 적용되어 있어 치명적이진 않으나, DB 집계로 옮기면 루프·직렬화 비용 제거 가능.
- **권장 수정**: `aggregate(Sum(F("quantity") * F("stock__real_time_price")))` 형태로 DB 집계.

### [H4] PortfolioDetailTableView — 동일 쿼리셋 2회 순회
- **파일**: `packages/shared/users/views.py:419, 429`
- **심각도**: HIGH | **수정난이도**: 쉬움
- **설명**: `sum(p.total_value for p in portfolios)`(419)와 `sum(p.total_cost for p in portfolios)`(429)로 같은 쿼리셋을 두 번 순회 + 프로퍼티마다 FK 접근. 단일 순회로 통합하거나 DB 집계로 대체.

### [H5] NewsViewSet.trending — symbol별 기사 재조회
- **파일**: `services/news/api/views.py:370-391`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: 집계 결과 `trending_data`를 루프하며 각 symbol마다 `NewsArticle.objects.filter(entities__symbol=symbol, ...)` 실행(372-377). trending 항목 수만큼 추가 쿼리.
- **권장 수정**: `entities__symbol__in=symbols`로 일괄 조회 후 Python에서 symbol별 그룹화(최대 3건).

### [H6] Validation _find_leader / LeaderComparisonView — peers 평가 패턴
- **파일**: `services/validation/api/views.py:196-202`, `426-431`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: `Stock.objects.filter(symbol__in=peer_symbols).order_by("-market_capitalization")` 결과에서 `.first()`/인덱싱 접근. 슬라이싱을 명시적으로 `[:2]` + `list()`로 강제 평가하지 않으면 쿼리셋 재평가 위험.
- **권장 수정**: `peers = list(Stock.objects.filter(...).order_by("-market_capitalization")[:2])`.

### [H7] ChainSightGraphView — 엣지당 2쿼리
- **파일**: `apps/chain_sight/api/views.py:78-91`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: `for edge in result["edges"]:` 루프에서 엣지마다 `CoMentionEdge.objects.filter(...).first()` + `PriceCoMovement.objects.filter(...).first()` 호출 → 엣지 N개당 2N 쿼리.
- **권장 수정**: 엣지쌍 목록을 `Q()` OR로 묶어 두 모델을 각 1쿼리로 일괄 조회 후 `dict` 매핑.

### [M1] AnalysisSession messages / basket 미선로딩
- **파일**: `services/rag_analysis/views.py:496`, `601-603`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `session.messages.all()`(496), `session.basket.items...`(601-603) 접근 전 session 조회 시 prefetch/select_related 미적용.
- **권장 수정**: `AnalysisSession.objects.select_related("basket").prefetch_related("messages").get(...)`.

### [M2] AlertHistorySerializer — FK source N+1
- **파일**: `services/serverless/serializers.py:649, 681`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `source="alert.name"` 등 FK 필드 참조. 리스트 직렬화 시 alert당 추가 쿼리.
- **권장 수정**: 뷰 쿼리셋에 `select_related("alert")` 추가.

### [M3] ChainSightSuggestionView — union() 비효율
- **파일**: `apps/chain_sight/api/views.py:174-193`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `CoMentionEdge.objects.filter(symbol_a=symbol).union(filter(symbol_b=symbol))`. 루프 내 FK 접근은 없어 N+1은 아니나, `union()`보다 `Q(symbol_a=symbol) | Q(symbol_b=symbol)`이 효율적.

### [M4] UserInterest 일괄 생성 루프
- **파일**: `packages/shared/users/views.py:1081-1155`
- **심각도**: MED | **수정난이도**: 중간
- **설명**: `interests_data` 루프 내 `get_or_create()` 반복(1089) + `_link_category()` 내부 `NewsCollectionCategory.objects.get_or_create()`(1128,1145). 요청 아이템 수만큼 쿼리.
- **권장 수정**: 기존 항목을 한 번에 조회해 메모리 비교 후 `bulk_create`.

---

## 2. 인덱스 누락

### [H8] RelationConfidence — composite index 부재
- **파일**: `apps/chain_sight/models/relation_discovery.py:64-163`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: `symbol_a`/`symbol_b`가 개별 `db_index=True`(94-95)이나 파이프라인·Neo4j 동기화에서 빈번한 `filter(symbol_a=..., symbol_b=...)` 조회에 대응하는 복합 인덱스 없음.
- **권장 수정**: `Meta.indexes`에 `models.Index(fields=["symbol_a", "symbol_b"])` 추가.

### [M5] PriceCoMovement — symbol_b 인덱스 정의 혼재
- **파일**: `apps/chain_sight/models/relation_discovery.py:36-58`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `symbol_b`가 필드 레벨 `db_index=True`인데 `Meta.indexes`에는 `symbol_a`만 포함. 정의 방식이 혼재되어 중복 인덱스/마이그레이션 혼선 위험.
- **권장 수정**: 필드 레벨 `db_index` 제거하고 `Meta.indexes`로 일원화(`symbol_a`, `symbol_b` 모두 등록).

### [M6] UserInterest — user 필터용 인덱스 부재
- **파일**: `packages/shared/users/models.py:274-295`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `views.py:1046-1047`에서 `filter(user=...)` 사용. `unique_together=("user","interest_type","value")`는 있으나 `user` 선두 단독/정렬 쿼리에는 별도 인덱스 유익.
- **권장 수정**: `models.Index(fields=["user", "-created_at"])` 추가.

### [M7] SP500Constituent — sector/sub_sector 인덱스 확인 필요
- **파일**: `services/serverless/views_admin.py:569-579` (모델: `packages/shared/stocks/models.py`)
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `filter(sector=value)`, `filter(sub_sector=value)` 조회에 대응하는 `db_index` 여부 확인 필요. 누락 시 추가 권장.

### [M8] AnalysisSession — (user, updated_at) 복합 인덱스 권장
- **파일**: `services/rag_analysis/models.py:128-129`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `filter(user=...).order_by("-updated_at")` 패턴 빈번 예상. FK 자동 인덱스만으로는 정렬 비용 발생.
- **권장 수정**: `models.Index(fields=["user", "-updated_at"])`.

### [L1] DailyPrice — volume 정렬 인덱스 부적합
- **파일**: `packages/shared/stocks/models.py:247-251`
- **심각도**: LOW | **수정난이도**: 쉬움
- **설명**: `Index(fields=["date","volume"])`는 volume 필터가 없으면 거래량 정렬에 활용도 낮음. 거래량 정렬 쿼리가 있으면 `-volume` 선두 인덱스 검토.

### [L2] WeeklyPrice — 범위 조회 인덱스 미활용
- **파일**: `packages/shared/stocks/models.py:267-279`
- **심각도**: LOW | **수정난이도**: 쉬움
- **설명**: `week_start_date`/`week_end_date`에 `db_index=True`는 있으나 범위 조회용 복합 인덱스는 없음. 주간 범위 조회 빈도에 따라 검토.

### [L3] StockNews — sentiment 인덱스 부재
- **파일**: `packages/shared/stocks/models.py:1164`
- **심각도**: LOW | **수정난이도**: 쉬움
- **설명**: `sentiment` 필터링 가능성 대비 인덱스 없음. 감정 기반 필터 쿼리가 있으면 추가 권장.

> **graph_analysis CorrelationEdge** (`services/_dormant/graph_analysis/models.py:83-134`): `stock_a`/`stock_b`는 FK 자동 인덱스 + `(stock_a, stock_b, -date)` 복합 인덱스 보유 → **양호**. (휴면 앱이므로 우선순위 낮음)

---

## 3. 느린 Serializer (SerializerMethodField 추가 쿼리/연산)

### [M9] MarketMoverListSerializer — 항목마다 Calculator 인스턴스화
- **파일**: `services/serverless/serializers.py:92-144`
- **심각도**: MED | **수정난이도**: 중간
- **설명**: `get_sector_alpha_display()`, `get_etf_sync_display()`, `get_volatility_pct_display()`가 항목마다 `IndicatorCalculator`를 생성·계산. `many=True` 리스트에서 항목 수만큼 반복 연산.
- **권장 수정**: 모델 save 시점 사전 계산 후 필드화, 또는 serializer 레벨 캐싱.

### [S1] WatchListStockSerializer.get_chart_data — 쿼리 후 미반환 (낭비)
- **파일**: `packages/shared/stocks/serializers.py:458-461`
- **심각도**: MED | **수정난이도**: 쉬움
- **설명**: `DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]` 조회만 하고 **반환값 없음(None)**. N+1 쿼리는 유발하면서 결과는 버려짐.
- **권장 수정**: 의도된 기능이면 직렬화 결과 반환 + prefetch; 불필요하면 메서드 제거.

### [L4] MarketBreadth / SectorPerformance Serializer — Service 인스턴스화·복잡 연산
- **파일**: `services/serverless/serializers.py:198-233`, `450-483`
- **심각도**: LOW | **수정난이도**: 중간
- **설명**: `get_signal_interpretation()`, `get_name_ko()`, `get_color()` 등이 매 항목 객체 생성/맵 조회. 상수 딕셔너리로 단순화 권장.

### [L5] OverviewTabSerializer.get_korean_overview — 광범위 except
- **파일**: `packages/shared/stocks/serializers.py:226-239`
- **심각도**: LOW | **수정난이도**: 쉬움
- **설명**: `except Exception: return None`으로 버그 은폐 위험(성능보단 품질). `except (AttributeError, DoesNotExist)`로 좁힐 것.

---

## 4. 페이지네이션 누락

### [H9] Users 관리자 목록 — 전체 로드
- **파일**: `packages/shared/users/views.py:92-95`
- **심각도**: HIGH | **수정난이도**: 중간
- **설명**: `User.objects.all()` 전체를 직렬화. 사용자 증가 시 메모리/응답 지연. `PageNumberPagination` 적용 필요.

### [M10] AdminNewsCategoryView — 전체 카테고리 루프
- **파일**: `services/serverless/views_admin.py:502-531`
- **심각도**: MED | **수정난이도**: 중간
- **설명**: `NewsCollectionCategory.objects.all()` 전건 루프 처리. 카테고리 증가 시 저하. 페이지네이션 권장.

### [M11] Stocks 다건 list 엔드포인트 — limit만 존재
- **파일**: `packages/shared/stocks/views_screener.py`(StockScreenerView 64-167, LargeCap 264-314, HighDividend 317-368, Sector 371-427, LowBeta 430-479, Exchange 482-538), `views_fundamentals.py`(KeyMetrics 31-103, Ratios 106-165), `views_indicators.py`(18-236)
- **심각도**: MED | **수정난이도**: 중간
- **설명**: APIView 기반으로 `limit`(최대 1000) 파라미터만 있고 표준 `pagination_class` 미설정. 대량 반환 시 메모리·payload 증가.
- **권장 수정**: `PageNumberPagination`/`LimitOffsetPagination` 도입 또는 limit 상한 하향.

### [M12] StockCompleteDataAPIView — 단일 응답 다건 묶음
- **파일**: `packages/shared/stocks/views.py:909-968`
- **심각도**: MED | **수정난이도**: 중간
- **설명**: chart(30) + balance/income/cashflow(각 5년) 등을 한 응답에 일괄 반환 → 큰 payload. 탭별 분리 로드 권장.

### [L6] StockSearchAPIView — 하드코딩 [:20]
- **파일**: `packages/shared/stocks/views.py:190-245`
- **심각도**: LOW | **수정난이도**: 중간
- **설명**: 고정 20건만 반환, 동적 페이지네이션 없음. 검색 UX 확장 시 표준 페이지네이션 검토.

### [L7] PresetListView — 페이지네이션 없음
- **파일**: `services/validation/api/views.py:536`
- **심각도**: LOW | **수정난이도**: 중간
- **설명**: `PeerPreset.objects.filter(...).order_by("preset_key")` 전건 루프. 현재 프리셋 수는 적으나 확장성 대비 검토.

### [L8] ChainSight SignalFeedView / NeighborGraphView — 수동 슬라이싱
- **파일**: `apps/chain_sight/api/views.py:736-934`(SignalFeed), `532-733`(Neighbor)
- **심각도**: LOW | **수정난이도**: 쉬움
- **설명**: 메모리에서 `chains[start:end]` / `neighbors[:limit]` 수동 슬라이싱. 기능상 문제 없으나 표준 `pagination_class`로 일관화 시 메모리 효율 개선.

---

## 양호 확인 (조치 불필요)

| 항목 | 파일:라인 | 상태 |
|------|-----------|------|
| NewsViewSet 리스트 | `services/news/api/views.py:68-73` | `pagination_class=NewsArticlePagination`(page_size 20/max 100) 적용됨 |
| WatchlistListCreateView | `packages/shared/users/views.py:622-655` | 수동 페이지네이션(최대 100) 적용됨 |
| WatchlistStocksView | `packages/shared/users/views.py:860-904` | 수동 페이지네이션 적용됨 |
| Portfolio 쿼리 | `packages/shared/users/models.py:88-94` | `(user, stock)` 인덱스 보유 — 양호 |
| graph_analysis CorrelationEdge | `services/_dormant/graph_analysis/models.py:133` | 복합 인덱스 보유 — 양호(휴면) |

---

## 권장 조치 우선순위

**1단계 (즉시, 영향 큼·난이도 낮음)**
- [H3][H4] Portfolio 프로퍼티 루프 → DB 집계/단일 순회 (쉬움)
- [H1] OverviewTab select_related/prefetch_related 6종 추가 (높음이나 효과 큼)
- [M2] AlertHistory `select_related("alert")` (쉬움)
- [M1] AnalysisSession `select_related/prefetch_related` (쉬움)

**2단계 (높음)**
- [H5] news trending 일괄 조회, [H7] ChainSightGraph 엣지 일괄 조회, [H6] validation peers 슬라이싱
- [H2] WatchList 최신가격 prefetch, [S1] get_chart_data 정리
- [H9] Users 목록 페이지네이션

**3단계 (중간)**
- [H8][M5][M6][M8] 인덱스 보강 (마이그레이션 동반)
- [M9] MarketMover serializer 사전계산
- [M10][M11][M12] 다건 엔드포인트 페이지네이션

**4단계 (낮음)**
- [L1~L8] 보조 인덱스/UX 확장/코드 품질

---

> 본 보고서는 정적 분석 결과이며, 실제 쿼리 수는 `django-debug-toolbar` 또는 `assertNumQueries` 로 재현 검증을 권장합니다. 특히 [H6] peers 슬라이싱은 런타임 동작 확인이 필요합니다.
