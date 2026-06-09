# 보안 감사 보고서 (Security Audit)

- **대상 프로젝트**: Stock-Vis (`/Users/byeongjinjeong/Desktop/stock_vis`)
- **감사 일자**: 2026-06-09
- **감사 범위**: OWASP Top 10 기반 정적 코드 감사 (인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿 관리, CORS/XSS/에러 노출)
- **감사 방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **저장소 구조 참고**: CLAUDE.md의 앱 경로(stocks/, users/ 등)는 모노레포로 재구성됨. 실제 경로는 `apps/`, `packages/shared/`, `services/`, `integrations/`, `thesis/`, `config/`.

---

## 0. 총평 (Executive Summary)

본 코드베이스는 **이전에 보안 감사(`audit P0 #2/#3/#5/#6`, 2026-05-12~19)가 수행된 흔적**이 코드 주석 곳곳에 남아 있으며, 전반적인 보안 자세(security posture)는 **양호**하다. 특히:

- DRF 전역 기본 권한이 `IsAuthenticated`로 설정되어 **명시적 권한 누락 뷰도 기본적으로 인증이 강제**된다 (fail-secure 기본값).
- 모든 raw SQL(`cursor.execute`)이 **파라미터 바인딩(`%s`) 또는 정적 쿼리**만 사용 → SQL 인젝션 표면 없음.
- LLM 프롬프트에 사용자 입력이 들어가는 주요 경로에 **명시적 인젝션 방어**(신뢰 경계 태그, escape, 길이 제한)가 적용됨.
- 하드코딩된 시크릿 없음, `.env` gitignore 처리됨, 운영 배포 가드(`SECRET_KEY`/`NEO4J_PASSWORD` 누락 시 즉시 실패) 존재.

다만 **이전 audit P0 #6에서 보호한 sync 트리거 엔드포인트 6건 중 2건이 누락**되어, 미인증 사용자가 비용 큰 백그라운드/외부 호출 작업을 트리거할 수 있는 **HIGH 등급 결함 2건**이 잔존한다.

### 심각도 요약

| 심각도 | 건수 | 항목 |
|--------|------|------|
| CRITICAL | 0 | — |
| HIGH | 2 | 미인증 sync 트리거 (`llm-relations/sync`, `etf/sync`) |
| MED | 2 | iron_trading 공개 엔드포인트(throttle/인증 없음), preset 공개 엔드포인트 |
| LOW | 3 | HealthCheck 인프라 토폴로지 노출, 통계 엔드포인트 정보 노출, SECRET_KEY dev fallback |
| INFO | 2 | macro/market-feed 공개(설계상 의도), 미인증 GET 정보성 노출 다수 |

---

## 1. 인증 / 인가 (A01: Broken Access Control)

### 1.1 전역 기본 권한 — 양호 ✅

`config/settings.py:355-374`

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '60/min', 'anon': '20/min', ...
    },
}
```

**중요**: 기본 권한이 `IsAuthenticated`이므로, `permission_classes`를 **명시하지 않은** APIView/ViewSet은 자동으로 인증을 요구한다. 즉, 본 프로젝트에서 "권한 누락"의 실제 위험은 **명시적 `AllowAny`를 지정한 뷰**에 집중된다. (지시서의 "permission_classes 누락 탐지" 가설은 이 fail-secure 기본값으로 인해 대부분 무효화됨 — 긍정적.)

- 명시적 권한 없는 뷰(예: `packages/shared/stocks/views_eod.py`, `views_indicators.py`, `views_search.py`, `apps/chain_sight/api/views.py`)는 모두 **기본값 `IsAuthenticated` 상속** → 무인증 노출 아님.

### 1.2 [HIGH] 미인증 sync 트리거 2건 — audit P0 #6 누락 🔴

`services/serverless/views.py`에서 동일 계열 sync 트리거 엔드포인트 6건은 `audit P0 #6` 주석과 함께 `IsAdminUser`로 보호되었으나, **2건이 `AllowAny`로 남아 있다.**

**(1) `sync_llm_relations_api` — `views.py:2669`**

```python
@permission_classes([AllowAny])
def sync_llm_relations_api(request):
    """POST /api/v1/serverless/llm-relations/sync  Body: {"days": 7}"""
    from services.serverless.tasks import sync_llm_relations_to_graph
    days = int(request.data.get("days", 7))
    task = sync_llm_relations_to_graph.delay(days=days)   # ← 미인증 Celery 작업 트리거
    return Response({"task_id": task.id, "days": days})
```

**(2) `trigger_etf_holdings_sync` — `views.py:2020`**

```python
@permission_classes([AllowAny])
def trigger_etf_holdings_sync(request):
    """POST /api/v1/serverless/etf/sync  Body: {"etf_symbol": "XLK"}"""
    ...
    downloader = ETFCSVDownloader()
    downloader.initialize_etf_profiles()   # ← 미인증으로 외부 CSV 다운로드 + DB 쓰기
```

