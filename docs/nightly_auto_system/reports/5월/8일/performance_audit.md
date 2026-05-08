# API 성능 감사 보고서

- **대상**: Stock-Vis Django 백엔드 (views 17개 + models 7개 + serializers 13개)
- **수행일**: 2026-05-08
- **모드**: 읽기 전용 (코드 수정 없음)
- **분석 방식**: 정적 코드 분석 — 패턴 매칭 기반 (런타임 측정 없음)

---

## 요약 (이슈 수 by 심각도)

| 영역 | HIGH | MED | LOW | 합계 |
|------|------|-----|-----|------|
| Views — N+1 / 페이지네이션 | 12 | 17 | 1 | 30 |
| Models — 인덱스 누락 | 0 | 8 | 7 | 15 |
| Serializers — N+1 / 추가 쿼리 | 6 | 4 | 0 | 10 |
| **합계** | **18** | **29** | **8** | **55** |

### 우선 수정 권장 Top 5 (HIGH + 쉬움)

| # | 위치 | 이슈 | 수정 |
|---|------|------|------|
| 1 | `stocks/views.py:75-105` `StockListAPIView` | 페이지네이션 누락 (`Stock.objects.all()` 무제한 반환) | `pagination_class` 1줄 추가 |
| 2 | `stocks/views_mvp.py:29-41` | 페이지네이션 누락 + 슬라이싱만 사용 | `ListAPIView` 전환 또는 `PageNumberPagination` |
| 3 | `users/views.py:880-898` | 루프 내 `Stock.objects.get(symbol=...)` 반복 | `Stock.objects.filter(symbol__in=...)` 배치 |
| 4 | `users/views.py:92-94` `User.objects.all() + UserSerializer(many=True)` | favorite_stock M2M 누락된 prefetch | `prefetch_related('favorite_stock')` |
| 5 | `news/api/serializers.py` `NewsArticleListSerializer` | 중첩 many=True (`entities`)에 prefetch 부재 | view에 `prefetch_related('entities__highlights')` |

### 가장 심각한 핫스팟

| 핫스팟 | 위험도 | 비고 |
|--------|--------|------|
| `validation/api/views.py:205-371` `_build_metric` / `LeaderComparisonView` | HIGH | metric_codes × 4 종 모델 루프 조회. Validation 페이지 응답 시 수백 쿼리 가능 |
| `stocks/serializers.py:190-307` `OverviewTabSerializer.get_dynamic_layers()` | HIGH | 6개 reverse 관계 무조건 로드, 코드에 TODO 주석 존재 |
| `news/api/views.py:328-333` trending action | HIGH | `for item in trending_data` 안에서 `NewsArticle.objects.filter(...).distinct()` |
| `news/api/views.py:1483-1503` collection_logs | HIGH | 동일 phase1_logs queryset을 4회 재필터링 |
| `serverless/serializers.py:88-185` MarketMover/Breadth Serializer | HIGH | many=True list에서 메서드마다 service 인스턴스 신규 생성 |

---

## 1. Views — N+1 / 페이지네이션

### 1.1 stocks/

#### stocks/views.py

- **[stocks/views.py:75-105]** `StockListAPIView` — **HIGH | 쉬움**
  - 패턴: `Stock.objects.all()` 후 `pagination_class` 미설정. 데이터 증가 시 메모리/응답 폭증.
  - 권장: `pagination_class = PageNumberPagination` 추가, page_size 50~100.

- **[stocks/views.py:146-149]** 차트 데이터 직렬화 — **MED | 쉬움**
  - 패턴: `DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]` 후 `ChartDataSerializer(many=True)`. 단일 stock context이지만 select_related 명시 누락.
  - 권장: `select_related('stock')` 추가로 안전망 구축.

- **[stocks/views.py:839-873]** `StockCompleteDataAPIView` — **MED | 쉬움**
  - 패턴: BalanceSheet/IncomeStatement/CashFlowStatement 3개 모델을 각각 `[:5]`로 조회 + many=True 직렬화.
  - 권장: 각 쿼리에 `select_related('stock')` 명시.

