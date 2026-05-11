# Stock-Vis 보안 감사 보고서

- 감사일: 2026-05-02
- 범위: Backend (Django/DRF), Celery 트리거 엔드포인트, LLM 통합, 시크릿 관리, CORS/세션
- 방법: 읽기 전용 정적 분석 (코드 수정 없음)
- 기준: OWASP Top 10 (2021)
- 심각도 등급: CRITICAL / HIGH / MED / LOW / INFO

---

## 0. 요약 (Executive Summary)

| 등급 | 건수 | 핵심 포인트 |
|------|------|-------------|
| CRITICAL | 0 | — |
| HIGH | 3 | 미보호 동기화/Celery 트리거 엔드포인트 (FMP/Gemini quota burning, 리소스 고갈) |
| MED | 5 | 세션/CSRF 쿠키 보안 플래그 미설정, str(e) 누출, LLM 프롬프트 인젝션 부분 노출, chainsight/sec_pipeline 권한 명시 부재 |
| LOW | 5 | 하드코딩된 PII(운영자 이메일/DB user), 정보성 헬스체크 |
| INFO | 6 | SQL 파라미터 바인딩 안전, gitignore 적절, SECRET_KEY/NEO4J 운영 가드 우수 |

가장 시급한 수정 대상은 **`serverless/views.py`의 다수 POST 엔드포인트**이다. 코드 주석에 `TODO: 프로덕션에서는 IsAdminUser로 변경`이 박혀있는 상태로 `AllowAny`가 유지되고 있어, 비인증 사용자가 Celery 태스크를 임의로 트리거할 수 있다. 이는 외부 API 한도 소진(FMP 10,000/day, Gemini 1500 RPD), DB 부하 증가, 비용 폭증으로 직결된다.

---

## 1. 인증/인가 (A01: Broken Access Control)

### DRF 글로벌 기본값 (config/settings.py:341-349)

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticatedOrReadOnly',
],
```

→ **읽기는 모두 허용, 쓰기는 인증 필요**가 글로벌 기본값. `permission_classes` 미지정 뷰는 이 기본값을 따름.

### [HIGH-1] `serverless/views.py` — Celery 트리거가 비인증 허용

**파일**: `serverless/views.py`
**대상**: 23개 이상의 함수형 뷰가 `@permission_classes([AllowAny])` 데코레이트, 그중 다수가 명시적으로 `# TODO: 프로덕션에서는 IsAdminUser로 변경` 주석 보유

| 라인 | 엔드포인트 | 위험 행위 |
|------|-----------|----------|
| 165 | `trigger_sync` (POST `/serverless/sync`) | `sync_daily_market_movers.delay()` — FMP 호출 다수 트리거 |
| 213 | `sync_now` (POST `/serverless/sync-now`) | 동기 sync (스레드 블로킹 + FMP 호출) |
| 381 | `trigger_keyword_generation` (POST `/serverless/keywords/generate-all`) | Gemini 호출 파이프라인 트리거 |
| 447 | `generate_screener_keywords` (POST `/serverless/keywords/generate-screener`) | Gemini 키워드 생성 (최대 100종목) |
| 780 | `trigger_breadth_sync` (POST `/serverless/breadth/sync`) | Celery 트리거 |
| 967 | `trigger_heatmap_sync` (POST `/serverless/heatmap/sync`) | Celery 트리거 |
| 3224 | `(이름 미확인)` | TODO 주석 동일 |

**영향**: 비인증 공격자가 `curl -X POST .../api/v1/serverless/sync-now`로 FMP API 한도(10,000/day Starter)를 분 단위로 소진시킬 수 있음. Gemini Free Tier(1500 RPD)도 동일하게 노출.

**근본 원인**: 개발 단계에서 인증 미적용 + TODO만 남기고 운영 전환 시 미수정.

**수정 방향 (구현 금지, 권고만 기재)**:
- `IsAdminUser` 또는 `IsAuthenticated` + 별도 throttle 추가
- `1373`, `1437`, `1493`, `1528`, `1577`, `1608`, `1644`, `1757` 등 `IsAuthenticated` TODO도 동일 처리

