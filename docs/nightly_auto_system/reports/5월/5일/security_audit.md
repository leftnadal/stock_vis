# Stock-Vis 보안 감사 보고서

- **감사일**: 2026-05-05
- **감사 범위**: Backend (Django/DRF) — OWASP Top 10 기반
- **감사 모드**: 읽기 전용, 정적 분석 (코드 수정 없음)
- **브랜치**: portfolio
- **감사 도구**: grep / read 기반 정적 코드 분석
- **비교 기준**: 전일 보고서 (`5월/4일/security_audit.md`)

---

## 0. Executive Summary (한눈에 보기)

| 영역 | 결과 | 핵심 발견 |
|------|------|----------|
| A01 — 권한/인가 (Broken Access Control) | **CRITICAL** | (1) `portfolio/views.py` 신규 — `coach_e5_adjustment`가 `@csrf_exempt` + 무인증 + LLM 직접 호출 (Anthropic Claude). (2) `serverless/views.py` 100+ AllowAny 함수형 뷰 (8개 TODO 미해소). (3) `chainsight WatchlistViewSet` 익명 IDOR. (4) `StockSyncAPIView` 무인증 외부 API 비용 직결 |
| A03 — SQL Injection | **PASS** | `cursor.execute` 4곳 모두 파라미터 바인딩(`%s`) 또는 정적 쿼리. ORM 위주 사용 |
| A02 — 암호학적 실패 / 시크릿 관리 | **MEDIUM** | `.env`는 gitignore 적용 + `chmod 600` 정상. `frontend/.env.local.bak` 백업 파일 잔존(미추적이지만 디스크에 존재). SECURE_* 헤더 (HSTS, SECURE_SSL_REDIRECT 등) **미설정** 상태 유지 |
| LLM 프롬프트 인젝션 | **HIGH** | (1) `portfolio/services/e5_adjustment_parser.py:66` — 무인증 사용자의 `user_command`가 f-string으로 직접 삽입(2,000자 길이 제한만 있음, 구분자 sanitization 없음). (2) `thesis/services/indicator_matcher.py:175` 신규 `_sanitize_for_prompt` 추가됨(✓ 개선). (3) news/sec/serverless 5개 서비스는 외부 데이터 직접 f-string 삽입 (전일과 동일) |
| A05 — Security Misconfiguration | **HIGH** | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` 등 **0개 설정** (전일 그대로). CORS는 명시 origin만 허용 (양호). DEBUG는 env로 분리 + 운영 가드 정상 |
| A04 — Insecure Design (LLM 비용 노출) | **CRITICAL** | (신규) `coach_e5_adjustment`는 **Anthropic Claude(haiku/sonnet) 호출**을 무인증·CSRF 우회·throttle 부재 상태로 노출. `LLMBudgetExceededError`는 인스턴스별 카운터(50회)로만 제한 → 워커 재시작/요청별 인스턴스화 시 가드 무력화 가능. 기존 `LLMPeerFilterView`, `serverless` LLM 트리거 무인증 그대로 |
| A09 — 에러 노출 | **MEDIUM** | `'error': str(e)` 패턴 30+ 곳 (전일 동일). `chainsight/api/views.py:229` 익명 무인증 노출 그대로 |
| A07 — 인증 (Brute Force) | **MEDIUM** | `LogIn`/`JWTLogin`/`ChangePassword` throttle 없음. `WatchlistRateThrottle`은 정상 적용되어 있음(전일 보고서 정정) |

**우선 조치 권장 순위 (5/5 신규 분 포함)**:
1. **(CRITICAL, NEW)** `portfolio/views.py` `coach_e5_adjustment` — 인증/throttle 즉시 적용. `@csrf_exempt`는 DRF 인증 도입 후에만 유지하거나 SessionAuth + CSRF로 전환
2. **(CRITICAL, NEW)** `portfolio/views.py` `coach_e1_garp` — Mock fixture 의존이지만 provider 파라미터에 `anthropic`/`gemini` 받아 실 호출 가능 → 인증 적용
3. (CRITICAL) `serverless/views.py`의 알림/프리셋 수정·삭제 엔드포인트 인증 적용 (8개 TODO)
4. (CRITICAL) `StockSyncAPIView`, `chainsight WatchlistViewSet` 인증 적용
5. (HIGH) DRF 글로벌 throttle + LLM scope 별도 추가 (인스턴스 로컬 가드는 신뢰 불가)
6. (HIGH) 운영 배포 전 `SECURE_*` 보안 헤더 4종 추가
7. (MEDIUM) `frontend/.env.local.bak` 삭제 + `.gitignore`에 `*.bak` 추가
8. (HIGH) 프롬프트 인젝션 sanitizer를 공통 유틸로 승격 (현재 `thesis_builder._call_llm`/`indicator_matcher._sanitize_for_prompt` 두 개로 분산)

**전일 대비 변동**:
- (+) `thesis/services/indicator_matcher.py:175` — `_sanitize_for_prompt` 신규 추가. **개선**
- (+) `users/views.py:39` `WatchlistRateThrottle = 100/hour` — Watchlist 8개 view에 적용 확인. 전일 보고서 1.2/6.1 항목 정정 (적용되어 있었음)
- (–) `portfolio/` 신규 앱 — Pure Django view + `@csrf_exempt` + LLM 호출 + 무인증. **신규 CRITICAL**

---

## 1. A01 - Broken Access Control (인증/인가)

### 1.1 CRITICAL (NEW) — `portfolio/views.py` 무인증 LLM POST + CSRF 우회

```python
# portfolio/views.py:56-71
@csrf_exempt
@require_POST
def coach_e5_adjustment(request: HttpRequest) -> JsonResponse:
    provider = request.GET.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:  # gemini/anthropic/sonnet/haiku
        return JsonResponse({...}, status=400)

    body = json.loads(request.body)
    e5_request = E5Request.model_validate(body)
    result = run_e5(e5_request, provider=provider)  # → Anthropic API 호출
    return JsonResponse(result, status=200, ...)
