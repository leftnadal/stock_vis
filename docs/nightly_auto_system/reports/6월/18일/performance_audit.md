# API 성능 감사 보고서

- **작성일**: 2026-06-18
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상 코드베이스**: `/Users/byeongjinjeong/stock-vis-nightly/repo` (모노레포 nightly 미러)
- **분석 방식**: 정적 코드 분석 (라인 단위). 런타임 쿼리 카운트로 검증되지 않은 항목은 "신뢰도" 칼럼에 *추정*으로 표기함.

> ⚠️ 경로 매핑 주의: 지시서의 `stocks/*`, `users/*`, `macro/*`, `news/api/*` 등은 이 repo에서 각각 `packages/shared/stocks/*`, `packages/shared/users/*`, `apps/market_pulse/*`(=macro/Market Pulse), `services/news/api/*` 로 매핑됨. 지시서 원본 경로(`/Users/byeongjinjeong/Desktop/stock_vis`)는 macOS TCC 권한 정책으로 접근 불가하여, 동일 프로젝트의 nightly 미러를 감사 대상으로 사용함.

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 쿼리 | 페이지네이션 누락 | 느린 Serializer | 인덱스 누락 | 합계 |
|--------|:--:|:--:|:--:|:--:|:--:|
| **HIGH** | 3 | 2 | 2 | 0 | **7** |
| **MED**  | 4 | 1 | 0 | 2 | **7** |
| **LOW**  | 0 | 0 | 0 | 3 | **3** |
| **합계** | 7 | 3 | 2 | 5 | **17** |

> 느린 Serializer 2건(HIGH)은 N+1 쿼리와 동일 원인(SerializerMethodField 내 추가 쿼리)으로, 아래 상세에서는 N+1 섹션에 통합 기술함. 따라서 고유 이슈 수는 **15건**.

### 우선순위 Top 5 (즉시 수정 권장)

| # | 위치 | 유형 | 심각도 | 난이도 |
|---|------|------|:--:|:--:|
| 1 | `packages/shared/stocks/serializers.py` WatchListStockSerializer | N+1 (Serializer) | HIGH | 중간 |
| 2 | `packages/shared/stocks/serializers.py` OverviewTabSerializer | N+1 (Serializer) | HIGH | 높음 |
| 3 | `packages/shared/stocks/views_indicators.py:371-388` | N+1 (루프 내 get) | HIGH | 중간 |
| 4 | `packages/shared/users/views.py:92-95` | 페이지네이션 누락 | HIGH | 쉬움 |
| 5 | `services/serverless/views_admin.py:502-531` | N+1 + 페이지네이션 누락 | HIGH | 중간 |

---

## 상세

### A. N+1 쿼리 / 느린 Serializer

#### A-1. WatchListStockSerializer — `many=True` 직렬화 시 종목당 가격 쿼리
- **위치**: `packages/shared/stocks/serializers.py:451-461` (`get_latest_price`, `get_chart_data`)
- **심각도**: HIGH · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: Watchlist 항목을 `many=True`로 직렬화할 때 각 Stock마다 아래 쿼리가 SerializerMethodField에서 개별 실행됨.
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by("-date").first()   # 종목당 1쿼리
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by("-date")[:7] # 종목당 1쿼리
  ```
  관심종목 N개 → 최소 2N개 추가 쿼리.
- **권장 수정**: 뷰에서 `Prefetch`로 최신 가격을 미리 적재하거나, 최신 가격을 별도 캐시/`latest_price` 컬럼으로 비정규화. 차트용 7일치는 종목 전체에 대해 한 번의 `DailyPrice.objects.filter(stock__in=...)` 후 메모리 그룹핑.

#### A-2. OverviewTabSerializer — 다중 OneToOne/역참조를 SerializerMethodField로 접근
- **위치**: `packages/shared/stocks/serializers.py:226-353` (`get_korean_overview`, `get_dynamic_layers` 등). 파일 내 라인 543-544에 `TODO: prefetch_related` 주석 존재.
- **심각도**: HIGH · **난이도**: 높음 · **신뢰도**: 확정
- **설명**: `overview_ko`, `validation_news_summary`, `sensitivity_profile`, `category_signals.all()` 등 다수의 관련 객체를 메서드 필드에서 직접 접근. 단건 상세 응답이라 N+1 폭은 작으나, 한 응답에 6~8개 추가 쿼리가 누적됨.
- **권장 수정**: 뷰의 Stock 조회 시
  ```python
  Stock.objects.select_related(
      "overview_ko", "validation_news_summary", "sensitivity_profile",
      "growth_stage", "capital_dna", "narrative_tag",
  ).prefetch_related("category_signals").get(symbol=symbol)
  ```

#### A-3. IndicatorComparison/Multi-symbol 뷰 — 루프 내 `Stock.objects.get()`
- **위치**: `packages/shared/stocks/views_indicators.py:371-388`
- **심각도**: HIGH · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: 다중 심볼 비교 시 심볼 리스트를 순회하며 종목당 `Stock.objects.get()` + `DailyPrice.objects.filter(...)`를 개별 실행.
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol.upper())       # 심볼당 1쿼리
      prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:50]  # 심볼당 1쿼리
  ```
