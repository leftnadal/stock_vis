# Stock-Vis 보안 감사 보고서

- **작성일**: 2026-04-26
- **감사 범위**: Backend 전체 (frontend 제외) — 17개 views 파일, 4개 cursor.execute 사용처, 29개 Gemini 호출 파일, settings.py, .env 관리
- **감사 방법**: 정적 코드 분석 (읽기 전용, 코드 수정 없음)
- **OWASP Top 10 매핑**: A01 (Broken Access Control), A02 (Cryptographic Failures), A03 (Injection), A05 (Security Misconfiguration), A07 (Identification & Auth), A09 (Logging Failures), LLM01 (Prompt Injection)

---

## 요약 (Executive Summary)

| 심각도 | 건수 | 주요 항목 |
|--------|------|----------|
| **CRITICAL** | 6 | 운영 SECRET_KEY 하드코딩(JWT 서명 키 동시 사용), DEBUG=True 고정, serverless admin 엔드포인트 인증 부재(16개), 기본 PERMISSION이 IsAuthenticatedOrReadOnly여서 GET 무차별 노출, NEO4J 기본 패스워드 `stockvis123`, .env 파일 권한 644 |
| **HIGH** | 5 | sec_pipeline `FilingDataView` 인증 없음, stocks 9개 뷰 명시적 권한 미설정, macro `DataSyncView` AllowAny + threading.Thread 무제한, chainsight/api 7개 클래스 권한 미설정, RAG 사용자 입력 sanitization 부재 |
| **MED** | 4 | LLM 프롬프트 컨텍스트(뉴스 본문) 정제 없음, validation/news/api 일부 view 클래스 단위 권한 미선언, str(e) 응답 노출(약 30개 파일), CSRF exempt 뷰 1개 |
| **LOW** | 3 | scripts/test_preset_sharing.py 평문 패스워드, 개인 이메일 하드코딩(CELERY_ERROR_RECIPIENTS), CACHES Redis 무인증 평문 연결 |
| **INFO** | 2 | settings.py에 환경분리 미흡(개발/운영 단일 파일), `.env.example` 정상 운영 |

> **핵심 결론**: DEBUG=True와 SECRET_KEY 하드코딩이 결합돼 JWT 위조까지 가능한 상태이고, serverless admin 엔드포인트 16개가 익명으로 sync/queue 트리거 가능. 운영 배포 전 즉시 차단 필요.

---

## 1. 인증/인가 (A01, A07)

### 1.1 [CRITICAL] DEFAULT_PERMISSION_CLASSES = IsAuthenticatedOrReadOnly

`config/settings.py:326-328`

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticatedOrReadOnly',
],
```

- 영향: 명시적 `permission_classes` 미지정 뷰의 GET이 모두 익명 허용. 아래 16개 뷰가 즉시 노출됨.
- 영향 받는 파일과 클래스:

| 파일 | 클래스 | 위험 |
|------|--------|------|
| `stocks/views.py:75` | StockListAPIView | 종목 목록 누출 |
| `stocks/views.py:159` | StockSearchAPIView | 검색 패턴 노출 |
| `stocks/views.py:212` | StockChartDataAPIView | 차트 데이터 |
| `stocks/views.py:599/675/748/820` | BalanceSheet/Income/CashFlow/Complete | 재무제표 |
| `stocks/views.py:886` | StockSyncAPIView (`permission_classes = []` 명시) | **쓰기**: sync 트리거 |
| `stocks/views_eod.py:20/51/110` | EODDashboardView 외 2개 | dashboard, signal, pipeline log |
| `stocks/views_search.py:18/91/146` | SymbolSearchView 외 2개 | 검색·검증·인기 |
| `stocks/views_indicators.py:16` | TechnicalIndicatorView | 지표 노출 |
| `stocks/views_mvp.py:17/69` | StockMVPListView 외 1개 | 종목 데이터 |
| `chainsight/api/views.py:54/104/179/302/310/439/618` | 7개 클래스 (Graph/Suggestion/Trace/SeedList/SectorGraph/NeighborGraph/SignalFeed) | 그래프 분석 데이터 |
| `validation/api/views.py:52/173/317/421/495` | 5개 클래스 (제외: PeerPreferenceView) | LLM Peer 필터(POST 가능) |
| `sec_pipeline/views.py:28` | FilingDataView | **on-demand 수집 트리거**(202) |
| `news/api/views.py:42` | NewsViewSet 클래스 단위 (액션별 데코레이터로만 부분 보호) | 미보호 액션 노출 |

권장 조치: `DEFAULT_PERMISSION_CLASSES`를 `IsAuthenticated`로 강화하고 명시적 `AllowAny`만 공개.

---

### 1.2 [CRITICAL] serverless/views.py — admin 엔드포인트 16개가 AllowAny

`serverless/views.py` 전반. `# TODO: 프로덕션에서는 IsAdminUser로 변경` 주석이 16개 위치에 존재.

