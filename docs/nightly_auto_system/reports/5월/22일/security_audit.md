# Stock-Vis 보안 감사 보고서

- **감사 일자**: 2026-05-22
- **감사 범위**: OWASP Top 10 기반 정적 코드 감사 (읽기 전용)
- **대상 브랜치**: `slice14` (HEAD `a353162`)
- **감사자**: 자동 감사 (claude opus 4.7)
- **권한**: 코드 수정 금지, 보고서 작성만 수행

---

## 0. 종합 의견

전반적으로 **방어 코드 품질이 양호**한 편이다. 직전 감사(P0 #5/#6)로 인해 DRF `DEFAULT_PERMISSION_CLASSES`가 `IsAuthenticated`로 상향되어 누락된 뷰도 기본 인증 보호를 받는다. SQL은 ORM 위주이고 raw 쿼리 4곳 모두 안전하다. LLM 프롬프트 인젝션 방어도 핵심 경로 3곳(`rag_analysis.llm_service`, `thesis.thesis_builder`, `thesis.indicator_matcher`)에 이미 적용돼 있다.

다만 **외부 데이터(뉴스 제목/요약)를 그대로 프롬프트에 끼워 넣는 LLM 호출 2곳**, **마이크로 서비스/거시 데이터의 무인증 노출에 따른 비용 노출**, 그리고 **명시적 `permission_classes` 누락(default 의존)** 패턴 일부가 잔존한다.

| 심각도 | 신규 발견 |
|--------|-----------|
| CRITICAL | 0 |
| HIGH | 1 |
| MED | 5 |
| LOW | 4 |
| INFO | 6 |

---

## 1. 인증 / 인가 (OWASP A01 / A07)

### 1.1 `DEFAULT_PERMISSION_CLASSES` 의존도

`config/settings.py:353-355`에서 default가 `IsAuthenticated`로 설정되어 있어, 명시 누락 뷰도 인증 강제가 자동 적용된다.

```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
```

**positive**: P0 #5 audit으로 안전한 default를 채택. AllowAny가 필요한 공개 뷰는 모두 명시되어 있음(예: `users.LogIn`, `users.PublicUser`, `serverless.views`의 시장 데이터 함수 뷰들).

### 1.2 명시적 `permission_classes` 누락 뷰 (LOW)

DEFAULT가 안전 측이라 실질 위험은 낮지만 명시성 향상 권장:

| 파일 | 클래스 / 라인 | 적용 perm | 비고 |
|------|---------------|-----------|------|
| `chainsight/api/views.py` | `ChainSightGraphView` (58), `ChainSightSuggestionView` (109), `ChainSightTraceView` (185), `SeedListView` (309), `SectorGraphView` (318), `NeighborGraphView` (448), `SignalFeedView` (628) | DEFAULT (IsAuthenticated) | 7개 모두 명시 누락. 의도 확인 필요 |
| `stocks/views.py` | `StockListAPIView` (84), `StockSearchAPIView` (169), `StockChartDataAPIView` (222), `StockBalanceSheetAPIView` (609), `StockIncomeStatementAPIView` (685), `StockCashFlowAPIView` (758), `StockCompleteDataAPIView` (830) | DEFAULT | 7개 명시 누락 |
| `stocks/views_eod.py` | `EODDashboardView` (20), `EODSignalDetailView` (51), `EODPipelineStatusView` (110) | DEFAULT | 3개 명시 누락 |
| `stocks/views_indicators.py` | `TechnicalIndicatorView` (16), `IndicatorSignalView` (200), `IndicatorComparisonView` (297) | DEFAULT | 3개 명시 누락 |
| `stocks/views_search.py` | `SymbolSearchView` (18), `SymbolValidateView` (91), `PopularSymbolsView` (146) | DEFAULT | 3개 명시 누락. 검색은 공개로 의도되었을 가능성 → 확인 필요 |
| `news/api/views.py` | `NewsViewSet` (55) ViewSet base | DEFAULT (action별 @action에서 명시) | base가 명시 안 됨. `list`/`retrieve` 기본 액션은 default 적용 |
| `validation/api/views.py` | `ValidationSummaryView` (52), `ValidationMetricsView` (173), `LeaderComparisonView` (317), `PresetListView` (424), `LLMPeerFilterView` (498) | DEFAULT | 5개 명시 누락 |

→ **권장**: 위 뷰들에 `permission_classes = [IsAuthenticated]` 또는 의도된 `[AllowAny]`/`[IsAdminUser]` 명시. 특히 `stocks/views_search.py`는 로그인 전에도 노출되어야 할 가능성이 높으므로 의도된 동작이 default와 일치하는지 검증 필요.

### 1.3 `macro/views.py` — 외부 API 비용 노출 (MED)

```
macro/views.py
  MarketPulseView (25)         permission_classes = [AllowAny]
  FearGreedIndexView (50)      [AllowAny]
  InterestRatesView (75)       [AllowAny]
  InflationDashboardView (106) [AllowAny]
  GlobalMarketsView (137)      [AllowAny]
  EconomicCalendarView (168)   [AllowAny]
  VIXView (214)                [AllowAny]
  SectorPerformanceView (244)  [AllowAny]
  DataSyncView (353)           [IsAdminUser]  ✓
  SyncStatusView (389)         [AllowAny]
```

8개 거시 데이터 뷰가 무인증 + DRF throttle은 `anon: 20/min`(`config/settings.py:357`)만 적용. 외부 API(FRED/FMP 등)를 호출하는 캐시 미스 시 비용/레이트 한도 소진 가능.

→ **권장**: (1) 캐시 의무화로 외부 호출 분리, (2) `anon` throttle 강화 또는 IP별 별도 throttle 적용, (3) 가능하면 `IsAuthenticated`로 상향.

### 1.4 `chainsight/views.py` 빈 파일 (INFO)

`chainsight/views.py`는 1줄 빈 파일. 실제 뷰는 `chainsight/api/views.py`에 존재. routing 일관성만 확인 필요.

### 1.5 `users.Users.get_permissions()` 동작 (INFO)

```python
def get_permissions(self):
    if self.request.method.lower() == 'get':
        return [IsAdminUser()]
    return []   # POST = 회원가입 = 사실상 AllowAny
```

`get_permissions()` 오버라이드 시 `DEFAULT_PERMISSION_CLASSES`가 우회됨. `return []`은 권한 검사 없음. **의도된 동작**(회원가입 공개)이며 안전하나, 명시적으로 `[AllowAny()]`를 반환하는 편이 가독성에 좋음.

---

## 2. SQL 인젝션 (OWASP A03)

`cursor.execute()` 사용 4곳 모두 검토 완료. **모두 안전**.

| 파일:라인 | 쿼리 형태 | 사용자 입력 바인딩 | 판정 |
|-----------|-----------|---------------------|------|
| `chainsight/services/seed_selection.py:152` | `WITH latest AS (... WHERE date = (SELECT MAX(date) FROM ... WHERE date <= %s) ...) ... WHERE date <= %s ...` | `%s` placeholder + `[market_date, market_date]` 파라미터 | **SAFE** — Django DB API 파라미터 바인딩 |
| `serverless/services/admin_status_service.py:833` | `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30` | 정적 SQL, 외부 입력 없음 | **SAFE** |
| `api_request/admin_views.py:300` | `SELECT 1` | 정적 헬스체크 | **SAFE** |
| `config/views.py:90` | `SELECT 1` | 정적 헬스체크 | **SAFE** |

→ **결론**: SQL 인젝션 표면 없음. 향후 raw SQL 추가 시에도 `%s`/`%(name)s` 패턴 강제 권장.

---

## 3. LLM 프롬프트 인젝션 (OWASP A03 LLM 확장)

### 3.1 방어가 적용된 곳 (POSITIVE)

| 파일 | 방어 패턴 |
|------|-----------|
| `rag_analysis/services/llm_service.py:178-192` | `</context_data>` / `</user_question>` 닫는 태그 escape + "데이터로만 취급" 명시 instruction. P0 #3 (2026-05-19) 적용 |
| `thesis/services/thesis_builder.py:435` | `text[:500]` + ` ``` `/`---` 제거 |
| `thesis/services/indicator_matcher.py:175-204` | `_sanitize_for_prompt()` 유틸 + 제목/대상 별도 적용 |

### 3.2 잔존 위험 — HIGH

#### H-1. `thesis/views/conversation_views.py:230-261` — 뉴스 제목 직접 삽입

```python
title_list = '\n'.join(
    f'{i+1}. {t["title"][:80]}' for i, t in enumerate(titles[:8])
)
prompt = f"""... {title_list} ..."""
```

- 길이 컷(80자)은 있으나, **닫는 태그 escape · 구분자 제거 · 신뢰 경계 표지 없음**.
- 외부 뉴스 API(Finnhub/Marketaux)는 일반적으로 신뢰 가능하지만, **공급 체인 공격**(키워드 인젝션 페이지 콘텐츠) 가능성 0이 아님.
- `response_mime_type="application/json"`로 강제 JSON 응답이라 폭발 반경은 제한적.

→ **권장**:
1. `title`을 `_sanitize_for_prompt()` 또는 동일 패턴 적용 (` ``` `, `---`, `</...>` 제거).
2. `<news_titles>...</news_titles>` 신뢰 경계 명시 + system instruction에 "데이터로만 취급" 추가.

