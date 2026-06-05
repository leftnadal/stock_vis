# API 성능 감사 보고서

- **생성일**: 2026-06-05
- **유형**: 읽기 전용 정적 감사 (코드 미수정)
- **대상**: DRF 뷰 17개 + 시리얼라이저 9개 + 모델 7개
- **방법**: 정적 코드 분석 (실측 쿼리 카운트 아님, 코드 경로 기반 추정)

> ⚠️ 경로 주의: 코드베이스가 모노레포로 재편되어 지시서의 앱 경로와 실제 경로가 다름.
> `stocks→packages/shared/stocks`, `users→packages/shared/users`, `news→services/news/api`,
> `macro→apps/market_pulse`, `rag_analysis/serverless/validation/sec_pipeline→services/*`,
> `chainsight→apps/chain_sight`, `graph_analysis→services/_dormant/graph_analysis`

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 건수 | 카테고리별 |
|--------|------|-----------|
| **HIGH** | 9 | N+1 7건 + 느린 Serializer 2건 |
| **MED** | 7 | N+1 4건 + 인덱스 1건 + 느린 Serializer 2건 |
| **LOW** | 10 | N+1/페이지네이션/캐싱 7건 + 인덱스 2건 + 기타 1건 |
| **합계** | **26** | |

### 검사 항목별 결론

| 항목 | 결론 |
|------|------|
| 1. N+1 쿼리 | HIGH 7 / MED 4 / LOW 4. **validation 앱이 최다 (3 HIGH)** |
| 2. 인덱스 누락 | HIGH 0 / MED 1 / LOW 2. 대용량 테이블(가격/뉴스/시그널) 인덱스 설계 **양호** |
| 3. 느린 Serializer | HIGH 2 / MED 2 / LOW 1. `OverviewTab`·`WatchListStock`이 핵심 |
| 4. 페이지네이션 누락 | 실질 HIGH 0. 대부분 `[:N]` 슬라이스 상한 또는 외부 API 결과라 위험 낮음 |

### 핵심 메시지

- **list 엔드포인트 다수가 외부 FMP/서비스 결과를 직렬화**하므로 ORM N+1이 구조적으로 발생하지 않음. `limit` 클램프(`min(max(1,limit), N)`)도 일관 적용됨.
- 진짜 ORM N+1은 **DB 모델을 루프 직렬화하는 소수 엔드포인트에 집중** — 특히 `validation/api/views.py`(검증 매트릭스), `chain_sight` 그래프, `rag_analysis` 세션 목록.
- 모범 사례 존재: `EODSignalDetailView`(`select_related+[:50]`), `chain_sight` `SectorGraphView`/`NeighborGraphView`(`filter(symbol__in)` bulk + dict 매핑), `users` Portfolio/Watchlist 뷰 전반.

---

## 상세

### 🔴 HIGH

#### H-1. `User.objects.all()` + favorite_stock M2M N+1
- **위치**: `packages/shared/users/views.py:93` (+ `serializers.py:16` `UserSerializer.favorite_stock = StockListingField(many=True)`)
- **코드**: `users = User.objects.all()` → `UserSerializer(users, many=True)`
- **설명**: 사용자 N명 직렬화 시 각자의 `favorite_stock`(M2M 역참조)을 개별 쿼리 → N+1. 관리자 전용이나 사용자 증가에 선형 비례. 페이지네이션도 없음.
- **난이도**: 쉬움
- **권장**: `User.objects.prefetch_related("favorite_stock")` + `PageNumberPagination` 적용.

#### H-2. AnalysisSession 목록 basket/basket.items 중첩 N+1
- **위치**: `services/rag_analysis/views.py:429-432` (+ `serializers.py:86-87`)
- **코드**: `AnalysisSession.objects.filter(user=...).prefetch_related("messages")` → `AnalysisSessionSerializer(many=True)`
- **설명**: 시리얼라이저가 `messages`(prefetch됨) 외에 `basket = DataBasketSerializer(read_only=True)`도 직렬화. 세션 N개 × `basket` 1쿼리 + 각 basket의 `items` 1쿼리 = N+1 + 중첩 N+1. `messages`만 prefetch되어 basket 경로 미커버.
- **난이도**: 쉬움
- **권장**: `.select_related("basket").prefetch_related("messages", "basket__items")`.

