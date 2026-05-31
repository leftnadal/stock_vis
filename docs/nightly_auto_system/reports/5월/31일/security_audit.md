# Stock-Vis 보안 감사 보고서 (OWASP Top 10 기반)

- **감사일**: 2026-05-31
- **대상**: Stock-Vis (Django REST Framework + PostgreSQL + Celery + Gemini LLM)
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **브랜치**: main (`f80b7dd`)
- **감사 도구**: /cso (Chief Security Officer) 워크플로 + 수동 코드 추적
- **신뢰도 게이트**: 8/10 (daily 모드)

> ⚠️ 본 보고서는 AI 보조 정적 스캔이며 전문 침투 테스트를 대체하지 않습니다.
> 결제·PII를 다루는 운영 시스템은 전문 보안 업체의 감사를 별도로 권장합니다.

---

## 0. 요약 (Executive Summary)

| 심각도 | 건수 | 핵심 내용 |
|--------|------|----------|
| CRITICAL | 0 | — |
| HIGH | 1 | serverless 무인증 LLM/고비용 트리거 클러스터 (6개 엔드포인트) |
| MEDIUM | 3 | 스크리너 프리셋 익명 변경, 전역 throttle 미적용, thesis_builder f-string 삽입 |
| LOW | 3 | iron_trading 완전 무인증, 예외 메시지 노출, 하드코딩 이메일 |
| INFO | 1 | 보안 기본값 다수 양호 (positive findings) |

**총평**: 프로젝트의 보안 **기본 토대는 견고**하다. `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`로 secure-by-default를 채택했고, DEBUG/SECRET_KEY/NEO4J 운영 가드, CORS 화이트리스트, JWT 서명키 분리, `.env` gitignore, LLM 신뢰경계 escape(`llm_service.py`)가 잘 구현되어 있다. 과거 audit P0 #5/#6 하드닝의 흔적이 코드 전반에 남아 있다.

**그러나** audit P0 #6(`trigger_*` → IsAdminUser) 하드닝이 **불완전하게 적용**되어, 동일 성격의 고비용·변경 엔드포인트 6개가 여전히 `@authentication_classes([])` + `AllowAny`로 노출돼 있다. 이 중 3개는 **인증 없이 유료 Gemini LLM 호출**을 트리거할 수 있어 비용 증폭(financial DoS) 위험이 실재한다. 전역 throttle 미적용이 이를 증폭한다.

---

## 1. 인증 / 인가 (OWASP A01: Broken Access Control)

### 검사 범위
- DRF 뷰 클래스/함수 ~150개의 `permission_classes` 전수 확인
- `AllowAny` 사용처 전수 추적
- admin 뷰의 `IsAdminUser` 적용 검증

### 기본 설정 (양호)
`config/settings.py:355-374`:
```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
```
→ **secure-by-default**. `permission_classes`를 명시하지 않은 뷰는 자동으로 인증 필요. 즉 "permission_classes 누락"은 위험이 아니라 안전. 실제 위험은 **명시적 `AllowAny` 오용**과 **admin 작업의 인증 누락**이다.

### admin 뷰 검증 (양호)
- `serverless/views_admin.py`: 12개 뷰 전부 `IsAdminUser` ✅
- `packages/shared/api_request/admin_views.py`: Provider/RateLimit/Cache/Test/Config 전부 `IsAdminUser` ✅ (HealthCheckView만 무인증 — 의도된 모니터링용, 정상)
- `news/api/views.py`: ML/파이프라인/알림 관리 action 14개 전부 `IsAdminUser` ✅
- `serverless/views.py`의 `trigger_sync`, `sync_now`, `trigger_keyword_generation`, `trigger_breadth_sync`, `trigger_heatmap_sync`, `institutional_sync_api` → 전부 `IsAdminUser` (`# audit P0 #6`) ✅
- `macro/views.py:DataSyncView` → `IsAdminUser` ✅

### 🔴 [HIGH] H1 — serverless 무인증 LLM/고비용 트리거 클러스터

