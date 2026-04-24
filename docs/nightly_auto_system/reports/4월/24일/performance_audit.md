# API 성능 감사 보고서

- **감사일**: 2026-04-24
- **범위**: 17개 views 파일 + 관련 serializers(10개) / models(7개)
- **대상 앱**: stocks, users, news, macro, rag_analysis, serverless, validation, chainsight, sec_pipeline, graph_analysis
- **방법**: 정적 분석 — N+1 쿼리, 인덱스 누락, Serializer 추가 쿼리, 페이지네이션 미설정
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 1. 요약 (이슈 수 by 심각도)

| 심각도 | 개수 | 주요 패턴 |
|--------|-----|----------|
| **HIGH / CRITICAL** | 12 | List endpoint의 루프 내 FK 조회, 페이지네이션 미설정, SerializerMethodField DB 쿼리 |
| **MED** | 14 | M2M `all()` 후 `in` 체크, 복합 인덱스 누락, `.count()` 중복 호출, 수동 페이지네이션 표준 미준수 |
| **LOW** | 7 | 단일 인덱스 권장, 소규모 데이터 리스트 페이지네이션 |
| **합계** | **33** | |

### 카테고리별 분포

| 카테고리 | HIGH | MED | LOW | 합계 |
|----------|------|-----|-----|------|
| N+1 쿼리 (views) | 4 | 3 | 1 | 8 |
| 인덱스 누락 (models) | 2 | 5 | 3 | 10 |
| 느린 Serializer | 4 | 2 | 0 | 6 |
| 페이지네이션 누락 | 2 | 4 | 3 | 9 |

### 우선순위 Top 7 (즉시 조치)

1. **NewsViewSet 페이지네이션 미설정** (`news/api/views.py:42`) — 수십만 건 기사 전체 반환 위험
2. **StockListAPIView 페이지네이션 미설정** (`stocks/views.py:75`) — 수천 개 종목 전체 반환
3. **WatchListStockSerializer N+1** (`stocks/serializers.py:376-410`) — 50개 종목 기준 150쿼리
4. **MetricDefinition 루프 조회** (`validation/api/views.py:204`) — 25-30회 추가 쿼리
5. **DailyPrice 단건 조회 반복** (`rag_analysis/views.py:232-336`) — data_type 수만큼 반복
6. **NewsArticle.llm_analyzed 복합 인덱스 누락** (`news/models.py:158`) — LLM 분석 대기열 스캔 저하
7. **OverviewTabSerializer 동적 레이어 6 OneToOne** (`stocks/serializers.py:205-307`) — 상세 페이지마다 +6 쿼리

---

## 2. 상세 이슈

## 2.1 N+1 쿼리 (views)

### [HIGH-N1] news/api/views.py:329-343 — trending 뉴스의 심볼별 기사 재조회

```python
for item in trending_data:
    symbol = item['symbol']
    recent_articles = NewsArticle.objects.filter(
        entities__symbol=symbol,
        published_at__gte=from_date,
    ).distinct().order_by('-published_at')[:3]
    results.append({...})
```

- **문제**: trending 20개 종목마다 별도 쿼리 발생 → 최대 20+ 쿼리
- **권장**: `symbol__in=[...]` 한 번에 받아 Python에서 그룹핑, 또는 `Prefetch`로 pre-slice
- **심각도**: HIGH / **난이도**: 중간

### [HIGH-N2] stocks/views_indicators.py:324-371 — 심볼 리스트 루프에서 Stock + DailyPrice 각각 조회

```python
for symbol in symbols:
    stock = Stock.objects.get(symbol=symbol.upper())
    prices = DailyPrice.objects.filter(stock=stock)[:N]
```

- **문제**: 비교 지표 엔드포인트에서 N개 심볼당 2쿼리
- **권장**: `Stock.objects.filter(symbol__in=upper)` 후 dict, `DailyPrice.objects.filter(stock_id__in=...)` 1회 조회 후 그룹핑
- **심각도**: HIGH / **난이도**: 중간

### [HIGH-N3] validation/api/views.py:204-208 — MetricDefinition 반복 단건 조회

```python
for mc in metric_codes:
    md = MetricDefinition.objects.filter(pk=mc).first()
```

