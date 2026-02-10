# News Feature Architecture Review

**작성자**: @qa-architect
**날짜**: 2025-12-08
**대상**: Phase 1-3 뉴스 기능 구현

---

## 1. 개요

### 1.1 검토 범위

- **인프라**: Docker Neo4j, 환경변수 설정
- **백엔드**: news 앱 (모델, Provider, Service, API)
- **프론트엔드**: 뉴스 컴포넌트, 페이지
- **테스트**: Unit 테스트 (모델, Provider, Service, API)

### 1.2 아키텍처 목표

1. **Provider 추상화**: 다중 뉴스 API 통합 (Finnhub, Marketaux)
2. **3계층 분리**: Provider → Service → API
3. **중복 제거**: URL 해시 + 제목 유사도 기반
4. **감성 분석**: Marketaux 내장 감성 점수 활용
5. **캐싱 전략**: Redis 캐싱으로 API 호출 최소화

---

## 2. 아키텍처 분석

### 2.1 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                      │
│  - 뉴스 리스트 컴포넌트                                      │
│  - 감성 분석 차트                                           │
│  - 트렌딩 종목 위젯                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (Django REST)                     │
│  - NewsViewSet (stock_news, stock_sentiment, trending)      │
│  - 캐싱 (10분, 30분, 5분)                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer (Aggregator)                 │
│  - NewsAggregatorService                                    │
│  - NewsDeduplicator                                         │
│  - 트랜잭션 관리                                            │
└─────────────────────────────────────────────────────────────┘
                    │                     │
                    ▼                     ▼
┌────────────────────────┐    ┌────────────────────────┐
│  FinnhubNewsProvider   │    │ MarketauxNewsProvider  │
│  - 60 calls/min        │    │ - 100 calls/day        │
│  - Rate limiting       │    │ - 감성 분석 포함       │
└────────────────────────┘    └────────────────────────┘
                    │                     │
                    ▼                     ▼
               External APIs (Finnhub, Marketaux)
```

### 2.2 데이터 모델 설계

#### 2.2.1 핵심 모델

| 모델 | 역할 | 주요 제약 |
|-----|------|----------|
| **NewsArticle** | 뉴스 기사 메타데이터 | `url` UNIQUE, `url_hash` 자동 생성 |
| **NewsEntity** | 뉴스-종목 M:N 관계 | `unique_together=['news', 'symbol']` |
| **EntityHighlight** | 엔티티별 감성 하이라이트 | Marketaux 전용 |
| **SentimentHistory** | 일별 감성 집계 | `unique_together=['symbol', 'date']` |

#### 2.2.2 모델 관계도

```
NewsArticle (1) ─────── (N) NewsEntity
    │                        │
    │                        │
    │                        ├── EntityHighlight (N)
    │                        │
    ├── url_hash (SHA256)    └── sentiment_score
    ├── finnhub_id
    └── marketaux_uuid

SentimentHistory (독립적 집계)
    ├── symbol
    ├── date
    ├── avg_sentiment
    └── news_count
```

**✅ 강점**:
- M:N 관계로 하나의 뉴스가 여러 종목에 연결 가능
- `url_hash` 자동 생성으로 중복 체크 최적화
- Provider별 ID 저장 (finnhub_id, marketaux_uuid)

**⚠️ 주의사항**:
- `url_hash`는 모델 `save()` 시점에 생성되므로, `objects.create()` 전에는 없음
- 대량 데이터 시 `NewsEntity` 인덱싱 최적화 필요 (현재 `symbol`, `sentiment_score` 인덱스 존재)

---

### 2.3 Provider 계층

#### 2.3.1 설계 패턴

```python
BaseNewsProvider (ABC)
    ├── fetch_company_news()    # 추상 메서드
    ├── fetch_market_news()     # 추상 메서드
    ├── get_rate_limit()        # 추상 메서드
    └── normalize_url()         # 공통 유틸

FinnhubNewsProvider
    ├── request_delay: 1.0s (60 calls/min)
    ├── _parse_article()
    └── entities: match_score=1.0 (명시적), 0.8 (related 필드)