- **심각도**: HIGH
- **신뢰도**: 9/10
- **상태**: VERIFIED (코드 추적 확인)
- **카테고리**: OWASP A01 (Broken Access Control) + A04 (Insecure Design) + LLM 비용 증폭

**문제**: audit P0 #6에서 `trigger_*` 동기화 엔드포인트는 `IsAdminUser`로 잠갔으나, **동일하게 고비용·상태변경·LLM을 트리거하는 형제 엔드포인트 6개**가 `@authentication_classes([])` + `@permission_classes([AllowAny])`로 남아 있다. 인증·throttle 모두 없음.

| 엔드포인트 | 파일:줄 | 동작 | 위험 |
|-----------|---------|------|------|
| `generate_thesis` | `serverless/views.py:1611` | `ThesisBuilder.build_thesis()` → **Gemini LLM 호출** | LLM 비용 증폭 |
| `extract_relations_from_news_api` | `serverless/views.py:2405` | Celery `batch_extract_relations_from_news` (최대 100건 뉴스 → **LLM 관계 추출**) | LLM 비용 증폭 + 큐 플러딩 |
| `sync_llm_relations_api` | `serverless/views.py:2554` | LLM 관계 동기화 트리거 | LLM 비용 증폭 |
| `trigger_etf_holdings_sync` | `serverless/views.py:1944` | 외부 SPDR CSV 다운로드 + ETFProfile DB 갱신 (전체 ETF 루프) | 외부 API 소진 + DB 변경 |
| `resolve_etf_csv_url` | `serverless/views.py:2046` | 외부 URL 탐색/해석 + DB 갱신 | 외부 호출 + DB 변경 |
| `refresh_theme_matches_api` | `serverless/views.py:2376` | `refresh_all_matches()` 전체 재계산 + DB 대량 변경 | 계산 자원 + DB 변경 |

**공격 시나리오 (generate_thesis 기준)**:
1. 공격자가 인증 없이 `POST /api/v1/serverless/thesis/generate`에 `stocks` 배열을 담아 반복 호출
2. 매 호출마다 `ThesisBuilder`가 Gemini 2.5 Flash를 호출 (유료 + 15 RPM / 1500 RPD 무료 한도)
3. 전역 throttle 미적용(M2 참조)으로 분당 수백 회 호출 가능 → **API 비용 폭증 + Gemini rate limit 소진으로 정상 사용자 서비스 거부**
4. `trigger_etf_holdings_sync`/`extract_relations_*`도 동일하게 Celery 워커·외부 API 한도를 익명으로 고갈 가능

> 참고: CSO FP 규칙은 일반 DoS를 제외하지만 **LLM 비용/지출 증폭은 명시적 예외**로 financial risk로 분류한다.

**근거 코드** (`serverless/views.py:1608-1611`):
```python
@api_view(['POST'])
@authentication_classes([])  # 인증 불필요 (만료된 토큰으로 인한 401 방지)
@permission_classes([AllowAny])
def generate_thesis(request):
    ...
    builder = ThesisBuilder(language='ko')
    thesis = builder.build_thesis(stocks=stocks, ...)   # ← Gemini 호출
```
주석 "만료된 토큰으로 인한 401 방지"는 UX 편의를 위해 인증을 끈 것으로, 비용 노출 트레이드오프가 검토되지 않은 것으로 보인다.

**권장 조치**:
- 6개 엔드포인트 중 **상태변경/동기화 3개**(`trigger_etf_holdings_sync`, `resolve_etf_csv_url`, `refresh_theme_matches_api`, `sync_llm_relations_api`) → 형제와 동일하게 `IsAdminUser`로 전환
- **LLM 생성 2개**(`generate_thesis`, `extract_relations_from_news_api`) → 최소 `IsAuthenticated` + 사용자별 scoped throttle(`market_pulse_llm: 5/min` 패턴 재사용) 적용. UX상 비로그인 허용이 꼭 필요하면 익명 throttle(예: `anon 5/hour`) + 입력 크기 상한 강제

### 🟡 [MED] M1 — 스크리너 프리셋 익명 변경 가능