- **문제**: 25-30개 지표마다 개별 쿼리
- **권장**: `{md.pk: md for md in MetricDefinition.objects.filter(pk__in=metric_codes)}` 1회 + dict 조회
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-N4] rag_analysis/views.py:232-336 — data_type 루프에서 Stock/Price/재무 반복 조회

```python
for data_type in data_types:
    if data_type == 'overview':
        stock = Stock.objects.filter(symbol=symbol).first()
    elif data_type == 'price':
        latest = DailyPrice.objects.filter(stock__symbol=symbol).order_by('-date').first()
    elif data_type in ('financial_summary', 'financial_full'):
        income = IncomeStatement.objects.filter(...)
        balance = BalanceSheet.objects.filter(...)
```

- **문제**: 같은 심볼에 대해 data_types 개수만큼 중복 조회 (overview/price/financial 각 분기)
- **권장**: 루프 밖에서 모든 필요한 데이터를 한번에 프리로드하고 루프 안에서는 조립만
- **심각도**: HIGH / **난이도**: 중간

### [MED-N5] users/views.py:206, :234 — M2M `all()` 후 `in` 체크

```python
if stock in user.favorite_stock.all():
if stock not in user.favorite_stock.all():
```

- **문제**: 전체 favorite 목록을 쿼리셋으로 로드 후 in 검사
- **권장**: `user.favorite_stock.filter(pk=stock.pk).exists()`
- **심각도**: MED / **난이도**: 쉬움

### [MED-N6] validation/api/views.py:149-154 — `.count()` 중복 쿼리

```python
peers = Stock.objects.filter(symbol__in=peer_symbols).order_by('-market_capitalization')
leader = peers.first()
if leader and leader.symbol == stock.symbol and peers.count() > 1:
    leader = peers[1]
```

- **문제**: `peers.first()` + `peers.count()` + `peers[1]` → 3회 쿼리 평가
- **권장**: `peers_list = list(peers)` 한 번 평가 후 인덱스/len() 접근
- **심각도**: MED / **난이도**: 쉬움

### [LOW-N7] stocks/views_mvp.py:47-56 — 단순 속성 접근 루프

- **상태**: 현재 FK 접근은 없어 N+1 미발생. 다만 컬럼 추가 시 위험.
- **권장**: `queryset.values('symbol', 'stock_name', ...)` 로 교체 시 안전.
- **심각도**: LOW / **난이도**: 쉬움

### [MED-N8] news/api/views.py 전역 — 심볼별 엔티티 조회 시 prefetch 미활용

- **문제**: ViewSet 레벨 `prefetch_related('entities')`는 있으나, 개별 액션에서 `NewsEntity.objects.filter(symbol=...).select_related('news')`로 재조회 (line ~322-327, ~252-255)
- **권장**: entities 프리페치된 상태에서 파이썬 필터링, 또는 최초 쿼리를 `annotate(entity_count=Count('entities', filter=Q(entities__symbol=...)))` 패턴으로 통합
- **심각도**: MED / **난이도**: 중간

---

## 2.2 인덱스 누락 (models)

### [HIGH-IDX1] news/models.py:158-161 — `NewsArticle.llm_analyzed` + `published_at` 복합 인덱스 부재

- **현재**: `llm_analyzed`는 단독 `db_index=True`만 있음
- **사용**: `news/api/views.py:1544, 1548, 1828, 1832` 에서 `filter(llm_analyzed=False).order_by('-published_at')` 반복
- **권장**: `Meta.indexes`에 `Index(fields=['llm_analyzed', '-published_at'])` 추가
- **심각도**: HIGH / **난이도**: 쉬움 (1 migration)

### [HIGH-IDX2] stocks/models.py — `DailyPrice.created_at` 인덱스 부재

- **현재**: `BasePriceData.created_at = DateTimeField(auto_now_add=True)` — 인덱스 없음
- **사용**: `stocks/views.py:146-148, 407, 421` 등 시계열 조회/수집 로그 추적
- **권장**: `Index(fields=['-created_at'])` 또는 복합 인덱스. (stock+date 복합은 이미 있으므로 created_at은 주로 운영/백필용)
- **심각도**: HIGH (빈도 높은 테이블) / **난이도**: 쉬움

### [MED-IDX3] stocks/models.py:25 — `Stock.currency` 인덱스 부재