MarketauxNewsProvider
    ├── request_delay: 900.0s (100 calls/day)
    ├── _parse_article()
    └── entities: 감성 점수 + 하이라이트 포함
```

**✅ 강점**:
- 추상 베이스 클래스로 Provider 일관성 보장
- Rate limiting을 Provider 자체에서 처리 (time.sleep)
- `normalize_url()` 공통 메서드로 중복 제거 지원

**⚠️ 개선 권고사항**:

1. **Rate Limiting 중앙화**:
   - 현재: 각 Provider가 `time.sleep()`으로 처리
   - 개선: Redis 기반 분산 Rate Limiting 도입 (Celery 환경에서 필수)

   ```python
   # 예시: Redis 기반 Rate Limiter
   from django_redis import get_redis_connection

   class RateLimiter:
       def check_and_wait(self, key, calls, period):
           redis_conn = get_redis_connection("default")
           # sliding window algorithm
   ```

2. **Retry 로직 추가**:
   - 현재: 1회 실패 시 바로 에러 반환
   - 개선: exponential backoff retry (3회 시도)

3. **타임아웃 설정**:
   - 현재: `requests.get()` 타임아웃 없음
   - 개선: `timeout=10` 설정 권장

---

### 2.4 Service 계층

#### 2.4.1 NewsDeduplicator

**알고리즘**:

1. **URL 해시 기반 중복 제거**:
   ```python
   normalized_url = url.lower().strip()
   url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
   ```

2. **제목 유사도 기반 중복 제거**:
   ```python
   similarity = SequenceMatcher(None, title1, title2).ratio()
   if similarity >= 0.85:  # 85% 유사도 임계값
       duplicate = True
   ```

**✅ 강점**:
- 2단계 중복 제거로 정확도 높음
- 대소문자, 공백 정규화 처리

**⚠️ 개선 권고사항**:

1. **임계값 조정 가능**:
   - 현재: 하드코딩된 0.85
   - 개선: 설정 파일로 분리 (`settings.NEWS_TITLE_SIMILARITY_THRESHOLD`)

2. **성능 최적화**:
   - 현재: O(N²) 비교 (모든 기사 쌍)
   - 개선: 제목 길이 차이가 큰 경우 조기 스킵

   ```python
   if abs(len(title1) - len(title2)) / max(len(title1), len(title2)) > 0.3:
       continue  # 길이 차이가 30% 이상이면 스킵
   ```

#### 2.4.2 NewsAggregatorService

**트랜잭션 처리**:

```python
@transaction.atomic
def _save_articles(self, articles: List[RawNewsArticle]) -> tuple:
    # 모든 저장 작업이 하나의 트랜잭션
