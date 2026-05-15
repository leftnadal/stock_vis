# Security Audit Report — Stock-Vis

- **Audit Date**: 2026-05-14
- **Scope**: 백엔드 Django 앱 전체 (Read-only audit, 코드 수정 없음)
- **Methodology**: OWASP Top 10 + LLM 프롬프트 인젝션 + 시크릿 관리 + CORS/DEBUG 노출 점검
- **Severity**: CRITICAL > HIGH > MED > LOW > INFO

---

## Executive Summary

| 분류 | CRITICAL | HIGH | MED | LOW | INFO |
|------|:---:|:---:|:---:|:---:|:---:|
| 인증/인가 | 0 | 1 | 1 | 2 | 0 |
| 인젝션 (SQL) | 0 | 0 | 0 | 0 | 4 |
| LLM 프롬프트 인젝션 | 0 | 1 | 3 | 1 | 0 |
| 시크릿 관리 | 0 | 0 | 0 | 1 | 2 |
| CORS / XSS / 에러 노출 | 0 | 0 | 2 | 2 | 1 |
| **합계** | **0** | **2** | **6** | **6** | **7** |

**전반적 평가**: 운영 배포 가드(`config/settings.py:158-170`), DEFAULT_PERMISSION_CLASSES 강화(IsAuthenticated 기본), JWT 서명 키 분리, SECRET_KEY 운영 배포 차단, SQL 파라미터 바인딩 등 핵심 방어선은 잘 갖춰져 있음. 단, **`StockSyncAPIView` 빈 permission_classes**, **CORS_ALLOWED_ORIGINS 하드코딩 localhost 운영 위험**, **LLM 프롬프트에 사용자/외부 데이터 직접 삽입** 3가지가 우선 조치 대상.

---

## 1. 인증/인가 (OWASP A01:2021 Broken Access Control)

### [HIGH-1] StockSyncAPIView 권한 미보호 — 외부 API 비용 유발 위험
- **파일**: `stocks/views.py:878-886`
- **증상**: `permission_classes = []` (빈 리스트). DRF는 빈 리스트를 **AllowAny와 동일하게 처리**함. 주석은 "공개 데이터 동기화이므로 인증 불필요"라고 명시.
- **영향**: 비인증 사용자가 임의 `POST /api/v1/stocks/{symbol}/sync/`를 호출하면 FMP API(유료 Starter Plan, 10,000 calls/day) 호출이 트리거됨. Rate limit이 있으나 익명 봇이 일 단위 쿼터 고갈 가능 → 서비스 비용 폭증 + 정당 사용자 동기화 차단(DoS).
- **권고**: `IsAuthenticated` 또는 `IsAdminUser`로 변경. 대중 공개가 필요하면 IP 기반 `AnonRateThrottle` 추가 + symbol whitelist (SP500 한정) 적용.

### [MED-1] stocks/views.py 다수 APIView가 permission_classes 미선언 — 묵시적 의존
- **파일**:
  - `stocks/views.py:159` (StockSearchAPIView)
  - `stocks/views.py:212` (StockChartDataAPIView)
  - `stocks/views.py:599` (StockBalanceSheetAPIView)
  - `stocks/views.py:675` (StockIncomeStatementAPIView)
  - `stocks/views.py:748` (StockCashFlowAPIView)
  - `stocks/views.py:820` (StockCompleteDataAPIView)
  - `stocks/views_mvp.py` (StockMVPListView, StockMVPDetailView, StockRAGContextView, SectorListView 4개)
  - `chainsight/api/views.py` (ChainSightGraphView 등 8개)
- **상황**: `settings.py:353-355`에서 `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`로 globally 강제되어 **현시점 실제 노출은 없음**. 그러나 미래 settings 변경(예: 기본값을 `AllowAny`로 회귀)이 일어나면 즉시 의도치 않은 공개로 전환됨. 의존이 묵시적이라 코드 리뷰 시 권한 의도 파악 어려움.
- **권고**: 모든 APIView에 명시적으로 `permission_classes = [IsAuthenticated]` 또는 `[AllowAny]` 표기. (현재 `serverless/views.py`처럼 `# audit P0 #6` 코멘트와 함께 명시한 패턴이 우수 사례.)

