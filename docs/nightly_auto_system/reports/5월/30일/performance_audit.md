# API 성능 감사 보고서

- **작성일**: 2026-05-30
- **대상**: 뷰 17개 + 모델 7개 + Serializer 11경로
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음, 라인 번호 실측)
- **주의**: 모노레포 마이그레이션으로 일부 경로 변경됨 (`stocks/` → `packages/shared/stocks/`, `users/` → `packages/shared/users/`, `graph_analysis/` → `services/_dormant/graph_analysis/`)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 쿼리 | 인덱스 누락 | 느린 Serializer | 페이지네이션 | 합계 |
|--------|:--------:|:-----------:|:---------------:|:------------:|:----:|
| **HIGH** | 4 | 1 | 3 | 0 | **8** |
| **MED** | 3 | 0 | 3 | 2 | **8** |
| **LOW** | 0 | 0 | 4 | 5 | **9** |
| **합계** | **7** | **1** | **10** | **7** | **25** |

> 일부 이슈는 카테고리가 겹친다(예: Watchlist serializer = N+1 + 느린 Serializer). 위 표는 카테고리별 1차 분류 기준이며, 중복 제거 후 **고유 이슈는 약 20건**이다.

### 최우선 수정 권장 (HIGH, 캐시 미적용)

| 순위 | 위치 | 유형 | 핵심 |
|:----:|------|------|------|
| 1 | `validation/api/views.py:228-294` | N+1 (중첩) | 캐시 없음. 지표 M개 × 5년 = 약 5M `PeerMetricBenchmark` 쿼리 |
| 2 | `validation/api/views.py:373-383` | N+1 | 캐시 없음. 약 3M 쿼리 (`MetricDefinition` + 스냅샷 2회) |
| 3 | `chainsight/api/views.py:73-86` | N+1 | 캐시 없음. edge 수 E × 2 (`CoMentionEdge` + `PriceCoMovement`) |
| 4 | `news/api/views.py:352-364` | N+1 | trending 종목별 기사 쿼리 + entities 직렬화 (5분 캐시로 완화) |
| 5 | `packages/shared/stocks/serializers.py:451-458` | 느린 Serializer | Watchlist N종목 × 2N `DailyPrice` 쿼리 + `get_chart_data` return 누락 버그 |
| 6 | `packages/shared/stocks/serializers.py:241-353` | 느린 Serializer | 상세페이지당 OneToOne 6 + reverse FK 1 = 7 lazy 쿼리 |
| 7 | `news/api/serializers.py:20` | 느린 Serializer | `entities__highlights` 2단 중첩 미prefetch (한 줄 수정으로 해결) |
| 8 | `packages/shared/stocks/models.py:900` | 인덱스 누락 | `SP500Constituent.sub_sector` — 형제 `sector`만 인덱스, 뉴스 배치 반복 풀스캔 |

### 전반적 평가

- **인덱스 설계는 매우 우수**: status/type/date/symbol 류 단골 필터는 거의 전부 `db_index=True` / `Meta.indexes` / FK 자동 인덱스로 커버. 실제 누락은 단 1건.
- **페이지네이션 위험은 낮음**: `Model.objects.all()` 전수 직렬화 폭주 패턴 거의 없음. 대부분 `[:limit]` slice 또는 외부 API limit clamp로 상한 처리. `StockListAPIView`는 `PageNumberPagination` 정상 적용(50/200).
- **stocks 뷰의 절반(views_search/exchange/screener/market_movers/fundamentals)은 외부 FMP API 직렬화**라 ORM N+1 범주 자체에 해당 없음.
- **진짜 위험은 validation/chainsight의 캐시 없는 N+1 루프**. news 쪽은 5~30분 캐시로 cold-cache에만 영향.

---

## 상세

### 1. N+1 쿼리