```

**✅ 강점**:
- `@transaction.atomic` 데코레이터로 ACID 보장
- 저장 실패 시 개별 건 스킵 (전체 실패 방지)
- Provider 에러 시 graceful failure

**⚠️ 개선 권고사항**:

1. **Bulk Insert 최적화**:
   - 현재: 개별 `update_or_create()` 호출
   - 개선: `bulk_create()` + `bulk_update()` 사용 (대량 데이터 시)

   ```python
   # 개선 예시
   new_articles = []
   for raw_article in articles:
       if not NewsArticle.objects.filter(url=raw_article.url).exists():
           new_articles.append(NewsArticle(...))

   NewsArticle.objects.bulk_create(new_articles, ignore_conflicts=True)
   ```

2. **에러 로깅 강화**:
   - 현재: `logger.error()` 만 출력
   - 개선: Sentry 연동으로 에러 추적

---

### 2.5 API 계층

#### 2.5.1 캐싱 전략

| 엔드포인트 | 캐시 키 | TTL | 이유 |
|----------|--------|-----|------|
| `/stock/{symbol}/` | `news:stock:{symbol}:{days}` | 10분 | 실시간성 중요 |
| `/stock/{symbol}/sentiment/` | `news:sentiment:{symbol}:{days}` | 30분 | 집계 데이터, 변동 적음 |
| `/trending/` | `news:trending:{timeframe}:{limit}` | 5분 | 자주 조회됨 |

**✅ 강점**:
- 데이터 특성에 맞는 차별화된 TTL
- `refresh=true` 파라미터로 강제 갱신 가능
- 캐시 키에 파라미터 포함으로 정확한 캐싱

**⚠️ 개선 권고사항**:

1. **캐시 무효화 전략**:
   - 현재: TTL 만료 대기
   - 개선: 새 뉴스 저장 시 관련 캐시 무효화

   ```python
   # Aggregator Service에서
   def _save_articles(self, articles):
       saved_symbols = set()
       for article in articles:
           # ... 저장 로직
           for entity in article.entities:
               saved_symbols.add(entity['symbol'])

       # 캐시 무효화
       for symbol in saved_symbols:
           cache.delete_pattern(f"news:stock:{symbol}:*")
   ```

2. **캐시 Warming**:
   - Celery Beat로 주요 종목(S&P 500) 캐시 사전 로딩

---

### 2.6 Rate Limiting 전략

#### 2.6.1 현재 구현

| Provider | Limit | 구현 방식 |
|---------|-------|----------|
| Finnhub | 60 calls/min | `time.sleep(1.0)` |
| Marketaux | 100 calls/day | `time.sleep(900.0)` |

**문제점**:

1. **동기적 대기**: API 호출 중 블로킹 (비효율적)
2. **분산 환경 미고려**: 여러 Celery Worker에서 동시 호출 시 Rate Limit 초과 가능
3. **사용량 추적 없음**: 일일 한도 소진 감지 불가

#### 2.6.2 개선 방안

**Redis Sliding Window Rate Limiter**:

```python
class RedisRateLimiter:
    def __init__(self, redis_conn):
        self.redis = redis_conn

    def is_allowed(self, key: str, max_calls: int, period: int) -> bool:
        """
        Sliding window rate limiter

        Args:
            key: Rate limit 키 (e.g., "news:rate:finnhub")
            max_calls: 최대 호출 수
            period: 기간 (초)

        Returns:
            bool: 호출 가능 여부
        """
        now = time.time()
        window_start = now - period

        # 만료된 항목 제거
        self.redis.zremrangebyscore(key, 0, window_start)

        # 현재 window 내 호출 수
        current_count = self.redis.zcard(key)

        if current_count < max_calls:
            # 새 호출 기록
            self.redis.zadd(key, {str(now): now})
            self.redis.expire(key, period)
            return True

        return False
```

**적용 예시**:

```python
class FinnhubNewsProvider(BaseNewsProvider):
    def _make_request(self, endpoint, params):
        limiter = RedisRateLimiter(get_redis_connection())

        while not limiter.is_allowed("news:rate:finnhub", 60, 60):
            time.sleep(1)  # 1초 대기 후 재시도

        response = requests.get(url, params=params, timeout=10)
        # ...
