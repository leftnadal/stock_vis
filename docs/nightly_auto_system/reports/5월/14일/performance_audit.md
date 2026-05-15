# API 성능 감사 보고서

**감사일**: 2026-05-14
**범위**: views 17개 + models 7개 + serializers 10개
**모드**: 읽기 전용 (코드 수정 없음)

---

## 요약

### 심각도별 이슈 카운트

| 영역 | HIGH | MED | LOW | 합계 |
|------|------|-----|-----|------|
| N+1 쿼리 (views) | 7 | 6 | 3 | 16 |
| 인덱스 누락 (models) | 3 | 4 | 4 | 11 |
| 느린 Serializer | 2 | 3 | 1 | 6 |
| 페이지네이션 누락 | 4 | 3 | 2 | 9 |
| **총합** | **16** | **16** | **10** | **42** |

### 핫스팟 파일 (이슈 3개 이상)

| 파일 | 이슈 수 | 주요 문제 |
|------|---------|----------|
| `validation/api/views.py` | 5 | 루프 내 ORM 쿼리 5건 (HIGH) |
| `stocks/serializers.py` | 3 | dynamic_layers 6개 OneToOne + WatchList N+1 |
| `news/api/views.py` | 3 | 페이지네이션 누락 + distinct() |
| `news/models.py` | 3 | published_at, sentiment, importance 인덱스 부족 |

### 글로벌 설정 이슈

- `config/settings.py`: `DEFAULT_PAGINATION_CLASS` **미설정** → 전역 기본 페이지네이션 없음 → list 뷰에서 명시적 설정 누락 시 전체 반환

### 우선순위 처리 순서 (CRITICAL TOP 5)

1. `stocks/serializers.py:205-306` — OverviewTab dynamic_layers 6개 OneToOne (잠재 600 쿼리)
2. `validation/api/views.py:148-400` — 루프 내 `.filter().first()` 5건
3. `config/settings.py` — `DEFAULT_PAGINATION_CLASS` 전역 설정 추가
4. `news/api/views.py:50-110` — NewsViewSet 페이지네이션 누락 (수만 건)
5. `users/views.py:91-94` — 관리자 Users 엔드포인트 페이지네이션 누락

---

## 상세 1: N+1 쿼리 (views)

### 🔴 HIGH (7건)

#### N1-H1: `validation/api/views.py:148-161` — rank_metrics 루프 [난이도: 중간]
**패턴**: `ValidationSummaryView.get()`에서 rank_metrics 리스트 순회 중 `CompanyBenchmarkDelta.objects.filter(...)` 반복 호출
**설명**: 메트릭당 1쿼리 (5개 메트릭 = 5쿼리)
**권장**: `CompanyBenchmarkDelta.objects.filter(symbol=stock, fiscal_year=fy, metric_code_id__in=rank_metrics)` 단일 쿼리

#### N1-H2: `validation/api/views.py:204` — metric_codes 루프 [난이도: 높음]
**패턴**: `_build_category()`에서 각 metric_code마다 `MetricDefinition.objects.filter(pk=mc).first()`
**권장**: `MetricDefinition.objects.filter(pk__in=metric_codes).in_bulk()` 후 dict lookup

#### N1-H3: `validation/api/views.py:264-286` — snaps 루프 [난이도: 높음]
**패턴**: `_build_metric()`에서 snapshot마다 `PeerMetricBenchmark.objects.filter().first()` (최대 5년 × 1쿼리)
**권장**: `filter(... fiscal_year__in=years)` 일괄 로드 후 메모리 필터

#### N1-H4: `validation/api/views.py:361-400` — all_metrics 루프 (MetricDefinition) [난이도: 높음]
**패턴**: `LeaderComparisonView.get()`에서 `MetricDefinition.objects.filter(pk=mc).first()` 반복
**권장**: `in_bulk(field_name='pk')` 사용

#### N1-H5: `validation/api/views.py:366-371` — all_metrics 루프 (CompanyMetricSnapshot) [난이도: 중간]
**패턴**: company/leader 메트릭 조합당 2쿼리
**권장**: 단일 쿼리로 모든 snapshot 로드 후 in-memory filter

#### N1-H6: `users/views.py:373-376` — PortfolioSummaryView 집계 [난이도: 쉬움]
**패턴**: portfolios 루프에서 Python으로 `total_value` 합산. select_related('stock') 적용은 되어 있으나 DB aggregate 사용 안 함
**권장**: `portfolios.aggregate(total=Sum(F('shares')*F('stock__current_price')))`

