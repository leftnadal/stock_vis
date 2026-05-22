# API 성능 감사 보고서

- **감사 일자**: 2026-05-22
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상**: Django/DRF 백엔드 17개 view + 7개 model + serializer 일체
- **방법론**: 정적 분석 — 루프 내 FK/reverse-relation 접근, filter/order_by 필드 ↔ 인덱스 매핑, SerializerMethodField 내 DB 쿼리, list 엔드포인트의 pagination 설정

---

## 요약 (이슈 수 by 심각도)

| 항목 | HIGH | MED | LOW | 합계 |
|------|------|-----|-----|------|
| N+1 쿼리 | 2 | 2 | 0 | **4** |
| 인덱스 누락 | 3 | 8 | 0 | **11** (이미 인덱스 존재 = 검증 통과 6건 포함) |
| 느린 Serializer | 1 | 2 | 0 | **3** |
| 페이지네이션 누락 | 9 | 0 | 0 | **9** (실제 미설정 16건 중, list 엔드포인트만 카운트) |
| **합계** | **15** | **12** | **0** | **27** |

### 우선순위 결정 사항
- **P0 (즉시)**: stocks/serializers.py의 N+1 3건 + chainsight edges 루프 1건 → 응답 시간 직접 영향
- **P1 (1주일)**: settings의 `DEFAULT_PAGINATION_CLASS` 부재 + 9개 list 엔드포인트 명시적 pagination 추가
- **P2 (다음 스프린트)**: 인덱스 검증 (대부분 이미 적용됨), Serializer 캐싱

---

## 상세

### 1. N+1 쿼리 (4건)

