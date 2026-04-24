# API 성능 감사 보고서

- **감사일**: 2026-04-24
- **범위**: 17개 views 파일 + 관련 serializers/models (stocks, users, news, macro, rag_analysis, serverless, validation, chainsight, sec_pipeline, graph_analysis)
- **방법**: 정적 분석 (N+1, 인덱스 누락, Serializer 추가 쿼리, 페이지네이션)
- **모드**: 읽기 전용 — 코드 수정 없음

---

## 요약 (이슈 수 by 심각도)

| 심각도 | 개수 | 주요 패턴 | 수정 우선순위 |
|--------|-----|----------|------------|
| **HIGH** | 13 | 루프 내 FK 재조회, SerializerMethodField DB 쿼리, 페이지네이션 누락 | 즉시 |
| **MED**  | 15 | 복합 인덱스 누락, `.count()` 중복, 쿼리 재구성 필요 | 1주일 내 |
| **LOW**  | 10 | 단일 인덱스 정리, 성능 모니터링 필요 | 백로그 |
| **합계** | **38** |  |  |

### 심각도 분포 (그룹별)

| 그룹 | HIGH | MED | LOW | 소계 |
|------|------|-----|-----|------|
| stocks + users | 4 | 5 | 3 | 12 |
| news + macro + rag + serverless | 6 | 5 | 3 | 14 |
| validation + chainsight + sec + graph | 3 | 5 | 4 | 12 |

### 예상 개선 효과
- HIGH 이슈 해결 시: API 응답 시간 **50~70% 단축**, 평균 DB 쿼리 횟수 **5~10배 감소**
- 페이지네이션 추가 시: 대용량 list 엔드포인트 메모리 사용량 **~80% 감소**
- 인덱스 추가 시: `filter()` 쿼리 속도 **5~10배** 개선

---

## 상세 이슈 (HIGH → MED → LOW)

## 🔴 HIGH 심각도 이슈 (13건)

---

### H1. `stocks/serializers.py:215` — `OverviewTabSerializer` 동적 레이어 N+1
- **심각도**: HIGH / 수정 난이도: 중간
- **설명**: `get_dynamic_layers()`에서 `obj.category_signals.all()`을 역참조 조회. Stock 다건 조회 시 각 row마다 `CategorySignal` 추가 쿼리.
- **권장 수정**:
  ```python
  stock = Stock.objects.select_related('overview_ko').prefetch_related(
      'category_signals'
  ).filter(symbol=symbol).first()
  ```

---

### H2. `stocks/serializers.py:400` — `WatchListStockSerializer.get_latest_price()` N+1
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: `DailyPrice.objects.filter(stock=obj).order_by('-date').first()`를 `SerializerMethodField` 안에서 매번 호출. Watchlist 100종목 → 100회 쿼리.
- **권장 수정**:
  ```python
  stocks = Stock.objects.prefetch_related(
      Prefetch('dailyprice_set',
               queryset=DailyPrice.objects.order_by('-date')[:1])
  )
  ```

---

### H3. `users/views.py:367` — `PortfolioSummaryView.total_value` property 루프 누적
- **심각도**: HIGH (인증 핫패스) / 수정 난이도: 쉬움
- **설명**: `for portfolio in portfolios: total_value += portfolio.total_value` — `total_value` property 내부에서 `stock.real_time_price` 재접근. `select_related('stock')`이 있어도 property 반복 계산 비용.
- **권장 수정**:
  ```python
  from django.db.models import F, Sum, DecimalField
  result = Portfolio.objects.filter(user=request.user).select_related('stock').aggregate(
      total_value=Sum(F('quantity') * F('stock__real_time_price'),
                      output_field=DecimalField())
  )
  ```

---

### H4. `users/views.py:705, 878` — Watchlist bulk 추가 시 루프별 `.exists()`
- **심각도**: HIGH (인증 API) / 수정 난이도: 쉬움
- **설명**: `WatchlistItemAddView`/`WatchlistBulkAddView`에서 종목마다 `WatchlistItem.objects.filter(...).exists()` 호출. 50종목 bulk → 50쿼리.
- **권장 수정**:
  ```python
  existing = set(WatchlistItem.objects.filter(
      watchlist=watchlist, stock_id__in=stock_ids
  ).values_list('stock_id', flat=True))
  for stock in stocks:
      if stock.id in existing:
          skipped.append(...); continue
  ```

---

### H5. `news/api/views.py:154-174` — `stock_sentiment` 엔드포인트 FK 재접근
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: `entities` queryset에 `select_related('news')`는 있지만, 루프 `e.news.published_at` 접근 시 캐시 미스 경로 존재. 1000+ 엔티티 케이스에서 확산.
- **권장 수정**: prefetch 경로를 모든 QuerySet 초기화 지점에 명시적으로 지정하고, 불변 체크 테스트 추가.