#### H-3. ValidationMetricsView `_build_metric` 메트릭×연도 다중 쿼리
- **위치**: `services/validation/api/views.py:254-368`
- **코드**: `for mc in metric_codes:` → `_build_metric`. 메트릭당 `MetricDefinition.filter(pk=mc).first()`(260), `CompanyMetricSnapshot...first()`(278/298), `CompanyBenchmarkDelta...first()`(316), `CompanyMetricSnapshot...[:5]`(339), **그 history 루프 내부에서 연도별** `PeerMetricBenchmark.filter(...).first()`(349)
- **설명**: `category=all`이면 전 카테고리 × 메트릭 × (4 + 연도수 N) 쿼리 = 수백 쿼리. 캐시 없음. 본 감사 최악의 N+1.
- **난이도**: 높음
- **권장**: (1) `MetricDefinition`을 `pk__in`으로 1회 일괄 조회. (2) `CompanyMetricSnapshot`/`CompanyBenchmarkDelta`/`PeerMetricBenchmark`를 symbol 기준 일괄 로드 후 Python에서 metric/year 그룹핑. (3) 응답 캐싱 도입.

#### H-4. LeaderComparisonView 메트릭당 3쿼리
- **위치**: `services/validation/api/views.py:459-475`
- **코드**: `for cat, mc in all_metrics:` 내부 `MetricDefinition...first()` + `CompanyMetricSnapshot...first()`(company) + `CompanyMetricSnapshot...first()`(leader)
- **설명**: 전체 메트릭 수 × 3쿼리, 캐시 없음.
- **난이도**: 높음
- **권장**: company/leader snapshot을 `metric_code_id__in=[...]` 각 1쿼리로 일괄 로드, `MetricDefinition`도 `pk__in` 일괄 후 dict 매칭.

#### H-5. ChainSightGraphView edge 루프 내 2쿼리
- **위치**: `apps/chain_sight/api/views.py:78-91`
- **코드**: `for edge in result.get("edges", []):` 내부 `CoMentionEdge.objects.filter(...).first()` + `PriceCoMovement.objects.filter(...).first()`
- **설명**: 엣지 E개 × 2쿼리. 캐시 없음. depth↑ 시 엣지 폭증.
- **난이도**: 중간
- **권장**: 모든 (a,b) 쌍 수집 후 `CoMentionEdge.objects.filter(symbol_a__in=..., symbol_b__in=...)` / `PriceCoMovement` 일괄 조회 → dict 매칭. 응답 캐싱 검토.

#### H-6. NewsViewSet.trending 종목 루프 내 기사 쿼리 + entities prefetch 누락
- **위치**: `services/news/api/views.py:370-391`
- **코드**: `for item in trending_data:` 내부 `NewsArticle.objects.filter(entities__symbol=symbol, ...)` → `NewsArticleListSerializer(recent_articles, many=True)`
- **설명**: 종목 `limit`개 × (기사 쿼리 + 직렬화 시 `entities` prefetch 누락으로 추가 N+1). 5분 캐시로 완화되나 cache miss 시 폭증.
- **난이도**: 중간
- **권장**: `recent_articles`에 `.prefetch_related("entities")` 추가. 가능하면 단일 쿼리 후 Python groupby.

#### H-7. AdminNewsCategoryView 카테고리 루프 내 resolve_symbols() DB 조회
- **위치**: `services/serverless/views_admin.py:505-530`
- **코드**: `categories = NewsCollectionCategory.objects.all()` → `for cat in categories: symbols = cat.resolve_symbols()`
- **설명**: `resolve_symbols()`가 sector/sub_sector 타입일 때 내부에서 `SP500Constituent.objects.filter(...)` 등 DB 조회 수행 → 카테고리 N개당 쿼리. admin 전용이나 명백한 N+1.
- **난이도**: 중간
- **권장**: sector/sub_sector 심볼 배치 조회 또는 결과 캐싱. 최소한 카테고리 수 제한/페이지네이션.

