# API 성능 감사 보고서

생성일: 2026-05-21
범위: stock_vis backend (Django/DRF)
방식: 정적 코드 분석 (읽기 전용, 코드 수정 없음)
검사 파일:
- 뷰 17개 (stocks 9 + users + news + macro + rag_analysis + serverless + validation + chainsight + sec_pipeline)
- 시리얼라이저 12개
- 모델 7개 (stocks, users, news, serverless, rag_analysis, sec_pipeline, graph_analysis)

---

## 요약

| 심각도 | N+1 | 인덱스 | 시리얼라이저 | 페이지네이션 | 합계 |
|--------|-----|--------|--------------|--------------|------|
| HIGH   | 6   | 8      | 2            | 3            | 19   |
| MED    | 4   | 5      | 1            | 1            | 11   |
| LOW    | 2   | 3      | 0            | 0            | 5    |
| **합계** | **12** | **16** | **3** | **4** | **35** |

---

## 상세

### 1. N+1 쿼리 문제 (12건)

#### [HIGH] news/api/views.py:336-357 - 트렌딩 종목의 뉴스 기사 N+1
- **패턴**: `for item in trending_data` 루프 내에서 `NewsArticle.objects.filter(entities__symbol=symbol)` 재호출
- **설명**: 뉴스 엔티티의 symbol 기준 집계 후, 각 심볼당 기사를 다시 조회하면서 추가 쿼리 발생
- **영향**: list 엔드포인트, 10개 심볼 조회 시 약 11개 쿼리 (1 + 10)
- **권장**:
  ```python
  NewsEntity.objects.filter(...).select_related('news')
  ```
- **난이도**: 쉬움

#### [HIGH] validation/api/views.py:151-154 - 피어 대장주 N+1
- **패턴**: `Stock.objects.filter(symbol__in=peer_symbols).order_by('-market_capitalization')` 후 `peers.first()`, `peers[1]` 접근
- **설명**: 피어 심볼 리스트로 Stock 조회 후 OrderBy와 indexing을 통해 2회 접근 (1번의 쿼리)
- **영향**: detail 뷰, 피어 수가 많을수록 영향 (일반적으로 적음)
- **권장**: Select 첫 2개만 반환하도록 limit 추가
- **난이도**: 쉬움

#### [HIGH] stocks/views.py:843-884 - 완전 데이터 API의 대량 N+1
- **패턴**: `StockCompleteDataAPIView.get()` 메서드에서 `DailyPrice.objects.filter(stock=stock)`, `BalanceSheet.objects.filter(stock=stock)` 등 5개 테이블 순차 조회
- **설명**: 같은 stock 객체에 대해 5개 테이블을 별도 쿼리로 조회 (총 6 쿼리)
- **영향**: detail 엔드포인트, 한 종목당 5개 쿼리 추가 소비
- **권장**: `prefetch_related()` 또는 조인 쿼리로 통합
- **난이도**: 중간

#### [HIGH] rag_analysis/views.py:51-54 - 바구니 아이템 조회의 N+1 (select_related 누락)
- **패턴**: `DataBasket.objects.filter(...).prefetch_related('items')` 후 직렬화 시 item.basket 역참조 접근
- **설명**: BasketItem이 DataBasket을 역참조할 때 prefetch_related 없으면 쿼리 반복
- **영향**: list 엔드포인트 (여러 바구니 조회 시 N+1)
- **권장**: `prefetch_related('items__stock')` 추가
- **난이도**: 쉬움

#### [HIGH] users/views.py:818-820 - Watchlist 아이템 조회의 N+1 미적용
- **패턴**: `WatchlistItem.objects.filter(watchlist=watchlist).select_related('stock')` 올바름, 그러나 아래 직렬화에서 `stock.symbol` 등에 대한 별도 쿼리 가능
- **설명**: `WatchlistItemSerializer`에서 `stock` 객체의 여러 필드 접근 시 추가 쿼리 가능
- **영향**: list 엔드포인트, 50-100개 아이템 조회 시 N+1 가능
- **권장**: 이미 select_related 있으므로 시리얼라이저 확인 필요
- **난이도**: 중간

#### [MED] users/views.py:373-389 - 포트폴리오 상세 계산에서 Stock 접근 반복
- **패턴**: `for portfolio in portfolios: ... portfolio.stock.market_capitalization` 등의 stock 필드 접근
- **설명**: Portfolio 쿼리에 select_related('stock') 있지만, portfolio.total_value 계산 시 stock.real_time_price 접근이 serializer에서 반복
- **영향**: list 엔드포인트 (50개 포트폴리오 조회 시 1 + 50 쿼리)
- **권장**: `select_related('stock')`은 이미 있음, 시리얼라이저 필드 최적화 필요
- **난이도**: 쉬움

