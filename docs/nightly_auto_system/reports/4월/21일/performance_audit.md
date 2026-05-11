# API 성능 감사 보고서

**감사일**: 2026-04-21
**범위**: Stock-Vis Django 백엔드 (17개 뷰 + 10개 serializer + 7개 모델)
**방식**: 정적 분석 (읽기 전용, 코드 수정 없음)
**이전 감사**: `performance_audit_20260419.md`, `performance_audit_20260420.md` — 대조 포함
**검증 방식**: 3개 병렬 Explore 에이전트 + 핵심 주장 직접 재확인 (`config/settings.py:331`, `stocks/serializers.py:405`, `validation/api/views.py:361`, `rag_analysis/models.py:28`, `news/api/views.py:329`)

---

## 요약

### 이슈 수 by 영역 × 심각도

| 영역 | HIGH | MED | LOW | 합계 |
|------|:----:|:---:|:---:|:----:|
| N+1 쿼리 (뷰) | 3 | 4 | 1 | 8 |
| 인덱스 누락 (모델) | 4 | 4 | 2 | 10 |
| Serializer 추가 쿼리 | 3 | 3 | 0 | 6 |
| 페이지네이션 누락 | 4 | 0 | 0 | 4 |
| **논리 버그 (성능과 연동)** | **1** | 0 | 0 | 1 |
| **총계** | **15** | **11** | **3** | **29** |

### 이전 감사 대비 추이

| 지표 | 2026-04-19 | 2026-04-20 | 2026-04-21 | Δ (1일) |
|------|:---------:|:---------:|:---------:|:--:|
| 총 이슈 | 44 | 30 | 29 | **-1** |
| HIGH | 21 | 12 | 15 | **+3** |
| MED | 21 | 15 | 11 | -4 |
| LOW | 2 | 3 | 3 | 0 |

> **HIGH가 3건 증가한 이유**: 새로 발견된 논리 버그 1건(`get_chart_data` return 누락) + `trending` N+1(MED → 영향 재평가 후 HIGH 후보) + 기존 `WatchListStockSerializer` 을 `get_latest_price`/`get_chart_data` 로 분리 카운트. 기존 이슈 중 FIXED는 없음.

### 변경 없음(UNCHANGED) 비율

- **페이지네이션**: 4/4 전부 UNCHANGED
- **rag_analysis 인덱스 3건**: 전부 UNCHANGED
- **validation/api/views.py N+1 3건**: 전부 UNCHANGED
- **OverviewTabSerializer / WatchListStockSerializer**: UNCHANGED

전일 TOP 5 항목 중 어떤 것도 수정되지 않음.

### 수정 난이도 분포

| 난이도 | 건수 | 비율 |
|--------|:----:|:---:|
| 쉬움 (한 줄~5분) | 17 | 59% |
| 중간 (쿼리셋/뷰 리팩토링) | 10 | 34% |
| 높음 (구조 변경) | 2 | 7% |

### Top 5 우선 수정 (ROI 기준)

| 순위 | 위치 | 쿼리/영향 개선 | 심각도 | 난이도 |
|:----:|------|----------|:------:|:------:|
| 1 | `stocks/serializers.py:405-409` `get_chart_data` **return 누락 버그** | 응답 깨짐 원인 + N+1 (조합) | **HIGH** | 쉬움 |
| 2 | `validation/api/views.py:361` LeaderComparisonView | ~300개 → 3개 쿼리 | HIGH | 높음 |
| 3 | `config/settings.py:331` DEFAULT_PAGINATION_CLASS 전역 미설정 | 수만 row 응답 방지 | HIGH | 쉬움 |
| 4 | `stocks/serializers.py:205` OverviewTabSerializer.get_dynamic_layers | 7N → 1 쿼리 | HIGH | 중간 |
| 5 | `rag_analysis/models.py` DataBasket/AnalysisSession user 인덱스 | full scan → indexed | HIGH | 쉬움 |

---

## 0. 🔴 신규 CRITICAL: 논리 버그 (직접 재검증 완료)