#### H-8. (Serializer) OverviewTabSerializer.get_dynamic_layers 6개 역참조 접근
- **위치**: `packages/shared/stocks/serializers.py:241-353` (사용처 `views.py:545` `StockOverviewAPIView`, `views_mvp.py` `StockMVPDetailView`, `views.py:909` `StockCompleteDataAPIView`)
- **코드**: `obj.category_signals.all()`, `obj.validation_news_summary`, `obj.sensitivity_profile`, `obj.growth_stage`, `obj.capital_dna`, `obj.narrative_tag` — 6개 관계 접근
- **설명**: 현재 사용처는 **모두 단일 객체** 뷰라 즉시 N+1은 아니나(요청당 6추가 쿼리 + 10분 캐싱으로 완화), 코드 주석에도 "TODO: prefetch_related 필요" 명시. `many=True` 컨텍스트로 재사용되면 객체당 6쿼리 N+1로 확대됨 → 잠재 HIGH로 분류.
- **난이도**: 중간
- **권장**: 사용 뷰에서 OneToOne은 `select_related("validation_news_summary","sensitivity_profile","growth_stage","capital_dna","narrative_tag")`, 역참조는 `prefetch_related("category_signals")`.

#### H-9. (Serializer) WatchListStockSerializer 종목당 DailyPrice 2쿼리 + return 누락 버그
- **위치**: `packages/shared/stocks/serializers.py:451-460`
- **코드**: `get_latest_price` → `DailyPrice.objects.filter(stock=obj).order_by("-date").first()`(451), `get_chart_data` → `DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]`(458)
- **설명**: 종목당 2쿼리. `many=True` 사용 시 명백한 N+1. 더불어 `get_chart_data`에 `return`문 누락으로 항상 `None` 반환(별개 버그, CLAUDE.md "Processor return 필수" 규칙 위반 성격).
- **난이도**: 높음
- **권장**: `Prefetch`로 최근 가격 미리 로드하거나 `stock.real_time_price` 사용. **단, 이 시리얼라이저가 현재 실제 사용 중인지 먼저 확인 필요(미사용 가능성)**.

---

### 🟡 MED

#### M-1. IndicatorComparisonView 루프 내 2N 쿼리 + 입력 상한 부재
- **위치**: `packages/shared/stocks/views_indicators.py:371-389`
- **코드**: `for symbol in symbols:` 내부 `Stock.objects.get(symbol=symbol)`(375) + `DailyPrice.objects.filter(stock=stock).order_by("-date")[:50]...`(380-384)
- **설명**: symbols 개수만큼 2N 쿼리. POST body `symbols`에 **입력 개수 상한 없음**(361) → 대량 전달 시 쿼리 폭증 + 캐싱 없음.
- **난이도**: 중간
- **권장**: (1) 입력 상한 `symbols[:20]` 또는 검증 후 400. (2) `stocks = {s.symbol: s for s in Stock.objects.filter(symbol__in=symbols)}`로 Stock N→1 축소. (3) DailyPrice는 종목별 정렬 슬라이스라 캐싱 권장.

#### M-2. Users.get 페이지네이션 누락 (H-1과 동일 엔드포인트의 페이지네이션 측면)
- **위치**: `packages/shared/users/views.py:92-95`
- **코드**: `users = User.objects.all()` → 전체 직렬화
- **설명**: 관리자 전용이나 사용자 수 증가 시 전체 반환. (N+1 측면은 H-1 참조)
- **난이도**: 중간
- **권장**: DRF `PageNumberPagination` 적용.

#### M-3. ValidationSummaryView 루프 내 다중 쿼리
- **위치**: `services/validation/api/views.py:148-166`
- **코드**: `for mc in rank_metrics:` 내부 `CompanyBenchmarkDelta...first()` + `MetricDefinition.objects.filter(pk=mc).first()`
- **설명**: 5개 고정 메트릭 × 2쿼리 = 10쿼리. 고정 상한이라 폭주는 아니나 캐시 없음.
- **난이도**: 중간
- **권장**: `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fy, metric_code_id__in=rank_metrics)` 일괄 + `MetricDefinition.objects.filter(pk__in=rank_metrics)` dict화.