#### stocks/views_search.py
- **이슈 없음**. `[:10]` 슬라이싱과 단일 심볼 조회만 사용.

#### stocks/views_exchange.py
- **이슈 없음**. 외부 FMP API 응답 처리. DB 쿼리 없음.

#### stocks/views_eod.py
- **[stocks/views_eod.py:72-79]** — **이슈 없음 (안전)**
  - `select_related('stock')` 이미 적용되어 있음. 향후 `s.stock.stock_name` 접근에도 N+1 없음.

#### stocks/views_screener.py
- **이슈 없음**. FMP 외부 API 호출 기반.

#### stocks/views_market_movers.py
- **이슈 없음**. FMP 외부 API 호출 기반.

#### stocks/views_fundamentals.py
- **이슈 없음**. 모든 view가 FMP 서비스 응답 처리.

#### stocks/views_indicators.py

- **[stocks/views_indicators.py:324-371]** `IndicatorComparisonView` — **MED | 중간**
  - 패턴: `for symbol in symbols: Stock.objects.get(symbol=symbol)` + 루프 내부 `DailyPrice.objects.filter(stock=stock)[:50]`. 비교 종목 N개에 대해 2N 쿼리.
  - 권장: `Stock.objects.filter(symbol__in=symbols)`로 배치 → dict 매핑 → DailyPrice도 `stock__in=stocks`로 일괄 조회 후 그룹핑.

- **[stocks/views_indicators.py:60-66]** — **LOW | 쉬움**
  - 패턴: `query.order_by('date').values(...)` 후 list 변환. 거대 데이터셋(10000+ 행) 시 위험.
  - 권장: 상한 슬라이싱 또는 페이지네이션 도입 고려.

#### stocks/views_mvp.py

- **[stocks/views_mvp.py:29-41]** — **HIGH | 중간**
  - 패턴: `Stock.objects.all()[:20]`로 슬라이싱만 사용 (페이지네이션 아님). 루프에서 추가 필드 접근.
  - 권장: `ListAPIView` + `pagination_class` 또는 `select_related/prefetch_related` 명시.

- **[stocks/views_mvp.py:113-126]** — **MED | 쉬움**
  - 패턴: `IncomeStatement.objects.filter(stock=stock).first()` — 단건이지만 select_related 부재.
  - 권장: `select_related('stock')` 일관성 확보.

- **[stocks/views_mvp.py:195-197]** — **MED | 쉬움**
  - 패턴: `Stock.objects.exclude(sector__isnull=True).values_list('sector', flat=True).distinct()` — 대량 데이터 시 메모리 영향.
  - 권장: 캐싱 또는 `.only('sector')` 결합.

### 1.2 users/

- **[users/views.py:92-94]** Users 목록 조회 — **HIGH | 중간**
  - 패턴: `User.objects.all()` + `UserSerializer(many=True)`. UserSerializer의 favorite_stock M2M으로 N+1.
  - 권장: `prefetch_related('favorite_stock')` 추가, 페이지네이션 도입.

- **[users/views.py:193]** favorite_stock 직렬화 — **MED | 쉬움**
  - 패턴: `user.favorite_stock.all()` → 관련 sector 등 추가 접근 시 N+1.
  - 권장: `prefetch_related('favorite_stock__sector')` 등.

- **[users/views.py:212]** `if stock in user.favorite_stock.all()` — **MED | 쉬움**
  - 패턴: in 연산자가 매번 쿼리 발생.
  - 권장: 사전 `set(user.favorite_stock.values_list('id', flat=True))`로 변환.

- **[users/views.py:264-266]** Portfolio 조회 — **이슈 없음 (안전 예시)**
  - `select_related('stock')` 이미 적용.

- **[users/views.py:374-376]** total_value 합산 — **MED | 중간**
  - 패턴: `for portfolio in portfolios: total_value += portfolio.total_value` — 프로퍼티 호출이 추가 쿼리 유발 가능.
  - 권장: ORM `aggregate(Sum(...))`로 DB 측 계산.