```

---

## 3. 테스트 품질 분석

### 3.1 테스트 커버리지 목표

| 계층 | 목표 커버리지 | 중요도 |
|-----|--------------|--------|
| 모델 (models.py) | 95%+ | 높음 |
| Provider (finnhub.py, marketaux.py) | 90%+ | 높음 |
| Service (deduplicator.py, aggregator.py) | 90%+ | 높음 |
| API (views.py) | 85%+ | 중간 |
| **전체** | **90%+** | - |

### 3.2 작성된 테스트

#### 3.2.1 test_models.py

- ✅ NewsArticle: URL 해시 생성, 중복 제약, 감성 점수 검증
- ✅ NewsEntity: unique_together 제약, CASCADE 삭제
- ✅ EntityHighlight: 정렬, 하이라이트 저장
- ✅ SentimentHistory: 집계 로직, 날짜별 unique

**총 25개 테스트**

#### 3.2.2 test_providers.py

- ✅ Finnhub: API 응답 파싱, Rate limiting, 심볼 대문자 변환
- ✅ Marketaux: 감성 분석 파싱, 하이라이트 추출, limit 제한
- ✅ BaseNewsProvider: URL 정규화 (쿼리 제거, 슬래시 제거)

**총 20개 테스트**

#### 3.2.3 test_services.py

- ✅ NewsDeduplicator: URL 해시 중복, 제목 유사도 중복
- ✅ NewsAggregatorService: Provider 통합, 트랜잭션, 저장/업데이트

**총 18개 테스트**

#### 3.2.4 test_api.py

- ✅ NewsViewSet: stock_news, stock_sentiment, trending 엔드포인트
- ✅ 캐싱: 캐시 히트, refresh=true
- ✅ 엣지 케이스: 데이터 없음, 감성 점수 없음

**총 22개 테스트**

### 3.3 테스트 품질 평가

**✅ 강점**:
- Given-When-Then 패턴 일관적 사용
- pytest fixture 활용으로 코드 재사용성 높음
- Mock 사용으로 외부 API 의존성 제거
- 엣지 케이스 처리 (빈 데이터, None 값)

**⚠️ 개선 권고사항**:

1. **통합 테스트 추가**:
   - 현재: Unit 테스트만 존재
   - 추가: `tests/integration/test_news_flow.py` (전체 플로우 테스트)

   ```python
   # 예시: 뉴스 수집 → 저장 → API 조회 전체 플로우
   @pytest.mark.django_db
   @pytest.mark.integration
   def test_news_full_workflow():
       # 1. 뉴스 수집
       service = NewsAggregatorService()
       result = service.fetch_and_save_company_news('AAPL')

       # 2. API 조회
       client = APIClient()
       response = client.get('/api/v1/news/stock/AAPL/')

       # 3. 검증
       assert response.status_code == 200
       assert result['saved'] > 0
   ```

2. **성능 테스트**:
   - 대량 뉴스 저장 시 성능 측정 (1000건 이상)
   - 중복 제거 알고리즘 성능 벤치마크

---

## 4. 보안 및 에러 처리

### 4.1 보안 체크리스트

| 항목 | 상태 | 비고 |
|-----|------|------|
| API 키 환경변수 관리 | ✅ | `settings.FINNHUB_API_KEY` |
| SQL Injection 방지 | ✅ | Django ORM 사용 |
| XSS 방지 | ✅ | DRF Serializer escape |
| Rate Limiting (외부 API) | ⚠️ | 분산 환경 미고려 |
| Rate Limiting (자체 API) | ❌ | 미구현 |

**개선 권고사항**:

1. **자체 API Rate Limiting**:
   ```python
   # settings.py
   REST_FRAMEWORK = {
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle'
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '100/hour',
           'user': '1000/hour'
       }
   }
   ```

2. **입력 검증 강화**:
   - `symbol` 파라미터: 알파벳 대문자만 허용 (Regex 검증)
   - `days` 파라미터: 1 ~ 365 범위 제한

### 4.2 에러 처리

**현재 구현**:

- Provider 에러: `try-except` → graceful failure (빈 리스트 반환)
- Service 에러: 개별 건 스킵, 전체 실패 방지
- API 에러: DRF 기본 에러 응답

**개선 권고사항**:

1. **구조화된 에러 응답**:
   ```python
   # 현재
   {'error': 'No news found for this symbol'}

   # 개선
   {
       'error': {
           'code': 'NEWS_NOT_FOUND',
           'message': 'No news found for symbol AAPL',
           'details': {
               'symbol': 'AAPL',
               'searched_days': 7
           }
       }
   }
   ```

2. **Sentry 통합**:
   ```python
   import sentry_sdk

   try:
       # ...
   except Exception as e:
       sentry_sdk.capture_exception(e)
       logger.error(f"Failed: {e}")
   ```

---

## 5. 성능 최적화 권고사항

### 5.1 데이터베이스 쿼리 최적화

**현재 문제점**:

1. **N+1 쿼리 발생 가능**:
   ```python
   # views.py:75-79
   articles = NewsArticle.objects.filter(...)  # 1회 쿼리
   for article in articles:
       article.entities.all()  # N회 쿼리
   ```

**개선 방안**:

```python
# prefetch_related 사용
articles = NewsArticle.objects.filter(
    entities__symbol=symbol,
    published_at__gte=from_date
).prefetch_related('entities').distinct().order_by('-published_at')
```

2. **인덱스 최적화**:
   - 현재: `NewsEntity`에 `symbol`, `sentiment_score` 인덱스 존재
   - 추가: 복합 인덱스 권장

   ```python
   class Meta:
       indexes = [
           models.Index(fields=['symbol', '-news__published_at']),  # 조회 최적화
       ]
   ```

### 5.2 캐싱 최적화

1. **Serializer 결과 캐싱**:
   - 현재: 전체 응답 캐싱
   - 개선: Serializer 결과도 캐싱 (재사용성 향상)

2. **Cache Warming (Celery Beat)**:
   ```python
   @celery_app.task
   def warm_trending_cache():
       """트렌딩 캐시 사전 로딩"""
       for timeframe in ['1h', '24h', '7d']:
           # API 호출하여 캐시 생성
   ```

---

## 6. 종합 평가

### 6.1 아키텍처 점수

| 영역 | 점수 | 평가 |
|-----|------|------|
| **모델 설계** | 9/10 | ✅ M:N 관계, 제약조건 우수 |
| **Provider 추상화** | 8/10 | ✅ 일관성 우수, ⚠️ Rate limiting 개선 필요 |
| **Service 계층** | 8/10 | ✅ 트랜잭션 관리 우수, ⚠️ Bulk insert 권장 |
| **API 설계** | 9/10 | ✅ RESTful, 캐싱 전략 우수 |
| **테스트 커버리지** | 8/10 | ✅ Unit 테스트 충분, ⚠️ 통합 테스트 추가 권장 |
| **에러 처리** | 7/10 | ⚠️ Graceful failure 우수, 구조화된 에러 개선 필요 |
| **보안** | 7/10 | ⚠️ 자체 API Rate limiting 미구현 |
| **성능** | 7/10 | ⚠️ N+1 쿼리 주의, Bulk insert 권장 |
| **문서화** | 8/10 | ✅ Docstring 우수 |
| **전체** | **8.1/10** | **우수** |

### 6.2 핵심 강점

1. ✅ **Provider 추상화**: Finnhub, Marketaux 통합 우수
2. ✅ **중복 제거 알고리즘**: 2단계 중복 제거 (URL + 제목 유사도)
3. ✅ **3계층 아키텍처**: Provider → Service → API 분리 명확
4. ✅ **감성 분석 통합**: Marketaux 감성 점수 + 하이라이트 활용
5. ✅ **캐싱 전략**: 데이터 특성별 차별화된 TTL

### 6.3 개선 우선순위

| 순위 | 항목 | 중요도 | 예상 작업량 |
|-----|------|--------|------------|
| 1 | **Redis Rate Limiter** | 높음 | 2-3일 |
| 2 | **자체 API Rate Limiting** | 높음 | 1일 |
| 3 | **N+1 쿼리 최적화** | 중간 | 1일 |
| 4 | **통합 테스트 추가** | 중간 | 2일 |
| 5 | **Bulk Insert 최적화** | 낮음 | 1일 |
| 6 | **Sentry 통합** | 낮음 | 0.5일 |

---

## 7. 다음 단계 권고사항

### 7.1 Phase 4: 뉴스 기능 개선

1. **Redis Rate Limiter 구현** (높음)
2. **자체 API Rate Limiting** (높음)
3. **통합 테스트 추가** (중간)

### 7.2 Phase 5: Frontend 통합

1. **뉴스 리스트 컴포넌트** (실시간 업데이트)
2. **감성 분석 차트** (Recharts)
3. **트렌딩 종목 위젯**

### 7.3 Phase 6: 고급 기능

1. **뉴스 알림 시스템** (Django Channels WebSocket)
2. **AI 요약 기능** (Claude API)
3. **뉴스 검색 기능** (Elasticsearch)

---

## 8. 결론

Phase 1-3에서 구현된 뉴스 기능은 **전반적으로 우수한 아키텍처**를 보여줍니다.

**핵심 성과**:
- Provider 추상화를 통한 다중 API 통합 성공
- 3계층 아키텍처 일관성 유지
- 감성 분석 통합 및 활용 우수

**개선 영역**:
- Redis 기반 분산 Rate Limiting 필요 (Celery 환경)
- N+1 쿼리 최적화
- 통합 테스트 보강

**최종 평가**: **8.1/10 (우수)**

---

**작성자**: @qa-architect
**검토 완료일**: 2025-12-08
**다음 검토**: Phase 4 완료 후