#### [HIGH] 1-1. `validation/api/views.py:228-294` — `ValidationMetricsView._build_metric` 연도별 중첩 N+1
- **유형**: N+1 (중첩) · **난이도**: 중간~높음
- **문제 코드**:
  ```python
  snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('fiscal_year')[:5]
  for s in snaps:
      peer_bench = PeerMetricBenchmark.objects.filter(symbol=stock, fiscal_year=s.fiscal_year, metric_code=md).first()
  ```
- **설명**: `_build_category`(213)에서 카테고리 지표마다 `_build_metric` 호출. 각 호출이 연도(최대 5)마다 `PeerMetricBenchmark` 쿼리 → 지표 M개 × 5년 = **5M 쿼리**. `category=all`이면 전 카테고리 곱연산. 추가로 `MetricDefinition.objects.filter(pk=mc).first()`(214)도 지표마다 1회. **캐시 없음.**
- **권장 수정**: 연도 루프 전 일괄 조회 후 dict 매핑.
  ```python
  years = [s.fiscal_year for s in snaps]
  benches = {b.fiscal_year: b for b in PeerMetricBenchmark.objects.filter(
      symbol=stock, metric_code=md, fiscal_year__in=years)}
  # _build_category 진입 시 MetricDefinition도 pk__in 일괄 로드
  ```

#### [HIGH] 1-2. `validation/api/views.py:373-383` — `LeaderComparisonView.get` 지표별 N+1
- **유형**: N+1 · **난이도**: 중간
- **문제 코드**:
  ```python
  for cat, mc in all_metrics:
      md = MetricDefinition.objects.filter(pk=mc).first()
      company_snap = CompanyMetricSnapshot.objects.filter(symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, ...).first()
      leader_snap = CompanyMetricSnapshot.objects.filter(symbol_id=leader.symbol, ...).first()
  ```
- **설명**: `CATEGORY_METRICS` 전체 지표 M에 대해 루프마다 3쿼리 = 약 **3M 쿼리**. 캐시 없음.
- **권장 수정**:
  ```python
  codes = [mc for _, mc in all_metrics]
  md_map = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=codes)}
  snaps = CompanyMetricSnapshot.objects.filter(
      symbol_id__in=[stock.symbol, leader.symbol], fiscal_year=latest_fy,
      metric_code_id__in=codes, value_status='normal')
  snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
  ```

#### [HIGH] 1-3. `chainsight/api/views.py:73-86` — `ChainSightGraphView.get` edge별 N+1
- **유형**: N+1 · **난이도**: 중간
- **문제 코드**:
  ```python
  for edge in result.get("edges", []):
      cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
      pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
  ```
- **설명**: edge 수 E에 대해 2E 쿼리. depth 최대 3이면 edge 수 큼. **캐시 없음.** (참고: 같은 파일의 `SectorGraphView`/`NeighborGraphView`는 `symbol__in` 일괄 조회 + dict 매핑하는 모범 패턴 — 이 뷰만 미적용.)
- **권장 수정**: 모든 (a,b) 쌍 수집 후 `symbol_a__in`/`symbol_b__in` 일괄 조회하여 `{(a,b): obj}` dict 매핑.

#### [HIGH] 1-4. `news/api/views.py:352-364` — `NewsViewSet.trending` 종목별 N+1
- **유형**: N+1 · **난이도**: 중간
- **문제 코드**:
  ```python
  for item in trending_data:
      recent_articles = NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')[:3]
      ...NewsArticleListSerializer(recent_articles, many=True)
  ```
- **설명**: 집계 종목마다 기사 쿼리 + 각 기사 `entities`(many=True) 직렬화로 추가 쿼리. 5분 캐시로 완화되나 cold-cache 비용 큼.
- **권장 수정**: 루프 내 queryset에 `.prefetch_related('entities')` 추가, 가능하면 종목 목록 in-clause로 묶어 메모리 그룹핑.

#### [MED] 1-5. `validation/api/views.py:121-133` — `ValidationSummaryView.get` rank 지표 N+1
- **유형**: N+1 · **난이도**: 쉬움
- **문제 코드**:
  ```python
  for mc in rank_metrics:
      delta = CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc).first()
      md = MetricDefinition.objects.filter(pk=mc).first()
  ```