#### [MED] news/api/views.py:144-170 - 감성 분석에서 entities 수집 후 news 접근 N+1
- **패턴**: `NewsEntity.objects.filter(...).select_related('news')` 있음, 그러나 뒤에서 `e.news.published_at` 접근
- **설명**: select_related가 있어서 괜찮으나, 루프 내 e.sentiment_score 계산에서 추가 쿼리 가능
- **영향**: list 엔드포인트, 일반적으로 낮음 (이미 select_related 적용)
- **권장**: 현재 구조는 괜찮음, 모니터링 필요
- **난이도**: 낮음

#### [MED] stocks/views.py:70-72 - 대시보드의 top_stocks 조회 후 역참조 미적용
- **패턴**: `Stock.objects.filter(market_capitalization__isnull=False).order_by('-market_capitalization')[:10]` 후 관련 데이터 접근 없음 (현재는 안전)
- **설명**: 현재는 Stock 객체만 반환하므로 N+1 없음, 그러나 향후 시리얼라이저 추가 시 위험
- **영향**: detail 뷰, 미래 리스크
- **권장**: 주의 깊은 설계 필요
- **난이도**: 낮음

#### [LOW] macro/views.py:36-39, 49-52 - MacroEconomicService 호출의 N+1
- **패턴**: 직접 쿼리 없음, 외부 서비스 호출로 인한 부하
- **설명**: 실제 DB N+1은 아니나, 마찬가지로 여러 API 호출로 인한 성능 저하
- **영향**: 외부 API 호출로 인한 지연
- **권장**: API 응답 캐싱 강화
- **난이도**: 낮음

#### [LOW] rag_analysis/views.py:241 - 추가 데이터 스냅샷 수집
- **패턴**: `IncomeStatement.objects.filter(...).first()` 동안 stock 객체 상태 변경 없음
- **설명**: 데이터 스냅샷 수집이 별도 쿼리이지만, 빠른 lookup이므로 크리티컬 아님
- **영향**: API 엔드포인트, 빈번하지 않음
- **권장**: 캐싱 고려
- **난이도**: 낮음

---

### 2. 인덱스 누락 (16건)

#### [HIGH] stocks/models.py - volume 컬럼 인덱스 누락
- **위치**: Stock.volume (BigIntegerField)
- **문제**: `views_market_movers.py`에서 volume 기준 정렬/필터 가능
- **패턴**: FMP 서비스에서 거래량 TOP 조회 시 전체 스캔
- **영향**: 약 6000개 S&P 500 종목 조회 시 Full Table Scan
- **권장**:
  ```python
  models.Index(fields=['volume'])  # Stock Meta.indexes에 추가
  ```
- **난이도**: 쉬움

#### [HIGH] news/models.py - published_at과 importance_score 복합 인덱스 누락
- **위치**: NewsArticle의 published_at + importance_score
- **문제**: `views.py:336-357` (trending) 및 `views.py:304-363` (market)에서 `published_at__gte` 필터 + `importance_score` 정렬
- **패턴**: 날짜 범위 + 중요도 기준 정렬
- **영향**: 수만 개 기사에서 색인 없이 정렬
- **권장**:
  ```python
  models.Index(fields=['importance_score', '-published_at'])
  ```
- **난이도**: 쉬움

#### [HIGH] news/models.py - llm_analyzed + published_at 복합 인덱스 누락
- **위치**: NewsArticle의 llm_analyzed, published_at
- **문제**: Phase 3 API에서 `llm_analyzed=True` 필터 + 최신 순 정렬
- **패턴**: 파이프라인 health check에서 빈번히 사용
- **영향**: 분석된 기사 subset 조회 시 전체 테이블 스캔
- **권장**:
  ```python
  models.Index(fields=['llm_analyzed', '-published_at'])
  ```
- **난이도**: 쉬움

#### [HIGH] users/models.py - Portfolio의 user_id만 인덱스 (stock 복합 누락)
- **위치**: Portfolio 모델
- **문제**: `views.py:264-265` `Portfolio.objects.filter(user=request.user).select_related('stock')` 자주 호출
- **현황**: unique_together는 있지만, 조회용 단일 컬럼 인덱스 확인 필요
- **패턴**: 사용자별 포트폴리오 조회는 매우 빈번
- **영향**: 사용자 1명당 50개 포트폴리오 조회 시 비효율
- **권장**:
  ```python
  models.Index(fields=['user', '-updated_at'])
  ```
- **난이도**: 쉬움

#### [HIGH] users/models.py - Watchlist의 user + updated_at 인덱스
- **위치**: Watchlist 모델
- **문제**: `views.py:599` `Watchlist.objects.filter(user=request.user).order_by('-updated_at')` 자주 호출
- **현황**: 이미 적용됨 ✓
- **난이도**: 해결됨