- **권장 수정**: `Stock.objects.filter(symbol__in=symbols_upper)`로 한 번에 dict 적재 후 매핑. 가격도 `stock__in` IN 쿼리로 일괄 조회.

#### A-4. AdminNewsCategoryView — 카테고리 루프 내 `resolve_symbols()`
- **위치**: `services/serverless/views_admin.py:502-531`
- **심각도**: HIGH · **난이도**: 중간 · **신뢰도**: *추정* (`resolve_symbols()`가 내부에서 DB 쿼리를 발생시키는지는 메서드 구현 확인 필요)
- **설명**: `NewsCollectionCategory.objects.all()`을 페이지네이션 없이 순회하며 카테고리마다 `cat.resolve_symbols()` 호출. 메서드가 쿼리를 유발하면 카테고리 수만큼 N+1. (페이지네이션 누락도 동반 — B-2 참조)
- **권장 수정**: `resolve_symbols()` 구현 확인 → 쿼리 유발 시 bulk 조회로 전환. 목록에 페이지네이션 적용.

#### A-5. news `trending` 액션 — 집계 후 종목별 최근 기사 추가 쿼리
- **위치**: `services/news/api/views.py:360-396`
- **심각도**: MED · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: 트렌딩 심볼 집계(`values().annotate()`) 후, 결과 심볼마다 `NewsArticle.objects.filter(entities__symbol=symbol...)[:3]`를 루프에서 실행 → O(limit) 추가 쿼리. (300초 캐시로 완화되나 캐시 미스 시 부하)
- **권장 수정**: 단일 쿼리로 상위 심볼들의 최근 기사를 한 번에 가져온 뒤 메모리에서 심볼별 3건 슬라이싱.

#### A-6. ValidationMetricsView `_build_metric` — 메트릭×연도 중첩 쿼리
- **위치**: `services/validation/api/views.py:276-401`
- **심각도**: MED · **난이도**: 높음 · **신뢰도**: 확정
- **설명**: `_build_category()`가 메트릭 코드 수만큼 `_build_metric()` 호출, 그 안에서 `CompanyMetricSnapshot`(최신·이력) + 이력 루프 내 `PeerMetricBenchmark.first()` 호출 → 대략 O(M × N) 쿼리 (M=메트릭, N=연도).
- **권장 수정**: 종목 단위로 `CompanyMetricSnapshot`/`PeerMetricBenchmark`를 한 번에 적재(`select_related('metric_code')` 포함) 후 메모리에서 매칭.

#### A-7. LeaderComparisonView — 메트릭 루프 내 정의+스냅샷 3쿼리
- **위치**: `services/validation/api/views.py:459-505`
- **심각도**: MED · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: 메트릭 루프마다 `MetricDefinition.filter(pk=mc).first()` + 자사 스냅샷 + 리더 스냅샷 = O(메트릭×3) 쿼리.
- **권장 수정**: `MetricDefinition.objects.filter(pk__in=[...])` 일괄 적재, 스냅샷도 `fiscal_year=latest_fy` 조건으로 자사·리더분을 IN 쿼리로 한 번에 적재 후 메모리 필터링.