---

### H6. `news/api/views.py:331-336` — `trending` 뷰 심볼별 루프 내 `NewsArticle` 쿼리
- **심각도**: HIGH / 수정 난이도: 중간
- **설명**: 상위 10 trending 심볼 각각에 대해 `NewsArticle.objects.filter(entities__symbol=symbol, ...)[:3]`. 10개 추가 쿼리 + distinct 조인 부하.
- **권장 수정**: 심볼 배열로 한 번에 fetch 후 Python에서 dict으로 그룹화.
  ```python
  all_articles = NewsArticle.objects.filter(
      entities__symbol__in=symbols, published_at__gte=from_date
  ).prefetch_related('entities').distinct().order_by('-published_at')
  # 심볼별 최대 3개로 그룹화
  ```

---

### H7. `news/api/views.py:42-52` — `NewsViewSet` 페이지네이션 미설정
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: `ReadOnlyModelViewSet` 기본 list 엔드포인트에 `pagination_class` 미지정. `NewsArticle` 행 100만 건 이상 시 OOM/타임아웃 위험.
- **권장 수정**:
  ```python
  class NewsViewSet(viewsets.ReadOnlyModelViewSet):
      pagination_class = PageNumberPagination
      ...
  ```

---

### H8. `rag_analysis/models.py:14` — `DataBasket.user` FK 인덱스 누락
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: `DataBasket.objects.filter(user=request.user)` 쿼리 빈번 (views.py:73 등). user FK에 인덱스 없으면 사용자당 full scan.
- **권장 수정**: `user = models.ForeignKey(User, ..., db_index=True)`.

---

### H9. `rag_analysis/models.py:138-148` — `AnalysisSession` 복합 인덱스 누락
- **심각도**: HIGH / 수정 난이도: 중간
- **설명**: views.py:433에서 `filter(user=...)` + ordering `-updated_at` + status 필터가 복합. 단일 인덱스로는 부족.
- **권장 수정**:
  ```python
  class Meta:
      indexes = [
          models.Index(fields=['user', '-updated_at']),
          models.Index(fields=['user', 'status']),
      ]
  ```

---

### H10. `rag_analysis/serializers.py:46` — `DataBasketSerializer.get_can_add_item` 호출 N+1
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: 모델의 `can_add_item()`이 내부적으로 `self.items.count()` 실행. `DataBasketListCreateView`에서 100 basket 직렬화 시 100회 추가 COUNT 쿼리.
- **권장 수정**: View에서 `prefetch_related('items')` + Serializer에서 `len(obj.items.all())`로 in-memory 카운트.

---

### H11. `chainsight/api/views.py:70-83` — `ChainSightGraphView` 에지별 이중 DB 쿼리
- **심각도**: HIGH / 수정 난이도: 중간
- **설명**: Neo4j에서 반환된 edge 배열을 루프하며 매 edge마다 `CoMentionEdge.objects.filter().first()` + `PriceCoMovement.objects.filter().first()`. 100 edge → 200 쿼리.
- **권장 수정**: edge 심볼쌍을 미리 수집 → `Q(symbol_a__in=..., symbol_b__in=...)`로 bulk fetch → dict lookup.

---

### H12. `validation/api/views.py:264-285` — `ValidationMetricsView._build_metric()` PeerMetricBenchmark N+1
- **심각도**: HIGH / 수정 난이도: 중간
- **설명**: metric_codes 배열(21개) × 각 metric의 snapshot 최대 5개에 대해 `PeerMetricBenchmark.filter().first()` 반복. 총 100+ 쿼리/요청.
- **권장 수정**: (snapshot의 fiscal_year, metric_code_id) 전체를 key로 한 번에 PeerMetricBenchmark bulk fetch 후 dict 매핑.

---

### H13. `validation/api/views.py:112-124` — `ValidationSummaryView.rank_metrics` 개별 조회
- **심각도**: HIGH / 수정 난이도: 쉬움
- **설명**: `rank_metrics`(5개) 루프마다 `CompanyBenchmarkDelta.filter().first()` + `MetricDefinition.filter(pk=mc).first()`. 5×2=10 쿼리.
- **권장 수정**: `metric_code_id__in=rank_metrics`로 Delta/MetricDefinition을 한 번씩 fetch 후 dict 매핑.

---

## 🟡 MED 심각도 이슈 (15건)

---

### M1. `stocks/models.py:20` — `Stock.exchange`, `currency`, `asset_type` 인덱스 누락
- **설명**: `filter(exchange=..., asset_type='Stock')` 쿼리 빈번하지만 필드 인덱스 없음.
- **권장 수정**: `db_index=True` 추가.

---

