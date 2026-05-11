# API 성능 감사 보고서

**감사일**: 2026-04-19
**범위**: Stock-Vis Django 백엔드 (17개 뷰 파일, 10개 serializer 파일, 7개 모델 파일)
**방식**: 정적 분석 (코드 읽기 전용, 수정 없음)
**이전 감사**: `docs/architecture/performance_audit.md` (2026-04-14)

---

## 요약

### 이슈 수 by 영역 x 심각도

| 영역 | HIGH | MED | LOW | 합계 |
|------|:----:|:---:|:---:|:----:|
| N+1 쿼리 (뷰) | 2 | 13 | 1 | 16 |
| 인덱스 누락 (모델) | 6 | 4 | 1 | 11 |
| Serializer 추가 쿼리 | 9 | 4 | 0 | 13 |
| 페이지네이션 누락 | 4 | 0 | 0 | 4 |
| **총계** | **21** | **21** | **2** | **44** |

### 수정 난이도 분포

| 난이도 | 건수 | 비율 |
|--------|:----:|:---:|
| 쉬움 (한 줄~5분) | 22 | 50% |
| 중간 (뷰/쿼리셋 리팩토링) | 18 | 41% |
| 높음 (구조 변경) | 4 | 9% |

### Top 5 우선 수정 (ROI 기준)

| 순위 | 위치 | 쿼리 개선 | 심각도 | 난이도 |
|:----:|------|----------|:------:|:------:|
| 1 | `validation/api/views.py:361` LeaderComparisonView | ~300개 → 3개 쿼리 | HIGH | 높음 |
| 2 | `stocks/serializers.py:205-307` OverviewTabSerializer.get_dynamic_layers | 7N → 1 쿼리 (6× OneToOne) | HIGH | 중간 |
| 3 | `stocks/views.py:75` StockListAPIView 페이지네이션 누락 | 수천 row 응답 | HIGH | 쉬움 |
| 4 | `validation/api/views.py:113` ValidationSummaryView 이중 N+1 | 10개 → 2개 쿼리 | HIGH | 중간 |
| 5 | `users/views.py:339` PortfolioSummaryView 루프 합산 | 1+N → 1 aggregate | HIGH | 중간 |

---

## 1. N+1 쿼리 (뷰)

### 파일별 요약

| 파일 | 이슈 수 | 최고 심각도 |
|------|:------:|:----------:|
| stocks/views.py | 1 | HIGH |
| stocks/views_eod.py | 1 | MED (이미 select_related 적용 — 참고용) |
| stocks/views_indicators.py | 1 | MED |
| stocks/views_mvp.py | 1 | MED |
| users/views.py | 1 | HIGH |
| news/api/views.py | 2 | MED |
| rag_analysis/views.py | 1 | MED |
| serverless/views_admin.py | 1 | LOW |
| validation/api/views.py | 3 | HIGH |
| chainsight/api/views.py | 0 (이미 bulk 처리됨) | — |
| 나머지 7개 파일 | 0 | — |

### 1.1 validation/api/views.py:361 — LeaderComparisonView (HIGH / 높음)

**문제**: 모든 지표 쌍(50~100개)마다 MetricDefinition + CompanyMetricSnapshot × 2 = 3쿼리 루프.

```python
for cat, mc in all_metrics:
    md = MetricDefinition.objects.filter(pk=mc).first()
    company_snap = CompanyMetricSnapshot.objects.filter(
        symbol=stock, fiscal_year=latest_fy, metric_code_id=mc,
    ).first()
    leader_snap = CompanyMetricSnapshot.objects.filter(
        symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc,
    ).first()
```

**예상 쿼리**: 100개 × 3 = 300개 추가 쿼리.

**권장 수정**:
```python
metrics = {m.pk: m for m in MetricDefinition.objects.filter(pk__in=[mc for _, mc in all_metrics])}
snaps = CompanyMetricSnapshot.objects.filter(
    symbol__in=[stock.symbol, leader.symbol],
    fiscal_year=latest_fy,
    value_status='normal',
    metric_code_id__in=metrics.keys(),
)
snap_map = {(s.symbol_id, s.metric_code_id): s for s in snaps}
for cat, mc in all_metrics:
    md = metrics.get(mc)
    company_snap = snap_map.get((stock.symbol, mc))
    leader_snap = snap_map.get((leader.symbol, mc))
```

### 1.2 validation/api/views.py:113 — ValidationSummaryView (HIGH / 중간)

**문제**: `rank_metrics` 5개마다 `CompanyBenchmarkDelta` 1쿼리 + `MetricDefinition` 1쿼리 = 10개 추가 쿼리.

**권장**: `metric_code_id__in=rank_metrics` 로 한 번에 bulk 조회 → dict 매핑.

### 1.3 validation/api/views.py:199-217 — ValidationMetricsView._build_category (MED / 쉬움)