- **사용**: `stocks/views.py:95`, `stocks/views_mvp.py:33-35`
- **권장**: `db_index=True` 또는 `(currency, sector)` 복합
- **심각도**: MED / **난이도**: 쉬움

### [MED-IDX4] users/models.py:261 — `UserInterest.created_at` 인덱스 부재

- **사용**: `users/views.py:967` — `filter(user=...).order_by('-created_at')`
- **권장**: `Index(fields=['user', '-created_at'])` 복합
- **심각도**: MED / **난이도**: 쉬움

### [MED-IDX5] news/models.py:432-437 — `DailyNewsKeyword` 역순 복합 인덱스 부재

- **현재**: `Index(fields=['-date', 'status'])` 있음
- **사용**: `news/services/market_feed.py:84, 89`, `news/api/views.py:549-556` 에서 `filter(status='completed').order_by('-date')` 사용
- **권장**: `Index(fields=['status', '-date'])` 추가 — status-first 쿼리 대응
- **심각도**: MED / **난이도**: 쉬움

### [MED-IDX6] stocks/models.py:258+ — 재무제표 복합 인덱스 부재

- **현재**: `fiscal_quarter`에 `db_index=True` 있음
- **사용**: `stocks/views.py:639, 713, 785` — `order_by('-fiscal_year', '-fiscal_quarter')`
- **권장**: `Index(fields=['stock', '-fiscal_year', '-fiscal_quarter'])` 복합 3종(BalanceSheet/IncomeStatement/CashFlowStatement)
- **심각도**: MED / **난이도**: 쉬움 (3개 migration 또는 1개로 묶음)

### [MED-IDX7] serverless/models.py:221-226 — `StockKeyword.expires_at` 복합 인덱스 부재

- **현재**: `status`에 `db_index=True` 있음
- **사용**: TTL 정리 배치 `filter(expires_at__lt=now)` (대량 scan)
- **권장**: `Index(fields=['expires_at', 'status'])` 추가
- **심각도**: MED / **난이도**: 쉬움

### [LOW-IDX8] serverless/models.py:103-110 — `MarketMover` 역순 인덱스

- **현재**: `Index(fields=['date', 'mover_type'])` 있음
- **사용**: 대부분 역순 `-date` 조회
- **권장**: 성능 모니터링 후 필요 시 역순 추가
- **심각도**: LOW / **난이도**: 쉬움

### [LOW-IDX9] sec_pipeline/models.py:251 — `FilingProcessLog.symbol` 단독 인덱스

- **현재**: 복합 `(symbol, stage, -started_at)`만 존재 — 복합의 leftmost prefix로 symbol 커버됨
- **권장**: 추가 인덱스 불필요. 모니터링만.
- **심각도**: LOW

### [LOW-IDX10] graph_analysis/models.py — 현재 인덱스 충분

- `CorrelationEdge.is_anomaly` + `-date` 복합 존재, `GraphMetadata.status` + `-date` 존재.
- 이상 없음. 단, 대용량 상관관계 Edge 증가 시 파티셔닝 고려 필요.

---

## 2.3 느린 Serializer

### [HIGH-S1] stocks/serializers.py:376-410 — WatchListStockSerializer 가격 조회

```python
def get_latest_price(self, obj):
    return DailyPrice.objects.filter(stock=obj).order_by('-date').first()

def get_chart_data(self, obj):
    return DailyPrice.objects.filter(stock=obj).order_by('-date')[:7]
```

- **문제**: `many=True` 직렬화 시 종목당 2쿼리 (50종목 → 150+쿼리)
- **권장**:
  - 뷰 쿼리셋에 `.prefetch_related(Prefetch('daily_prices', queryset=DailyPrice.objects.order_by('-date')[:7]))`
  - 또는 최신가 `annotate(Subquery(...))`
- **심각도**: HIGH / **난이도**: 중간

### [HIGH-S2] stocks/serializers.py:205-307 — OverviewTabSerializer 동적 레이어

- **문제**: 주식 상세 응답에서 6개 OneToOne(`validation_news_summary`, `sensitivity_profile`, `growth_stage`, `capital_dna`, `narrative_tag`) + `category_signals.all()` reverse FK 접근 → 7+ 쿼리
- **권장**: StockDetailView 쿼리셋에 `select_related('validation_news_summary', 'sensitivity_profile', 'growth_stage', 'capital_dna', 'narrative_tag')` + `prefetch_related('category_signals')`
- **코멘트**: 파일 내부 TODO 주석에서도 최적화 필요성 언급됨 (라인 208 인근)
- **심각도**: HIGH / **난이도**: 중간