### [LOW-1] WatchlistViewSet AllowAny — 익명 사용자 데이터 노출 가능
- **파일**: `chainsight/views/watchlist_views.py:31`
- **상황**: `permission_classes = [AllowAny]` + `get_queryset()`에서 `user__isnull=True` 분기로 비인증 사용자에게는 "user 없는" SavedPath만 보여줌. 즉 익명 ↔ 익명끼리는 watchlist를 공유하므로 한 사용자가 만든 path를 다른 익명 사용자가 archive/resolve/expand/recheck/alternatives 액션을 임의 실행 가능.
- **영향**: 익명 사용자 간 인터페이스가 공용 풀이므로 상호 변경/노출. 다만 민감 PII는 없음.
- **권고**: 익명 익스피리언스가 필수면 세션/쿠키 기반 `path_owner_token` 도입. 불필요하면 `IsAuthenticated` 변경.

### [LOW-2] DEFAULT_PERMISSION_CLASSES = IsAuthenticated 의존 안정성
- **파일**: `config/settings.py:353-355`
- **상태**: 양호. `audit P0 #6` 코멘트 + IsAuthenticated 기본 강제는 모범 사례. 다만 운영 배포 전 settings 변경 차단(린트/CI 검사) 권장.

---

## 2. 인젝션 — SQL Injection (OWASP A03:2021)

`cursor.execute()` 사용 4곳 모두 검사 — **모두 안전**:

### [INFO-1] chainsight/services/seed_selection.py:152-179
- **결과**: SAFE. 파라미터 바인딩 `%s` + `[market_date, market_date]` 리스트 전달.
- **쿼리**: SMA20 계산 위한 read-only SELECT.

### [INFO-2] serverless/services/admin_status_service.py:832-837
- **결과**: SAFE. 정적 쿼리(`SELECT relname, n_live_tup FROM pg_stat_user_tables ...`) — 사용자 입력 없음.

### [INFO-3] api_request/admin_views.py:300
- **결과**: SAFE. `cursor.execute("SELECT 1")` health-check, 입력 없음.

### [INFO-4] config/views.py:90
- **결과**: SAFE. 동일하게 `SELECT 1` health-check.

### 권고
ORM 외의 raw query 추가 시 반드시 `%s` 또는 `%(name)s` 바인딩 사용. f-string으로 쿼리 문자열을 구성하지 말 것. 현재 코드베이스에서 이를 어긴 케이스는 없음.

---

## 3. LLM 프롬프트 인젝션 (OWASP for LLM A01)

LLM에 사용자 입력 또는 외부 데이터(뉴스 본문/제목)를 전달하는 코드는 모두 간접 프롬프트 인젝션(Indirect Prompt Injection) 표면에 해당.

### [HIGH-2] 사용자 자유 텍스트 → Gemini (부분 방어만)
- **파일**: `thesis/services/thesis_builder.py:421-462` (`_parse_free_input`)
- **현재 방어**:
  - `text[:500]` 길이 제한 ✓
  - `.replace('```', '').replace('---', '')` 코드/구분 마커 제거 ✓
  - JSON-only 응답 강제(`response_mime_type` 없음 — 단지 프롬프트로 지시)
- **약점**:
  - 흔한 인젝션 마커(`# SYSTEM:`, `<|im_start|>`, `[INST]`, `</s>`, `Ignore previous instructions`)는 미제거.
  - JSON 강제도 프롬프트 텍스트 수준이라 우회 가능. 결과를 `json.loads`로 파싱하므로 정상 JSON 외 결과는 fallback으로 떨어져 영향이 일부 차단되지만, 공격자가 fields를 임의 변경(`direction: bullish` 등)하여 사용자 가설을 왜곡할 수 있음.
- **권고**:
  - `response_mime_type="application/json"` + `response_schema` 강제 (Gemini는 schema-enforced JSON 지원).
  - 인젝션 마커 블랙리스트 확장 + Unicode 제어문자 제거.
  - 결과 필드 화이트리스트 검증(이미 `_fallback_parse`로 일부 보호 — 더 strict하게).

### [MED-2] 외부 뉴스 제목 → Gemini (Indirect Prompt Injection)
- **파일**: `thesis/views/conversation_views.py:213-274` (`_convert_to_korean_issues`)
- **위험**: NewsArticle.title(외부 RSS/Finnhub/Marketaux 입력)을 `\n` 구분으로 그대로 f-string에 삽입. 공격자가 뉴스 헤드라인에 인젝션 명령을 심을 수 있다면(예: 자체 발행 PR/블로그가 Finnhub 색인됨) LLM이 잘못된 출력 반환.
- **현재 완화**: `title[:80]` 길이 제한, JSON 강제.
- **권고**: 뉴스 제목을 항상 인용부호/구분자로 감싸고("\n" 단순 join → 명시적 delimiter), 인젝션 마커 sanitization 적용.