### 3.3 잔존 위험 — MED

#### M-1. `news/services/keyword_extractor.py:262-275` — 뉴스 요약·종목 LLM 삽입

```python
f"{i}. [{news['source']}] {news['title']}\n"
f"   요약: {news['summary'][:100]}...\n"
f"   감성: {sentiment_str}, 관련종목: {symbols_str}"
```

길이 컷만 있고 escape 없음. 시스템 프롬프트(`_build_system_prompt`)가 분리되어 있어 위험은 더 낮지만 H-1과 동일한 보강 필요.

#### M-2. `serverless/services/keyword_generator_v2.py:258-306`

`build_batch_prompt(contexts, mover_type)` — market mover context를 LLM에 삽입. context는 내부 산출 데이터로 신뢰도가 높으나, 만약 종목명/회사명에 외부 입력이 섞이면 인젝션 표면. `keyword_prompts_v2.py`의 빌더에서 escape 여부 확인 필요(이번 감사 범위 외 — 별도 추적).

→ **권장**: 모든 LLM 프롬프트 빌더에 `_sanitize_for_prompt()` 같은 공통 헬퍼 일관 적용. `shared` 모듈로 추출 권장.

### 3.4 `tests/unit/security/test_prompt_injection_guards.py` 존재 (INFO)

