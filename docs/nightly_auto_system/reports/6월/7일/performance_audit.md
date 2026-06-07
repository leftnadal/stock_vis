# API 성능 감사 보고서

- **작성일**: 2026-06-07
- **유형**: 읽기 전용 정적 분석 (코드 미수정)
- **범위**: 뷰 17개(모노레포 경로 매핑 반영) + 모델 7개
- **방법**: 4개 병렬 에이전트 정적 분석 + 핵심 HIGH 이슈 직접 스팟 체크(5건)
- **경로 변경 주의**: 지시서 경로는 구 구조 기준. 실제는 모노레포로 이전됨
  - `stocks/*` → `packages/shared/stocks/*`
  - `users/*` → `packages/shared/users/*`
  - `macro/*` → `apps/market_pulse/*`
  - `news/api/*` → `services/news/api/*`
  - `chainsight/*` → `apps/chain_sight/*`
  - `rag_analysis/`, `serverless/`, `validation/`, `sec_pipeline/` → `services/*`

---

## 요약 (심각도별 이슈 수)

| 심각도 | 건수 | 핵심 내용 |
|--------|------|----------|
| **HIGH** | 5 | 루프 내 쿼리 N+1 (요청당 쿼리 수가 데이터 크기에 비례하여 폭증) |
| **MED** | 11 | 고정 추가 쿼리 수개·페이지네이션 누락·메모리 필터링 |
| **LOW** | 6 | `in` 연산자 M2M 전체 로드·소규모 테이블 인덱스·수동 직렬화 |

### 검증으로 정정된 항목 (보고에서 제외/하향)
- ❌ `users/views.py:419` PortfolioDetailTableView `total_value` 루프 → **N+1 아님**. property가 `self.stock.real_time_price`만 접근하고 queryset에 `select_related("stock")` 존재. 페이지네이션 누락(MED)만 유효.
- ❌ `NewsEntity`에 `-news__published_at` 복합 인덱스 권장 → **Django에서 생성 불가** (역참조/조인 필드는 인덱스 컬럼 대상이 아님). `NewsArticle.published_at`은 이미 `db_index=True`.

### 인덱스 총평
모델 인덱스 커버리지는 **전반적으로 양호**. 자주 필터/정렬되는 필드 대부분이 `db_index=True` / `Meta.indexes` / `unique_together`로 이미 커버됨. 실질 누락은 LOW 2건뿐.

---

## 상세 (심각도 순)

### 🔴 HIGH — 루프 내 쿼리 N+1

#### H-1. `services/validation/api/views.py:261-265, 339-353` — 중첩 N+1 (가장 심각) ✅직접확인
**난이도: 중간**

`_build_category` → `_build_metric`이 메트릭 코드 루프 안에서 호출되며, 각 호출이 또 내부 루프 쿼리를 돈다. 이중 중첩 N+1.

```python
# views.py:261 _build_category — 카테고리당 metric_codes 개수만큼 반복
for mc in metric_codes:
    md = MetricDefinition.objects.filter(pk=mc).first()   # ← 메트릭당 1쿼리
    if not md: continue
    metrics_data.append(self._build_metric(stock, md))

# views.py:339 _build_metric 내부 — history 5건마다 또 쿼리
snaps = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by("fiscal_year")[:5]
for s in snaps:
    peer_bench = PeerMetricBenchmark.objects.filter(           # ← snapshot당 1쿼리
        symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
    ).first()
```

**쿼리 폭증 추정**: 카테고리당 메트릭 10~20개 × (MetricDefinition 1 + snapshot 1~2 + benchmark 1 + history 1 + peer_bench ×5). 8개 카테고리 전체 조회 시 **수백 쿼리**.

**권장 수정**:
1. `MetricDefinition.objects.filter(pk__in=metric_codes)`로 일괄 로드 후 dict 매핑 (루프 밖)
2. `PeerMetricBenchmark`를 `fiscal_year__in=[s.fiscal_year for s in snaps]`로 일괄 로드 후 `(fiscal_year, metric_code)` dict 매핑
3. (선택) `MetricDefinition`은 거의 정적 → 모듈 캐시