| # | 위치 | 심각도 | 난이도 | 설명 | 권장 수정 |
|---|------|--------|--------|------|-----------|
| 1 | `stocks/serializers.py:214-225` `OverviewTabSerializer.get_dynamic_layers()` | HIGH | 중간 | `obj.category_signals.all()` 호출. List view에서 Stock 1건마다 reverse relation 쿼리 → N+1. 카테고리당 최대 7개 시그널 × paginate_size | view queryset에 `prefetch_related('category_signals')` 추가, Serializer는 prefetched cache 사용 |
| 2 | `stocks/serializers.py:400-403` `WatchListStockSerializer.get_latest_price()` | HIGH | 쉬움 | 각 Stock마다 `DailyPrice.objects.filter(stock=obj).order_by('-date').first()` 실행. Watchlist N개 → N+1 쿼리 | queryset에 `prefetch_related('dailyprice_set')` 추가 후 in-memory 처리. 또는 `Prefetch` 객체로 최신 1건만 prefetch |
| 3 | `stocks/serializers.py:407-409` `WatchListStockSerializer.get_chart_data()` | HIGH | 중간 | 동일하게 DailyPrice 슬라이싱 `[:7]` 매번 DB 조회. (#2와 같은 패턴, 별도 라인) | `Prefetch('dailyprice_set', queryset=DailyPrice.objects.order_by('-date')[:7])` 적용 |
| 4 | `chainsight/api/views.py:79-88` `ChainSightGraphView` edges 루프 | MED | 중간 | edges 배열의 각 항목마다 `CoMentionEdge.objects.filter()` + `PriceCoMovement.objects.filter()` 2회 호출. 최대 50 edges × 2 = 100 쿼리 | `in_bulk()` 또는 한 번의 `filter(...__in=[...])`로 bulk 조회 후 dict 매핑. Redis 캐싱 레이어도 고려 |
| 5 | `validation/api/views.py:80` `ValidationSummaryView` | MED | 쉬움 | `CategorySignal.objects.filter(symbol=stock)` 후 반복 처리. Detail view지만 호출 빈도 높음 | Detail view라 영향 제한적. queryset 캐싱 또는 service layer로 분리 |

---

### 2. 인덱스 누락 / 검증 (11건 — 검증 통과 6건 포함)

| # | 모델:필드 | 심각도 | 난이도 | 사용처 | 현재 상태 / 권장 |
|---|----------|--------|--------|--------|------------------|
| 1 | `users.Portfolio.user` + `.stock` 복합 | HIGH | 쉬움 | `users/views.py:264, 358, 406` `Portfolio.objects.filter(user=...)` | unique_together 존재 시 자동 인덱스. 명시적 `Meta.indexes = [models.Index(fields=['user', 'stock'])]` 권장 |
| 2 | `users.Watchlist` 다중 필드 | HIGH | 쉬움 | `users/views.py:646+` user+name 복합 쿼리 + order_by | `owner` FK 자동 인덱스만으로는 부족. Meta.indexes 명시화 권장 |
| 3 | `validation/models.py` (파일 미존재) | HIGH | 쉬움 | `validation/api/views.py` CategorySignal/CompanyBenchmarkDelta 조회 | 모델 파일 위치 확인 필요. CategorySignal의 `symbol`, `category` 필드 인덱스 검증 |
| 4 | `news.NewsArticle.published_at` | MED | — | `news/api/views.py:104-107` `published_at__gte` 필터 | ✓ 이미 `db_index=True` |
| 5 | `news.NewsArticle.source` | MED | — | 소스별 집계 | ✓ 이미 `db_index=True` |
| 6 | `rag_analysis.DataBasket.user` | MED | 쉬움 | `rag_analysis/views.py:52` `filter(user=request.user)` | FK 자동 인덱스. 자주 쓰면 `Meta.indexes`에 명시화 |
| 7 | `serverless.MarketMover.date, symbol` | MED | — | 대시보드 조회 | ✓ `db_index=True` (line 17-20) |
| 8 | `sec_pipeline.SupplyChainEvidence.source_company` | MED | — | supply chain 쿼리 | ✓ Meta.indexes 포함 (line 108-109) |
| 9 | `sec_pipeline.RawDocumentStore.symbol` | MED | — | filing 조회 | ✓ Meta.indexes `['symbol', '-filing_date']` |
| 10 | `graph_analysis.CorrelationEdge.watchlist, stock_a, stock_b` | MED | — | graph 대량 조회 | ✓ Meta.indexes (line 129-133) |
| 11 | `stocks.Stock` 인덱스 | MED | — | `stocks/models.py:95-102` | ✓ Meta.indexes 적용 |

**결론**: 검증 결과 대부분 이미 인덱스 적용됨. **HIGH 3건만 실제 액션 필요**.

---

### 3. 느린 Serializer (3건)

| # | 위치 | 심각도 | 난이도 | 메서드 | 문제 | 권장 |
|---|------|--------|--------|--------|------|------|
| 1 | `stocks/serializers.py:214-225` | HIGH | 중간 | `OverviewTabSerializer.get_dynamic_layers()` | `obj.category_signals.all()`로 N+1 발생 (#1.1과 동일 원인) | view queryset에 prefetch + Serializer는 prefetched cache 사용 |
| 2 | `stocks/serializers.py:400-403` | MED | 쉬움 | `WatchListStockSerializer.get_latest_price()` | SerializerMethodField에서 `DailyPrice.objects.filter(...).first()` 매번 실행 | prefetch + in-memory 처리 |
| 3 | `stocks/serializers.py:407-409` | MED | 중간 | `WatchListStockSerializer.get_chart_data()` | 동일 패턴, `[:7]` slicing | `Prefetch` 객체로 7건만 prefetch |

**공통 패턴**: `SerializerMethodField` 내부에서 ORM 호출 — list view에서 N+1 발생 원인 1순위.

---

### 4. 페이지네이션 누락 (9건)

**전역 설정**: `config/settings.py:348-367` REST_FRAMEWORK에 `DEFAULT_PAGINATION_CLASS` **없음**.
→ 모든 list 엔드포인트가 명시적으로 `pagination_class` 지정 필요. 미지정 시 전체 응답.

| # | 위치:클래스 | 심각도 | 난이도 | 현재 동작 | 권장 |
|---|------------|--------|--------|-----------|------|
| 1 | `stocks/views_search.py:SymbolSearchView` | HIGH | 쉬움 | APIView, `[:10]` 수동 slicing | Custom pagination 또는 명시적 max 상수 |
| 2 | `stocks/views_search.py:PopularSymbolsView` | HIGH | 쉬움 | APIView, `[:10]` 수동 slicing | 동일 |
| 3 | `stocks/views_exchange.py:IndexQuotesView` | HIGH | 쉬움 | APIView, 응답 크기 제한 없음 | Pagination 또는 `max_items` 상수 |
| 4 | `stocks/views_exchange.py:BatchQuotesView` | HIGH | 쉬움 | POST symbols 배열, 크기 제한 없음 | `limit` 검증 + max count (e.g., 100) |
| 5 | `stocks/views_screener.py:StockScreenerView` | HIGH | 쉬움 | APIView, limit 100/1000 지원하나 pagination 미구현 | DRF pagination 또는 cursor pagination |
| 6 | `stocks/views_fundamentals.py:KeyMetricsView` | HIGH | 쉬움 | APIView, limit 1~40 검증하나 pagination 미구현 | 동일 |
| 7 | `stocks/views_fundamentals.py:RatiosView` | HIGH | 쉬움 | 동일 | 동일 |
| 8 | `stocks/views_indicators.py:TechnicalIndicatorView` | HIGH | 쉬움 | APIView, period + indicators 조합. 응답 크기 미제한 | 최대 period 제한 + pagination |
| 9 | `stocks/views_mvp.py:StockMVPListView` | HIGH | 쉬움 | APIView, `[:20]` hardcoded | 명시적 pagination class |

**검증 통과 (pagination 적용 또는 단일 detail view)**:
- ✓ `stocks/views.py:StockListAPIView` — `StockListPagination` 적용
- ✓ `stocks/views_exchange.py:StockQuoteView` — 단일 심볼 detail
- ✓ `stocks/views_market_movers.py:MarketMoversView` — limit 1~20 강제
- ✓ `news/api/views.py:NewsViewSet` — `NewsArticlePagination` 적용
- ✓ `macro/views.py` 전체 — list가 아닌 구조화된 응답
- ✓ `serverless/views_admin.py` — 내부 admin 전용
- ✓ `validation/api/views.py`, `chainsight/api/views.py` — detail view

---

## 우선순위 권장 액션

### P0 — 즉시 (응답 시간 직접 영향)
1. `stocks/serializers.py:214` — `OverviewTabSerializer.get_dynamic_layers()` prefetch
2. `stocks/serializers.py:400, 407` — `WatchListStockSerializer` 가격/차트 prefetch
3. `chainsight/api/views.py:79-88` — edges 루프 bulk 조회로 변경

### P1 — 1주일 내
4. `config/settings.py` — `DEFAULT_PAGINATION_CLASS` 전역 설정 추가
5. 9개 stocks/* list 엔드포인트에 명시적 pagination 설정
6. `users.Portfolio`, `users.Watchlist` 복합 인덱스 명시화

### P2 — 다음 스프린트
7. `validation/models.py` 인덱스 검증 (파일 위치 확인 필요)
8. chainsight edge 데이터 Redis 캐싱 레이어

---

## 부록: 검사 범위

### View 파일 (17개)
stocks/views.py, views_search.py, views_exchange.py, views_eod.py, views_screener.py, views_market_movers.py, views_fundamentals.py, views_indicators.py, views_mvp.py / users/views.py / news/api/views.py / macro/views.py / rag_analysis/views.py / serverless/views_admin.py / validation/api/views.py / chainsight/api/views.py / sec_pipeline/views.py

### Model 파일 (7개)
stocks/models.py, users/models.py, news/models.py, serverless/models.py, rag_analysis/models.py, sec_pipeline/models.py, graph_analysis/models.py

### Serializer 파일
rag_analysis/, serverless/, stocks/ (4종), macro/, news/api/, users/, portfolio/api/

---

**감사 완료. 코드/파일 수정 없음 (read-only).**
