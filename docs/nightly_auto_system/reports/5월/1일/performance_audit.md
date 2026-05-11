# API 성능 감사 보고서

- 감사일: 2026-05-01
- 대상: Backend Django/DRF (`stocks/`, `users/`, `news/`, `macro/`, `rag_analysis/`, `serverless/`, `validation/`, `chainsight/`, `sec_pipeline/`)
- 범위: 뷰 17개, 모델 7개, Serializer 10개 + 글로벌 설정(`config/settings.py`)
- 방식: 정적 코드 감사 (실행/프로파일링 없음, 코드 수정 없음)

---

## 요약 (이슈 수 by 심각도)

| 심각도 | N+1 | 인덱스 | Serializer | 페이지네이션 | 합계 |
|--------|-----|--------|-----------|-------------|------|
| HIGH   | 6   | 0      | 2         | 4           | **12** |
| MED    | 5   | 1      | 1         | 1           | **8**  |
| LOW    | 0   | 2      | 0         | 1           | **3**  |
| **총계** | **11** | **3** | **3** | **6** | **23** |

### 핵심 발견

1. **`config/settings.py:341-349` REST_FRAMEWORK 설정에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE`가 없음.** → 글로벌 페이지네이션 미적용. 모든 ListAPIView/ViewSet은 자체 설정이 없으면 무제한 반환 가능. (HIGH, 수정 난이도: 쉬움)
2. **`validation/api/views.py`** 3개 뷰에서 카테고리/지표 루프 안에서 `MetricDefinition.objects.filter().first()`, `CompanyMetricSnapshot.objects.filter().first()`, `PeerMetricBenchmark.objects.filter().first()`를 매 iteration 호출. 하나의 GET 요청에 100~300+ 쿼리 발생 가능. (HIGH)
3. **`stocks/serializers.py:381-409` WatchListStockSerializer**의 `get_latest_price` / `get_chart_data`가 종목별로 `DailyPrice` 쿼리를 호출. N개 종목 → 2N 추가 쿼리. (HIGH)
4. **`news/api/views.py:42` NewsViewSet**은 `NewsArticle.objects.all()`을 페이지네이션 없이 직렬화. 뉴스 테이블이 수만 건 단위로 성장하면 OOM/느린 응답 위험. (HIGH)
5. 모델 인덱스는 전체적으로 양호. 다만 `rag_analysis.AnalysisSession`은 `ordering=['-updated_at']`만 정의되고 인덱스가 없음.

---

## 상세

### 1. N+1 쿼리

#### [HIGH-1] `validation/api/views.py:112-124` — `ValidationDashboardView.get`
```python
rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
for mc in rank_metrics:
    delta = CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
    ).first()
    if delta and delta.rank and delta.total:
        md = MetricDefinition.objects.filter(pk=mc).first()
```
- 5회 루프 × 2쿼리 = **최대 10 쿼리**.
- 권장 수정 (난이도: **쉬움**):
  - `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics).select_related('metric_code')` 1회 + 파이썬 dict로 매핑
  - 또는 `MetricDefinition.objects.in_bulk(rank_metrics)` 캐싱

#### [HIGH-2] `validation/api/views.py:191-285` — `ValidationMetricsView` & `_build_metric`
```python
for cat in categories:                           # ~7
    cat_data = self._build_category(stock, cat)  # 내부에서
        for mc in metric_codes:                  # 평균 ~5
            md = MetricDefinition.objects.filter(pk=mc).first()           # 1
            metrics_data.append(self._build_metric(stock, md))            # 내부에서:
                # latest_snap, any_snap, delta = 각각 .filter(...).first()  # 3
                snaps = CompanyMetricSnapshot.objects.filter(...)[:5]
                for s in snaps:                                            # 5
                    PeerMetricBenchmark.objects.filter(...).first()        # 1