- **설명**: 고정 5개 지표라 최대 약 10쿼리. 캐시 없음.
- **권장 수정**: `metric_code_id__in=rank_metrics`로 `CompanyBenchmarkDelta`/`MetricDefinition` 일괄 조회 후 dict 매핑.

#### [MED] 1-6. `serverless/views_admin.py:475-497` — `AdminNewsCategoryView.get` resolve_symbols 루프
- **유형**: N+1 (메서드 호출형) · **난이도**: 중간
- **문제 코드**:
  ```python
  categories = NewsCollectionCategory.objects.all()
  for cat in categories:
      symbols = cat.resolve_symbols()  # 내부에서 SP500Constituent 등 DB 조회
  ```
- **설명**: 관리자 전용·저빈도이나 카테고리마다 `resolve_symbols()`가 DB를 침 (`news/models.py:651`의 `SP500Constituent.objects.filter(sub_sector=...)`). 인덱스 누락(2-1)과 복합 영향.
- **권장 수정**: sector/sub_sector 조회를 루프 밖 일괄 캐싱, 또는 목록 응답에서 `resolved_symbol_count` 지연 계산/생략.

#### [MED] 1-7. `news/api/views.py:108-115` & `:292-297` — `stock_news` / `market` entities prefetch 누락
- **유형**: select_related/prefetch 누락 · **난이도**: 쉬움
- **문제 코드**:
  ```python
  articles = NewsArticle.objects.filter(entities__symbol=symbol, ...).distinct().order_by('-published_at')
  serializer = self.get_serializer(articles, many=True)  # NewsArticleListSerializer가 entities 직렬화
  ```
- **설명**: ViewSet base queryset은 prefetch가 있으나, 이 액션들은 별도 queryset을 만들어 prefetch가 빠짐. 10분 캐시로 cold-cache에만 영향.
- **권장 수정**: 두 queryset에 `.prefetch_related('entities')` 추가.

> **N+1 이슈 없음 / 이미 방어됨**: `views_eod.py:81`(`.select_related("stock")` 적용), `users/views.py` Watchlist 계열(`prefetch_related("items__stock")`), `chainsight` Sector/Neighbor 뷰(in-clause 일괄), `macro`/`sec_pipeline`(외부 서비스 위임). stocks 뷰 중 `views_indicators.py:371-384`(`IndicatorComparisonView`)는 루프 내 per-symbol 쿼리 2N + 입력 상한 없음 — **MED 추가 항목**(아래 권장: `Stock.objects.filter(symbol__in=...)` 일괄 + 입력 길이 상한).

---

### 2. 인덱스 누락

#### [HIGH] 2-1. `packages/shared/stocks/models.py:900` — `SP500Constituent.sub_sector`
- **난이도**: 쉬움 (소형 테이블 ~500행, 마이그레이션 1개)
- **문제 코드**:
  ```python
  # models.py:900 — 인덱스 없음 (형제 sector는 line 899에서 db_index=True)
  sub_sector = models.CharField(max_length=100, blank=True, default="")
  ```
- **실제 사용처** (filter 다수):
  - `serverless/views_admin.py:529` — `filter(sub_sector=value, is_active=True).exists()`
  - `serverless/views_admin.py:610` — 배치 검증 루프
  - `news/models.py:651` — `resolve_symbols()`에서 `filter(sub_sector=self.value, is_active=True)` (뉴스 수집 Celery Beat 배치 반복 호출)
- **설명**: 형제 `sector`만 인덱스가 있는 명백한 비대칭. 테이블은 작지만 뉴스 수집 배치가 카테고리마다 반복 호출 → 풀스캔 누적.
- **권장 수정**: `is_active`와 함께 자주 쓰이므로 복합 인덱스가 효율적.
  ```python
  # Meta.indexes (line 929)
  indexes = [
      models.Index(fields=["is_active", "symbol"]),
      models.Index(fields=["sub_sector", "is_active"]),  # 추가
  ]
  ```