`thesis_builder`와 `llm_service` 가드가 회귀 방지 테스트로 보호되고 있음. → 신규 호출 사이트(H-1, M-1)에도 동일 테스트 추가 권장.

---

## 4. 시크릿 관리 (OWASP A05 / A07)

### 4.1 환경 변수 처리 — POSITIVE

- `.gitignore`에 `.env` 명시 (line 9-10).
- `git ls-files`에서 `.env` 추적 0건, `.env.example`만 추적.
- `.env` 권한 `-rw-------` (600).
- `config/settings.py:142-170` 운영 배포 가드: `DEBUG=False`에서 `SECRET_KEY`/`NEO4J_PASSWORD` 미설정 시 `ImproperlyConfigured` 발생.
- `JWT_SIGNING_KEY`를 `SECRET_KEY`와 분리하여 별도 회전 가능 (line 148).

### 4.2 하드코딩 시크릿 — 0건

`(token|secret|key|password) = "..."` 패턴 정적 스캔 결과 0건 (테스트/fixture 제외). 모두 `os.getenv()` 경유.

### 4.3 LOW 사항

| 항목 | 위치 | 위험 |
|------|------|------|
| `DEFAULT_FROM_EMAIL` fallback `stockvis@example.com` | `settings.py:528` | INFO — 운영에서 미설정 시 잘못된 발신자. ImproperlyConfigured 가드 추가 권장 |
| `CELERY_ERROR_RECIPIENTS` 하드코딩 | `settings.py:536-537` | INFO — `goid545@naver.com`, `jinie545@gmail.com`. 개인 메일이 코드에 노출. env로 분리 권장 |
| `DB_USER` fallback `'byeongjinjeong'` | `settings.py:253` | INFO — 운영에서 의도치 않게 dev 사용자명을 시도할 수 있음 |
| `_SECRET_KEY_DEV_FALLBACK` placeholder | `settings.py:143` | INFO — DEBUG에서만 사용 가능, 가드 OK |

### 4.4 LOG 노출 — INFO

`stocks.log`(`settings.py:459`)가 프로젝트 루트에 기록됨. `.gitignore`에 `*.log` 명시 여부 확인 필요(이번 감사 범위에선 미확인). 운영에서 로그가 git에 섞이지 않도록 보호 권장.