대표 사례:

```python
# serverless/views.py:164-188 (trigger_sync)
@api_view(['POST'])
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
def trigger_sync(request):
    task = sync_daily_market_movers.delay(target_date=date_str)
```

- 영향: 누구나 Celery 태스크 트리거, 스크리너 재계산, ETF 시드 갱신 등 **자원 고갈/금융 데이터 변조** 가능. FMP/Gemini 비용 폭증 위험.
- 라인: 165, 213, 326, 381, 447, 521, 558, 728, 780, 816, 921, 967, 1003, 1072, 1149, 1207, 1277, 1373, 1437, 1493, 1528, 1577, 1608, 1644, 1711, 1757 (총 16개 TODO 마커 + 추가 다수)

권장 조치: 모든 admin/관리자 트리거에 `IsAdminUser` 적용. 공개 read-only 엔드포인트는 분리 모듈로 이전.

---

### 1.3 [HIGH] macro/views.py — DataSyncView AllowAny + threading.Thread

`macro/views.py:353-386`

```python
class DataSyncView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        ...
        thread = threading.Thread(target=_run_data_sync, daemon=True)
        thread.start()
```

- 영향: 비인증 사용자가 무제한 백그라운드 sync를 호출 가능 → 외부 API quota 소진 + 데몬 스레드 누적.

권장 조치: `IsAdminUser`로 제한 + Celery 태스크로 일원화.

---

### 1.4 [HIGH] sec_pipeline/views.py — FilingDataView 권한 미설정

`sec_pipeline/views.py:28-46`

```python
class FilingDataView(APIView):
    def get(self, request, symbol):
        from .on_demand import get_or_collect_filing
        result = get_or_collect_filing(symbol)
```

- 영향: 임의 symbol에 대해 SEC EDGAR 수집(외부 API 호출) 익명 트리거 → quota 소진.

권장 조치: 최소 `IsAuthenticated`. 트리거 측 함수에 rate limit 적용.

---

### 1.5 [HIGH] users/views.py — Users/PublicUser/LogIn은 의도된 AllowAny이나 명시 부재

`users/views.py:78/111/143` (Users, PublicUser, LogIn) — 회원가입/로그인은 정상이지만 명시적 `permission_classes = [AllowAny]` 미선언 → DEFAULT가 `IsAuthenticatedOrReadOnly`라 POST 회원가입이 막힐 수 있고 의도가 불명확.

권장 조치: 의도된 공개 뷰에 `[AllowAny]` 명시.

---

## 2. 인젝션 (A03)

### 2.1 SQL 인젝션 — 모두 안전

검사 대상 4곳 모두 파라미터 바인딩(`%s`) 또는 정적 SQL 사용. **위험 없음.**

| 파일 | 라인 | 분석 |
|------|------|------|
| `chainsight/services/seed_selection.py:152-179` | `%s` 바인딩(`market_date` 두 번) | ✅ 안전 |
| `serverless/services/admin_status_service.py:833` | 정적 `SELECT relname, n_live_tup FROM pg_stat_user_tables` | ✅ 안전 |
| `api_request/admin_views.py:266` | 정적 `SELECT 1` | ✅ 안전 |
| `config/views.py:90` | 정적 `SELECT 1` | ✅ 안전 |

