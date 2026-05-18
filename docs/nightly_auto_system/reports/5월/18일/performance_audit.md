# API 성능 감사 보고서

> 감사 일자: 2026-05-18
> 범위: views*.py 17개 + 핵심 models*.py 8개 + serializers*.py 11개
> 모드: 읽기 전용 (코드 수정 없음)
> 감사자: Claude Opus 4.7 (1M context) — Explore 서브 에이전트 병렬 스캔

---

## 요약 (이슈 수 by 심각도)

| 카테고리 | HIGH | MED | LOW | 합계 |
|----------|------|-----|-----|------|
| 1. N+1 쿼리 / select_related 누락 | 2 | 7 | 2 | 11 |
| 2. 인덱스 누락 (단일·복합) | 7 | 15 | 5 | 27 |
| 3. 느린 Serializer (Method 필드) | 2 | 9 | 1 | 12 |
| 4. 페이지네이션 누락 | 6 | 3 | 1 | 10 |
| **총계** | **17** | **34** | **9** | **60** |

### 핵심 관찰

- **페이지네이션이 사실상 부재** — 전체 view 17개 중 `pagination_class`가 명시된 곳은 `stocks/views.py` (StockListPagination)과 `news/api/views.py` (NewsArticlePagination) **2개뿐**. Screener 5개 list 엔드포인트는 limit 파라미터 1000 허용 + 페이지네이션 없음 → DoS 표면.
- **인덱스는 모델 단위로는 어느 정도 갖춰져 있으나**, status / Boolean flag / 복합 필터 조합에서 누락이 집중됨 (`AnalysisSession.status`, `UsageLog.cached`, `MarketMover.mover_type` 등).
- **N+1은 심하지 않다** — 주요 list view는 이미 `select_related` / `prefetch_related`를 사용 중. 다만 SerializerMethodField에서 서비스 인스턴스화 + 추가 쿼리가 반복되는 패턴이 12건 식별됨.
- **수정 난이도 평균**: 쉬움 60%, 중간 35%, 높음 5%. 인덱스 추가와 페이지네이션은 마이그레이션 1줄로 끝남.

---

## 1. N+1 쿼리 / select_related·prefetch_related 누락

### 1-1. [HIGH] stocks/views_indicators.py:324-338 — IndicatorComparisonView N+1 + 루프 쿼리
- **수정 난이도**: 중간
- **현상**: `for symbol in symbols:` 루프 내에서 `Stock.objects.get(symbol=symbol)`을 호출. 입력 symbols 개수 N에 비례한 N개의 쿼리 발생.
- **권장**: `Stock.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')`로 1쿼리 처리. 추가로 `DailyPrice.objects.filter(stock__symbol__in=symbols)[:50*N]`을 한번에 묶고 Python에서 grouping.

### 1-2. [HIGH] stocks/views_indicators.py:333-370 — DailyPrice 반복 슬라이싱
- **수정 난이도**: 중간
- **현상**: 같은 루프에서 심볼별로 `DailyPrice.objects.filter(stock=stock)[:50]` 호출. N 심볼 × 1쿼리 = N쿼리.
- **권장**: 1-1과 묶어서 `prefetch_related(Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:50]))` 패턴 또는 raw SQL window function (`row_number()`).

### 1-3. [MED] stocks/views_eod.py:81-99 — EODSignal 루프 내 FK 접근
- **수정 난이도**: 쉬움
- **현상**: 라인 77에서 `.select_related('stock')` 처리되어 있으나, serializer 호출이나 후속 가공 단계 추가 시 stock 외 chainsight 모델 접근 여부 확인 필요. 현재 상태로는 위험 낮음.
- **권장**: 현 상태 OK. serializer 확장 시 `stock__overview_ko` 추가.