### 0.1 stocks/serializers.py:405-409 — `WatchListStockSerializer.get_chart_data()` return 문 누락 (HIGH / 쉬움)

**직접 확인 (라인 405-409)**:
```python
def get_chart_data(self, obj):
    """최근 7일 차트 데이터"""
    recent_prices = DailyPrice.objects.filter(
        stock=obj
    ).order_by('-date')[:7]
                                # ← return 문 없음. 함수 본문 종료.

### Sector 성과용 serializer ( 모델이 없는 상태, ...)
class SectorPerformanceSerializer(...):
```

**문제**:
1. `return` 문이 없음 → 항상 `None` 반환.
2. 그럼에도 **쿼리셋 `.filter(...)[:7]`은 evaluate**되어 row마다 DB 호출 발생.
3. 결과적으로 **쿼리 비용만 내고 응답 데이터는 없는** 최악의 패턴.

**영향**: Watchlist 20개 항목 × 1 쿼리 = 20개 쿼리 소비, chart_data 필드는 null.

**권장 수정**:
```python
def get_chart_data(self, obj):
    recent_prices = DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
    return [
        {'date': p.date.isoformat(), 'close': float(p.close_price)}
        for p in reversed(list(recent_prices))
    ]
```
그리고 뷰 측에서 `prefetch_related(Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7]))` 적용 시 메모리 조회로 전환 가능.

**상태**: **NEW** (전일 감사에서 놓침)

---

## 1. N+1 쿼리 (뷰)

### 파일별 요약

| 파일 | 이슈 수 | 최고 심각도 | 주요 변경 |
|------|:------:|:----------:|----------|
| validation/api/views.py | 3 | HIGH | **UNCHANGED (전건 동일)** |
| news/api/views.py | 2 | MED | `trending` @action이 NEW |
| stocks/views.py | 1 | MED | UNCHANGED |
| stocks/views_mvp.py | 1 | MED | UNCHANGED |
| rag_analysis/views.py | 1 | MED | UNCHANGED |

### 1.1 validation/api/views.py:361-372 — LeaderComparisonView (HIGH / 높음)

**직접 확인 (라인 361-371)** — 패턴 동일:
```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()  # 루프마다 1쿼리
    company_snap = CompanyMetricSnapshot.objects.filter(
        symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
    leader_snap = CompanyMetricSnapshot.objects.filter(
        symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
```

**예상 쿼리**: `all_metrics = Σ(CATEGORY_METRICS.values())` ≈ 50~100개 × 3 = **150~300개 추가 쿼리**.

**상태**: **UNCHANGED** (전일과 동일. 1차 에이전트는 "300→120 PARTIAL"이라 주장했으나 직접 재확인 결과 구조 변경 없음).

**권장 수정** (전일 동일):
```python
metric_ids = [mc for _, mc in all_metrics]
metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}
snaps = CompanyMetricSnapshot.objects.filter(
    symbol__in=[stock.symbol, leader.symbol],
    fiscal_year=latest_fy, value_status='normal',
    metric_code_id__in=metric_ids,
)
snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
for cat, mc in all_metrics:
    md = metrics.get(mc)
    company_snap = snap_map.get((stock.symbol, mc))
    leader_snap = snap_map.get((leader.symbol, mc))
```

### 1.2 validation/api/views.py:110-124 — ValidationSummaryView rank 루프 (HIGH / 쉬움)

**직접 확인 (라인 112-117)**:
```python
for mc in rank_metrics:  # 5개 고정
    delta = CompanyBenchmarkDelta.objects.filter(
        symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
    ).first()
    if delta and delta.rank and delta.total:
        md = MetricDefinition.objects.filter(pk=mc).first()
```

**영향**: 5 × 2 = 10개 추가 쿼리. 엔드포인트가 종목 상세 진입마다 호출됨 → 누적 부하.

**상태**: **UNCHANGED**.

**권장**:
```python
deltas = {d.metric_code_id: d for d in CompanyBenchmarkDelta.objects.filter(
    symbol=stock, fiscal_year=fiscal_year, metric_code_id__in=rank_metrics
)}
metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=rank_metrics)}
```