```

**라우팅**: `config/urls.py:46` → `portfolio.urls` → `coach/e5/adjustment/` 노출.

**리스크**:
- 익명 사용자가 임의 횟수만큼 Anthropic Claude(haiku/sonnet)/Gemini API 호출 가능 → **비용 폭발**.
- `LLMBudgetExceededError` 가드는 `LLM_BUDGET_MAX_CALLS=50` (settings.py:31) 인스턴스별 카운터로만 동작. Django runserver는 동일 프로세스라 가드가 적용되지만, gunicorn 다중 워커/Daphne ASGI에서는 워커별 독립 카운터 → 실효 한도 = `워커 수 × 50`.
- `@csrf_exempt`는 DRF 인증과 무관하게 **모든 origin에서 POST 가능** (CORS만 통과하면 됨). Pure Django view라 `DEFAULT_AUTHENTICATION_CLASSES`도 적용되지 않음.
- `user_command` (max 2,000자) + `analysis_context` (자유 dict)이 그대로 LLM 프롬프트에 들어감 → **프롬프트 인젝션 + 비용 공격 동시**.

**현재 가드**:
- `_VALID_PROVIDERS` whitelist (✓)
- `E5Request` Pydantic 검증 — `extra="forbid"`, `user_command` 길이 제한 (✓)
- LLMBudgetExceededError → 503 (제한적, 위 설명 참조)

**권장**:
1. `@csrf_exempt` 제거하고 DRF APIView로 전환 (`permission_classes = [IsAuthenticated]` + `throttle_classes = [UserRateThrottle]`).
2. provider별 별도 budget 카운터를 Redis로 외부화 (`shared_state` 패턴).
3. `analysis_context`에 대한 schema 강제 (현재 `dict[str, Any]` → 구조화된 Pydantic 모델 필수화).

### 1.2 HIGH (NEW) — `coach_e1_garp` 무인증 GET (Mock fallback이지만 provider 분기 존재)

```python
# portfolio/views.py:31-53
@require_GET
def coach_e1_garp(request: HttpRequest) -> JsonResponse:
    provider = request.GET.get("provider", "haiku")
    ...
    result = run_e1_garp(provider=provider)
```

`run_e1_garp`는 GARP 프리셋 + Mock fixture 기반 실행이지만 provider가 `anthropic`/`sonnet`/`haiku`/`gemini` 중 어느 것이든 LLMClient 호출 흐름을 탄다. Mock 패치가 없는 환경에선 실제 비용 발생 가능.

**권장**: 1.1과 동일.

### 1.3 CRITICAL — `permission_classes = []` 명시적 무인증 (전일 그대로)

| 파일:라인 | 클래스 | 메서드 | 위험 |
|-----------|--------|--------|------|
| `stocks/views.py:886` | `StockSyncAPIView` | POST | **외부 API 비용 폭발**. 무인증 사용자가 임의 symbol에 대해 동기화 트리거 가능. FMP rate limit 소진 + DB 쓰기 |

```python
# stocks/views.py:878-886 (변동 없음)
class StockSyncAPIView(APIView):
    permission_classes = []   # ← 명시적 빈 리스트 = 모든 사용자 허용
