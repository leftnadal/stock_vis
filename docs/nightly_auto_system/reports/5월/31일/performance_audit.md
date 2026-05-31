# API 성능 감사 보고서

- **작성일**: 2026-05-31
- **유형**: 읽기 전용 감사 (코드 수정 없음)
- **감사 범위**: 뷰 17개 + 모델 7개 + 연계 Serializer (stocks/users/news/macro/rag/serverless/validation/chainsight/sec)
- **경로 주의**: 모노레포 마이그레이션(PR7)으로 일부 경로 변경됨 — `stocks/` → `packages/shared/stocks/`, `users/` → `packages/shared/users/`, `chainsight/` → `apps/chain_sight/`, `graph_analysis/` → `services/_dormant/graph_analysis/`

---

## 요약 (심각도별 이슈 수)

| 심각도 | 개수 | 항목 |
|--------|------|------|
| **HIGH** | 8 | N+1 쿼리 6건, 페이지네이션 누락 2건(N+1과 중복 카운트) |
| **MED** | 10 | N+1/반복 쿼리 7건, 인덱스 누락 2건, 페이지네이션 1건 |
| **LOW** | 7 | 무제한 로드/캐시 미적용/미세 인덱스 후보 |

### 검사 항목별 결론

| 항목 | 결과 |
|------|------|
| 1. N+1 쿼리 | **HIGH 6건, MED 5건** — validation/users/rag/news/chainsight/stocks-indicators에 집중 |
| 2. 인덱스 누락 | **HIGH 0건, MED 2건** — 인덱스 설계 전반 우수. sec_pipeline 시계열 2건만 실익 |
| 3. 느린 Serializer | **HIGH 2건, MED 2건** — `OverviewTabSerializer.get_dynamic_layers`, `DataBasketSerializer` |
| 4. 페이지네이션 누락 | **HIGH 2건, MED 1건** — users/rag 목록 엔드포인트 (전체 테이블 반환) |

### 가장 시급한 5건 (비용 대비 효과)

| 순위 | 위치 | 이슈 | 난이도 |
|------|------|------|--------|
| 1 | `validation/api/views.py:228-294` | `_build_metric` 지표×연도 N+1 (category=all 시 수백 쿼리, 캐시 없음) | 높음 |
| 2 | `validation/api/views.py:364-383` | `LeaderComparisonView` 전체 지표 snapshot N+1 (캐시 없음) | 높음 |
| 3 | `packages/shared/users/views.py:92-95` | `Users.get()` favorite_stock N+1 + 페이지네이션 전무 | 쉬움 |
| 4 | `rag_analysis/views.py:378-379` | 세션 목록 nested basket/items N+1 + 페이지네이션 없음 | 쉬움 |
| 5 | `packages/shared/stocks/views_indicators.py:371-384` | `IndicatorComparisonView` 2N 쿼리 + 입력 상한 없음(DoS 표면) | 중간 |

> **3·4·5번은 난이도 쉬움/중간 + prefetch 추가로 해결** — 우선 처리 권장. 1·2번은 구조적 리팩토링(bulk fetch + 캐시) 필요.

---

## 상세

### [HIGH-1] `_build_metric` 지표×연도 N+1 (validation)

- **위치**: `validation/api/views.py:213-217, 228-294`
- **문제 코드**:
  ```python
  for mc in metric_codes:
      md = MetricDefinition.objects.filter(pk=mc).first()       # 지표마다 1쿼리
      # _build_metric 내부:
      latest_snap = CompanyMetricSnapshot.objects...first()      # 1
      delta = CompanyBenchmarkDelta.objects...first()            # 1
      snaps = CompanyMetricSnapshot.objects...[:5]               # 1
      for s in snaps:
          peer_bench = PeerMetricBenchmark.objects...first()     # history 연도마다 1쿼리!
  ```
- **설명**: `category=all`이면 전체 카테고리 × 전체 지표를 순회. 지표 1개당 MetricDefinition 1 + snapshot 2~3 + delta 1 + history 1 + **history 5년 × PeerMetricBenchmark 5쿼리**. 지표 수십 개면 수백 쿼리 발생. 응답 캐시 없음 — 가장 무거운 엔드포인트.
- **권장 수정**: MetricDefinition을 `pk__in`으로 일괄 로드(dict 캐시). CompanyMetricSnapshot / PeerMetricBenchmark / Delta를 `(metric_code, fiscal_year)` 키로 bulk fetch 후 메모리 매핑. 응답 캐시 추가.
- **심각도**: HIGH / **난이도**: 높음

