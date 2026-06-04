# API 성능 감사 보고서

> **작성일**: 2026-06-04
> **범위**: 읽기 전용 성능 감사 (N+1 쿼리 / DB 인덱스 / 느린 Serializer / 페이지네이션)
> **대상**: 뷰 17개 + 모델 7개 + Serializer 11개
> **방식**: 코드 정적 분석 (실행/수정 없음). 라인 번호는 감사 시점(`main` HEAD `7d8f7a7`) 기준.

---

## 전제 사실 (분석 근거)

- **DRF 전역 페이지네이션 미설정**: `config/settings.py:354-355` REST_FRAMEWORK 블록에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 없음 (주석에 "audit P0 #14 페이지네이션 표준은 별도 PR" 명시). → 명시적 `pagination_class`가 없는 모든 list 엔드포인트는 **페이지네이션 미적용**. `APIView` + `Response(list)` 패턴은 어떤 경우에도 페이지네이션되지 않음.
- **`Stock.sector` / `Stock.industry`는 CharField** (FK 아님) → 이 두 필드 직렬화는 N+1 무관.
- 다수 stocks 뷰(exchange, fundamentals, market_movers, screener 일부)는 **외부 FMP 서비스 dict** 결과를 직렬화 → ORM N+1 구조적으로 불가능, 대부분 코드 레벨 `[:N]` slice 상한 존재.

---

## 요약 (심각도별 이슈 수)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 누락 | 합계 |
|--------|:--------:|:----------:|:--------------:|:----------------:|:----:|
| **HIGH** | 4 | 0 | 1 | 0 | **5** |
| **MED**  | 5 | 3 | 4 | 4 | **16** |
| **LOW**  | 6 | 4 | 1 | 5 | **16** |
| **합계** | 15 | 7 | 6 | 9 | **37** |

> **핵심 결론**: 코드베이스의 인덱스 위생은 전반적으로 매우 우수하며(대량 테이블 대부분 복합 인덱스 보유), 무제한 테이블 덤프는 외부 FMP 서비스 결과이거나 `[:N]` slice로 차단되어 있다. **실질 위험은 (1) validation 지표 카탈로그 루프 N+1, (2) chain_sight 그래프 엣지 루프 N+1, (3) news trending 중첩 N+1** 세 곳에 집중된다. 페이지네이션은 전역 표준 부재(설정 1줄)가 근본 원인이다.

### 최우선 수정 권장 (영향도 순)

| 순위 | 위치 | 유형 | 심각도 | 난이도 |
|:----:|------|------|:------:|:------:|
| 1 | `validation/api/views.py:261-353` `_build_metric` | N+1 (지표×연도 곱셈 폭증) | HIGH | 높음 |
| 2 | `validation/api/views.py:459-475` `LeaderComparisonView` | N+1 (전 지표 × 3쿼리) | HIGH | 높음 |
| 3 | `chain_sight/api/views.py:78-95` `ChainSightGraphView` | N+1 (엣지당 2쿼리) | HIGH | 중간 |
| 4 | `news/api/views.py:370-391` `trending` | N+1 (종목×기사×엔티티 3중) | HIGH | 중간 |
| 5 | `stocks/views_indicators.py:371-434` `IndicatorComparisonView` | N+1 (2N, 입력 상한 없음) | MED→HIGH | 중간 |
| 6 | `config/settings.py:354` | 전역 페이지네이션 표준 부재 | MED | 쉬움 |
| 7 | `news/models.py:535` `NewsCollectionLog.task_name` | 인덱스 누락 (운영 핫패스) | MED | 쉬움 |
| 8 | `stocks/serializers.py:241` `OverviewTabSerializer` (뷰 3곳) | Serializer +6 O2O 쿼리 | MED | 쉬움 |

---

# 상세

## 1. N+1 쿼리