```

**권장**: `IsAuthenticatedOrReadOnly` 또는 `IsAdminUser`.

### 1.4 CRITICAL — `serverless/views.py` AllowAny 만연 (전일 그대로, 53건)

`grep -c '@permission_classes([AllowAny])` = **53** (1373~3337라인). 그중 본인 코드 TODO 8건:

| 라인 | 엔드포인트 | 위험 |
|------|-----------|------|
| 1373 | `screener_alerts_api` (POST) — 알림 생성 | 데이터 변조 |
| 1437 | `screener_alert_detail` (PUT/DELETE) | 데이터 변조 |
| 1493 | `toggle_alert` | 타인 알림 토글 |
| 1528 | `alert_history_api` | 타인 알림 이력 조회 |
| 1577 | `mark_alert_read` | POST 무인증 가능 |
| 1608 | `dismiss_alert` | 동상 |
| 1644 | `share_preset` | 타인 프리셋 공유 가능 |
| 1757 | `import_preset` | 비용 미미하나 노출 |

추가 LLM/Admin TODO 4건: 165, 213, 381, 447, 780, 967, 3224.

**권장**: 일괄 `IsAuthenticated` (LLM/Admin 라인은 `IsAdminUser`).

### 1.5 HIGH — `chainsight/views/watchlist_views.py:31` 익명 IDOR (전일 그대로)

```python
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    throttle_classes = [WatchlistAnonThrottle]  # 30/min
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        ...
        if user:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True)   # ← 모든 익명이 같은 풀 공유
```

**리스크**: 익명 A가 만든 SavedPath를 익명 B가 GET/DELETE 가능 → IDOR.

**권장**: `session_key` 또는 `anonymous_token`으로 소유권 모델, 또는 `IsAuthenticated`.

### 1.6 HIGH — DRF 기본 권한 의존 뷰들 (메서드 미보호)

`config/settings.py:347` 기본 `IsAuthenticatedOrReadOnly`. 명시 선언 없는 뷰들 (전일 그대로):

| 파일 | 클래스 | 메서드 | 비고 |
|------|--------|--------|------|
| `stocks/views.py` | `StockSearchAPIView`, `StockChartDataAPIView`, `StockBalanceSheetAPIView`, `StockIncomeStatementAPIView`, `StockCashFlowAPIView`, `StockCompleteDataAPIView` | GET | 전체 공개 |
| `stocks/views_eod.py` | `EODDashboardView`, `EODSignalDetailView`, `EODPipelineStatusView` | GET | 전체 공개 |
| `stocks/views_indicators.py` | `IndicatorComparisonView` | POST | 기본 IsAuthenticatedOrReadOnly로 보호 (안전, 표기 권장) |
| `stocks/views_search.py` | `SymbolSearchView`, `SymbolValidateView`, `PopularSymbolsView` | GET | 공개 |
| `stocks/views_mvp.py` | `StockMVPListView`, `StockMVPDetailView`, `StockRAGContextView`, `SectorListView` | GET | 공개 |
| `chainsight/api/views.py` | `ChainSightGraphView`, `ChainSightSuggestionView`, `ChainSightTraceView`, `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` | GET | 공개 |
| `validation/api/views.py` | `ValidationSummaryView`, `ValidationMetricsView`, `LeaderComparisonView`, `PresetListView`, **`LLMPeerFilterView`** | GET/POST | LLM 호출 무인증! (1.7 참조) |
| `sec_pipeline/views.py:28` | `FilingDataView` | GET | 공개 (`get_or_collect_filing` → `collect_and_extract.delay` Celery 트리거 → Gemini extractor) |

`stocks/views_screener.py`, `stocks/views_fundamentals.py`, `stocks/views_exchange.py`, `stocks/views_market_movers.py`는 `IsAuthenticated` 명시. ✓

**권장**: 모든 APIView에 `permission_classes` 명시.

### 1.7 HIGH — LLM 호출 엔드포인트 무인증 (비용 직결)

