# Stock-Vis 보안 감사 보고서

- **일자**: 2026-06-07
- **범위**: OWASP Top 10 기반 (인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿 관리, CORS/XSS/에러 노출)
- **모드**: 읽기 전용 감사 (코드 수정 없음)
- **브랜치**: main
- **감사자**: CSO 모드 (Claude) — 코드 트레이싱 기반, 라이브 요청 없음

> ⚠️ 이 보고서는 AI 보조 스캔입니다. 전문 침투 테스트를 대체하지 않습니다. 운영 배포 전 자격 있는 보안 업체의 검증을 권장합니다.

---

## 0. 요약 (Executive Summary)

전반적으로 **방어 자세는 양호**하다. `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` 기본값, SQL 파라미터 바인딩 100%, env 기반 시크릿 관리 + 운영 배포 가드, IDOR 방어(`get_queryset(user=request.user)`)가 일관되게 적용되어 있다. **CRITICAL/HIGH 등급 취약점은 발견되지 않았다.**

남은 위험은 주로 **운영 환경(DEBUG=False) 전환 시 드러나는 하드닝 격차**와 **인증 엔드포인트 브루트포스 방어 부재**다.

### 심각도별 집계

| 심각도 | 건수 | 항목 |
|--------|------|------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| **MED** | **4** | M1 로그인 throttle 부재, M2 iron-trading 무인증 공개 API, M3 운영 보안 헤더 미설정, M4 에러 메시지 노출(54곳) |
| **LOW** | **4** | L1 권한 클래스 미명시(22뷰), L2 HealthCheck 무인증, L3 프롬프트 인젝션 방어 부분적, L4 CORS credentials 조합 위험 |
| **INFO** | **6** | I1 하드코딩 이메일, I2 DB 기본값 커밋, I3~I6 긍정 확인 |

---

## 1. 인증 / 인가 (OWASP A01: Broken Access Control)

### 1.1 기본값 — 양호 ✅

`config/settings.py:360-362`
```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
```
audit P0 #5 (2026-04-29)에서 `IsAuthenticatedOrReadOnly → IsAuthenticated`로 강화됨. **권한 클래스를 명시하지 않은 모든 뷰는 인증 필수로 기본 보호**된다.

### 1.2 IDOR 방어 — 양호 ✅

사용자별 자원(Portfolio, Watchlist, Thesis, UserInterest, Favorites)을 다루는 모든 뷰가 `IsAuthenticated` + `filter(user=request.user)` / `get_object(pk, user)` 패턴을 일관 적용. pk/symbol 변조로 타 사용자 자원 접근 불가.

### 1.3 [MED] M2 — iron-trading 공개 무인증 API

**파일**: `integrations/iron_trading/views.py:19-50` (`DailyContextView`)
```python
permission_classes = [AllowAny]
authentication_classes: list = []
```
- **설명**: 외부 봇용 read-only 일별 시장 컨텍스트 API. 인증·API 키·전용 throttle이 전혀 없다.
- **공격 시나리오**: 외부인이 `date`/`universe`/`limit` 파라미터를 바꿔가며 무제한 호출 → ① 집계된 유니버스 랭킹 데이터 스크래핑, ② `limit` 대량 지정 시 스냅샷 빌드 부하 유발.
- **영향**: 가공된 시장 데이터 무단 수집 + 리소스 abuse 표면.
- **권장**: 외부 봇 전용 API 키(헤더 토큰) 도입 또는 IP 허용목록 + `ScopedRateThrottle` 적용, `limit` 상한 검증 확인.
- **신뢰도**: 8/10 (코드 확인). 단, 노출 데이터가 공개 시장 데이터 수준이면 위험 하향 가능.

### 1.4 [LOW] L1 — 권한 클래스 미명시 (의도 불명확)

DEFAULT(`IsAuthenticated`)로 보호되나 `permission_classes`를 **명시하지 않은** 뷰가 약 22개 존재. 공개 의도인지 인증 의도인지 코드만으로 판단 불가 → 향후 DEFAULT 변경 시 의도치 않은 노출/차단 위험.