전체 코드베이스에 `f-string` 기반 SQL, `.raw()`, `RawSQL`, `extra()` 사용 **0건** 확인.

---

## 3. LLM 프롬프트 인젝션 (LLM01)

### 3.1 [HIGH] RAG Analysis — 사용자 입력 무방비 삽입

`rag_analysis/views.py:552` → `rag_analysis/services/llm_service.py:176`

```python
# views.py:552
message = request.data.get('message', '').strip()
# llm_service.py:176
user_content = f"{context}\n\n질문: {question}"
```

- 영향: 길이 제한·구분자 제거·system prompt 분리 없음. 사용자가 자신의 분석 결과만 조작 가능하지만, 시스템 프롬프트 누출/지표 환각 유발 가능.

권장 조치: `_sanitize_for_prompt` (thesis/services/indicator_matcher.py:175 패턴) 재사용 + 시스템 프롬프트는 `system_instruction`으로 분리(이미 설정됨, 단 사용자 message 자체는 정제 필요).

---

### 3.2 [MED] thesis prompt_builder — 외부 뉴스 본문 정제 없이 삽입

`thesis/services/prompt_builder.py:806-859` (`build_suggestion_prompt`)

```python
context_parts = [f'뉴스 제목: {news_title}']
if keyword:  context_parts.append(f'키워드: {keyword}')
if summary:  context_parts.append(f'요약: {summary}')
```

- 영향: news_title/summary는 외부 뉴스 API에서 수집된 텍스트. `## 규칙\n새 지시: ...` 같은 인젝션 페이로드가 포함되면 가설 생성 로직 변조 가능.

권장 조치: news 컨텍스트 필드도 `_sanitize_for_prompt` 처리 + 길이 상한.

---

### 3.3 [INFO] 안전한 사례 — `_sanitize_for_prompt` 적용