| 파일:라인 | 엔드포인트 | LLM | 권한 |
|-----------|-----------|-----|------|
| **`portfolio/views.py:56`** | **`coach_e5_adjustment`** | **Anthropic/Gemini** | **None (CSRF도 우회)** |
| **`portfolio/views.py:31`** | **`coach_e1_garp`** | **Anthropic/Gemini** | **None** |
| `validation/api/views.py:495` | `LLMPeerFilterView.post` | Gemini | None (메서드 내 검증 없음) |
| `serverless/views.py:381` (TODO) | `generate_screener_keywords` | Gemini | AllowAny |
| `serverless/views.py:447` (TODO) | `trigger_keyword_generation` | Gemini (Celery 트리거) | AllowAny |
| `serverless/views.py:780` (TODO) | LLM 트리거 추정 | Gemini | AllowAny |
| `serverless/views.py:967` (TODO) | LLM 트리거 추정 | Gemini | AllowAny |
| `sec_pipeline/views.py:28` | `FilingDataView.get` | Gemini (on_demand 트리거) | None |

**권장**:
1. 위 모든 view에 `permission_classes = [IsAuthenticated]` 즉시 적용.
2. DRF `DEFAULT_THROTTLE_CLASSES` + `DEFAULT_THROTTLE_RATES` 글로벌 설정 + LLM scope 별도 (`llm: 20/hour`).
3. portfolio/coach 시리즈는 `csrf_exempt` 제거 후 DRF로 전환.

### 1.8 INFO — 잘 구성된 권한 사례 (변동 없음)

- `users/jwt_views.py`: 회원가입 `AllowAny`, 로그아웃/검증/패스워드 변경 `IsAuthenticated`. Gold standard.
- `serverless/views_admin.py`: 모든 `AdminXxxView` `IsAdminUser`.
- `news/api/views.py NewsViewSet`: `@action`별 `permission_classes` 명시. Admin 분리 정상.
- `thesis/views/*`: 모든 ViewSet/APIView에 `IsAuthenticated` 명시.
- `api_request/admin_views.py`: `IsAdminUser` (헬스체크는 의도적 무인증).
- `users/views.py:586+` Watchlist 8개 view에 `WatchlistRateThrottle = 100/hour` 적용 확인.

---

## 2. A03 - Injection

### 2.1 SQL Injection 점검 (PASS, 변동 없음)

`cursor.execute()` 사용처 4곳 모두 안전:

| 파일:라인 | 패턴 | 안전성 |
|-----------|------|--------|
| `chainsight/services/seed_selection.py:152` | `cursor.execute("""...WHERE date <= %s..., date <= %s...""", [market_date, market_date])` | ✅ 파라미터 바인딩 |
| `serverless/services/admin_status_service.py:833` | `cursor.execute("SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30")` | ✅ 정적 쿼리 |
| `api_request/admin_views.py:266` | `cursor.execute("SELECT 1")` | ✅ 헬스체크 |
| `config/views.py:90` | `cursor.execute("SELECT 1")` | ✅ 헬스체크 |

ORM 위주 사용. SQL injection 표면 매우 낮음.

### 2.2 Command Injection 점검 (PASS)

`subprocess`, `os.system`, `shell=True` 백엔드 코드 없음 (재확인).

### 2.3 LLM Prompt Injection (HIGH, 신규 finding 포함)

| 파일 | 입력 처리 | 위험도 | 비고 |
|------|----------|--------|------|
| `thesis/services/thesis_builder.py:434` | `safe_text = text[:500].replace('```', '').replace('---', '').strip()` | **LOW** | ✅ 모범 사례 |
| **`thesis/services/indicator_matcher.py:175` (NEW)** | `_sanitize_for_prompt(text, max_length)` 헬퍼 추가 → 199, 202, 203에 적용 | **LOW** | ✅ **개선됨**. 그러나 동일 패턴이 두 파일에 분산 — 공통 유틸 승격 권장 |
| `thesis/services/prompt_builder.py:806` `build_suggestion_prompt(news_title, keyword, summary, ...)` | f-string 직접 삽입 | **HIGH** | NewsArticle.title은 외부 RSS/API에서 수집 → 공급망 인젝션 가능. 길이/구분자 통제 없음 |
| `thesis/services/prompt_builder.py:625` `build_question_answer_prompt` | `article.content[:300]` 직접 | **MED** | 길이 제한은 있으나 구분자/지시문 없음 |
| `thesis/views/conversation_views.py:234` `_convert_to_korean_issues` | `t["title"][:80]` 8개 연결 | **MED** | 뉴스 제목 정제 없음 |
| `news/services/keyword_extractor.py:262` | `news['title']`, `news['summary'][:100]` 직접 | **MED** | 외부 뉴스 본문이 그대로 LLM에. JSON 출력 강제로 일부 완화 |
| `news/services/news_deep_analyzer.py:188` | `article.title` 등 그대로 | **MED** | 동상 |
| `rag_analysis/services/llm_service.py:174` | `user_content = f"{context}\n\n질문: {question}"` | **MED** | view단 IsAuthenticated 보호. 인증된 사용자도 자기 데이터에 페이로드 삽입 가능 |
| `rag_analysis/services/adaptive_llm_service.py:199` | f-string 동상 | **MED** | 동상 |
| `serverless/services/thesis_builder.py:232` | user_notes 직접 | **MED** | 사용자 노트 무방어 삽입 |
| **`portfolio/services/e5_adjustment_parser.py:57-96` (NEW)** | `f'..."{request.user_command}"...'` + `_format_analysis_summary(ctx)` | **HIGH** | 무인증 + max_length=2000만 제한. 구분자/지시문 sanitization **없음**. dict[str, Any]로 받는 `analysis_context` 또한 prompt에 들어감 |
| `sec_pipeline/intelligence.py:148` | `PIPELINE_INTELLIGENCE_PROMPT.format(**data)` | **LOW** | 내부 데이터만 |