---

#### H-2. `packages/shared/stocks/views_indicators.py:371-387` — IndicatorComparisonView 루프 N+1
**난이도: 쉬움**

```python
for symbol in symbols:
    symbol = symbol.upper()
    stock = Stock.objects.get(symbol=symbol)              # ← 심볼당 1쿼리
    prices = DailyPrice.objects.filter(stock=stock)       # ← 심볼당 1쿼리
        .order_by("-date")[:50].values_list("close_price", flat=True)
```

심볼 N개 → `2N` 쿼리. (예: 5개 비교 → 10쿼리)

**권장 수정**:
```python
symbols_upper = [s.upper() for s in symbols]
stocks = Stock.objects.filter(symbol__in=symbols_upper)          # 1쿼리
prices = (DailyPrice.objects.filter(stock__in=stocks)
          .order_by("stock_id", "-date")
          .values("stock_id", "close_price"))                    # 1쿼리 후 메모리 그룹핑
```

---

#### H-3. `packages/shared/users/views.py:939-948` — WatchlistItemAddView(벌크) 루프 N+1
**난이도: 중간**

```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol.upper())                       # ← N쿼리
    if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():  # ← N쿼리
        ...
```

심볼 N개 → 최소 `2N` 쿼리 + 생성. 벌크 추가 시 폭증.

**권장 수정**: `Stock.objects.filter(symbol__in=...)` dict 매핑 + 기존 항목 `stock__symbol__in` set 조회로 1+1 쿼리, 신규는 `bulk_create`.

---

#### H-4. `packages/shared/users/views.py:1010-1014` — WatchlistBulkRemoveView 루프 N+1
**난이도: 중간**

```python
for symbol in symbols:
    item = WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())  # ← N쿼리
    item.delete()                                                                        # ← N쿼리(개별 delete)
```

**권장 수정**:
```python
items = WatchlistItem.objects.filter(watchlist=watchlist, stock__symbol__in=symbols_upper)
removed = set(items.values_list("stock__symbol", flat=True))   # 1쿼리
items.delete()                                                  # 1쿼리(벌크)
```

---

#### H-5. `services/news/api/views.py:369-391` — trending() 루프 N+1 ✅직접확인
**난이도: 중간** · *완화 요인: 5분 캐시(`cache.set(..., 300)`) 존재*

```python
for item in trending_data:                  # limit 기본 10
    recent_articles = (NewsArticle.objects
        .filter(entities__symbol=symbol, published_at__gte=from_date)  # ← 종목당 1쿼리
        .distinct().order_by("-published_at")[:3])
```

종목 10개 → 집계 1 + 루프 10 = 11쿼리, 각 쿼리가 `entities` 조인 + `distinct`(중복제거 비용).

**권장 수정**: 종목 전체를 `entities__symbol__in=symbols`로 한 번에 가져온 뒤 메모리에서 종목별 상위 3개 분배, 또는 종목별 `news_id` Subquery 사용. (캐시가 빈도를 낮추므로 우선순위는 H-1~H-4 다음)

---

### 🟡 MED

#### M-1. `packages/shared/stocks/views.py` OverviewTabSerializer.get_dynamic_layers() — prefetch 누락
**난이도: 중간**

OverviewTab 직렬화 시 `category_signals`(역참조), `validation_news_summary`·`sensitivity_profile`·`growth_stage`·`capital_dna`·`narrative_tag`(OneToOne) 등 6개 관계를 각각 접근. 단일 Stock이므로 N+1은 아니지만 **요청당 고정 +6 쿼리**.
**권장**: 뷰의 Stock 조회에 `prefetch_related(...)` / `select_related(...)` 추가.