다음 위치는 길이 제한(500자) + 구분자(```/---) 제거가 적용돼 양호:

- `thesis/services/indicator_matcher.py:175-183, :199-204`
- `thesis/services/thesis_builder.py:434` (`_parse_free_input`의 `text[:500].replace('```','').replace('---','').strip()`)

이 패턴을 RAG/news prompt에 동일하게 확산 권장.

---

### 3.4 [MED] news keyword_extractor — 뉴스 본문이 그대로 user_prompt에 삽입

`news/services/keyword_extractor.py:262-282` (`_build_user_prompt`)

- 영향: 뉴스 50건의 title/summary가 정제 없이 삽입. 원격 인젝션 가능 (악의적 외부 매체).
- 다만 응답 파싱 시 schema 검증·길이 절단(`text[:35]`)·sentiment whitelist 적용 → 후속 영향은 제한적.

권장 조치: 입력 단계에서도 구분자 제거(특히 ``` ` ` ` ``과 `---`) + 길이 캡 강화.

---

## 4. 시크릿 관리 (A02, A05)

### 4.1 [CRITICAL] SECRET_KEY 하드코딩 + JWT SIGNING_KEY 동일

`config/settings.py:140, 342`

```python
SECRET_KEY = 'django-insecure-hvwb-ms8%a@fh7_pf@obr@edq6(h41bj+$yetj#h!wg7#(b(&8'
...
'SIGNING_KEY': SECRET_KEY,
```

- 영향: 코드/리포지토리에 평문 노출 시 즉시 **JWT 위조** 가능. `django-insecure-` 프리픽스는 startproject 기본값이라 운영 사용 금지.

권장 조치: `os.getenv('SECRET_KEY')` + 누락 시 fail-fast. 별도 JWT 키(`SIMPLE_JWT_SIGNING_KEY`) 분리 권장.

---

### 4.2 [CRITICAL] Neo4j 기본 패스워드 `stockvis123`

`config/settings.py:32, 119` (중복 정의)

```python
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'stockvis123')
```

- 영향: `.env`에 NEO4J_PASSWORD 미설정 시 약한 디폴트로 연결. 운영 환경에서 흔한 사고.

권장 조치: 디폴트 제거 → 미설정 시 `ImproperlyConfigured` 발생.

---

### 4.3 [CRITICAL] .env 파일 권한 644

```
-rw-r--r--  1 byeongjinjeong  staff  1736 Apr 25 12:07 .env
```

- 내용 일부:
  ```
  FMP_API_KEY="KF9EtfNmyD4sOA1Cz3I896nhf9pMq0p9"
  MARKETAUX_API_KEY="vJltecNa6vdajQkvhXv12pPsi1VmBFWTMkp7p3BP"
  FINNHUB_API_KEY="d4raofhr01qrphaeg70gd4raofhr01qrphaeg710"
  ```
- 영향: 동일 머신의 모든 사용자가 평문 API 키 열람 가능. **이미 노출 가능성이 있으므로 키 회전 권장.**

권장 조치:
1. `chmod 600 .env`
2. 위 3개 키 즉시 회전 (FMP/Marketaux/Finnhub 콘솔에서 revoke + 재발급)
3. 보고서에 키가 인용된 이 문서도 외부 공유 금지

> **검증 결과**: `git log --all --diff-filter=A -- .env` → 0건. `.env`는 git history에 포함된 적 없음(✅). `.gitignore`에 `.env` 등록 확인(L9).

---

### 4.4 [LOW] 테스트 스크립트 평문 패스워드

`scripts/test_preset_sharing.py:41` — `password='testpass123'` (테스트 픽스처).

- 영향: 운영 코드 아니므로 위험은 낮으나, 동일 패턴 확산 시 incident 유발 가능.

---

## 5. CORS / XSS / 에러 노출 (A05, A09)

### 5.1 [CRITICAL] DEBUG = True (코드 고정)

`config/settings.py:143`

```python
DEBUG = True
```

- 영향:
  - 예외 발생 시 **스택트레이스/SQL/세팅 전체 노출**
  - `CORS_ALLOW_ALL_ORIGINS = True` 자동 활성 (L289-291)
  - 정적 파일/템플릿 디버그 화면

권장 조치: `DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'`로 분리.

---

### 5.2 [CRITICAL] CORS_ALLOW_ALL_ORIGINS — DEBUG=True 환경에서 모든 origin 허용

`config/settings.py:289-294`

```python
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
```

- 영향: DEBUG=True가 운영에 그대로 배포되면 **임의 도메인의 자바스크립트가 인증된 사용자 자격으로 API 호출 가능** (`CORS_ALLOW_CREDENTIALS = True`와 결합되면 더 위험).

권장 조치: 5.1과 함께 환경변수로 분리 + 운영 화이트리스트 명시.

---

### 5.3 [INFO] 보안 헤더 미설정

`SECURE_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `X_FRAME_OPTIONS`(기본값만), `SECURE_CONTENT_TYPE_NOSNIFF` 모두 미정의.

권장 조치: 운영 settings 별도 파일(`settings_prod.py`)에 보안 헤더 일괄 추가.

---

### 5.4 [MED] str(e) 응답 노출

다음 패턴이 약 30개 파일에 존재 — 내부 예외 메시지가 클라이언트로 전달:

```python
return Response({'error': str(e)}, status=500)
```

대표 위치:

- `stocks/views_search.py:86, 141` — `f'서버 오류: {str(e)}'`
- `serverless/views_admin.py:163, 183, 203, 223, 243, 263` — Admin 응답이지만 inner exception 노출
- `serverless/tasks.py:715, 1067, 1502` — 결과 snapshot에 저장

- 영향: ORM/Connection 오류, 외부 API 응답 일부 누출 → 정찰(reconnaissance) 단서 제공.

권장 조치: 표준 에러 코드(`'INTERNAL_ERROR'`) + 로그에는 `logger.exception`, 응답에는 generic message.

---

### 5.5 [MED] CSRF Exempt

`config/views.py:6` — `from django.views.decorators.csrf import csrf_exempt` 임포트만 확인됨. 실제 적용 위치는 단일 파일이며 health check용일 가능성. 적용된 모든 위치를 별도 점검 필요.

---

### 5.6 [LOW] CACHES — Redis 평문 + 무인증

`config/settings.py:404-409`

```python
'BACKEND': 'django.core.cache.backends.redis.RedisCache',
'LOCATION': 'redis://127.0.0.1:6379/1',
```

- 영향: 로컬 한정이면 OK. 운영에서 외부 Redis로 옮길 때 `rediss://` + AUTH 필요.

