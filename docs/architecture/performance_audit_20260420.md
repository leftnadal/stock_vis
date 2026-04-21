# API 성능 감사 보고서

**감사일**: 2026-04-20
**범위**: Stock-Vis Django 백엔드 (17개 뷰 + 10개 serializer + 7개 모델)
**방식**: 정적 분석 (읽기 전용, 코드 수정 없음)
**이전 감사**: `performance_audit_20260419.md` — 결과 대조 포함
**검증 방식**: 3개 병렬 Explore 에이전트 + 핵심 주장 직접 재확인 (`config/settings.py:331`, `rag_analysis/models.py:28`, `validation/api/views.py:361`)

---

## 요약

### 이슈 수 by 영역 × 심각도

| 영역 | HIGH | MED | LOW | 합계 |
|------|:----:|:---:|:---:|:----:|
| N+1 쿼리 (뷰) | 2 | 8 | 1 | 11 |
| 인덱스 누락 (모델) | 4 | 3 | 2 | 9 |
| Serializer 추가 쿼리 | 2 | 4 | 0 | 6 |
| 페이지네이션 누락 | 4 | 0 | 0 | 4 |
| **총계** | **12** | **15** | **3** | **30** |

### 이전 감사 대비 변화

| 지표 | 2026-04-19 | 2026-04-20 | Δ |
|------|:---------:|:---------:|:--:|
| 총 이슈 | 44 | 30 | **-14** |
| HIGH | 21 | 12 | **-9** |
| MED | 21 | 15 | -6 |
| LOW | 2 | 3 | +1 |

**개선된 항목 (FIXED)**:
- `users/views.py:339` PortfolioSummaryView — `select_related('stock')` 적용 (루프 합산 자체는 여전히 구조 개선 여지 있음)
- `news/models.py` NewsArticle — `['-published_at', 'category']` 복합 인덱스 확인됨
- `serverless/models.py` ScreenerPreset — `(user, -use_count)` 인덱스 확인됨
- `stocks/models.py` DailyPrice — `['stock', '-date']`, `['date', 'volume']` 복합 인덱스 확인됨
- `stocks/models.py` Stock.sector / Stock.industry — `db_index=True` 적용 확인됨

### 수정 난이도 분포

| 난이도 | 건수 | 비율 |
|--------|:----:|:---:|
| 쉬움 (한 줄~5분) | 16 | 53% |
| 중간 (쿼리셋/뷰 리팩토링) | 12 | 40% |
| 높음 (구조 변경) | 2 | 7% |

### Top 5 우선 수정 (ROI 기준)

| 순위 | 위치 | 쿼리/영향 개선 | 심각도 | 난이도 |
|:----:|------|----------|:------:|:------:|
| 1 | `validation/api/views.py:361` LeaderComparisonView | ~300개 → 3개 쿼리 | HIGH | 높음 |
| 2 | `config/settings.py:331` DEFAULT_PAGINATION_CLASS 전역 미설정 | 수만 row 응답 방지 | HIGH | 쉬움 |
| 3 | `stocks/serializers.py:205` OverviewTabSerializer.get_dynamic_layers | 7N → 1 쿼리 (6× OneToOne + reverse FK) | HIGH | 중간 |
| 4 | `rag_analysis/models.py` DataBasket / AnalysisSession user 인덱스 부재 | full scan → indexed lookup | HIGH | 쉬움 |
| 5 | `news/api/views.py:42` NewsViewSet 페이지네이션 누락 | 수만 row 방지 | HIGH | 쉬움 |

---

## 1. N+1 쿼리 (뷰)

### 파일별 요약

| 파일 | 이슈 수 | 최고 심각도 |
|------|:------:|:----------:|
| validation/api/views.py | 3 | HIGH |
| stocks/views.py | 2 | MED |
| stocks/views_mvp.py | 1 | MED |
| users/views.py | 1 | MED |
| news/api/views.py | 2 | MED |
| rag_analysis/views.py | 1 | MED |
| serverless/views_admin.py | 1 | LOW |
| 나머지 10개 파일 | 0 | — |