#### M-2. `packages/shared/stocks/views.py:928-950` StockCompleteDataAPIView — 4개 분리 쿼리
**난이도: 중간** · 단일 stock 대상이라 N+1은 아님. DailyPrice/BalanceSheet/IncomeStatement/CashFlow 각 1쿼리 = +4.
**권장**: `Prefetch`로 묶거나 응답 캐싱(심볼별).

#### M-3. `services/validation/api/views.py:279-302` — CompanyMetricSnapshot 이중 쿼리 ✅직접확인
**난이도: 쉬움** · `value_status="normal"` 미존재 시 동일 조건 재쿼리. 메트릭 다수에서 누적.
**권장**: `.order_by("-value_status", "-fiscal_year").first()` 단일 쿼리로 통합(또는 정렬 키 보정).

#### M-4. `packages/shared/users/views.py:269-273` PortfolioListCreateView — 페이지네이션 누락
**난이도: 중간** · `select_related("stock")`은 있으나 전체 직렬화. 항목 多 사용자에서 응답 비대.
**권장**: `pagination_class` 지정.

#### M-5. `packages/shared/users/views.py:414-435` PortfolioDetailTableView — 페이지네이션 누락
**난이도: 중간** · (※ property N+1 주장은 정정됨, 페이지네이션만 유효)

#### M-6. `services/news/api/views.py:117-123` stock_news() — 역참조 조인 + distinct
**난이도: 중간** · `entities__symbol` 조인 후 `.distinct()`로 전행 중복제거 부하.
**권장**: `NewsEntity`에서 `news_id` Subquery로 좁힌 뒤 `NewsArticle.filter(id__in=...)`.

#### M-7. `services/news/api/views.py:186-213` stock_sentiment() — 메모리 필터 + 루프 내 FK 접근
**난이도: 중간** · Python 리스트 컴프리헨션으로 집계 + `e.news.published_at` 접근(N+1 소지).
**권장**: `aggregate(Avg/Count + Case/When)` DB 집계로 전환, 또는 `select_related("news")`.

#### M-8. `services/news/api/views.py:~1479` collection_logs() — provider 루프 내 count 쿼리
**난이도: 중간** · provider별 `qs.filter(provider=..., errors__gt=0).count()` 반복.
**권장**: `.filter(errors__gt=0).values("provider").annotate(Count("id"))` 1쿼리 후 dict 매핑.

#### M-9. `services/news/api/views.py:1616-1860` pipeline_health() — phase별 반복 쿼리
**난이도: 높음** · *관리자 전용/저빈도*. 6개 phase가 유사 쿼리를 중복 실행.
**권장**: 26h 윈도 로그 1회 로드 후 phase별 메모리 분류. 빈도 낮아 우선순위 낮음.

#### M-10. `services/serverless/views_admin.py:505-530` NewsCategory resolve_symbols() 루프
**난이도: 높음** · ⚠️*미검증*: `resolve_symbols()` 내부가 DB를 치는지 확인 못 함. 카테고리마다 호출되므로 내부가 쿼리면 N+1.
**권장**: `resolve_symbols()` 구현 확인 → DB 접근 시 사전 일괄 로드로 리팩터.

#### M-11. `services/rag_analysis/` DataBasketSerializer.get_can_add_item() + 페이지네이션
**난이도: 쉬움** · `can_add_item()`이 `.count()` 계열이면 basket마다 +1쿼리. 리스트 뷰(`views.py:50-54`, `428-433`) 페이지네이션 없음과 결합 시 누적.
**권장**: 뷰 queryset에 `annotate(item_count=Count("items"))` 후 serializer는 annotate 값 사용 + `pagination_class` 지정.

---

### 🟢 LOW

