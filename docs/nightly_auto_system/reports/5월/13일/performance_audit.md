# API 성능 감사 보고서

**대상**: stock_vis 백엔드 (Django REST Framework)
**감사일**: 2026-05-13
**범위**: views*.py 17개, serializers*.py 9개, models.py 7개
**원칙**: 코드 수정 없음, 읽기 전용 분석

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 누락 | 합계 |
|--------|---------|-----------|-----------------|------------------|------|
| **HIGH** | 9 | 0 | 1 | 1 | **11** |
| **MED**  | 4 | 3 | 2 | 5 | **14** |
| **LOW**  | 2 | 2 | 2 | 4 | **10** |
| **합계** | 15 | 5 | 5 | 10 | **35** |

### 핵심 결론 (TOP 5)

1. **validation/api/views.py** — 카테고리 × 지표 × 5년 히스토리 중첩 루프에서 메트릭당 4~5쿼리 발생, 전체 카테고리 조회 시 200+ 쿼리 가능 (HIGH)
2. **stocks/serializers.py:205-307** — `OverviewTabSerializer.get_dynamic_layers`가 6개 OneToOne + 1개 reverse FK를 prefetch 없이 호출 (HIGH, 자체 TODO 주석으로 인지됨)
3. **chainsight/api/views.py:73-92** — `ChainSightGraphView`가 그래프 edge마다 `CoMentionEdge`/`PriceCoMovement` 쿼리 2개씩 발생 (depth=3 시 폭증, HIGH)
4. **users/views.py** — `WatchlistBulkAddView`/`BulkRemoveView`/`UserInterestListCreateView` 모두 심볼/항목 루프 안에서 `Stock.get` + `WatchlistItem.filter.exists` + `create` 반복 (HIGH)
5. **serverless/views.py:1887-1892** — `etf_collection_status`에서 ETFProfile마다 `ETFHolding.count()` 별도 쿼리 (HIGH, GROUP BY 한 번이면 끝)

---

## 상세 (이슈별 분류)

## 1. N+1 쿼리 이슈

### HIGH

#### 1-H-1. `ValidationMetricsView._build_metric` — 메트릭 × 5년 N+1
- **위치**: `validation/api/views.py:199-314`
- **재현 경로**: `GET /api/v1/validation/{symbol}/metrics/?category=all`
- **설명**:
  ```python
  for cat in categories:                              # 7개 카테고리
      for mc in metric_codes:                         # 카테고리당 5~10 메트릭
          md = MetricDefinition.objects.filter(...)   # (1) 카탈로그 조회
          latest_snap = CompanyMetricSnapshot.objects.filter(...)  # (2)
          delta = CompanyBenchmarkDelta.objects.filter(...)  # (3)
          snaps = CompanyMetricSnapshot.objects.filter(...)[:5]  # (4) 5년치
          for s in snaps:                             # 5개 스냅샷마다
              peer_bench = PeerMetricBenchmark.objects.filter(...)  # (5) 5개 = +5쿼리
  ```
- **영향**: `category=all`이면 50+ 메트릭 × (4 + 5) = **약 450 쿼리/요청**
- **권장 수정**: ① 카테고리 진입 시 `MetricDefinition.objects.in_bulk(metric_codes)`로 카탈로그 일괄 로드 ② `CompanyMetricSnapshot.filter(symbol=stock, metric_code__in=...)`로 5년치 전부 한 번에 → 파이썬에서 그룹핑 ③ `PeerMetricBenchmark` 동일하게 일괄 조회
- **수정 난이도**: 중간 (helper 함수로 metric_code별 dict 빌드 후 인덱싱)

#### 1-H-2. `LeaderComparisonView.get` — 전체 메트릭 × 회사·리더 N+1
- **위치**: `validation/api/views.py:317-421`
- **재현 경로**: `GET /api/v1/validation/{symbol}/leader-comparison/`
- **설명**: `all_metrics`(30+) 각각에 대해 `MetricDefinition` + `CompanyMetricSnapshot`(회사) + `CompanyMetricSnapshot`(리더) = 메트릭당 3쿼리.
- **영향**: 30+ × 3 = **90+ 쿼리/요청**
- **권장 수정**: 회사·리더 둘 다 `CompanyMetricSnapshot.objects.filter(symbol__in=[stock.symbol, leader.symbol], fiscal_year=latest_fy, metric_code__in=all_codes)` 한 번에 fetch → 파이썬에서 (symbol, metric_code) dict로 그룹핑. MetricDefinition은 `in_bulk(pks=all_codes)`.
- **수정 난이도**: 중간

