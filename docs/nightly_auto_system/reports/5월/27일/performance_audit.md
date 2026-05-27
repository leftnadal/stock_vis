# API 성능 감사 보고서

- **생성일**: 2026-05-27
- **대상**: Django 뷰 17개 + 시리얼라이저 12개 + 모델 7개
- **검사 범위**: N+1 쿼리, select_related/prefetch_related 누락, 인덱스 누락, 느린 SerializerMethodField, 페이지네이션 누락
- **모드**: 읽기 전용 감사 (코드 수정 없음)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 합계 | N+1 | select_related 누락 | 페이지네이션 누락 | 느린 Serializer | 인덱스 누락 |
|--------|------|-----|---------------------|-------------------|-----------------|-------------|
| **HIGH** | 19 | 9 | 0 | 4 | 2 | 4 |
| **MED** | 19 | 3 | 5 | 4 | 4 | 3 |
| **LOW** | 5 | 0 | 0 | 0 | 5 | 0 |
| **합계** | **43** | **12** | **5** | **8** | **11** | **7** |

### 즉시 수정 권장 P0 (HIGH × 쉬움/중간)

1. `users/views.py:374-409` — Portfolio 합계 계산을 Python 루프에서 ORM Aggregate로 전환 (쿼리 80% 감소)
2. `stocks/serializers.py:205-300` — `get_dynamic_layers()` 6개 reverse FK/OneToOne → prefetch_related 적용 필수 (쿼리 6배 감소)
3. `stocks/views_mvp.py:29-41` — `[:20]` 하드코딩 제거, pagination_class 도입
4. `news/api/views.py:345-358` — `trending()` 루프 내 symbol별 NewsArticle 조회 → `__in` 일괄 조회
5. `rag_analysis/views.py:298-340` — `_get_data_snapshot()` 루프 외부에서 사전 로드
6. `chainsight/api/views.py:74-87` — edge별 `CoMentionEdge` + `PriceCoMovement` 개별 조회 → bulk 로드
7. `validation/api/views.py:112-124, 204-208, 364-365` — `MetricDefinition` 루프 내 개별 조회 → `pk__in` 일괄 조회
8. `serverless/serializers.py:88-137` — `MarketMoverListSerializer`의 `IndicatorCalculator` 인스턴스 N×3회 생성 → `__init__`에서 1회

---

## 상세

### 1. N+1 쿼리 (12건)

#### 1.1 [HIGH] `stocks/views.py:213-226` — UserFavorites 즐겨찾기 직렬화
- **현재 동작**: `user.favorite_stock.all()` 반환 후 `StockSerializer(many=True)`. 시리얼라이저 내부 `get_dynamic_layers()`가 종목별로 6개 reverse FK/OneToOne을 접근.
- **수정 난이도**: 중간
- **권장 수정**: `favorite_stock.all().prefetch_related('category_signals', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')`

#### 1.2 [HIGH] `stocks/views.py:215-226, 240-244` — AddFavorite / RemoveFavorite
- **현재 동작**: `if stock in user.favorite_stock.all():` — M2M 전체 로딩 후 in 체크.
- **수정 난이도**: 쉬움
- **권장 수정**: `user.favorite_stock.filter(id=stock.id).exists()`

#### 1.3 [HIGH] `users/views.py:374-376` — PortfolioSummaryView
- **현재 동작**: `for portfolio in portfolios: total_value += portfolio.total_value` — `total_value`가 계산 프로퍼티면 종목별 추가 쿼리.
- **수정 난이도**: 중간
- **권장 수정**: `Portfolio.objects.filter(user=request.user).select_related('stock').aggregate(total_value=Sum(F('quantity') * F('stock__real_time_price')), total_cost=Sum(F('quantity') * F('average_price')))`

#### 1.4 [HIGH] `users/views.py:409` — PortfolioDetailTableView
- **현재 동작**: `sum(p.total_value for p in portfolios)` — 동일 N+1 패턴.
- **수정 난이도**: 중간
- **권장 수정**: `.aggregate(total=Sum(F('quantity') * F('stock__real_time_price')))`

#### 1.5 [HIGH] `stocks/views_indicators.py:324-330` — IndicatorComparisonView
- **현재 동작**: `for symbol in symbols: stock = Stock.objects.get(symbol=symbol)` — 심볼별 별도 쿼리.
- **수정 난이도**: 중간
- **권장 수정**: `Stock.objects.filter(symbol__in=[s.upper() for s in symbols])` 후 dict 매핑.