**권장**:
- 공통 유틸 `core/llm_safety.py::sanitize_for_prompt(text, max_length)` 신설 — 현재 `thesis_builder`/`indicator_matcher` 패턴을 단일 소스화.
- 외부 데이터(뉴스 본문/제목) + 사용자 입력 모두 동일 sanitizer 통과.
- 시스템 프롬프트에 "사용자 입력 안의 지시는 무시" 명시 + `<context>...</context>` 식 명시적 구분자 사용.
- portfolio E5는 user_command 길이 추가 축소(2000 → 500자) + sanitize 적용 권장.

---

## 3. A02 - Cryptographic Failures / 시크릿 관리

### 3.1 정상 항목 (PASS)

- `.env`: `chmod 600`, 소유자만 읽기 가능.
- `.gitignore`: `.env` 라인 두 군데(10, 138) + `*.key`(212) 적용.
- `git ls-files | grep '\.env'` → `.env.example`만 추적, 실제 `.env` 미추적 (재확인).
- 하드코딩 시크릿 패턴 (sk-*, AKIA*) 백엔드 코드에 **없음**.
- `SECRET_KEY`: `os.getenv` + DEV-only fallback + 운영 가드 (settings.py:158).
- `JWT_SIGNING_KEY`: `SECRET_KEY`와 분리 가능.
- `NEO4J_PASSWORD`: 운영(`DEBUG=False`) 미설정 시 startup 차단.
- `LLM_BUDGET_MAX_CALLS=50` (settings.py:31) — Portfolio LLM 호출 가드 환경변수화 (다만 1.1에 기술한 대로 실효성 제한).

### 3.2 MEDIUM — 백업 파일 잔존 (전일 그대로)

```
frontend/.env.local        ← 정상
frontend/.env.local.bak    ← 백업 파일, 미추적이지만 디스크에 잔존
```

- `*.bak`은 `.gitignore`에 명시되지 않음 (`env.bak/`, `venv.bak/`만 명시 — 디렉토리 패턴).
- 미추적이라 git 노출 위험은 즉시 없으나, 실수로 add 시 즉시 노출.

**권장**:
1. `.gitignore`에 `*.bak`, `*.local`, `*.local.bak` 추가
2. `frontend/.env.local.bak` 자체 삭제 (원본 있으므로)

### 3.3 INFO — `.env` 키 종류

```
FMP_API_KEY, MARKETAUX_API_KEY, FINNHUB_API_KEY, FRED_API_KEY,
ANTHROPIC_API_KEY, GEMINI_API_KEY, EODHD_API_KEY
```

평소대로 환경변수에서만 읽음. 노출 채널 없음.

---

## 4. A05 - Security Misconfiguration

### 4.1 HIGH — Django 보안 헤더 미설정 (전일 그대로)

`config/settings.py` 전체에서 다음 항목 **0건**:
- `SECURE_SSL_REDIRECT`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`
- `SECURE_CONTENT_TYPE_NOSNIFF`
- `SECURE_BROWSER_XSS_FILTER`
- `SECURE_PROXY_SSL_HEADER`
- `X_FRAME_OPTIONS` 명시 (Django 기본값 'DENY' 적용되긴 함)

**리스크**: HTTPS 배포 시 평문 쿠키 노출, MITM, downgrade attack.

**권장 (운영 전 필수)**:
```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### 4.2 PASS — CORS

```python
# config/settings.py:308-315
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True
```

- 명시 origin만 허용. 모범.
- `CORS_ALLOW_ALL_ORIGINS` 기본 False, env로만 활성. 모범.
- 운영 환경에 `https://app.stockvis.com` 추가 시 `CORS_ALLOWED_ORIGINS`에 명시 필요.