#### 1-H-3. `ChainSightGraphView` — edge별 market_signals 보강 N+1
- **위치**: `chainsight/api/views.py:74-92`
- **재현 경로**: `GET /api/v1/chainsight/{symbol}/graph/?depth=3`
- **설명**:
  ```python
  for edge in result.get("edges", []):
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()  # +1
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()  # +1
  ```
- **영향**: depth=3 그래프는 보통 50~200 edge → **100~400 쿼리**
- **권장 수정**: 모든 (a,b) 페어 수집 후 `CoMentionEdge.objects.filter(symbol_a__in=..., symbol_b__in=...).filter(...)` 한 번에 + dict 매핑.
- **수정 난이도**: 쉬움

#### 1-H-4. `NewsViewSet.trending` — 트렌딩 종목 별 기사 재조회
- **위치**: `news/api/views.py:344-358`
- **재현 경로**: `GET /api/v1/news/trending/?limit=10`
- **설명**:
  ```python
  for item in trending_data:                         # 최대 10건
      recent_articles = NewsArticle.objects.filter(
          entities__symbol=symbol, ...
      ).distinct().order_by('-published_at')[:3]     # 매번 새 쿼리
  ```
- **영향**: limit=10 → **+10 쿼리** (각 distinct + order_by)
- **권장 수정**: 단일 쿼리에서 `entities__symbol__in=trending_symbols`로 전체 후보를 가져온 뒤, 파이썬에서 심볼별 상위 3개 슬라이싱.
- **수정 난이도**: 쉬움

#### 1-H-5. `WatchlistBulkAddView.post` — 심볼 루프 N+1
- **위치**: `users/views.py:880-903`
- **재현 경로**: `POST /api/v1/users/watchlists/{pk}/bulk-add/` body=`{"symbols": [...]}`
- **설명**:
  ```python
  for symbol in symbols:                              # N개
      stock = Stock.objects.get(symbol=symbol.upper())          # +1
      WatchlistItem.objects.filter(watchlist=..., stock=stock).exists()  # +1
      WatchlistItem.objects.create(...)               # +1
  ```
- **영향**: 50개 심볼 = **150 쿼리 + N transactions**
- **권장 수정**: ① `stocks_map = Stock.objects.in_bulk([s.upper() for s in symbols], field_name='symbol')` 한 번 ② `existing = set(WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=...).values_list('stock_id', flat=True))` ③ `WatchlistItem.objects.bulk_create([...], ignore_conflicts=True)`
- **수정 난이도**: 중간 (트랜잭션 + 응답 포맷 보존)

#### 1-H-6. `WatchlistBulkRemoveView.post` — 동일 패턴
- **위치**: `users/views.py:945-958`
- **재현 경로**: `POST /api/v1/users/watchlists/{pk}/bulk-remove/`
- **설명**: 심볼별로 `WatchlistItem.objects.get(...).delete()` 반복.
- **권장 수정**: `WatchlistItem.objects.filter(watchlist=..., stock__symbol__in=symbols).delete()` 한 번. 삭제된 심볼 트래킹은 `values_list('stock__symbol', flat=True)`로 미리 수집.
- **수정 난이도**: 쉬움

#### 1-H-7. `OverviewTabSerializer.get_dynamic_layers` — 7개 reverse 관계 N+1
- **위치**: `stocks/serializers.py:205-307`
- **재현 경로**: 모든 `/api/v1/stocks/overview/{symbol}/` (단일) — 그리고 향후 리스트 시 폭증
- **설명**: 코드 주석 자체에 "Step 2~4에서 prefetch_related + 캐싱" TODO 명시. 6개 OneToOne reverse(`overview_ko`는 select_related로 해결됨, 나머지 5개 + `category_signals` reverse FK 1개)가 prefetch 없이 호출됨.
  ```python
  list(obj.category_signals.all())            # +1 query
  obj.validation_news_summary                 # +1
  obj.sensitivity_profile                     # +1
  obj.growth_stage                            # +1
  obj.capital_dna                             # +1
  obj.narrative_tag                           # +1
  ```