#### 1.6 [HIGH] `news/api/views.py:345-358` — trending()
- **현재 동작**: trending symbol 10개 각각에 대해 `NewsArticle.objects.filter(entities__symbol=symbol)` 호출. 10 symbol = 11 쿼리 + entities N+1.
- **수정 난이도**: 중간
- **권장 수정**: `NewsArticle.objects.filter(entities__symbol__in=symbols, published_at__gte=from_date).prefetch_related('entities').distinct()` 후 Python에서 symbol별 분류.

#### 1.7 [MED] `news/api/views.py:1386-1398` — pipeline_health() provider_agg
- **현재 동작**: `for row in provider_agg: qs.filter(provider=row['provider'], errors__gt=0).count()` — provider 수만큼 추가 count 쿼리.
- **수정 난이도**: 중간
- **권장 수정**: `qs.filter(errors__gt=0).values('provider').annotate(error_count=Count('id'))` 후 dict 매핑.

#### 1.8 [HIGH] `rag_analysis/views.py:298-340, 237-281` — `_get_data_snapshot()` 루프
- **현재 동작**: `for data_type in data_types: _get_data_snapshot()` — 각 호출이 `Stock`, `DailyPrice`, `IncomeStatement`, `BalanceSheet` 등 4~5개 쿼리. 3개 타입 선택 시 12~15쿼리.
- **수정 난이도**: 높음
- **권장 수정**: 루프 진입 전 stock/latest_price/income/balance를 1회 로드 후 헬퍼에 주입.

#### 1.9 [HIGH] `serverless/views_admin.py:475-497` — AdminNewsCategoryView.get()
- **현재 동작**: `for cat in NewsCollectionCategory.objects.all(): cat.resolve_symbols()` — 카테고리별 심볼 해석 호출.
- **수정 난이도**: 높음
- **권장 수정**: `resolve_symbols()` 내부의 쿼리를 bulk 형태로 외부에서 1회 수집 후 매핑.

#### 1.10 [HIGH] `validation/api/views.py:112-124, 204-208, 364-365` — MetricDefinition 개별 조회
- **현재 동작**: 3곳에서 `for mc in metric_codes: MetricDefinition.objects.filter(pk=mc).first()` — 지표당 1쿼리.
- **수정 난이도**: 중간
- **권장 수정**: `defs = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_codes)}` 후 dict 조회.

#### 1.11 [HIGH] `validation/api/views.py:265-276` — Peer Snapshot 루프
- **현재 동작**: `for s in snaps: PeerMetricBenchmark.objects.filter(...)` — 스냅샷 N개당 추가 쿼리.
- **수정 난이도**: 높음
- **권장 수정**: snapshot pk 일괄 수집 후 `PeerMetricBenchmark.objects.filter(snapshot_id__in=...)`로 일괄 로드.

#### 1.12 [CRITICAL/HIGH] `chainsight/api/views.py:74-87` — co-mention edges
- **현재 동작**: Neo4j 응답 edge 리스트를 순회하며 edge마다 `CoMentionEdge.objects.filter()` + `PriceCoMovement.objects.filter()` 호출. edge N개 = 2N 쿼리.
- **수정 난이도**: 높음
- **권장 수정**: edge 쌍 (symbol_a, symbol_b) 튜플 리스트 수집 후 `Q(...)|Q(...)` 일괄 OR 쿼리로 1회 로드 + 클라이언트 측 매핑.

---

### 2. select_related / prefetch_related 누락 (5건)

#### 2.1 [MED] `stocks/views.py:502-504` — StockOverviewAPIView
- **현재**: `Stock.objects.select_related('overview_ko')` 만 적용.
- **수정 난이도**: 쉬움
- **권장 수정**: `.prefetch_related('category_signals', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')` 추가.

#### 2.2 [MED] `users/views.py:264, 404-406, 655, 819` — Portfolio/Watchlist 4건
- **현재**: `select_related('stock')` 만 있고 `stock__overview_ko` 누락.
- **수정 난이도**: 쉬움
- **권장 수정**: `select_related('stock', 'stock__overview_ko')` 또는 `Prefetch('items', queryset=WatchlistItem.objects.select_related('stock', 'stock__overview_ko'))`.

#### 2.3 [MED] `chainsight/api/views.py:391, 529` — Stock bulk 매핑
- **현재**: `{s.symbol: s for s in Stock.objects.filter(symbol__in=tickers)}` — 모든 필드 로드.
- **수정 난이도**: 쉬움
- **권장 수정**: `.values('symbol', 'stock_name', 'change_percent', 'sector', 'industry', 'market_capitalization')`로 필드 한정.