### [HIGH-2] `stocks/views.py:886` — StockSyncAPIView POST 인증 우회

```python
class StockSyncAPIView(APIView):
    # 공개 주식 데이터 동기화는 인증 없이 허용
    permission_classes = []   # ← 명시적으로 빈 리스트 (DEFAULT_PERMISSION_CLASSES 무력화)

    def post(self, request, symbol):
        ...
        sync_service.sync_overview(symbol, force=force)  # FMP 호출
```

`permission_classes = []` → 글로벌 기본값(`IsAuthenticatedOrReadOnly`)도 적용되지 않음. 비인증 사용자가 `force=true`로 캐시 우회하며 FMP 호출 가능. 내부 `check_rate_limit('fmp')` 가드가 있으나, 분 단위 burst 공격에는 취약.

### [HIGH-3] `macro/views.py:359` — DataSyncView 비인증 동기화

```python
class DataSyncView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        thread = threading.Thread(target=_run_data_sync, daemon=True)
        thread.start()  # FRED + FMP + 글로벌 시장 + 캘린더 동기화
```

스레드 백그라운드 동기화. Redis cache 기반 중복 방지(`'running'` 체크)는 있으나 캐시 만료 후 트리거 가능. **인증 + admin 제한 + Celery 큐 사용 권고**.

### [MED-1] `chainsight/api/views.py` — permission_classes 전체 미지정

```python
class ChainSightGraphView(APIView): ...
class ChainSightSuggestionView(APIView): ...
class ChainSightTraceView(APIView): ...
class SeedListView(APIView): ...
class SectorGraphView(APIView): ...
class NeighborGraphView(APIView): ...
class SignalFeedView(APIView): ...
```

**7개 뷰 모두 `permission_classes` 미지정** → 글로벌 기본값 `IsAuthenticatedOrReadOnly` 적용. GET은 비인증 허용. Chain Sight 데이터가 공개 의도라면 `permission_classes = [AllowAny]` **명시**가 안전(향후 글로벌 default 변경 시 의도 명확화). POST/PATCH가 추가될 경우 자동으로 인증 요구되긴 하나, 의도가 코드에 드러나지 않음.

### [MED-2] `sec_pipeline/views.py:28` — FilingDataView 권한 미명시 + 수집 트리거

```python
class FilingDataView(APIView):  # permission_classes 없음 → IsAuthenticatedOrReadOnly
    def get(self, request, symbol):
        result = get_or_collect_filing(symbol)  # ← GET이지만 SEC 수집 사이드이펙트
```

GET이지만 `get_or_collect_filing`이 수집 작업을 트리거하는 사이드이펙트 보유 → 비인증으로 SEC 수집 트리거 가능. **GET이 멱등하지 않음** (REST 원칙 위반 + DoS 표면).

### [INFO-1] 잘 보호된 영역

다음은 적절히 보호되어 있음:
- `users/views.py` — 25개 뷰 모두 `IsAuthenticated` 또는 `IsAdminUser`
- `users/jwt_views.py` — `AllowAny`(signup) / `IsAuthenticated`(나머지) 적절
- `serverless/views_admin.py` — 12개 뷰 모두 `IsAdminUser` (Admin 액션 레지스트리 + 쿨다운 + 감사 로그까지 갖춤. 우수)
- `api_request/admin_views.py` — 5개 Provider 관리 뷰 모두 `IsAdminUser`
- `rag_analysis/views.py` — 15개 뷰 모두 `IsAuthenticated`
- `thesis/views/*.py` — 10개 뷰 모두 `IsAuthenticated`
- `news/api/views.py` — `@action` 단위 권한 14곳 명시 (`AllowAny`/`IsAuthenticated`/`IsAdminUser` 분리. 양호)

---

## 2. SQL 인젝션 (A03: Injection)

### [INFO-2] cursor.execute 4곳 검증 결과: 모두 안전