대표 목록:
- `packages/shared/stocks/views_search.py`: `SymbolSearchView`, `SymbolValidateView`, `PopularSymbolsView`
- `packages/shared/stocks/views_mvp.py`: `StockMVPListView`, `StockMVPDetailView`, `StockRAGContextView`, `SectorListView`
- `packages/shared/stocks/views_indicators.py`: `TechnicalIndicatorView` 외 2
- `packages/shared/stocks/views_eod.py`: `EODDashboardView`, `EODSignalDetailView`, `EODPipelineStatusView`
- `apps/chain_sight/api/views.py`: `ChainSightGraphView`, `SeedListView`, `SectorGraphView` 외 4
- `services/news/api/views.py`: `NewsViewSet`

- **권장**: 각 뷰에 의도를 명시 (`[AllowAny]` 또는 `[IsAuthenticated]`). 동작 변경 아님, 가독성·안전성 개선.

### 1.5 [LOW] L2 — HealthCheckView 무인증

**파일**: `packages/shared/api_request/admin_views.py:294-360`
```python
class HealthCheckView(APIView):
    permission_classes = []  # 인증 불필요
```
- **설명**: DB/Redis/Provider 상태를 무인증 노출. 헬스체크 용도로 **의도된 설계**이나, 내부 컴포넌트 구성(`postgresql`, `redis`, 활성 provider 이름)을 익명에게 드러낸다.
- **권장**: 운영에서는 모니터링 IP만 접근 허용 또는 상세 컴포넌트 정보를 인증 사용자에게만 노출.
- **신뢰도**: 7/10.

> 📌 **정정**: 사전 census 단계에서 서브에이전트가 이 항목을 "LogViewerView(시스템 로그 노출)"로 보고했으나, **실제 코드는 `HealthCheckView`이며 로그를 노출하지 않는다**. 시스템 로그를 무인증 노출하는 뷰는 존재하지 않음을 코드 확인으로 정정한다.

### 1.6 AllowAny 적정성 — 양호 ✅

- Market Pulse v1 (`macro`) 8개 뷰, Serverless Market Movers — 모두 공개 거시경제/시장 데이터. `[AllowAny]` 명시적 지정으로 의도 표현됨. 적절.
- 관리 기능(`trigger_sync`, `sync_now`, serverless `views_admin.py` 12개, Provider admin 5개)은 `IsAdminUser` 적용. 적절.

---

## 2. 인젝션 (OWASP A03: Injection)

### 2.1 SQL 인젝션 — 발견 없음 ✅ (I3)

`cursor.execute()` 사용 4개 파일 전수 검사 결과 **모두 안전**:

| 파일:라인 | 쿼리 | 바인딩 | 판정 |
|-----------|------|--------|------|
| `config/views.py:90` | `SELECT 1` | 정적 | ✅ 안전 |
| `packages/shared/api_request/admin_views.py:318` | `SELECT 1` | 정적 | ✅ 안전 |
| `services/serverless/services/admin_status_service.py:159` | volume CTE | `%s` + `[market_date, market_date]` | ✅ 파라미터 바인딩 |
| `services/serverless/services/admin_status_service.py:892` | `pg_stat_user_tables` | 정적 | ✅ 안전 |
| `apps/chain_sight/services/seed_selection.py:159` | SMA20 CTE | `%s` + `[market_date, market_date]` | ✅ 파라미터 바인딩 |

- 사용자 입력을 SQL 문자열에 f-string/format/`%` 연산으로 직접 삽입하는 곳 없음.
- 나머지 DB 접근은 전부 Django ORM(파라미터화 자동). **SQL 인젝션 위험 없음.**

### 2.2 명령/템플릿 인젝션 — 발견 없음 ✅