---

## 5. CORS / CSRF / 헤더 (OWASP A05)

### 5.1 CORS — POSITIVE

```python
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True
```

- DEBUG 의존 제거하고 별도 env로 운영 사고 방지(코멘트 명시).
- 운영 도메인은 env로 추가해야 함(`CORS_ALLOWED_ORIGINS`에 dev origin만 하드코딩 → MED).

#### M-3. `CORS_ALLOWED_ORIGINS`에 운영 도메인 분리 부재

→ **권장**: `CORS_ALLOWED_ORIGINS_EXTRA = os.getenv('DJANGO_CORS_ORIGINS', '').split(',')` 같은 형태로 운영 도메인 주입.

### 5.2 CSRF — INFO

- `MIDDLEWARE`에 `CsrfViewMiddleware` 포함(`settings.py:219`).
- `@csrf_exempt` 실사용 0건 (import만 `config/views.py:6`에 있고 사용처 없음).
- JWT API는 SessionAuth와 병행되므로 CSRF가 의미를 가짐. 단, `rest_framework_simplejwt` JWT만 통과시키려면 SessionAuth 제거 검토 가능.

### 5.3 보안 헤더 / 추가 미들웨어 — LOW

`SECURE_*` 설정(`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)이 settings에 없음. 운영 배포 시 reverse proxy/load balancer에서 보강된다고 가정 가능하나, 명시 권장.

```text
누락 설정 (운영 배포 가드 권장):
- SECURE_SSL_REDIRECT = True
- SECURE_HSTS_SECONDS = 31536000
- SECURE_HSTS_INCLUDE_SUBDOMAINS = True
- SESSION_COOKIE_SECURE = True
- CSRF_COOKIE_SECURE = True
- SECURE_CONTENT_TYPE_NOSNIFF = True
- SECURE_REFERRER_POLICY = "same-origin"
- X_FRAME_OPTIONS = "DENY"  (clickjacking middleware 자체는 활성)
```

### 5.4 DEBUG / ALLOWED_HOSTS — INFO

```python
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [...] or (['*'] if DEBUG else [])
```

- 기본 `False` ✓
- DEBUG=True에서만 `['*']` 허용, 운영에서는 명시 hosts 필요 ✓ (배포 시 `DJANGO_ALLOWED_HOSTS` env 필수).

---

## 6. 에러 / 스택트레이스 노출 (OWASP A04 / A05)

### 6.1 표준 envelope 적용 — POSITIVE

`config/exception_handler.py`가 DRF 응답 envelope을 `{detail, code, errors, status_code}`로 표준화. `ValidationError`만 `errors` dict 노출, 그 외는 `detail` 문자열.

### 6.2 `str(e)` 직접 응답 — MED / LOW

```
api_request/admin_views.py:69,77,104,127,154,185,238,272 — "error": str(e)
api_request/stock_service.py:745 — return {'error': str(e)}
rag_analysis/tasks.py:264,323,375,447,516,557 — Celery 결과 dict에 'error': str(e)
```

- `api_request/admin_views.py`는 전부 `IsAdminUser` 보호 → 위험 LOW.
- `api_request/stock_service.py:745`는 내부 서비스 반환이라 직접 노출 여부는 호출자 의존. 확인 필요 → MED 잠정.
- `rag_analysis/tasks.py`는 Celery task 결과로 사용자 응답에는 직접 노출되지 않지만, `django_celery_results` admin/조회 API를 통해 노출 가능성 → LOW.

→ **권장**: (1) admin/internal 외 응답 경로에서 `str(e)` 제거 또는 generic message로 대체, (2) 로깅은 유지하되 사용자 facing 메시지는 sanitize.

### 6.3 Logging — INFO

- `LOGGING.handlers.file.filename = 'stocks.log'` (프로젝트 루트).
- 운영에서는 `LOG_FILE_PATH` env로 외부 경로 지정 권장.

---

## 7. 기타 점검 항목

### 7.1 IDOR — INFO

이전 감사에서 Watchlist IDOR 패치 적용된 것으로 메모리에 기록(`project_p0_security_patches_2026-05-20.md`). 본 감사에선 직접 검증 안 함.

### 7.2 Mass assignment — INFO

`users.Users.post`(line 96-109)에서 `PrivateUserSerializer(data=request.data)` 통째로 전달 후 `set_password()`. PrivateUserSerializer가 `is_admin`/`is_staff` 등 권한 필드를 read-only 또는 제외했는지 확인 필요 → 별도 감사.

### 7.3 Open Redirect / SSRF — 본 감사 범위 외

뉴스/주가 외부 API URL은 settings/env에서 정해진 base URL로 호출되므로 SSRF 표면 작음. 다만 `serverless/services/csv_url_resolver.py`는 외부 URL 다루므로 별도 검토 권장.

### 7.4 의존성 취약점 — 본 감사 범위 외

`poetry.lock`/`requirements.txt` 기반 CVE 스캔 필요 (별도 작업).

---

## 8. 종합 권장 우선순위

### Sprint A (이번 주, 30분~2시간씩)

1. **H-1 — `thesis/views/conversation_views.py` 뉴스 제목 escape** (MED→이지 픽스)
   - `_sanitize_for_prompt()` 적용 + `<news_titles>` 신뢰 경계 추가. 약 15분.
   - 회귀 테스트 `tests/unit/security/test_prompt_injection_guards.py`에 케이스 추가.

2. **M-3 — `CORS_ALLOWED_ORIGINS` 운영 도메인 env 분리**
   - `DJANGO_CORS_ORIGINS` env 도입.

3. **M-1, M-2 — 뉴스/keyword 빌더 sanitize**
   - 공통 헬퍼 추출. 약 30분.

### Sprint B (다음 주)

4. **macro 뷰 throttle / 캐시 의무화** (1.3)
5. **명시적 `permission_classes` 추가** (1.2) — 30개 뷰. 자동화 가능.
6. **운영 보안 헤더(`SECURE_*`) 추가** (5.3)
7. **`CELERY_ERROR_RECIPIENTS` env로 분리** (4.3)

### Sprint C (배경 작업)

8. **`api_request/stock_service.py:745` 등 `str(e)` 응답 sanitize** (6.2)
9. **PrivateUserSerializer mass-assignment 검증** (7.2)
10. **의존성 CVE 스캔 도입** (7.4)

---

## 9. Positive Findings (재발 방지를 위해 기록)

| 항목 | 위치 | 비고 |
|------|------|------|
| DEFAULT_PERMISSION_CLASSES = IsAuthenticated | `settings.py:353` | P0 #5 (2026-04-29) |
| SECRET_KEY/NEO4J_PASSWORD 운영 가드 | `settings.py:158-170` | ImproperlyConfigured raise |
| JWT_SIGNING_KEY 분리 | `settings.py:148` | 별도 회전 가능 |
| LLM 닫는태그 escape | `rag_analysis/services/llm_service.py:178-192` | P0 #3 (2026-05-19) |
| `_sanitize_for_prompt()` 유틸 | `thesis/services/indicator_matcher.py:175` | 재사용 패턴 정착 |
| 회귀 방지 테스트 | `tests/unit/security/test_prompt_injection_guards.py` | LLM 가드 테스트 |
| CORS_ALLOW_ALL_ORIGINS env 명시 제어 | `settings.py:316-318` | DEBUG 의존 제거 |
| `.env` gitignore + 600 권한 | `.gitignore:10`, FS 권한 | 시크릿 보호 |
| 표준 에러 envelope | `config/exception_handler.py` | 일관된 응답 |
| raw SQL 모두 안전 | (위 §2 참조) | 파라미터 바인딩 또는 정적 |

---

## 10. 감사 메서드 / 한계

- **정적 분석만 수행** (코드 실행/엔드포인트 호출 없음).
- **검토 대상**: 지시받은 17개 뷰 파일 + `config/settings.py` + `cursor.execute` 4곳 + 주요 LLM 호출 파일.
- **검토 미수행**(별도 감사 권장): `rag_analysis/services/pipeline.py`, `serverless/services/keyword_prompts_v2.py`, `serverless/services/llm_relation_extractor.py`, `serverless/services/thesis_builder.py`(기존 thesis와 별개 파일), poetry 의존성 CVE, 프론트엔드 XSS 표면, JWT lifetime/refresh 정책 적정성, Celery task 권한 모델, Neo4j 쿼리 인젝션.
- **memory 의존**: 이전 P0 패치(`project_p0_security_patches_2026-05-20.md`)에 따라 일부 항목은 패치된 것으로 가정. 재검증 없음.

— EOF —