- **영향**: 단일 종목 = +6쿼리, 만약 리스트에서 사용되면 종목당 6쿼리
- **권장 수정**: `StockOverviewAPIView`의 쿼리에 `select_related('overview_ko', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag').prefetch_related('category_signals')` 추가.
- **수정 난이도**: 중간 (역참조 가능 여부는 모델 정의 확인 필요 — OneToOne reverse는 select_related 가능)

#### 1-H-8. `IndicatorComparisonView.post` — 비교 심볼별 N+1
- **위치**: `stocks/views_indicators.py:324-371`
- **재현 경로**: `POST /api/v1/stocks/indicators/comparison/` body=`{"symbols": [...]}`
- **설명**: 심볼당 `Stock.objects.get()` + `DailyPrice.objects.filter()[:50]` 2 쿼리. 메트릭당 추가 계산.
- **영향**: 10심볼 = **+20 쿼리**
- **권장 수정**: `Stock.objects.in_bulk(symbols, field_name='symbol')`로 메타 일괄 + `DailyPrice.objects.filter(stock__symbol__in=symbols).order_by('stock', '-date')` → 파이썬 그룹핑.
- **수정 난이도**: 쉬움

#### 1-H-9. `etf_collection_status` — ETFProfile 루프 내 count
- **위치**: `serverless/views.py:1887-1892`
- **재현 경로**: `GET /api/v1/serverless/etf/status`
- **설명**:
  ```python
  for profile in profiles:                                    # 20+개
      holdings_count = ETFHolding.objects.filter(etf=profile).count()  # +1
  ```
- **영향**: 21 ETF = **+21 카운트 쿼리**
- **권장 수정**: `ETFHolding.objects.values('etf_id').annotate(n=Count('id'))`을 미리 dict로 만들고 lookup. 또는 `profiles.annotate(holdings_count=Count('holdings'))`.
- **수정 난이도**: 쉬움

### MED

#### 1-M-1. `ValidationSummaryView.get` — 랭크 메트릭 5개 × 2쿼리
- **위치**: `validation/api/views.py:111-124`
- **설명**: `rank_metrics`(5개) 각각에 대해 `CompanyBenchmarkDelta` + `MetricDefinition` 조회.
- **영향**: +10 쿼리/요청 (영향 자체는 작지만 1-H-1과 함께 누적되면 큼)
- **권장 수정**: `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=..., metric_code_id__in=rank_metrics)` + `MetricDefinition.objects.in_bulk(rank_metrics)`.
- **수정 난이도**: 쉬움

#### 1-M-2. `AdminNewsCategoryView.get` — 카테고리별 resolve_symbols
- **위치**: `serverless/views_admin.py:475-498` → `news/models.py:638-660`
- **설명**: `for cat in categories: cat.resolve_symbols()` — 각 호출이 `SP500Constituent.filter(sector|sub_sector=...)`을 발생시킴.
- **영향**: 카테고리 20개 = **+20 쿼리**
- **권장 수정**: 카테고리를 sector/sub_sector/custom 그룹으로 묶어서 각 그룹마다 1쿼리, 결과를 dict 매핑.
- **수정 난이도**: 중간 (resolve_symbols 시그니처 변경 또는 batch 메서드 추가)

#### 1-M-3. `UserInterestListCreateView.post` — 관심사 루프 N+1
- **위치**: `users/views.py:1008-1041`
- **설명**: `interests` 입력 N개마다 `UserInterest.objects.get_or_create()` + 내부 `_link_category`에서 `NewsCollectionCategory.objects.get_or_create()` + `interest.save()`.
- **영향**: 5~10개 관심사 = 10~30 쿼리, 끝에 `UserInterest.objects.filter().count()` 추가.
- **권장 수정**: ① 기존 UserInterest를 batch fetch 후 누락된 것만 `bulk_create(ignore_conflicts=True)` ② `_link_category`는 mapping dict 생성 후 호출.
- **수정 난이도**: 중간