- **[users/views.py:410-416]** `PortfolioDetailSerializer(many=True)` — **MED | 높음**
  - 패턴: SerializerMethodField가 prefetch 미보장 시 N+1.
  - 권장: `to_representation` 오버라이드 + view에서 prefetch 보장.

- **[users/views.py:599]** Watchlist 페이지네이션 — **이슈 없음 (안전 예시)**.
- **[users/views.py:655]** `prefetch_related('items__stock')` — **이슈 없음 (안전 예시)**.
- **[users/views.py:819]** WatchlistItem `select_related` — **이슈 없음 (안전 예시)**.

- **[users/views.py:880-898]** symbols 루프 — **HIGH | 중간**
  - 패턴: `for symbol in symbols: Stock.objects.get(symbol=symbol.upper())` — N개 심볼당 N개 쿼리.
  - 권장: `Stock.objects.filter(symbol__in=upper_symbols)` + dict 매핑.

- **[users/views.py:975-985]** UserInterest 조회 — **MED | 쉬움**
  - 패턴: 단순 필드 접근만 사용 (현재는 안전), `user` 인덱스 누락은 별도 이슈.

### 1.3 news/api/views.py

- **[news/api/views.py:50]** — **이슈 없음 (안전)**. `prefetch_related('entities')` 적용.

- **[news/api/views.py:95-98]** — **MED | 쉬움**
  - 패턴: `entities__symbol=symbol` M2M 조인 + `.distinct()`로 중복 제거 비용.
  - 권장: 결과 카디널리티 검증 후 distinct 회피.

- **[news/api/views.py:160-162]** sentiment_scores 리스트 컴프리헨션 — **MED | 쉬움**
  - 권장: DB 측 `aggregate(Avg('sentiment_score'))`로 이동.

- **[news/api/views.py:328-333]** trending — **HIGH | 높음**
  - 패턴: `for item in trending_data: NewsArticle.objects.filter(entities__symbol=symbol)[:3]` — 종목 N개 × distinct 쿼리.
  - 권장: 사전 `entities__symbol__in=tickers` 일괄 조회 후 Python에서 그룹핑.

- **[news/api/views.py:401-403]** — **이슈 없음 (안전)**. prefetch 적용.

- **[news/api/views.py:710-744]** keyword_detail Fallback — **HIGH | 높음**
  - 패턴: article_ids 부재 시 매개변수 4개로 distinct 검색.
  - 권장: 프론트에서 항상 article_ids 전달, Fallback 경로 제거 또는 단일 SQL 통합.

- **[news/api/views.py:1369-1374]** provider_agg — **이슈 없음 (안전 예시)**.

- **[news/api/views.py:1380]** error_runs 보조 쿼리 — **MED | 중간**
  - 패턴: 그룹마다 `qs.filter(...).count()` 추가 호출.
  - 권장: `annotate(error_runs=Count('id', filter=Q(errors__gt=0)))`로 통합.

- **[news/api/views.py:1483-1503]** phase1_logs 4회 재쿼리 — **HIGH | 높음**
  - 패턴: 동일 base queryset에 `.first()` / `.aggregate(...)` / `.values_list(...).distinct()`를 순차 실행.
  - 권장: `values('provider').annotate(...)` 단일 쿼리로 통합.

- **[news/api/views.py:1614-1616]** MLModelHistory 2회 조회 — **MED | 쉬움**
  - 권장: `MLModelHistory.objects.order_by('-trained_at')[:N]` + 파이썬 분기.

- **[news/api/views.py:1709-1726]** history_qs 루프 직렬화 — **MED | 쉬움**
  - 권장: ModelSerializer 도입 (성능보다 가독성).

- **[news/api/views.py:1844-1855]** tier별 count() 3회 — **MED | 중간**
  - 패턴: tier_a/b/c 각각 `.count()` 호출.
  - 권장: `.values('llm_analysis__tier').annotate(count=Count('id'))` 단일 호출.

### 1.4 macro/views.py
- **이슈 없음**. 서비스 계층에서 dict 반환만 직렬화.

### 1.5 rag_analysis/views.py
- 라인 76, 106, 437, 477 — 모두 `prefetch_related('items')` / `'messages'` 적용된 **안전 예시**.
- 라인 507 `session.messages.all().order_by('created_at')` — 세션이 prefetch된 경우 안전.