#### 2.4 [MED] `chainsight/api/views.py:150-154` — co_mentions union
- **현재**: 두 개의 쿼리 union.
- **수정 난이도**: 쉬움
- **권장 수정**: `CoMentionEdge.objects.filter(Q(symbol_a=symbol) | Q(symbol_b=symbol))` 단일 쿼리.

#### 2.5 [MED] `serverless/serializers.py:531-535` — ScreenerAlertSerializer.preset FK
- **현재**: `obj.preset.icon`, `obj.preset.name` 접근. 뷰에서 `select_related('preset')` 보장 필요.
- **수정 난이도**: 쉬움
- **권장 수정**: ScreenerAlert 쿼리셋에 `.select_related('preset')` 확인/추가.

---

### 3. 페이지네이션 누락 (8건)

#### 3.1 [HIGH] `stocks/views_mvp.py:29-41` — StockMVPListView
- **현재**: `queryset = Stock.objects.all()` 후 `[:20]` 하드코딩. 클라이언트 페이지 이동 불가.
- **수정 난이도**: 쉬움
- **권장 수정**: `PageNumberPagination(page_size=20, max_page_size=100)` 설정 + `paginator.paginate_queryset()` 사용.

#### 3.2 [HIGH] `users/views.py:92-94` — Users 관리자 목록
- **현재**: `User.objects.all()` 전건 반환.
- **수정 난이도**: 쉬움
- **권장 수정**: `PageNumberPagination(page_size=50)` 적용.

#### 3.3 [MED] `users/views.py:974-987` — UserInterestListCreateView.get()
- **현재**: `UserInterest.objects.filter(user=...).order_by(...)` 전건 반환.
- **수정 난이도**: 쉬움
- **권장 수정**: `paginate_queryset()` 적용 후 list comprehension은 page 대상으로만.

#### 3.4 [MED] `serverless/views_admin.py:472-497` — AdminNewsCategoryView
- **현재**: 모든 NewsCollectionCategory 메모리 리스트 변환.
- **수정 난이도**: 쉬움
- **권장 수정**: `pagination_class = CategoryPagination(page_size=50)` 적용.

#### 3.5 [MED] `validation/api/views.py:429` — PresetListView
- **현재**: `PeerPreset.objects.filter(symbol_id=symbol).order_by('preset_key')` 전건.
- **수정 난이도**: 쉬움
- **권장 수정**: `pagination_class` 추가 또는 `[:50]` 제한.

#### 3.6 [MED] `chainsight/api/views.py:631-660` — SignalFeedView
- **현재**: `_build_chain_signals()` 내부 수동 슬라이싱. 메모리 비효율.
- **수정 난이도**: 중간
- **권장 수정**: 정식 DRF Paginator 도입.

#### 3.7 [HIGH] `news/api/views.py` `trending()` — 위 1.6과 결합되는 페이지네이션 부재
- **현재**: 상위 10개 하드코딩이나 클라이언트 페이지 이동 불가.
- **수정 난이도**: 쉬움
- **권장 수정**: `limit` 쿼리 파라미터 + 최대값 제한.

#### 3.8 [HIGH] `stocks/views.py:213-226` — UserFavorites
- **현재**: 즐겨찾기 전건 반환. 1000+ 보유 시 응답 폭증.
- **수정 난이도**: 쉬움
- **권장 수정**: PageNumberPagination 추가.

---

### 4. 느린 SerializerMethodField (11건)

#### 4.1 [HIGH] `stocks/serializers.py:205-300` — OverviewTabSerializer.get_dynamic_layers
- **현재**: 메서드 내부에서 `obj.category_signals.all()` + `obj.validation_news_summary` + `obj.sensitivity_profile` + `obj.growth_stage` + `obj.capital_dna` + `obj.narrative_tag` 등 6개 관계 직접 접근. 뷰의 prefetch_related가 없으면 종목당 6 쿼리.
- **수정 난이도**: 높음 (뷰와 쌍으로 변경)
- **권장 수정**: 뷰 쿼리셋에 `prefetch_related` 강제. 시리얼라이저는 이미 로드된 데이터만 사용.