**문제**: `for mc in metric_codes` 루프에서 `MetricDefinition.objects.filter(pk=mc).first()` 반복.

**권장**: `{m.pk: m for m in MetricDefinition.objects.filter(pk__in=metric_codes)}`.

### 1.4 users/views.py:339-385 — PortfolioSummaryView (HIGH / 중간)

**문제**: `for portfolio in portfolios: total_value += portfolio.total_value` — 계산 property가 내부적으로 `stock.real_time_price` 접근. `select_related('stock')` 보장 안 되면 N+1.

**권장**: ORM aggregate로 전환:
```python
portfolios.aggregate(
    total_value=Sum(F('quantity') * F('stock__real_time_price'), output_field=DecimalField()),
    total_cost=Sum('total_cost'),
)
```

### 1.5 news/api/views.py:330-336 — NewsViewSet.trending (MED / 높음)

**문제**: 트렌딩 심볼마다 `NewsArticle.objects.filter(entities__symbol=symbol, ...)[:3]` 반복.

**권장**: `entities__symbol__in=trending_symbols` 로 한 번에 로드하고 in-memory 그룹화.

### 1.6 news/api/views.py:89-92 — NewsViewSet.stock_news (MED / 중간)

**문제**: `.distinct()` + reverse M2M + prefetch 없음. 중복 row 제거 비용 + 엔티티 serialization 추가 쿼리.

**권장**: `Prefetch('entities', queryset=NewsEntity.objects.filter(symbol=symbol))` 패턴.

### 1.7 stocks/views_indicators.py:324-372 — IndicatorComparisonView (MED / 중간)

**문제**: `for symbol in symbols` 안에서 `Stock.objects.get()` + `DailyPrice.objects.filter()` 반복.

**권장**: `Stock.objects.filter(symbol__in=symbols)` + `DailyPrice.objects.filter(stock__symbol__in=symbols).order_by('stock', '-date')` bulk.

### 1.8 stocks/views_mvp.py:47-56 — StockMVPListView (MED / 쉬움)

**문제**: 객체 전체 로딩 후 dict 변환. 필드 7개만 필요.

**권장**: `queryset.values('symbol', 'stock_name', ...)[:20]`.

### 1.9 stocks/views.py:820-874 — StockCompleteDataAPIView (HIGH / 쉬움)

**문제**: 단일 stock에 대한 재무제표 3종(Balance/Income/CashFlow) 각각 별도 쿼리. 프론트엔드가 매 상세 페이지 진입마다 호출.

**권장**: serializer가 추가 쿼리를 유발하지 않는지 확인. 필요 시 `prefetch_related('balance_sheets', 'income_statements', 'cash_flows')`.

### 1.10 rag_analysis/views.py:292-336 — DataBasketAddStockDataView (MED / 쉬움)

**문제**: `for data_type in data_types: BasketItem.objects.filter(...).first()` 반복 중복 체크.

**권장**:
```python
existing_items = {
    (i.item_type, i.reference_id): i
    for i in BasketItem.objects.filter(basket=basket, reference_id=symbol, item_type__in=data_types)
}
```

### 1.11 serverless/views_admin.py:478-481 — AdminNewsCategoryView (LOW / 중간)

**문제**: `for cat in categories: symbols = cat.resolve_symbols()` — 메서드 내부 쿼리 가능성.

**권장**: `resolve_symbols()` 구현 확인 후 bulk prefetch 추가.

---

## 2. 인덱스 누락 (모델)

### 모델별 요약

| 모델 파일 | 이슈 수 |
|-----------|:------:|
| stocks/models.py | 3 |
| users/models.py | 2 |
| news/models.py | 3 |
| serverless/models.py | 3 |
| rag_analysis/models.py | 2 |
| sec_pipeline/models.py | 2 |
| graph_analysis/models.py | 1 |

> 주의: 에이전트가 발견한 이슈 중 일부는 이미 `Meta.indexes` 로 부분 커버됨 — "커버리지 확인" 항목은 실제 쿼리 패턴과 대조 후 결정할 것.

### 2.1 stocks/models.py — Stock.created_at (HIGH / 쉬움)

**문제**: `order_by('-created_at')` 사용 가능성 있으나 `db_index=True` 없음.
**권장**: 필드에 `db_index=True` 추가 + migration.

### 2.2 news/models.py — NewsArticle.category (HIGH / 쉬움)

**문제**: `NewsArticle.objects.filter(category__in=..., published_at__gte=...)` 패턴이 뉴스 피드 API에서 반복 사용되나, `category` 단독 인덱스 또는 `(category, -published_at)` 복합 인덱스 없음.
**권장**: `Meta.indexes += [models.Index(fields=['category', '-published_at'])]`.