### M2. `stocks/serializers.py:190-203` — `OverviewTabSerializer` 다중 OneToOne try/except
- **설명**: `obj.overview_ko`, `obj.sensitivity_profile`, `obj.growth_stage` 등 6개 OneToOne을 try/except로 접근. `select_related` 없이 호출 시 각각 DB 조회.
- **권장 수정**: View에서 전부 `select_related()` 체인.

---

### M3. `users/views.py:1031` — `UserInterestListCreateView` 응답 내 불필요한 `.count()`
- **설명**: 응답 dict에 `'total_interests': UserInterest.objects.filter(user=...).count()`. 이미 created/skipped 정보가 있어 중복.
- **권장 수정**: 한 번의 aggregate로 한정하거나 계산 기반으로 대체.

---

### M4. `users/models.py:188-190` — `Watchlist.stock_count` property N+1 위험
- **설명**: property 내부 `self.items.count()` 호출. 리스트 직렬화 시 row당 COUNT 한 번씩.
- **권장 수정**: View에서 `annotate(stock_count=Count('items'))` 사용.

---

### M5. `stocks/views.py:75` — `StockListAPIView` pagination 미설정
- **설명**: `ListAPIView`이지만 `pagination_class` 없음. Stock 전량(~5000건) 반환 위험.
- **권장 수정**: `pagination_class = PageNumberPagination` 명시.

---

### M6. `stocks/views.py:189-192` — `StockSearchAPIView` order_by 후 slicing 역순
- **설명**: `.filter(...).order_by('symbol')[:20]`에서 매칭된 전체 행을 정렬한 뒤 20개 추출. 매칭 수가 크면 비용 증가.
- **권장 수정**: 인덱스 활용 가능하도록 쿼리 재설계 (`symbol` 인덱스 + prefix match).

---

### M7. `news/api/views.py:201` — `entities.count()` 쿼리 추가
- **설명**: 이미 로드된 queryset에 대해 `.count()`는 별도 COUNT 쿼리 발생.
- **권장 수정**: `len(list(entities))` 또는 이전 결과 재사용.

---

### M8. `serverless/serializers.py:121-137` — `MarketMoverListSerializer` 인스턴스 반복 생성
- **설명**: 각 SerializerMethodField에서 `IndicatorCalculator()` 매번 생성. 100 row 직렬화 시 100회 인스턴스화.
- **권장 수정**: `__init__`에서 1회 생성 후 `self.calc` 재사용.

---

### M9. `news/models.py:290` — `NewsEntity.symbol` 단일 인덱스 누락
- **설명**: 현재 `['symbol', 'entity_type']` 복합만 존재. `symbol` 단독 필터(trending, stock_sentiment)에서 left-prefix 활용되나 정렬 포함 쿼리 최적화 부족.
- **권장 수정**: `['symbol', '-sentiment_score']` 인덱스 추가.

---

### M10. `serverless/models.py:17-29` — `MarketMover` 복합 인덱스 보강
- **설명**: unique_together는 있지만, `date + symbol` 단독 조회용 복합 인덱스 부재.
- **권장 수정**: `Meta.indexes = [Index(['date', 'symbol']), Index(['date', 'mover_type'])]`.

---

### M11. `rag_analysis/views.py:538-630` — `ChatStreamView` `async_to_sync` 오버헤드
- **설명**: 동기 DRF View에서 async 파이프라인을 `async_to_sync`로 호출. 동시 50+ 사용자에서 ASGI 스레드 병목.
- **권장 수정**: `AsyncAPIView` 또는 Celery + WebSocket 구조로 이관 (설계 변경 필요).

---

### M12. `validation/models/peer_preset.py:19-40` — `PeerPreset.symbol` 단일 인덱스 누락
- **설명**: `filter(symbol_id=symbol)`(views.py:426) 빈번하지만 symbol 단독 인덱스 없음.
- **권장 수정**: `indexes = [Index(['symbol'])]` 추가.

---

### M13. `validation/models/benchmark_delta.py:58-63` — `CompanyBenchmarkDelta` 3-필드 복합 인덱스
- **설명**: `filter(symbol, fiscal_year, metric_code)` 쿼리 다발.
- **권장 수정**: `Index(['symbol', 'fiscal_year', 'metric_code'])` 추가.

---

### M14. `validation/api/views.py:351-375` — `LeaderComparisonView` all_metrics 루프 N+1
- **설명**: 50~80 metric 배열 루프에서 metric당 3쿼리. 최대 240쿼리.
- **권장 수정**: MetricDefinition + 2개 CompanyMetricSnapshot을 `metric_code_id__in=...`로 한 번에 fetch.

---

### M15. `sec_pipeline/models.py:335-345` — `UnmatchedCompanyQueue` status+정렬 복합 인덱스
- **설명**: `status='pending'` 필터 + `-occurrence_count` 정렬 조합에서 단일 인덱스 활용 불가.
- **권장 수정**: `Index(['status', '-occurrence_count'])` 추가.