### [HIGH-S3] serverless/serializers.py:120-137 — MarketMoverListSerializer 파생 필드 3종

- **문제**: `get_sector_alpha_display`, `get_etf_sync_display`, `get_volatility_pct_display` 모두 `IndicatorCalculator` 호출 → list 100개 × 3 = 300회 계산 (DB/캐시 접근 포함)
- **권장**: 
  - (a) Baking 단계에서 미리 계산 후 컬럼 저장
  - (b) 뷰에서 1회 벌크 계산 후 serializer context에 주입
- **심각도**: HIGH / **난이도**: 중간~높음

### [HIGH-S4] news/api/views.py:89-94 — NewsViewSet 엔티티 재조회

- **문제**: viewset 레벨 `prefetch_related('entities')`와 별개로 action에서 `NewsEntity.objects.filter(symbol=...).select_related('news')`로 news 재쿼리
- **권장**: prefetch 활용 또는 한 쿼리로 합치기
- **심각도**: HIGH / **난이도**: 중간

### [MED-S5] users/serializers.py:95-109 — PortfolioDetailSerializer weight 계산

- **문제**: `get_portfolio_weight` 가 context `total_portfolio_value`에 의존. 뷰에서 파이썬 루프로 총합 계산 (`users/views.py:402`)
- **권장**: `portfolios.aggregate(Sum('total_value'))` 한 번으로 대체
- **심각도**: MED / **난이도**: 쉬움

### [MED-S6] rag_analysis/serializers.py:24-51, 68-69 — Nested Lazy Loading

- **문제**: `items = BasketItemSerializer(many=True)`, `messages = AnalysisMessageSerializer(many=True)`, `basket = DataBasketSerializer()` — 뷰에서 prefetch 보장 없으면 N+1
- **권장**: `DataBasketListCreateView`, `AnalysisSessionListCreateView` 에 `prefetch_related('items', 'messages')`, `select_related('basket')`
- **심각도**: MED / **난이도**: 쉬움

---

## 2.4 페이지네이션 누락

### 전제: 프로젝트 설정 상태

- **config/settings.py:332-340**: `DEFAULT_PAGINATION_CLASS` **미지정**
- 결과: ListAPIView / ReadOnlyModelViewSet 에서 `pagination_class` 를 명시하지 않으면 **전체 리스트가 한 번에 직렬화**됨
- 권장(공통): `PageNumberPagination` 또는 `CursorPagination`을 settings 기본값으로 지정 + per-view override

### [CRITICAL-P1] news/api/views.py:42-104 — NewsViewSet

```python
class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.all().prefetch_related('entities')
```

- **문제**: `pagination_class` 미지정. NewsArticle은 수십만 건 가능
- **권장**: `pagination_class = PageNumberPagination`; page_size 50
- **심각도**: CRITICAL / **난이도**: 쉬움 (1줄)

### [HIGH-P2] stocks/views.py:75-105 — StockListAPIView

- **문제**: Stock 수천 건 이상 전체 반환
- **권장**: PageNumberPagination
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-P3] stocks/views.py:196 — StockSearchAPIView

- **문제**: 전체 매칭 결과 `many=True` 반환 (1000+ 건 가능)
- **권장**: page_size 20 + 검색 필드 인덱스 확인
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-P4] stocks/views.py:268, 271 — StockChartDataAPIView

- **문제**: 최대 5년 일봉(≈1260건) 또는 전체 `price_data` 반환. 데이터 타입상 페이지네이션 대신 **기간 필터 강제**가 적합
- **권장**: `start`/`end` 파라미터 필수화, 최대 범위 가드
- **심각도**: HIGH / **난이도**: 중간 (API 계약 변경)

### [HIGH-P5] stocks/views_mvp.py:59 — StockMVPListView

- **문제**: 500+ 종목 반환 가능
- **권장**: pagination_class 추가
- **심각도**: HIGH / **난이도**: 쉬움

### [HIGH-P6] stocks/views_screener.py — Screener 뷰들 (다수)

- **문제**: ScreenedStockSerializer(stocks, many=True) 패턴에서 100-1000건 반환 가능
- **권장**: page_size 25-50
- **심각도**: HIGH / **난이도**: 쉬움