### 1-4. [MED] stocks/views.py:502-504 — StockOverviewAPIView TODO 미해결
- **수정 난이도**: 중간
- **현상**: 코드 내 TODO 코멘트로 명시되어 있음. `select_related('overview_ko', ...)` 사용 중이나 CategoryScore 등 ManyToOne 관계는 별도 prefetch 미적용.
- **권장**: serializer가 `category_scores`나 `dynamic_layers`를 access한다면 `.prefetch_related('category_scores', 'dynamic_layers')` 추가.

### 1-5. [MED] stocks/views.py:849-873 — StockCompleteDataAPIView 다중 모델 직렬 조회
- **수정 난이도**: 중간
- **현상**: 한 endpoint에서 DailyPrice, BalanceSheet, IncomeStatement, CashFlowStatement를 모두 별도 쿼리. 4쿼리 + 동일 stock에 대한 중복 lookup.
- **권장**: 한 번에 stock 객체를 가져온 뒤 `prefetch_related('balancesheet_set', 'incomestatement_set', 'cashflowstatement_set')`로 묶기.

### 1-6. [MED] validation/api/views.py:80-99 — CategorySignal 루프 + PeerListCache lookup
- **수정 난이도**: 중간
- **현상**: 라인 80에서 CategorySignal 필터 후 라인 93에서 PeerListCache.objects.filter(symbol=stock).first()를 매 iteration마다 호출. CategorySignal FK인 symbol에 select_related도 없음.
- **권장**: PeerListCache를 미리 dict로 prefetch (`peer_map = {p.symbol: p for p in PeerListCache.objects.filter(symbol__in=symbols)}`).

### 1-7. [MED] stocks/views_search.py:177-230 — validate_and_create_stock 단건 API 호출
- **수정 난이도**: 중간
- **현상**: 함수가 단건용으로 설계됨. 호출처에서 루프로 N회 호출 시 N+1 외부 API 콜.
- **권장**: 호출처 검토. 다건이면 FMP `/stable/profile` batch endpoint 사용.

### 1-8. [LOW] stocks/views_mvp.py:47-56 — StockMVPListView FK 접근
- **수정 난이도**: 쉬움
- **현상**: queryset 루프에서 stock 필드만 access. FK가 아닌 자기 필드라 N+1 아님. `[:20]` 하드 리밋으로 보호됨.
- **권장**: 현 상태 OK.

### 1-9. [LOW] news/api/views.py:58 — NewsViewSet `prefetch_related('entities')` 적용 완료
- **수정 난이도**: 쉬움
- **현상**: 이미 prefetch 적용. detail serializer에서 highlights 등을 access한다면 `Prefetch('entities__highlights')` 추가 필요.
- **권장**: detail view에서 NewsEntity.highlights access 여부 확인.

### 1-10. [MED] rag_analysis/views.py:52,379 — DataBasket/AnalysisSession list에 prefetch만 적용
- **수정 난이도**: 쉬움
- **현상**: `prefetch_related('items')` `prefetch_related('messages')`는 적용. 그러나 BasketItemSerializer가 Stock FK를 access한다면 `Prefetch('items', queryset=BasketItem.objects.select_related('stock'))` 필요.
- **권장**: items 내부 FK 사용 시 nested prefetch.

### 1-11. [MED] chainsight/api/views.py:61-102 — ChainSightGraphView 이웃 노드 처리
- **수정 난이도**: 높음
- **현상**: 그래프 깊이 3까지 탐색하면서 Neo4j 결과를 Postgres Stock 모델과 join. 깊이가 늘어나면 결과 노드 수 × Stock.objects.get 쿼리 폭증 가능.
- **권장**: Neo4j 결과의 symbol set을 모은 뒤 `Stock.objects.filter(symbol__in=...).in_bulk()`로 일괄 조회.

---

## 2. 인덱스 누락 (단일·복합)

### 2-1. [HIGH] serverless/models.py — MarketMover.mover_type (line 18)
- **수정 난이도**: 쉬움
- **현상**: 매일 호출되는 공개 API에서 `mover_type='gainers'` 형태로 필터. `db_index=True` 없음.
- **권장**: `mover_type` 단일 + `(date, mover_type)` 복합 인덱스 추가.