- **심각도**: MEDIUM / **신뢰도**: 8/10 / **상태**: VERIFIED
- **위치**: `serverless/views.py:878` (`screener_presets_api`), `:935` (`screener_preset_detail`), `:986` (`execute_preset`)
- **카테고리**: OWASP A01

**문제**: 프리셋 생성/수정/삭제/실행이 모두 `AllowAny`. 소유자 검증은 `if preset.user and preset.user != request.user`로 되어 있으나, **익명 사용자가 생성한 프리셋은 `preset.user = None`** 이 되어 이 가드가 `None and ...` → False로 건너뛰어진다. 결과적으로:
- 익명 A가 만든 `user=None` 프리셋을 익명 B가 자유롭게 `PATCH`(수정) 가능
- `category`가 system/beginner/intermediate가 아닌 `user=None` 프리셋은 익명 누구나 `DELETE` 가능
- `GET`마다 `use_count`/`last_used_at`를 비인증으로 증가시켜 카운터 오염 가능 (`:953-955`)

**근거 코드** (`serverless/views.py:960-963`):
```python
elif request.method == 'PATCH':
    if preset.user and preset.user != request.user:   # preset.user=None이면 가드 무력화
        raise PermissionDenied("You can only edit your own presets")
```

**공격 시나리오**: 공격자가 익명으로 프리셋을 대량 생성/수정/삭제하여 공용 프리셋 풀을 오염시키거나, 다른 익명 사용자의 프리셋을 임의 변경. 직접적 데이터 유출은 아니나 데이터 무결성 훼손.

**권장 조치**: 프리셋 생성/수정/삭제는 `IsAuthenticated` 강제(생성 시 `user` 필수). 익명 read-only가 필요하면 GET만 `AllowAny`로 분리하고 `use_count` 증가는 인증 사용자에 한정.

