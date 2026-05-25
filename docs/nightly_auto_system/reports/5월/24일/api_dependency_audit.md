# 외부 API 의존성 감사 보고서
생성일: 2026-05-24
범위: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 호출 지점
방식: 읽기 전용 코드 감사 (수정 없음)

---

## 의존성 매트릭스

| 서비스 | 외부 API | 호출 위치 | 동기/Celery | retry | fallback | rate limit 대응 | circuit breaker | 위험도 |
|--------|---------|----------|------------|-------|---------|----------------|---|--------|
| Quote 조회 | FMP | api_request/providers/fmp/client.py:167 | 동기 | ✓ 지수백오프(3회) | ✗ | ✓ 자동지연 | ✗ | 중 |
| 회사 프로필 | FMP | api_request/providers/fmp/client.py:231 | 동기 | ✓ 지수백오프(3회) | ✗ | ✓ 자동지연 | ✗ | 중 |
| 일별/주별 가격 | FMP | api_request/providers/fmp/client.py:195 | 동기 | ✓ 지수백오프(3회) | ✗ | ✓ 자동지연 | ✗ | 중 |
| 재무제표 | FMP | api_request/providers/fmp/client.py:286 | 동기 | ✓ 지수백오프(3회) | ✗ | ✓ 자동지연 | ✗ | 중 |
| Market Movers | FMP | serverless/services/fmp_client.py:94 | Celery | ✗ (sync only) | ✓ 캐시 | ✓ 300/min 추적 | ✓ (threshold=5) | 중 |
| 매크로 지표 | FRED | macro/services/fred_client.py:75 | 동기 | ✓ 지수백오프(3회) | ✗ | ✓ 120/min 추적 | ✗ | 저 |
| SEC EDGAR 10-K | SEC | api_request/sec_edgar_client.py:126 | 동기 | ✓ 재귀(429 시) | ✗ | ✓ 10/sec 명시 | ✗ | 저 |
| 뉴스 수집 | FMP | news/providers/fmp.py:30 | 동기 | ✗ | ✓ 빈 배열 | ✗ | ✗ | 중 |
| LLM 응답 스트리밍 | Gemini | rag_analysis/services/llm_service.py:204 | 비동기 | ✓ 지수백오프 | ✗ | ✓ 429 감지 | ✓ (threshold=5) | 고 |
| 투자 테제 생성 | Gemini | serverless/services/thesis_builder.py:114 | 동기 (Celery) | ✗ | ✗ | ✗ | ✗ | 고 |
| 키워드 생성 | Gemini | serverless/services/keyword_generator.py:114 | 비동기 | ✗ | ✗ | ✗ | ✗ | 고 |
| Neo4j 그래프 | Neo4j | rag_analysis/services/neo4j_service.py:57 | 동기 | ✗ | ✓ 빈 데이터 | ✓ 2초 timeout | ✗ | 중 |
| Market Movers 동기화 | FMP | serverless/tasks.py:22 | Celery (max_retries=3) | ✓ | ✓ 캐시/빈값 | ✓ | ✓ (threshold=5) | 중 |
| 뉴스 키워드 추출 | Gemini/LLM | news/tasks.py:25 | Celery (max_retries=2) | ✓ | ✗ | ✗ | ✗ | 고 |
| Redis 캐시 | Redis | config/settings.py:495 | 동기 | ✗ | ✓ 캐시미스→API | ✗ | ✗ | 중 |
| Celery Broker | Redis | config/settings.py:477 | 비동기 | ✗ | ✗ | ✗ | ✗ | 고 |

---

## FMP 상세

### 공통 클라이언트 분석
**파일**: `api_request/providers/fmp/client.py`

**공통 에러 정책**:
- **재시도**: 최대 3회, 지수 백오프(1s, 2s, 4s)
- **Rate Limit 처리**:
  - 자동 지연: `time.sleep()` 기반 (분당 300회 제한)
  - 일일 한도: 10,000회 추적 (line:110-112)
- **명시적 에러 분류**:
  - `FMPPremiumError(402)`: 즉시 raise, 재시도 안함 (line:149)
  - `FMPAuthError(401/403)`: 즉시 raise
  - `FMPRateLimitError(429)`: 즉시 raise, 상위층에서 재시도 결정
  - 기타 네트워크 에러: 지수 백오프로 재시도 (line:151-159)

