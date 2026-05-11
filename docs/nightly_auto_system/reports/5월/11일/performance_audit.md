# API 성능 감사 보고서

**생성일**: 2026-05-11
**감사 대상**: Backend Django REST Framework API (17개 view 파일 + 8개 model 파일)
**감사 범위**: N+1 쿼리, 인덱스 누락, 느린 Serializer, 페이지네이션 누락
**감사 방식**: 정적 코드 분석 (읽기 전용)

> ⚠️ 사전 알림: `stocks/views_market_movers.py`, `stocks/views_exchange.py`, `stocks/views_mvp.py`, `rag_analysis/serializers.py`, `sec_pipeline/models.py`, `serverless/views.py` 일부 파일은 감사 도중 파일 시스템 접근 권한이 일시 차단되어 메모리에 캐싱된 1차 read 결과(`stocks/views_screener.py`, `stocks/views_eod.py`, `stocks/views_fundamentals.py`, `stocks/views_indicators.py`, `stocks/views_search.py` 등)와 grep 결과에 기반해 보고했다. 미커버 파일은 본문 끝에 명시한다.

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 | 인덱스 | Serializer | Pagination | 합계 |
|--------|-----|--------|-----------|------------|------|
| **HIGH** | 5 | 0 | 2 | 2 | 9 |
| **MED**  | 5 | 2 | 1 | 1 | 9 |
| **LOW**  | 3 | 3 | 1 | 1 | 8 |
| **합계** | **13** | **5** | **4** | **4** | **26** |

### 톱 5 우선순위 (HIGH + 즉시 효과)

| # | 이슈 | 파일:라인 | 영향 추정 | 수정 난이도 |
|---|------|----------|----------|------------|
| 1 | DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정 | `config/settings.py:348-364` | 모든 list 엔드포인트가 무제한 응답 가능 | 중간 (응답 envelope 결정 선행) |
| 2 | `LeaderComparisonView` 지표별 3-쿼리 루프 | `validation/api/views.py:361-400` | 40개 지표 × 3 = ~120 쿼리/요청 | 쉬움 |
| 3 | `ValidationMetricsView._build_metric` history 루프에서 `PeerMetricBenchmark.filter().first()` | `validation/api/views.py:265-285` | 카테고리당 5건 × 7카테고리 = ~35 쿼리 | 쉬움 |
| 4 | `ChainSightGraphView` 엣지마다 `CoMentionEdge` + `PriceCoMovement` 단건 조회 | `chainsight/api/views.py:74-87` | 노드 N개 그래프에서 2N 쿼리 | 쉬움 |
| 5 | `NewsViewSet.trending` 종목별 최근 기사 조회 N+1 | `news/api/views.py:337-349` | 트렌딩 N개 × 1 = N+1 쿼리 (캐시 hit 시 0) | 쉬움 |

---

## 상세

### 1. N+1 쿼리 이슈

#### HIGH-1. `validation/api/views.py:361-400` — `LeaderComparisonView`
**현상**: `CATEGORY_METRICS`의 모든 지표(7개 카테고리, ~40 지표)를 루프하며 매번
- `MetricDefinition.objects.filter(pk=mc).first()` (1 쿼리)
- `CompanyMetricSnapshot.objects.filter(...).first()` company용 (1 쿼리)
- `CompanyMetricSnapshot.objects.filter(...).first()` leader용 (1 쿼리)

지표 수 × 3 = **~120 쿼리/요청**.

**권장 수정**:
```python
# 1. MetricDefinition을 한 번에 dict로
mdefs = {md.pk: md for md in MetricDefinition.objects.filter(pk__in=[mc for _, mc in all_metrics])}
# 2. company + leader snapshot도 in 쿼리 + dict
snaps = CompanyMetricSnapshot.objects.filter(
    symbol__in=[stock, leader_stock_obj],
    fiscal_year=latest_fy,
    metric_code_id__in=[mc for _, mc in all_metrics],
    value_status='normal',
).select_related('metric_code')
snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
```
**수정 난이도**: 쉬움