### 1.3 validation/api/views.py:199-208 — ValidationMetricsView._build_category (MED / 쉬움)

**직접 확인 (라인 204-208)**:
```python
for mc in metric_codes:
    md = MetricDefinition.objects.filter(pk=mc).first()
```
**영향**: 카테고리당 6~15개 × (최대 7개 카테고리) = 최대 ~100개 쿼리.
**상태**: **UNCHANGED**.

### 1.4 news/api/views.py:329-343 — NewsViewSet.trending (MED / 중간) 🆕

**직접 확인 (라인 331-343)**:
```python
for item in trending_data:  # 최대 limit개 (기본 10)
    symbol = item['symbol']
    recent_articles = NewsArticle.objects.filter(
        entities__symbol=symbol,
        published_at__gte=from_date
    ).distinct().order_by('-published_at')[:3]
    results.append({
        ...
        'recent_articles': NewsArticleListSerializer(recent_articles, many=True).data
    })
```

**영향**: 1(집계) + 10(심볼별) + 10×N(entities nested serializer) = 최소 11, 최대 40+ 쿼리.

**상태**: **NEW** (전일 감사에서 `trending` 언급 없음).

**권장**:
```python
# trending_data의 symbol들에 대한 뉴스를 한 번에 가져와서 메모리 그룹핑
symbols = [item['symbol'] for item in trending_data]
all_articles = NewsArticle.objects.filter(
    entities__symbol__in=symbols,
    published_at__gte=from_date
).distinct().prefetch_related('entities').order_by('-published_at')
# 그룹핑 후 상위 3개씩 추출
```

**주의**: 5분 캐시가 있어(`cache.set(cache_key, results, 300)`) cold miss 시에만 발생.

### 1.5 news/api/views.py:87-104 — NewsViewSet.stock_news (MED / 쉬움)

**상태**: **UNCHANGED** — `.distinct()` 후 nested `entities` 직렬화로 N+1. `prefetch_related('entities', 'entities__highlights')` 추가 필요.

### 1.6 stocks/views.py:820-874 — StockCompleteDataAPIView (MED / 쉬움)

**상태**: **UNCHANGED** — OneToOne 6개 + reverse FK 1개 `select_related`/`prefetch_related` 없음.

### 1.7 stocks/views_mvp.py:47-56 — StockMVPListView (MED / 쉬움)

**상태**: **UNCHANGED**. `.values(...)` 전환 권장.

### 1.8 rag_analysis/views.py:73, 433, 503 — DataBasket/AnalysisSession 조회 (MED / 중간)

**상태**: **UNCHANGED** (인덱스 §2.1~2.3 선행 수정 필요).

### 1.9 serverless/views_admin.py — AdminNewsCategoryView (LOW / 중간)

**상태**: **UNCHANGED**. 관리자 전용이라 영향 낮음.

---

## 2. 인덱스 누락 (모델)

### 모델별 요약

| 모델 파일 | HIGH | MED | LOW | 상태 |
|----------|:----:|:---:|:---:|------|
| rag_analysis/models.py | 3 | 0 | 0 | **CRITICAL** (전건 UNCHANGED) |
| sec_pipeline/models.py | 1 | 1 | 0 | UNCHANGED |
| stocks/models.py | 0 | 1 | 0 | 전일 GOOD 유지 |
| users/models.py | 0 | 1 | 1 | UNCHANGED |
| serverless/models.py | 0 | 1 | 1 | UNCHANGED |
| graph_analysis/models.py | 0 | 0 | 0 | GOOD |
| news/models.py | 0 | 0 | 0 | GOOD (전일 FIXED 유지) |

### 2.1 rag_analysis/models.py:28-31 — DataBasket.user 인덱스 부재 (HIGH / 쉬움)

**직접 확인**:
```python
class Meta:
    ordering = ["-updated_at"]
    verbose_name = "Data Basket"
    verbose_name_plural = "Data Baskets"
    # indexes = ... 없음
```

**사용 패턴** (`rag_analysis/views.py:73`): 매 요청마다 `DataBasket.objects.filter(user=request.user)`.