#### M-4. NewsArticle entities prefetch 누락 (stock_news / market)
- **위치**: `services/news/api/views.py:117-125`(`stock_news`), `:309-313`(`market`)
- **코드**: `NewsArticle.objects.filter(...)` → `NewsArticleListSerializer(many=True)` (base queryset의 prefetch 미상속)
- **설명**: `NewsArticleListSerializer.entities` 직렬화 시 기사당 entities 쿼리. 10분 캐시로 완화.
- **난이도**: 쉬움
- **권장**: 두 곳 모두 `.prefetch_related("entities")` 추가.

#### M-5. (인덱스) StockRelationship 정렬 결합 복합 인덱스 부재
- **위치**: `services/serverless/models.py:900` (`relationship_type`)
- **근거**: `services/serverless/views.py:2956/3013/3017` — `filter(source_symbol=symbol, relationship_type=...).order_by("-strength")`
- **설명**: 기존 인덱스가 `(source_symbol, relationship_type)`, `(source_symbol, -strength)`로 분리. filter 후 `-strength` 별도 sort 발생. Chain Sight 관계 테이블 중간 규모(수천~수만 행), 매 요청 정렬. 1시간 캐시가 완화.
- **난이도**: 쉬움
- **권장**: `Meta.indexes`에 `models.Index(fields=["source_symbol", "relationship_type", "-strength"])` 추가.

#### M-6. (Serializer) MarketMoverListSerializer display 필드 3개 IndicatorCalculator 반복 생성
- **위치**: `services/serverless/serializers.py:125-144`
- **코드**: `get_sector_alpha_display`/`get_etf_sync_display`/`get_volatility_pct_display` 각각 `IndicatorCalculator()` 인스턴스 생성 후 포맷
- **설명**: DB 쿼리는 아니나 객체×3회 인스턴스 생성 + import. `many=True` 대량 리스트에서 CPU 오버헤드.
- **난이도**: 쉬움
- **권장**: `IndicatorCalculator()`를 모듈 레벨 싱글톤 또는 `to_representation`에서 1회 생성. 포맷이 순수 함수면 staticmethod.

#### M-7. (Serializer) MarketBreadthSerializer.get_signal_interpretation 서비스 인스턴스 반복 생성
- **위치**: `services/serverless/serializers.py:221-226`
- **코드**: 객체당 `MarketBreadthService()` 인스턴스 생성 → `get_signal_interpretation()`
- **설명**: 히스토리 `many=True`에서 인스턴스 N회 생성. 내부가 DB/캐시 조회면 N+1 가능.
- **난이도**: 쉬움
- **권장**: 서비스 인스턴스 재사용 또는 정적 매핑.

---

### 🟢 LOW

#### L-1. UserFavorites.get 일관성 (M2M 직렬화)
- **위치**: `packages/shared/users/views.py:197-200`
- **설명**: `user.favorite_stock.all()` 자체는 1쿼리. 현재 `StockSerializer`가 단순 필드만 써 안전. 실질 위험 낮음(참고). 일관성 위해 `Stock.objects.filter(...)` 직접 사용 검토.
- **난이도**: 쉬움 / **권장**: 현 상태 허용 가능.

#### L-2. OverviewTabSerializer 단일 객체 다중 쿼리 (StockOverviewAPIView/StockCompleteDataAPIView)
- **위치**: `packages/shared/stocks/views.py:545`, `:909-968`
- **설명**: H-8과 동일 성격. 단일 객체 + 10분 캐싱으로 N+1 아님. 데이터 유입 시 prefetch 추가 여지.
- **난이도**: 중간 / **권장**: H-8 권장 적용 시 동시 해소.

#### L-3. SectorListView 캐싱 부재
- **위치**: `packages/shared/stocks/views_mvp.py:220-227`
- **코드**: `Stock.objects.exclude(sector__isnull=True).values_list("sector", flat=True).distinct()`
- **설명**: distinct 섹터 카디널리티가 수십 개로 자연 제한(무제한 list지만 실위험 무시 가능). 캐싱 없음.
- **난이도**: 쉬움 / **권장**: 결과 1시간 캐싱. 페이지네이션 불필요.