```
- 카테고리 7 × 메트릭 5 × (4 단건 쿼리 + 5 peer band 쿼리) ≈ **300+ 쿼리**.
- 권장 수정 (난이도: **높음**):
  - `MetricDefinition.objects.in_bulk()`로 메트릭 정의 일괄 조회
  - `CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code_id__in=all_codes)`를 한 번에 가져와 `(metric_code, fiscal_year)` dict 구성
  - `CompanyBenchmarkDelta`, `PeerMetricBenchmark`도 동일 패턴으로 사전 적재
- 캐싱 후보: `MetricDefinition`은 마스터 데이터이므로 `lru_cache` 또는 Redis 영속 캐시.

#### [HIGH-3] `validation/api/views.py:361-372` — `LeaderComparisonView.get`
```python
for cat, mc in all_metrics:                                  # ~35
    md = MetricDefinition.objects.filter(pk=mc).first()      # 1
    company_snap = CompanyMetricSnapshot.objects.filter(...).first()  # 1
    leader_snap = CompanyMetricSnapshot.objects.filter(...).first()   # 1
```
- 35 × 3 = **약 105 쿼리**.
- 권장 수정 (난이도: **중간**): 두 종목(stock, leader) × 모든 metric_code를 단일 쿼리로 받아 dict 매핑. `MetricDefinition`은 `in_bulk`.

#### [HIGH-4] `serverless/views.py:2258-2259` — `admin_etf_status`
```python
for profile in profiles:                                                    # 21~30개
    holdings_count = ETFHolding.objects.filter(etf=profile).count()         # 매번 1쿼리
```
- 권장 수정 (난이도: **쉬움**):
  - `ETFProfile.objects.annotate(holdings_count=Count('etfholding'))`로 단일 쿼리 변경 (related_name 확인 필요).

#### [HIGH-5] `serverless/views_admin.py:478-499` — `AdminNewsCategoryView.get`
```python
categories = NewsCollectionCategory.objects.all()
for cat in categories:
    symbols = cat.resolve_symbols()  # → SP500Constituent.objects.filter(...).values_list(...)
```
- `news/models.py:638` `resolve_symbols()`는 `sector`/`sub_sector` 카테고리마다 SP500Constituent 쿼리를 1회 발생.
- 카테고리 N개 → **N+1**.
- 권장 수정 (난이도: **중간**):
  - 카테고리 그룹별로 sector/sub_sector 값 set을 모아 `SP500Constituent.objects.filter(sector__in=...)` 한 번에 받아 dict 매핑.

#### [HIGH-6] `stocks/serializers.py:381-409` — `WatchListStockSerializer`
```python
def get_latest_price(self, obj):
    latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()  # N
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]  # N
```
- Watchlist 종목 N개 → **2N 쿼리**.
- 권장 수정 (난이도: **중간**):
  - 뷰에서 `Prefetch('stock__dailyprice_set', queryset=DailyPrice.objects.order_by('-date'))` 사용 후 시리얼라이저는 `obj.dailyprice_set.all()[:7]` 활용
  - 또는 `obj.real_time_price`만 표시하도록 단순화 (이미 Stock 모델에 캐싱되어 있음).

#### [MED-1] `users/views.py:872-910` — `WatchlistBulkAddView.post`
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol.upper())                                  # N
    if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists(): ...   # N
    item = WatchlistItem.objects.create(...)                                          # N
```
- 권장 수정 (난이도: **중간**): `Stock.objects.in_bulk(symbols, field_name='symbol')` + 기존 `WatchlistItem`을 `stock_id__in=...`로 한 번에 조회 + `bulk_create`.

#### [MED-2] `users/views.py:937-944` — `WatchlistBulkRemoveView.post`
```python
for symbol in symbols:
    item = WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())  # N
    item.delete()                                                                        # N
```
- 권장 수정 (난이도: **쉬움**): `WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=...).delete()` 단일 호출.