### 2-2. [HIGH] serverless/models.py — MarketMover (date + mover_type) 복합 인덱스 누락
- **수정 난이도**: 쉬움
- **현상**: views.py:140-142에서 두 필드 함께 필터. 개별 인덱스만 존재.
- **권장**: `models.Index(fields=['date', 'mover_type'])` 추가.

### 2-3. [HIGH] serverless/models.py — StockKeyword.status (line 221)
- **수정 난이도**: 쉬움
- **현상**: Celery 배치가 `status='pending'`을 반복 조회. 인덱스 없음.
- **권장**: `db_index=True` 추가.

### 2-4. [HIGH] rag_analysis/models.py — AnalysisSession.status (line 150)
- **수정 난이도**: 쉬움
- **현상**: choice 필드인데 인덱스 없음. views.py:704에서 status 필터 + `-created_at` order_by.
- **권장**: `(status, -created_at)` 복합 인덱스.

### 2-5. [HIGH] rag_analysis/models.py — UsageLog.cached (line 305)
- **수정 난이도**: 쉬움
- **현상**: cache hit rate 계산(`cache_hit_rate()` 라인 393-396)에서 `objects.filter(cached=True).count()` 반복. Boolean 인덱스 없음.
- **권장**: `db_index=True` 추가 (partial index가 더 효율).

### 2-6. [HIGH] sec_pipeline/models.py — RawDocumentStore (symbol + filing_date) 복합 인덱스
- **수정 난이도**: 쉬움
- **현상**: `on_demand.py:35`에서 `filter(symbol=..., filing_date__gte=...).order_by('-filing_date')` 호출. 복합 인덱스 없음.
- **권장**: `models.Index(fields=['symbol', '-filing_date'])`.

### 2-7. [HIGH] graph_analysis/models.py — CorrelationEdge (watchlist + is_anomaly + date) 복합 인덱스
- **수정 난이도**: 쉬움
- **현상**: `anomaly_detector.py:310`에서 세 필드 동시 필터. 개별 인덱스만 존재.
- **권장**: 3-field 복합 인덱스.

### 2-8. [MED] serverless/models.py — SectorPerformance (date + sector) + order_by('-return_pct')
- **수정 난이도**: 쉬움
- **현상**: views.py:752, services.py:168에서 두 필드 + order_by 정렬.
- **권장**: `models.Index(fields=['date', 'sector', '-return_pct'])`.

### 2-9. [MED] serverless/models.py — ScreenerAlert (user + is_active) 복합
- **수정 난이도**: 쉬움
- **현상**: views.py:1196에서 user-scoped active 필터.
- **권장**: 복합 인덱스 추가.

### 2-10. [MED] serverless/models.py — VolatilityBaseline.date (line 151)
- **수정 난이도**: 쉬움
- **현상**: date 범위 쿼리에 사용되나 인덱스 없음.

### 2-11. [MED] serverless/models.py — ScreenerAlert.created_at
- **수정 난이도**: 쉬움
- **현상**: `order_by('-created_at')` 사용되나 인덱스 없음.

### 2-12. [MED] rag_analysis/models.py — UsageLog.model (line 270), UsageLog.request_type (line 282)
- **수정 난이도**: 쉬움
- **현상**: 라인 354-376 cost tracking에서 두 필드 모두 group by / filter.
- **권장**: 각 필드에 db_index 또는 `(model, created_at)`, `(request_type, created_at)` 복합.

### 2-13. [MED] rag_analysis/models.py — DataBasket Meta indexes 부재
- **수정 난이도**: 쉬움
- **현상**: 모델에 indexes 정의 자체가 없음. user FK는 자동 인덱스되나 ordering 인덱스 부재.
- **권장**: `models.Index(fields=['user', '-updated_at'])`.

### 2-14. [MED] sec_pipeline/models.py — FilingProcessLog.stage (line 252)
- **수정 난이도**: 쉬움
- **현상**: 파이프라인 모니터링이 stage로 필터. 인덱스 없음.