#### N1-H7: `users/views.py:409` — PortfolioDetailTableView [난이도: 쉬움]
**패턴**: portfolio 루프 중 property 접근
**권장**: SUM/Aggregate 쿼리로 변경

### 🟡 MED (6건)

#### N1-M1: `rag_analysis/views.py:76` — DataBasket items 깊이 부족 [난이도: 쉬움]
**패턴**: `.prefetch_related('items')` 만 적용, `items.stock` 접근 시 N+1
**권장**: `.prefetch_related('items__stock')`

#### N1-M2: `rag_analysis/views.py:106` — 단일 조회 동일 문제 [난이도: 쉬움]
**권장**: `.prefetch_related('items__stock')`

#### N1-M3: `stocks/views_mvp.py:47-56` — MVP 리스트 [난이도: 중간]
**패턴**: `for stock in queryset:` 안에서 sector/industry/real_time_price 접근, select_related 없음
**권장**: `.select_related('sector', 'industry')` 또는 `.values()` 사용

#### N1-M4: `stocks/views_indicators.py:324-371` — symbols 루프 (Stock) [난이도: 중간]
**패턴**: `IndicatorComparisonView.post()`에서 symbol당 `Stock.objects.get(symbol=symbol)` 호출
**권장**: `Stock.objects.filter(symbol__in=symbols).in_bulk(field_name='symbol')`

#### N1-M5: `stocks/views_indicators.py:333-335` — symbols 루프 (DailyPrice) [난이도: 중간]
**패턴**: stock마다 `DailyPrice.objects.filter(stock=stock)` 호출
**권장**: `DailyPrice.objects.filter(stock__in=stocks)` 후 stock_id로 그룹핑

#### N1-M6: `serverless/views_admin.py:480-491` — categories.resolve_symbols() 루프 [난이도: 중간]
**패턴**: 각 카테고리마다 메서드 내부에서 추가 쿼리 가능성
**권장**: bulk resolve 또는 캐싱 (TTL 60s 등)

### 🟢 LOW (3건)

#### N1-L1: `users/views.py:975-987` — UserInterest 리스트
**상태**: 루프 안 FK 접근 없음, 직접 필드만 사용 → 현재 안전. 모니터링만 권장.

#### N1-L2: `chainsight/api/views.py:79-87` — edges 메모리 처리
**상태**: DB 쿼리 아님, in-memory loop → 안전.

#### N1-L3: `chainsight/api/views.py:391` — Stock.objects.filter(symbol__in=tickers)
**상태**: bulk lookup → 안전. 참고용 기록.

### 안전 (감사 결과 문제 없음)

- `stocks/views_eod.py:82-99` — `select_related('stock')` 적용됨
- `stocks/views.py`, `stocks/views_search.py`, `stocks/views_exchange.py`, `stocks/views_screener.py`, `stocks/views_market_movers.py`, `stocks/views_fundamentals.py`, `macro/views.py`, `sec_pipeline/views.py` — 적절한 prefetch/select_related 적용 또는 N+1 패턴 없음

---

## 상세 2: 인덱스 누락 (models)

### 🔴 HIGH (3건)

#### IDX-H1: `news/models.py:73` — `NewsArticle.published_at` 범위 쿼리 [난이도: 쉬움]
**호출 위치**: `news/api/views.py:95-98`, `:276-280` (filter + order_by 빈번)
**설명**: 복합 인덱스만 정의, 단일 `-published_at` 인덱스 없음. 대용량 뉴스 테이블 (100만+)에서 정렬 성능 저하
**권장**: `Meta.indexes`에 `models.Index(fields=['-published_at'])` 추가

#### IDX-H2: `stocks/models.py:757` — `EODSignal` JSONB 검색 [난이도: 중간]
**호출 위치**: `stocks/views_eod.py:72-78` (date + signals__contains + order_by composite_score)
**설명**: `Index(fields=['date', '-composite_score'])`는 존재하나 `signals__contains` JSONB 스캔이 병행됨. 매일 대시보드 호출에서 병목
**권장**: signal 카테고리를 별도 컬럼 또는 부분 인덱스(GIN)로 정규화 검토

#### IDX-H3: `stocks/models.py:137` — `DailyPrice.date` 범위 쿼리 [난이도: 높음]
**호출 위치**: `stocks/views.py:398-407` (date__lte + order_by -date)
**설명**: 기존 인덱스로 부분 커버되나 대용량 시계열에서 LIMIT 없이 호출되는 경우 우려
**권장**: 쿼리 패턴 분석 후 LIMIT 강제 + 인덱스 적중 EXPLAIN 검증