### 1.6 serverless/views_admin.py

- **[serverless/views_admin.py:478-500]** category 루프 — **HIGH | 높음**
  - 패턴: `for cat in categories: cat.resolve_symbols()` — Python 메서드가 내부에서 추가 쿼리 수행.
  - 권장: `resolve_symbols`를 ORM 일괄 호출로 재설계 또는 결과 캐싱.

- **[serverless/views_admin.py:670-683]** sectors annotate — **이슈 없음 (안전 예시)**.

### 1.7 validation/api/views.py

- **[validation/api/views.py:113-124]** rank_metrics 루프 — **MED | 쉬움**
  - 패턴: `for mc in rank_metrics: CompanyBenchmarkDelta.objects.filter(...).first()`.
  - 권장: `metric_code_id__in=rank_metrics` 일괄 조회 후 dict 매핑.

- **[validation/api/views.py:151]** Stock peers 조회 — **MED | 쉬움**
  - 권장: 결과를 `in_bulk(...)` 또는 dict로 변환해 단일 패스 처리.

- **[validation/api/views.py:205-267]** `_build_metric` — **HIGH | 높음**
  - 패턴: 한 metric마다 `latest_snap.first()` / `any_snap.first()` / `delta.first()` / `snaps[:5]` 루프 내 `peer_bench.first()` — 메트릭 N개 × 4~5 쿼리.
  - 권장: metric_code 전체에 대한 4종 모델 일괄 조회 → metric_code 키 dict로 매핑 → Python에서 조립.

- **[validation/api/views.py:335-340]** peers + leader.first() / count() / [1] — **HIGH | 높음**
  - 권장: `peers = list(Stock.objects.filter(...))`로 1회 평가 후 인덱싱.

- **[validation/api/views.py:366-371]** all_metrics 루프 × 2개 모델 — **HIGH | 높음**
  - 패턴: cat × mc 쌍마다 company_snap.first() + leader_snap.first().
  - 권장: bulk 조회 후 `(symbol, metric_code_id) → snap` dict 매핑.

### 1.8 chainsight/api/views.py

- **[chainsight/api/views.py:80-87]** edges 루프 — **MED | 쉬움**
  - 패턴: `for edge in edges: CoMentionEdge.first() + PriceCoMovement.first()`.
  - 권장: 좌표쌍 일괄 조회 후 dict 매핑.

- **[chainsight/api/views.py:150-154]** `union(...)` 후 루프 — **HIGH | 중간**
  - 패턴: union 결과를 Python 루프로 처리하면서 추가 분기.
  - 권장: `Q(symbol_a=symbol) | Q(symbol_b=symbol)` 단일 쿼리로 변경.

- **[chainsight/api/views.py:391]**, **[:528-529]** stock_map 생성 — **MED | 쉬움**
  - 권장: `Stock.objects.in_bulk(tickers, field_name='symbol')` 사용.

### 1.9 sec_pipeline/views.py
- **이슈 없음**. 단순 트리거/조회 형태.

---

## 2. Models — 인덱스 누락

> 기준: `filter` / `order_by` / `exclude`에서 자주 사용되지만 `db_index=True`도 없고 `unique`도 아니고 `Meta.indexes`/`unique_together`로 커버되지 않는 필드.

### 2.1 stocks/models.py

- **[stocks/models.py:359-362, 428-431, 527-530]** BalanceSheet/IncomeStatement/CashFlowStatement — **MED | 쉬움**
  - 사용처: `views.py:636-639, 710-713, 782-785` — `.filter(stock=stock, period_type='annual').order_by('-fiscal_year')`.
  - 현재: `(stock, fiscal_year)` 인덱스만 존재. period_type 필터가 매번 추가됨.
  - 권장: `Meta.indexes`에 `Index(fields=['stock', 'period_type', '-fiscal_year'])` 추가.