- **공격 시나리오**: 인증 없이 `POST .../llm-relations/sync` 또는 `.../etf/sync`를 반복 호출 → LLM/Neo4j 동기화 Celery 작업 또는 외부 SPDR/ETF CSV 다운로드를 대량 트리거. **리소스 고갈(DoS) + LLM 비용 폭증 + 무단 상태 변경(데이터 덮어쓰기)**.
- `days` 파라미터는 공격자 제어(`int()` 변환만) → 큰 값으로 작업 부하 증폭 가능.
- **대조 근거**: 같은 파일의 `trigger_sync(163)`, `sync_now(204)`, `trigger_keyword_generation(351)`, `trigger_breadth_sync(710)`, `trigger_heatmap_sync(885)`, `institutional_sync_api(2888)`는 모두 `@permission_classes([IsAdminUser])  # audit P0 #6`. → 이 2건은 명백한 누락.
- **권고**: 두 함수의 `AllowAny`를 `IsAdminUser`로 교체 (audit P0 #6 패턴과 동일). 동기 외부 호출(`etf/sync`)은 가능하면 `.delay()` 비동기 전환 + 관리자 한정.

### 1.3 [MED] 의도적 `AllowAny` 뷰 — 데이터/비용 노출 점검

대부분의 `AllowAny`는 **공개 시장 데이터(읽기 전용)** 이며 주석으로 의도가 명시됨. 다만 다음은 재검토 필요:

- **`integrations/iron_trading/views.py:25` `DailyContextView`** — `permission_classes = [AllowAny]` + `authentication_classes = []` + **throttle 없음**.
  - `GET /api/v1/iron-trading/daily-context` → 외부 트레이딩 봇용 일별 결정보드 입력 제공.
  - 위험: 인증·rate limit 모두 없어 **독자적 트레이딩 시그널(잠재적 영업 자산)을 누구나 무제한 조회** 가능. 최소 `AnonRateThrottle` 적용 또는 API 키/IP allowlist 권고. (MED)
- **`services/serverless/views.py` preset 계열**:
  - `execute_preset(1029)` `POST .../presets/{id}/execute` — `AllowAny`. 스크리너 필터 연산 실행(읽기성이나 연산 비용 존재). (MED — 비용 DoS 표면)
  - `get_shared_preset(1507)` GET, `trending_presets(1607)` GET — 읽기 전용, 공유 코드 기반. (LOW)
  - `share_preset(1448)`, `import_preset(1545)`는 `IsAuthenticated`로 적절히 보호됨 ✅.

### 1.4 정상 확인된 항목 ✅

- `users/jwt_views.py:55 JWTSignUpView`, `users/views.py:152 LogIn`, `:115 PublicUser` → `AllowAny` (회원가입/로그인/공개 프로필, 설계상 정당, `audit P0 #5` 주석).
- `apps/portfolio/api/views.py` 6개 view → `IsAuthenticated`로 통일됨 (`Slice 16 Step 0-B #70`, 과거 `AllowAny`에서 전환).
- `apps/chain_sight/views/watchlist_views.py:33` → `IsAuthenticated` + `audit P0 #2`로 IDOR 수정 흔적.
- admin 계열(`api_request/admin_views.py`, `serverless/views_admin.py`, `market_pulse` Sync/Health) → `IsAdminUser` 적용 ✅.

---

## 2. 인젝션 (A03: Injection)

### 2.1 SQL 인젝션 — 표면 없음 ✅

지정된 4개 `cursor.execute()` 사용처 전수 검토 결과 **모두 안전**:

| 파일:라인 | 쿼리 | 평가 |
|-----------|------|------|
| `config/views.py:90` | `cursor.execute("SELECT 1")` | 정적 헬스체크. 안전 |
| `packages/shared/api_request/admin_views.py:318` | `cursor.execute("SELECT 1")` | 정적. 안전 |
| `apps/chain_sight/services/seed_selection.py:159` | 다중라인 CTE, 모든 변수 `%s` 파라미터 바인딩 (`WHERE date <= %s` 등) | **파라미터화됨. 안전** |
| `services/serverless/services/admin_status_service.py:892` | `pg_stat_user_tables` 정적 쿼리 (사용자 입력 없음) | 안전 |

- 문자열 포매팅(f-string/`.format`/`%`)으로 SQL을 조립하는 패턴 **미발견**. Django ORM 위주 사용으로 인젝션 표면이 구조적으로 낮음.

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01)

사용자 입력이 Gemini 프롬프트로 흘러가는 주요 경로를 검토. **명시적 방어가 적용되어 있음** (`audit P0 #3`).

### 3.1 방어 적용 확인 ✅