#### A-8. PortfolioDetailView — `select_related("stock")` 누락
- **위치**: `packages/shared/users/views.py:320-325` (`get_object`)
- **심각도**: MED · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: `Portfolio.objects.get(pk=pk, user=user)` 후 직렬화 단계에서 `stock.symbol/stock_name/real_time_price` 등 FK 접근으로 추가 쿼리. (단건이라 폭은 제한적)
- **권장 수정**: `Portfolio.objects.select_related("stock").get(pk=pk, user=user)`. 목록 직렬화 경로가 있다면 동일하게 `select_related("stock")` 적용.

#### A-9. StockCompleteDataAPIView — 재무제표 3개 쿼리 분리 실행 (다중 쿼리)
- **위치**: `packages/shared/stocks/views.py:937-950`
- **심각도**: MED · **난이도**: 중간 · **신뢰도**: 확정
- **설명**: BalanceSheet / IncomeStatement / CashFlowStatement를 각각 별도 쿼리로 순차 조회. 엄밀히 N+1은 아니나 단건 응답에 동기 쿼리 3회 누적.
- **권장 수정**: Stock 조회 시 `Prefetch`로 각 재무제표(annual, 최근 5년)를 함께 적재.

> **오탐 정정**: `views_eod.py:81-104`(EOD 신호 목록)은 이미 `select_related("stock")`가 적용되어 있어 루프 내 `s.stock.stock_name` 접근이 N+1을 유발하지 않음 — **이슈 아님**.

---

### B. 페이지네이션 누락

#### B-1. 사용자 목록 — 전체 queryset 직렬화
- **위치**: `packages/shared/users/views.py:92-95`
- **심각도**: HIGH · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: `User.objects.all()`을 `UserSerializer(many=True)`로 페이지네이션 없이 직렬화. 사용자 증가 시 응답 크기·메모리 선형 증가.
- **권장 수정**: `pagination_class` 지정(예: `PageNumberPagination`) 또는 limit 파라미터 도입.

#### B-2. AdminNewsCategoryView — 전체 카테고리 직렬화
- **위치**: `services/serverless/views_admin.py:502-531`
- **심각도**: HIGH · **난이도**: 중간 · **신뢰도**: 확정 (목록 페이지네이션 부재) / 동반 N+1은 A-4 참조
- **설명**: `NewsCollectionCategory.objects.all()`을 페이지네이션 없이 전부 반환.
- **권장 수정**: 페이지네이션 적용(목록 규모가 작으면 LOW로 강등 가능 — 카테고리 총량 확인 권장).

#### B-3. news `all_news` — 캐시 키에 offset 포함으로 캐시 효율 저하
- **위치**: `services/news/api/views.py:398-486`
- **심각도**: MED · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: 수동 `offset:offset+limit` 슬라이스로 페이지네이션은 동작하나, 캐시 키에 offset이 포함되어 페이지마다 캐시가 분리됨(히트율 저하).
- **권장 수정**: DRF `CursorPagination`/`PageNumberPagination`으로 표준화하고 캐시 키 설계 재검토.

> **참고(이슈 아님)**: `rag_analysis/views.py:762-822`(UsageHistory)는 Django `Paginator` 사용, `rag_analysis/views.py:50-54`(DataBasket 목록)는 `prefetch_related("items")` 적용으로 기본 방어됨. 단, DataBasket의 nested FK(예: `items.stock`)는 `Prefetch(queryset=BasketItem.objects.select_related("stock"))`로 보강 시 추가 쿼리 제거 가능(MED 후보, 신뢰도 *추정*).

---

### C. 인덱스 누락

> ForeignKey 필드는 Django가 기본 인덱스를 자동 생성하므로 제외함. `unique=True`/`unique_together`/`Meta.indexes`로 이미 커버되는 필드도 제외.