### [HIGH-2] `LeaderComparisonView` 전체 지표 snapshot N+1 (validation)

- **위치**: `validation/api/views.py:364-383`
- **문제 코드**:
  ```python
  for cat, mc in all_metrics:                                # 전체 카테고리×지표
      md = MetricDefinition.objects.filter(pk=mc).first()
      company_snap = CompanyMetricSnapshot.objects...first() # 지표마다
      leader_snap  = CompanyMetricSnapshot.objects...first() # 지표마다
  ```
- **설명**: 전체 지표 수(수십)마다 MetricDefinition 1 + snapshot 2 = 100+ 쿼리. 캐시 없음.
- **권장 수정**: company/leader snapshot을 `symbol_id__in=[stock, leader], fiscal_year=latest_fy, metric_code_id__in=all_codes`로 2~3쿼리 bulk 로드 후 매핑. MetricDefinition도 일괄 조회.
- **심각도**: HIGH / **난이도**: 높음

### [HIGH-3] `Users.get()` favorite_stock N+1 + 페이지네이션 누락 (users)

- **위치**: `packages/shared/users/views.py:92-95` + `serializers.py:16`
- **문제 코드**:
  ```python
  users = User.objects.all()
  serializer = UserSerializer(users, many=True)  # favorite_stock = StockListingField(many=True)
  ```
- **설명**: `UserSerializer.favorite_stock`가 각 user의 M2M를 순회 → user N명이면 favorite 조회 N회. 동시에 `User.objects.all()`을 페이지네이션 없이 전체 직렬화(전체 테이블 반환). 관리자 전용이라 호출 빈도는 낮음.
- **권장 수정**: `User.objects.prefetch_related('favorite_stock')` + DRF 페이지네이션 적용.
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-4] `OverviewTabSerializer.get_dynamic_layers` 역참조 6개 미prefetch (stocks)

- **위치**: `packages/shared/stocks/views.py:545-551` + `serializers.py:241-353`
- **문제 코드**:
  ```python
  # views.py — overview_ko만 select_related
  stock = Stock.objects.select_related("overview_ko").filter(symbol=symbol).first()
  # serializers.py get_dynamic_layers 내부 — 역참조 6개 lazy load
  signals = list(obj.category_signals.all())   # 역FK 쿼리
  ns = obj.validation_news_summary             # OneToOne
  sp = obj.sensitivity_profile; gs = obj.growth_stage
  cd = obj.capital_dna; nt = obj.narrative_tag # OneToOne ×4
  ```
- **설명**: 단일 종목 조회라 N+1은 아니지만 **요청당 +6 쿼리 고정**. 코드 내 TODO 주석(`views.py:544`, `serializers.py:244`)이 이미 부채 인지. 10분 캐시(`cache_ttl=600`)로 완화되나 cold cache/무효화 시 매번 발생.
- **권장 수정**: `views.py:545`의 select_related에 OneToOne 5개 추가 + `prefetch_related("category_signals")`:
  ```python
  Stock.objects.select_related(
      "overview_ko", "validation_news_summary", "sensitivity_profile",
      "growth_stage", "capital_dna", "narrative_tag",
  ).prefetch_related("category_signals").filter(symbol=symbol).first()
  ```
- **심각도**: HIGH (단일 객체 + 캐시 완화로 실질 MED~HIGH 경계) / **난이도**: 쉬움

### [HIGH-5] `IndicatorComparisonView` 루프 내 2N 쿼리 + 입력 상한 없음 (stocks)

- **위치**: `packages/shared/stocks/views_indicators.py:371-384`
- **문제 코드**:
  ```python
  for symbol in symbols:
      stock = Stock.objects.get(symbol=symbol)                               # N회
      prices = DailyPrice.objects.filter(stock=stock).order_by("-date")[:50] # N회
  ```
- **설명**: 클라이언트 입력 `symbols` 길이 N에 대해 루프마다 **Stock 1 + DailyPrice 1 = 2N 쿼리**. `symbols` 개수 상한 검증이 없어(`views_indicators.py:361-367`은 빈 배열만 체크) 임의 대량 입력으로 쿼리 폭증 → **DoS 표면**. 캐시도 없음.
- **권장 수정**: (1) `symbols` 개수 상한(예 ≤20) 추가. (2) `stocks = {s.symbol: s for s in Stock.objects.filter(symbol__in=upper_symbols)}`로 Stock 일괄 조회 1쿼리화. (3) DailyPrice는 종목별 정렬+slice가 필요하므로 `Prefetch` 객체 또는 윈도우 함수로 묶기.
- **심각도**: HIGH / **난이도**: 중간