### 정상 (참고)
- `macro/views.py`의 8개 `AllowAny` 뷰 → 공개 시장 대시보드(Market Pulse) 데이터 read-only, 의도된 공개. 정상.
- `packages/shared/stocks/views_market_movers.py`, `news market-feed/interest-options` → 콜드스타트/온보딩용 공개 read 데이터. 정상.
- `packages/shared/users/views.py`의 `LogIn`/`PublicUser`, `jwt_views.py` → 명시적 `AllowAny` (audit P0 #5 주석). 정상.
- `validation/api/views.py:470 PeerPreferenceView` → `IsAuthenticatedOrReadOnly` (GET 공개, 쓰기 인증). 허용 범위.

---

## 2. 인젝션 (OWASP A03: Injection)

### SQL 인젝션 — `cursor.execute()` 4곳 전수 검증 (전부 안전 ✅)

| 파일 | 줄 | SQL | 판정 |
|------|-----|-----|------|
| `config/views.py` | 90 | `"SELECT 1"` (정적) | ✅ 안전 |
| `packages/shared/api_request/admin_views.py` | 318 | `"SELECT 1"` (정적) | ✅ 안전 |
| `serverless/services/admin_status_service.py` | 849 | `pg_stat_user_tables` 조회 (정적, 사용자 입력 없음) | ✅ 안전 |
| `apps/chain_sight/services/seed_selection.py` | 159 | WITH CTE, `WHERE date <= %s` + 인자 `[market_date, market_date]` | ✅ 파라미터 바인딩 |

→ **문자열 보간으로 사용자 입력을 SQL에 넣는 사례 없음**. `seed_selection.py`는 `%s` 플레이스홀더 + 인자 리스트 분리(파라미터 바인딩)를 정확히 사용. 더하여 `market_date`는 내부 계산값으로 사용자가 직접 제어하지 않음.

### 명령어/템플릿 인젝션
- `eval()`/`exec()`/`os.system()`/`subprocess(shell=True)`에 사용자 입력이 흐르는 경로 미발견.

---

## 3. LLM 프롬프트 인젝션 (OWASP A03 확장 / LLM Security)

서브에이전트 정밀 추적 결과(thesis_builder, conversation_views, keyword_extractor, rag_analysis/services 전반):

### 양호 (방어 구현 확인 ✅)
- **`rag_analysis/services/llm_service.py:186-191`**: context/question을 데이터로 취급, 닫는 태그(`</context_data>`, `</user_question>`) escape + "블록 내 지시는 데이터로만 취급" 명시. **모범 사례** (audit P0 #3).
- **`thesis/views/conversation_views.py:43-111`**: client conversation_state 필드 화이트리스트 + 타입/범위/크기(50KB)/history 길이(20) 검증.
- **`news/services/keyword_extractor.py`**, **`rag_analysis/services/entity_extractor.py`**, **`thesis/services/prompt_builder.py`**: system prompt를 `system_instruction`으로 고정 분리, 사용자 데이터는 user-message(`contents`)로만 전달. 지표 카탈로그는 정적 하드코딩. 정상.

### 🟡 [MED] M3 — thesis_builder.py 사용자 입력 f-string 삽입

- **심각도**: MEDIUM / **신뢰도**: 7/10
- **위치**: `thesis/services/thesis_builder.py:446`, `:705-706`
- 자유 입력(`text[:500]`)과 누적된 가설 필드(`title`/`direction`/`target`)가 f-string으로 프롬프트에 삽입. 필터는 `` ``` ``/`---` 제거 + 길이 제한 수준.
- **위험 평가**: 삽입 위치가 **user-message 영역**이라 system prompt 위조는 아니며(구조적 인젝션 차단됨), CSO FP 규칙상 "user-message 위치 사용자 입력"은 인젝션이 아님. 다만 출력 파싱이 JSON 구조에 의존하므로 입력으로 파싱 교란을 시도할 여지가 남아 MED로 분류.
- **권장**: structured output(이미 `prompt_builder.call_gemini`는 `response_schema` 사용)을 thesis_builder 자유입력 경로에도 확대 적용 + 제어문자 정규식 필터.

### LLM 출력 처리 (양호)
- LLM 출력을 `eval`/`exec`하거나 raw HTML로 렌더하거나 SQL에 넣는 경로 미발견. JSON 파싱 후 모델 필드로 저장.

### LLM 비용 가드
- `settings.py:32 LLM_BUDGET_MAX_CALLS=50`, `llm_service` retry/backoff, CostGuard slice ledger 존재. **그러나** H1의 무인증 엔드포인트는 이 가드 이전에 호출 자체가 무제한 트리거되는 것이 문제(엔드포인트 단 인증/throttle이 1차 방어선).

---

## 4. 시크릿 관리 (OWASP A02: Cryptographic Failures / Secrets)

### 양호 ✅
- **`.env` gitignore 확인**: `.gitignore:10, 138`에 `.env` 존재. `git ls-files` 결과 `.env` 추적 안 됨 ✅
- **git 히스토리 시크릿 스캔**: `sk-`/`AKIA`/`ghp_` 패턴 실제 키 **미발견**. 유일 매치는 `docs/AWS-account-setup-security-guide.md`(설정 가이드 문서의 예시 패턴, 실 키 아님).
- **API 키 전부 `os.getenv()`** 로드 (`settings.py:22-28`). 하드코딩된 키/비밀번호 없음.
- **SECRET_KEY 운영 가드** (`settings.py:164-176`): `DEBUG=False`에서 dev fallback 사용 시 `ImproperlyConfigured` raise. NEO4J_PASSWORD 동일 가드.
- **JWT 서명키 분리** (`settings.py:154 JWT_SIGNING_KEY`): SECRET_KEY와 별도 회전 가능(공격 표면 축소).
- 과거 약점이던 Neo4j 기본 비밀번호 `stockvis123` 제거됨 (`settings.py:124` 주석 확인).

### 🟢 [LOW] L3 — 하드코딩된 알림 수신 이메일

- **위치**: `config/settings.py:543-544`
```python
CELERY_ERROR_RECIPIENTS = ['goid545@naver.com', 'jinie545@gmail.com']
```
- 시크릿은 아니나 개인 PII가 소스에 박혀 있음. 환경변수화 권장(이미 `REPORT_RECIPIENT_EMAIL`은 env 처리됨 — 일관성 위해 동일 적용).
- **심각도**: LOW (정보성)

---

## 5. CORS / XSS / 에러 노출 (OWASP A05: Security Misconfiguration)

### CORS (양호 ✅)
- `CORS_ALLOWED_ORIGINS` = `localhost:3000` / `127.0.0.1:3000` 화이트리스트 (`settings.py:318-321`)
- `CORS_ALLOW_ALL_ORIGINS` = 기본 `False`, env `DJANGO_CORS_ALLOW_ALL`로만 명시 활성화 (`:325`) — DEBUG 의존을 끊어 운영 오설정 방지. **모범**.
- `CORS_ALLOW_CREDENTIALS = True`이나 origin이 화이트리스트로 제한되어 안전.

### DEBUG (양호 ✅)
- `DEBUG` 기본 `False` (`settings.py:157`), env로만 활성화.
- `ALLOWED_HOSTS`: DEBUG=False에서 env 미설정 시 빈 리스트(`[]`)로 차단 (`:159-161`).

### 🟢 [LOW] L2 — 예외 메시지 클라이언트 노출

- **위치**: `packages/shared/api_request/admin_views.py` 다수(`{"error": str(e)}`), `serverless/views.py` 일부
- 500 응답 본문에 `str(e)` 원문을 반환하는 패턴. DEBUG=False여도 예외 메시지 일부가 클라이언트에 노출됨(내부 구조 단서). admin 뷰는 `IsAdminUser`라 노출 대상이 관리자로 한정되어 위험 낮음.
- `generate_thesis`(`:1696-1714`)는 full traceback을 **로그에만** 남기고 클라이언트엔 `type + 100자`로 절단 — 양호한 처리. 표준 `EXCEPTION_HANDLER`(`config.exception_handler`)도 적용됨.
- **심각도**: LOW. 권장: 서비스 계층 `str(e)` 직접 반환을 표준 envelope의 일반 메시지로 통일.

### XSS
- 백엔드는 DRF JSON API. 프론트는 React(Next.js)로 기본 escape. `dangerouslySetInnerHTML`로 LLM/사용자 출력을 렌더하는 백엔드 경로 미발견(프론트 전수는 본 감사 범위 외).

### 🟢 [LOW] L1 — iron_trading 완전 무인증 공개 API

- **위치**: `integrations/iron_trading/views.py:25-26` (`DailyContextView`, `permission_classes=[AllowAny]` + `authentication_classes=[]`)
- 외부 봇용 read-only 일별 컨텍스트 API. 의도된 설계이나 **인증·API 키·throttle 전무**. 누구나 시장 컨텍스트 데이터를 무제한 수집 가능.
- **심각도**: LOW (read-only, 데이터 민감도 낮음). 권장: API 키 헤더 또는 익명 throttle 적용.

---

## 6. 부가 발견 — 전역 Throttle 미적용

### 🟡 [MED] M2 — DEFAULT_THROTTLE_CLASSES 미설정

- **심각도**: MEDIUM / **신뢰도**: 9/10 / **상태**: VERIFIED
- **위치**: `config/settings.py:355-374` REST_FRAMEWORK
- `DEFAULT_THROTTLE_RATES`(user 60/min, anon 20/min, market_pulse_llm 5/min 등)는 **정의**되어 있으나, 이를 적용할 **`DEFAULT_THROTTLE_CLASSES`가 없다**. DRF는 throttle 클래스가 지정된 뷰에만 rate를 적용하므로, 전역 throttle은 **사실상 비활성**.
- throttle을 명시한 뷰는 watchlist(8) / market_pulse(4) / stocks sync(1) / chainsight watchlist(1)뿐. **serverless의 무인증 LLM/sync 엔드포인트(H1)는 throttle_classes 없음** → 무제한 호출 가능.
- **영향**: H1의 비용 증폭 위험을 직접 증폭. anon 20/min 한도가 정의돼 있어도 적용되지 않으므로 무의미.
- **권장**:
```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
],
```
추가 + LLM 엔드포인트엔 scoped throttle(`market_pulse_llm` 패턴) 적용.

---

## 7. STRIDE 요약 (주요 컴포넌트)

| 컴포넌트 | 주요 위협 | 현황 |
|----------|----------|------|
| JWT 인증 | Spoofing | HS256 + 서명키 분리 + refresh rotation + blacklist. 양호 |
| serverless LLM/sync API | Elevation of Privilege / 자원 남용 | **H1/M2 — 무인증 + throttle 부재** |
| 스크리너 프리셋 | Tampering | **M1 — 익명 변경 가능** |
| admin 대시보드 | Information Disclosure | IsAdminUser 적용. 양호 (L2 예외 메시지만 경미) |
| LLM 프롬프트 경로 | Tampering (injection) | system/user 분리 + escape. 양호 (M3 경미) |
| 외부 봇 API | Information Disclosure | **L1 — 무인증 공개** |

---

## 8. 권장 조치 우선순위

| 순위 | 항목 | 조치 | 노력 |
|------|------|------|------|
| 1 | **H1** | serverless 6개 엔드포인트 인증 추가 (sync 4 → IsAdminUser, LLM 2 → IsAuthenticated + throttle) | 낮음 (데코레이터 교체) |
| 2 | **M2** | `DEFAULT_THROTTLE_CLASSES` 추가 + LLM scoped throttle | 낮음 |
| 3 | **M1** | 프리셋 생성/수정/삭제 `IsAuthenticated` 강제 | 낮음 |
| 4 | **M3** | thesis_builder 자유입력 structured output + 제어문자 필터 | 중간 |
| 5 | **L1/L2/L3** | iron_trading throttle, 예외 메시지 표준화, 이메일 env화 | 낮음 |

> 1~3번은 audit P0 #6의 **미완 항목 마무리** 성격으로, 동일 패턴(`# audit P0 #6` 데코레이터)을 누락된 엔드포인트에 확장하면 된다.

---

## 9. 긍정적 발견 (INFO — 유지 권장)

- ✅ secure-by-default 권한 모델 (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated`)
- ✅ DEBUG/SECRET_KEY/NEO4J 운영 배포 가드 (오설정 시 부팅 차단)
- ✅ JWT 서명키 SECRET_KEY 분리, refresh rotation + blacklist
- ✅ CORS 화이트리스트 + `CORS_ALLOW_ALL` DEBUG 비의존
- ✅ `.env` gitignore, git 히스토리 실 키 미발견
- ✅ `cursor.execute` 4곳 전부 정적/파라미터 바인딩 (SQL 인젝션 없음)
- ✅ LLM 신뢰경계 escape (`llm_service.py`) + system/user prompt 분리
- ✅ admin·sync 트리거 대부분 `IsAdminUser` (audit P0 #6 적용분)
- ✅ 표준 EXCEPTION_HANDLER 응답 envelope

---

## 부록 — 감사 메타데이터

- **검사한 뷰 파일**: validation, chain_sight, macro, news, rag_analysis, serverless(+admin), sec_pipeline, iron_trading, users(+jwt), stocks(views/fundamentals/screener/exchange/market_movers/indicators/eod/mvp/search), portfolio, market_pulse
- **cursor.execute 검사**: 4/4 전수
- **AllowAny 검사**: serverless(50+) / macro(8) / users(공개 3) / news(2) / iron_trading(1) / market_movers(1) 전수 분류
- **Gemini 호출 LLM 인젝션 검사**: thesis_builder, conversation_views, keyword_extractor, llm_service, entity_extractor, adaptive_llm_service, prompt_builder
- **git 히스토리**: `-G` 시크릿 패턴 스캔 (실 키 0건)

---
*본 보고서는 /cso(Chief Security Officer) 워크플로 기반 읽기 전용 감사로 생성되었으며, 어떤 소스 코드도 수정하지 않았습니다.*