### 🟡 MED (4건)

#### IDX-M1: `serverless/models.py:274` — `MarketBreadth.date` 정렬 [난이도: 쉬움]
**호출 위치**: `serverless/views.py:765` (filter(date__gte=) + order_by('-date'))
**권장**: `Index(fields=['-date'])` 추가

#### IDX-M2: `news/models.py:344-352` — `SentimentHistory` 복합 인덱스 [난이도: 쉬움]
**호출 위치**: `news/api/views.py:135-138`
**설명**: symbol + date 단일 인덱스만 존재, 복합 쿼리에서 부분 스캔
**권장**: `Index(fields=['symbol', '-date'])` 복합 인덱스 추가

#### IDX-M3: `news/models.py:146` — `NewsArticle.importance_score` 복합 정렬 [난이도: 쉬움]
**설명**: 단일 인덱스만 존재, `published_at + importance_score` 정렬 시 메모리 정렬 발생
**권장**: `Index(fields=['-importance_score', '-published_at'])` 추가

#### IDX-M4: `news/models.py:667` — `NewsCollectionLog.executed_at + provider` [난이도: 쉬움]
**설명**: provider 단방향 인덱스만 존재, executed_at 범위 쿼리에서 인덱스 미사용
**권장**: `Index(fields=['executed_at', 'provider'])` 추가

### 🟢 LOW (4건)

#### IDX-L1: `serverless/models.py:367` — ScreenerPreset
**상태**: 기존 인덱스 충분, 조치 불필요

#### IDX-L2: `news/models.py:711` — AlertLog
**상태**: 기존 `Index(fields=['is_resolved', '-created_at'])` 적절

#### IDX-L3: `serverless/models.py:1303` — LLMExtractedRelation
**상태**: TTL 자동 정리로 데이터 크기 제한, 인덱스 충분

#### IDX-L4: `serverless/models.py:645` — ScreenerAlert
**상태**: 선택사항, `Index(fields=['user', '-created_at'])` 추가 시 미세 개선

---

## 상세 3: 느린 Serializer

### 🔴 HIGH (2건)

#### SER-H1: `stocks/serializers.py:205-306` — OverviewTabSerializer.get_dynamic_layers [난이도: 높음]
**패턴**: 6개 OneToOne/Reverse FK 접근 — `obj.category_signals.all()`, `obj.validation_news_summary`, `obj.sensitivity_profile`, `obj.growth_stage`, `obj.capital_dna`, `obj.narrative_tag`
**설명**: list 100개 × 6 = ~600 추가 쿼리. 코드 주석에도 TODO 명시됨
**권장**: ViewSet에서 `prefetch_related('category_signals', 'validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')` 적용