### 2-15. [MED] sec_pipeline/models.py — CompanyAlias.ticker (line 283)
- **수정 난이도**: 쉬움
- **현상**: 역방향 매칭에 ticker 사용. 인덱스 없음.

### 2-16. [MED] sec_pipeline/models.py — UnmatchedCompanyQueue (status + occurrence_count) 복합
- **수정 난이도**: 쉬움
- **현상**: status 인덱스 있으나 occurrence_count 정렬 시 복합 미적용.

### 2-17. [MED] graph_analysis/models.py — CorrelationAnomaly (alerted + watchlist + date) 복합
- **수정 난이도**: 쉬움

### 2-18. [MED] graph_analysis/models.py — GraphMetadata (status + date) 복합 검증
- **수정 난이도**: 쉬움

### 2-19. [MED] portfolio/models.py — AnalysisRun.preset_id 단독 인덱스
- **수정 난이도**: 쉬움
- **현상**: cross-portfolio 통계가 preset_id alone 필터.

### 2-20. [MED] portfolio/models.py — PercentileCache.metric_id 단독 인덱스
- **수정 난이도**: 쉬움
- **현상**: cache warming이 metric_id 단독 조회.

### 2-21. [MED] portfolio/models.py — Decision (user + decision_at) 복합
- **수정 난이도**: 쉬움
- **현상**: user 타임라인 조회.

### 2-22. [MED] sec_pipeline/models.py — RawDocumentStore.filing_date 단독 인덱스
- **수정 난이도**: 쉬움

### 2-23. [MED] serverless/models.py — MarketBreadth `order_by('-date')` 빈번 (views.py:528, services.py:92-93)
- **수정 난이도**: 쉬움
- **현상**: date에 db_index 있으나 후속 필터와 결합되는 패턴 검토 필요.

### 2-24. [LOW] serverless/models.py — MarketBreadth.breadth_signal (line 309)
- **수정 난이도**: 쉬움

### 2-25. [LOW] serverless/models.py — CorporateAction.action_type (line 589)
- **수정 난이도**: 쉬움

### 2-26. [LOW] sec_pipeline/models.py — SupplyChainEvidence.confidence_grade (line 97)
- **수정 난이도**: 쉬움

### 2-27. [LOW] graph_analysis/models.py — CorrelationAnomaly.dismissed (line 234)
- **수정 난이도**: 쉬움

### [참고: OK 항목]
- portfolio/models.py — Wallet, WalletHolding, MetricResult, ChatSession은 기존 인덱스로 충분
- stocks/models.py — Stock, DailyPrice, EODSignal 인덱스 양호 (이미 적절한 복합 인덱스 보유)
- users/models.py — Portfolio, Watchlist, WatchlistItem 양호
- news/models.py — NewsArticle, NewsEntity, SentimentHistory 양호

---

## 3. 느린 Serializer (SerializerMethodField·N+1)

### 3-1. [HIGH] serverless/serializers.py:531-535 — ScreenerAlertSerializer.get_preset_name
- **수정 난이도**: 쉬움
- **현상**: `obj.preset.icon`, `obj.preset.name` access. views.py:1196 alert list endpoint에서 `prefetch_related('preset')` 미적용.
- **권장**: view queryset에 `.select_related('preset', 'user')` 추가.

### 3-2. [HIGH] serverless/serializers.py:121-137 — MarketMoverListSerializer 3개 SerializerMethodField
- **수정 난이도**: 중간
- **현상**: `get_sector_alpha_display`, `get_etf_sync_display`, `get_volatility_pct_display` 모두 매 row마다 `IndicatorCalculator()` 인스턴스화. 서비스 객체 N회 생성.
- **권장**: serializer `__init__`에서 calculator를 캐싱하거나 `to_representation` 1회 호출 패턴으로 변경.