### 4.3 PASS — DEBUG/ALLOWED_HOSTS

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False')` — 안전한 기본값.
- `ALLOWED_HOSTS = ... or (['*'] if DEBUG else [])` — 운영에서 `*` 차단.
- 운영 가드 `if not DEBUG: raise ImproperlyConfigured(...)` — SECRET_KEY/NEO4J_PASSWORD 누락 시 즉시 실패. 모범.

### 4.4 INFO — JWT 설정

```python
ACCESS_TOKEN_LIFETIME = 60분
REFRESH_TOKEN_LIFETIME = 7일
ROTATE_REFRESH_TOKENS = True
BLACKLIST_AFTER_ROTATION = True
ALGORITHM = 'HS256'
SIGNING_KEY = JWT_SIGNING_KEY  # SECRET_KEY와 분리됨
```

- 회전 + 블랙리스트 정상.
- HS256 단일 키 모델. 멀티 서비스 분리 시 RS256 고려.
- 60분 access는 일반적.

### 4.5 PASS — Cache 격리

`config/settings.py:424` Redis DB `1` (CELERY_BROKER는 DB 0 분리). 운영 시 패스워드 + AUTH 적용 필요.

---

## 5. A09 - Security Logging and Monitoring Failures

### 5.1 MEDIUM — `'error': str(e)` 노출 패턴 (전일 그대로)

총 30+ 곳에서 발견. 대표 예:

| 파일:라인 | 컨텍스트 | 위험 |
|-----------|---------|------|
| `api_request/admin_views.py:274-276` | health check `cursor.execute("SELECT 1")` 실패 시 | DB 연결 문자열의 호스트/포트가 노출될 수 있음 (Admin 전용이지만 가시성 있음) |
| `chainsight/api/views.py:229` | `Response({"from": ..., "to": ..., "found": False, "error": str(e)})` | **무인증 노출**. 1.6 항목과 결합 시 위험 |
| `serverless/views_admin.py:163, 183, 203, 223, 243, 263` | Admin (안전한 편) | 권한 일관성 OK |
| `portfolio/views.py:49, 51, 86, 93, 101, 105, 111` | LLMError → `str(exc)[:300/500]` | **길이 제한이 있어 양호**. 그러나 `LLMError`가 외부 API의 에러 메시지를 그대로 담고 있다면 키 단편이나 cluster ID 노출 가능 |

**리스크**: 보통 DRF가 DEBUG=False일 때 traceback을 가리지만, 위 코드는 명시적으로 `str(e)`를 응답에 포함하므로 **DEBUG와 무관하게 항상 노출**.

**권장**:
- view 응답: 사용자에게는 `"내부 오류가 발생했습니다"` + `request_id`만 반환.
- 상세 `str(e)`는 `logger.exception()`으로 서버 로그에만.
- 공통 헬퍼 `safe_error_response(exc, request)` 추출.

---

## 6. A04 - Insecure Design (LLM 비용/오용)

### 6.1 CRITICAL — LLM Budget 가드 신뢰성 (NEW)

```python
# config/settings.py:31
LLM_BUDGET_MAX_CALLS = int(os.getenv('LLM_BUDGET_MAX_CALLS', '50'))
```

- `portfolio/llm/client.py:147` 인스턴스별 `_call_count` 카운터로 50회 제한 후 `LLMBudgetExceededError`.
- 문제 1: 인스턴스 재생성 시 카운터 리셋 → 요청마다 새 LLMClient 만들면 가드 무력.
- 문제 2: gunicorn N 워커 환경에서 워커별 독립 → 실효 한도 = `N × 50`.
- 문제 3: 무인증 endpoint(`coach_e5_adjustment`)와 결합 시 분당 수백 호출 가능.

**권장**:
1. Redis 기반 분산 카운터(`shared_state` 또는 `django-redis`)로 외부화.
2. 인증 사용자별/IP별 quota 분리.
3. DRF `ScopedRateThrottle`로 view 단위 rate limit 추가.

### 6.2 HIGH — Rate Limit 부재 (전일 정정 포함)

- ✅ `users/views.py:39` `WatchlistRateThrottle = '100/hour'` Watchlist 8개 view에 적용 확인 (전일 보고서 정정).
- ✅ `chainsight/views/watchlist_views.py:26` `WatchlistAnonThrottle = '30/minute'` 적용.
- ❌ LLM 호출 view(`SuggestThesesView`, `LLMPeerFilterView`, `serverless` LLM 트리거, **`coach_e5_adjustment`**)에 throttle 없음.
- ❌ DRF 글로벌 `DEFAULT_THROTTLE_CLASSES` 미설정.