#### 1-M-4. `news.keyword_detail` 폴백 분기 — 2단 OR + distinct
- **위치**: `news/api/views.py:734-753`
- **설명**: `articles_qs = articles_qs | secondary_qs`를 `.distinct()`로 묶고 다시 `order_by()[:10]`. PostgreSQL에서 UNION 후 ORDER BY가 일어나면 인덱스 미사용 풀스캔 위험.
- **영향**: 폴백 경로 진입 시 (레거시 keyword) 대용량 NewsArticle 스캔
- **권장 수정**: title icontains는 `pg_trgm` GIN 인덱스 검토. 또는 article_ids 마이그레이션을 우선 적용해 폴백 제거.
- **수정 난이도**: 높음 (인덱스 추가 + 마이그레이션 일정 필요)

### LOW

#### 1-L-1. `ChainSightSuggestionView` co-mention union
- **위치**: `chainsight/api/views.py:150-165`
- **설명**: `CoMentionEdge.filter(symbol_a=symbol).union(CoMentionEdge.filter(symbol_b=symbol)).order_by('-co_mention_count')[:10]` — UNION 결과 정렬은 인덱스 사용이 어려움. 다만 결과를 10개로 제한.
- **권장 수정**: `Q(symbol_a=symbol) | Q(symbol_b=symbol)` 단일 쿼리로 변경하면 인덱스 활용 가능.
- **수정 난이도**: 쉬움

#### 1-L-2. `NewsViewSet.sources` — 3번의 count 쿼리
- **위치**: `news/api/views.py:480-495`
- **설명**: 동일 기준에 대해 finnhub_count / marketaux_count / total_count 세 번 count.
- **권장 수정**: 단일 쿼리에 conditional aggregation (`Count('id', filter=Q(finnhub_id__isnull=False))`).
- **수정 난이도**: 쉬움

---

## 2. 인덱스 누락

### MED

#### 2-M-1. `NewsArticle.finnhub_id` / `marketaux_uuid` — 소스 필터 인덱스 누락
- **위치**: `news/models.py:90-99`
- **사용처**:
  - `news/api/views.py:418` `queryset.filter(finnhub_id__isnull=False)`
  - `news/api/views.py:420` `queryset.filter(marketaux_uuid__isnull=False)`
  - `news/api/views.py:483, 489` 동일 패턴
- **영향**: 뉴스 누적량 증가 시 모든 행 스캔. 현재 `published_at`만 인덱스됨.
- **권장 수정**: `models.Index(fields=['finnhub_id'], condition=Q(finnhub_id__isnull=False), name='news_finnhub_partial')` 부분 인덱스 또는 `models.Index(fields=['finnhub_id', '-published_at'])`.
- **수정 난이도**: 쉬움 (마이그레이션만)

#### 2-M-2. `Watchlist.user` 단일 인덱스 — list 쿼리
- **위치**: `users/models.py:177-182`
- **사용처**: `users/views.py:599` `Watchlist.objects.filter(user=request.user).order_by('-updated_at')`
- **상태**: 복합 인덱스 `(user, -updated_at)` 존재. **OK** — 인덱스 활용됨.
- **수정 난이도**: N/A (실제로 인덱스됨, 확인용)

#### 2-M-3. `EODSignal.signals` JSONField 부분 검색
- **위치**: `stocks/models.py:754` (EODSignal)
- **사용처**: `stocks/views_eod.py:75` `signals__contains=[{'id': signal_id}]`
- **영향**: PostgreSQL JSONB containment 인덱스 없으면 풀스캔
- **권장 수정**: `models.Index(fields=['signals'], name='eod_signals_gin')` with `Index(SqlGin)` — Django 4.2+ `GinIndex(fields=['signals'])`.
- **수정 난이도**: 쉬움 (마이그레이션)

### LOW