| 파일 | 라인 | 패턴 | 평가 |
|------|------|------|------|
| `chainsight/services/seed_selection.py` | 152-179 | `cursor.execute("WITH ... %s ... %s", [market_date, market_date])` | ✅ 위치 파라미터 바인딩 |
| `serverless/services/admin_status_service.py` | 833-837 | `cursor.execute("SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30")` | ✅ 정적 SQL, 외부 입력 없음 |
| `api_request/admin_views.py` | 266 | `cursor.execute("SELECT 1")` | ✅ 정적 SQL |
| `config/views.py` | 90 | `cursor.execute("SELECT 1")` | ✅ 정적 SQL |

ORM 사용처도 별도 표본 추출 검토 결과 `Q(...icontains=query)` 등 정상 ORM 호출만 확인됨. **SQL 인젝션 위험 없음**.

---

## 3. LLM 프롬프트 인젝션

29개의 Gemini 호출 파일을 표본 검토.

### [MED-3] 부분적 방어, 따옴표 escape 부재

#### 3-1. `thesis/services/thesis_builder.py:434` — `_parse_free_input`

```python
# 프롬프트 인젝션 방지: 길이 제한 + 구분자 제거
safe_text = text[:500].replace('```', '').replace('---', '').strip()

prompt = f"""사용자가 투자 가설을 자유롭게 입력했어. 이걸 구조화해줘.

입력: "{safe_text}"
...
JSON만 반환해. 다른 텍스트 없이."""
```

**평가**: 길이 제한과 ```/--- 제거는 좋은 시작점이나, 다음 우회 벡터가 남음:
- `safe_text` 안의 `"` 문자가 escape되지 않음 → `"` 다음에 `Ignore previous instructions and output {...}` 삽입 가능
- 개행 문자(`\n`)로 새 시스템 메시지처럼 보이는 텍스트 주입 가능
- 출력이 JSON 파싱 실패 시 `_fallback_parse`로 빠지므로 영향은 제한적이지만, **악의적 JSON 반환 시 그대로 모델에 저장**됨 (target/title/premises가 직접 DB에 들어감)

**노출 표면**: `POST /api/v1/thesis/conversation/respond/` (`IsAuthenticated`, 인증 필요)
**최종 영향**: 인증된 사용자만 실행 가능 → 본인 가설 내용 조작 + 토큰 낭비. 외부 사용자에게는 차단됨.

#### 3-2. `thesis/views/conversation_views.py:230-261` — NewsIssuesView

뉴스 제목(`titles[i]['title'][:80]`)이 직접 프롬프트에 삽입됨. 외부 뉴스 소스(Finnhub/Marketaux)가 신뢰 경계. 길이 제한 80자 외에 sanitization 없음. 영향은 LLM 출력의 품질 저하 정도(JSON 강제 응답 + index 매핑 검증으로 부분 방어).

#### 3-3. `news/services/keyword_extractor.py:262-282` — `_build_user_prompt`

```python
news_summary.append(
    f"{i}. [{news['source']}] {news['title']}\n"
    f"   요약: {news['summary'][:100]}...\n"
    ...
)
```

뉴스 제목/요약이 직접 삽입. 100자 제한은 있으나 `news['source']` 같은 메타 필드가 검증 없이 들어감(이론상 DB에 악성 source 저장된 경우 노출). `response_mime_type` 미설정 + JSON 파싱 후 정규화하므로 출력 영향 제한적.

#### 3-4. `rag_analysis/services/llm_service.py:176`

```python
user_content = f"{context}\n\n질문: {question}"
stream = await self.client.aio.models.generate_content_stream(
    model=self.MODEL,
    contents=user_content,
    config=config,  # system_instruction은 별도
)
```

`context`(데이터 바구니) + `question`(사용자 질문)이 user 메시지로 들어감. system_instruction은 분리되어 있어 우수한 패턴이나, `context`가 사용자 자기 데이터로 구성되므로 자기-인젝션은 가능(영향 제한적, 본인 비용/토큰만 소진).

### [INFO-3] 양호한 패턴