### 1.1 validation/api/views.py:361-372 — LeaderComparisonView (HIGH / 높음)

**문제**: 모든 지표 쌍(50~100개)마다 `MetricDefinition` + `CompanyMetricSnapshot × 2` = 3쿼리 루프.

```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()
    company_snap = CompanyMetricSnapshot.objects.filter(
        symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
    leader_snap = CompanyMetricSnapshot.objects.filter(
        symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
    ).first()
```

**예상 쿼리**: 100 × 3 = **300개 추가 쿼리**. 이전 감사 대비 **UNCHANGED**.

**권장 수정**:
```python
metric_ids = [mc for _, mc in all_metrics]
metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_ids)}
snaps = CompanyMetricSnapshot.objects.filter(
    symbol__in=[stock.symbol, leader.symbol],
    fiscal_year=latest_fy,
    value_status='normal',
    metric_code_id__in=metric_ids,
)
snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
for cat, mc in all_metrics:
    md = metrics.get(mc)
    company_snap = snap_map.get((stock.symbol, mc))
    leader_snap = snap_map.get((leader.symbol, mc))
```

### 1.2 validation/api/views.py:113-124 — ValidationSummaryView (HIGH / 중간)

**문제**: `rank_metrics` 5개마다 `CompanyBenchmarkDelta` 1쿼리 + `MetricDefinition` 1쿼리 = 10개 추가. **UNCHANGED**.

**권장**: `metric_code_id__in=rank_metrics` 로 한 번에 bulk 조회 → dict 매핑.

### 1.3 validation/api/views.py:199-208 — ValidationMetricsView._build_category (MED / 쉬움)

**문제**: 카테고리당 6~15개 지표 루프 안에서 `MetricDefinition.objects.filter(pk=mc).first()`. **UNCHANGED**.

**권장**:
```python
metric_codes = CATEGORY_METRICS.get(category, [])
metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_codes)}
for mc in metric_codes:
    md = metrics.get(mc)
```

### 1.4 users/views.py:339-385 — PortfolioSummaryView (MED / 중간) *(부분 개선)*

**변경**: 이전 감사 대비 `select_related('stock')` 적용됨 (라인 351) → N+1 자체는 해결.

**잔여 문제**: `portfolio.total_value` / `portfolio.total_cost` property 접근을 Python 루프에서 합산. `stock.real_time_price` 사용 시 DB에서 바로 집계 가능.

**권장**:
```python
from django.db.models import F, Sum, DecimalField
summary = portfolios.aggregate(
    total_value=Sum(F('quantity') * F('stock__real_time_price'), output_field=DecimalField()),
    total_cost=Sum('total_cost'),
    total_stocks=Count('id'),
)
```

### 1.5 stocks/views.py:820-874 — StockCompleteDataAPIView (MED / 쉬움)

**문제**: `stock = get_object_or_404(Stock, symbol=...)` 후 `OverviewTabSerializer(stock)` 호출 → 내부에서 OneToOne 6개 + reverse FK 접근. 재무제표 3종(BalanceSheet, IncomeStatement, CashFlowStatement) 별도 쿼리.

**권장**:
```python
stock = Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals').get(symbol=symbol.upper())
```

### 1.6 stocks/views_mvp.py:47-56 — StockMVPListView (MED / 쉬움)

**문제**: 쿼리셋 전체를 Python 루프로 돌며 dict 생성. FK 접근은 없지만 Stock 객체 메모리 로드 과다.

**권장**: `queryset.values('symbol', 'stock_name', ...)[:20]` 으로 DB에서 필요한 필드만.

### 1.7 news/api/views.py:87-104 — NewsViewSet.stock_news (MED / 쉬움)

**문제**: `.distinct()` 호출 후 `NewsArticleListSerializer`에서 `entities` (M2M) 접근 → N+1.

**권장**:
```python
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).prefetch_related('entities', 'entities__highlights').distinct().order_by('-published_at')
```

### 1.8 news/api/views.py:406-440 — NewsViewSet.list (MED / 쉬움)