> **누락 아님으로 확인 (오탐 방지)**: `Stock.exchange/asset_type`(필터 미사용), `SignalAccuracy.signal_tag`(unique_together + 복합 인덱스), `StockNews.symbol/industry`(복합 인덱스), `NewsArticle.importance_score/llm_analyzed/published_at`(전부 `db_index=True`), `NewsEntity.symbol`(`db_index=True`), `MarketMover.rank`/`StockKeyword.status`/`CorporateAction.action_type`(복합 인덱스 또는 update_or_create), sec_pipeline status 필드(저빈도 + 인덱스 보유), users/rag/graph_analysis(전부 FK + unique_together + 복합 인덱스 커버). graph_analysis는 휴면 앱.

---

### 3. 느린 Serializer

#### [HIGH] 3-1. `packages/shared/stocks/serializers.py:241-353` — `OverviewTabSerializer.get_dynamic_layers`
- **난이도**: 중간
- **문제 코드**:
  ```python
  signals = list(obj.category_signals.all())   # reverse FK → 쿼리 1
  ns = obj.validation_news_summary             # OneToOne → 쿼리 2
  sp = obj.sensitivity_profile                 # OneToOne → 쿼리 3
  gs = obj.growth_stage; cd = obj.capital_dna; nt = obj.narrative_tag  # 쿼리 4~6
  ```
- **설명**: 단건 직렬화이나 한 메서드에서 OneToOne 6 + reverse FK 1 = **최대 7 lazy 쿼리**. 상세 페이지 로드마다 발생. 호출처 `views.py:184/545/572/585/932`, `views_mvp.py:158`. 코드에 `# TODO: prefetch 필요` 주석 존재.
- **권장 수정**: 뷰 queryset에 일괄 적용.
  ```python
  Stock.objects.select_related(
      "overview_ko", "validation_news_summary", "sensitivity_profile",
      "growth_stage", "capital_dna", "narrative_tag"
  ).prefetch_related("category_signals")
  ```

#### [HIGH] 3-2. `packages/shared/stocks/serializers.py:451-458` — `WatchListStockSerializer.get_latest_price` / `get_chart_data`
- **난이도**: 중간
- **문제 코드**:
  ```python
  def get_latest_price(self, obj):
      latest = DailyPrice.objects.filter(stock=obj).order_by("-date").first()
  def get_chart_data(self, obj):
      recent_prices = DailyPrice.objects.filter(stock=obj).order_by("-date")[:7]
      # ← return 문 누락: 항상 None 반환 (잠재 버그)
  ```
- **설명**: Watchlist는 본질적으로 N종목 리스트(many=True). 종목당 2쿼리 = **2N 쿼리**. + `get_chart_data`에 `return` 누락 (CLAUDE.md "Processor return 필수" 규칙 성격 위반).
- **권장 수정**: 뷰에서 `Prefetch("dailyprice_set", queryset=DailyPrice.objects.order_by("-date"), to_attr="recent_prices")`로 적재, 메서드는 `obj.recent_prices[:7]` 슬라이싱. 최신가는 `Stock.real_time_price` 활용으로 쿼리 제거 가능. `get_chart_data`에 `return` 추가.

#### [HIGH] 3-3. `news/api/serializers.py:20` — `NewsEntitySerializer.highlights` 2단 중첩
- **난이도**: 쉬움 (한 줄 수정 — 가장 효율 높음)
- **문제 코드**:
  ```python
  class NewsEntitySerializer(serializers.ModelSerializer):
      highlights = EntityHighlightSerializer(many=True, read_only=True)  # reverse relation
  ```
- **설명**: `NewsArticleDetailSerializer.entities`(many=True) → 각 entity의 `highlights`(many=True) 2단 중첩. 뷰 queryset(`news/api/views.py:64`)은 `prefetch_related('entities')`만 하고 `entities__highlights`는 미prefetch → retrieve 시 entity N개당 N+1.
- **권장 수정**: `news/api/views.py:64` → `prefetch_related('entities', 'entities__highlights')`.