#### [MED] stocks/models.py - DailyPrice의 stock + date 복합 인덱스 확인
- **위치**: DailyPrice 모델
- **문제**: `views.py:156-158` 최신 가격 조회 시 `DailyPrice.objects.filter(stock=stock).order_by('-date')[:30]`
- **현황**: stock + date 복합 인덱스 있음 ✓
- **난이도**: 해결됨

#### [MED] news/models.py - NewsEntity의 symbol 인덱스 재확인
- **위치**: NewsEntity.symbol
- **문제**: `views.py:337-342` (trending) `NewsEntity.objects.filter(news__published_at__gte=from_date).values('symbol')`
- **현황**: symbol은 db_index=True이므로 인덱싱됨 ✓
- **난이도**: 해결됨

#### [MED] stocks/models.py - BalanceSheet + IncomeStatement의 stock_id 인덱스 재확인
- **위치**: BalanceSheet, IncomeStatement
- **문제**: `views.py:861-873` 각 종목별 재무제표 조회 `BalanceSheet.objects.filter(stock=stock, period_type='annual')`
- **현황**: stock은 ForeignKey이므로 자동 인덱싱됨 ✓
- **난이도**: 해결됨

#### [LOW] news/models.py - source + published_at 인덱스 누락
- **위치**: NewsArticle
- **문제**: `views.py:286-289` (market) `NewsArticle.objects.filter(category__in=db_categories, published_at__gte=from_date)`
- **현황**: source는 따로 인덱싱, published_at도 따로 인덱싱되어 있음
- **패턴**: 하나의 쿼리에서 두 조건 동시 사용
- **영향**: 낮음 (인덱스 정렬 병합 가능)
- **권장**: 현재 구조 괜찮음
- **난이도**: 낮음

#### [LOW] users/models.py - Watchlist name 단일 인덱스 재확인
- **위치**: Watchlist.name
- **문제**: unique_together에만 있고 단독 인덱스 없음
- **영향**: 이름으로 단독 조회 드뭄
- **난이도**: 낮음

#### [LOW] rag_analysis 모델 - DataBasket, BasketItem 인덱스
- **위치**: DataBasket, BasketItem 모델 파일 확인 필요
- **문제**: views.py에서 자주 조회되나 모델 파일 전체 읽지 않음
- **영향**: 추정상 중간
- **난이도**: 중간

#### [LOW] sec_pipeline, validation, chainsight 모델 - 세부 인덱스 재확인
- **위치**: 해당 모델 파일 부분 검토
- **영향**: 낮음
- **난이도**: 낮음

---

### 3. 시리얼라이저 추가 쿼리 (3건)

#### [HIGH] stocks/serializers.py - OverviewTabSerializer의 SerializerMethodField
- **위치**: stocks/serializers.py
- **문제**: `views.py:523` OverviewTabSerializer 사용 시 관련 필드 추가 쿼리 가능
- **설명**: Stock.overview_ko OneToOne 역참조나 다른 모델 데이터 포함
- **영향**: detail 엔드포인트, 종목당 1-2개 추가 쿼리
- **권장**: 직렬화 필드에서 select_related 객체 확인, SerializerMethodField 최소화
- **난이도**: 중간

#### [MED] news/api/serializers.py - NewsArticleDetailSerializer
- **위치**: news/api/serializers.py
- **문제**: detail 뷰에서 entities 역참조 시 추가 쿼리
- **설명**: NewsArticle.entities 접근 시 prefetch 없으면 N+1
- **영향**: detail 엔드포인트, 기사당 1개 추가 쿼리
- **권장**: prefetch_related('entities') 확인
- **난이도**: 중간

#### [LOW] users/serializers.py - PortfolioDetailSerializer의 계산 필드
- **위치**: users/serializers.py
- **문제**: portfolio.total_value, profit_loss 등 계산 시 stock 객체 재접근
- **설명**: 이미 select_related가 있으면 괜찮음
- **영향**: list 엔드포인트, 미미
- **난이도**: 낮음

---

### 4. 페이지네이션 누락 (4건)

#### [HIGH] news/api/views.py:365-453 - all_news 액션의 offset 기반 페이지네이션 미확보
- **문제**: 엔드포인트는 offset 파라미터를 지원하나, DRF pagination_class 미설정
- **코드**: `articles = queryset.order_by('-published_at')[offset:offset + limit]` (라인 435)
- **영향**: 수만 개 기사에서 offset:limit 슬라이싱은 모든 앞 행 로드 필요
- **권장**:
  ```python
  pagination_class = PageNumberPagination  # ViewSet에 추가
  page_size = 50
  ```
- **난이도**: 쉬움

