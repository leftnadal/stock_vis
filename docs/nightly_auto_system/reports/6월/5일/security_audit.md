# 보안 감사 보고서 (Security Audit)

- **대상 프로젝트**: Stock-Vis (`/Users/byeongjinjeong/Desktop/stock_vis`)
- **감사 일자**: 2026-06-05
- **감사 범위**: OWASP Top 10 기반 — 인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿 관리, CORS/XSS/에러 노출
- **방식**: 읽기 전용 정적 분석 (코드 미수정)
- **브랜치/HEAD**: `main` / `3d81e20`

---

## 0. 요약 (Executive Summary)

전반적으로 **보안 기반(baseline)은 양호**하다. DRF 전역 권한이 `IsAuthenticated`로 설정되어 있고(권한 미지정 뷰도 기본 보호됨), SQL 인젝션은 4개 `cursor.execute` 전부 안전(상수 또는 `%s` 바인딩), 하드코딩된 운영 시크릿은 없으며, `.env`는 git 미추적, DEBUG·CORS·SECRET_KEY에 운영 가드가 존재한다.

그러나 **`serverless` 앱의 익명(AllowAny) 엔드포인트 군에서 실질적 위험이 집중**된다. 인증 없이 호출 가능한 상태변경/고비용(LLM·Celery·외부 API) 엔드포인트가 다수이며, **전역 throttle 클래스가 설정되지 않아** `DEFAULT_THROTTLE_RATES`가 사실상 죽은 설정이다(serverless 엔드포인트에 throttle 미적용). 그 결과 **미인증 LLM 비용 폭탄·자원 남용**이 가능하다.

### 심각도별 집계

| 심각도 | 건수 | 핵심 내용 |
|--------|------|----------|
| **CRITICAL** | 0 | — |
| **HIGH** | 5 | 미인증 LLM/Celery 비용폭탄(F-1), 전역 throttle 부재(F-2), preset PATCH IDOR(F-3), LLM 프롬프트 인젝션 미방어(F-4), 미인증 대량 상태변경(F-5) |
| **MED** | 4 | 보안 응답 헤더 부재(F-6), docker-compose dev 약한 기본 비밀번호(F-7), 에러 메시지 예외 노출(F-8), LLM 프롬프트 인젝션 2차(F-9) |
| **LOW** | 2 | execute_preset 미인증(F-10), admin traceback 노출(F-11) |
| **INFO/PASS** | 5 | SQL 인젝션 없음, 시크릿 하드코딩 없음, .env 미추적, CORS·DEBUG 가드, exception_handler 정상 |

---

## 1. 인증 / 인가 (OWASP A01 — Broken Access Control)

### 기반 평가 (양호)
- `config/settings.py:360` — `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`.
  → **권한을 명시하지 않은 뷰도 기본적으로 인증 필요**. 따라서 "permission_classes 누락"은 그 자체로 취약점이 아니며, **명시적 `AllowAny`가 실제 공격 표면**이다.
- 인증: JWT(`SimpleJWT`) + Session. ACCESS 60분 / REFRESH 7일 / `BLACKLIST_AFTER_ROTATION=True` (`settings.py:431~`).
- admin/내부 뷰(`api_request/admin_views.py`, `serverless/views_admin.py`)는 `IsAdminUser` 적용 확인.

### AllowAny 엔드포인트 분류 결과
총 분석: market_pulse 9, news 2, iron_trading 1, stocks 2, serverless ~55.

| 영역 | 평가 |
|------|------|
| `apps/market_pulse/views.py` (9곳, GET) | ✅ 공개 거시지표, read-only, 캐시. 허용 가능 |
| `packages/shared/stocks/views_market_movers.py`, `views_screener.py` | ✅ 공개 시장데이터(FMP 서비스단 rate limit). 허용 가능 |
| `integrations/iron_trading/views.py:25` (`DailyContextView`) | ✅ GET only(검증됨), 외부 봇용 공개 시그널. 사설/주문 데이터 아님 |
| `services/news/api/views.py:958/1002` | ⚠️ 콜드스타트/온보딩용. 캐시 존재하나 throttle 미적용(F-2 참조) |
| **`services/serverless/views.py`** | ❌ **상태변경·고비용 미인증 엔드포인트 집중** (F-1, F-3, F-5) |