#### 4.2 [HIGH] `serverless/serializers.py:88-137` — MarketMoverListSerializer
- **현재**: 3개 SerializerMethodField가 각각 `IndicatorCalculator()` 인스턴스 신규 생성. N항목 × 3 = 3N 객체 생성/계산.
- **수정 난이도**: 중간
- **권장 수정**: `__init__`에서 `self.calc = IndicatorCalculator()` 1회 생성 또는 DB 레벨 `annotate(Case/When)`으로 포맷 전가.

#### 4.3 [MED] `stocks/serializers.py:190-203` — get_korean_overview
- **현재**: `obj.overview_ko` 접근. select_related 미보장 시 N+1.
- **수정 난이도**: 쉬움 (뷰 측)
- **권장 수정**: 뷰에서 `select_related('overview_ko')` 보장.

#### 4.4 [MED] `serverless/serializers.py:208-219` — MarketBreadthSerializer.signal_interpretation
- **현재**: 메서드 호출마다 `MarketBreadthService()` 신규 생성.
- **수정 난이도**: 중간
- **권장 수정**: `__init__`에서 서비스 인스턴스화.

#### 4.5 [MED] `serverless/serializers.py:419-422` — SectorPerformanceSerializer.name_ko
- **현재**: 매번 `SectorHeatmapService.SECTOR_NAMES_KO` 접근. 부하는 낮으나 패턴 일관성.
- **수정 난이도**: 중간
- **권장 수정**: `__init__`에서 사전 로드.

#### 4.6 [MED] `serverless/serializers.py:501-554` — ScreenerAlertSerializer
- **현재**: `get_preset_name()`이 `obj.preset.*` FK 접근 → select_related 미적용 시 N+1.
- **수정 난이도**: 쉬움
- **권장 수정**: 뷰 쿼리셋 `select_related('preset')` (위 2.5와 동일 항목).

#### 4.7 [MED] `rag_analysis/serializers.py:29-34, 46-50` — DataBasketSerializer
- **현재**: `can_add_item`, `max_units` 등 메서드 호출. 가벼우나 N항목에서 일관성.
- **수정 난이도**: 중간
- **권장 수정**: 메서드 비용 확인 후 필요 시 캐싱.

#### 4.8 [LOW × 4] 기타 단순 계산 필드
- `stocks/serializers.py:65-71` (StockHeaderSerializer 포맷 필드), `serverless/serializers.py` 형식 필드 3건 — 순수 계산, 이슈 없음.

---

### 5. 인덱스 누락 (7건)

#### 5.1 [HIGH] `stocks/models.py:863` — PipelineLog.status
- **현재**: `Meta.indexes`에 `['-date', 'status']` 복합만 있음. 단독 status 조회 빈번.
- **수정 난이도**: 쉬움
- **권장 수정**: `status = models.CharField(..., db_index=True)`.

#### 5.2 [HIGH] `news/models.py:82-86` — NewsArticle.category
- **현재**: `Meta.indexes`에 `(category, -published_at)` 복합만. `news_classifier.py:295/301/349`에서 단독 필터.
- **수정 난이도**: 쉬움
- **권장 수정**: `category = models.CharField(..., db_index=True)`.

#### 5.3 [MED] `news/models.py:432-437` — DailyNewsKeyword.status
- **현재**: `(-date, status)` 복합 인덱스만. status 단독 조회 시 인덱스 미활용.
- **수정 난이도**: 쉬움
- **권장 수정**: `status = models.CharField(..., db_index=True)`.

#### 5.4 [HIGH] `rag_analysis/models.py:247-252` — UsageLog (user, -created_at)
- **현재**: `Meta.indexes`에 `(user, created_at)` 정순만. `views.py:701-704`에서 `order_by('-created_at')` 사용 → 역순 인덱스 부재로 정렬 비용.
- **수정 난이도**: 쉬움
- **권장 수정**: `models.Index(fields=['user', '-created_at'])` 추가.

#### 5.5 [MED] `rag_analysis/models.py:138-154` — AnalysisSession 인덱스 부재
- **현재**: `Meta.indexes` 미정의. `views.py:379`에서 `user` 단독 필터 빈번 (FK 자동 인덱스로 일부 커버되나 정렬 미커버).
- **수정 난이도**: 쉬움
- **권장 수정**: `indexes = [Index(fields=['user', '-updated_at']), Index(fields=['user', 'status'])]`.

#### 5.6 [MED] `users/models.py:27-28` — Portfolio (user, -updated_at)
- **현재**: unique_together + 인덱스 2종 있으나 (user, -updated_at) 복합 없음. `views.py:404, 599`에서 정렬 빈번.
- **수정 난이도**: 쉬움
- **권장 수정**: `models.Index(fields=['user', '-updated_at'])` 추가.