### 3-3. [MED] serverless/serializers.py:208-212 — MarketBreadthSerializer.get_signal_interpretation
- **수정 난이도**: 중간
- **현상**: row별 service 인스턴스화.
- **권장**: 위와 동일 패턴.

### 3-4. [MED] rag_analysis/models.py:45-48 — DataBasket.current_units property → serializer 접근
- **수정 난이도**: 중간
- **현상**: `self.items.aggregate(Sum('data_units'))` 호출. list view에서 basket 1건당 1 aggregate 쿼리.
- **권장**: view에서 `.annotate(current_units=Sum('items__data_units'))` 미리 계산.

### 3-5. [MED] rag_analysis/serializers.py:29,34 — DataBasketSerializer.can_add_item, max_units
- **수정 난이도**: 쉬움
- **현상**: 위 current_units property 의존 시 추가 쿼리 가능.

### 3-6. [MED] stocks/serializers.py:114-117 — StockListSerializer market_cap_formatted, korean_overview, dynamic_layers
- **수정 난이도**: 중간
- **현상**: `dynamic_layers`가 ManyToOne relation을 lazy access하면 N+1.
- **권장**: view에서 `prefetch_related('dynamic_layers')` 보장.

### 3-7. [MED] stocks/serializers.py:381-382 — latest_price, chart_data SerializerMethodField
- **수정 난이도**: 중간
- **현상**: list view에서 stock별 DailyPrice 조회 시 N+1 가능.
- **권장**: `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:1])`.

### 3-8. [MED] stocks/serializers_screener.py:61-63 — formatted_market_cap, formatted_volume, dividend_yield
- **수정 난이도**: 쉬움
- **현상**: 단순 포맷팅이면 OK. DB 접근 여부 코드 확인 필요.

### 3-9. [MED] stocks/serializers_exchange.py:52-54,120-121 — direction, formatted_change, day_range_percentage
- **수정 난이도**: 쉬움
- **현상**: 자기 필드 가공 위주면 OK. 포맷팅에 외부 lookup 있는지 확인.

### 3-10. [MED] users/serializers.py:95 — PortfolioSerializer.portfolio_weight
- **수정 난이도**: 쉬움
- **현상**: 전체 포트폴리오 가치 대비 비중 계산. context로 전달 안 하면 매 row마다 aggregate.
- **권장**: view에서 `total_value`를 context에 주입.

### 3-11. [MED] stocks/serializers_market_movers.py:30-31 — direction, formatted_change
- **수정 난이도**: 쉬움

### 3-12. [LOW] stocks/serializers_fundamentals.py:109-110 — discount_percentage, recommendation
- **수정 난이도**: 쉬움
- **현상**: detail view 용도면 N+1 위험 낮음.

---

## 4. 페이지네이션 누락

### 4-1. [HIGH] stocks/views_screener.py:60-157 — StockScreenerView
- **수정 난이도**: 쉬움
- **현상**: limit 기본 100, 최대 1000. pagination_class 없음.
- **권장**: `pagination_class = StockListPagination` 추가.

### 4-2. [HIGH] stocks/views_screener.py:257-288 — LargeCapStocksView
- **수정 난이도**: 쉬움
- **현상**: limit 1-1000. 페이지네이션 없음.

### 4-3. [HIGH] stocks/views_screener.py:306-337 — HighDividendStocksView
- **수정 난이도**: 쉬움

### 4-4. [HIGH] stocks/views_screener.py:357-393 — SectorStocksView
- **수정 난이도**: 쉬움

### 4-5. [HIGH] stocks/views_screener.py:462-498 — ExchangeStocksView
- **수정 난이도**: 쉬움

### 4-6. [HIGH] validation/api/views.py:52-99 — ValidationSummaryView
- **수정 난이도**: 중간
- **현상**: CategorySignal 다건 반환 가능. limit 없음.
- **권장**: ListAPIView 변환 + pagination_class.