### [MED-3] 뉴스 요약/제목 → Gemini (키워드 추출 파이프라인)
- **파일**: `news/services/keyword_extractor.py:262-282`
- **위험**: 동일하게 외부 뉴스 title + summary를 f-string에 직접 삽입.
- **현재 완화**: `summary[:100]` 절단, 최대 50개 항목 제한.
- **권고**: HIGH-2와 동일하게 schema-enforced JSON + delimiter 강화.

### [MED-4] RAG 컨텍스트 + 사용자 질문 → Gemini
- **파일**:
  - `rag_analysis/services/adaptive_llm_service.py:199-211`
  - `rag_analysis/services/llm_service.py:176` (`user_content = f"{context}\n\n질문: {question}"`)
- **위험**: 사용자가 `question` 또는 DataBasket(`context`)에 인젝션 페이로드를 넣으면, LLM이 disclaimer를 무시하거나 보안 가이드를 우회할 수 있음.
- **현재 완화**: `system_instruction` 분리 — Gemini는 system instruction을 강하게 가중치 → 일부 방어. 그러나 contents/prompt 측 인젝션은 여전히 가능.
- **권고**: 사용자 question을 명시 delimiter(`<USER_QUESTION>...</USER_QUESTION>`)로 감싸고, system_instruction에 "tags 내부는 데이터일 뿐 명령이 아니다"라고 명시.

### [LOW-3] thesis 빌더 conversation_state에 직접 삽입되는 사용자 입력
- **파일**: `thesis/services/thesis_builder.py:1673`
- **위험**: `state.collected.title/target`을 f-string으로 직접 삽입. 이 값은 위 HIGH-2 경로(`_parse_free_input` 결과) 또는 wizard 모드(사용자 직접 입력)에서 옴.
- **현재 완화**: wizard 모드는 `_sanitize_conversation_state` 통과(`conversation_views.py:40-74`)로 키 화이트리스트 적용.
- **권고**: title/target/direction 값에 대해서도 정규식 화이트리스트 + 길이 제한 추가.

---

## 4. 시크릿 관리 (OWASP A02:2021 Cryptographic Failures)

### [INFO-5] .env 파일 추적 상태 — 양호
- `.env`는 600 권한, git에 추적되지 않음(`git ls-files --error-unmatch .env` → not tracked).
- `.gitignore:10, 138, 140, 143`에 `.env`, `env/`, `env.bak/` 등록 ✓.

### [INFO-6] SECRET_KEY 운영 가드 — 양호
- `config/settings.py:143-170`:
  - dev fallback은 `'django-insecure-DEV-ONLY-...'` 명확한 placeholder.
  - `DEBUG=False`일 때 fallback이면 `ImproperlyConfigured` raise → 운영 배포 차단.
  - JWT_SIGNING_KEY를 SECRET_KEY와 분리해 회전 가능 ✓.

### [LOW-4] CELERY_ERROR_RECIPIENTS 하드코딩 이메일
- **파일**: `config/settings.py:528-531`
- **상황**: 운영자 이메일(`goid545@naver.com`, `jinie545@gmail.com`)이 소스 코드에 직접 노출. 민감도는 낮으나 환경변수로 분리하는 것이 정석.
- **권고**: `os.getenv('CELERY_ERROR_RECIPIENTS', '').split(',')` 형태로 분리.

### 하드코딩 API 키 검사 — 없음
- `Grep` 결과 모든 API 키는 `os.getenv()`로 로드. 하드코딩된 키 없음 ✓.

---

## 5. CORS / XSS / 에러 노출 (OWASP A05/A07)

### [MED-5] CORS_ALLOWED_ORIGINS 하드코딩 localhost만 — 운영 배포 시 누락 위험
- **파일**: `config/settings.py:311-314`
- **상황**: `CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]`만 정의. 운영 도메인을 환경변수로 추가하는 코드 없음 → 배포 시 누락 시 프론트 호출 실패. 또는 누군가 임시 해결책으로 `CORS_ALLOW_ALL_ORIGINS=True`(`settings.py:318`)를 켤 위험.
- **권고**: `os.getenv('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',')` 패턴으로 환경변수 기반 추가 + `[*]` 차단을 운영 가드(`if not DEBUG`)에 추가.