- **`services/serverless/services/thesis_builder.py:306-311`** — `user_notes`를 명령이 아닌 **데이터로 취급**. 닫는 태그 escape + 신뢰 경계(`<user_note_untrusted>`) 마커로 인젝션 차단:
  ```python
  # security audit P0 #3 (2026-05-19): 사용자 입력은 명령이 아닌 데이터로 취급.
  # 닫는 태그 escape + 신뢰 경계 표시로 prompt injection 차단.
  sanitized = user_notes.replace("</user_note_untrusted>", "</user_note_untrusted_escaped>")
  ```
- **`thesis/services/thesis_builder.py:445-446`** — 자유 입력 가설 구조화 시 **길이 제한(500자) + 구분자(```` ``` ````, `---`) 제거**:
  ```python
  # 프롬프트 인젝션 방지: 길이 제한 + 구분자 제거
  safe_text = text[:500].replace('```', '').replace('---', '').strip()
  ```
- **`thesis/views/conversation_views.py`** — 입력을 Serializer로 검증(`ConversationResponseSerializer`)하고 `sanitized_state`로 전달.
- **`services/news/services/keyword_extractor.py`** — 프롬프트에 들어가는 것은 시스템이 수집한 **뉴스 데이터(내부)** 이며, source index 매핑에 `1 <= idx <= prompt_limit` 범위 검증 적용. 직접적 사용자 자유 입력 경로 아님.

### 3.2 [INFO] RAG 파이프라인 — 사용자 `question` 직접 삽입

`services/rag_analysis/services/pipeline.py`에서 사용자 `question`이 여러 LLM 호출에 직접 전달됨(`question=question`, 17개 지점). 별도 sanitization 래퍼는 관찰되지 않음.

- **평가**: RAG 분석은 인증된 사용자(`DataBasket*` 뷰 전부 `IsAuthenticated`) + 자기 데이터 컨텍스트 한정이므로 실질 위험 낮음. 다만 LLM 출력이 다운스트림(자동 매매/실행)으로 흐르지 않는지, 출력 신뢰 경계는 유지되는지 정책 문서화 권고. (INFO)
- **공통 권고**: 모든 LLM 응답에 면책 조항 포함 + LLM 출력을 코드/SQL/명령으로 절대 직접 실행 금지 원칙 유지(현재 위반 미발견).

---

## 4. 시크릿 관리 (A07: Identification & Authentication Failures / A05)

### 4.1 양호 ✅

- **하드코딩 시크릿 미발견**: `(api_key|password|secret|token) = "<16+자 리터럴>"` 패턴 스캔 결과 0건 (테스트/placeholder/getenv 제외).
- **`.gitignore`**: `.env`, `*.key`, `.venv` 등 포함. `git ls-files`에 추적되는 것은 `.env.example`뿐 (실제 `.env` 미추적 확인).
- **운영 배포 가드** (`config/settings.py:163-177`):
  ```python
  if not DEBUG:
      if SECRET_KEY == _SECRET_KEY_DEV_FALLBACK:
          raise ImproperlyConfigured("SECRET_KEY ... 운영에서 반드시 지정")
      if not NEO4J_PASSWORD:
          raise ImproperlyConfigured("NEO4J_PASSWORD ... 운영에서 반드시 지정")
  ```
  → 운영(DEBUG=False)에서 시크릿 누락 시 **즉시 기동 실패**. fail-secure ✅.
- **JWT 서명 키 분리**: `JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or SECRET_KEY` (`settings.py:154`) — 위조 공격 표면 축소 의도.

### 4.2 [LOW] SECRET_KEY dev fallback

`settings.py:149-151`에 dev 전용 placeholder fallback 존재. 운영 가드로 차단되므로 위험은 낮으나, fallback 문자열이 소스에 상수로 존재(`django-insecure-DEV-ONLY-...`). 개발 환경에서만 사용되며 운영 차단됨 → **LOW (수용 가능)**.

---

## 5. CORS / XSS / 에러 노출 (A05: Security Misconfiguration)

### 5.1 CORS — 양호 ✅

`config/settings.py:317-338`

```python
CORS_ALLOWED_ORIGINS = [ ... ]   # allowlist 명시
# DEBUG 의존 제거 — 운영 배포 시 의도치 않은 전체 허용 방지
CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'  # 기본 False
CORS_ALLOW_CREDENTIALS = True
```

- 전체 허용(`CORS_ALLOW_ALL_ORIGINS`)이 **DEBUG와 분리**되어 명시적 env로만 활성화 → 운영 오설정 방지. 양호.
- 참고: `CORS_ALLOW_CREDENTIALS = True`이므로 allowlist에 와일드카드/과도한 origin이 들어가지 않도록 배포 시 점검 권고.

### 5.2 DEBUG / ALLOWED_HOSTS — 양호 ✅

`settings.py:157-160`

```python
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'   # 기본 False
ALLOWED_HOSTS = [...env...] or (['*'] if DEBUG else [])         # 운영은 빈 목록 → 명시 강제
```

- DEBUG 기본 False, `ALLOWED_HOSTS` 와일드카드는 DEBUG에서만. 양호.

### 5.3 에러 노출 — 양호 ✅

`config/exception_handler.py` (`custom_exception_handler`)

- DRF 기본 핸들러를 감싸 `{detail, code, errors, status_code}` envelope로 표준화. **스택트레이스/내부 예외 메시지를 클라이언트에 노출하지 않음** (알 수 없는 dict는 `"Error"`로 일반화).
- 미처리 예외(`response is None`)는 `None` 반환 → Django가 처리, DEBUG=False에서 일반 500 페이지(트레이스백 없음).
- **권고**: `EXCEPTION_HANDLER`가 `response is None`인 비-DRF 예외에 대해서는 표준 envelope를 적용하지 않으므로, 운영 500 응답 포맷 일관성을 위해 fallback 처리 추가 검토(기능적 사항, 보안 영향 낮음).

### 5.4 [LOW] HealthCheckView 정보 노출

`packages/shared/api_request/admin_views.py:294-301` — `permission_classes = []` (완전 공개).

```python
class HealthCheckView(APIView):
    permission_classes = []  # 인증 불필요
    def get(self, request):
        # DB(postgresql) / Redis(redis) 컴포넌트 상태 반환
```

- `GET /api/v1/health/`가 인프라 구성(PostgreSQL, Redis)과 컴포넌트 healthy/degraded 상태를 **미인증 공개**. 로드밸런서 헬스체크 용도로는 일반적이나, 인프라 토폴로지(DB/캐시 종류) 노출은 정찰(reconnaissance) 정보 제공.
- **권고**: 상태만(`{"status": "ok"}`) 반환하고 컴포넌트 상세(type 등)는 `IsAdminUser` 전용 엔드포인트로 분리. (LOW)

### 5.5 [LOW] 통계/stats 엔드포인트 정보 노출

`services/serverless/views.py`의 `llm_relations_stats_api(2700)` 등 다수 `AllowAny` GET가 내부 데이터 규모(관계 수, 신뢰도 분포 등)를 노출. 민감도 낮으나 미인증 공개 범위 점검 권고. (LOW)

---

## 6. 권고 조치 우선순위 (Remediation Priority)

| 우선 | 항목 | 위치 | 조치 |
|------|------|------|------|
| 🔴 1 | 미인증 sync 트리거 | `serverless/views.py:2669`, `:2020` | `AllowAny` → `IsAdminUser` (audit P0 #6 패턴) |
| 🟠 2 | iron_trading 공개+무제한 | `integrations/iron_trading/views.py:25` | throttle 추가 + API 키/IP allowlist 또는 인증 |
| 🟠 3 | execute_preset 비용 DoS | `serverless/views.py:1029` | rate limit 강화 또는 `IsAuthenticated` 검토 |
| 🟡 4 | HealthCheck 토폴로지 노출 | `api_request/admin_views.py:294` | 공개 응답 최소화, 상세는 admin 전용 |
| 🟡 5 | RAG question 인젝션 정책 | `rag_analysis/services/pipeline.py` | LLM 출력 신뢰 경계 정책 문서화 |
| ⚪ 6 | SECRET_KEY fallback / 통계 노출 | `settings.py:149`, stats API | 현 가드로 수용 가능, 모니터링 |

---

## 7. 긍정 평가 요약 (What's Working Well)

1. **Fail-secure 기본 권한**: 전역 `IsAuthenticated`로 누락 뷰도 인증 강제.
2. **SQL 인젝션 표면 없음**: 모든 raw SQL 파라미터 바인딩 / Django ORM 중심.
3. **프롬프트 인젝션 방어 내재화**: 신뢰 경계 태그 + escape + 길이/구분자 제한 (audit P0 #3).
4. **시크릿 위생**: 하드코딩 없음, `.env` 미추적, 운영 가드로 누락 시 기동 차단.
5. **에러 envelope 표준화**: 스택트레이스 미노출.
6. **CORS/DEBUG 운영 분리**: 오설정으로 인한 전체 허용 방지.
7. **점진적 보안 부채 상환 이력**: P0 #2/#3/#5/#6, Slice 16 #70 등 과거 감사 조치가 코드에 반영됨.

> 본 보고서는 정적 코드 분석 기반이며, 동적 테스트(실제 인증 우회 PoC, 부하 테스트)는 포함하지 않았다. HIGH 항목 2건은 별도 검증 PoC 없이도 코드상 명확하므로 우선 조치 권장.

---

*감사 수행: Claude (읽기 전용 정적 분석) · 2026-06-09 · 코드 수정 없음*