### [HIGH-6] 세션 목록 nested basket/items N+1 + 페이지네이션 누락 (rag_analysis)

- **위치**: `rag_analysis/views.py:378-379` + `serializers.py:66-84, 28`
- **문제 코드**:
  ```python
  sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')
  serializer = AnalysisSessionSerializer(sessions, many=True)
  # AnalysisSessionSerializer.basket = DataBasketSerializer → items=BasketItemSerializer(many=True) + can_add_item()
  ```
- **설명**: `messages`는 prefetch되나 **`basket` FK + `basket.items` + `can_add_item()`(추가 쿼리 가능)이 세션 N개에 비례**해 발생. 페이지네이션도 없어 목록 전체 반환.
- **권장 수정**: `select_related('basket').prefetch_related('messages', 'basket__items')` + 페이지네이션.
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-7] News detail `entities__highlights` prefetch 누락 (news)

- **위치**: `news/api/views.py:64` (queryset) vs `serializers.py:68-92` (`NewsArticleDetailSerializer`)
- **문제 코드**:
  ```python
  queryset = NewsArticle.objects.all().prefetch_related('entities')  # highlights 미포함
  # retrieve → NewsEntitySerializer(many=True) → EntityHighlightSerializer(highlights, many=True)
  ```
- **설명**: 상세 직렬화 시 각 entity의 `highlights`(reverse FK, `news/models.py:311-314`)를 순회하는데 queryset은 `entities`만 prefetch → entity M개마다 highlights 쿼리 M회.
- **권장 수정**: `get_queryset`을 액션별로 분기, retrieve 시 `prefetch_related('entities__highlights')`.
- **심각도**: HIGH (단건이나 entity 수만큼 N+1) / **난이도**: 쉬움

### [HIGH-8] `trending` 심볼별 article 루프 쿼리 + entities 미prefetch (news)

- **위치**: `news/api/views.py:352-364`
- **문제 코드**:
  ```python
  for item in trending_data:   # limit개 (기본 10)
      recent_articles = NewsArticle.objects.filter(
          entities__symbol=symbol, ...).distinct().order_by('-published_at')[:3]
      ... NewsArticleListSerializer(recent_articles, many=True)  # entities prefetch 없음
  ```
- **설명**: limit개 심볼마다 article 쿼리 1회 + 직렬화에서 `entities` prefetch 누락 → 추가 N+1. 5분 캐시(`:367`)로 완화.
- **권장 수정**: 루프 내 쿼리에 `.prefetch_related('entities')` 추가, 또는 심볼 전체를 단일 in-쿼리로.
- **심각도**: HIGH (캐시로 실질 MED 수준 완화) / **난이도**: 중간

---

### [MED-1] `StockCompleteDataAPIView` 무prefetch + 무캐시 (stocks)

- **위치**: `packages/shared/stocks/views.py:909-968` (특히 `:922, :932`)
- **문제 코드**:
  ```python
  stock = get_object_or_404(Stock, symbol=symbol.upper())  # :922, prefetch 전무
  overview_data = OverviewTabSerializer(stock).data         # :932 → +7 쿼리
  ```
- **설명**: HIGH-4와 동일한 `OverviewTabSerializer` 사용처이나 **캐시가 없어** 매 요청마다 `overview_ko` + 역참조 6개 = +7 쿼리. balance/income/cashflow 각 1쿼리는 정상.
- **권장 수정**: `:922`를 `select_related(...).prefetch_related("category_signals")` 포함 쿼리로 교체.
- **심각도**: MED (캐시 없음으로 HIGH 성향이나 호출 빈도 낮음) / **난이도**: 쉬움

### [MED-2] 포트폴리오 요약 Python 루프 집계 (users)

- **위치**: `packages/shared/users/views.py:367, 383-385, 393, 419, 429`
- **문제 코드**:
  ```python
  for portfolio in portfolios:
      total_value += portfolio.total_value   # 모델 프로퍼티
  ```
- **설명**: queryset은 `select_related("stock")`라 FK 추가 쿼리는 없으나, 동일 queryset이 `.exists()`(:367) + 순회(:383) + `.count()`(:393)로 여러 번 평가될 수 있음. DB `Sum` aggregate 한 번이면 끝날 계산을 Python 루프로 수행. (patch 핸들러 `:476`은 이미 aggregate 사용.)
- **권장 수정**: `aggregate(Sum(F('quantity')*F('stock__real_time_price')))`.
- **심각도**: MED / **난이도**: 중간