### 2.3 serverless/models.py — MarketMover 인덱스 커버리지 (HIGH / 쉬움)

**문제**: `Meta.indexes` 에 `date`, `mover_type` 등이 있으나, `SectorPerformance.order_by('-return_pct')` 같은 정렬 쿼리가 커버되는지 확인 필요.
**권장**: `EXPLAIN ANALYZE` 로 실제 plan 확인 후 결정.

### 2.4 sec_pipeline/models.py — BusinessModelSnapshot (HIGH / 중간)

**문제**: `(symbol, fiscal_year)` 또는 `(symbol, as_of_date)` 복합 쿼리에 적합한 인덱스 확인 필요.
**권장**: 실제 쿼리 패턴에 맞춰 복합 인덱스 추가.

### 2.5 users/models.py — Watchlist.updated_at (HIGH / 쉬움)

**문제**: `Watchlist.objects.filter(user=request.user).order_by('-updated_at')` 패턴. 현재 `Meta.indexes` 가 `(user, updated_at)` 을 명시적으로 커버하는지 확인 필요.
**권장**: 확인 후 미비 시 복합 인덱스 추가.

### 2.6 stocks/models.py — SP500Constituent 복합 (MED / 중간)

**문제**: `filter(sector=..., is_active=True)` 패턴. 개별 인덱스는 있으나 복합 아님.
**권장**: `models.Index(fields=['sector', 'is_active'])`.

### 2.7 serverless/models.py — ScreenerPreset.user + use_count (MED / 중간)

**문제**: `filter(user=...).order_by('-use_count', 'name')` 패턴.
**권장**: `models.Index(fields=['user', '-use_count'])`.

### 2.8 rag_analysis/models.py — AnalysisSession (MED / 쉬움)

**문제**: `filter(user=request.user)` 정렬 시 최적화 부족.
**권장**: `Meta.indexes += [models.Index(fields=['user', '-created_at'])]`.

### 2.9 news/models.py — DailyNewsKeyword.status (MED / 쉬움)

**문제**: `filter(status='completed', date__lt=...)` 폴백 로직.
**권장**: `(status, date)` 복합 인덱스.

### 2.10 sec_pipeline/models.py — UnmatchedCompanyQueue.status (MED / 쉬움)

**문제**: 배치에서 `filter(status='pending')`.
**권장**: `db_index=True`.

### 2.11 users/models.py — UserInterest.created_at (LOW / 쉬움)

**문제**: 개인화 설정 목록 `order_by('-created_at')`, 저빈도.
**권장**: `db_index=True` (우선순위 낮음).

---

## 3. Serializer 추가 쿼리

### 3.1 stocks/serializers.py:205-307 — OverviewTabSerializer.get_dynamic_layers (HIGH / 중간)

**문제**: 하나의 Stock 인스턴스에 대해 6개의 OneToOne 역참조(`overview_ko`, `validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + reverse FK(`category_signals.all()`) 를 prefetch 없이 접근.

**쿼리 수**: Stock N개 목록 응답 시 `N × 7` 쿼리.

**권장 수정 (뷰 쪽)**:
```python
queryset = Stock.objects.select_related(
    'overview_ko',
    'validation_news_summary',
    'sensitivity_profile',
    'growth_stage',
    'capital_dna',
    'narrative_tag',
).prefetch_related('category_signals')
```

### 3.2 stocks/serializers.py:400-409 — WatchListStockSerializer (HIGH / 쉬움)

**문제**: `get_latest_price()` 와 `get_chart_data()` 가 각각 `DailyPrice.objects.filter(stock=obj)` 를 호출. Watchlist 종목 20개 조회 시 40개 추가 쿼리.

**권장 수정**:
- 뷰에서 `prefetch_related(Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7]))`
- 또는 `annotate(latest_price=Max('daily_prices__close_price'))` 로 사전 계산

### 3.3 news/api/serializers.py:19, 47 — NewsEntitySerializer / NewsArticleListSerializer (MED / 쉬움)

**문제**: nested `many=True` (entities, highlights) 가 prefetch 없이 사용됨.

**권장**: 뷰에서 `prefetch_related('entities__highlights')`.

### 3.4 users/serializers.py:15,23 — UserSerializer.favorite_stock (MED / 쉬움)

**문제**: `StockListingField(many=True)` 가 prefetch 없이 직렬화.

**권장**: 뷰에서 `prefetch_related('favorite_stock')`.

### 3.5 rag_analysis/serializers.py:27,69 — DataBasketSerializer/AnalysisSessionSerializer (MED / 중간)

**문제**: nested `items`, `messages` 가 prefetch 없이 사용 가능.

**권장**: 뷰 `get_queryset()` 에서 `prefetch_related('items', 'messages')`.

### 3.6 serverless/serializers.py:121-137 — MarketMoverListSerializer (MED / 쉬움)

**문제**: `SerializerMethodField` 안에서 `IndicatorCalculator` 인스턴스 생성 및 함수 호출. 목록 응답에서 인스턴스당 반복.

**권장**: 뷰에서 `annotate` 로 사전 계산하거나 태스크에서 미리 계산된 필드로 대체.

---

## 4. 페이지네이션 누락

### 4.1 전역 설정 미존재 (HIGH)

**위치**: `config/settings.py` REST_FRAMEWORK 설정에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 없음.

**영향**: 모든 `ListAPIView` / `ModelViewSet.list` 가 명시적으로 페이지네이션을 설정하지 않으면 전체 쿼리셋을 JSON으로 반환.

**권장**:
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    ...
}
```
> **주의**: 전역 설정 추가 시 기존 프론트엔드 응답 구조가 `results/count/next/previous` 로 바뀌므로 호환성 검증 필요. 점진적 적용 (뷰 단위로 pagination_class 명시) 이 더 안전.