### [HIGH] N+1-1 · validation `_build_metric` 지표 카탈로그 루프
- **위치**: `services/validation/api/views.py:261-353` (`ValidationMetricsView._build_metric` / `_build_category`)
- **난이도**: 높음
- **설명**: `_build_category`가 `metric_codes`를 순회하며 metric당 `_build_metric` 호출. 그 안에서 `MetricDefinition`(262), `CompanyMetricSnapshot` latest(279), 폴백(299), `CompanyBenchmarkDelta`(316), `CompanyMetricSnapshot` history(339), 그리고 **history 루프(343-353) 안에서 연도별 `PeerMetricBenchmark.objects.filter().first()`** 호출. `category=all`이면 전 카테고리 × 전 지표 × (5 + 연도별 peer 쿼리)로 쿼리 수가 곱셈으로 폭증한다. 본 감사에서 발견된 가장 심각한 N+1.
- **권장 수정**: metric_code 전체를 한 번에 `CompanyMetricSnapshot` / `CompanyBenchmarkDelta` / `PeerMetricBenchmark` bulk fetch 후 dict 매핑. `MetricDefinition`은 `in_bulk()`로 일괄 조회.

### [HIGH] N+1-2 · validation `LeaderComparisonView` 전 지표 루프
- **위치**: `services/validation/api/views.py:459-475`
- **난이도**: 높음
- **설명**: `for cat, mc in all_metrics:` (전 카테고리 × 전 지표) 루프 안에서 `MetricDefinition`(460) + `CompanyMetricSnapshot` company(464) + leader(470) = metric당 3쿼리. 전체 지표 수 × 3 N+1.
- **권장 수정**: company/leader snapshot을 `metric_code_id__in=[...]`로 각 1쿼리 일괄 조회 후 매핑.

### [HIGH] N+1-3 · chain_sight `ChainSightGraphView` 엣지 루프
- **위치**: `apps/chain_sight/api/views.py:78-95`
- **난이도**: 중간
- **설명**:
  ```python
  for edge in result.get("edges", []):    # depth=3이면 엣지 다수
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
  ```
  엣지당 2개 PostgreSQL 쿼리. depth가 클수록(max 3) 엣지 수십~수백으로 증가 → 명백한 N+1.
- **권장 수정**: 모든 `(a, b)` 페어를 모아 `Q` OR 또는 `__in` tuple 필터로 1~2 쿼리 일괄 조회 후 dict 매핑.

### [HIGH] N+1-4 · news `trending` 종목×기사×엔티티 3중 중첩
- **위치**: `services/news/api/views.py:370-391`
- **난이도**: 중간
- **설명**:
  ```python
  for item in trending_data:          # 최대 limit개 (기본 10)
      recent_articles = NewsArticle.objects.filter(
          entities__symbol=symbol, published_at__gte=from_date
      ).distinct().order_by("-published_at")[:3]
      ... NewsArticleListSerializer(recent_articles, many=True)
  ```
  루프마다 별도 쿼리 1회 + `NewsArticleListSerializer.entities`(NewsEntitySimpleSerializer, many)를 직렬화하는데 `recent_articles`에 `prefetch_related("entities")`가 없음 → 종목 × 기사 × 엔티티 N+1 중첩. (5분 캐시로 완화되나 cache miss 시 발생)
- **권장 수정**: 루프 쿼리에 `.prefetch_related("entities")` 추가. 가능하면 종목 전체를 한 번에 prefetch.

### [MED] N+1-5 · stocks `IndicatorComparisonView` 심볼 루프 (입력 상한 없음)
- **위치**: `packages/shared/stocks/views_indicators.py:371-434`
- **난이도**: 중간
- **설명**: `for symbol in symbols:` 루프 내 매 반복 2개 쿼리 — `Stock.objects.get(symbol=symbol)`(375), `DailyPrice.objects.filter(stock=stock).order_by("-date")[:50]`(381). 입력 심볼 N개 → 2N 쿼리. `symbols` 개수 상한 검증이 없어(빈 배열만 거부, 364) 수백 심볼 POST 시 수백 쿼리 + 지표 계산. 입력 무제한이라 잠재적 HIGH.
- **권장 수정**: (1) `symbols` 개수 상한(예: 50) 추가. (2) `Stock.objects.filter(symbol__in=symbols)` 일괄 조회 후 dict 매핑. 최소 Stock get을 루프 밖으로.