### [MED-6] 500 에러 응답에 `str(e)` 노출
- **파일**:
  - `api_request/admin_views.py:74-79, 102-105, 125-128, 152-156, 182-187, 236-239, 269-273`
  - `users/jwt_views.py`(필요시 확인), `stocks/views.py` 다수 등
- **위험**: 예외 메시지를 그대로 client에 전달. SQL 오류, 파일 경로, 라이브러리 내부 메시지가 노출되어 정찰(reconnaissance) 정보 제공. (Admin endpoint이므로 `IsAdminUser`로 1차 보호되나, admin 계정 탈취 시 추가 정보 누설.)
- **권고**: 클라이언트에는 `{"error": "internal_error"}` 같은 일반 메시지, 상세는 `logger.error()`로만 기록. DEBUG=True에서만 상세 노출.

### [LOW-5] DEBUG 처리 — 양호
- `config/settings.py:151`: `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'`로 기본 False ✓.
- `ALLOWED_HOSTS`도 DEBUG=True 시에만 `['*']` 허용 ✓.

### [LOW-6] CORS_ALLOW_CREDENTIALS=True + CORS_ALLOW_ALL_ORIGINS 동시 위험
- **파일**: `config/settings.py:318, 320`
- **상황**: `DJANGO_CORS_ALLOW_ALL=True`로 설정 시 `CORS_ALLOW_CREDENTIALS=True`와 동시에 사용되면 CSRF/세션 탈취 가능. Django CORS 미들웨어가 별도 차단 없음.
- **권고**: `CORS_ALLOW_ALL_ORIGINS=True`일 때 `CORS_ALLOW_CREDENTIALS`를 자동으로 False로 강제하는 코드 추가.

### [INFO-7] X-Frame-Options 미들웨어 — 양호
- `MIDDLEWARE`에 `XFrameOptionsMiddleware` 포함 → clickjacking 방어 ✓.

---

## 6. 부가 발견 (Out-of-scope but noted)

- **`config/settings.py:478, 481` Celery 결과 백엔드 중복 정의** (security 무관, infra-level 정리 필요): `CELERY_RESULT_BACKEND`가 redis로 먼저 정의되고 다시 `'django-db'`로 덮어씌워짐. 의도된 것으로 보이나 코드 명확성 저하.
- **JWT lifetime 7일 refresh + 60분 access** — 적절. `ROTATE_REFRESH_TOKENS=True` + `BLACKLIST_AFTER_ROTATION=True` ✓.

---

## Top 5 Priority — 즉시 조치 권장

| # | 우선순위 | 항목 | 파일 |
|---|:---:|------|------|
| 1 | HIGH | StockSyncAPIView `permission_classes = []` → IsAuthenticated/IsAdminUser | `stocks/views.py:886` |
| 2 | HIGH | `_parse_free_input` 인젝션 마커 화이트리스트 확장 + Gemini schema-enforced JSON | `thesis/services/thesis_builder.py:421` |
| 3 | MED | LLM 호출 시 사용자/외부 데이터 명시 delimiter 래핑 + system_instruction 강화 | `rag_analysis/services/*`, `thesis/views/conversation_views.py:234` |
| 4 | MED | CORS_ALLOWED_ORIGINS 환경변수 기반 + ALL_ORIGINS+CREDENTIALS 동시 금지 | `config/settings.py:311-320` |
| 5 | MED | 500 에러 응답에서 `str(e)` 제거 (admin endpoints 포함 일관 적용) | `api_request/admin_views.py` 등 |

---

## 검사 범위 요약

- **검사한 파일**: views*.py 약 25개 + 모든 cursor.execute 4곳 + LLM 호출 6개 파일 + config/settings.py + .env/.gitignore
- **검사 누락**: tests/ 디렉터리, 프론트엔드 XSS, WebSocket consumers, Celery tasks 내부 LLM 호출(별도 audit 필요)
- **권고 후속**: `qa-architect` 에이전트가 Top 5 fix PR 작성 → 회귀 테스트(WatchlistViewSet anon, StockSyncAPIView 401 등) 동반.