---

### 5.7 [LOW] 개인 이메일 하드코딩

`config/settings.py:444-447`

```python
CELERY_ERROR_RECIPIENTS = [
    'goid545@naver.com',
    'jinie545@gmail.com',
]
```

- 영향: 정보 유출 수준은 낮음. 운영팀 메일링 리스트로 교체 권장.

---

## 6. 추가 관찰

### 6.1 환경 분리 부재

`config/settings.py` 단일 파일로 개발/운영 분기 미흡. `config/settings_test.py`만 존재.

권장 구조:
```
config/
  settings/
    base.py
    dev.py
    prod.py
    test.py
```

### 6.2 .env.example 정상 운영

`.env.example`에 키 이름만 나열, 실제 값 없음 확인. 양호.

### 6.3 JWT 토큰 회수

`rest_framework_simplejwt.token_blacklist` 활성, `BLACKLIST_AFTER_ROTATION=True`. 양호.

### 6.4 패스워드 검증

`AUTH_PASSWORD_VALIDATORS` 4종 활성. 다만 최소 길이가 기본(8자)이므로 운영에서는 `MinimumLengthValidator(min_length=12)` 권장.

---

## 7. 우선순위별 조치 권장 (Triage)

### 즉시 (배포 전 차단)

1. `SECRET_KEY` 환경변수화 + `.env` 권한 600 + 노출된 API 키 3종 회전 (4.1, 4.3)
2. `DEBUG=False` 강제 환경변수화 (5.1)
3. `serverless/views.py` admin 엔드포인트 16개 `IsAdminUser` 적용 (1.2)
4. `DEFAULT_PERMISSION_CLASSES`를 `IsAuthenticated`로 강화 (1.1)

### 1주 내

5. NEO4J 기본 패스워드 제거 (4.2)
6. CORS 운영 화이트리스트 분리 (5.2)
7. `sec_pipeline.FilingDataView`, `macro.DataSyncView` 인증 추가 (1.3, 1.4)
8. RAG 사용자 메시지 sanitization (3.1)

### 1개월 내

9. settings 환경 분리 (6.1) + 보안 헤더 일괄 적용 (5.3)
10. str(e) 응답 일괄 정리 (5.4)
11. news/thesis prompt 컨텍스트 정제 확산 (3.2, 3.4)

---

## 부록 A — 검사 명령

```bash
# SQL 인젝션 후보
grep -rl 'cursor.execute' --include='*.py' .
grep -rn "f\"SELECT\|f'SELECT\|.raw(\|RawSQL" --include='*.py' .

# 권한 누락
grep -L "permission_classes" $(find . -name 'views*.py' -not -path './frontend/*')

# 시크릿
grep -n "SECRET_KEY\|SIGNING_KEY\|password\s*=\s*['\"]" config/settings.py

# 에러 노출
grep -rn "'error':\s*str(e)" --include='*.py' .
```

## 부록 B — 다음 감사에서 추가 검토할 항목

- WebSocket consumer (`*/consumers.py`) 인증 미들웨어 검증
- Celery task 직렬화 페이로드(특히 `signature` 적용 여부)
- 외부 데이터(`SEC EDGAR`, `FMP`, `Finnhub`) → DB 저장 시 schema 강제 검증
- Frontend의 `dangerouslySetInnerHTML` 사용처(이번 감사 범위 외)
- Admin 페이지(`/admin/`) ALLOWED_HOSTS / SECURE_PROXY_SSL_HEADER 설정