### [MED-3] `UserFavorites.get()` StockSerializer N+1 가능 (users)

- **위치**: `packages/shared/users/views.py:197-200`
- **문제 코드**: `favorite_stocks = user.favorite_stock.all()` → `StockSerializer(..., many=True)`. M2M 자체는 1쿼리지만 StockSerializer 내부 FK 접근 시 N+1 가능. 단일 사용자 범위라 영향 제한적.
- **권장 수정**: 필요 시 `select_related`/`prefetch_related`.
- **심각도**: MED / **난이도**: 쉬움

### [MED-4] `collection_logs` by_provider 루프 내 count (news)

- **위치**: `news/api/views.py:1395-1399`
- **문제 코드**:
  ```python
  for row in provider_agg:
      error_runs = qs.filter(provider=row['provider'], errors__gt=0).count()  # provider마다
  ```
- **설명**: provider 수만큼 추가 count 쿼리. provider 수가 적고(보통 2~3) 캐시(`:1443`)되어 영향 제한적.
- **권장 수정**: `Count('id', filter=Q(errors__gt=0))` annotate로 단일 쿼리화.
- **심각도**: MED / **난이도**: 중간

### [MED-5] `DataBasketSerializer.get_can_add_item` 추가 쿼리 (rag_analysis)

- **위치**: `rag_analysis/serializers.py:47-51` + 모델 `can_add_item()`
- **설명**: `DataBasketListCreateView`(`views.py:50`)는 `prefetch_related('items')`로 items는 커버하나, `can_add_item()`/`current_units`/`remaining_units`가 items count를 별도 쿼리로 수행하면 basket마다 추가 쿼리.
- **권장 수정**: 프로퍼티가 prefetch된 `items`를 재사용하도록 확인, 아니면 annotate.
- **심각도**: MED / **난이도**: 중간

### [MED-6] `DataBasketListCreateView` / `AnalysisSessionListCreateView` 페이지네이션 누락 (rag_analysis)

- **위치**: `rag_analysis/views.py:50-51, 378-379`
- **설명**: 사용자별 목록 전체를 `many=True` 반환. 사용자당 개수는 제한적이나 상한 없음.
- **권장 수정**: DRF 페이지네이션.
- **심각도**: MED / **난이도**: 쉬움

### [MED-7] `AdminNewsCategoryView` resolve_symbols 루프 (serverless)

- **위치**: `serverless/views_admin.py:477-478`
- **문제 코드**:
  ```python
  for cat in categories:
      symbols = cat.resolve_symbols()  # 카테고리마다 SP500Constituent 등 조회
  ```
- **설명**: `resolve_symbols()`가 sector/sub_sector를 SP500Constituent에서 해석 → 카테고리 N개마다 쿼리. 카테고리 수 적고(수십) admin 전용이라 빈도 낮음. 캐시 없음.
- **권장 수정**: 카테고리 수가 커지면 sector→symbols 맵을 한 번 빌드해 재사용.
- **심각도**: MED / **난이도**: 중간

### [MED-8] `ValidationSummaryView` rank_metrics 루프 (validation)

- **위치**: `validation/api/views.py:121-133`
- **문제 코드**:
  ```python
  for mc in rank_metrics:   # 5개 고정
      delta = CompanyBenchmarkDelta.objects...first()
      md = MetricDefinition.objects.filter(pk=mc).first()
  ```
- **설명**: 5개 고정이라 10쿼리. 작지만 bulk 가능. 캐시 없음.
- **권장 수정**: `metric_code_id__in=rank_metrics` 일괄 조회.
- **심각도**: MED / **난이도**: 중간

### [MED-9] `ChainSightGraphView` edge별 ORM 단건 조회 (chainsight)

- **위치**: `apps/chain_sight/api/views.py:78-91`
- **문제 코드**:
  ```python
  for edge in result.get("edges", []):
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()    # edge마다
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()  # edge마다
  ```
- **설명**: Neo4j에서 받은 edge 수만큼 Postgres 단건 쿼리 2회씩. depth=3이면 edge 수십~수백 개 가능, 캐시 없음.
- **권장 수정**: edge 쌍 전체를 모아 `filter(Q(...)|...)` 단일 쿼리로 bulk fetch 후 dict 매핑.
- **심각도**: MED (depth↑ 시 HIGH) / **난이도**: 중간

### [MED-10] sec_pipeline 시계열 필터 인덱스 누락 (sec_pipeline)