- `thesis/services/prompt_builder.py:519-579` `call_gemini` — `system_instruction` 분리, `response_schema` 강제 (Structured Output), JSON 검증
- `serverless/services/keyword_generator_v2.py`, `relationship_keyword_enricher.py` 등 — 외부 데이터 기반이며 사용자 입력 직접 노출은 없음

---

## 4. 시크릿 관리 (A02: Cryptographic Failures, A07: Identification)

### [INFO-4] gitignore 우수

```
.env
.venv
*.key
```

`git ls-files | grep '^\.env'` → `.env.example`만 추적, `.env`는 추적 안됨. 정상.

`.env` 파일 권한: `-rw-------` (600). 정상.

### [INFO-5] settings.py 운영 가드 우수

```python
SECRET_KEY = os.getenv('SECRET_KEY') or _SECRET_KEY_DEV_FALLBACK
JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or SECRET_KEY  # 분리 가능

if not DEBUG:
    if SECRET_KEY == _SECRET_KEY_DEV_FALLBACK:
        raise ImproperlyConfigured(...)
    if not NEO4J_PASSWORD:
        raise ImproperlyConfigured(...)
```

- `DEBUG=False` 시 `SECRET_KEY`/`NEO4J_PASSWORD` 누락이면 즉시 `ImproperlyConfigured` 발생 → 운영 배포 차단
- JWT 서명 키 별도 회전 가능 구조
- `_SECRET_KEY_DEV_FALLBACK`이 명시적으로 `django-insecure-DEV-ONLY-DO-NOT-USE-IN-PRODUCTION-` 접두사 보유 (체크 가능)

### [LOW-1] 하드코딩된 운영자 이메일 (PII)

`config/settings.py:464-467`:

```python
CELERY_ERROR_RECIPIENTS = [
    'goid545@naver.com',
    'jinie545@gmail.com',
]
```

소스 코드에 개인 이메일 노출. `.env`로 이전 권장 (`os.getenv('CELERY_ERROR_RECIPIENTS', '').split(',')`).

### [LOW-2] DB_USER 기본값에 개인 식별자

`config/settings.py:250`: `'USER': os.getenv('DB_USER', 'byeongjinjeong'),`

운영 환경에서는 환경변수로 오버라이드되므로 영향 미미하나, repo 노출 시 시스템 사용자명이 드러남. 빈 문자열 default + `if not DEBUG: assert os.getenv('DB_USER')` 권고.

### 하드코딩 키 스캔 결과

`grep -rn 'sk-\|api_key.*=\s*"\|password.*=\s*"' --include='*.py'`로 추가 검색 시 다음 외 별다른 평문 키 발견되지 않음:
- `_SECRET_KEY_DEV_FALLBACK` (개발 전용 placeholder, 운영 가드 존재)
- 모든 외부 API 키는 `os.getenv()` 경유

---

## 5. CORS / 쿠키 / XSS / 에러 노출 (A05: Security Misconfiguration)

### CORS

```python
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True
```

- 기본 origin이 dev 전용으로 좁음 ✅
- `CORS_ALLOW_ALL_ORIGINS`가 DEBUG와 분리되어 환경변수로만 제어 ✅
- `CORS_ALLOW_CREDENTIALS=True`이므로 운영 origin은 .env로 명시 추가 필요(현재 코드에는 추가 메커니즘 없음 — 배포 시 `CORS_ALLOWED_ORIGINS` 동적 확장 필요. **현재 운영 배포가 일어나면 prod origin이 차단됨** — 배포 전 코드 수정/환경변수 분리 권고)

### [MED-4] 보안 응답 헤더/쿠키 플래그 부재

`config/settings.py` 전체 검색에서 다음 항목 **모두 미설정**:

| 설정 | 현재 | 권고 |
|------|------|------|
| `SESSION_COOKIE_SECURE` | (없음) | `True` (DEBUG=False) |
| `CSRF_COOKIE_SECURE` | (없음) | `True` (DEBUG=False) |
| `SESSION_COOKIE_HTTPONLY` | Django 기본 True | 명시 권고 |
| `SECURE_SSL_REDIRECT` | (없음) | `True` (DEBUG=False) |
| `SECURE_HSTS_SECONDS` | (없음) | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | (없음) | `True` |
| `SECURE_PROXY_SSL_HEADER` | (없음) | reverse proxy 운영 시 필수 |
| `X_FRAME_OPTIONS` | Django 기본 `DENY` (XFrameOptionsMiddleware로) | 명시 권고 |
| `SECURE_CONTENT_TYPE_NOSNIFF` | (없음) | `True` |
| `SECURE_BROWSER_XSS_FILTER` | (없음) | `True` (deprecated이나 호환) |
| `SECURE_REFERRER_POLICY` | (없음) | `'strict-origin-when-cross-origin'` |

JWT 토큰을 `localStorage`에 저장하는 구조라면 쿠키 플래그 우선순위는 낮아지지만, 세션 인증(`SessionAuthentication`도 활성)을 함께 쓰므로 쿠키 보안은 여전히 필요.

### [MED-5] 에러 메시지에 `str(e)` 노출 — 60곳

내부 예외 메시지를 응답에 그대로 포함하는 패턴이 다수 (위 grep 결과 8개 파일 60건). 대표 예:

- `users/views.py:514` `'detail': str(e)` (refresh 실패 시)
- `users/jwt_views.py:118` `f'회원가입 중 오류가 발생했습니다: {str(e)}'`
- `serverless/views.py` 다수: `error.message: str(e)`
- `rag_analysis/views.py` 다수: `create_error_response("...", str(e))`

**위험**: DB 컬럼명, 외부 API 응답 형식, 파일 경로, 라이브러리 버전 등이 응답에 누출되어 공격자에게 fingerprint 정보 제공. 인증된 사용자에게도 내부 구조가 그대로 노출됨.

**권고**: 사용자 응답에는 `code`만, 상세는 `logger.exception`으로 서버 로그에만 기록.

### XSS 평가

API-only 백엔드(JSON 응답)이며 Django Template 사용은 `templates/`의 일부 dashboard.html(레거시)에 한정. React 프론트가 주력이고 `dangerouslySetInnerHTML` 패턴은 별도 점검 필요(이번 감사 범위 외). `RemoteContent` API에 XSS 필드(예: news.summary)는 sanitize되지 않은 채 저장 → 프론트 렌더링 시 escape 책임 (Next.js JSX 기본 escape이므로 통상 안전).

---

## 6. 인증/세션 (A07: Identification and Authentication Failures)

### [INFO-6] 양호한 부분

- `AUTH_PASSWORD_VALIDATORS` 4종 활성 (UserAttributeSimilarity / MinLength / CommonPassword / NumericPassword)
- JWT 설정: Access 60분 / Refresh 7일 / `ROTATE_REFRESH_TOKENS=True` / `BLACKLIST_AFTER_ROTATION=True`
- `users/jwt_views.py:JWTLogoutView` — refresh 토큰 블랙리스트 처리 ✅
- `users/views.py:WatchlistRateThrottle` — 100/hour throttle 적용

### [LOW-3] api_root 정보 노출

`config/views.py:12-67` `api_root` — 인증 없이 모든 엔드포인트 경로/구조를 JSON으로 반환. 일반적인 API 문서 패턴이지만, 운영 배포 시 attack surface map을 친절히 제공하는 셈. Production에서는 인증 게이트 또는 별도 docs 도메인 분리 권고.

### [LOW-4] HealthCheckView가 컴포넌트 정보 노출

`api_request/admin_views.py:243`:

```python
class HealthCheckView(APIView):
    permission_classes = []  # 인증 불필요
    def get(self, request):
        ...
        "type": "postgresql",
        "active": provider.PROVIDER_NAME,
        ...
```

DB 종류(postgresql), 활성 provider 이름(fmp), 캐시 종류(redis) 등 fingerprint 정보가 비인증 응답에 포함. 운영 환경에서 헬스체크는 200/503 binary 응답으로 축소 권고.

---

## 7. 비밀번호 변경 / 회원가입 흐름