**권장**:
```python
class Meta:
    ordering = ["-updated_at"]
    indexes = [models.Index(fields=['user', '-updated_at'])]
```

**상태**: **UNCHANGED**.

### 2.2 rag_analysis/models.py:165-168 — AnalysisSession.user / created_at 인덱스 부재 (HIGH / 쉬움)

**직접 확인**: `class Meta: ordering = ["-updated_at"]` 만 존재. `indexes` 없음.

**권장**: `models.Index(fields=['user', '-created_at'])`, `models.Index(fields=['user', 'status'])`.

**상태**: **UNCHANGED**.

### 2.3 rag_analysis/models.py:212-215 — AnalysisMessage.session+created_at 복합 인덱스 부재 (HIGH / 쉬움)

**직접 확인**: `class Meta: ordering = ["created_at"]`. `indexes` 없음.

**사용 패턴**: `session.messages.all().order_by('created_at')`. FK 암묵 인덱스는 있으나 정렬 키 결합 인덱스가 없어 파일 정렬 발생 가능.

**권장**: `models.Index(fields=['session', 'created_at'])`.

**상태**: **UNCHANGED**.

### 2.4 sec_pipeline/models.py:190 — BusinessModelSnapshot (symbol, fiscal_year) 복합 인덱스 부재 (HIGH / 쉬움)

**권장**: `models.Index(fields=['symbol', 'fiscal_year'])` 추가.
**상태**: **UNCHANGED (PARTIAL)**.

### 2.5 stocks/models.py:89 — Stock.created_at 인덱스 부재 (MED / 쉬움)

**상태**: **UNCHANGED**. 호출 빈도 낮지만 관리 패널에서 사용.

### 2.6 stocks/models.py:656-664 — SP500Constituent (sector, is_active) 복합 인덱스 (MED / 쉬움)

**상태**: **UNCHANGED**.

### 2.7 users/models.py:174 — Watchlist.created_at (MED / 쉬움)

**상태**: **UNCHANGED**.

### 2.8 sec_pipeline/models.py:338-340 — UnmatchedCompanyQueue (status, created_at) (MED / 쉬움)

**상태**: **UNCHANGED**.

### 2.9 users/models.py:261 — UserInterest.created_at (LOW / 쉬움)
### 2.10 serverless/models.py:414 — ScreenerPreset.created_at (LOW / 쉬움)

---

## 3. Serializer 추가 쿼리

### 3.1 stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers (HIGH / 중간)