#### [MED-3] `news/api/views.py:331-336` — `trending_stocks`
```python
for item in trending_data:                          # limit ≤ 20
    recent_articles = NewsArticle.objects.filter(
        entities__symbol=symbol,
        published_at__gte=from_date
    ).distinct().order_by('-published_at')[:3]
```
- 5분 캐시가 있어 큰 위험은 아니나 캐시 미스 시 20+ 쿼리.
- 권장 수정 (난이도: **중간**): `NewsArticle.objects.filter(entities__symbol__in=symbols, ...).order_by('-published_at')` 한 번 + 파이썬에서 그룹핑 (`itertools.groupby` 또는 `defaultdict`).

#### [MED-4] `stocks/views_indicators.py:324-360` — `compare_indicators` (POST)
```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol)                              # N
    prices = DailyPrice.objects.filter(stock=stock).order_by('-date')[:50]  # N
```
- 권장 수정 (난이도: **중간**): 종목 일괄 조회 + `DailyPrice.objects.filter(stock_id__in=...)` 후 dict 그룹화.

#### [MED-5] `stocks/serializers.py:205-310` — `OverviewTabSerializer.get_dynamic_layers`
- OneToOne 6개(`overview_ko`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + ForeignKey 역참조 1개(`category_signals`).
- `stocks/views.py:492`은 `select_related('overview_ko')`만 적용 → 나머지 5개는 추가 쿼리.
- 단일 객체 응답 + `cache_key=stock_overview_{symbol}` 캐싱이 있어 캐시 미스 시 약 7쿼리.
- 권장 수정 (난이도: **쉬움**): `select_related`를 OneToOne 5개 추가, `prefetch_related('category_signals')` 적용. (코드 주석에 이미 TODO로 명시됨)

---

### 2. 인덱스 누락

#### [MED-6] `rag_analysis/models.py:165-168` — `AnalysisSession`
```python
class Meta:
    ordering = ["-updated_at"]
    # indexes 없음
```
- 사용처: `rag_analysis/views.py:433` `AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')` (정렬은 모델 ordering 의존).
- 권장 수정 (난이도: **쉬움**):
  ```python
  indexes = [models.Index(fields=['user', '-updated_at'])]
  ```

#### [LOW-1] `rag_analysis/models.py:106-111` — `BasketItem`
- `unique_together = ["basket", "item_type", "reference_id"]`로 인덱스가 만들어지지만 `basket` 단독 정렬(`ordering=["created_at"]`)에 대한 인덱스 없음. 단일 basket의 아이템 수가 ≤15로 제한되므로 영향 적음.
- 권장 수정 (난이도: **쉬움**, 우선순위 낮음): 필요 시 `Index(fields=['basket', 'created_at'])` 추가.

#### [LOW-2] `users/models.py:249-265` — `UserInterest`
- `unique_together = ('user', 'interest_type', 'value')`만 정의. 사용처에서는 `user` 단독 카운트(`UserInterest.objects.filter(user=request.user).count()` `users/views.py:1031`)가 자주 호출.
- unique_together가 (user, ...) 시작이라 prefix 인덱스로 user 필터는 사용 가능 → 실제 누락 아님. 정보 차원 표기.

#### [추가 검토] 아래 모델들은 적절히 인덱스됨 (참고):
- `stocks/models.py` Stock (sector, industry, market_capitalization, last_updated, real_time_price 인덱스), DailyPrice/WeeklyPrice (`stock+date`, `date+volume`), BalanceSheet/IncomeStatement/CashFlowStatement (BasicFinancialStatement 추상에서 `stock+period_type+fiscal_year`).
- `news/models.py` NewsArticle (`-published_at + category`, `source + -published_at`, `sentiment_score + -published_at`, `importance_score + -published_at`, `llm_analyzed + -published_at`).
- `serverless/models.py`는 거의 모든 핵심 필드(symbol, date, sector, theme_id, source_symbol, target_symbol, institution_cik, action 등) `db_index=True`.
- `sec_pipeline/models.py` 8개 모델 모두 `Meta.indexes` 정의.
- `graph_analysis/models.py`는 사용 대상이 아니지만 인덱스 양호 (`db_index=True` 다수).

---

### 3. 느린 Serializer (SerializerMethodField 추가 쿼리)

#### [HIGH-7] `serverless/serializers.py:240-292` — `ScreenerPresetSerializer`
```python
def get_owner_email(self, obj):
    if obj.user:
        email = obj.user.email   # ← user select_related 없으면 N+1
def get_is_owner(self, obj):
    return obj.user == request.user  # user 비교 (PK만 비교는 OK이지만 user 미로드 시 LAZY)
```
- 사용처: `serverless/views.py:1017-1034` `ScreenerPreset.objects.all()` + `user_presets = ScreenerPreset.objects.filter(user=request.user)`. **`select_related('user')` 누락**.
- 시스템 프리셋(user=null) 비율이 높으면 영향 작지만 사용자 프리셋이 늘면 N+1.
- 권장 수정 (난이도: **쉬움**): 뷰에서 `ScreenerPreset.objects.all().select_related('user')`. ListSerializer는 `is_system`만 사용하므로 `select_related` 영향 없음.

#### [HIGH-8] `stocks/serializers.py:381-409` — `WatchListStockSerializer`
- (HIGH-6과 동일, 위 N+1 섹션 참조)

#### [MED-7] `stocks/serializers.py:114-310` — `OverviewTabSerializer`
- (MED-5와 동일, 위 N+1 섹션 참조)

#### [참고] 이슈 없음으로 분류:
- `stocks/serializers_screener.py` `EnhancedScreenerStockSerializer`: dict 입력(FMP API 응답) 처리, DB 액세스 없음.
- `stocks/serializers_market_movers.py`, `stocks/serializers_exchange.py`: 단순 포맷팅.
- `stocks/serializers_fundamentals.py:109-110` `discount_percentage`/`recommendation`: 모델 필드만 접근.
- `users/serializers.py:95` `portfolio_weight`: context에서 값 참조, DB 액세스 없음.
- `rag_analysis/serializers.py:29,34` `can_add_item`/`max_units`: 메서드 호출이지만 `prefetch_related('items')`가 뷰에서 적용 (`rag_analysis/views.py:73`).

---

### 4. 페이지네이션 누락

`config/settings.py:341` `REST_FRAMEWORK` 딕셔너리에 **`DEFAULT_PAGINATION_CLASS`와 `PAGE_SIZE`가 정의되어 있지 않음**. 따라서 아래 list 엔드포인트는 모두 무제한 반환 (수동 슬라이스가 있는 경우만 안전).

#### [HIGH-9] `stocks/views.py:75-105` — `StockListAPIView (generics.ListAPIView)`
- `pagination_class` 없음. 슬라이스 없음. Stock 테이블 수천~수만 행 반환 가능.
- 권장 수정 (난이도: **쉬움**): 글로벌 `DEFAULT_PAGINATION_CLASS = 'rest_framework.pagination.PageNumberPagination'` + `PAGE_SIZE = 50` 설정 또는 클래스에 `pagination_class` 명시.

#### [HIGH-10] `news/api/views.py:42-45` — `NewsViewSet (ReadOnlyModelViewSet)`
```python
queryset = NewsArticle.objects.all().prefetch_related('entities')
```
- list action 페이지네이션 없음.
- 권장 수정 (난이도: **쉬움**): `pagination_class = PageNumberPagination` 또는 글로벌 설정.

#### [HIGH-11] `news/api/views.py:89-99` — `stock_news` action
```python
articles = NewsArticle.objects.filter(...).distinct().order_by('-published_at')
serializer = self.get_serializer(articles, many=True)
'count': articles.count(),  # 별도 쿼리 1회 추가
```
- 슬라이스/페이지네이션 없음. `articles.count()`가 별도 쿼리.
- 권장 수정 (난이도: **중간**): DRF Paginator(`self.paginate_queryset(...)`) 또는 명시적 `[:limit]` 슬라이스.

#### [HIGH-12] `serverless/views.py:1017-1034` — 스크리너 프리셋 list
```python
queryset = ScreenerPreset.objects.all()
if category: ...
if request.user.is_authenticated:
    queryset = queryset | user_presets
queryset = queryset.distinct().order_by(...)
```
- 페이지네이션/슬라이스 없음. 사용자 증가 시 폭증 가능.
- 권장 수정 (난이도: **쉬움**): DRF Paginator 적용 또는 카테고리별 limit.

#### [MED-8] `chainsight/api/views.py` 다수 엔드포인트, `validation/api/views.py:421-453` `PresetListView` 등
- 도메인 특성상 결과 수가 작게 제한됨 (preset ≤ 6, peer ≤ 10). 즉시 위험은 낮으나 정책상 일관성을 위해 글로벌 페이지네이션 추가 권장.

#### [LOW-3] `serverless/views.py:2248-2302` `admin_etf_status`
- `ETFProfile.objects.all()` (≤ 30개). 관리자 전용이라 우선순위 낮음.

---

## 권장 우선 조치 (Quick Wins)

1. **글로벌 페이지네이션 활성화** — `config/settings.py:341` `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE` 추가 → HIGH-9, HIGH-10, HIGH-12 동시 해결. (난이도: **쉬움**, 영향: 큼)
2. **`select_related('user')`** — `serverless/views.py:1017,1031` ScreenerPreset 쿼리 → HIGH-7 해결. (난이도: **쉬움**)
3. **`annotate(Count)`** — `serverless/views.py:2248` ETFProfile → HIGH-4 해결. (난이도: **쉬움**)
4. **WatchlistBulkRemove 단일 쿼리화** — `users/views.py:937` → MED-2 해결. (난이도: **쉬움**)
5. **`MetricDefinition.in_bulk` 캐싱** — `validation/api/views.py` 3개 뷰 → HIGH-1, HIGH-2, HIGH-3 부분 해결. (난이도: **중간**)

## 중장기 리팩토링

- `validation/api/views.py` ValidationMetricsView/`_build_metric`: 사전 일괄 조회 + 메모리 dict 매핑 패턴 도입 (300+ 쿼리 → 5~10 쿼리).
- `stocks/serializers.py` `OverviewTabSerializer.get_dynamic_layers`: TODO 주석에 따라 `select_related`/`prefetch_related` 적용 + Stock detail에 캐시 invalidation 정책 명문화.
- `news/api/views.py` `stock_news`: 페이지네이션 + 사전 collected article 캐싱 (cache_key 이미 사용 중이므로 paginated payload 캐시).

---

## 부록 — 검사 범위 (확인 완료)

- **뷰 (17/17)**: stocks/views.py, stocks/views_search.py, stocks/views_exchange.py, stocks/views_eod.py, stocks/views_screener.py, stocks/views_market_movers.py, stocks/views_fundamentals.py, stocks/views_indicators.py, stocks/views_mvp.py, users/views.py, news/api/views.py, macro/views.py, rag_analysis/views.py, serverless/views_admin.py, validation/api/views.py, chainsight/api/views.py, sec_pipeline/views.py
- **모델 (7/7)**: stocks/models.py, users/models.py, news/models.py, serverless/models.py, rag_analysis/models.py, sec_pipeline/models.py, graph_analysis/models.py
- **시리얼라이저 (10/10)**: stocks/serializers.py, stocks/serializers_screener.py, stocks/serializers_exchange.py, stocks/serializers_fundamentals.py, stocks/serializers_market_movers.py, users/serializers.py, news/api/serializers.py, macro/serializers.py, rag_analysis/serializers.py, serverless/serializers.py
- **글로벌 설정**: config/settings.py:340-349 (`REST_FRAMEWORK`)
- **검사 방법**: 정적 패턴 매칭 (Grep) + 후보 라인 직접 정독 (Read). 실행/프로파일링 없음.
- **검사 미수행**: serverless/views.py 전체(2900+ 라인), news/api/views.py 일부(2183라인 중 핵심 영역만), portfolio/, thesis/, metrics/, validation/views.py(엔드포인트 미사용 추정).