**권장**:
```python
# config/settings.py REST_FRAMEWORK에 추가
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.UserRateThrottle',
    'rest_framework.throttling.AnonRateThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'user': '300/hour',
    'anon': '60/hour',
    'llm': '20/hour',  # 별도 scope
    'login': '5/min',  # 7.4 brute force 대응
},
```
LLM view는 `throttle_scope = 'llm'` 또는 별도 ScopedRateThrottle.

### 6.3 MED — Watchlist 익명 디자인 (전일 그대로)

`chainsight/views/watchlist_views.py`가 익명 사용자 데이터를 풀에 모으는 디자인은 IDOR을 본질적으로 만든다 (1.5 참조). 디자인 단계에서 익명/세션 token 모델로 재설계 권장.

---

## 7. A07 - Identification and Authentication Failures

### 7.1 PASS — 패스워드 검증 (전일 그대로)

`AUTH_PASSWORD_VALIDATORS` 4종(UserAttributeSimilarity / MinimumLength / CommonPassword / NumericPassword) 적용.

### 7.2 INFO — 로그인 실패 메시지 (전일 그대로)

`users/views.py:165-167` `"Wrong username or password"` — 사용자 존재 여부 노출 안 함.

### 7.3 INFO — 세션 무효화 (전일 그대로)

`users/views.py:178` `LogOut` 세션 무효화 정상. JWT는 `BLACKLIST_AFTER_ROTATION=True`로 자동 무효화.

### 7.4 MED — Brute force 보호 없음 (전일 그대로)

`LogIn`, `JWTLogin`, `ChangePassword`에 throttle 없음. 무차별 대입 공격 가능.

**권장**:
- `LogIn` / `CustomTokenObtainPairView`에 `throttle_classes = [AnonRateThrottle]` + 별도 scope (5/min).
- `ChangePassword`에 `throttle_classes = [UserRateThrottle]`.

---

## 8. 종합 권장 우선순위 (운영 배포 전)

### Tier 1 (즉시, 코드 변경 시급)

1. **`portfolio/views.py` 두 view 인증 적용** — `coach_e1_garp`, `coach_e5_adjustment`. `@csrf_exempt` 제거하고 DRF APIView로 전환 후 `[IsAuthenticated]` + `throttle_scope = 'llm'`. **NEW** Tier 1
2. **`StockSyncAPIView` permission 변경** — `permission_classes = []` → `[IsAuthenticated]` 또는 `[IsAdminUser]`.
3. **`serverless/views.py` LLM/쓰기 엔드포인트 인증 적용** — 8개 TODO + LLM 트리거 4개. `screener_alerts_api`, `screener_alert_detail`, `toggle_alert`, `mark_alert_read`, `dismiss_alert`, `share_preset` 우선.
4. **`LLMPeerFilterView` 인증** — `validation/api/views.py:495` POST에 `permission_classes = [IsAuthenticated]`.
5. **`chainsight WatchlistViewSet` 인증** — `[AllowAny]` → `[IsAuthenticated]` 또는 익명 소유권 모델.

### Tier 2 (운영 배포 직전)

6. **DRF 글로벌 throttle** + LLM scope (6.2 권장 코드).
7. **LLM Budget Redis 분산 카운터** — `LLM_BUDGET_MAX_CALLS` 인스턴스 로컬 → 분산화 (6.1).
8. **Django 보안 헤더 4종** (`SECURE_SSL_REDIRECT`, cookie secure, HSTS) — 4.1 코드 적용.
9. **`frontend/.env.local.bak` 제거** + `.gitignore`에 `*.bak` 추가.
10. **`'error': str(e)` 응답 패턴** → `safe_error_response` 헬퍼로 일괄 교체.

### Tier 3 (개선)

11. LLM 프롬프트 sanitizer 공통 유틸 승격 — 현재 `thesis_builder._call_llm` + `indicator_matcher._sanitize_for_prompt` 두 곳. `core/llm_safety.py`로 단일화.
12. 로그인/비번변경에 throttle scope 적용 (brute force 방지).
13. 모든 APIView에 `permission_classes` 명시적 선언 (default 의존 제거).
14. `portfolio` E5 schema 강화 — `analysis_context: dict[str, Any]` → 구조화 모델.

---

## 9. 부록 — 감사 대상 파일 목록

### 9.1 view 파일 (32개, +1 portfolio 신규)