LLM 응답을 `eval()`/`exec()`/`Function()`으로 실행하는 코드 없음(2.3·LLM 섹션 참조). `os.system`/`subprocess`로 사용자 입력을 전달하는 경로 없음.

---

## 3. LLM 프롬프트 인젝션 (OWASP A03 확장 / LLM 보안)

### 3.1 [LOW] L3 — 프롬프트 인젝션 방어가 부분적

사용자 입력이 프롬프트에 삽입되는 주요 지점과 방어 상태:

| 파일:라인 | 입력 출처 | 방어 | 평가 |
|-----------|----------|------|------|
| `thesis/services/thesis_builder.py:446-450` | 사용자 가설 자유 입력 | `text[:500]` + ` ``` `·`---` 제거 | 부분적 |
| `thesis/services/indicator_matcher.py:175-206` | 전제/제목/대상 | `_sanitize_for_prompt()` (길이+구분자) | 부분적 |
| `thesis/views/conversation_views.py:237` | 외부 뉴스 제목 | 길이 제한 | 외부 데이터 |
| `services/news/api/views.py:830` | keyword + sentiment | — | 외부/구조화 |
| `services/rag_analysis/services/adaptive_llm_service.py:193` | 사용자 질문 + context | 없음 (user-message 위치) | FP 규칙 #13 |

**현 방어의 한계** (`_sanitize_for_prompt`):
```python
text = text[:max_length]                       # 길이 제한
text = text.replace('```', '').replace('---', '')  # 구분자 제거
```
- 길이·구분자만 제거하므로 **명령형 인젝션**("이전 지시 무시하고 …")은 차단하지 못한다.

**블라스트 반경이 제한적인 이유** (→ LOW 등급):
1. 출력이 **JSON으로 파싱**되어 사용되며, HTML 렌더링이나 코드 실행이 없다.
2. 입력은 대부분 **사용자 본인 데이터가 본인에게** 되돌아오는 구조 (자기 표적).
3. `max_output_tokens` 상한(1000~2000) + circuit breaker(`get_circuit('gemini_thesis', ...)`)로 폭주 방지.
4. RAG의 사용자 질문은 user-message 위치 → OWASP/CSO FP 규칙상 인젝션으로 분류 안 함.

- **권장**: 명령형 패턴(예: "ignore", "instructions", "system") 탐지 또는 입력을 구조화된 필드로 분리(프롬프트 본문과 데이터 경계 명확화). 다만 현 위험 등급은 낮음.

### 3.2 긍정 확인 ✅ (I6)

- LLM 출력을 `eval`/`exec`로 실행하는 경로 없음.
- 프론트엔드에 `dangerouslySetInnerHTML` 사용 없음(테스트의 `innerHTML` 검증 2건뿐) → LLM 출력 XSS 경로 없음. React 자동 이스케이프.
- LLM 비용 가드 존재: `LLM_BUDGET_MAX_CALLS=50`, `CostGuard`, circuit breaker → 비용 증폭 공격 방어.

---

## 4. 시크릿 관리 (OWASP A02 / A05)

### 4.1 긍정 확인 ✅ (I4)

- **하드코딩 시크릿 0건**. 모든 API 키/비밀번호가 `os.getenv()` 경유.
- `SECRET_KEY`: dev 전용 placeholder fallback + **운영 배포 가드** — `DEBUG=False`에서 미설정 시 `ImproperlyConfigured` raise (`settings.py:164-171`).
- `JWT_SIGNING_KEY`를 `SECRET_KEY`와 분리(위조 표면 축소).
- `NEO4J_PASSWORD`: 운영 배포 가드 적용. 기존 디폴트 `'stockvis123'` 제거됨.
- `.env`는 `.gitignore`에 포함(`:10`, `:138`), **git 추적 중인 `.env` 파일 없음** 확인.

### 4.2 [INFO] I1 — 하드코딩 수신자 이메일

`config/settings.py:542-545`
```python
CELERY_ERROR_RECIPIENTS = ['goid545@naver.com', 'jinie545@gmail.com']
```
- 시크릿은 아니나 개인 PII가 소스에 박혀 있음. env 변수화 권장.

### 4.3 [INFO] I2 — DB 기본값 커밋

`settings.py:260-261`: `DB_USER` 기본값 `'byeongjinjeong'`, `DB_PASSWORD` 기본값 `''`. 로컬 개발용이며 운영에서는 env로 override되나, 기본 사용자명 노출은 정보 축소 차원에서 env 강제 권장.

---

## 5. CORS / XSS / 에러 노출 (OWASP A05: Security Misconfiguration)

### 5.1 CORS — 대체로 양호, 조건부 주의

`settings.py:317-327`
```python
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'  # 기본 False
CORS_ALLOW_CREDENTIALS = True
```
- ✅ 허용 origin이 localhost로 한정. `CORS_ALLOW_ALL`이 DEBUG에서 분리되어 명시적 env 제어(의도치 않은 전체 허용 방지).
- **[LOW] L4**: `CORS_ALLOW_CREDENTIALS = True` 상태에서 누군가 운영에 `DJANGO_CORS_ALLOW_ALL=True`를 설정하면 **임의 origin이 인증 쿠키와 함께 요청 가능**해진다(브라우저는 credentials+wildcard를 막지만 django-cors-headers는 origin 반사 방식). 운영 .env에서 절대 `True`로 두지 않도록 문서/가드 권장.

### 5.2 DEBUG / ALLOWED_HOSTS — 양호 ✅

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False')` → 기본 False.
- `ALLOWED_HOSTS`는 DEBUG=True일 때만 `['*']`, 운영에서는 env 필수.