#### [MED] 3-4. `serverless/serializers.py:122-138` — `MarketMoverListSerializer` (3개 메서드)
- **난이도**: 쉬움 · **유형**: row당 객체 반복 생성 (DB 쿼리 아님)
- **문제 코드**: `get_sector_alpha_display` 등에서 row·필드마다 `IndicatorCalculator()` 신규 인스턴스화 (리스트 길이 × 3회).
- **권장 수정**: 모듈 레벨 단일 인스턴스(`_CALC = IndicatorCalculator()`) 재사용 또는 `format_*`를 `@staticmethod`로.

#### [MED] 3-5. `serverless/serializers.py:209-213` — `MarketBreadthSerializer.get_signal_interpretation`
- **난이도**: 쉬움 · row당 `MarketBreadthService()` 인스턴스 생성. 모듈 레벨 캐시 또는 staticmethod 매핑 권장.

#### [MED] 3-6. `serverless/serializers.py:420-423` — `SectorPerformanceSerializer.get_name_ko`
- **난이도**: 쉬움 · `SectorHeatmapSerializer.sectors`(many=True)에서 row마다 함수 내 import + 상수 조회. import를 모듈 상단으로 이동(순환 import 주의).

#### [LOW] 3-7. `serverless/serializers.py:272-288` — `ScreenerPresetSerializer.get_owner_email/get_is_owner`
- **난이도**: 쉬움 · `obj.user` FK 접근 (리스트 시 N+1 소지, 단 리스트 전용 serializer는 user 미노출이라 영향 제한). 뷰에 `select_related("user")` 보장 권장.

#### [LOW] 3-8. `serverless/serializers.py:532-628` — `ScreenerAlertSerializer.get_preset_name` / `AlertHistorySerializer.alert_name`
- **난이도**: 쉬움 · `obj.preset.*`, `source='alert.name'` FK 체인. 리스트 뷰에 `select_related("preset")`, `select_related("alert")` 추가.

#### [LOW] 3-9. `packages/shared/users/serializers.py:16, 26` — `UserSerializer.favorite_stock` / `PrivateUserSerializer.favorite_stock`
- **난이도**: 쉬움 · `StockListingField(many=True)`로 M2M 직렬화. user 조회 뷰에 `prefetch_related("favorite_stock")` 추가.

#### [LOW] 3-10. `news/api/views.py:354` (serializer `news/api/serializers.py:128`) — `TrendingStockSerializer.recent_articles`
- **난이도**: 중간 · trending 루프 종목당 `NewsArticle.objects.filter(...)[:3]` queryset이 entities 미prefetch (1-4와 동일 뿌리). 5분 캐시로 완화 → LOW. 해당 queryset에 `.prefetch_related('entities')`.

> **Serializer 이슈 없음 (clean)**: `serializers_exchange/fundamentals/market_movers/screener.py`(전부 FMP dict 기반, ORM 쿼리 없음), `macro/serializers.py`(단순 source 필드, 메서드 내 쿼리 없음), `rag_analysis/serializers.py`(메서드 자체는 clean — 단 뷰 prefetch는 적용 확인됨), `chainsight/serializers/path_watchlist.py`(JSON 필드 접근 + 뷰에서 `prefetch_related('actions')` 보장 — 모범 사례).

---

### 4. 페이지네이션 누락

> 대부분 select_related/prefetch가 이미 적용돼 N+1은 없고, queryset 무제한 직렬화로 인한 **응답 페이로드 폭주** 리스크 차원의 지적이다.

#### [MED] 4-1. `rag_analysis/views.py:376-380` — `AnalysisSessionListCreateView.get`
- **난이도**: 쉬움
- **문제 코드**:
  ```python
  sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')
  serializer = AnalysisSessionSerializer(sessions, many=True)
  ```
