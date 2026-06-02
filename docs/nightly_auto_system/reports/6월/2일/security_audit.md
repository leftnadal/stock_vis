# 보안 감사 보고서 — Stock-Vis

- **작성일**: 2026-06-02
- **유형**: 읽기 전용 보안 감사 (OWASP Top 10 기반)
- **범위**: 인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿 관리, CORS/XSS/에러 노출
- **방법**: 정적 코드 분석 (코드 수정 없음)
- **브랜치**: main

---

## 요약 (Executive Summary)

전반적으로 **보안 기본기가 잘 갖춰진 상태**입니다. 과거 audit P0 트랙(#5/#6/#14 등)의 영향으로 DRF 기본 권한이 `IsAuthenticated`로 잠겨 있고, SQL은 전부 파라미터 바인딩, 시크릿은 환경변수로 분리되어 있으며 운영 배포 가드까지 존재합니다.

다만 다음 영역에서 보강이 필요합니다.

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| CRITICAL | 0 | — |
| HIGH | 1 | serverless 스크리너 프리셋 미인증 수정/삭제 (접근통제 우회) |
| MED | 4 | 운영 보안 헤더 부재 / 미인증 LLM·비용 트리거 / thesis 프롬프트 인젝션 / 뉴스 간접 프롬프트 인젝션 |
| LOW | 5 | ReadOnly 공개 GET / SSRF 표면 / 예외 메시지 노출 / `authentication_classes([])` 부작용 / iron_trading 공개 뷰 |
| INFO | — | 양호 항목 다수 (아래 §7) |

---

## 1. 인증 / 인가 (OWASP A01: Broken Access Control)

### 1.1 DRF 전역 기본 권한 — 양호 ✅

`config/settings.py:360`
```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
```
- 과거 `IsAuthenticatedOrReadOnly` → `IsAuthenticated`로 강화됨 (audit P0 #5).
- 따라서 **`permission_classes`를 명시하지 않은 뷰는 자동으로 인증 요구**됩니다.
- 명시 누락이지만 기본값으로 보호되는 뷰(정상): `stocks/views_eod.py`, `views_indicators.py`, `views_search.py`, `views_mvp.py`, `chain_sight/api/views.py`(7개 뷰), `validation/api/views.py`(Summary/Metrics/Leader/Preset/LLMPeerFilter) 등.
  - ⚠️ 권고: 이들은 **전역 기본값에 암묵적으로 의존**합니다. 향후 누군가 전역 기본값을 완화하면 일괄 노출됩니다. 민감 뷰는 `permission_classes`를 명시하는 것이 안전합니다 (방어적 이중화).

### 1.2 [HIGH] serverless 스크리너 프리셋 — 미인증 수정/삭제 접근통제 우회

**파일**: `services/serverless/views.py:977` `screener_preset_detail` (GET/PATCH/DELETE), `:918` `screener_presets_api` (GET/POST), `:1028` `execute_preset`

```python
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def screener_preset_detail(request, preset_id):
    ...
    elif request.method == "DELETE":
        if preset.category in ["system", "beginner", "intermediate"]:
            raise PermissionDenied("Cannot delete system presets")
        if preset.user and preset.user != request.user:   # ← preset.user 가 None 이면 통과
            raise PermissionDenied("You can only delete your own presets")
        preset.delete()
```

**문제**:
1. `AllowAny` + 소유권 체크가 `if preset.user and ...` 형태 → **`preset.user`가 `None`(소유자 없음)인 프리셋은 누구나(미인증 포함) PATCH/DELETE 가능**.
2. `screener_presets_api`(POST)도 `@authentication_classes([])` + `AllowAny`라 **미인증 사용자가 프리셋을 생성**할 수 있고, 이때 생성되는 프리셋은 `user=None`이 되어 위 우회의 표적이 됩니다.
3. `GET`/`execute_preset` 호출 시 임의의 `preset_id`로 `use_count`/`last_used_at`을 무제한 증가시킬 수 있음(데이터 무결성/순위 조작).

**영향**: 미인증 공격자가 다른 사용자의 비소유(공개/익명) 프리셋을 임의 삭제·변조. OWASP A01.

**권고**:
- 해당 엔드포인트를 `IsAuthenticated`로 전환하고, 생성 시 `user=request.user`를 강제.
- 소유권 체크를 `if preset.user is None or preset.user != request.user: raise PermissionDenied`로 변경(소유자 없는 객체는 변경 금지).
- 공개 읽기가 필요하면 GET만 `AllowAny`, 쓰기(PATCH/DELETE/POST)는 인증 필수로 메서드별 분리.

### 1.3 [LOW] `IsAuthenticatedOrReadOnly` — 익명 GET 허용

- `packages/shared/stocks/views.py:521` `StockOverviewAPIView`
- `services/validation/api/views.py:575` `PeerPreferenceView`

익명 사용자가 GET 가능. 종목 개요/peer 설정 읽기로 민감도는 낮으나, 전역 정책(`IsAuthenticated`)과 불일치. 의도된 공개라면 주석으로 명시 권장.

### 1.4 [LOW] iron_trading 공개 뷰

`integrations/iron_trading/views.py:19` `DailyContextView` → `AllowAny`. 공개 데일리 컨텍스트 제공 목적으로 보이나, 노출 데이터 범위 재확인 권장.

### 1.5 관리자 트리거 — 양호 ✅

데이터 동기화/키워드 생성/heatmap·breadth sync, SEC fetch, 관리 액션은 모두 `IsAdminUser` 적용됨 (audit P0 #6):
- `services/serverless/views.py` `trigger_sync`/`sync_now`/`trigger_keyword_generation`/`generate_screener_keywords`/`trigger_breadth_sync`/`trigger_heatmap_sync`/`institutional_sync_api`
- `services/serverless/views_admin.py` 전체 (Admin* 12개 뷰)
- `services/sec_pipeline/views.py` `FilingDataView`
- `apps/market_pulse/views.py` `DataSyncView`
- `packages/shared/api_request/admin_views.py` Provider/RateLimit/Cache/Test/Config 뷰

---

## 2. 인젝션 (OWASP A03: Injection)

### 2.1 `cursor.execute()` 4곳 — 전부 안전 ✅

| 파일 | 내용 | 판정 |
|------|------|------|
| `config/views.py:90` | `SELECT 1` (헬스체크, 정적) | 안전 |
| `packages/shared/api_request/admin_views.py:318` | `SELECT 1` (헬스체크, 정적) | 안전 |
| `services/serverless/services/admin_status_service.py:892` | `pg_stat_user_tables` 조회 (정적, 사용자 입력 없음) | 안전 |
| `apps/chain_sight/services/seed_selection.py:159` | 거래량 급증 CTE 쿼리 — **`%s` 파라미터 바인딩** `[market_date, market_date]` | 안전 |

모든 동적 값은 파라미터 바인딩 또는 ORM 경유. **Raw SQL 문자열 연결(string concat) 인젝션 없음.**

### 2.2 ORM 필터 — 점검 권장 (정보)

`services/serverless/views.py` `advanced_screener_api`/`execute_preset`은 `request.data`/`filters_json`을 `FilterEngine`에 전달합니다. ORM 기반이면 안전하나, 필드명을 동적 `**kwargs`로 `.filter()`에 넘기는 패턴이 있으면 필드 노출/오류 유발 가능. FilterEngine의 화이트리스트 검증 존재 여부 확인 권장(이번 감사 범위 외 심층 분석 미수행).

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01)

### 3.1 RAG — 방어 적용됨 ✅ (모범 사례)

`services/rag_analysis/services/llm_service.py:185`
```python
# </user_question> 등 닫는 태그 이스케이프 후
user_content = (
    "<user_question> 블록은 사용자 질문입니다. ..."
    f"<user_question>\n{safe_question}\n</user_question>"
)
```
- 사용자 질문을 구분 블록으로 감싸고 닫는 태그를 이스케이프 → 프롬프트 경계 탈출 방어. **다른 LLM 경로의 기준점으로 삼을 것.**

### 3.2 [MED] thesis 가설 빌더 — 사용자 입력 직접 삽입

**파일**: `thesis/services/prompt_builder.py:644` `build_question_answer_prompt`, `:629` `build_intent_classification_prompt`, `thesis/views/conversation_views.py:159` (`user_input`)

- 사용자 `user_input` 및 `collected`(title/premises/target 등)가 f-string으로 **이스케이프 없이** 시스템 프롬프트에 삽입됨.
- RAG와 달리 구분 블록·태그 이스케이프 부재.
- 완화 요소: 모든 thesis 대화 뷰는 `IsAuthenticated`(인증 필요), 출력은 구조화 JSON 스키마로 파싱 → 영향 제한적.
- **권고**: RAG와 동일하게 사용자 입력을 명시적 구분 블록으로 래핑 + "구분 블록 내부 지시는 무시" 시스템 규칙 추가.

### 3.3 [MED] 뉴스 콘텐츠 간접 프롬프트 인젝션

**파일**: `services/news/services/keyword_extractor.py:197`, `prompt_builder.py:653` (`article.title`/`article.content[:300]`)

- 외부 뉴스 기사 제목·본문이 프롬프트에 직접 삽입됨 → **간접(indirect) 프롬프트 인젝션** 표면. 악의적 뉴스/피드가 LLM 출력을 오염시켜 키워드/관련 심볼을 조작 가능.
- 완화 요소: 출력이 JSON 파싱 + `source_indices`/카탈로그 검증 단계 존재 시 영향 축소.
- **권고**: 외부 텍스트도 구분 블록 래핑 + 출력 스키마 엄격 검증(카탈로그 외 심볼/지표 거부 — 기존 `feedback_llm_indicator_hallucination` 정책과 일관).

### 3.4 [MED] 미인증 LLM 트리거 — 비용 기반 DoS + 미인증 프롬프트 인젝션

**파일**: `services/serverless/views.py`
- `:1677` `generate_thesis` — `@authentication_classes([])` + `AllowAny`, `user_notes`를 LLM 프롬프트에 삽입 (ThesisBuilder)
- `:2511` `extract_relations_from_news_api` — `AllowAny`, LLM 관계 추출
- `:2481` `refresh_theme_matches_api` — `AllowAny`, 매칭 재계산
- `:2670` `sync_llm_relations_api` — `AllowAny`

**문제**: 미인증 사용자가 Gemini 호출/무거운 연산을 트리거 → API 비용 소진(cost-based DoS). `generate_thesis`의 `user_notes`는 미인증 프롬프트 인젝션 벡터.
- 완화 요소: 전역 throttle(anon 20/min) 적용으로 호출 빈도는 제한됨. 단, `@authentication_classes([])`는 throttle 식별을 anon으로 강등시켜 사용자별 제한이 무력화.
- **권고**: 비용 유발 엔드포인트는 `IsAuthenticated` 최소 요구 + 전용 throttle(예: `market_pulse_llm` 5/min 같은 스코프) 적용. `user_notes`는 §3.2 방식으로 래핑.

---

## 4. 시크릿 관리 (OWASP A05/A07)

### 4.1 양호 ✅

- **하드코딩된 API 키/비밀번호 없음** (코드 스캔 결과 무매치). 모든 키는 `os.getenv()` 경유:
  `FMP/FINNHUB/MARKETAUX/FRED/ANTHROPIC/GEMINI_API_KEY`, `SECRET_KEY`, `JWT_SIGNING_KEY`, `DB_PASSWORD`, `NEO4J_PASSWORD` 등.
- `.env`는 `.gitignore`에 등록됨(`.gitignore:10, 138`), `git ls-files` 추적 대상은 `.env.example`만.
- **SECRET_KEY / JWT_SIGNING_KEY 분리** (`settings.py:151,154`) — 토큰 위조 공격 표면 축소 (모범).
- **운영 배포 가드** (`settings.py:164~`): `DEBUG=False`인데 `SECRET_KEY`가 dev fallback이거나 `NEO4J_PASSWORD` 미설정이면 즉시 `RuntimeError` → 안전하지 않은 기본값으로 운영 기동 차단.

### 4.2 [INFO] dev fallback SECRET_KEY 상수

`settings.py:149` `_SECRET_KEY_DEV_FALLBACK = 'django-insecure-...'` — 개발 전용이며 운영 가드로 차단됨. 정상이나, 로컬 `DEBUG=True` 환경에서는 고정 키 사용됨을 인지(로컬 한정 위험).

---

## 5. CORS / XSS / 에러 노출 (OWASP A05)

### 5.1 CORS — 양호 ✅

`config/settings.py:318`
- `CORS_ALLOWED_ORIGINS`: `localhost:3000`, `127.0.0.1:3000`만 (와일드카드 아님).
- `CORS_ALLOW_ALL_ORIGINS`: 기본 `False`, **DEBUG 의존 제거** 후 별도 env(`DJANGO_CORS_ALLOW_ALL`)로만 활성화 — 운영 실수 방지 (모범).
- `CORS_ALLOW_CREDENTIALS=True`이나 origin 화이트리스트가 좁아 위험 낮음.
- ⚠️ **운영 배포 시 실제 프론트엔드 도메인을 `CORS_ALLOWED_ORIGINS`/`ALLOWED_HOSTS`에 추가 필요** (현재 localhost 전용).

### 5.2 DEBUG — 양호 ✅

`settings.py:157` `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'` → **기본 False**. `ALLOWED_HOSTS`도 DEBUG=False에서 빈 값이면 빈 리스트(전체 차단), DEBUG=True에서만 `['*']`.

### 5.3 [MED] 운영 보안 헤더 / 쿠키 플래그 부재

`config/settings.py`에 다음 설정이 **전무**합니다:
- `SECURE_HSTS_SECONDS` / `SECURE_HSTS_INCLUDE_SUBDOMAINS` / `SECURE_HSTS_PRELOAD`
- `SECURE_SSL_REDIRECT`
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`
- `SECURE_PROXY_SSL_HEADER` (리버스 프록시 뒤 HTTPS 인식)
- `SECURE_CONTENT_TYPE_NOSNIFF` (명시 권장)

완화 요소: `SecurityMiddleware`, `XFrameOptionsMiddleware`(클릭재킹 — 기본 `DENY`) 미들웨어는 포함됨(`settings.py:222,229`). SessionAuthentication이 활성(`settings.py:358`)이라 세션 쿠키가 존재하므로 `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` 부재는 HTTPS 환경에서 쿠키 평문 전송 위험.

**권고**: `DEBUG=False`일 때 위 항목 일괄 활성화(`SECURE_SSL_REDIRECT=True`, HSTS 1년, 쿠키 Secure, NOSNIFF). 프록시 환경이면 `SECURE_PROXY_SSL_HEADER` 설정.

### 5.4 [LOW] 예외 메시지 노출 (`str(e)`)

응답 본문에 `str(e)`를 직접 반환하는 위치 다수:
- `packages/shared/api_request/admin_views.py` 다수(73/80/110/133/163/190/250/290) — **단, `IsAdminUser` 전용**이라 노출 대상 제한적.
- `packages/shared/stocks/views.py:1065`, `packages/shared/users/views.py:964` — 인증 사용자 대상, 부분 결과 에러 메시지.

내부 예외 메시지(드라이버/경로/스택 힌트)가 클라이언트로 누출될 수 있음. **권고**: 표준 에러 envelope(이미 정책 존재 — `docs/features/api_envelope/policy.md`)로 일반화 메시지 반환, 상세는 서버 로그에만 기록. (DEBUG=False면 Django 자체 스택트레이스는 미노출이므로 위험은 LOW.)

### 5.5 XSS — 정보

백엔드는 JSON API(DRF)로 응답 → 서버 측 반사형 XSS 표면 낮음. 실제 XSS 위험은 프론트엔드(Next.js) 렌더링 단계에 있으며 이번 백엔드 감사 범위 외. LLM 출력(키워드/요약)을 프론트에서 `dangerouslySetInnerHTML` 등으로 렌더하지 않는지 별도 확인 권장.

---

## 6. 기타 발견

### 6.1 [LOW] `@authentication_classes([])` 부작용

`screener_presets_api`(:918), `generate_thesis`(:1677), `resolve_etf_csv_url`(:2135)에 적용. 인증을 완전 비활성화하여 **유효한 JWT를 보내도 무시**됨(`request.user`는 항상 Anonymous). 결과:
- `screener_presets_api`의 "사용자 본인 프리셋 추가" 분기가 실행되지 않음(기능 결함).
- 사용자별 throttle 식별 불가 → anon throttle로 강등.
- §1.2/§3.4의 미인증 노출과 직접 연결.

### 6.2 [LOW] SSRF 표면 — `resolve_etf_csv_url`

`:2135` `AllowAny` + `CSVURLResolver`가 외부 URL을 탐색/요청. 입력은 `etf_symbol`(사전 정의 ETF 조회)로 보여 직접 URL 주입은 아니나, 미인증으로 외부 fetch를 트리거할 수 있음. resolver가 임의 URL을 따라가지 않는지(허용 도메인 화이트리스트) 확인 권장.

---

## 7. 양호 항목 (긍정적 발견) ✅

1. SQL 전 구간 파라미터 바인딩 — 인젝션 0건.
2. 시크릿 하드코딩 0건, `.env` gitignore 처리.
3. DRF 전역 기본 권한 `IsAuthenticated`로 강화.
4. 관리자 작업 전건 `IsAdminUser` 적용.
5. `SECRET_KEY`/`JWT_SIGNING_KEY` 분리 + 운영 배포 가드(RuntimeError).
6. RAG LLM 프롬프트 인젝션 방어(구분 블록 + 태그 이스케이프).
7. CORS 화이트리스트 + `CORS_ALLOW_ALL` 명시적 env 제어.
8. `DEBUG`/`ALLOWED_HOSTS` 안전한 기본값.
9. throttle 레이트(user/anon/llm 스코프) 구성.
10. SecurityMiddleware / XFrameOptionsMiddleware 포함.

---

## 8. 우선순위 권고 (조치 순서)

| 순위 | 심각도 | 항목 | 위치 |
|------|--------|------|------|
| 1 | HIGH | 스크리너 프리셋 쓰기 작업 인증 필수화 + 소유권 체크 `is None` 보강 | `serverless/views.py:918,977,1028` |
| 2 | MED | 미인증 LLM/비용 트리거 → `IsAuthenticated` + 전용 throttle | `serverless/views.py:1677,2481,2511,2670` |
| 3 | MED | 운영 보안 헤더/쿠키(HSTS·SSL_REDIRECT·COOKIE_SECURE·NOSNIFF) 추가 | `config/settings.py` |
| 4 | MED | thesis/뉴스 프롬프트 입력 RAG식 래핑·이스케이프 | `thesis/services/prompt_builder.py`, `news/.../keyword_extractor.py` |
| 5 | LOW | `@authentication_classes([])` 제거(인증 무시 부작용) | 위 3개 함수 |
| 6 | LOW | 예외 메시지 envelope 일반화 | `admin_views.py` 외 |
| 7 | LOW | `IsAuthenticatedOrReadOnly`/iron_trading 공개 GET 의도 재확인 | `stocks/views.py:521`, `validation/api/views.py:575`, `iron_trading/views.py:19` |
| — | 배포 | 운영 도메인 `CORS_ALLOWED_ORIGINS`/`ALLOWED_HOSTS` 등록 | `config/settings.py` |

---

## 부록: 검사 메타데이터

- **검사 대상 뷰 파일**: stocks(11), users(1), news(2), macro/market_pulse(1), rag_analysis(1), serverless(2), validation(2), chainsight(2), sec_pipeline(1), config/admin(2), iron_trading(1)
- **`cursor.execute()` 점검**: 4/4 (전부 안전)
- **Gemini 호출 파일 점검**: 핵심 경로 — RAG(방어 확인), thesis(builder/prompt_builder/conversation_views), news(keyword_extractor/news_deep_analyzer/stock_insights), serverless(thesis_builder/keyword/relation extractor)
- **시크릿 스캔 패턴**: `sk-*`, `AIza*`, `secret=`, `api_key=`, `password=` (env/example/test 제외) → 무매치
- **주의**: 본 보고서는 정적 분석 기반이며 런타임 검증(실제 요청 재현)은 수행하지 않음. HIGH/MED 항목은 실 환경 PoC로 재확인 권장.