### [MED-P7] stocks/views_exchange.py:62 — IndexQuotesView

- **문제**: 인덱스 50+건 반환. 수용 가능하지만 표준화 필요
- **심각도**: MED / **난이도**: 쉬움

### [MED-P8] users/views.py:91 — Users GET

- **문제**: 사용자 목록 전체 반환 (관리 목적으로 보이나 확인 필요)
- **권장**: admin 전용이면 페이지네이션 + 권한 점검
- **심각도**: MED / **난이도**: 쉬움

### [MED-P9] 수동 페이지네이션 (DRF 표준 미준수) — 일관성

| 파일:라인 | 뷰 |
|-----------|-----|
| users/views.py:580-620 | WatchlistListCreateView |
| users/views.py:792-840 | WatchlistStocksView |
| rag_analysis/views.py:764-833 | UsageHistoryView |

- **문제**: Django `Paginator`로 수동 처리 → 응답 스키마 불일관
- **권장**: DRF `PageNumberPagination` 으로 통일
- **심각도**: MED / **난이도**: 중간

### [LOW-P10] 사용자별 소규모 리스트

| 파일:라인 | 뷰 | 예상 크기 |
|-----------|-----|-----------|
| users/views.py:189 | UserFavorites | <100 |
| users/views.py:258 | PortfolioListCreateView | <100 |
| users/views.py:407 | PortfolioDetailTableView | <100 |
| rag_analysis/views.py:74 | DataBasketListCreateView | <50 |
| rag_analysis/views.py:434 | AnalysisSessionListCreateView | <100 |

- **권장**: 단기적으로 무시 가능. 설계상 "사용자별 소규모"라는 전제가 깨지면 조치.
- **심각도**: LOW / **난이도**: 쉬움

---

## 3. 예상 효과 (추정)

| 이슈 영역 | 현 상태 | 개선 후 | 감소율 |
|----------|-----|---------|--------|
| NewsViewSet 전체 반환 | ~수만 행 직렬화 | 50행 | 메모리/응답시간 99%↓ |
| StockListAPIView | 5000+ 행 | 20-50행 | 99%↓ |
| WatchListStockSerializer (50종목) | ~150 쿼리 | 2-3 쿼리 | 98%↓ |
| OverviewTabSerializer | +7 쿼리/상세 | +1 쿼리/상세 | 85%↓ |
| MetricDefinition 반복 조회 | N+1 (25-30) | 1 쿼리 | 96%↓ |
| llm_analyzed 필터+정렬 | 풀스캔/파일정렬 | 인덱스 레인지 | 쿼리 P95 수 백ms→ms |

---

## 4. 권장 로드맵

**Phase 1 (즉시, 1-2일)** — 외부 노출 엔드포인트 안전화
- P1 NewsViewSet pagination
- P2 StockListAPIView pagination
- P3 StockSearchAPIView pagination
- N3 MetricDefinition 벌크 조회

**Phase 2 (1주일)** — 주요 화면 성능 체감
- S1 WatchListStockSerializer prefetch
- S2 OverviewTabSerializer select_related
- IDX1 llm_analyzed 복합 인덱스
- IDX2 DailyPrice.created_at 인덱스
- N1/N2/N4 루프 쿼리 재구성

**Phase 3 (2-4주)** — 표준화 / 모니터링
- 수동 페이지네이션 → DRF 표준 통일 (P9)
- 재무제표 복합 인덱스 (IDX6)
- Screener 뷰 페이지네이션 (P6)
- DEFAULT_PAGINATION_CLASS 글로벌 적용 가이드 수립

**Phase 4 (백로그)**
- LOW 항목 재검토 (운영 메트릭 기반)
- Serializer 파생 필드 캐시 전략 (S3)

---

## 5. 감사 한계 및 주의사항

- 정적 분석 한계: 실제 쿼리 카운트는 `django-debug-toolbar` / `django-silk` / APM으로 확인 권장
- FK는 기본 인덱스가 있으므로 본 보고서에서는 제외
- Celery 태스크(`tasks.py`)는 본 감사 범위 제외 — 별도 infra 감사에서 다룰 것
- `graph_analysis/views.py`는 API 미구현 상태(보류)로 실제 호출 경로 없음 → 실제 위험도 낮음