- **[stocks/models.py:789]** EODSignal 보조 정렬 — **LOW | 쉬움**
  - 사용처: `views_eod.py:73-78` — `.filter(date=date).order_by('-composite_score')[:50]`.
  - 권장: `Index(fields=['date', '-composite_score'])` 검토 (기존 인덱스 충분 가능성도 있음 — 실측 후 결정).

### 2.2 users/models.py

- **[users/models.py:263-265]** UserInterest — **MED | 쉬움**
  - 사용처: `news/services/interest_options.py:108` — `UserInterest.objects.filter(user=user)`.
  - 권장: `Meta.indexes`에 `['user']` 추가 또는 `user` 필드에 `db_index=True`.

- Portfolio, WatchlistItem — **인덱스 충분**.

### 2.3 news/models.py

- **[news/models.py:588-593]** MLModelHistory.deployment_status — **MED | 쉬움**
  - 사용처: `api/views.py:1613-1615` — `.filter(deployment_status='deployed').order_by('-trained_at')`. 운영 대시보드 빈번 호출.
  - 권장: `Index(fields=['deployment_status', '-trained_at'])` 추가.

- **[news/models.py:676-679]** NewsCollectionLog.task_name — **MED | 쉬움**
  - 사용처: `api/views.py:1520, 1548, 1580` — `.filter(task_name=...).order_by('-executed_at')`.
  - 권장: `Index(fields=['task_name', '-executed_at'])` 추가.

- **[news/models.py:718-725]** AlertLog.severity — **LOW | 쉬움**
  - 사용처: `api/views.py:2124` — `qs.filter(severity=severity)`.
  - 권장: `Index(fields=['severity', '-created_at'])` (선택).

- NewsArticle, NewsEntity, SentimentHistory, DailyNewsKeyword — **인덱스 충분**.

### 2.4 serverless/models.py

- **[serverless/models.py:785-792]** AlertHistory.read_at + dismissed — **MED | 쉬움**
  - 사용처: `views.py:1562` — `.filter(read_at__isnull=True, dismissed=False)`.
  - 권장: `Index(fields=['read_at', 'dismissed', '-triggered_at'])` 부분 인덱스 검토.

- **[serverless/models.py:1309-1325]** LLMExtractedRelation.target_symbol — **LOW | 쉬움**
  - 기존 복합 인덱스에 일부 커버됨. 단일 인덱스 추가는 옵션.

- MarketMover, StockKeyword, ScreenerPreset, ScreenerAlert, StockRelationship — **인덱스 충분**.

### 2.5 rag_analysis/models.py

- **[rag_analysis/models.py:28-31]** DataBasket.user — **MED | 쉬움**
  - 사용처: `views.py:76` — 매 세션 호출.
  - 권장: `Meta.indexes`에 `['user']` 추가.

- **[rag_analysis/models.py:106-112]** BasketItem.basket — **MED | 쉬움**
  - 사용처: `views.py:315`. `unique_together`가 있어 복합 인덱스가 자동 생성되지만 첫 컬럼이 basket이면 활용 가능. 확인 후 추가 인덱스 검토.

- **[rag_analysis/models.py:165-169]** AnalysisSession.user — **MED | 쉬움**
  - 사용처: `views.py:437`.
  - 권장: `Index(fields=['user', '-updated_at'])` 추가.

- UsageLog — **인덱스 충분**.

### 2.6 sec_pipeline/models.py

- **[sec_pipeline/models.py:106-113]** SupplyChainEvidence.extracted_at — **LOW | 쉬움**
  - 권장: `Index(fields=['-extracted_at'])` (배치/시간순 분석용, 옵션).

- **[sec_pipeline/models.py:258-264]** FilingProcessLog.status — **LOW | 쉬움**
  - 권장: `Index(fields=['status', '-started_at'])` 추가 (모니터링 최적화용).

- RawDocumentStore, BusinessModelSnapshot, CompanyAlias, UnmatchedCompanyQueue — **인덱스 충분**.

### 2.7 graph_analysis/models.py
- 모든 모델 — **인덱스 충분**. CorrelationMatrix/Edge/Anomaly/PriceCache/GraphMetadata 모두 적절한 복합 인덱스 보유.

---

## 3. Serializers — N+1 / 추가 쿼리