```
api_request/admin_views.py          chainsight/api/views.py
chainsight/views.py                 chainsight/views/watchlist_views.py
config/views.py                     graph_analysis/views.py
macro/views.py                      metrics/views.py
news/api/views.py                   news/views.py
portfolio/views.py                  ★ 신규 (Pure Django + LLM)
rag_analysis/views.py               sec_pipeline/views.py
serverless/views.py                 serverless/views_admin.py
stocks/views.py                     stocks/views_eod.py
stocks/views_exchange.py            stocks/views_fundamentals.py
stocks/views_indicators.py          stocks/views_market_movers.py
stocks/views_mvp.py                 stocks/views_screener.py
stocks/views_search.py              thesis/views/conversation_views.py
thesis/views/monitoring_views.py    thesis/views/thesis_views.py
users/jwt_views.py                  users/views.py
validation/api/views.py             validation/views.py
```

`graph_analysis/views.py`, `metrics/views.py`는 빈 파일 (`render` import만).

### 9.2 LLM 호출 파일 (확인됨, +portfolio 시리즈)

```
news/api/views.py                              news/services/keyword_extractor.py
news/services/news_deep_analyzer.py            news/services/stock_insights.py
portfolio/llm/client.py                        ★ 신규 LLMClient (Anthropic + Gemini)
portfolio/services/e1_garp.py                  ★ 신규
portfolio/services/e5_adjustment_parser.py     ★ 신규 (사용자 입력 직접 prompt 삽입)
portfolio/prompts/{e1,e2,e3,e4,e5,e6}/*        ★ 신규 (내부 데이터 빌더)
rag_analysis/services/adaptive_llm_service.py  rag_analysis/services/context_compressor.py
rag_analysis/services/entity_extractor.py      rag_analysis/services/llm_service.py
sec_pipeline/extractor.py                      sec_pipeline/intelligence.py
serverless/services/csv_url_resolver.py        serverless/services/keyword_generator.py
serverless/services/keyword_generator_v2.py    serverless/services/keyword_service.py
serverless/services/llm_relation_extractor.py  serverless/services/regulatory_service.py
serverless/services/relationship_keyword_enricher.py
serverless/services/thesis_builder.py          stocks/services/korean_overview_service.py
thesis/services/indicator_matcher.py           ★ _sanitize_for_prompt 신규
thesis/services/prompt_builder.py              thesis/services/thesis_builder.py
thesis/views/conversation_views.py             validation/services/llm_peer_filter.py
```

### 9.3 cursor.execute 사용 파일 (4개, 모두 PASS, 변동 없음)

```
api_request/admin_views.py:266        config/views.py:90
chainsight/services/seed_selection.py:152    serverless/services/admin_status_service.py:833
```

### 9.4 csrf_exempt 사용 (NEW 추적)

```
config/views.py:6                  ← import만 (사용처는 health endpoint 추정, 무인증 의도)
portfolio/views.py:16              ← coach_e5_adjustment에 적용 (★ Tier 1 risk)
```

---

## 10. 감사자 노트

- **본 감사는 정적 분석 only**입니다. 런타임 동작, race condition, 분산 환경 정합성은 별도 검증 필요.
- **5/5 신규 발견**: `portfolio` 앱이 Pure Django view + `@csrf_exempt`로 LLM API를 무인증 호출 가능 상태. CRITICAL 분류. DRF의 `DEFAULT_PERMISSION_CLASSES`가 적용되지 않는 Pure Django view는 별도 추적 필요.
- **5/5 정정**: 전일 보고서에서 "WatchlistRateThrottle 적용 흔적 미발견"으로 표기했으나, 재확인 결과 8개 Watchlist view에 모두 적용되어 있음. 정정.
- **5/5 개선 확인**: `thesis/services/indicator_matcher.py`에 `_sanitize_for_prompt` 헬퍼 신규 추가됨. `thesis_builder._call_llm` 패턴이 다른 모듈로 확산되기 시작 — 공통 유틸 승격이 시급.
- LLM 프롬프트 인젝션은 본질적으로 "완벽 방어 불가"이며, 출력 필터링 + 비용 모니터링 + 사용자별 quota를 함께 가져가는 것이 현실적 방어 전략. 특히 `LLM_BUDGET_MAX_CALLS` 같은 인스턴스 로컬 가드는 다중 워커 환경에서 무력화됨에 주의.
- 본 감사 도중 코드는 한 줄도 수정하지 않았습니다. 모든 권장 사항은 별도 PR로 처리해야 합니다.