| ID | 위치 | 내용 | 난이도 |
|----|------|------|--------|
| L-1 | `users/views.py:217` AddFavorite | `if stock in user.favorite_stock.all()` — M2M 전체 로드. `.filter(id=...).exists()` 권장 | 쉬움 |
| L-2 | `users/views.py:248` RemoveFavorite | 동일 패턴(`not in`) | 쉬움 |
| L-3 | `users/views.py:1049-1060` UserInterestListCreate | serializer 없이 수동 dict 직렬화(쿼리 영향 없음, 유지보수성) | 쉬움 |
| L-4 | `serverless/views_admin.py:569-692` | 카테고리 검증 시 `SP500Constituent...exists()` 2회. 유효 sector set 캐싱 권장 | 쉬움 |
| L-5 | `rag_analysis/models.py:180` AnalysisMessage.role | `(session, created_at)` 인덱스 부재. ⚠️실사용 미확인 → 추정 | 쉬움 |
| L-6 | `serverless/models.py:495` ScreenerFilter.is_active | 인덱스 없음. 단 소규모 메타 테이블(<200행)로 영향 미미 | 쉬움 |

---

## 파일별 결과 매트릭스

| 파일 | HIGH | MED | LOW | 비고 |
|------|:---:|:---:|:---:|------|
| stocks/views.py | - | 2 | - | M-1 serializer, M-2 4쿼리 |
| stocks/views_indicators.py | 1 | - | - | H-2 |
| stocks/views_search.py | - | - | - | 이슈 없음 |
| stocks/views_exchange.py | - | - | - | 고정 데이터, 이슈 없음 |
| stocks/views_eod.py | - | - | - | `select_related("stock")` 적용됨 |
| stocks/views_screener.py | - | - | - | FMP API 응답(ORM 아님), 페이지네이션 한계는 limit으로 제어 |
| stocks/views_market_movers.py | - | - | - | limit 제어, 이슈 없음 |
| stocks/views_fundamentals.py | - | - | - | FMP API, limit 제어 |
| stocks/views_mvp.py | - | - | - | 단일 객체 접근, 이슈 없음 |
| users/views.py | 2 | 2 | 3 | H-3, H-4 / M-4, M-5 / L-1~3 |
| news/api/views.py | 1 | 4 | - | H-5 / M-6~9 |
| market_pulse(macro)/views.py | - | - | - | 서비스 계층 추상화, 이슈 없음 |
| rag_analysis/views.py | - | 1 | 1 | M-11 / L-5(모델) |
| serverless/views_admin.py | - | 1 | 1 | M-10(미검증) / L-4 |
| validation/api/views.py | 1 | 1 | - | H-1(+339), M-3 |
| chain_sight/api/views.py | - | - | - | bulk 로드 패턴 적용됨, 이슈 없음 |
| sec_pipeline/views.py | - | - | - | 뷰 2개, 이슈 없음 |
| serverless/models.py | - | - | 1 | L-6 |

---

## 권장 수정 우선순위

1. **H-1** validation 중첩 N+1 — 수백 쿼리 → 일괄 로드로 ~10쿼리. 효과 대비 난이도 최적.
2. **H-3 / H-4** Watchlist 벌크 루프 — `__in` + `bulk_create`/`bulk delete`로 단순 치환.
3. **H-2** IndicatorComparison — `__in` 치환(쉬움).
4. **M-1** OverviewTab `prefetch_related` — 핫패스(종목 상세) 고정 +6쿼리 제거.
5. **H-5** trending — 캐시로 완화되나 cold hit 부하 큼.
6. 나머지 MED/LOW는 트래픽·핫패스 여부로 취사.

---

## 한계 및 주의

- 본 보고서는 **정적 분석** 결과로, 실제 쿼리 수는 `django-debug-toolbar` / `CaptureQueriesContext` 로 런타임 검증 권장.
- HIGH 5건 중 **H-1·H-5는 코드 직접 확인 완료**, H-2·H-3·H-4는 에이전트 분석 기반(패턴 명확).
- M-10(serverless `resolve_symbols`)은 메서드 내부 미확인 → 실제 영향 별도 검증 필요.
- 인덱스 L-5는 실제 필터 사용처 미확정 → 추정 항목.