### 호출 지점별 (주요 5개)

1. **stocks/tasks.py** — Celery 태스크에서 FMP 호출
   - 상태: ✓ FMPClient 통해 공통 에러 처리 상속
   - 위험도: 중 (Celery 백그라운드이므로 사용자 영향 적음)

2. **serverless/services/fmp_client.py:94-154** — Market Gainers/Losers/Actives 배치 조회
   - 캐시 전략: 5분 (line:118, 135, 152)
   - 에러 처리: `try-except` 후 FMPAPIError 전파 (line:84-92)
   - 위험도: 중 (API 직접 호출, 캐시 fallback 있음)

3. **macro/services/fmp_client.py:128-223** — 지수/섹터 ETF 배치 조회
   - 에러 처리: 개별 quote 호출에서 None 반환 (line:138-144)
   - 위험도: 중 (부분 실패 허용)

4. **news/providers/fmp.py:30-71** — 종목별 뉴스 조회
   - 에러 처리: Exception 발생 시 빈 배열 반환 (line:52-54)
   - 응답 파싱: try-except로 개별 기사 파싱 실패 격리 (line:66-68)
   - 위험도: 중 (부분 실패 격리, fallback 없음)

5. **serverless/services/data_sync.py:74-91** — Market Movers Circuit Breaker 사용
   - Circuit Breaker: `get_circuit('fmp_market_movers', threshold=5, recovery=120s)`
   - 부분 실패: 3가지 type(gainers/losers/actives) 중 1개 실패해도 나머지 진행
   - 위험도: 중 (CB로 격리, 부분 진행 가능)

### Rate Limit 처리
- **분당 제한**: 300회 (FMP Starter Plan)
  - 구현: `time.sleep()` 기반 요청 간 지연 (0.2s) — line:104-107
  - 문제: **분산 환경에서 동기화 부재** → 여러 워커가 동시 요청 시 한도 초과 가능
- **일일 제한**: 10,000회
  - 구현: 단순 카운터 (`self.daily_calls`) — line:110-112
  - 문제: **프로세스 재시작 시 카운터 리셋**, 분산 환경 미지원 → **정확도 낮음**
- **권장 개선**: Redis 기반 분산 rate limiter 적용

### FMPPremiumError(402) 처리
- **감지**: HTTP 402 상태 코드 (line:128-129)
- **처리**: 즉시 `FMPPremiumError` raise, 재시도 없음
- **호출처**:
  - `api_request/providers/fmp/provider.py:247, 293, 339` — Exception catch 후 error response 반환
  - `news/providers/fmp.py` — Exception catch 후 빈 배열 반환
- **위험도**: 낮음 (명시적 처리, 호출처에서 격리)

### 종합 평가
- ✓ 클라이언트 수준의 에러 분류 명확함
- ✓ 지수 백오프 재시도 구현됨
- ✗ **분산 rate limiting 없음** (분당/일일 한도가 단일 프로세스 기준)
- ✗ **Circuit Breaker 개별 호출에는 미적용** (Market Movers 태스크 수준에만 적용)

---

## Gemini 상세

### 공통 호출 패턴
**파일**: `rag_analysis/services/llm_service.py:54-64`, `serverless/services/thesis_builder.py:50-56`

**클라이언트 초기화**:
- `genai.Client(api_key=...)` (line:64)
- Timeout: 기본값 사용 (명시 설정 없음) → **timeout 정책 미정의**

### 호출 지점별 (주요 5개)

1. **rag_analysis/services/llm_service.py:204-241** — 비동기 스트리밍 (RAG 응답)
   - 재시도: ✓ 지수 백오프 (line:251-256, RETRY_DELAYS=[1,2,4]s)
   - Circuit Breaker: ✓ `get_circuit('gemini_rag', threshold=5, recovery=60s)` (line:198-203)
   - Rate Limit 처리: ✓ 429/rate/quota 문자열 감지 (line:249)
   - 타임아웃: ✗ 명시 설정 없음 → **기본값 의존, 스트림 대기 시간 제한 불명확**
   - 위험도: 중 (CB+retry 있음, timeout 미정)