#### L-4. StockMVPListView 정식 페이지네이션 부재 (20 상한 존재)
- **위치**: `packages/shared/stocks/views_mvp.py:41-47`
- **설명**: `queryset[:20]` 하드 상한 존재. 루프 내 접근 필드는 전부 동일 테이블 컬럼이라 N+1 아님. 정식 페이지네이션 없으나 20 고정이라 위험 낮음.
- **난이도**: 쉬움 / **권장**: 필요 시 offset/page 파라미터. 현 상태 허용 가능.

#### L-5. StockSearchAPIView 미페이지네이션 ([:20] 슬라이스 상한)
- **위치**: `packages/shared/stocks/views.py:225`
- **설명**: `[:20]` 슬라이스로 상한 고정, `StockSearchSerializer`는 plain 필드 → 안전.
- **난이도**: 쉬움 / **권장**: 현 상태 허용 가능.

#### L-6. NewsViewSet.stock_sentiment QuerySet 다중 평가
- **위치**: `services/news/api/views.py:162-237`
- **설명**: `entities`(QuerySet)를 `.exists()`/Python 순회/`.count()` 여러 번 평가. `e.news`는 `select_related("news")` 적용되어 N+1 아님. count 1회 추가 정도.
- **난이도**: 쉬움 / **권장**: `entities = list(...)` 1회 평가 후 `len()` 사용.

#### L-7. validation `_find_leader` QuerySet 다중 평가
- **위치**: `services/validation/api/views.py:197-201`
- **코드**: `peers.first()` + `peers.count()` + `peers[1]`
- **설명**: 동일 QuerySet 다중 평가.
- **난이도**: 쉬움 / **권장**: `peers = list(Stock.objects.filter(...).order_by(...))` 후 인덱싱/len.

#### L-8. (인덱스) FilingProcessLog stage/started_at 선두 인덱스 부재
- **위치**: `services/sec_pipeline/models.py:283/287`
- **근거**: `services/sec_pipeline/intelligence.py:106` — `filter(started_at__gte=since, stage="section_extract", detail__startswith="FAIL:")` (symbol 술어 없음)
- **설명**: 유일 인덱스 `(symbol, stage, -started_at)`가 symbol 선두라 이 쿼리 미커버. 파이프라인 로그(소규모), 일 1회 품질 리포트 시에만 호출.
- **난이도**: 쉬움 / **권장**: `models.Index(fields=["-started_at", "stage"])` 추가 (또는 저빈도라 무시 가능).
- **참고**: `on_demand.py:51`의 `filter(symbol, stage, started_at__gte)`는 기존 인덱스로 완전 커버 — 누락 아님.

#### L-9. (인덱스) MarketMover rank 정렬 결합 복합 인덱스 부재
- **위치**: `services/serverless/models.py:20` (`rank`)
- **근거**: `keyword_generator.py:80`, `keyword_service.py:174` — `filter(date=..., mover_type=...).order_by("rank")`
- **설명**: filter는 `(date, mover_type)`로 커버. 결과가 소량(`[:max_stocks]`)이라 in-memory sort 부담 미미.
- **난이도**: 쉬움 / **권장**: 필요 시 `(date, mover_type, rank)` 복합. 우선순위 낮음.

#### L-10. (Serializer) ScreenerPresetSerializer owner FK 접근
- **위치**: `services/serverless/serializers.py:299-316`
- **코드**: `get_owner_email`/`get_is_owner`에서 `obj.user.email`
- **설명**: 프리셋 `many=True` 리스트에서 `obj.user`가 select_related 안 되면 N+1. 프리셋은 소량이라 LOW.
- **난이도**: 쉬움 / **권장**: 프리셋 목록 뷰에서 `select_related("user")` 적용 확인.

---

## 점검했으나 이슈 없음 (오탐 방지 기록)