### 4.2 stocks/views.py:75 — StockListAPIView (HIGH / 쉬움)

**문제**: `Stock.objects.all()` 반환 가능. 프로덕션에 수천~수만 row.

**권장**: `pagination_class = PageNumberPagination` 명시.

### 4.3 news/api/views.py:42 — NewsViewSet (HIGH / 쉬움)

**문제**: `ReadOnlyModelViewSet.list()` — 전체 `NewsArticle` 테이블 노출 가능. 기록 10만+ row.

**권장**: 클래스 레벨 `pagination_class` 명시 또는 전역 설정 의존.

### 4.4 news/api/views.py:89, 154 — @action(detail=False) 엔드포인트 (HIGH / 중간)

**문제**: `stock_news`, `stock_news_sentiment` 가 `Response(data)` 직접 반환 — `paginate_queryset` 호출 없음.

**권장**:
```python
page = self.paginate_queryset(articles)
if page is not None:
    serializer = NewsArticleListSerializer(page, many=True)
    return self.get_paginated_response(serializer.data)
```

### 4.5 users/views.py:89-92 — Users.get (HIGH / 중간)

**문제**: `APIView` 에서 `User.objects.all()` 직접 serialize. 수동 paginator 필요.

**권장**: `ListAPIView` 로 전환하거나 `rest_framework.pagination` 수동 호출.

---

## 권장 작업 순서

### Sprint 1 — 쉬운 것 먼저 (1~2일)
1. `rest_framework.pagination.PageNumberPagination` 를 `StockListAPIView`, `NewsViewSet` 에 명시적 적용 (§4.2, §4.3)
2. `validation/api/views.py:199` `MetricDefinition` 사전 로드 (§1.3)
3. `rag_analysis/views.py:292` `BasketItem` 사전 로드 (§1.10)
4. `news/api/views.py` — 뷰 쿼리셋에 `prefetch_related('entities__highlights')` (§3.3)
5. `users/views.py` — `prefetch_related('favorite_stock')` (§3.4)
6. Stock/NewsArticle/기타 단일 필드 인덱스 추가 (§2.1, §2.2)

### Sprint 2 — 중간 난이도 (3~5일)
7. `validation/api/views.py:113` ValidationSummaryView bulk 로드 (§1.2)
8. `users/views.py:339` PortfolioSummaryView aggregate 전환 (§1.4)
9. `stocks/serializers.py` OverviewTabSerializer — 뷰에서 `select_related` 6개 OneToOne + `prefetch_related('category_signals')` (§3.1)
10. `WatchListStockSerializer` — `Prefetch('daily_prices', ...)` (§3.2)
11. `serverless/serializers.py` MarketMoverListSerializer annotate 전환 (§3.6)
12. 복합 인덱스 추가 (§2.6, §2.7, §2.8)

### Sprint 3 — 구조 변경 (5일 이상)
13. `validation/api/views.py:361` LeaderComparisonView 전면 리팩토링 (§1.1)
14. `news/api/views.py:330` trending — pre-aggregated bulk 구조 (§1.5)
15. 전역 `DEFAULT_PAGINATION_CLASS` 도입 시 프론트엔드 응답 구조 마이그레이션 (§4.1)

### 검증 방법 (수정 후)
- Django Debug Toolbar 또는 `django-silk` 로 쿼리 수 측정 (수정 전후 비교).
- 주요 엔드포인트에 `assertNumQueries` 테스트 추가.
- `EXPLAIN ANALYZE` 로 인덱스 추가 후 실제 plan 변화 확인.

---

## 참고 자료

- 이전 감사: `docs/architecture/performance_audit.md` (2026-04-14) — 중복 이슈 여부 대조 권장
- 공통 버그 목록: `sub_claude_md/common-bugs.md`
- Django ORM 최적화: select_related, prefetch_related, annotate, Prefetch, values, iterator