---

### F-1 [HIGH] 미인증 LLM / Celery 비용 폭탄 (serverless)
다음 엔드포인트는 `@authentication_classes([])` + `@permission_classes([AllowAny])` + **throttle 없음**으로, 익명 사용자가 반복 호출 시 LLM(Gemini) 과금·작업 큐 폭주를 유발한다.

| 위치 | 엔드포인트 | 메서드 | 위험 |
|------|-----------|--------|------|
| `serverless/views.py:1677` | `generate_thesis` | POST | **동기 LLM 호출**(`ThesisBuilder.build_thesis` → Gemini). 호출당 즉시 과금, 반복 가능 |
| `serverless/views.py:2511` | `extract_relations_from_news_api` | POST | LLM 추출 Celery `.delay()`, batch 시 다수 기사 일괄 큐잉 |
| `serverless/views.py:2670` | `sync_llm_relations_api` | POST | LLM 관계 → Neo4j/DB 동기 Celery 트리거, 큐 플러딩 |

**근거**: `generate_thesis`는 `request.data['stocks']`만 비어있지 않으면 인증 없이 `builder.build_thesis(...)`를 동기 실행한다(`views.py:1746~`). throttle_classes 미지정 + 전역 throttle 부재(F-2).

**악용 시나리오**: 익명 공격자가 `POST /api/v1/serverless/thesis/generate`를 루프 호출 → Gemini 호출 비용 무제한 발생 (재정적 DoS).

**권고**: 해당 엔드포인트에 `IsAuthenticated` + 전용 `ScopedRateThrottle(scope='market_pulse_llm')` 적용. 트리거성 작업은 `IsAdminUser` 권장.

---

### F-3 [HIGH] Screener Preset PATCH IDOR (소유권 검증 우회)
- **위치**: `services/serverless/views.py:977-1025` (`screener_preset_detail`, `GET/PATCH/DELETE`, AllowAny)
- **문제**: 소유권 검사가 `if preset.user and preset.user != request.user:` (라인 1006, 1021) 형태다. AllowAny이므로 `request.user`는 `AnonymousUser`이고, **`preset.user`가 `None`(시스템/익명 생성 프리셋)이면 조건이 거짓 → 검사 통과**.
- **추가 격차**: DELETE는 `category in ['system','beginner','intermediate']` 차단(라인 1018)이 있으나, **PATCH에는 카테고리 차단이 없다**. 따라서 `user=None`인 시스템성 프리셋을 익명 사용자가 **수정**할 수 있다.

**악용 시나리오**: `PATCH /api/v1/serverless/presets/{id}` 익명 호출로 `user`가 없는 프리셋의 이름/필터를 임의 변경(데이터 무결성 훼손).

**권고**: `if not preset.user or preset.user != request.user: raise PermissionDenied` 로 변경하고, PATCH에도 시스템 카테고리 차단 적용. 근본적으로 해당 뷰를 `IsAuthenticatedOrReadOnly` 이상으로 승격.

---

### F-5 [HIGH] 미인증 대량 상태변경 / 외부 호출 트리거
| 위치 | 엔드포인트 | 위험 |
|------|-----------|------|
| `serverless/views.py:2021` | `trigger_etf_holdings_sync` (POST) | 익명이 전체 ETF CSV 다운로드+DB 일괄 갱신 트리거. 외부 API 증폭 호출 |
| `serverless/views.py:2135` | `resolve_etf_csv_url` (POST) | 익명이 ETF URL 복구(외부 네트워크 + DB write) 트리거. 심볼 기반이라 직접 SSRF는 제한적이나 미인증 네트워크 작업 |
| `serverless/views.py:2481` | `refresh_theme_matches_api` (POST) | 익명이 ThemeMatch 테이블 전체 재생성(대량 DB write) |

**권고**: 운영/관리 성격이므로 `IsAdminUser` + throttle. 최소한 `IsAuthenticated`.