### [MED] N+1-6 · rag_analysis `AnalysisSessionListCreateView` basket nested 누락
- **위치**: `services/rag_analysis/views.py:429-433`
- **난이도**: 중간
- **설명**: `sessions = AnalysisSession.objects.filter(user=...).prefetch_related("messages")` 로 가져온 뒤 `AnalysisSessionSerializer(sessions, many=True)`. 이 serializer는 `messages`뿐 아니라 `basket = DataBasketSerializer`를 nested하고, `DataBasketSerializer`가 다시 `items`(many)를 직렬화한다. 뷰 prefetch는 `messages`만 → 세션 수만큼 basket 조회 + basket마다 items 조회 N+1.
- **권장 수정**: `.select_related("basket").prefetch_related("messages", "basket__items")`.

### [MED] N+1-7 · news `stock_news` entities prefetch 누락
- **위치**: `services/news/api/views.py:117-130`
- **난이도**: 쉬움
- **설명**: `articles = NewsArticle.objects.filter(...).distinct()` 에 `prefetch_related("entities")` 없음. `NewsArticleListSerializer`가 `entities`를 직렬화 → 기사 수만큼 entities N+1. (ViewSet 기본 queryset 71행엔 prefetch 있으나 이 액션은 자체 쿼리셋을 새로 만들어 미상속.) 추가로 `articles.count()`(129)를 직렬화 직후 또 호출.
- **권장 수정**: `.prefetch_related("entities")` 추가, `len(serializer.data)`로 count 대체.

### [MED] N+1-8 · validation `ValidationSummaryView` rank 루프 (고정 10쿼리)
- **위치**: `services/validation/api/views.py:147-166`
- **난이도**: 중간
- **설명**: `for mc in rank_metrics:`(5개 고정) 안에서 `CompanyBenchmarkDelta.first()` + `MetricDefinition.first()` = 지표당 2쿼리 × 5 = 고정 10쿼리. 개수 고정이라 MED.
- **권장 수정**: rank_metrics 전체를 `__in` bulk fetch 후 매핑.

### [MED] N+1-9 · serverless `AdminNewsCategoryView` resolve_symbols 루프
- **위치**: `services/serverless/views_admin.py:505-530`
- **난이도**: 중간
- **설명**: `for cat in NewsCollectionCategory.objects.all(): symbols = cat.resolve_symbols()` — `resolve_symbols()`가 sector→SP500Constituent 등을 매 호출 쿼리하면 카테고리 수만큼 N+1 (메서드 구현 미확인, sector/custom 분기상 DB 조회 가능성 높음). 카테고리 수가 적어 MED.
- **권장 수정**: `resolve_symbols`가 쿼리한다면 일괄 prefetch 또는 캐싱.

### [MED] N+1-10 · news `stock_sentiment` 동일 queryset 다중 평가
- **위치**: `services/news/api/views.py:160-237`
- **난이도**: 쉬움
- **설명**: `entities = NewsEntity.objects.filter(...).select_related("news")`(N+1은 방어됨)를 `exists()`(166) → `count()`(237) → 컴프리헨션 순회(186,204,209)로 동일 queryset을 3~4회 재평가 → 같은 쿼리 반복 실행.
- **권장 수정**: `entities = list(entities)`로 한 번만 평가 후 재사용.

### [MED] N+1-11 · chain_sight `SignalFeedView` Neo4j 라운드트립 반복
- **위치**: `apps/chain_sight/api/views.py:809-920` (`_build_chain_signals`)
- **난이도**: 높음
- **설명**: 시드 페어 루프마다 Neo4j `run_query`(shortestPath) 호출. PostgreSQL N+1은 아니나 페어 수만큼 Neo4j 라운드트립. `max_candidates = page_size*3` 상한 있음.
- **권장 수정**: 가능 시 배치 Cypher 쿼리로 묶기. 긴급도 중간.