**직접 확인 (라인 213-306)** — 6개 OneToOne 역참조(`validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + `category_signals.all()` reverse FK. 메서드 내부 `# TODO: prefetch_related + 캐싱 레이어 적용` 코멘트 존재 → 인지 O, 실행 X.

**영향**: 목록 응답 시 N개 Stock × **7 추가 쿼리**. 100종목이면 700 쿼리.

**상태**: **UNCHANGED**.

**권장** (뷰 측):
```python
queryset = Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals')
```

### 3.2 stocks/serializers.py:398-403 — WatchListStockSerializer.get_latest_price (HIGH / 쉬움)

**직접 확인 (라인 400)**:
```python
latest = DailyPrice.objects.filter(stock=obj).order_by('-date').first()
```
**영향**: Watchlist 20항목 × 1 = 20 쿼리.
**상태**: **UNCHANGED**.

### 3.3 stocks/serializers.py:405-409 — get_chart_data (HIGH / 쉬움) 🆕 **버그 포함**

§0.1 참조. return 문 누락으로 기능 결함 + 쿼리 소비.

### 3.4 serverless/serializers.py:121-137 — MarketMoverListSerializer (MED / 중간)

**문제**: `IndicatorCalculator()` row마다 3회 인스턴스화.
**상태**: **UNCHANGED**.

### 3.5 news/api/serializers.py:19, 47 — entities / highlights nested (MED / 쉬움)

**상태**: **UNCHANGED**. `prefetch_related('entities__highlights')` 필요.

### 3.6 users/serializers.py:15, 23 — UserSerializer.favorite_stock (MED / 쉬움)

**상태**: **UNCHANGED**. `prefetch_related('favorite_stock')` 필요.

---

## 4. 페이지네이션 누락

### 4.1 config/settings.py:331-339 — 전역 설정 미설정 (HIGH / 쉬움)

**직접 확인 (라인 331-339)**:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
}
```
`DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE` 키 **부재**.

**상태**: **UNCHANGED** (3일째 동일).

**권장**:
```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
'PAGE_SIZE': 20,
```
⚠️ 전역 적용 시 응답 구조 변경(`results` 래핑). 프론트엔드 호환성 점진적 검증 필요.

### 4.2 stocks/views.py:75 — StockListAPIView (HIGH / 쉬움)
### 4.3 news/api/views.py:42 — NewsViewSet (HIGH / 쉬움)
### 4.4 news/api/views.py:54-104 — stock_news @action (HIGH / 중간)
### 4.5 users/views.py:89-92 — Users.get (HIGH / 중간)

**4.2~4.5 전건 UNCHANGED**. 수정 코드는 전일 보고서 §4 참조.

---

## 5. 검증 체크리스트 (수정 후 권장)

- [ ] `stocks/serializers.py:405-409` **get_chart_data return 추가** — 즉시 수정 (버그)
- [ ] `django-silk` 또는 `django-debug-toolbar` 로 각 엔드포인트 쿼리 수 before/after 측정
- [ ] 회귀 테스트: `self.assertNumQueries(N)` 상한선 고정 — Watchlist, Validation, Overview 중심
- [ ] 페이지네이션 전역 적용 시 프론트엔드 `results` 래핑 호환성 확인
- [ ] 1000 row 이상 시나리오에서 응답 크기 < 5MB 확인
- [ ] 인덱스 마이그레이션 생성 전 `EXPLAIN ANALYZE` 로 계획 변화 확인
- [ ] Watchlist 20항목 스냅샷 요청의 쿼리 수 < 5 (현재 ≥ 40 추정)

---

## 6. 전일 대비 변화 분석

### 6.1 FIXED 없음 (0건)

전일 TOP 5 권고 중 어느 것도 수정되지 않음. 구조 변경(LeaderComparisonView 등)은 시간이 걸리는 것이 이해되나, **쉬움 난이도 17건 중 단 한 건도 적용 안 됨**은 우려스러움:
- `DEFAULT_PAGINATION_CLASS` (2줄 추가)
- `rag_analysis` 3개 인덱스 (9줄 추가)
- `NewsViewSet` `pagination_class` 지정 (1줄)

### 6.2 신규 발견 (2건 추가)

| 구분 | 위치 | 심각도 |
|------|------|:------:|
| 논리 버그 | `stocks/serializers.py:405-409` `get_chart_data` return 누락 | HIGH |
| 신규 N+1 | `news/api/views.py:329-343` trending @action | MED |

### 6.3 에이전트 검증 결과 대조

1차 에이전트는 LeaderComparisonView를 "300→120 쿼리로 PARTIAL 개선"으로 보고했으나, **직접 원본을 읽어 확인한 결과 UNCHANGED**. 에이전트 요약을 맹신하지 않고 핵심 주장을 재검증한 것이 교훈.

---

## 7. 결론

- **전일 대비 이슈 총수는 1건 감소**(-30 → 29)하였으나, 이는 실제 수정이 아니라 재분류의 결과.
- **가장 시급한 조치 1건**: `get_chart_data` return 추가 — 기능 + 성능 이중 문제.
- **수정이 쉬운데 누적되는 부채**: rag_analysis 인덱스 3건 + 전역 페이지네이션. 총 작업 30분 이내, 영향 매우 큼.
- **최대 ROI**: `validation/api/views.py` 3건 일괄 리팩토링 시 쿼리 수 수백 개 감소.
- **구조적 이슈**: `OverviewTabSerializer.get_dynamic_layers` 는 TODO 주석만 있고 3일째 방치. Stock 목록 API의 은폐된 폭탄.