#### SER-H2: `stocks/serializers.py:398-409` — WatchListStockSerializer [난이도: 중간]
**패턴**: 각 종목마다 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()`
**설명**: watchlist 100개 → 101 쿼리
**권장**: 뷰에서 사전 계산하여 serializer context로 전달, 또는 latest_price 캐시 필드 도입

### 🟡 MED (3건)

#### SER-M1: `stocks/serializers.py:190-203` — get_korean_overview [난이도: 쉬움]
**패턴**: `obj.overview_ko` OneToOne 접근
**권장**: `select_related('overview_ko')` 적용

#### SER-M2: `serverless/serializers.py:121-137` — MarketMoverListSerializer [난이도: 중간]
**패턴**: `get_sector_alpha_display` 등 3개 메서드에서 매번 `IndicatorCalculator()` 인스턴스 생성
**설명**: 20 movers × 3 = 60회 인스턴스화
**권장**: 싱글톤 또는 module-level 인스턴스

#### SER-M3: `serverless/serializers.py:208-219` — MarketBreadthSerializer [난이도: 중간]
**패턴**: `get_signal_interpretation`에서 매번 `MarketBreadthService` 인스턴스 생성
**권장**: 싱글톤 또는 classmethod

### 🟢 LOW (1건)

#### SER-L1: `users/serializers.py:103-109` — PortfolioDetailSerializer.get_portfolio_weight
**패턴**: `self.context.get('total_portfolio_value', 0)` 의존
**권장**: 뷰에서 context 보장하도록 명시화 (기능 영향 미미)

---

## 상세 4: 페이지네이션 누락

### 글로벌

#### PAG-GLOBAL: `config/settings.py` — DEFAULT_PAGINATION_CLASS 미설정 [난이도: 쉬움]
**설명**: `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` 없음 → 기본 페이지네이션 없음
**권장**: `'rest_framework.pagination.PageNumberPagination'` 또는 `LimitOffsetPagination` 전역 설정 + `PAGE_SIZE = 50`

### 🔴 HIGH (4건)

#### PAG-H1: `stocks/views.py:75-100` — StockListAPIView [난이도: 높음]
**패턴**: `generics.ListAPIView`, 페이지네이션 없음
**설명**: Stock 테이블 수천 건 전체 직렬화
**권장**: `pagination_class = PageNumberPagination`

#### PAG-H2: `users/views.py:91-94` — Users.get [난이도: 높음]
**패턴**: `User.objects.all()` → `Response(serializer.data)` 직접 반환 (관리자 API)
**설명**: 사용자 수천 명 시 DDoS 취약
**권장**: Paginator 적용 또는 admin 전용 제한

#### PAG-H3: `news/api/views.py:50-110` — NewsViewSet [난이도: 높음]
**패턴**: `NewsArticle.objects.all().prefetch_related('entities')` 후 list 응답
**설명**: 뉴스 수만 건 전체 반환 시 메모리/네트워크 장애
**권장**: `pagination_class = PageNumberPagination`, `page_size=20`

#### PAG-H4: `news/api/views.py:95-98` — stock_news 액션 [난이도: 중간]
**패턴**: filter + `.distinct().order_by('-published_at')`, slice 없음
**설명**: 종목당 수백 건 반환 가능 + distinct() 성능 저하
**권장**: `[:50]` slice 또는 페이지네이션, distinct 제거 (prefetch_related로 대체)

### 🟡 MED (3건)

#### PAG-M1: `rag_analysis/views.py:74-92` — DataBasketListCreateView [난이도: 높음]
**패턴**: `filter(user=request.user).prefetch_related('items')` 후 전체 직렬화
**권장**: 사용자당 limit 또는 페이지네이션

#### PAG-M2: `validation/api/views.py:80-100` — ValidationSummaryView [난이도: 높음]
**패턴**: `CategorySignal.objects.filter(symbol=stock)` 전체 반환
**권장**: limit 또는 페이지네이션

#### PAG-M3: `serverless/views.py:36-100` — market_movers_api [난이도: 높음]
**패턴**: 일일 movers 전체 반환 (현재 30-60건)
**설명**: 현재는 작지만 확장 시 위험
**권장**: 하드 캡 또는 페이지네이션

### 🟢 LOW (2건)

#### PAG-L1: `chainsight/api/views.py:61-100` — ChainSightGraphView
**설명**: depth 최대 3으로 제한되어 있음
**권장**: depth 확대 대비 edge/node 하드 캡 설정

#### PAG-L2: `macro/views.py:25-100` — 대시보드 응답
**상태**: 응답 크기 고정 (FearGreed 등), 페이지네이션 불필요

---

## 우선순위 처리 가이드

### 즉시 (이번 스프린트)
1. **PAG-GLOBAL** — `DEFAULT_PAGINATION_CLASS` 전역 설정 (가장 적은 노력, 최대 효과)
2. **SER-H1** — OverviewTab dynamic_layers prefetch (이미 코드에 TODO 명시)
3. **N1-H1~H5** — validation/api/views.py 5개 루프 → bulk 쿼리

### 단기 (이번 달)
4. **PAG-H1~H4** — 4개 list 엔드포인트 페이지네이션
5. **SER-H2** — WatchList latest_price 캐싱
6. **IDX-H1** — NewsArticle published_at 단일 인덱스

### 중기 (다음 달)
7. **N1-H6, H7** — Portfolio aggregate 쿼리 전환
8. **IDX-M1~M4** — 복합 인덱스 4개 추가
9. **SER-M1~M3** — Serializer 인스턴스 캐싱

### 모니터링
10. LOW 이슈는 트래픽 증가 시 재평가

---

## 부록: 검사 범위

- **뷰 파일**: 17개 (stocks 9, users 1, news 1, macro 1, rag_analysis 1, serverless 1, validation 1, chainsight 1, sec_pipeline 1)
- **모델 파일**: 7개 (stocks, users, news, serverless, rag_analysis, sec_pipeline, graph_analysis)
- **Serializer 파일**: 10개
- **검사 방법**: Read 전체 + Grep 패턴 매칭 + queryset 정의 vs 사용처 대조