**문제**: ViewSet의 기본 `queryset = NewsArticle.objects.all().prefetch_related('entities')` 은 있지만, `entities__highlights`가 빠져서 detail 응답에서 N+1.

**권장**: `queryset = NewsArticle.objects.all().prefetch_related('entities__highlights')`.

### 1.9 rag_analysis/views.py:73, 433, 503 — DataBasket / AnalysisSession 조회 (MED / 중간)

**문제**: `DataBasket.objects.filter(user=request.user).prefetch_related('items')` 는 적용되어 있으나, user 필드 인덱스 없음 → 사용자 수 증가 시 full scan. 인덱스 섹션 §2.5 참조.

### 1.10 serverless/views_admin.py:478-481 — AdminNewsCategoryView (LOW / 중간)

**상태**: 파일 내 해당 라인 범위 구조 미확인. 관리자 뷰로 호출 빈도 낮음.

---

## 2. 인덱스 누락 (모델)

### 모델별 요약

| 모델 파일 | HIGH | MED | LOW | 상태 |
|----------|:----:|:---:|:---:|------|
| rag_analysis/models.py | 3 | 0 | 0 | **CRITICAL** |
| sec_pipeline/models.py | 1 | 1 | 0 | CRITICAL |
| stocks/models.py | 0 | 1 | 0 | GOOD (전일 대비 대폭 개선) |
| users/models.py | 0 | 1 | 1 | PARTIAL |
| news/models.py | 0 | 0 | 0 | **FIXED** |
| serverless/models.py | 0 | 1 | 1 | GOOD |
| graph_analysis/models.py | 0 | 0 | 0 | GOOD |

### 2.1 rag_analysis/models.py:11-57 — DataBasket.user 인덱스 부재 (HIGH / 쉬움)

**현재**: `class Meta: ordering = ["-updated_at"]` 만 있음, `indexes = []` 없음.

**사용 패턴** (`rag_analysis/views.py:73`): `DataBasket.objects.filter(user=request.user)` — 매 요청마다 호출.

**권장**:
```python
class Meta:
    ordering = ["-updated_at"]
    indexes = [
        models.Index(fields=['user', '-updated_at']),
    ]
```

### 2.2 rag_analysis/models.py:130-181 — AnalysisSession.user / created_at 인덱스 부재 (HIGH / 쉬움)

**사용 패턴** (`rag_analysis/views.py:433`): `AnalysisSession.objects.filter(user=request.user).order_by('-created_at')`.

**권장**:
```python
class Meta:
    indexes = [
        models.Index(fields=['user', '-created_at']),
        models.Index(fields=['user', 'status']),
    ]
```

### 2.3 rag_analysis/models.py:184-218 — AnalysisMessage.session 정렬 인덱스 (HIGH / 쉬움)

**사용 패턴** (`rag_analysis/views.py:503`): `session.messages.all().order_by('created_at')`.

**권장**: `models.Index(fields=['session', 'created_at'])` (FK 암묵 인덱스가 있지만 정렬에는 복합이 유리).

### 2.4 sec_pipeline/models.py:190 — BusinessModelSnapshot (symbol, fiscal_year) 복합 인덱스 부재 (HIGH / 쉬움)

**현재**: `indexes = [models.Index(fields=['symbol', '-as_of_date'])]` 만 존재.

**문제**: 뷰에서 `filter(symbol=..., fiscal_year=...)` 패턴이 빈번 → 현재 인덱스로 미커버.

**권장**:
```python
indexes = [
    models.Index(fields=['symbol', '-as_of_date']),
    models.Index(fields=['symbol', 'fiscal_year']),
]
```

### 2.5 stocks/models.py:89 — Stock.created_at 인덱스 부재 (MED / 쉬움)

**사용 패턴**: `order_by('-created_at')` (일부 관리/통계 뷰).

**권장**: `created_at = models.DateTimeField(auto_now_add=True, db_index=True)`.

### 2.6 stocks/models.py:656-664 — SP500Constituent (sector, is_active) 복합 인덱스 부재 (MED / 쉬움)