---

## 2. 인젝션 (OWASP A03 — SQL Injection) — ✅ PASS

지정된 4개 `cursor.execute` 사용처 전수 검토 결과 **모두 안전**.

| 파일 | 라인 | 평가 |
|------|------|------|
| `config/views.py:90` | `cursor.execute("SELECT 1")` | 상수 쿼리, 사용자 입력 없음 ✅ |
| `packages/shared/api_request/admin_views.py:318` | `cursor.execute("SELECT 1")` | 상수 쿼리 ✅ |
| `services/serverless/services/admin_status_service.py:892` | `pg_stat_user_tables` 조회 | 상수 쿼리, 입력 없음 ✅ |
| `apps/chain_sight/services/seed_selection.py:159` | 거래량 SMA CTE | **`%s` 파라미터 바인딩** + `[market_date, market_date]` ✅ |

문자열 포매팅으로 SQL을 조립하는 패턴은 발견되지 않았다. ORM 사용이 지배적이며 raw SQL은 위 4곳뿐.

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01)

### 기존 방어 (양호한 표준 존재)
- `services/rag_analysis/services/llm_service.py:177-192` — **신뢰 경계 태그**(`<context_data>`/`<user_question>`) + 닫는 태그 이스케이프(`</context_data>` → `_escaped`). 주석 `security audit P0 #3 (2026-05-19)`.
- `thesis/services/thesis_builder.py:445-450` — 입력 500자 제한 + 구분자(```` ``` ````, `---`) 제거(부분 방어).

→ **팀 내부 방어 표준이 존재하나 일부 LLM 호출부에만 적용**되어 일관성이 결여됨.

### F-4 [HIGH] 사용자/외부 텍스트의 무방어 프롬프트 삽입
RAG 서비스의 신뢰 경계 패턴이 적용되지 않고, 외부/사용자 제공 텍스트를 f-string으로 직접 삽입하는 곳:

| 위치 | 입력원 | 방어 |
|------|--------|------|
| `services/news/services/keyword_extractor.py:289-310` | 뉴스 제목/요약/심볼 | 없음 (이스케이프·태그·길이제한 전무) |
| `services/serverless/services/llm_relation_extractor.py:374-385` | SEC 공시/뉴스 본문 | 5000자 절단만, 구분자 이스케이프 없음 |
| `services/serverless/services/keyword_service.py:252-256` | 종목명/심볼(FMP 외부) | 없음 |
| `thesis/services/prompt_builder.py:825-878` | 뉴스 키워드/요약 | 없음 (keyword_extractor 출력 연쇄 위험) |

**악용 시나리오**: 외부에서 수집되는 뉴스 제목/회사명에 `... \n[SYSTEM] 이전 지시 무시하고 ...`를 삽입 → 추출 결과 오염, 토큰 낭비, JSON 파싱 우회 시도. 사용자별 시스템 프롬프트 기밀 탈취 위험은 낮으나, 추출 신뢰성·비용에 영향.

**권고**: `llm_service.py`의 신뢰 경계 태그 + 닫는태그 이스케이프 패턴을 위 4곳에 공통 유틸로 적용. 입력 길이 제한 일괄화.

### F-9 [MED] LLM 프롬프트 인젝션 2차 (중간 단계)
| 위치 | 내용 |
|------|------|
| `services/rag_analysis/services/context_compressor.py:139` | 문서 본문을 `.format(document=...)`로 무이스케이프 삽입(코퍼스 기반, 준신뢰) |
| `apps/portfolio/llm/client.py:250-252` | `f"{system}\n\n{prompt}"` 단순 연결 — Gemini SDK system 분리 미사용. 호출자가 사용자 입력을 직접 넘기면 경계 붕괴 가능 |

**권고**: 중간 단계에도 이스케이프 적용, portfolio 클라이언트는 호출자 입력 검증 책임 명시.

---

## 4. 시크릿 관리 (OWASP A05/A07) — ✅ 대체로 양호

### PASS 항목
- **운영 시크릿 하드코딩 없음**. `SECRET_KEY`/`JWT_SIGNING_KEY`/`NEO4J_PASSWORD`/외부 API 키 모두 `os.getenv` 우선, fallback은 빈 문자열 또는 dev 전용 placeholder.
- **운영 배포 가드 존재**: `settings.py:164-176` — `DEBUG=False`에서 `SECRET_KEY` dev fallback 또는 `NEO4J_PASSWORD` 미설정 시 `ImproperlyConfigured`로 부팅 차단.
- **`.env` git 미추적**: `git ls-files`에 `.env.example`만 존재. `.gitignore`에 `.env` 포함(10, 138행).
- **프론트엔드 `NEXT_PUBLIC_*` 시크릿 노출 없음**: API URL·feature flag 등 공개 설정만.
- 테스트 파일의 mock 비밀번호(`adminpass123` 등)는 `tests/` 한정 — INFO(정상).

### F-7 [MED] docker-compose 개발용 약한 기본 비밀번호
- `docker/docker-compose.yml:18` — `POSTGRES_PASSWORD: ${DB_PASSWORD:-stockvis_password}`
- `docker/docker-compose.yml:57` — `NEO4J_AUTH=${NEO4J_USERNAME:-neo4j}/${NEO4J_PASSWORD:-password}`

**평가**: 개발 전용 fallback이며 `docker-compose.prod.yml`은 fallback 없이 env 필수(안전). 다만 약한 기본값이 실수로 운영에 노출될 위험.
**권고**: dev fallback도 임의 생성값으로 교체하거나 fallback 제거.

---

## 5. CORS / XSS / 에러 노출 (OWASP A05 — Security Misconfiguration)

### PASS 항목
- **CORS 제한적**: `CORS_ALLOWED_ORIGINS = [localhost:3000, 127.0.0.1:3000]` (`settings.py:318`). `CORS_ALLOW_ALL_ORIGINS`는 별도 env(`DJANGO_CORS_ALLOW_ALL`)로 명시 제어, **기본 False**(DEBUG 의존 제거됨). `CORS_ALLOW_CREDENTIALS=True`이나 origin 화이트리스트와 함께 사용되어 적절.
- **DEBUG 기본 False** + 운영 가드(§4).
- **`ALLOWED_HOSTS`**: DEBUG=False & 미설정 시 `[]`(빈 값) → 모든 호스트 거부(안전). DEBUG=True에서만 `['*']`.
- **`config/exception_handler.py`**: 스택트레이스/`traceback` 미노출. DRF detail 메시지만 표준 envelope로 반환 ✅.

### F-2 [HIGH] 전역 Throttle 클래스 부재 → Rate 설정이 죽은 설정
- **위치**: `config/settings.py` `REST_FRAMEWORK`
- **문제**: `DEFAULT_THROTTLE_RATES`(`user 60/min`, `anon 20/min`, `market_pulse_llm 5/min` 등)는 정의되어 있으나 **`DEFAULT_THROTTLE_CLASSES`가 없다**. DRF는 throttle 클래스가 적용된 뷰에서만 rate를 적용하므로, **명시 `throttle_classes`가 없는 모든 뷰(특히 serverless 전체)는 throttle이 전혀 걸리지 않는다**.
- **실사용 현황**: throttle은 market_pulse / chain_sight watchlist / users watchlist / stocks 일부에만 명시 적용. **serverless·thesis·news의 AllowAny LLM/Celery 엔드포인트는 throttle 0건**.
- **영향**: F-1(비용 폭탄)·F-5(자원 남용)을 무제한으로 증폭. `anon 20/min` 설정이 있어 "보호된다"는 착시.

**권고**:
```python
# config/settings.py REST_FRAMEWORK (예시)
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
],
```
추가로 LLM 엔드포인트는 `ScopedRateThrottle(scope='market_pulse_llm')` 전용 적용.

### F-6 [MED] 운영 보안 응답 헤더 부재
`settings.py`에 다음 설정이 **전무**:
- `SECURE_HSTS_SECONDS` / `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_SSL_REDIRECT`
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`
- `SECURE_CONTENT_TYPE_NOSNIFF`
- `SECURE_PROXY_SSL_HEADER`