### [LOW] N+1-12~15 · stocks `OverviewTabSerializer` 호출 4곳 (select_related 부분 누락)
- **위치**: `packages/shared/stocks/views.py:545` (`StockOverviewAPIView`), `:167-184` (`StockDetailView`), `:922-932` (`StockCompleteDataAPIView`), `views_mvp.py:158` (`StockMVPDetailView` full 모드)
- **난이도**: 중간
- **설명**: 모두 **단일 Stock 객체**에 `OverviewTabSerializer` 적용 → 루프형 N+1은 아니지만 객체당 +6 OneToOne 쿼리(`validation_news_summary`/`sensitivity_profile`/`growth_stage`/`capital_dna`/`narrative_tag` + reverse `category_signals`). `StockOverviewAPIView`는 `overview_ko`만 select_related(코드에 `# TODO prefetch_related 필요` 명시), 나머지 3곳은 select_related 전무. 캐싱(10분)으로 완화되나 cache miss마다 7쿼리. → 상세는 Serializer #SER-3 참조.
- **권장 수정**: 4개 뷰 queryset에 `.select_related("overview_ko","validation_news_summary","sensitivity_profile","growth_stage","capital_dna","narrative_tag").prefetch_related("category_signals")` 통일.

> **N+1 이슈 없음 확인**: `users/views.py`(Portfolio/Watchlist 전부 select_related 적용), `apps/market_pulse/views.py`, `services/sec_pipeline/views.py`, stocks의 exchange/fundamentals/market_movers/search/eod(select_related 적용).

---

## 2. DB 인덱스 누락

> 전반적으로 인덱스 위생 우수. 대량 테이블(EODSignal, NewsArticle, MarketMover, StockRelationship, InstitutionalHolding 등)은 뷰의 복합 필터/정렬에 맞춘 복합 인덱스를 이미 보유. 아래는 실제 뷰 쿼리 대비 비어 있는 케이스만.

### [MED] IDX-1 · NewsCollectionLog.task_name (운영 대시보드 핫패스)
- **위치**: `services/news/models.py:535` (필드), Meta 인덱스는 `:547` `(provider, -executed_at)`만 존재
- **난이도**: 쉬움 (migration 1건)
- **설명**: `news/api/views.py:1443-1449, 1616, 1668-1669, 1708-1709, 1752-1758, 2225, 2253`에서 `filter(task_name="...", executed_at__gte=...).order_by("-executed_at")`가 운영 대시보드에서 매우 빈번. 현 `(provider, -executed_at)` 인덱스는 task_name 필터를 커버 못 함.
- **권장 수정**: `Index(fields=["task_name", "-executed_at"])` 추가. (단 `task_name__icontains` 케이스는 여전히 인덱스 미적용 — exact 필터가 다수라 가치 있음)

### [MED] IDX-2 · NewsArticle.llm_analysis__tier (JSONB 내부 키 반복 집계)
- **위치**: `services/news/models.py:119` (`llm_analysis` JSONField)
- **난이도**: 중간 (GIN 인덱스 또는 비정규화)
- **설명**: `news/api/views.py:2088-2098`에서 `filter(llm_analyzed=True, llm_analysis__tier="A").count()`를 A/B/C 3회 반복. `llm_analyzed`는 `db_index=True`(117)지만 `llm_analysis__tier`는 JSONB 경로 조회로 B-tree 인덱스 없음. NewsArticle은 대량 테이블이며 대시보드에서 반복 호출.
- **권장 수정**: tier를 별도 컬럼(`tier = CharField(db_index=True)`)으로 비정규화하거나 PostgreSQL GIN 인덱스(`jsonb_path_ops`). 고트래픽이면 비정규화 권장.

### [MED] IDX-3 · NewsArticle.updated_at (일일 집계 범위 필터)
- **위치**: `services/news/models.py:139` (`updated_at`, `auto_now=True`, 인덱스 없음)
- **난이도**: 쉬움
- **설명**: `news/api/views.py:2078-2081` 등에서 `filter(updated_at__gte=today_start_kst, ...)`. 대개 `llm_analyzed`(인덱스 有)와 AND 조합이라 선두 인덱스가 일부 커버하나 단독 범위 스캔은 인덱스 없음.
- **권장 수정**: 빈번하면 `Index(fields=["llm_analyzed", "updated_at"])` 복합. 빈도 낮으면 보류.