2. **serverless/services/thesis_builder.py:114** — 동기 LLM 호출 (Celery 태스크)
   - 재시도: ✗ `_call_llm_sync()` 내부 구현 확인 필요
   - JSON 파싱: ✓ try-except (line:449, 487, 499)
   - Circuit Breaker: ✗ **미적용**
   - 에러 처리: Exception catch 후 raise (line:151-153)
   - 위험도: 높음 (**Celery 태스크, CB 없음, timeout 불명확**)

3. **serverless/services/keyword_generator.py:114** — 비동기 키워드 생성
   - 재시도: ✗ await 호출에 retry 로직 없음
   - Circuit Breaker: ✗ **미적용**
   - 에러 처리: Exception catch 후 예외 전파 (line:139-140)
   - 위험도: 높음 (**비동기, CB 없음, retry 없음**)

4. **news/services/keyword_extractor.py** — 뉴스 키워드 추출
   - 위치: news/services 디렉토리 (확인 필요)
   - 위험도: 예상 높음

5. **metrics/services/daily_report.py** — 일일 리포트 생성 (genai 사용)
   - 위치: metrics 디렉토리 (상세 확인 필요)
   - 위험도: 예상 높음 (배경 태스크)

### 429 / JSON 파싱 / timeout 처리 매트릭스

| 지점 | 429 감지 | JSON 파싱 | timeout | 신뢰도 |
|-----|---------|---------|--------|-------|
| llm_service.py (비동기) | ✓ 문자열 매칭 | ✓ JSONDecodeError | ✗ | 중 |
| thesis_builder.py (동기) | ✗ | ✓ JSONDecodeError | ✗ | 낮음 |
| keyword_generator.py | ✗ | ✗ (raw 응답) | ✗ | 낮음 |
| rag_analysis llm_service | ✓ | ✓ | ✗ | 중 |

**문제점**:
- ✗ Gemini API 429 응답은 `google.api_core.exceptions.TooManyRequests` 예외로 던져짐 → 문자열 매칭은 불충분
- ✗ JSON 파싱 에러 처리는 있지만, **파싱 실패 시 응답 자체가 버려짐** (부분 처리 없음)
- ✗ Timeout 설정 전무 → 무한 대기 가능

### 종합 평가
- ✓ llm_service.py의 비동기 스트리밍은 CB+retry 구현됨
- ✗ **thesis_builder.py (Celery 태스크) CB 없음** → 장애 전파 위험
- ✗ **keyword_generator.py retry/CB 없음** → 장애 전파 위험
- ✗ **Gemini 429 처리가 불안정** (문자열 매칭 방식)
- ✗ **timeout 정책 미정의**
- ✗ **응답 JSON 부분 실패 처리 없음** (전체 실패 또는 전체 성공)

---

## 기타 의존성

### FRED (Federal Reserve Economic Data)
**파일**: `macro/services/fred_client.py:75-155`

**에러 처리**:
- 재시도: ✓ 3회, 지수 백오프 (2s, 4s, 6s) — line:120-128
- Transient 에러: ✓ 500/502/503/504 명시적 재시도 (line:114-128)
- Permanent 에러: ✓ 401/403/404 즉시 raise, 재시도 안함 (line:106-111)
- Rate Limit: ✓ 분당 120회 + `get_rate_limiter("fred")` 사용 (line:70)

**위험도**: 낮음 (안정적 구현)

### Neo4j
**파일**: `rag_analysis/services/neo4j_driver.py`, `rag_analysis/services/neo4j_service.py:34-86`

**연결 정책**:
- Lazy initialization: ✓ 첫 사용 시 연결 시도, 실패 시 None 반환 (neo4j_driver.py:19-67)
- 반환값: ✓ 모든 메서드가 Neo4j 없으면 빈 데이터 반환 (neo4j_service.py:57-86)
- Timeout: ✓ 쿼리별 2초 timeout 설정 (neo4j_service.py:30)
- Circuit Breaker: ✗ **미적용** (대신 exception catch 후 빈 배열)

**위험도**: 중 (graceful degradation 있음, CB 없음)