- **설명**: prefetch로 N+1은 방지되나, `AnalysisSessionSerializer.messages`(many=True)를 목록 응답에서 **전 세션 전 메시지** 직렬화 → 누적 시 페이로드 폭주.
- **권장 수정**: 목록 응답에서 messages 제외(전용 경량 serializer) 또는 페이지네이션 추가.

#### [MED] 4-2. `packages/shared/users/views.py:92-95` — `Users.get`
- **난이도**: 쉬움
- **문제 코드**:
  ```python
  users = User.objects.all()
  serializer = UserSerializer(users, many=True)  # favorite_stock M2M 직렬화 → N+1
  ```
- **설명**: 관리자 전용·저빈도이나 전체 User 무제한 반환 + `favorite_stock` prefetch 없음 (페이지네이션 + N+1 복합).
- **권장 수정**: `User.objects.all().prefetch_related("favorite_stock")` + DRF 페이지네이션.

#### [LOW] 4-3 ~ 4-7. select_related/prefetch는 적용됐으나 상한 미설정
- `packages/shared/users/views.py:195`(`UserFavorites.get`), `:269`(`PortfolioListCreateView`, `select_related("stock")` 적용), `:414`(`PortfolioDetailTableView`, 합계는 별도 aggregate 필요), `:1045`(`UserInterestListCreateView`) — 모두 N+1 없음, 데이터 규모 커지면 페이지네이션.
- `rag_analysis/views.py:48`(`DataBasketListCreateView`, prefetch 적용), `:439`(`SessionMessagesView`) — 사용자당 소량, LOW.
- `packages/shared/stocks/views_mvp.py:41-62`(`StockMVPListView`) — `[:20]` 하드 상한 존재로 폭주 없음. offset 페이지 이동 미지원의 기능적 한계만.

> **페이지네이션 양호**: `StockListAPIView`(`PageNumberPagination` 50/200 명시), `news/api/views.py:416`(`all_news`, offset/limit + prefetch), `rag_analysis/views.py:702`(`UsageHistoryView`, Paginator), Watchlist 계열. 외부 API 직렬화 뷰들은 전부 limit clamp(1~20/40/1000) 처리.

---

## 부록: 추가 발견 (범위 보완)

- **`packages/shared/stocks/views_indicators.py:371-384` (`IndicatorComparisonView.post`)** — [MED] 루프 내 per-symbol `Stock.objects.get()` + `DailyPrice.objects.filter()` = 입력 심볼 N개당 2N 쿼리, **입력 길이 상한 없음 + 캐시 없음**. 권장: `Stock.objects.filter(symbol__in=symbols)` 일괄 조회 + 입력 상한(`[:20]`).
- **`packages/shared/stocks/views.py:545-551` (`StockOverviewAPIView`)** — [MED] `overview_ko`만 select_related, 나머지 6개 관계 미적용 (3-1과 동일 뿌리, 뷰 측 한 줄 보강으로 동시 해결).

---

## 권장 조치 우선순위

1. **즉시 (HIGH, 캐시 없음 → 운영 부하 직접 영향)**: validation `_build_metric`/`LeaderComparison`(1-1, 1-2), chainsight Graph edges(1-3) — 일괄 조회 + dict 매핑 리팩터.
2. **한 줄 수정으로 큰 효과 (HIGH, 난이도 낮음)**: news `entities__highlights` prefetch(3-3), `StockOverviewAPIView` select_related 보강(3-1 / 부록).
3. **버그 동반 (HIGH)**: Watchlist serializer(3-2) — `get_chart_data` return 누락 함께 수정.
4. **인덱스 1건 (HIGH, 마이그레이션)**: `SP500Constituent.sub_sector`(2-1).
5. **보강 (MED/LOW)**: 페이지네이션(4-1, 4-2), serializer 인스턴스화 최적화(3-4~3-6), FK 체인 select_related(3-7~3-9).

*본 보고서는 정적 분석 기반이며, 실제 쿼리 수는 `django-debug-toolbar` 또는 `assertNumQueries`로 검증 권장. 코드는 수정하지 않았음.*