### [LOW] IDX-4 · Stock.sector + market_capitalization 복합 정렬
- **위치**: `packages/shared/stocks/models.py:28` (sector), `:45` (market_capitalization)
- **난이도**: 쉬움
- **설명**: `views.py:118-132`에서 `filter(sector__icontains=...).filter(market_capitalization__gte=...).order_by("-market_capitalization")`. 단독 인덱스는 존재하나 **`sector__icontains`는 LIKE '%x%'라 인덱스 미적용**. Stock 테이블은 ~535행 소형이라 실질 영향 낮음.
- **권장 수정**: `icontains`→`exact`/`iexact` 전환 가능 시 `Index(fields=["sector", "-market_capitalization"])`. 테이블 규모상 후순위.

### [LOW] IDX-5 · NewsArticle.finnhub_id / marketaux_uuid (null 여부 필터)
- **위치**: `services/news/models.py:64, :67`
- **난이도**: 쉬움
- **설명**: `news/api/views.py:451-453, 514-519`에서 `filter(finnhub_id__isnull=False)` 등. 인덱스 없음. 주로 `published_at__gte`(인덱스 有)와 AND 조합이라 영향 제한적.
- **권장 수정**: 소스별 카운트가 핫패스면 partial index. 일반적으로 보류.

### [LOW] IDX-6 · UserInterest (정렬 인덱스 없음)
- **위치**: `packages/shared/users/models.py:282-291`
- **난이도**: 쉬움
- **설명**: `users/views.py:1046` `filter(user=...).order_by(...)`. user는 FK 자동 인덱스로 filter 커버, 사용자당 행 수 적어 정렬 비용 무시 가능.
- **권장 수정**: 불필요.

### [LOW] IDX-7 · ScreenerFilter.is_active + category (소량 메타 테이블)
- **위치**: `services/serverless/models.py:450, :495`
- **난이도**: 쉬움
- **설명**: `views.py:1109-1114` `filter(is_active=True).filter(category=...).order_by(...)`. ~50행 메타 테이블이라 풀스캔 무시 가능.
- **권장 수정**: 불필요.

> **인덱스 이슈 없음 확인**: EODSignal(4종 복합 인덱스로 전 패턴 커버), Portfolio/Watchlist/WatchlistItem, MarketMover, rag_analysis 전 모델(FK+복합 충분), sec_pipeline 전 모델, graph_analysis(dormant, API 미구현 — 감사 대상 외).

---

## 3. 느린 Serializer (SerializerMethodField 추가 쿼리)

### [HIGH] SER-1 · WatchListStockSerializer.get_latest_price
- **위치**: `packages/shared/stocks/serializers.py:451`
- **난이도**: 중간
- **설명**: 관심종목 리스트(many=True) 직렬화 시 Stock마다 1쿼리 — `DailyPrice.objects.filter(stock=obj).order_by("-date").first()`. N개 종목 → N개 추가 쿼리. `get_chart_data`(458-460)도 동일 패턴(단 `return` 누락으로 항상 None 반환 — 별도 버그).
- **권장 수정**: 뷰 queryset에서 `Prefetch`로 최신 DailyPrice 선로드, 또는 `annotate(latest_close=Subquery(...))`. **단, 현 호출 뷰가 grep상 미확인** — 사용처 생존 시 HIGH, 데드코드면 LOW로 강등 (확인 필요).

### [MED] SER-2 · OverviewTabSerializer.get_dynamic_layers / get_korean_overview
- **위치**: `packages/shared/stocks/serializers.py:241` (dynamic_layers), `:226` (korean_overview)
- **난이도**: 쉬움
- **설명**: 단일 객체 직렬화(detail)지만 7개 관계 순차 접근 — `category_signals.all()`(251, reverse FK), `validation_news_summary`(271), `sensitivity_profile`(289), `growth_stage`(304), `capital_dna`(322), `narrative_tag`(340), `overview_ko`(229). 호출 뷰가 `select_related`를 빠뜨리면 요청당 6~7쿼리. (코드 line 244에 TODO 명시)
- **권장 수정**: 호출 뷰 4곳(N+1-12~15 참조) queryset에 6개 O2O `select_related` + `category_signals` prefetch 통일.

### [MED] SER-3 · UserSerializer / PrivateUserSerializer.favorite_stock
- **위치**: `packages/shared/users/serializers.py:16, :26`
- **난이도**: 쉬움
- **설명**: `favorite_stock`(M2M)를 `StockListingField(many=True)`로 직렬화. list 직렬화(`users/views.py:93` `User.objects.all()`) 시 사용자마다 M2M 조회 1쿼리. 단일 객체(me/프로필)는 영향 작음.
- **권장 수정**: list 뷰에 `.prefetch_related("favorite_stock")` 추가.