- **위치**: `sec_pipeline/models.py:103`(`SupplyChainEvidence.extracted_at`), `:181`(`BusinessModelSnapshot.created_at`)
- **근거**: `quality_checks.py:50,68` 및 `intelligence.py:84,110`에서 `filter(extracted_at__gte=since)` / `filter(created_at__gte=since)`로 품질 모니터링 배치가 주기적으로 시간범위 스캔. 두 필드 모두 `db_index` 없음.
- **권장 수정**: `SupplyChainEvidence`에 `Index(fields=["extracted_at"])`, `BusinessModelSnapshot`에 `Index(fields=["created_at"])` 추가 (마이그레이션 1건).
- **심각도**: MED / **난이도**: 쉬움

---

### [LOW] 경미 항목 (모니터링 권장)

| # | 위치 | 이슈 | 난이도 |
|---|------|------|--------|
| L1 | `stocks/views_mvp.py:41-62` | `StockMVPListView` summary 모드 페이지네이션 없음 (단 `[:20]` 상한으로 보호) | 쉬움 |
| L2 | `stocks/views_indicators.py:60-70` | `period=max`일 때 종목 전체 일봉 로드 (5분 캐시 완화, `.values()` 사용) | 쉬움 |
| L3 | `serverless/models.py:925` `StockRelationship` | filter(source_symbol+type) + order_by(-strength) 인덱스 분리 — 3컬럼 복합 후보 | 쉬움 |
| L4 | `sec_pipeline/models.py:281` `CompanyAlias` | `alias__iexact` 핫패스에 표현식 인덱스 필요 (현재 데이터 0건 → 즉시 조치 불필요) | 중간 |
| L5 | `rag_analysis/models.py:192` `AnalysisMessage` | session+created_at 복합 인덱스 (대화 길어지면) | 쉬움 |
| L6 | `stocks/models.py:147` `Stock.last_api_call` | 현재 단일 인스턴스 비교만 — queryset 필터 도입 시에만 db_index 추가 | 쉬움 |
| L7 | `validation/api/views.py:157` `_find_leader` | peers.count() 후 인덱싱으로 동일 queryset 재평가 (소규모) | 쉬움 |

---

## 모범 사례 (양호 확인)

감사 중 **올바르게 작성된 패턴**도 확인했으며, 향후 수정 시 참고 기준:

- **`stocks/views_eod.py:76-83`** `EODSignalDetailView` — 루프 내 `s.stock.stock_name` FK 접근을 `select_related("stock")`로 정확히 방어 + `[:50]` 상한. N+1 회피 모범.
- **`apps/chain_sight/api/views.py:463, 619`** `SectorGraphView`/`NeighborGraphView` — `Stock.objects.filter(symbol__in=...)` bulk fetch 후 dict 매핑.
- **인덱스 설계 전반** — `DailyPrice`(stock+date, -date), `NewsArticle`(-published_at+category), `EODSignal`(4종), `Portfolio`/`Watchlist`(user+-updated_at), `UsageLog`(4종) 등 시계열 정렬·choice 필터를 복합 인덱스로 선제 커버. **HIGH 등급 인덱스 누락 0건**.
- **외부 API 위임 뷰** — `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`, `views_exchange.py`, `macro/views.py`, `sec_pipeline/views.py`는 FMP/서비스 응답(dict)을 plain serializer로 포맷 → DB N+1 없음 (단 일부 외부 API 캐시 미적용은 rate-limit 관점 별도 이슈).

---

## 부록: 감사 대상 파일 (24개)

**뷰 17개**: `packages/shared/stocks/views.py`, `views_search.py`, `views_exchange.py`, `views_eod.py`, `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`, `views_indicators.py`, `views_mvp.py`, `packages/shared/users/views.py`, `news/api/views.py`, `macro/views.py`, `rag_analysis/views.py`, `serverless/views_admin.py`, `validation/api/views.py`, `apps/chain_sight/api/views.py`, `sec_pipeline/views.py`

**모델 7개**: `packages/shared/stocks/models.py`, `packages/shared/users/models.py`, `news/models.py`, `serverless/models.py`, `rag_analysis/models.py`, `sec_pipeline/models.py`, `services/_dormant/graph_analysis/models.py`

**연계 Serializer**: stocks(`serializers.py`, `_fundamentals`, `_market_movers`, `_exchange`, `_screener`), `news/api/serializers.py`, `rag_analysis/serializers.py`, `macro/serializers.py`, `packages/shared/users/serializers.py`