**현재**: 개별 `db_index=True`만 있음.

**사용 패턴**: `filter(sector=..., is_active=True)`.

**권장**: `Meta.indexes += [models.Index(fields=['sector', 'is_active'])]`.

### 2.7 users/models.py:174 — Watchlist.created_at 인덱스 부재 (MED / 쉬움)

**현재**: `indexes = [models.Index(fields=['user', '-updated_at'])]` 만 존재. `created_at` 정렬/필터 시 커버 안 됨.

**권장**: `created_at = models.DateTimeField(auto_now_add=True, db_index=True)`.

### 2.8 sec_pipeline/models.py:338-340 — UnmatchedCompanyQueue (status, created_at) (MED / 쉬움)

**현재**: `status` 단일 인덱스. 배치에서 `filter(status='pending').order_by('-created_at')` 패턴.

**권장**: `models.Index(fields=['status', '-created_at'])`.

### 2.9 users/models.py:261 — UserInterest.created_at (LOW / 쉬움)

**사용 패턴**: `order_by('-created_at')`. 호출 빈도 낮음.

**권장**: `db_index=True` 추가.

### 2.10 serverless/models.py:414 — ScreenerPreset.created_at (LOW / 쉬움)

**사용 패턴**: 관리 뷰에서 `order_by('-created_at')`. 호출 빈도 낮음.

---

## 3. Serializer 추가 쿼리

### 3.1 stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers (HIGH / 중간)

**문제**: 6개 OneToOne 역참조(`overview_ko`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + 1개 reverse FK(`category_signals`)를 인스턴스마다 접근 → prefetch 없음.

**영향**: Stock 목록 N개에 대해 **N × 7 추가 쿼리**.

**권장** (뷰 측):
```python
queryset = Stock.objects.select_related(
    'overview_ko', 'validation_news_summary', 'sensitivity_profile',
    'growth_stage', 'capital_dna', 'narrative_tag',
).prefetch_related('category_signals')
```

### 3.2 stocks/serializers.py:398-410 — WatchListStockSerializer (HIGH / 쉬움)

**문제**: `get_latest_price()`, `get_chart_data()` 두 메서드가 각각 `DailyPrice.objects.filter(stock=obj)` 호출.

**영향**: Watchlist 항목 20개 × 2 = **40개 추가 쿼리**.

**권장**:
```python
from django.db.models import Prefetch
items = WatchlistItem.objects.select_related('stock').prefetch_related(
    Prefetch('stock__daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7])
)
```

### 3.3 news/api/serializers.py:19 — NewsEntitySerializer.highlights (MED / 쉬움)

**문제**: `highlights = EntityHighlightSerializer(many=True, read_only=True)` nested → prefetch 없음.

**권장**: 뷰에서 `prefetch_related('entities__highlights')`.

### 3.4 news/api/serializers.py:47 — NewsArticleListSerializer.entities (MED / 쉬움)

**문제**: `entities = NewsEntitySimpleSerializer(many=True, read_only=True)` → ViewSet의 `queryset = NewsArticle.objects.all().prefetch_related('entities')`는 적용되어 있지만, `.distinct()`가 들어간 stock_news 등 커스텀 액션에서 prefetch 누락.

### 3.5 users/serializers.py:15, 23 — UserSerializer.favorite_stock (MED / 쉬움)

**문제**: `StockListingField(many=True, read_only=True)` M2M → 뷰에서 prefetch 없음.

**권장**: `User.objects.prefetch_related('favorite_stock')`.

### 3.6 serverless/serializers.py:121-137 — MarketMoverListSerializer (MED / 중간)

**문제**: `get_sector_alpha_display`, `get_etf_sync_display`, `get_volatility_pct_display` 세 메서드가 각자 `IndicatorCalculator()` 를 **row마다 인스턴스화**.

**권장**: serializer `__init__`에서 한 번 생성하고 재사용.

---

## 4. 페이지네이션 누락

### 4.1 config/settings.py:331-339 — DEFAULT_PAGINATION_CLASS 전역 미설정 (HIGH / 쉬움)

**현재 상태** (직접 확인):
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
}
```
`DEFAULT_PAGINATION_CLASS`, `PAGE_SIZE` 키가 없음 → 모든 ListAPIView가 명시 없이는 전체 반환.

**권장**:
```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
'PAGE_SIZE': 20,
```

**⚠️ 주의**: 전역 적용 시 기존 응답 구조 변경 (배열 → `{results, count, next, previous}`). 프론트엔드 호환성 검증 필요. 점진적 적용(뷰별 `pagination_class = ...`)이 더 안전.

### 4.2 stocks/views.py:75 — StockListAPIView (HIGH / 쉬움)

**현재**: `pagination_class` 미설정. Stock 테이블은 수천~수만 row.

**권장**: `pagination_class = PageNumberPagination`.

### 4.3 news/api/views.py:42 — NewsViewSet (HIGH / 쉬움)

**현재**: `ReadOnlyModelViewSet`에 페이지네이션 미설정. NewsArticle은 수만 row 규모.

**권장**: `pagination_class = PageNumberPagination`.

### 4.4 news/api/views.py:54-104 — stock_news @action (HIGH / 중간)

**현재**: `@action` 메서드 내부에서 `self.paginate_queryset(articles)` 호출 없음. 특정 심볼의 뉴스가 수백 개일 수 있음.

**권장**:
```python
page = self.paginate_queryset(articles)
if page is not None:
    serializer = self.get_serializer(page, many=True)
    return self.get_paginated_response(serializer.data)