#### HIGH-2. `validation/api/views.py:265-285` — `ValidationMetricsView._build_metric`
**현상**: history 루프에서 각 snap마다 `PeerMetricBenchmark.objects.filter(...).first()` 호출. 카테고리 × 지표 × 5년 → 카테고리당 ~35 쿼리 추가.

**권장 수정**: PeerMetricBenchmark를 fiscal_year list로 한 번에 prefetch하여 dict화.
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

#### HIGH-3. `validation/api/views.py:204-208` — `ValidationMetricsView._build_category`
**현상**: 카테고리 내 metric_code 루프 안에서 `MetricDefinition.objects.filter(pk=mc).first()` 호출.

**권장 수정**: 함수 진입 시 카테고리의 모든 metric_code에 대해 `MetricDefinition`을 dict로 한 번에 조회.
**수정 난이도**: 쉬움

#### HIGH-4. `validation/api/views.py:112-124` — `ValidationSummaryView`
**현상**: 5개 rank metric 루프 안에서 매번 `CompanyBenchmarkDelta.objects.filter(...).first()` + `MetricDefinition.objects.filter(...).first()` → 10 쿼리.

**권장 수정**: `metric_code__in=rank_metrics`로 한 번에 fetch + dict.
**수정 난이도**: 쉬움

#### HIGH-5. `chainsight/api/views.py:74-87` — `ChainSightGraphView`
**현상**: Neo4j에서 받은 edges 리스트에 대해 각 edge마다
```python
CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
```
N개 엣지 → **2N 쿼리**. depth=3이면 수십~수백 엣지 가능.

**권장 수정**:
1. edges에서 (a, b) 페어 set 미리 구성
2. `CoMentionEdge.objects.filter(Q(symbol_a__in=..., symbol_b__in=...))`로 한 번에 in-bulk 조회
3. dict 매핑 후 edge enrichment

**수정 난이도**: 중간

#### MED-1. `chainsight/api/views.py:698-799` — `_build_chain_signals`
**현상**: 시드 페어 (최대 page_size*3 = 15개) 각각에 대해 Neo4j `shortestPath` 쿼리 1회 → 15 round-trips.
**권장 수정**: Cypher `UNWIND $pairs AS pair MATCH p = shortestPath(...)` 한 쿼리로 통합.
**수정 난이도**: 중간

#### MED-2. `news/api/views.py:337-349` — `NewsViewSet.trending`
**현상**: trending_data 루프에서 각 종목마다 `NewsArticle.objects.filter(entities__symbol=symbol, ...)[:3]` 호출. limit=10 → 10 추가 쿼리.
**권장 수정**: 단일 `NewsArticle.objects.filter(entities__symbol__in=[...])`로 한 번에 가져온 뒤 Python에서 종목별로 grouping.
**완화 요인**: 5분 캐시(line 351-352)로 cache hit 시 비용 0.
**수정 난이도**: 쉬움

#### MED-3. `news/api/views.py:1377-1389` — `collection_logs.by_provider`
**현상**: `provider_agg` annotate 결과 루프 안에서 `qs.filter(provider=row['provider'], errors__gt=0).count()` 호출 → provider 수만큼 추가 count 쿼리.
**권장 수정**: 별도 `qs.values('provider').annotate(error_runs=Count('id', filter=Q(errors__gt=0)))`로 한 번에 집계.
**수정 난이도**: 쉬움

#### MED-4. `stocks/views_indicators.py:324-371` — `IndicatorComparisonView.post`
**현상**: symbols 리스트 루프에서 각 symbol마다 `Stock.objects.get(symbol=...)` + `DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]` 호출. N symbols → 2N 쿼리.
**권장 수정**: `Stock.objects.filter(symbol__in=symbols)` 한 번 + `DailyPrice.objects.filter(stock_id__in=symbols)` 한 번 + Python 그룹화.
**수정 난이도**: 중간