### [MED] SER-4 · serverless preset/thesis `obj.user` FK 접근
- **위치**: `services/serverless/serializers.py:301` (get_owner_email), `:314` (get_is_owner), `:738` (InvestmentThesis get_is_owner)
- **난이도**: 쉬움
- **설명**: preset/thesis 리스트(many=True) 직렬화 시 `obj.user` 접근 → select_related 없으면 객체당 1쿼리.
- **권장 수정**: serverless ScreenerPreset/InvestmentThesis list queryset에 `.select_related("user")` 추가.

### [MED] SER-5 · news detail `entities__highlights` prefetch 누락
- **위치**: `services/news/api/serializers.py` (NewsArticleDetailSerializer → NewsEntitySerializer.highlights many=True)
- **난이도**: 쉬움
- **설명**: 주 ViewSet list는 `prefetch_related("entities")` 적용(정상)이나 `EntityHighlight`(highlights)는 prefetch 누락 → detail 직렬화 시 entity당 1쿼리.
- **권장 수정**: detail 뷰 queryset을 `prefetch_related("entities__highlights")`로 보강.

### [LOW] SER-6 · market_pulse FK source 잠재 N+1
- **위치**: `apps/market_pulse/serializers.py:29` (`source="indicator.code"`), `:46` (`source="index.symbol"`)
- **난이도**: 쉬움
- **설명**: IndicatorValue/MarketIndexPrice list 직렬화 시 FK traversal로 N+1 가능. 호출 뷰 미확인.
- **권장 수정**: 호출 뷰에 `select_related("indicator")` / `select_related("index")` 권장.

> **Serializer 이슈 없음 확인**: stocks의 fundamentals/market_movers/exchange/screener serializer(전부 FMP dict 입력, ORM 무관), rag_analysis serializer(메서드/상수 호출만), serverless의 IndicatorCalculator/Service 생성 필드(쿼리 아님, 객체 생성 오버헤드만 LOW), portfolio serializer(호출 뷰가 이미 `select_related("stock")` 적용 — 현 상태 정상).

---

## 4. 페이지네이션 누락

> **근본 원인**: 전역 `DEFAULT_PAGINATION_CLASS` 부재 (전제 사실 참조). 아래는 그로 인해 무제한 반환되는 엔드포인트.

### [MED] PAG-1 · users `Users.get` 전체 사용자 반환
- **위치**: `packages/shared/users/views.py:92-95`
- **난이도**: 중간
- **설명**: `User.objects.all()`을 `UserSerializer(many=True)`로 반환. 페이지네이션 없음. IsAdminUser 한정이나 사용자 수만큼 무제한 증가. (SER-3 favorite_stock N+1 동반)
- **권장 수정**: Paginator 수동 적용 (같은 파일 624-655 Watchlist 패턴 재사용).

### [MED] PAG-2 · rag_analysis `DataBasketListCreateView.get`
- **위치**: `services/rag_analysis/views.py:50-54`
- **난이도**: 중간
- **설명**: `DataBasket.objects.filter(user=...)` 전체 반환. 각 basket이 items nested 직렬화 → 데이터 폭증 가능.
- **권장 수정**: Paginator 적용 (같은 파일 783 `UsageHistoryView` 패턴 재사용).

### [MED] PAG-3 · rag_analysis `AnalysisSessionListCreateView.get`
- **위치**: `services/rag_analysis/views.py:427-433`
- **난이도**: 중간
- **설명**: 사용자 전 세션 무제한 반환 + N+1-6 동반.
- **권장 수정**: Paginator 적용 + `select_related/prefetch_related` 보강.

### [MED] PAG-4 · news `collection_logs` 전체 반환
- **위치**: `services/news/api/views.py:1452-1465`
- **난이도**: 중간
- **설명**: `list(qs.values(...))` 전체 반환(상한 없음, days≤30이나 하루 다건 누적 가능). IsAdminUser.
- **권장 수정**: 페이지네이션 또는 행 수 상한.