### SEC EDGAR
**파일**: `api_request/sec_edgar_client.py:126-224`

**에러 처리**:
- Rate Limit: ✓ 10 req/sec 명시 + 자동 0.1초 지연 (line:98-124)
- 429 처리: ✓ 재귀 호출로 1초 대기 후 재시도 (line:162-166) → **재귀 깊이 제한 없음 (위험)**
- 404 처리: ✓ SECEdgarError raise
- Timeout: ✓ 30초 설정 (line:157)
- CIK 캐싱: ✓ 메모리 캐시 (_cik_cache) (line:113)

**위험도**: 중 (재귀 재시도 상한 없음)

### Redis (캐시 + Celery Broker)
**파일**: `config/settings.py:477-509`

**설정**:
- 캐시: `redis://127.0.0.1:6379/1` (RedisCache)
- Celery Broker: `redis://127.0.0.1:6379/0`
- 채널 레이어: `redis://127.0.0.1:6379` (Channels WebSocket)

**에러 처리**: ✗ 명시 구현 없음
- 캐시 미스 → API 호출 (자동 fallback)
- 캐시 장애 → Django 기본 동작 (에러 전파 가능)

**위험도**: 높음 (**SPOF: Redis 다운 시 Celery 중단**)

---

## Circuit Breaker 후보

### 1순위 (사용자 요청 경로 + SPOF) — 이미 구현됨
1. **Gemini RAG 스트리밍**: `rag_analysis/services/llm_service.py:198-203`
   - ✓ `get_circuit('gemini_rag', threshold=5, recovery=60s)`
   - 이유: 사용자 요청 경로, 비동기 스트리밍 (실시간)

2. **Market Movers 동기화**: `serverless/services/data_sync.py:74-91`
   - ✓ `get_circuit('fmp_market_movers', threshold=5, recovery=120s)`
   - 이유: Celery 태스크, FMP 의존 (외부 API)

### 1순위 (필요 — 미구현)

1. **Gemini 투자 테제 생성**: `serverless/services/thesis_builder.py:58-150`
   - 위치: Celery 태스크 (`serverless/tasks.py` 호출)
   - 경로: 사용자 요청 → API → Celery → thesis_builder._call_llm_sync()
   - 문제: Gemini 429/timeout 시 **전체 테제 생성 실패**, 사용자에게 노출
   - 권장: `CircuitBreaker('gemini_thesis', threshold=3, recovery=120s)` 적용

2. **Gemini 키워드 생성**: `serverless/services/keyword_generator.py:61-120`
   - 위치: Celery 비동기 함수
   - 경로: 사용자 요청 → API → Celery → _call_llm()
   - 문제: retry/CB 없음, 실패 시 재시도 안함
   - 권장: `CircuitBreaker('gemini_keywords', threshold=5, recovery=60s)` + retry 추가

3. **Neo4j 공급망 분석**: `serverless/services/neo4j_chain_sight_service.py:57-141`
   - 위치: `serverless/views.py` REST API 직접 호출
   - 경로: 사용자 REST API → service.get_stock_relationships()
   - 문제: Neo4j 연결 실패 시 빈 데이터 반환 (graceful) 하지만, **timeout 없는 쿼리 대기 가능**
   - 권장: 기존 2초 timeout 유지, CB 추가 불필요 (이미 fallback)

### 2순위 (부분적 개선 필요)

1. **FMP 개별 호출** (Quote, Profile 등): `api_request/providers/fmp/client.py`
   - 문제: View 레벨 동기 호출, CB 없음
   - 경로: 사용자 동기 요청 → FMPClient._make_request()
   - 권장: Provider 레벨 CB 또는 View 레벨 rate limiting 추가

2. **FRED 경제 지표**: `macro/services/macro_service.py`
   - 현황: 개별 메서드에서 FREDClient 호출, retry만 있음
   - 권장: 캐시 활용 충분, CB 불필요 (저 호출량)

### 도입 불필요
- 뉴스 수집 (FMP): 부분 실패 격리되어 있음
- SEC EDGAR: 배경 작업, timeout 설정됨

---

## 요약 및 권고

### 즉시 개선 권고 (P0)