---

## 🟢 LOW 심각도 이슈 (10건)

---

### L1. `stocks/serializers.py:337` — `DailyPriceSerializer.stock_symbol` source 지정
- **설명**: `CharField(source='stock.symbol')` — 대부분 `select_related` 있으면 무해. 명시적 annotation 여지.

---

### L2. `users/models.py:83` — `Portfolio.total_value` property에서 FK 접근
- **설명**: `stock.real_time_price` 접근. select_related 이미 있으나 property 비용 주의.

---

### L3. `stocks/models.py:95-102` — 복합 인덱스와 `icontains`
- **설명**: `['symbol','sector']` 인덱스가 `sector__icontains`에서 활용되지 않음. 설계 검토 필요.

---

### L4. `macro/views.py:273-410` — `DataSyncView` 데몬 스레드
- **설명**: `threading.Thread(daemon=True)` 종료 시 캐시 상태 유실 가능. 권장: Celery 태스크로 이관.

---

### L5. `rag_analysis/models.py:192` — `AnalysisMessage.session` FK `db_index` 누락
- **설명**: `session.messages.all()` 호출 빈번.
- **권장 수정**: `db_index=True` 추가.

---

### L6. `serverless/serializers.py:454-476` — `SectorHeatmapSerializer.get_summary` in-memory 재순회
- **설명**: 섹터 10~15개라 영향 미미하지만, view 단에서 aggregate 처리 권장.

---

### L7. `validation/api/views.py:421-453` — `PresetListView` pagination 없음
- **설명**: 심볼당 6개 내외라 현재는 문제 없음. 스케일 대비 pagination 추가가 모범 사례.

---

### L8. `validation/api/views.py:148-161` — `_find_leader()` peer bulk fetch
- **설명**: peer 심볼 10~20개라 acceptable. 모니터링만.

---

### L9. `chainsight/api/views.py:145-160` — `CoMentionEdge.union()`
- **설명**: 2쿼리 union 후 Python merge. `Q(symbol_a=s)|Q(symbol_b=s)`로 단일 쿼리 통일 가능.

---

### L10. `validation/models/category_score.py:56-61` — `CategorySignal` 인덱스 재정렬
- **설명**: 실제 쿼리는 `filter(symbol, category)`. 현재 단일 인덱스 `['symbol']`.
- **권장 수정**: `Index(['symbol','category'])`로 대체.

---

## 종합 권장 사항

### 즉시 수정 (Phase 1 — 1일 내)
1. **H10**: `DataBasketSerializer.get_can_add_item` — prefetch + in-memory count
2. **H2**: `WatchListStockSerializer.get_latest_price` — `Prefetch(... [:1])`
3. **H4**: Watchlist bulk `.exists()` — 단일 `values_list` 조회
4. **H13**: `ValidationSummaryView.rank_metrics` — 단일 bulk fetch
5. **H7**: `NewsViewSet.pagination_class` 추가

### 단기 수정 (Phase 2 — 1주일 내)
6. **H1, H5, M2**: `select_related`/`prefetch_related` 체인 강화
7. **H3**: `Sum(F() * F())` aggregate 변경
8. **H6, H11, H12, M14**: 루프 내 DB 쿼리 → bulk fetch 패턴으로 리팩터
9. **H8, H9, M1, M12, M13, M15**: 인덱스 migration 1건으로 배치 처리

### 설계 검토 (Phase 3 — 백로그)
10. **M11**: RAG async 파이프라인 — AsyncAPIView 또는 Celery+WebSocket
11. **L4**: `DataSyncView` → Celery 이관
12. **L3**: `icontains` 검색 — pg_trgm 또는 full-text search 도입

### 모니터링 포인트
- `django-silk` 또는 `django-debug-toolbar` 로 N+1 회귀 상시 감지
- `select_related/prefetch_related` 누락을 감지하는 `nplusone` 라이브러리 도입 검토
- `pg_stat_statements` 로 장기 실행 쿼리 트렌드 추적

---

## 메트릭 요약

| 지표 | 현재 추정치 | HIGH 해결 후 |
|------|-----------|-------------|
| Watchlist 100개 조회 쿼리 수 | ~100+ | ~3~5 |
| ValidationMetrics 응답 쿼리 수 | 100+ | 10~15 |
| NewsViewSet list 메모리 | 수십 MB~ | 수백 KB |
| ChainSightGraph edge 100개 쿼리 수 | ~200 | ~2 |

> 본 감사는 정적 분석 기반이며, 실제 영향은 트래픽/데이터 크기/인덱스 분포에 따라 달라질 수 있음. Phase 1 수정 후 `pg_stat_statements` + APM 지표로 실측 재검증을 권장함.