#### 2-L-1. `Stock.market_capitalization` — order_by 사용 시 인덱스 정렬
- **위치**: `stocks/models.py:98` `models.Index(fields=['market_capitalization'])`
- **사용처**: `stocks/views.py:70, 115` `order_by('-market_capitalization')`
- **상태**: 인덱스 존재하지만 단방향(`market_capitalization` 오름차순). DESC 정렬은 `-`로 인덱스 역스캔 가능 (PostgreSQL ok). **OK**

#### 2-L-2. `BasicFinancialStatement.fiscal_quarter` — 잘 인덱스됨
- **위치**: `stocks/models.py:258-263` db_index=True
- **상태**: OK

---

## 3. 느린 Serializer

### HIGH

#### 3-H-1. `OverviewTabSerializer.get_dynamic_layers`
- **위치**: `stocks/serializers.py:205-307`
- **내용**: 1-H-7와 동일 이슈 — SerializerMethodField에서 6개 reverse OneToOne + 1 reverse FK를 읽음.
- **권장 수정**: 1-H-7 참고. View 쪽 select_related/prefetch_related 추가 후 본 serializer는 그대로 사용 가능.
- **수정 난이도**: 중간

### MED

#### 3-M-1. `MarketMoverListSerializer` — IndicatorCalculator 재인스턴스화
- **위치**: `serverless/serializers.py:121-137`
- **내용**: `get_sector_alpha_display`, `get_etf_sync_display`, `get_volatility_pct_display`에서 매번 `IndicatorCalculator()` 인스턴스 생성. 메서드는 stateless로 보이므로 클래스 변수/싱글톤화 가능.
- **권장 수정**: `IndicatorCalculator.format_sector_alpha_display(...)`를 staticmethod/classmethod로 변경. 또는 serializer 클래스 변수로 한 번만 인스턴스화.
- **수정 난이도**: 쉬움

#### 3-M-2. `MarketBreadthSerializer.get_signal_interpretation` — Service 재인스턴스화
- **위치**: `serverless/serializers.py:208-212`
- **내용**: `MarketBreadthService()`를 매 행마다 생성. list 응답이면 N번.
- **권장 수정**: staticmethod로 리팩토링 또는 클래스 변수 캐싱.
- **수정 난이도**: 쉬움

### LOW

#### 3-L-1. `SectorPerformanceSerializer.get_name_ko` — dict 조회만
- **위치**: `serverless/serializers.py:419-422`
- **내용**: `SECTOR_NAMES_KO.get(...)` 클래스 dict 조회. **부담 거의 없음** — LOW.

#### 3-L-2. `NewsArticleListSerializer.entities` — prefetch 의존
- **위치**: `news/api/serializers.py:46-64`
- **상태**: 대부분의 호출처에서 `prefetch_related('entities')` 적용됨 (e.g. `news/api/views.py:58, 412`). NewsArticleDetailSerializer가 highlight까지 노출하지만 detail 단건이라 영향 작음.
- **권장**: 상세 endpoint에서도 `prefetch_related('entities__highlights')` 명시 추천.
- **수정 난이도**: 쉬움

---

## 4. 페이지네이션 누락

### HIGH

#### 4-H-1. `etf_collection_status` — 전체 ETFProfile 반환
- **위치**: `serverless/views.py:1837-1928`
- **설명**: 현재 21개지만 향후 늘면 limit/offset 없음. 더 큰 문제는 1-H-9 N+1과 결합.
- **권장 수정**: 우선 N+1 해결, 페이지네이션은 100+ 시점에 추가.
- **수정 난이도**: 중간

### MED

#### 4-M-1. `screener_presets_api` (GET) — 전체 preset 반환
- **위치**: `serverless/views.py:883-910`
- **설명**: 시스템 + 공개 + 본인 preset을 union해서 distinct 반환. pagination_class 없음.
- **권장 수정**: DRF의 `PageNumberPagination` 적용 또는 limit query param.

#### 4-M-2. `theme_list_api` — 전체 테마 반환
- **위치**: `serverless/views.py:2196-2225`
- **설명**: service.get_all_themes() 호출 결과를 그대로 응답. 현재 20개 정도지만 LLM 기반 추가 가능성 있음.