### 뷰 (모범 사례 포함)
- **`EODSignalDetailView`** (`views_eod.py:76`): `select_related("stock") + [:50]` — N+1·무제한 모두 차단. **모범**.
- **`chain_sight` `SectorGraphView`(378)/`NeighborGraphView`(532)**: `Stock.objects.filter(symbol__in=...)` bulk + dict 매핑 + 캐시. **모범**.
- **`users` Portfolio/Watchlist 뷰 전반**: `select_related`/`prefetch_related` + `Paginator` 정확 적용.
- **`StockListAPIView`** (`views.py:100`): `StockListPagination`(50/200)으로 S&P 6000+ 일괄 반환 차단.
- `views_search.py`, `views_exchange.py`, `views_screener.py`, `views_market_movers.py`, `views_fundamentals.py`: 외부 FMP 서비스 결과 직렬화 + `limit` 클램프. ORM N+1 없음.
- `apps/market_pulse/views.py`, `services/sec_pipeline/views.py`: 서비스 위임 + 단일 dict/단건. 이슈 없음.

### 인덱스 (대용량 테이블 전수 커버 확인)
- **`DailyPrice`**: `(stock,-date)`, `(date,volume)`, `unique_together(stock,date)`로 전 패턴 커버.
- **`StockNews`** (`stocks/models.py:1150`): EOD 5단계 매칭(`symbol/industry/sector + published_at`) 인덱스 4종 커버.
- **`NewsArticle`**: ML/분류 필터 `published_at__gte` 선두 → `[-published_at, ...]` 인덱스 커버.
- **`SignalAccuracy.signal_date`**: `(signal_date, signal_tag)` 선두 컬럼 커버.
- **`CompanyAlias`**: `unique_together(alias, context_sector)` 커버.
- **users / rag_analysis / graph_analysis(_dormant) 앱**: 조회 패턴별 인덱스 완비, 누락 없음.

### 시리얼라이저
- `serializers_fundamentals.py`, `serializers_market_movers.py`, `serializers_screener.py`: dict 입력 순수 계산. 쿼리 없음.
- `market_pulse/serializers.py`: `DictField`/단순 필드. 이슈 없음.
- `news/api/serializers.py`: 중첩 `entities`/`highlights`만 — 뷰 prefetch에 의존(M-4/H-6와 연동), 시리얼라이저 자체 쿼리 없음.

---

## 권장 작업 우선순위

| 순위 | 이슈 | 위치 | 심각도 | 난이도 | 효과 |
|------|------|------|--------|--------|------|
| 1 | H-3 ValidationMetricsView | validation/api/views.py:254-368 | HIGH | 높음 | 수백 쿼리 → 수 쿼리 |
| 2 | H-4 LeaderComparisonView | validation/api/views.py:459-475 | HIGH | 높음 | 메트릭×3 → 일괄 |
| 3 | H-2 AnalysisSession basket | rag_analysis/views.py:429 | HIGH | 쉬움 | 1줄 수정으로 중첩 N+1 제거 |
| 4 | H-1 User favorite_stock | users/views.py:93 | HIGH | 쉬움 | prefetch 1줄 |
| 5 | H-5 ChainSightGraphView | chain_sight/api/views.py:78 | HIGH | 중간 | 엣지 N+1 → bulk |
| 6 | H-6 trending entities | news/api/views.py:370 | HIGH | 중간 | prefetch + groupby |
| 7 | H-7 AdminNewsCategory | serverless/views_admin.py:505 | HIGH | 중간 | 배치 조회 |
| 8 | H-8/H-9 Serializer prefetch | stocks/serializers.py:241/451 | HIGH | 중간 | 뷰 prefetch (H-9는 사용여부 선확인) |
| 9 | M-1~M-7 | (상세 참조) | MED | 쉬움~중간 | 점진 개선 |
| 10 | L-1~L-10 | (상세 참조) | LOW | 쉬움 | 선택적 |

### 즉시 효과 큰 저비용 작업 (쉬움 + HIGH)
- **H-2** (`select_related("basket").prefetch_related("messages","basket__items")`)
- **H-1** (`prefetch_related("favorite_stock")`)
- → 1줄씩으로 HIGH 2건 해소 가능. **가장 먼저 권장**.

> 주의: H-9는 `WatchListStockSerializer`가 실제 라우팅에 연결되어 있는지 먼저 확인 후 작업 권장(미사용 시 우선순위 하향). 모든 권장은 별도 PR + 마이그레이션(인덱스)/회귀 테스트 동반 필요.