#### C-1. Stock — `sector` + `industry` 복합 인덱스 부재
- **위치**: `packages/shared/stocks/models.py:27-28` (필드), 인덱스 정의 `:155-162`
- **심각도**: MED · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: `sector`, `industry` 각각의 단일 인덱스는 존재하나, 둘을 함께 거는 조회(스크리너/EOD 계산기 등 sector+industry 동시 필터)는 복합 인덱스가 없어 한쪽 인덱스만 활용됨. (단, `views.py:122`의 `sector__icontains`는 인덱스 활용이 제한적인 패턴임에 유의)
- **권장 수정**: `Meta.indexes`에 `models.Index(fields=["sector", "industry"])` 추가.

#### C-2. MarketMover — `rank` 정렬 인덱스 부재
- **위치**: `services/serverless/models.py:20` (필드), 인덱스 정의 `:102-105`, `Meta.ordering`에 rank 포함
- **심각도**: MED · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: Top-N 조회가 `date`+`mover_type` 필터 후 `rank` 정렬로 이뤄지나, 기존 인덱스에 rank가 없어 정렬 단계에서 비용 발생.
- **권장 수정**: `models.Index(fields=["date", "mover_type", "rank"])` 추가(쿼리 패턴에 정합).

#### C-3. DailyPrice — `volume` 단일 필터 인덱스 부재
- **위치**: `packages/shared/stocks/models.py:208` (필드), 복합 인덱스 `("date","volume")` `:249`
- **심각도**: LOW · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: `("date","volume")` 복합 인덱스는 있으나 volume 단독 필터/정렬에는 선두 컬럼(date)이 없어 활용 제한. 현재 volume 단독 필터 빈도는 낮음.
- **권장 수정**: volume 단독 필터가 실제로 빈번할 때만 단일 인덱스 추가(현재는 선택적).

#### C-4. NewsArticle — `category` 단일 필터 인덱스 부재
- **위치**: `services/news/models.py:56` (필드), 인덱스 `("-published_at","category")` `:144-150`
- **심각도**: LOW · **난이도**: 쉬움 · **신뢰도**: 확정
- **설명**: `news_classifier.py:339/345`에서 `filter(category=...)` 단독 사용. 기존 복합 인덱스의 선두 컬럼은 `-published_at`이라 category 단독 필터에는 부분 활용.
- **권장 수정**: category 단독 집계가 빈번하면 `models.Index(fields=["category"])` 추가(선택적).

#### C-5. (정정) ScreenerPreset / Portfolio 등 `user` 단독 인덱스
- **위치**: `services/serverless/models.py:351` 등
- **심각도**: LOW · **난이도**: 쉬움 · **신뢰도**: 확정 — **권장하지 않음**
- **설명**: 보조 분석에서 "user FK 인덱스 추가" 제안이 있었으나, **`user`는 ForeignKey이므로 Django가 이미 인덱스를 자동 생성**함. 별도 단일 인덱스 추가는 중복이므로 불필요. (복합 인덱스 `("user","use_count")` 등은 별개 목적으로 유효)

> **검증 완료(이슈 아님)**: `users/models.py`(Portfolio/Watchlist/WatchlistItem/UserInterest), `graph_analysis/models.py`(상관관계 모델 일체), `sec_pipeline` `SupplyChainEvidence.neo4j_dirty`(이미 `:123` 단일 인덱스 존재), `rag_analysis.UsageLog`(`cached`+`created_at` 복합 인덱스 존재)는 주요 쿼리 패턴이 인덱스로 커버됨.

---

## 한계 및 후속 권장

- 본 감사는 **정적 분석**이며 실제 쿼리 수는 `django-debug-toolbar` 또는 `CaptureQueriesContext`로 검증해야 함. *추정* 표기 항목(A-4, B-3 nested prefetch)은 메서드 구현/런타임 확인 후 심각도 확정 권장.
- 외부 API 의존 뷰(`views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`, `views_exchange.py`, `apps/market_pulse/views.py`, `apps/chain_sight/api/views.py`[Neo4j 직접 쿼리])는 ORM N+1 관점에서 **이슈 없음**으로 확인됨.
- 권장 수정 적용 시 우선순위: **A-1 → A-3 → B-1 → A-4/B-2 → A-2** (사용 빈도·N+1 폭 기준).