#### 5.7 [MED] `serverless/models.py:1407` — AdminActionLog.action 단독 조회
- **현재**: `(-created_at, action)` 복합 인덱스만. action 단독 조회는 인덱스 미활용.
- **수정 난이도**: 쉬움
- **권장 수정**: 단독 조회 빈도 확인 후 `action`에 `db_index=True` 추가 검토.

#### 이미 적절히 인덱싱된 모델 (변경 불필요)
- `stocks/models.py` StockNews(symbol, -published_at), `news/models.py` NewsArticle.llm_analyzed/NewsEntity(symbol, entity_type)/SentimentHistory(symbol, -date), `serverless/models.py` MarketMover(date, mover_type)/StockKeyword.status/ScreenerAlert(user, is_active)/CategoryCache(symbol, date), `sec_pipeline/models.py` SupplyChainEvidence.neo4j_dirty/UnmatchedCompanyQueue.status/FilingProcessLog(symbol, stage, -started_at), `graph_analysis/models.py` 전체 3개 모델.

---

## 우선순위별 권장 조치표

| 우선순위 | 카테고리 | 위치 | 예상 효과 | 난이도 |
|----------|----------|------|-----------|--------|
| P0 | N+1 | `users/views.py:374-409` Portfolio 합계 | 쿼리 O(n) → O(1), 80% 감소 | 중간 |
| P0 | Serializer | `stocks/serializers.py:205-300` dynamic_layers | 종목당 6 쿼리 → 0 | 높음 |
| P0 | N+1 | `chainsight/api/views.py:74-87` edges | edge N개 → 1 쿼리 | 높음 |
| P0 | N+1 | `validation/api/views.py:112/204/364` MetricDefinition | 지표당 1쿼리 → 1회 | 중간 |
| P0 | N+1 | `news/api/views.py:345-358` trending | symbol당 1쿼리 → 1회 | 중간 |
| P0 | N+1 | `rag_analysis/views.py:298-340` snapshot | 타입당 N쿼리 → 1회 | 높음 |
| P0 | Serializer | `serverless/serializers.py:88-137` MarketMover | 항목당 3 인스턴스 → 1 | 중간 |
| P1 | Pagination | `stocks/views_mvp.py:29-41` MVP 목록 | 메모리 제한 | 쉬움 |
| P1 | Pagination | `users/views.py:92` Users 관리자 | 메모리 제한 | 쉬움 |
| P1 | select_related | `users/views.py:264/404/655/819` Portfolio/Watchlist | 쿼리 5개 감소/stock | 쉬움 |
| P1 | Index | `rag_analysis` UsageLog `(user, -created_at)` | 정렬 비용 ↓ | 쉬움 |
| P1 | Index | `stocks` PipelineLog.status | 단독 필터 가속 | 쉬움 |
| P1 | Index | `news` NewsArticle.category | 분류기 필터 가속 | 쉬움 |
| P2 | N+1 | `stocks/views_indicators.py:324-330` | 심볼당 1쿼리 → 1회 | 중간 |
| P2 | N+1 | `news/api/views.py:1386-1398` pipeline_health | provider당 count → 1쿼리 | 중간 |
| P2 | Pagination | UserInterest / AdminCategory / PresetList / SignalFeed | 응답 크기 제한 | 쉬움~중간 |
| P3 | Serializer | MarketBreadth/SectorPerformance/ScreenerAlert | 마이크로 최적화 | 중간 |
| P3 | Index | Portfolio(user, -updated_at) / AnalysisSession / AdminActionLog | 정렬/필터 가속 | 쉬움 |

---

## 미발견 카테고리

- raw SQL 사용 없음.
- 직렬화 내 `.count()` 직접 호출 없음.
- macro/views.py + macro/serializers.py + sec_pipeline/views.py + news/api/serializers.py — 이슈 없음 (Service 패턴 + 단순 조회/Celery 트리거).

---

## 검증 메모

- 본 보고서는 정적 분석 기반. 실측 쿼리 카운트는 `django-debug-toolbar` 또는 `assertNumQueries` 테스트로 별도 검증 필요.
- HIGH 항목 수정 전후 `pytest --num-queries` (또는 `connection.queries`)로 회귀 확인 권장.
- `stocks/serializers.py:205-300`은 시리얼라이저 단독 수정으로는 해결 불가 — 호출 뷰 측에서 `prefetch_related` 동시 적용 필요 (쌍으로 변경).