### 3.1 stocks/serializers.py — **HIGH | 높음**

- **[stocks/serializers.py:190-307]** `OverviewTabSerializer.get_dynamic_layers()`
  - 패턴: 단일 객체 detail 직렬화에서 6개 reverse 관계 — `category_signals.all()`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag` — 를 try/except로 감싸 무조건 호출. 각각 추가 쿼리 1회.
  - 코드 주석에 이미 TODO 존재 ("Step 2~4에서 데이터 유입 시 prefetch_related + 캐싱 레이어 적용 필요").
  - 권장: 호출 view에서 `prefetch_related('category_signals', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')` + OneToOne은 `select_related('validation_news_summary')`.

- **[stocks/serializers.py:398-409]** `WatchListStockSerializer.get_latest_price() + get_chart_data()`
  - 패턴: SerializerMethodField 안에서 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` 및 `[:7]`.
  - many=True list에서 N+2 추가 쿼리.
  - 권장: list 엔드포인트에선 `get_chart_data` 분리, `latest_price`는 `obj.real_time_price` 활용. 또는 `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])`.

### 3.2 serverless/serializers.py

- **[serverless/serializers.py:88-137]** `MarketMoverListSerializer.get_sector_alpha_display / get_etf_sync_display / get_volatility_pct_display` — **HIGH | 중간**
  - 패턴: 매 row마다 `IndicatorCalculator()` 인스턴스 신규 생성 후 포맷 호출. many=True에서 3N개 인스턴스 생성.
  - 권장: 모듈 레벨 싱글톤 또는 staticmethod로 변경. 가능하면 프론트에서 포맷팅.

- **[serverless/serializers.py:185, 214]** `MarketBreadthSerializer.get_signal_interpretation / get_advance_percent` — **HIGH | 중간**
  - 패턴: 매번 `MarketBreadthService()` 인스턴스화.
  - 권장: 정적 매핑 테이블 또는 cached_property.

- **[serverless/serializers.py:242-244]** `ScreenerPresetSerializer.get_owner_email / get_is_owner` — **MED | 쉬움**
  - 패턴: context의 request 매번 접근. 추가 쿼리는 없으나 list에서 N회 분기.
  - 권장: 단일 인증 체크 후 캐싱.

### 3.3 news/api/serializers.py — **HIGH | 중간**

- **[news/api/serializers.py:19, 47, 69]** `NewsArticleListSerializer / NewsArticleDetailSerializer / NewsEntitySerializer`
  - 패턴: 중첩 many=True (`entities`, `entities__highlights`)에 명시적 prefetch 부재 시 N+M N+1.
  - 권장: list view에 `prefetch_related('entities')`, detail view에 `prefetch_related('entities__highlights')`. 일부 view에는 적용되어 있으나 모든 호출 경로 점검 필요.

### 3.4 users/serializers.py — **HIGH | 중간**

- **[users/serializers.py:15, 23]** `StockListingField(many=True) — UserSerializer / PrivateUserSerializer`
  - 패턴: 사용자 list 직렬화에서 `favorite_stock` M2M 자동 로드 → N+1.
  - 권장: list view에 `prefetch_related('favorite_stock')` 강제. 또는 `users/views.py:92-94`처럼 모든 사용자 list 엔드포인트에 적용.

### 3.5 validation/api/views.py (인라인 직렬화) — **MED | 중간**

- **[validation/api/views.py:151, 273-284]** `ValidationMetricsView._build_metric`
  - 동일 이슈가 view 섹션과 중복. metric_codes 루프에서 `MetricDefinition / CompanyMetricSnapshot / CompanyBenchmarkDelta / PeerMetricBenchmark` 각각 `.first()` 반복.
  - 권장: 사전 bulk 조회로 4종 dict 빌드.

- **[validation/api/views.py:335, 369]** `LeaderComparisonView`
  - all_metrics 루프 × `CompanyMetricSnapshot.first()` × 2.
  - 권장: bulk 조회 후 metric_code 키 dict.

### 3.6 rag_analysis/serializers.py — **MED | 중간**

- **[rag_analysis/serializers.py:46-47]** `DataBasketSerializer.get_can_add_item`
  - 패턴: `obj.can_add_item()` 모델 메서드 호출. 메서드가 내부에서 count() 등을 호출하면 N+1.
  - 권장: 모델 메서드 구현 확인 후 `annotate` 또는 property 전환.

### 3.7 이슈 없음

- `stocks/serializers_fundamentals.py` — Dict 기반.
- `stocks/serializers_market_movers.py` — Dict 기반 (FMP 응답).
- `stocks/serializers_exchange.py` — Dict 기반.
- `stocks/serializers_screener.py` — Dict 기반.
- `macro/serializers.py` — 경량 포맷팅만.
- `chainsight/api/views.py` — Neo4j 기반, Django serializer 미사용.
- `sec_pipeline/views.py` — Admin 단순 조회.

---

## 4. 권장 적용 순서

### Phase 1 — 즉시 적용 (HIGH + 쉬움)

1. `stocks/views.py:75-105` `StockListAPIView` 페이지네이션
2. `users/views.py:92-94` `prefetch_related('favorite_stock')`
3. `users/views.py:880-898` 심볼 루프 → `filter(symbol__in=...)` 배치
4. `news/api/views.py:1483-1503` phase1_logs 단일 쿼리 통합
5. `news/api/views.py:1844-1855` tier count → `.values().annotate()`

### Phase 2 — 인덱스 추가 (모두 쉬움, MED)

6. `BalanceSheet/IncomeStatement/CashFlowStatement` `(stock, period_type, -fiscal_year)` 복합 인덱스
7. `MLModelHistory` `(deployment_status, -trained_at)` 인덱스
8. `NewsCollectionLog` `(task_name, -executed_at)` 인덱스
9. `DataBasket(user)`, `AnalysisSession(user, -updated_at)`, `UserInterest(user)` 인덱스
10. `AlertHistory(read_at, dismissed, -triggered_at)` 인덱스

### Phase 3 — 핫스팟 재설계 (HIGH + 높음)

11. `stocks/serializers.py:190-307` `get_dynamic_layers` + view에 prefetch_related 6종
12. `validation/api/views.py:205-371` `_build_metric / LeaderComparisonView` bulk 조회 패턴 도입
13. `news/api/views.py:328-333` trending 일괄 조회 + Python 그룹핑
14. `serverless/serializers.py:88-185` 메서드별 service 인스턴스 → 싱글톤/staticmethod

### Phase 4 — 중간 우선순위 (MED)

15. `users/views.py:374-376` aggregate(Sum) 전환
16. `chainsight/api/views.py:150-154` `Q(...) | Q(...)` 단일 쿼리
17. `validation/api/views.py:113-124` 루프 bulk화
18. 나머지 `select_related` 명시 누락 보완

---

## 5. 비고 / 한계

- **정적 분석 한계**: 본 보고서는 패턴 매칭 기반이며 실제 호출 빈도/페이로드 크기는 측정하지 않았다. 우선순위는 "운영 빈도 추정"에 의존.
- **검증 권장**: Phase 1 적용 전 `django-debug-toolbar` / `silk` / `pytest --reuse-db -p no:cacheprovider`로 실제 쿼리 카운트 측정 권장.
- **인덱스 추가 비용**: 인덱스는 쓰기 성능에 영향. NewsCollectionLog 같은 고빈도 INSERT 테이블은 운영 트래픽 측정 후 결정.
- **확신 수준**: HIGH 등급 — 코드 명시적 패턴이라 강한 확신. MED — 호출 빈도 가정 의존. LOW — 옵션성 최적화.
- **이슈 없음으로 분류된 파일**: `views_search.py`, `views_exchange.py`, `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`, `macro/views.py`, `sec_pipeline/views.py`, `graph_analysis/models.py`, `stocks/serializers_fundamentals.py`, `stocks/serializers_market_movers.py`, `stocks/serializers_exchange.py`, `stocks/serializers_screener.py`, `macro/serializers.py` — 모두 외부 API 응답 처리 또는 Dict 기반 직렬화로 ORM 영향 없음.