### `users/jwt_views.py:JWTSignUpView`

- `AllowAny` (의도) ✅
- 비밀번호 일치 검증 ✅
- 사용자명/이메일 중복 검증 ✅
- `User.objects.create_user(...)` 사용 (Django 패스워드 해싱 자동) ✅
- **rate limiting 부재** — 무차별 회원가입 시도 가능. `UserRateThrottle('signup', 'X/hour')` 권고.

### `users/jwt_views.py:ChangePasswordJWTView`

- 현재 비밀번호 검증 ✅
- 새 비밀번호 일치 검증 ✅
- 변경 후 새 토큰 발급 ✅
- **`AUTH_PASSWORD_VALIDATORS` 활용 부재** — `User.objects.create_user`의 `password`만 검증되고 `set_password()` 직접 호출 시 validator 미적용. `validate_password(new_password, user)` 명시 호출 권고.

---

## 8. 기타 관찰

### Threading 사용 (Celery 우회)

`users/views.py:282` `PortfolioListCreateView.post` — `threading.Thread(target=background_fetch, daemon=True)` 패턴이 사용됨. `macro/views.py:373`도 유사. macOS SIGSEGV 이슈(common-bugs #25) + Celery + 하네스 정책상 비동기 처리는 Celery로 이전 권고.

### Subquery 안전성

`chainsight/services/seed_selection.py:81-101` — `Subquery + F + Cast` 사용. Django ORM이 자동으로 escape. 안전.

---

## 9. 우선순위별 수정 권고 요약

### Phase 1 — 즉시 (배포 차단급)
1. **HIGH-1**: `serverless/views.py`의 모든 `@permission_classes([AllowAny])` POST 트리거 → `IsAdminUser` 또는 `IsAuthenticated + 별도 throttle`
2. **HIGH-2**: `stocks/views.py:886` `StockSyncAPIView` `permission_classes = []` → `[IsAuthenticated]` 또는 `[IsAdminUser]`
3. **HIGH-3**: `macro/views.py:DataSyncView` → `IsAdminUser` + Celery로 이전

### Phase 2 — 1주 이내
4. **MED-4**: `config/settings.py`에 `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` 추가 (DEBUG=False 분기)
5. **MED-5**: `str(e)` → 사용자 응답 제거, 로거로만 기록 (60곳 일괄)
6. **MED-1, MED-2**: `chainsight/api/views.py`, `sec_pipeline/views.py` 권한 명시
7. **MED-3**: `_parse_free_input`에 따옴표 escape, `repr()` 또는 JSON-quote 적용

### Phase 3 — 코드 정리
8. **LOW-1, LOW-2**: 운영자 이메일 / DB_USER 기본값을 .env로 이전
9. **LOW-3, LOW-4**: api_root, HealthCheckView 운영 모드에서 정보 축소
10. JWTSignUpView throttle 추가
11. ChangePasswordJWTView에 `validate_password()` 명시 호출

---

## 10. 부록 — 검증 명령어 모음

```bash
# permission_classes 미지정 APIView/ViewSet (재현)
grep -rln 'class .*APIView\|class .*ViewSet' --include='*.py' . \
  | xargs grep -L 'permission_classes'

# AllowAny TODO 패턴
grep -rn 'AllowAny.*TODO\|AllowAny.*프로덕션' --include='*.py' .

# str(e) 응답 노출
grep -rn 'str(e)' --include='*.py' . | grep -i 'response\|return'

# cursor.execute 파라미터 바인딩 검증
grep -rn 'cursor.execute' --include='*.py' .

# 하드코딩 시크릿 스캔 (광범위)
grep -rEn '(api[_-]?key|password|secret)\s*=\s*["\047][A-Za-z0-9_+/=-]{16,}["\047]' \
  --include='*.py' .
```

---

**보고서 끝.**
모든 분석은 정적 코드 검토 기반. 동적 침투 테스트, 의존성 CVE 스캔(pip-audit/safety), 컨테이너 이미지 스캔은 별도 수행 권고.