```

### 4.5 users/views.py:89-92 — Users.get (HIGH / 중간) *(추가 조사 권장)*

**현재**: `APIView.get`에서 `User.objects.all()` → 전체 반환. 관리자용이지만 명시적 페이지네이터 없음.

**권장**: `ListAPIView`로 전환하거나 `PageNumberPagination.paginate_queryset()` 수동 호출.

---

## 5. 검증 체크리스트 (수정 후 권장)

- [ ] `django-silk` 또는 `django-debug-toolbar`로 각 엔드포인트 쿼리 수 before/after 측정
- [ ] 회귀 테스트: `self.assertNumQueries(N):` 로 상한선 고정
- [ ] 페이지네이션 적용 시 프론트엔드 응답 파싱 호환성 확인 (`results` 래핑)
- [ ] 1000 row 이상 시나리오에서 응답 크기 < 5MB 확인
- [ ] 인덱스 마이그레이션 생성 전 `EXPLAIN ANALYZE`로 계획 변화 확인

---

## 6. 참고: 이미 FIXED된 전일 지적 사항

| 전일 지적 | 현재 상태 | 확인 라인 |
|----------|----------|----------|
| `users/views.py:339` N+1 | `select_related('stock')` 적용 (루프 합산은 잔여) | users/views.py:351 |
| `news/models.py` NewsArticle.category | `['-published_at', 'category']` 복합 인덱스 | news/models.py:193 |
| `serverless/models.py` ScreenerPreset | `(user, -use_count)` 인덱스 | serverless/models.py:422 |
| `stocks/models.py` DailyPrice 복합 인덱스 | `['-date']`, `['date', 'volume']`, `['stock', '-date']` | stocks/models.py:186-189 |
| `stocks/models.py` Stock.sector/industry | `db_index=True` | stocks/models.py:96-97 |

---

## 7. 결론

- **HIGH 이슈 9개 감소** (21 → 12). 특히 뉴스/스크리너/DailyPrice 인덱스 영역에서 큰 개선.
- **새로운 집중 영역**: `rag_analysis` 앱이 0 인덱스 상태 → 사용자 증가 시 병목 확실. 3줄 추가로 해결 가능.
- **최대 ROI**: LeaderComparisonView 리팩토링 (쿼리 100× 감소) + 전역 페이지네이션 설정.
- **여전히 문제**: `stocks/serializers.py` OverviewTabSerializer가 prefetch 보호 없이 서빙되고 있어, 목록 페이지에서 은밀하게 대량 쿼리 발생.