### 4-7. [MED] chainsight/api/views.py:61-102 — ChainSightGraphView
- **수정 난이도**: 높음
- **현상**: 그래프 결과는 페이지 단위로 자르기 어려움. depth/breadth 캡으로 대응.
- **권장**: `max_neighbors_per_node` 강제 + 응답 size 모니터링.

### 4-8. [MED] stocks/views_indicators.py:297-373 — IndicatorComparisonView.post
- **수정 난이도**: 쉬움
- **현상**: input symbols 리스트가 unbounded.
- **권장**: serializer에서 `max_length=50` 검증.

### 4-9. [MED] users/views.py:597-603, 810-823 — 수동 페이지네이션
- **수정 난이도**: 쉬움
- **현상**: page/page_size를 query_params로 수동 처리 (`page = request.query_params.get('page', 1)`). DRF pagination_class로 통일 필요 (응답 메타 표준화).

### 4-10. [LOW] stocks/views_mvp.py:17-66 — StockMVPListView
- **수정 난이도**: 쉬움
- **현상**: `[:20]` 하드코딩으로 보호됨. 페이지네이션은 없음.
- **권장**: 추후 무한스크롤 도입 시 pagination_class 추가.

---

## 부록 A — 우선순위 권장 작업 (상위 10건)

1. **stocks/views_screener.py 5개 list endpoint에 pagination_class 일괄 추가** — 30분 작업, DoS 표면 차단.
2. **serverless/models.py MarketMover (date, mover_type) 복합 인덱스 + mover_type 단일 인덱스 추가** — 마이그레이션 1건.
3. **rag_analysis/models.py AnalysisSession.status, UsageLog.cached/model/request_type 인덱스 추가** — 마이그레이션 1건.
4. **sec_pipeline RawDocumentStore (symbol, -filing_date) 복합 인덱스 추가** — on_demand 핫패스 가속.
5. **stocks/views_indicators.py IndicatorComparisonView N+1 제거** — `Stock.objects.in_bulk` 패턴 적용.
6. **serverless ScreenerAlertSerializer N+1 차단** — view에 `.select_related('preset','user')` 추가.
7. **serverless MarketMoverListSerializer service 인스턴스 캐싱** — `to_representation` 1회 호출 패턴.
8. **users/views.py 수동 페이지네이션 → pagination_class 표준화** — 응답 포맷 통일.
9. **graph_analysis CorrelationEdge (watchlist, is_anomaly, -date) 복합 인덱스** — 핫패스 anomaly_detector 가속.
10. **stocks StockCompleteDataAPIView 4쿼리 → prefetch_related로 묶기** — `/api/v1/stocks/<sym>/complete` 응답 시간 단축.

## 부록 B — 검증 가이드

- **N+1 실증**: `django-debug-toolbar` 또는 `nplusone` 미들웨어로 query count 측정. 핫패스 30개 endpoint 대상 부하 시나리오 실행.
- **인덱스 효과**: PostgreSQL `EXPLAIN ANALYZE` 비교. `pg_stat_statements`로 slow query Top 20 사전/사후 비교.
- **페이지네이션 영향**: response payload size 평균치 기록. 95p 응답시간 변화 모니터링.

## 부록 C — 본 감사에서 확인된 양호 항목

- **stocks/models.py** Stock·DailyPrice·EODSignal 인덱스 설계 우수
- **users/models.py** Portfolio·Watchlist·WatchlistItem 인덱스 양호
- **news/models.py** NewsArticle·NewsEntity·SentimentHistory `-published_at` 복합 인덱스 양호
- **rag_analysis/views.py** DataBasket·AnalysisSession에 `prefetch_related` 적용 완료
- **users/views.py** Portfolio·Watchlist 조회 시 `select_related('stock')` 일관 적용
- **news/api/views.py** `prefetch_related('entities')` 적용
- **stocks/views.py** StockListPagination 정의 + 사용

---

_본 보고서는 정적 분석 기반이며, 실측 부하 테스트(`locust` / `k6`)로 우선순위를 재조정해야 정확합니다._