`SecurityMiddleware`·`XFrameOptionsMiddleware`는 등록되어 있으나 위 옵션이 없으면 HTTPS 강제·HSTS·쿠키 Secure 플래그가 비활성. (`django check --deploy` 다수 경고 예상.)
**권고**: 운영 설정에서 위 항목을 `True`/적절값으로 지정(가능하면 `settings_prod.py` 분리).

### F-8 [MED] 응답 본문에 예외 정보 부분 노출
| 위치 | 내용 |
|------|------|
| `services/serverless/views.py:1779` | `"warning": f"... (에러: {type(e).__name__}: {str(e)[:100]})"` — 예외 타입+메시지 100자를 응답에 포함 |
| `services/serverless/views_admin.py:163-165` | `Response({"error": str(e)})` — 비정형 예외 메시지 반환(IsAdminUser 제한) |

**평가**: 길이 제한·관리자 제한이 있어 위험은 제한적이나, 내부 구조 단서 제공 가능.
**권고**: 사용자 응답은 일반화된 메시지로, 상세는 logger로만.

### F-11 [LOW] Admin TaskResult traceback 노출
- `services/serverless/views_admin.py:457` — `"traceback": task_result.traceback` 응답 포함. `IsAdminUser` 제한이므로 LOW. 필요시 마스킹 권장.