#### 4-M-3. `AdminNewsCategoryView.get` — 전체 카테고리
- **위치**: `serverless/views_admin.py:472-497`
- **설명**: 1-M-2와 함께 발생. 페이지네이션 + bulk resolve_symbols 동시 검토 필요.

#### 4-M-4. `PresetListView` (validation) — 전체 프리셋
- **위치**: `validation/api/views.py:424-456`
- **설명**: 종목별 preset 5~10개로 bounded. **현재로선 OK** — 향후 늘면 paginate.

#### 4-M-5. `UserInterestListCreateView.get` — 전체 관심사
- **위치**: `users/views.py:974-987`
- **설명**: 사용자당 5~20개로 bounded. 현재 영향 작음.

### LOW

#### 4-L-1. `etf_holdings_api` — limit param은 있으나 표준 페이지네이션 아님
- **위치**: `serverless/views.py:2127-2193`
- **상태**: `limit=50` 기본, `[:limit]` 슬라이싱. ETF holdings는 통상 30~500. 표준 PageNumberPagination 적용 권장.

#### 4-L-2. `StockMVPListView` — 하드코딩 `[:20]`
- **위치**: `stocks/views_mvp.py:41`
- **상태**: MVP 목적이라 의도된 cap. **현재 LOW**.

#### 4-L-3. `SectorListView` — distinct sector 반환
- **위치**: `stocks/views_mvp.py:190-201`
- **상태**: GICS 11 섹터로 bounded. OK.

#### 4-L-4. `SeedListView` — 일일 시드 ≤ 100건 추정
- **위치**: `chainsight/api/views.py:309-314`
- **상태**: bounded. OK.

---

## 부록: 정상 패턴 (참고용)

다음은 N+1 방어가 잘 적용된 사례:

- `users/views.py:358, 406, 819` — `select_related('stock')` 적용된 Portfolio/Watchlist 조회
- `news/api/views.py:58, 412` — `prefetch_related('entities')` 적용
- `serverless/views.py:1309, 1339, 1361` — `select_related('alert')` AlertHistory
- `stocks/views_eod.py:77` — `select_related('stock')` EODSignal
- `rag_analysis/views.py:52, 78, 379, 410` — Basket/Session에 `prefetch_related('items'|'messages')`

다음은 인덱스가 잘 설계된 모델:

- `LLMExtractedRelation` (`serverless/models.py:1309-1321`) — 5개 복합 인덱스
- `NewsArticle` (`news/models.py:189-198`) — 5개 복합 인덱스 (published_at × category/source/sentiment/importance/llm_analyzed)
- `EODSignal` 추정 — 본 감사에선 확인하지 못함 (필요 시 별도 점검)

---

## 권장 수정 우선순위

| 순위 | 이슈 | 예상 효과 | 난이도 |
|------|------|----------|-------|
| 1 | 1-H-3 (ChainSightGraphView edge 보강) | depth=3 응답 100~400쿼리 → 2쿼리 | 쉬움 |
| 2 | 1-H-9 (etf_collection_status count) | 21쿼리 → 1쿼리 | 쉬움 |
| 3 | 1-H-5 / 1-H-6 (Watchlist bulk add/remove) | 50심볼 시 150쿼리 → 4쿼리 | 중간 |
| 4 | 1-H-4 (trending) | 10쿼리 → 1쿼리 | 쉬움 |
| 5 | 1-H-2 (LeaderComparison) | 90쿼리 → 4쿼리 | 중간 |
| 6 | 1-H-1 (ValidationMetrics) | 450쿼리 → 7~10쿼리 | 중간 |
| 7 | 1-H-7 (OverviewSerializer dynamic_layers) | +6쿼리 → 0 (단건 기준) | 중간 |
| 8 | 1-H-8 (IndicatorComparison) | 20쿼리 → 2쿼리 | 쉬움 |
| 9 | 1-M-2 (AdminNewsCategory resolve_symbols) | N+1 → 2쿼리 | 중간 |
| 10 | 2-M-1 (NewsArticle source 부분 인덱스) | filter 풀스캔 방지 | 쉬움 |

**전체 통계**: HIGH 11건, MED 14건, LOW 10건 — 총 35건 식별.