### [LOW] PAG-5 · rag_analysis `SessionMessagesView.get`
- **위치**: `services/rag_analysis/views.py:489-498`
- **난이도**: 쉬움
- **설명**: `session.messages.all()` 전체 반환. 긴 대화는 메시지 수 무제한.
- **권장 수정**: Paginator 적용.

### [LOW] PAG-6 · users `UserFavorites.get`
- **위치**: `packages/shared/users/views.py:195-201`
- **난이도**: 쉬움
- **설명**: `user.favorite_stock.all()` 전체 반환. 보통 소량(사용자당 즐겨찾기).
- **권장 수정**: 소량이라 보류 가능. 단 StockSerializer FK 참조 시 prefetch 권장.

### [LOW] PAG-7 · serverless `AdminNewsCategoryView.get`
- **위치**: `services/serverless/views_admin.py:505-531`
- **난이도**: 쉬움
- **설명**: `NewsCollectionCategory.objects.all()` 전체. 카테고리 소량 + IsAdminUser. (N+1-9 동반)
- **권장 수정**: 보류 가능 (소량).

### [LOW] PAG-8 · stocks screener 6개 뷰 (최대 1000개)
- **위치**: `packages/shared/stocks/views_screener.py` (StockScreener/LargeCap/HighDividend/Sector/LowBeta/Exchange)
- **난이도**: 중간
- **설명**: 외부 FMP 결과를 `Response`에 list로 직접 반환(APIView라 자동 페이지네이션 불가). `limit`이 `min(max(1,limit),1000)`로 최대 1000개(283,338,393,451,507). ORM 아님(N+1 없음). 1000개 직렬화는 중간 부하.
- **권장 수정**: limit 상한 1000→200 축소 또는 커서/페이지 파라미터 도입. 긴급도 낮음.

### [LOW] PAG-9 · news `trending` / `market` (limit 상한 검증 없음)
- **위치**: `services/news/api/views.py:325-396` (trending), `:255-323` (market)
- **난이도**: 쉬움
- **설명**: `[:limit]` slice만 있고 `limit` 상한 검증 없음(`int(...)`) → 과도한 limit 가능.
- **권장 수정**: `limit = min(int(...), 50)` 상한 추가.

> **페이지네이션 이슈 없음 확인**: stocks `StockListAPIView`(StockListPagination 명시), news ViewSet list/all_news(자체 pagination + prefetch), validation 전 엔드포인트(고정 지표/카테고리 또는 단일 symbol), chain_sight(SectorGraph/NeighborGraph limit≤30, SignalFeed page/page_size 구현), users Watchlist 계열(Paginator 수동 구현), market_pulse/sec_pipeline(외부 서비스 결과/단건).

---

## 부록: 검사 범위

**뷰 (17개)**: stocks/{views, views_search, views_exchange, views_eod, views_screener, views_market_movers, views_fundamentals, views_indicators, views_mvp}, users/views, news/api/views, market_pulse/views(=macro), rag_analysis/views, serverless/views_admin, validation/api/views, chain_sight/api/views, sec_pipeline/views

**모델 (7개)**: stocks/models, users/models, news/models, serverless/models, rag_analysis/models, sec_pipeline/models, graph_analysis/models(dormant)

**Serializer (11개)**: stocks/{serializers, serializers_fundamentals, serializers_market_movers, serializers_exchange, serializers_screener}, users/serializers, portfolio/api/serializers, market_pulse/serializers, rag_analysis/serializers, serverless/serializers, news/api/serializers

> 실제 디렉토리 구조는 monorepo(`packages/shared/`, `apps/`, `services/`). 지시서의 논리 경로 ↔ 실제 경로 매핑: `stocks/`→`packages/shared/stocks/`, `users/`→`packages/shared/users/`, `macro/`→`apps/market_pulse/`, `chainsight/`→`apps/chain_sight/`, `news,rag_analysis,serverless,validation,sec_pipeline`→`services/*`.

---

*본 보고서는 정적 코드 분석 결과이며 코드를 수정하지 않았습니다. 라인 번호는 감사 시점 기준으로, 파일 변경 시 재확인이 필요합니다.*