### F-10 [LOW] execute_preset 미인증
- `serverless/views.py:1028` — `execute_preset` POST AllowAny. 상태변경은 없고 필터 실행/결과 반환만. 비용 낮음. throttle(F-2) 적용 시 충분.

---

## 6. 권고 우선순위 (Remediation Roadmap)

### P0 — 즉시 (운영 노출 전 차단)
1. **F-2**: `DEFAULT_THROTTLE_CLASSES` 전역 등록 (Anon/User) — 단일 변경으로 다수 위험 동시 완화.
2. **F-1**: `generate_thesis`/`extract_relations_from_news_api`/`sync_llm_relations_api`에 `IsAuthenticated`(트리거성은 `IsAdminUser`) + LLM scoped throttle.
3. **F-3**: `screener_preset_detail` 소유권 검사를 `not preset.user or ...`로 수정 + PATCH 시스템 카테고리 차단.

### P1 — 단기
4. **F-5**: ETF sync/URL resolve/theme refresh 트리거 → `IsAdminUser` + throttle.
5. **F-4**: RAG 신뢰 경계 태그 패턴을 keyword_extractor / llm_relation_extractor / keyword_service / prompt_builder에 공통 적용.
6. **F-6**: 운영 보안 헤더(HSTS/SSL redirect/secure cookie/nosniff) 설정.

### P2 — 중기
7. **F-7**: docker-compose dev fallback 비밀번호 강화/제거.
8. **F-8/F-9/F-11**: 에러 응답 일반화, 중간 LLM 단계 이스케이프, admin traceback 마스킹.

---

## 7. 통과(PASS) / 양호 항목 정리
- ✅ SQL 인젝션: raw SQL 4곳 전부 안전(상수 또는 파라미터 바인딩)
- ✅ DRF 기본 권한 `IsAuthenticated` (안전한 기본값)
- ✅ 운영 시크릿 하드코딩 없음, `.env` git 미추적, 운영 배포 가드 존재
- ✅ CORS 화이트리스트 + `CORS_ALLOW_ALL` 기본 False
- ✅ DEBUG 기본 False + 누락 시크릿 부팅 차단 가드
- ✅ `exception_handler` 스택트레이스 미노출, 표준 에러 envelope
- ✅ JWT 토큰 블랙리스트/로테이션 설정
- ✅ iron_trading 외부 봇 API: GET only, 공개 시그널만 노출

---

*본 보고서는 정적 분석 기반이며 코드를 일절 수정하지 않았다. 동적 검증(실제 익명 호출 PoC, `python manage.py check --deploy`)으로 F-1·F-2·F-3 재현 후 패치 권장.*