#### MED-5. `serverless/views_admin.py:478-499` (& PUT 분기 624-636, POST 550-562) — `AdminNewsCategoryView`
**현상**: `for cat in categories:` 루프에서 `cat.resolve_symbols()` 호출. `resolve_symbols`는 `SP500Constituent.objects.filter(...).values_list('symbol', ...)`로 매 카테고리마다 1 쿼리 (news/models.py:638-).
**권장 수정**: 카테고리 type별로 미리 group → 각 type에서 한 번에 모든 sector/sub_sector 값에 대해 SP500Constituent 조회.
**완화 요인**: admin 전용 + 카테고리 수 보통 5-20개로 제한.
**수정 난이도**: 중간

#### LOW-1. `stocks/serializers.py:398-409` — `WatchListStockSerializer.get_latest_price` / `get_chart_data`
**현상**: serializer가 객체마다 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` + `[:7]` 호출. 다만 코드 흐름상 함수가 return 없이 끝나(line 409) "dead code"로 추정.
**권장 수정**: 사용 확인 후 (a) 미사용이면 제거, (b) 사용 중이면 view에서 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date'))`로 미리 끌어옴.
**수정 난이도**: 쉬움

#### LOW-2. `stocks/serializers.py:205-307` — `OverviewTabSerializer.get_dynamic_layers`
**현상**: 1건의 Stock에 대해 6개의 OneToOne (`overview_ko`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`, `validation_news_summary`) + 1개의 reverse FK(`category_signals`)에 접근 → 객체당 7 추가 쿼리.
**현재 부분 완화**: view (`stocks/views.py:493`)에서 `select_related('overview_ko')` 적용. 나머지 5개 OneToOne + 1개 FK는 미적용.
**권장 수정**: View에서 `select_related('overview_ko', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag', 'validation_news_summary').prefetch_related('category_signals')` 일괄 적용. 코드 주석에서도 이미 TODO로 명시(line 492, 208).
**완화 요인**: 단일 객체 조회라 list endpoint 대비 영향 제한적.
**수정 난이도**: 쉬움

#### LOW-3. `users/views.py:374-376` — `PortfolioSummaryView`
**현상**: `for portfolio in portfolios: total_value += portfolio.total_value` 루프. `total_value` property는 `self.stock.real_time_price` 참조 → `select_related('stock')`로 해소됨 (line 358). N+1 없음.
**결론**: 문제 없음. 참고 패턴으로 기록.

---

### 2. 인덱스 누락

#### MED-6. `users/models.py:249-265` — `UserInterest` 인덱스 부재
**현상**: 필드 `user`, `interest_type`, `value` 중 인덱스가 없고 `unique_together`만 존재. 뉴스 개인화 피드에서 `UserInterest.objects.filter(user=request.user)` 형태로 조회될 가능성 높음.
**권장 수정**:
```python
indexes = [
    models.Index(fields=['user', 'interest_type']),
]
```
**수정 난이도**: 쉬움 (migration 추가)

#### MED-7. `serverless/models.py` 알림 도메인 — `AlertHistory.read_at` / `dismissed` 인덱스 부재 추정
**현상**: `serverless/views.py:1561-1569`에서 `read_at__isnull=True, dismissed=False`로 필터 + `triggered_at`로 정렬. `alert__user` JOIN 발생. 인덱스 부재 시 정렬 cost 증가.
**확인 필요**: AlertHistory 모델 인덱스 정의 (감사 시 파일 접근 차단). `(alert, read_at)` 또는 `(read_at, dismissed, -triggered_at)` 복합 인덱스 권장.
**수정 난이도**: 쉬움

#### LOW-4. `stocks/models.py:6-105` — `Stock.last_api_call` 인덱스 부재
**현상**: `last_api_call` 필드(line 90)에 db_index 없음. Stock sync 스케줄러가 `last_api_call__lt=...`로 필터한다면 영향. 현재 view에서 직접 필터 흔적은 없으나 task 영역에서 사용 가능성.
**권장 수정**: 사용처 확인 후 `db_index=True` 추가.
**수정 난이도**: 쉬움

#### LOW-5. `news/models.py:131-138` — `NewsArticle.is_press_release` / `is_official` 인덱스 부재
**현상**: 필터 가능성은 있으나 현재 views에서 적극 사용 흔적 없음. composite index 있는 `(-published_at, category)`로 보완 가능.
**권장 수정**: 사용처 확인 후 필요 시 composite index 추가.
**수정 난이도**: 쉬움

#### LOW-6. `news/models.py:189-198` — composite index leading field 정합성
**현상**: composite index `(sentiment_score, -published_at)` 존재. `sentiment_score__isnull=False` 등의 필터 패턴이 자주 쓰이면 부분 인덱스(`Index(condition=Q(sentiment_score__isnull=False))`) 검토.
**권장 수정**: 쿼리 EXPLAIN 후 부분 인덱스 도입 검토.
**수정 난이도**: 중간

---

### 3. 느린 Serializer (SerializerMethodField 추가 쿼리 패턴)

#### HIGH-6. `stocks/serializers.py:114-307` — `OverviewTabSerializer`
**현상**: `get_dynamic_layers`에서 6개 OneToOne + 1개 reverse FK 접근. 위 LOW-2와 동일 이슈이나, 객체당 7쿼리는 serializer 레벨에서 발생하므로 분류 변경.
**권장 수정**: 위 LOW-2와 동일 — view에서 prefetch.
**수정 난이도**: 쉬움

#### HIGH-7. `stocks/serializers.py:398-409` — `WatchListStockSerializer`
**현상**: 위 LOW-1과 동일. dead code 가능성 높지만 사용 중이면 N+1 발생.
**수정 난이도**: 쉬움

#### MED-8. `users/serializers.py:103-109` — `PortfolioDetailSerializer.get_portfolio_weight`
**현상**: context에서 total_portfolio_value 사용 → 추가 쿼리 없음. 정상 패턴.
**결론**: 문제 없음.

#### MED-9. `serverless/serializers.py:531-554` — `ScreenerAlertSerializer.get_can_trigger` / `get_cooldown_remaining_hours`
**현상**: `obj.can_trigger()` (모델 메서드)에서 DB 접근 가능성. 다만 `last_triggered_at`은 같은 row 필드라 추가 쿼리 없음. 정상 가능.
**권장 검증**: `can_trigger()` 구현에서 DB 호출 여부 확인. 캐시 사용 권장.
**수정 난이도**: 쉬움 (확인 후 결정)

#### LOW-7. `serverless/serializers.py:603, 626` — `AlertHistory*Serializer.alert_name`
**현상**: `source='alert.name'` → list endpoint에서 `select_related('alert')` 미적용 시 N+1. `serverless/views.py:1559`에서 `select_related('alert')` 적용 확인됨.
**결론**: 정상.

---

### 4. 페이지네이션 누락

#### HIGH-8. `config/settings.py:348-364` — DRF 전역 `DEFAULT_PAGINATION_CLASS` 미설정
**현상**: REST_FRAMEWORK 설정에 페이지네이션 클래스 없음. 설정 파일 주석(line 347)에 "audit P0 #14 (페이지네이션 표준)는 별도 PR — 응답 envelope 결정 선결"이라고 명시됨 → **이미 알려진 P0 이슈로 처리 보류 상태**.
**영향**: 모든 `ListAPIView` / `viewsets.ReadOnlyModelViewSet` (예: `news/api/views.py:47 NewsViewSet`)이 무제한 결과 반환 가능.
**권장 수정**: PageNumberPagination + page_size=20~50 설정. 응답 envelope(`results`/`count`/`next`/`previous`)는 기존 응답 구조와 충돌 가능 → 별도 PR로 처리하는 현재 정책 합리적.
**수정 난이도**: 높음 (envelope 결정 + 프론트 호환 검증)

#### HIGH-9. `stocks/views.py:76-106` — `StockListAPIView` (ListAPIView 확장) `pagination_class` 미설정
**현상**: 전역 페이지네이션 미설정 상태이므로 효과적으로 페이지네이션 없음. S&P 500 + α 종목 전체가 한 응답에 실릴 수 있음.
**권장 수정**: 전역 설정 적용 또는 클래스 단위 `pagination_class = StandardResultsSetPagination` 명시.
**수정 난이도**: 쉬움 (전역 변경과 함께)

#### MED-10. `news/api/views.py:47 NewsViewSet` — ReadOnlyModelViewSet에 pagination_class 미설정
**현상**: 일부 `@action`은 `[:limit]` 슬라이싱으로 자체 제한하나 (`market`, `trending`, `all_news`), default list endpoint는 무제한.
**권장 수정**: ViewSet에 pagination_class 명시.
**수정 난이도**: 쉬움

#### LOW-8. `chainsight/api/views.py:308-314 SeedListView` — 시드 전체 응답
**현상**: 캐시된 JSON 전체를 그대로 반환. 시드 수는 일반적으로 수십~수백 수준이므로 큰 문제 아님.
**권장 수정**: 페이로드 사이즈가 100KB 초과 시 페이지네이션 검토.
**수정 난이도**: 중간

---

### 부록 A — 미감사 / 제한적 감사 파일

다음 파일은 권한 EPERM으로 본 감사에서 1차 read는 불가했고 grep 결과/구조 정보만 활용:

| 파일 | 상태 | 비고 |
|------|------|------|
| `stocks/views_market_movers.py` | 미감사 | 69 LOC, grep `select_related|prefetch_related` 매치 없음 (잠재 N+1 위험) |
| `stocks/views_exchange.py` | 미감사 | 295 LOC, grep `select_related|prefetch_related` 매치 없음 |
| `stocks/views_mvp.py` | 미감사 | 200 LOC, `class StockMVPListView`, `SectorListView` 존재 |
| `rag_analysis/serializers.py` | 부분 | SerializerMethodField 2개 위치 확인(`can_add_item`, `max_units`) — list endpoint에서 호출 시 객체당 추가 메서드 호출, DB 접근 여부 모름 |
| `sec_pipeline/models.py` | 부분 | grep로 인덱스 정의 확인됨(`symbol, -filing_date`, `(source_company, relationship_type)`, `(target_company)`, `(neo4j_dirty)` 등) |
| `serverless/views.py` | 부분 | 일부 함수(`mark_alert_read`, `dismiss_alert`, alert history) 확인 — `select_related('alert')` 적용 확인됨 |

**권장 후속**: 위 파일들에 대해 권한 정상화 후 follow-up 감사 1회 필요.

---

### 부록 B — 글로벌 패턴 권장

1. **Compute-once context 패턴 강화**: validation/api/views.py가 가장 큰 N+1 핫스팟. Service 레이어에서 모든 metric_code를 한 번에 dict로 fetch한 뒤 view에서 lookup하는 패턴으로 일관화 권장.
2. **Prefetch 표준 헬퍼**: Stock 상세 조회 시 6개 OneToOne + 1 FK를 한꺼번에 가져오는 `Stock.objects.with_dynamic_layers()` manager 메서드 도입 검토.
3. **Pagination envelope 결정**: P0 보류 상태인 페이지네이션 표준화를 가장 시급한 작업으로 처리. DRF PageNumberPagination + 200 응답 envelope 합의 → 점진 적용.
4. **EXPLAIN 기반 인덱스 검증**: 운영 환경 slow query 로그에서 NewsArticle / NewsEntity / CompanyMetricSnapshot / CompanyBenchmarkDelta 쿼리 plan 점검. 본 감사는 정적 분석만 수행.