1. **Gemini 투자 테제 생성에 Circuit Breaker 추가** (HIGH IMPACT)
   - 파일: `serverless/services/thesis_builder.py:114`
   - 개선: `_call_llm_sync()` 호출을 CB로 래핑
   - 이유: Celery 태스크, Gemini 429 시 전체 실패 → 사용자 영향 큼
   - 예상 구현:
     ```python
     cb = get_circuit('gemini_thesis', failure_threshold=3, recovery_seconds=120)
     response_text = cb.call(self._call_llm_sync, system_prompt, user_prompt)
     ```

2. **Gemini API 429 처리 안정화** (MEDIUM IMPACT)
   - 파일: `rag_analysis/services/llm_service.py:249`
   - 문제: 문자열 매칭 `'rate' in error_str` → 불안정
   - 개선: `google.api_core.exceptions.TooManyRequests` 예외 명시 catch

3. **Redis 장애 대응 (CRITICAL SPOF)**
   - 파일: `config/settings.py:477`, `config/celery.py`
   - 문제: Redis 다운 시 Celery 중단, 애플리케이션 동작 불가
   - 개선: Redis fallback (in-memory cache) 또는 Celery broker 이중화
   - 임시: 환경 변수로 Celery 비활성화 옵션 추가

4. **FMP 분산 Rate Limiting 도입** (MEDIUM)
   - 파일: `api_request/providers/fmp/client.py:100-123`
   - 문제: 단일 프로세스 기준 지연, 다중 워커 시 한도 초과 가능
   - 개선: Redis 기반 distributed rate limiter 적용
   - 패턴: `api_request/rate_limiter.py`의 RateLimiter 클래스 활용

### 중기 개선 권고 (P1)

5. **Gemini 키워드 생성에 재시도 + CB 추가**
   - 파일: `serverless/services/keyword_generator.py:114`
   - 개선: `_call_llm()` 비동기 호출에 tenacity retry 데코레이터 + CB 추가

6. **Gemini API Timeout 정책 정의**
   - 파일: `rag_analysis/services/llm_service.py:64`, `serverless/services/thesis_builder.py:56`
   - 개선: `genai.Client(api_key=..., timeout=30)` 또는 request 수준 timeout 설정
   - 참고: FRED는 30초 설정됨

7. **SEC EDGAR 재귀 재시도 상한 설정**
   - 파일: `api_request/sec_edgar_client.py:162-166`
   - 현황: 429 시 재귀 호출, 깊이 제한 없음
   - 개선: 재귀 깊이 카운터 추가 또는 반복 루프로 전환

8. **Neo4j 쿼리 실패 로깅 강화**
   - 파일: `rag_analysis/services/neo4j_service.py:130-133`
   - 현황: Exception catch 후 로그만 기록
   - 개선: 실패 원인별 모니터링 메트릭 추가 (timeout, connection refused 등)

### 장기 개선 (P2)

9. **통합 Circuit Breaker 대시보드**
   - 현황: 분산된 CB 상태 추적 불가
   - 개선: Admin 페이지에서 모든 CB 상태 모니터링

10. **LLM 응답 부분 처리 지원**
    - 문제: JSON 파싱 실패 시 전체 응답 손실
    - 개선: 스트림 방식으로 전환, 부분 성공 지원

---

## 파일 위치 참고

| 구성 | 파일 |
|-----|-----|
| FMP 클라이언트 | `api_request/providers/fmp/client.py` |
| FMP Provider | `api_request/providers/fmp/provider.py` |
| Rate Limiter | `api_request/rate_limiter.py` |
| Gemini LLM 서비스 | `rag_analysis/services/llm_service.py` |
| 투자 테제 빌더 | `serverless/services/thesis_builder.py` |
| Market Movers 동기화 | `serverless/services/data_sync.py` |
| Circuit Breaker 구현 | `marketpulse/utils/circuit_breaker.py` |
| FRED 클라이언트 | `macro/services/fred_client.py` |
| Neo4j 서비스 | `rag_analysis/services/neo4j_service.py` |
| SEC EDGAR 클라이언트 | `api_request/sec_edgar_client.py` |
| 설정 (Redis/Celery) | `config/settings.py:477-509` |