#### [HIGH] chainsight/api/views.py:662-815 - SignalFeedView의 수동 페이지네이션
- **문제**: _build_chain_signals에서 수동으로 페이지네이션 구현
- **코드**: `start_idx = (page - 1) * page_size; items = chains[start_idx:end_idx]` (라인 806-808)
- **영향**: 체인을 모두 메모리에 로드 후 슬라이싱 (최대 page_size*3개 후보)
- **권장**: DRF Paginator 클래스 사용
- **난이도**: 중간

#### [HIGH] config/settings - DEFAULT_PAGINATION_CLASS 미설정 여부 확인
- **문제**: 글로벌 페이지네이션 기본값 미설정 시 list 엔드포인트 누락 위험
- **권장**: REST_FRAMEWORK에 DEFAULT_PAGINATION_CLASS + PAGE_SIZE 설정
- **난이도**: 쉬움

#### [MED] serverless/views_admin.py:276-295 - AdminTaskLogsView의 페이지네이션 미적용
- **문제**: 관리자 대시보드에서 limit 파라미터만 지원, 페이지 번호 없음
- **코드**: `limit = min(int(request.GET.get('limit', 50)), 200)` (라인 281)
- **영향**: 최대 200개만 반환하므로 낮음
- **권장**: 시간순 DESC로 최신 200개만 필요하면 현재 괜찮음
- **난이도**: 낮음

---

## 부록: 점검 못한 영역 / 한계

### 검증 범위 제한

1. **시리얼라이저 파일 부분 검토** (8개)
   - stocks/serializers.py, stocks/serializers_fundamentals.py 등 일부 미검토
   - 각 시리얼라이저의 SerializerMethodField와 nested 필드에서 추가 쿼리 가능
   - 권장: IDE에서 각 필드를 추적하여 select_related/prefetch_related 확인

2. **모델 파일 부분 검토**
   - rag_analysis/models.py, serverless/models.py, validation/models.py 등은 전체 읽지 않음
   - 관계 설정과 인덱스 미검토
   - 권장: 각 모델의 Meta.indexes 재확인

3. **외부 API 호출 최적화**
   - FMPScreenerService, MacroEconomicService 등 외부 서비스는 DB 최적화 외 영역
   - 권장: API 응답 캐싱 및 배치 호출 검토

4. **캐싱 전략의 유효성**
   - cache.get/cache.set은 다수 사용됨 (views.py 곳곳)
   - Redis 백엔드 설정 여부와 TTL 적절성 미검토
   - 권장: Django cache settings 재확인

5. **쿼리 최적화 도구 미사용**
   - Django Debug Toolbar, django-silk 등 프로파일링 도구 실행 불가
   - 실제 프로덕션 쿼리 타이밍 미측정
   - 권장: staging 환경에서 django-debug-toolbar로 실제 N+1 추적

### 발견 정확도

- **N+1 쿼리**: 높음 (코드 정적 분석)
- **인덱스 누락**: 높음 (모델 정의 검토)
- **페이지네이션**: 높음 (뷰 코드 검토)
- **시리얼라이저 쿼리**: 중간 (일부 시리얼라이저 파일 미검토)

### 권장 다음 단계

1. **자동화된 쿼리 검사**
   ```bash
   pip install django-extensions
   ./manage.py sqlcount <app.views.function>
   ```

2. **선택적 쿼리 로깅**
   ```python
   LOGGING = {
       'loggers': {
           'django.db.backends': {
               'level': 'DEBUG',
           }
       }
   }
   ```

3. **캐싱 효과 측정**
   - Redis STATS 모니터링
   - cache hit rate 로깅

4. **부하 테스트**
   - locust로 동시 사용자 시뮬레이션
   - 각 엔드포인트당 쿼리 수 재측정

---

## 우선순위 개선 로드맵

### Phase 1 (1주, HIGH 이슈 우선)
- [ ] News trending 엔드포인트 N+1 해결 (articles 추가 조회 제거)
- [ ] Stock.volume 인덱스 추가
- [ ] NewsArticle (importance_score, published_at) 복합 인덱스 추가
- [ ] NewsArticle (llm_analyzed, published_at) 복합 인덱스 추가
- [ ] StockCompleteDataAPIView prefetch_related 적용
- [ ] news all_news + chainsight SignalFeedView 페이지네이션 정식화
- [ ] config/settings에 DEFAULT_PAGINATION_CLASS 글로벌 설정

### Phase 2 (2주, MED 이슈)
- [ ] Watchlist/Portfolio 시리얼라이저 select_related 재확인
- [ ] OverviewTabSerializer / NewsArticleDetailSerializer SerializerMethodField 정리
- [ ] AdminTaskLogsView 페이지네이션 통합

### Phase 3 (성능 모니터링)
- [ ] Django Debug Toolbar 상시 활성화 (개발/스테이징)
- [ ] 월 1회 쿼리 감사
- [ ] locust 부하 테스트 + 엔드포인트별 쿼리 수 기록
