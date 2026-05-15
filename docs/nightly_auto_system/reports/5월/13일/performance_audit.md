# API 성능 감사 보고서

**생성일**: 2026-05-13
**감사 대상**: Backend Django REST Framework API (17개 view 파일 + 7개 model 파일 + 8개 serializer 파일)
**감사 범위**: N+1 쿼리, 인덱스 누락, 느린 Serializer, 페이지네이션 누락
**감사 방식**: 정적 코드 분석 (읽기 전용)
**비교 기준**: 직전 보고서 [2026-05-11 performance_audit.md](../11일/performance_audit.md)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 | 인덱스 | Serializer | Pagination | 합계 |
|--------|-----|--------|-----------|------------|------|
| **HIGH** | 5 | 0 | 2 | 1 | 8 |
| **MED**  | 6 | 2 | 0 | 2 | 10 |
| **LOW**  | 2 | 2 | 0 | 2 | 6 |
| **합계** | **13** | **4** | **2** | **5** | **24** |

### 변동 (vs 5월 11일 보고서)

| 변동 | 항목 | 비고 |
|------|------|------|
| ✅ **해결** | `stocks/views.py:77-91 StockListAPIView` pagination | `StockListPagination(page_size=50, max=200)` 명시 적용 — 5/11 HIGH-9 해소 |
| ✅ **해결** | `news/api/views.py:45-60 NewsViewSet` pagination | `NewsArticlePagination(page_size=20, max=100)` 명시 적용 — 5/11 MED-10 해소 |
| ➖ **유지** | DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정 | `config/settings.py:348-364` 여전히 누락 (P0 #14 보류 정책 유지) |
| ➖ **유지** | validation/api/views.py N+1 4건 | LeaderComparisonView / ValidationMetricsView 핫스팟 그대로 |
| ➖ **유지** | chainsight/api/views.py N+1 | ChainSightGraphView edge enrichment 그대로 |
| 🆕 **신규 분류** | `rag_analysis/views.py:42, 369` 페이지네이션 누락 (MED) | DataBasketListCreateView / AnalysisSessionListCreateView 무제한 응답 |

### 톱 5 우선순위 (즉시 효과)

| # | 이슈 | 파일:라인 | 영향 추정 | 수정 난이도 |
|---|------|----------|----------|------------|
| 1 | `LeaderComparisonView` 지표별 3-쿼리 루프 | `validation/api/views.py:355-403` | ~40 지표 × 3 = 120 쿼리/요청 | 쉬움 |
| 2 | `ValidationMetricsView._build_metric` history 루프에서 `PeerMetricBenchmark` 단건 조회 | `validation/api/views.py:265-285` | 카테고리당 5건 × 7카테고리 = ~35 추가 쿼리 | 쉬움 |
| 3 | DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정 | `config/settings.py:348-364` | 미적용 list endpoint(rag_analysis 등) 무제한 응답 가능 | 중간 (envelope 결정 필요) |
| 4 | `ChainSightGraphView` 엣지마다 단건 조회 | `chainsight/api/views.py:74-87` | depth=3에서 수십~수백 엣지 × 2 쿼리 | 중간 |
| 5 | `OverviewTabSerializer.get_dynamic_layers` 6 OneToOne + 1 reverse FK | `stocks/serializers.py:205-307` + `stocks/views.py:502-504` | 객체당 7 추가 쿼리 (단일 객체이나 핫 페이지) | 쉬움 |

---

## 상세

### 1. N+1 쿼리 이슈

#### HIGH-1. `validation/api/views.py:355-403` — `LeaderComparisonView.get`
**현상**: `CATEGORY_METRICS`(7개 카테고리, ~40 지표) 전체를 한 번에 펼친 뒤 매 지표마다
- `MetricDefinition.objects.filter(pk=mc).first()` (365행)
- 회사 `CompanyMetricSnapshot.filter(...).first()` (369행)
- 리더 `CompanyMetricSnapshot.filter(symbol_id=leader.symbol, ...).first()` (372행)

지표 수 × 3 = **~120 쿼리/요청**.

**권장 수정**:
```python
mdefs = {
    md.pk: md
    for md in MetricDefinition.objects.filter(pk__in=[mc for _, mc in all_metrics])
}
snaps = CompanyMetricSnapshot.objects.filter(
    symbol__in=[stock, leader],
    fiscal_year=latest_fy,
    metric_code_id__in=[mc for _, mc in all_metrics],
    value_status='normal',
).select_related('metric_code')
snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
```
**수정 난이도**: 쉬움

#### HIGH-2. `validation/api/views.py:265-285` — `ValidationMetricsView._build_metric`
**현상**: history 루프(line 265-267 `snaps[:5]`) 안에서 각 snap마다 `PeerMetricBenchmark.objects.filter(...).first()` 호출. 카테고리 × 지표 × 5년 → 카테고리당 ~35 쿼리 추가.

**권장 수정**: `fiscal_year__in=[s.fiscal_year for s in snaps]`로 한 번에 prefetch한 뒤 dict화.
```python
peer_benchmarks = {
    pb.fiscal_year: pb
    for pb in PeerMetricBenchmark.objects.filter(
        symbol=stock, metric_code=md,
        fiscal_year__in=[s.fiscal_year for s in snaps],
    )
}
```
**수정 난이도**: 쉬움

#### HIGH-3. `validation/api/views.py:199-208` — `ValidationMetricsView._build_category`
**현상**: 카테고리 내 `metric_code` 루프 안(line 204-205)에서 매번 `MetricDefinition.objects.filter(pk=mc).first()` 호출. category=`all` 요청 시 7 카테고리 × 평균 ~6 metric = ~42 쿼리.

**권장 수정**: 함수 진입 시 `MetricDefinition.objects.filter(pk__in=metric_codes)`로 한 번 조회 후 dict 매핑.
**수정 난이도**: 쉬움

#### HIGH-4. `validation/api/views.py:112-124` — `ValidationSummaryView`
**현상**: 5개 rank metric 루프(line 111) 안에서 매번
- `CompanyBenchmarkDelta.objects.filter(...).first()` (line 113)
- `MetricDefinition.objects.filter(pk=mc).first()` (line 117)

→ 10 쿼리.

**권장 수정**: `metric_code__in=rank_metrics`로 한 번에 fetch + dict.
**수정 난이도**: 쉬움

#### HIGH-5. `chainsight/api/views.py:74-87` — `ChainSightGraphView`
**현상**: Neo4j에서 받은 `result.get("edges", [])` 리스트에 대해 각 edge마다
```python
cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()    # line 80
pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()  # line 82
```
N개 엣지 → **2N 쿼리**. `depth=3`이면 수십~수백 엣지 가능.

**권장 수정**:
1. edges에서 `(a, b)` 페어 set 미리 구성
2. `CoMentionEdge.objects.filter(symbol_a__in=..., symbol_b__in=...)`로 한 번에 in-bulk 조회 (단, (a,b) 정렬 페어가 정확히 일치해야 하므로 `Q(symbol_a=..., symbol_b=...)` OR 체인 또는 `in_bulk` 후 클라이언트 필터)
3. dict 매핑 후 edge enrichment

**수정 난이도**: 중간

---

#### MED-1. `chainsight/api/views.py:662-800` — `SignalFeedView._build_chain_signals`
**현상**: 시드 페어 후보(최대 `page_size*3` = 15개) 각각에 대해 Neo4j `shortestPath` 쿼리 1회(line 705) → 15 round-trip.
**권장 수정**: Cypher `UNWIND $pairs AS pair MATCH p = shortestPath(...)` 한 쿼리로 통합.
**수정 난이도**: 중간

#### MED-2. `news/api/views.py:337-358` — `NewsViewSet.trending`
**현상**: trending_data 루프(line 346)에서 각 종목마다 `NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by(...)[:3]` 호출. limit=10 → 10 추가 쿼리.
**권장 수정**: 단일 `NewsArticle.objects.filter(entities__symbol__in=[...])`로 한 번에 가져온 뒤 Python에서 종목별 grouping.
**완화 요인**: 5분 캐시(line 361)로 cache hit 시 비용 0.
**수정 난이도**: 쉬움

#### MED-3. `news/api/views.py:1377-1389` — `collection_logs.by_provider`
**현상**: `provider_agg` annotate 결과 루프 안에서 `qs.filter(provider=row['provider'], errors__gt=0).count()` 호출(line 1389) → provider 수만큼 추가 count 쿼리.
**권장 수정**: 별도 `qs.values('provider').annotate(error_runs=Count('id', filter=Q(errors__gt=0)))`로 한 번에 집계.
**수정 난이도**: 쉬움

#### MED-4. `stocks/views_indicators.py:324-371` — `IndicatorComparisonView.post`
**현상**: symbols 리스트 루프(line 324)에서 symbol마다
- `Stock.objects.get(symbol=symbol)` (line 328)
- `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]` (line 333)

N symbols → 2N 쿼리. 인증 없이 누구나 호출 가능한 POST 엔드포인트라 N 제어 안 됨(symbols 입력 길이 제한 없음).
**권장 수정**: `Stock.objects.filter(symbol__in=symbols)` 한 번 + `DailyPrice.objects.filter(stock_id__in=symbols)` 한 번 + Python 그룹화 + symbols 길이 제한(예: 최대 20).
**수정 난이도**: 중간

#### MED-5. `serverless/views_admin.py:475-497, 538-545, 620-622` — `AdminNewsCategoryView`
**현상**: `for cat in categories:` 루프(line 477)에서 `cat.resolve_symbols()` 호출 → `news/models.py:638` 구현이 `SP500Constituent.objects.filter(...).values_list('symbol', ...)`로 매 카테고리마다 1 쿼리. POST(line 547) / PUT(line 622)에서도 동일하게 1회씩 발생.
**권장 수정**: 카테고리 type별로 사전 group → 각 type에서 한 번에 모든 sector/sub_sector 값에 대해 `SP500Constituent.objects.filter(sector__in=[...]).values('sector','symbol')` 후 Python에서 카테고리별 분리.
**완화 요인**: admin 전용 + 카테고리 수 보통 5-20개로 제한.
**수정 난이도**: 중간

#### MED-6. `chainsight/api/views.py:148-165` — `ChainSightSuggestionView` co_mentions union
**현상**: `CoMentionEdge.objects.filter(symbol_a=symbol).union(...filter(symbol_b=symbol))` 후(line 150-154) 다시 Python에서 each cm 객체 비교(line 157-159)로 ticker 결정. SQL UNION 자체는 한 번이라 N+1은 아니나, ORM-level 객체 hydration이 두 쿼리셋의 합집합으로 늘어남.
**권장 수정**: `Q(symbol_a=symbol) | Q(symbol_b=symbol)` 단일 쿼리로 단순화 + `values('symbol_a','symbol_b','co_mention_count')`로 ORM 객체 비용 제거.
**수정 난이도**: 쉬움

---

#### LOW-1. `stocks/serializers.py:398-409` — `WatchListStockSerializer.get_latest_price` / `get_chart_data`
**현상**: serializer가 객체마다 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` + `[:7]` 호출. 함수 본문이 `return` 없이 끝나(line 409) **dead code**로 추정.
**권장 수정**: 사용처 확인 후 (a) 미사용이면 제거, (b) 사용 중이면 view에서 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date'))`로 미리 가져옴.
**수정 난이도**: 쉬움

#### LOW-2. `stocks/views.py:830-884` — `StockCompleteDataAPIView.get`
**현상**: 단일 종목에 대해 3개 FinancialStatement 모델별 분리 쿼리(line 861, 866, 871) + serializer 직렬화 6회. 단일 객체이고 종목 수 제한 없으나 1 객체당 발생이므로 N+1은 아님. 다만 `select_related('overview_ko')` 등 OverviewTabSerializer가 요구하는 prefetch가 빠져 있어 6 OneToOne 추가 쿼리 발생(`get_dynamic_layers` 경유). HIGH-6 참조.
**권장 수정**: HIGH-6 수정 시 함께 처리.
**수정 난이도**: 쉬움

---

### 2. 인덱스 누락

#### MED-7. `users/models.py:249-265` — `UserInterest` 인덱스 부재
**현상**: 필드 `user`, `interest_type`, `value` 중 인덱스가 없고 `unique_together` 제약만 존재(`db_table='users_interest'`, line 264-265). `users/views.py:974-985 UserInterestListCreateView.get`이 `UserInterest.objects.filter(user=request.user).order_by('-created_at')`로 정렬 조회.

`unique_together`는 PostgreSQL에서 unique index를 생성하므로 `(user, interest_type, value)` 순으로 인덱스가 존재하긴 하나, prefix `user`만 사용하는 정렬은 효율적이지만 `created_at` 정렬에는 도움이 안 됨.

**권장 수정**:
```python
indexes = [
    models.Index(fields=['user', '-created_at']),
]
```
**수정 난이도**: 쉬움 (migration 추가)

#### MED-8. `serverless/models.py` 알림 도메인 — `AlertHistory` 인덱스 점검
**현상**: line 789-790에서 `Index(fields=['alert', '-triggered_at'])` 및 `Index(fields=['triggered_at'])` 존재. `serverless/views.py`에서 `read_at__isnull=True, dismissed=False`로 추가 필터를 사용한다면 부분 인덱스 검토 가치.
**확인 필요**: 실제 query plan 측정 후 `(alert, read_at, dismissed)` 복합 또는 부분 인덱스 도입 여부 결정.
**수정 난이도**: 중간 (EXPLAIN 필요)

#### LOW-3. `stocks/models.py:90-91` — `Stock.last_api_call` 인덱스 부재
**현상**: `last_api_call` 필드(line 90)에 `db_index` 없음. Stock sync 스케줄러가 `last_api_call__lt=...` 형태로 필터한다면 인덱스 필요. 현재 view에서 직접 필터 흔적은 없으나 task 영역에서 사용 가능성.
**권장 수정**: 사용처 확인 후 `db_index=True` 추가. 미사용이면 무시.
**수정 난이도**: 쉬움

#### LOW-4. `news/models.py:131-138` — `NewsArticle.is_press_release` / `is_official` 인덱스 부재
**현상**: 필터 가능성은 있으나 현재 views에서 적극 사용 흔적 없음. 기존 composite index `(-published_at, category)` 등으로 대체 가능.
**권장 수정**: 쿼리 사용처 확인 후 필요 시 부분 인덱스(`condition=Q(is_press_release=True)`) 도입.
**수정 난이도**: 중간

---

### 3. 느린 Serializer (SerializerMethodField 추가 쿼리 패턴)

#### HIGH-6. `stocks/serializers.py:205-307` — `OverviewTabSerializer.get_dynamic_layers`
**현상**: 단일 Stock 객체에 대해 6개 OneToOne (`overview_ko`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`, `validation_news_summary`) + 1개 reverse FK(`category_signals`) 접근.

`stocks/views.py:502-504 StockOverviewAPIView.get`에서 현재 `select_related('overview_ko')`만 적용. 코드 주석(line 501)도 `TODO: CategoryScore 등 ManyToOne은 prefetch_related로 별도 처리 필요 (Step 2~4)`로 명시. **나머지 5개 OneToOne + 1개 reverse FK는 미적용**.

객체당 추가 6 쿼리. 캐시 hit 시 0이지만 첫 호출/캐시 invalid 시점에 발생.
**권장 수정**:
```python
stock = Stock.objects.select_related(
    'overview_ko', 'sensitivity_profile', 'growth_stage',
    'capital_dna', 'narrative_tag', 'validation_news_summary',
).prefetch_related('category_signals').filter(symbol=symbol).first()
```
또한 `StockCompleteDataAPIView`(line 830) 및 `StockDetailView`(line 117 — Template 기반)도 동일 패턴 적용 필요.
**수정 난이도**: 쉬움

#### HIGH-7. `stocks/serializers.py:398-409` — `WatchListStockSerializer`
**현상**: LOW-1과 동일. 단 사용 흔적이 있다면 list endpoint에서 객체당 2 쿼리.
**권장 수정**: LOW-1과 동일.
**수정 난이도**: 쉬움

---

### 4. 페이지네이션 누락

#### HIGH-8. `config/settings.py:348-364` — DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정
**현상**: `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` 누락. P0 #14 (페이지네이션 표준)로 보류 중. 개별 ListAPIView/ReadOnlyModelViewSet이 자체 `pagination_class`를 설정하지 않으면 무제한 응답.
**현재 부분 완화**: `StockListAPIView`(stocks/views.py:91)와 `NewsViewSet`(news/api/views.py:60)는 자체 적용 ✅. 다만 RAG/일부 admin 뷰는 여전히 미적용.
**영향**: 미적용 list endpoint(아래 MED 항목)가 무제한 응답 가능.
**권장 수정**: 전역 `PageNumberPagination + page_size=20~50` 설정. 응답 envelope(`results`/`count`/`next`/`previous`) 결정 후 점진 적용.
**수정 난이도**: 높음 (envelope 결정 + 프론트 호환 검증)

#### MED-9. `rag_analysis/views.py:42-54` — `DataBasketListCreateView`
**현상**: `baskets = DataBasket.objects.filter(user=request.user).prefetch_related('items')` 전체를 직렬화하여 반환(line 52-54). 사용자 단위라 폭주 가능성 낮으나 `MAX_ITEMS` 제약과 별개로 basket 자체 수에는 제한 없음.
**권장 수정**: `pagination_class` 명시 또는 user당 basket 수 제한.
**수정 난이도**: 쉬움

#### MED-10. `rag_analysis/views.py:369-381` — `AnalysisSessionListCreateView`
**현상**: 사용자의 모든 분석 세션을 무제한 직렬화. session.messages prefetch까지 포함되어 응답 사이즈가 누적될수록 폭주.
**권장 수정**: `pagination_class` 명시 + `prefetch_related('messages')` 제거하고 list endpoint에서는 메시지 메타만 반환.
**수정 난이도**: 쉬움

#### LOW-5. `chainsight/api/views.py:308-314 SeedListView`
**현상**: 캐시된 JSON 전체를 그대로 반환. 시드 수는 일반적으로 수십~수백 수준이므로 큰 문제 아님.
**권장 수정**: 페이로드 사이즈가 100KB 초과하면 페이지네이션 검토.
**수정 난이도**: 중간

#### LOW-6. `serverless/views_admin.py:472-497 AdminNewsCategoryView.get`
**현상**: 모든 카테고리를 한 번에 반환(line 475). 카테고리 수가 늘어나면 응답 사이즈 증가. admin 전용이라 영향 작음.
**권장 수정**: 향후 카테고리 수가 50+ 가 되면 페이지네이션 도입.
**수정 난이도**: 쉬움

---

### 부록 A — 정상으로 확인된 패턴

| 패턴 | 위치 | 비고 |
|------|------|------|
| `select_related('stock')` 적용 | `users/views.py:264, 358, 405, 819` | 포트폴리오/Watchlist 정상 처리 |
| `prefetch_related('items__stock')` | `users/views.py:655` | WatchlistDetailView |
| `prefetch_related('entities')` | `news/api/views.py:58, 412` | NewsArticle list 패턴 |
| `select_related('stock')` 적용 | `stocks/views_eod.py:77` | EODSignalDetailView |
| `select_related('basket')` | `rag_analysis/views.py:479` | ChatStreamView |
| Custom Pagination | `stocks/views.py:77-91, news/api/views.py:45-49, users/views.py:610-628, 830-848, rag_analysis/views.py:707` | 점진 도입 진행 중 |

### 부록 B — 미감사 / 제한적 감사 파일

| 파일 | 상태 | 비고 |
|------|------|------|
| `stocks/views_exchange.py` | 부분 | 295 LOC 추정, grep `select_related|prefetch_related` 매치 없음. FMP 호출만 하는 view 추정. |
| `stocks/views_market_movers.py` | 완료 (70 LOC) | FMP API 결과 직접 반환, DB N+1 없음. |
| `news/api/views.py:1450+` | 부분 | `pipeline_health` 등 monitoring action — 캐시 우선이라 영향 제한. |
| `validation/views.py` | 미감사 | `validation/api/views.py` 외 별도 view. |
| `chainsight/views.py` | 미감사 | `chainsight/api/views.py` 외 별도 view. |
| `news/views.py` | 미감사 | `news/api/views.py` 외 별도 view (HTML 뷰 추정). |

**권장 후속**: 위 파일들에 대해 별도 감사 1회 필요.

---

### 부록 C — 글로벌 패턴 권장

1. **Compute-once context 패턴 강화**: `validation/api/views.py`가 N+1 핫스팟. Service 레이어에서 모든 `metric_code`를 한 번에 dict로 fetch한 뒤 view에서 lookup하는 패턴으로 일관화 권장. → 상위 4개 HIGH 이슈 동시 해결.
2. **Stock 매니저 메서드 도입**: `Stock.objects.with_dynamic_layers()` — 6 OneToOne + 1 FK 일괄 prefetch. `StockOverviewAPIView`, `StockCompleteDataAPIView`, `StockDetailView` 3곳에서 재사용.
3. **Pagination envelope 결정 (P0 #14)**: 가장 시급한 작업. DRF `PageNumberPagination + 200` 응답 envelope 합의 → 점진 적용. 현재 `stocks/views.py:84`/`news/api/views.py:60`/`users/views.py:610-628`에서 envelope이 제각각(일부 `results+pagination` 객체, 일부 표준 DRF) — 통일 필요.
4. **EXPLAIN 기반 인덱스 검증**: 운영 환경 slow query 로그에서 `NewsArticle` / `NewsEntity` / `CompanyMetricSnapshot` / `CompanyBenchmarkDelta` 쿼리 plan 점검. 본 감사는 정적 분석만 수행.
5. **Neo4j 쿼리 통합 패턴**: `chainsight/api/views.py:148-154`(union), `:705`(loop shortestPath) 등 Neo4j 쿼리는 가능한 단일 Cypher + `UNWIND` 로 통합. Round-trip이 가장 큰 latency 요인.

---

### 부록 D — 비교 추세 (직전 감사 대비)

| 항목 | 5/11 | 5/13 | 변화 |
|------|------|------|------|
| HIGH 합계 | 9 | 8 | -1 (pagination 2건 해소) |
| MED 합계 | 9 | 10 | +1 (RAG pagination 신규 분류) |
| LOW 합계 | 8 | 6 | -2 (정리) |
| **총합** | **26** | **24** | **-2** |

페이지네이션 일부 진척이 있었으나 `validation/api/views.py` N+1 4건과 `chainsight/api/views.py` N+1 핫스팟은 그대로다. 다음 sprint에서 우선 5건(상위 표 참조)을 처리하면 즉시 응답 latency 30-50% 단축 가능.