### 5.3 [MED] M3 — 운영 전송/쿠키 보안 헤더 미설정

`settings.py` 전체에 다음 설정이 **0건**:
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`
- `SecurityMiddleware`는 등록되어 있으나 위 설정 없이는 HSTS·HTTPS 강제·Secure 쿠키가 비활성.
- **영향**: 운영(HTTPS) 배포 시 세션/CSRF 쿠키가 평문 전송 가능, 다운그레이드/중간자 노출.
- **권장**: 운영 settings에 `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_HSTS_SECONDS` 추가. (개발 영향 없도록 `DEBUG` 분기)
- **신뢰도**: 8/10. (현재 로컬 개발 한정이면 영향 없음 → 운영 전환 전 필수)

### 5.4 [MED] M4 — 에러 메시지(`str(e)`) 응답 노출 54곳

`{"error": str(e)}` / `Response(..., str(e))` 형태로 내부 예외 문자열을 클라이언트에 반환하는 곳이 **54건**. 예: `admin_views.py`, `admin_status_service`는 try/except에서 raw 예외를 그대로 노출.
- **영향**: ORM 쿼리 구조, 파일 경로, 내부 모듈명 등 정보 노출 → 공격 정찰 보조.
- **참고**: DRF 표준 예외는 `config.exception_handler.custom_exception_handler`로 처리되나, 명시적 `try/except: return Response({"error": str(e)})`는 이 핸들러를 우회한다.
- **권장**: 사용자에게는 일반 메시지("내부 오류"), 상세는 `logger.exception`으로만. 운영(DEBUG=False)에서 `str(e)` 노출 일괄 제거.
- **신뢰도**: 7/10 (각 케이스의 민감도 편차 있음).

---

## 6. 추가 발견 — 인증 설계 (OWASP A04 / A07)

### 6.1 [MED] M1 — 로그인/회원가입 엔드포인트 브루트포스 방어 부재

- `REST_FRAMEWORK`에 `DEFAULT_THROTTLE_RATES`는 정의되어 있으나 **`DEFAULT_THROTTLE_CLASSES`가 없다** → throttle이 전역 적용되지 않는다.
- `throttle_classes`가 적용된 곳은 Watchlist 뷰(`WatchlistRateThrottle`)와 market_pulse 일부뿐.
- **`CustomTokenObtainPairView`(로그인), `JWTSignUpView`(회원가입), `LogIn`에 throttle 미적용** — 확인됨.
- **공격 시나리오**: 공격자가 로그인 엔드포인트에 비밀번호 사전을 무제한 대입(credential stuffing / brute force). 계정 잠금 정책도 없음.
- **영향**: 계정 탈취, 회원가입 스팸.
- **권장**: 로그인/회원가입 뷰에 `ScopedRateThrottle`(예: `5/min` anon) 적용 + 실패 횟수 기반 계정 잠금. 이미 정의된 `'anon': '20/min'` rate를 활용하려면 `DEFAULT_THROTTLE_CLASSES`에 `AnonRateThrottle`/`UserRateThrottle` 추가.
- **신뢰도**: 8/10.

### 6.2 긍정 확인 ✅ (I5)

- JWT: Access 60분 / Refresh 7일, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, token_blacklist 앱 등록. 토큰 관리 양호.
- 비밀번호 검증기 4종 활성(`AUTH_PASSWORD_VALIDATORS`).

---

## 7. 우선순위 권장 로드맵

| 순위 | 항목 | 등급 | 조치 | 비고 |
|------|------|------|------|------|
| 1 | M1 로그인 throttle | MED | `DEFAULT_THROTTLE_CLASSES` + 로그인/회원가입 `ScopedRateThrottle` | 운영 전 필수 |
| 2 | M3 보안 헤더 | MED | 운영 settings에 `SECURE_*`/쿠키 Secure | 운영 전 필수 |
| 3 | M4 에러 노출 | MED | 운영에서 `str(e)` 응답 제거, 일반 메시지화 | 점진 적용 |
| 4 | M2 iron-trading | MED | API 키/IP 허용목록 + throttle | 데이터 민감도 확인 후 |
| 5 | L1 권한 명시 | LOW | 22개 뷰 `permission_classes` 명시 | 동작 변경 없음 |
| 6 | L3 프롬프트 방어 | LOW | 명령형 패턴 탐지 보강 | 블라스트 반경 작음 |
| 7 | L4/I1/I2 | LOW/INFO | CORS_ALLOW_ALL 가드 문서화, 이메일·DB 기본값 env화 | — |

---

## 8. 결론

- **CRITICAL/HIGH 없음.** 핵심 방어(인증 기본값, SQL 파라미터화, 시크릿 env 관리, IDOR 방어, 운영 배포 가드)가 견고하게 적용됨.
- 남은 위험은 **운영 환경 전환 시점의 하드닝**(M1 throttle, M3 보안 헤더, M4 에러 노출)에 집중. 개발 단계에서는 영향이 제한적이나, 운영 배포 **전에 M1·M3는 반드시** 처리할 것.
- 사전 census 단계의 "시스템 로그 무인증 노출(LogViewerView)" 보고는 코드 확인 결과 **오탐**으로 정정함(실제는 `HealthCheckView`, 로그 노출 없음).

---

### 부록 A — 감사 커버리지

- 인증/인가: APIView/ViewSet/@api_view 정의 40개 파일 전수 census
- 인젝션: `cursor.execute()` 4개 파일 + ORM 경로 전수
- LLM: Gemini/genai 호출 29개 파일 중 사용자 입력 삽입 지점 5개 트레이싱
- 시크릿: 하드코딩 패턴 grep + `.gitignore`/git 추적 확인
- 설정: `config/settings.py` 전수 (CORS, DEBUG, REST_FRAMEWORK, JWT, throttle, 보안 헤더)

### 부록 B — 면책

이 도구는 전문 보안 감사를 대체하지 않습니다. AI 보조 스캔으로 일반적 취약점 패턴을 잡아내지만, 미묘한 인증 흐름 결함이나 false negative가 있을 수 있습니다. 민감 데이터·결제·PII를 다루는 운영 시스템은 전문 침투 테스트 업체의 검증을 받으십시오.
