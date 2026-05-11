# Stock-Vis 보안 감사 보고서

- 감사일: 2026-05-09
- 범위: Backend (Django REST Framework), Frontend는 XSS 패턴만 표면 검사
- 모드: 읽기 전용 (코드 수정 없음)
- 기준: OWASP Top 10 (2021)

---

## 요약 (Executive Summary)

| 심각도 | 건수 | 분류 |
|-------|----|------|
| CRITICAL | 1 | A01 인가 (익명 Watchlist 공유) |
| HIGH | 3 | A02 비밀 관리, A05 보안 헤더, A09 에러 노출 |
| MED | 5 | A01 명시적 권한 누락, A03 LLM 인젝션, A05 CORS, A07 로그 정보 노출 |
| LOW | 3 | 코드 일관성, 의도 명시 누락 |
| INFO | 4 | 모범 사례 확인 |

전반적으로 **인증 기본값이 IsAuthenticated**로 안전하게 설정되어 있고 SQL 인젝션·하드코딩 시크릿은 발견되지 않습니다. 다만 **chainsight WatchlistViewSet의 익명 데이터 풀 공유**는 즉시 수정 필요한 권한 우회 결함입니다.

---

## 1. 인증 / 인가 (A01: Broken Access Control)

### 1.1 [CRITICAL] 익명 사용자가 다른 익명 사용자의 Watchlist를 조회·삭제 가능

`chainsight/views/watchlist_views.py:30-46`

```python
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    ...
    def get_queryset(self):
        qs = SavedPath.objects.all()
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True)
```

- 비로그인 요청은 모두 `user__isnull=True`로 필터링되는 **공용 풀**에 적재됨.
- 익명 사용자 A가 만든 SavedPath를 익명 사용자 B가 GET, DELETE, archive할 수 있음 (동일 ViewSet에 `delete`/`archive` 액션 존재).
- 단순 IDOR(Insecure Direct Object Reference) 시나리오: `/api/v1/chainsight/watchlist/<id>/` 직접 호출.
- AnonRateThrottle 30/min이 걸려 있으나 권한 우회를 막지는 못함.

권장: `IsAuthenticated`로 변경하거나, 익명 사용자에게는 세션 기반 ownership 토큰(예: 클라이언트가 보낸 unique cookie/UUID)을 쿼리에 포함시키도록 수정.

### 1.2 [HIGH] view 클래스에 `permission_classes` 명시 누락 (의존성 위험)

DRF DEFAULT_PERMISSION_CLASSES가 `IsAuthenticated`로 설정되어 있어 현재는 보호되지만 (`config/settings.py:353-355`), 다음 파일들은 클래스 단위 명시가 없어서 **settings.py 기본값을 누가 변경하면 곧바로 익명 노출**됩니다.

| 파일 | 클래스 (라인) | 비고 |
|------|--------|----|
| stocks/views_eod.py | EODDashboardView, EODSignalDetailView, EODPipelineStatusView (20, 51, 110) | docstring에 "admin 전용"이라 적혀 있으나 IsAdminUser 미적용 — 실제로는 일반 인증 사용자도 접근 가능 |
| stocks/views_indicators.py | TechnicalIndicatorView, IndicatorSignalView, IndicatorComparisonView (16, 200, 297) | |
| stocks/views_search.py | SymbolSearchView, SymbolValidateView, PopularSymbolsView (18, 91, 146) | |
| stocks/views_mvp.py | StockMVPListView, StockMVPDetailView, StockRAGContextView, SectorListView (17, 69, 142, 190) | |
| chainsight/api/views.py | ChainSightGraphView, SuggestionView, TraceView, SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView (58~628) | 7개 모두 명시 누락 |
| validation/api/views.py | ValidationSummaryView, ValidationMetricsView, LeaderComparisonView, PresetListView, LLMPeerFilterView (52, 173, 317, 421, 495) | PeerPreferenceView만 명시(458) |

심각도: MED (현재 안전, 의존성 취약)
권장: 각 클래스에 `permission_classes = [IsAuthenticated]` 명시.

### 1.3 [HIGH] EOD admin 엔드포인트가 일반 인증 사용자에게 노출

`stocks/views_eod.py:110-136` `EODPipelineStatusView` 는 docstring에 "admin 전용"이라 명시되어 있지만 `permission_classes`가 없어서 모든 인증 사용자가 7일치 파이프라인 로그(`run_id`, 단계별 status, error_message)를 조회할 수 있습니다. 운영 정보 노출은 정찰 단계에서 악용될 수 있습니다.

권장: `permission_classes = [IsAdminUser]` 명시.

### 1.4 [LOW] `StockSyncAPIView`의 빈 `permission_classes = []`

`stocks/views.py:878-886`

```python
class StockSyncAPIView(APIView):
    # 공개 주식 데이터 동기화는 인증 없이 허용
    permission_classes = []
```

- 빈 리스트는 DRF가 기본값(IsAuthenticated)으로 회귀시킵니다 → 의도가 "공개 허용"이면 `[AllowAny]`로 명시해야 합니다. 의도와 결과가 일치하지 않는 위험.
- POST 동작이 외부 API 호출(Alpha Vantage, FMP)을 트리거하는 sync 액션이므로, 인증 없이 호출되도록 의도했다면 abuse 방지(레이트리밋, 캡차 등) 검토 필요.

### 1.5 [INFO] 적절히 설계된 영역

- `users/views.py`: 27개 클래스 중 `LogIn`, `PublicUser`만 `AllowAny`로 명시되고 나머지 모두 `IsAuthenticated`. 인증 흐름은 정상.
- `news/api/views.py`: 17개 ml-* / collection-logs / pipeline-health 등 admin 전용 액션이 모두 `IsAdminUser`로 명시됨.
- `serverless/views_admin.py`: 12개 모두 `IsAdminUser`.
- `serverless/views.py`: 함수형 뷰들이 audit P0 #6 주석과 함께 명시적 권한 적용됨.
- `marketpulse/api/views/*.py`: 모두 명시.
- `sec_pipeline/views.py:34`: `IsAdminUser` 명시.
- `macro/views.py`의 8개 `AllowAny`: 거시경제 데이터(공포/탐욕, 금리, 인플레이션 등)는 공개 데이터로 의도 일치.

---

## 2. 인젝션 (A03)

### 2.1 [INFO] SQL 인젝션 — 안전

`grep cursor.execute` 결과 4건 모두 검토 완료:

| 파일 | 라인 | 패턴 | 평가 |
|------|----|----|----|
| config/views.py | 90 | `cursor.execute("SELECT 1")` 하드코딩 | 안전 |
| api_request/admin_views.py | 300 | `cursor.execute("SELECT 1")` 하드코딩 | 안전 |
| serverless/services/admin_status_service.py | 833 | `pg_stat_user_tables` 하드코딩 | 안전 |
| chainsight/services/seed_selection.py | 152 | `WITH latest AS (...)` + `%s` 파라미터 바인딩 | 안전 |

ORM 외 raw SQL 사용 4곳 모두 사용자 입력이 직접 삽입되는 경로 없음.

### 2.2 [INFO] XSS — 안전 표면 검사

- `mark_safe`, `format_html` Backend 사용 없음.
- Frontend `dangerouslySetInnerHTML` 사용 없음 (테스트 파일의 `innerHTML` 비교만 존재).
- DRF JSON 응답이 기본이고, Django 템플릿 렌더링은 사용하지 않으므로 reflected XSS 위험 낮음.

---

## 3. LLM 프롬프트 인젝션 (A03 확장)

총 29개 파일에서 Gemini를 호출합니다. 사용자 입력이 프롬프트에 들어가는 핵심 경로를 검토했습니다.

### 3.1 [LOW] `_parse_free_input` — 부분적 방어 적용됨

`thesis/services/thesis_builder.py:421-450`

```python
# 프롬프트 인젝션 방지: 길이 제한 + 구분자 제거
safe_text = text[:500].replace('```', '').replace('---', '').strip()
prompt = f"""사용자가 투자 가설을 자유롭게 입력했어. 이걸 구조화해줘.
입력: "{safe_text}"
다음 JSON 형식으로만 반환해:
...
JSON만 반환해. 다른 텍스트 없이."""
```

- 길이 제한(500자)과 markdown fence 제거는 적절합니다.
- 다만 `JSON만 반환해` 등 system instruction이 user content와 같은 turn에 들어가 있어 jailbreak에 약함. `system_instruction` 인자로 분리 권장.
- 출력 검증: `json.loads`만 하고 schema validation이 없음 → `direction`/`target_type`/`thesis_type` 값이 enum 외 값일 때 fallback이 없음.

### 3.2 [MED] `NewsIssuesView._convert_to_korean_issues` — 사용자 인입 영역

`thesis/views/conversation_views.py:213-303`

- DB의 NewsArticle 제목(`a.title`)을 `[:80]`로 자른 후 그대로 프롬프트에 삽입.
- 뉴스는 외부 출처(Finnhub, Marketaux, NewsAPI 등)에서 옴 — **외부 공급자가 적대적 제목**을 게시하면 프롬프트 인젝션 매개체로 사용 가능.
- 영향: 내부 LLM 호출 1회당 비용 증가 또는 잘못된 분류, 직접적인 데이터 유출은 없음 (system_instruction 미사용).
- 권장: 시스템 지시를 `config.system_instruction`으로 분리하고, 입력 직전에 `NEWS_TITLES_BEGIN`/`NEWS_TITLES_END` 같은 명시적 sentinel 추가.

### 3.3 [MED] `keyword_extractor` — 외부 뉴스 본문 직접 삽입

`news/services/keyword_extractor.py:262-282`

```python
news_summary.append(
    f"{i}. [{news['source']}] {news['title']}\n"
    f"   요약: {news['summary'][:100]}...\n"
    ...
)
return f"""# {target_date.strftime('%Y년 %m월 %d일')} 뉴스 분석
...
{chr(10).join(news_summary)}
..."""
```

- 외부 뉴스 제목/요약을 직접 프롬프트에 합침. system_instruction 분리는 되어 있으나(`_build_system_prompt`), 입력 sanitization은 없음.
- Structured Output(JSON schema)이 없어 출력 검증은 정규식 `\[[\s\S]*\]`에 의존.
- `_call_llm` 응답이 DB(`DailyNewsKeyword.keywords`)와 사용자 응답에 그대로 들어감 → 적대적 뉴스 제목으로 응답에 의도된 텍스트를 주입할 가능성.

권장: title/summary를 토큰으로 둘러싸고("`<NEWS_TITLE>...</NEWS_TITLE>`"), Structured Output(`response_schema`)을 thesis suggestion처럼 적용.

### 3.4 [LOW] `thesis/services/prompt_builder.py:build_modify_premise_prompt` 등

- `f"""현재 가설의 전제 목록: {premises_desc}..."""` 처럼 DB 사용자 데이터(전제 title)를 그대로 system_prompt에 주입.
- 단, 본인 데이터(자신의 전제) 한정이므로 self-injection만 가능 → 영향 제한적이지만 LLM 비용 abuse 가능성은 존재.

### 3.5 [INFO] 적절한 부분

- `rag_analysis/services/llm_service.py`: `system_instruction` 분리(`config=types.GenerateContentConfig(system_instruction=self.get_system_prompt())`), `<suggestions>`/`<basket-action>` 태그로 응답 구조화.
- `thesis/services/prompt_builder.py:call_gemini`: `response_mime_type="application/json"` + `response_schema` 사용으로 출력 검증.
- 모든 Gemini 호출에 `thinking_budget=0` 일관 적용.

---

## 4. 시크릿 관리 (A02)

### 4.1 [INFO] `.env` 보호 양호

- `.env` 파일 권한 `-rw-------` (600).
- `.gitignore`에 `.env`와 `*.key` 등재.
- `git ls-files .env`, `git log -- .env` 모두 결과 없음 → 추적 이력 없음.
- AWS/OpenAI/Gemini/GitHub/Slack 패턴 (`AKIA*`, `sk-*`, `AIza*`, `ghp_*`, `xox[baprs]-`) 코드베이스 전체 grep 결과 0건.

### 4.2 [INFO] SECRET_KEY / NEO4J_PASSWORD 운영 가드

`config/settings.py:142-170`

- DEV-ONLY placeholder 사용 시 `DEBUG=False`이면 `RuntimeError` 발생.
- `JWT_SIGNING_KEY`를 SECRET_KEY와 분리하여 회전 가능.
- `ALLOWED_HOSTS` 미지정 + DEBUG=False면 빈 리스트(요청 거절) — 안전한 fail-closed.

### 4.3 [HIGH] Settings 단계의 보안 강화 헤더 누락

`config/settings.py` 전체 검색 결과 다음 항목이 **없음**:

- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_PROXY_SSL_HEADER`
- `X_FRAME_OPTIONS` (Django 기본 `SAMEORIGIN`이 있으나 명시 권장)
- `SECURE_REFERRER_POLICY`

운영(`DEBUG=False`) 배포 시 HTTP 다운그레이드/쿠키 탈취/Clickjacking 위험.

권장: 운영 환경 settings에서 위 항목 명시 (`SESSION_COOKIE_SECURE=True`, `SECURE_HSTS_SECONDS=31536000` 등).

---

## 5. CORS / 에러 노출 / 로그

### 5.1 [INFO] CORS 설정 — 안전

`config/settings.py:310-341`

- `CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]`
- `CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'` — DEBUG 의존성 제거하고 명시 env로만 제어. **모범 사례.**
- `CORS_ALLOW_CREDENTIALS = True`
- 다만 `CORS_ALLOWED_ORIGINS`이 하드코딩이라 운영 도메인이 추가되면 코드 수정 필요 — env 기반 화 권장.

### 5.2 [MED] 에러 응답에 내부 메시지/스택 누설

다음 위치들이 `str(e)`를 사용자에게 그대로 반환합니다:

| 파일 | 라인 |
|------|----|
| rag_analysis/views.py | 420 (`snapshot['error']=str(e)`), 593 (`PIPELINE_ERROR`), 604 (`STREAM_ERROR`), 676, 732, 763, 835 |
| users/views.py | 520, 565 (RefreshPortfolioData 등에 GE 에러 메시지 직접 노출), 903 |
| stocks/views_search.py | 87, 142 (`'서버 오류: {str(e)}'`) |

위험: DB 제약 메시지, 쿼리 일부, 외부 API 응답 본문이 클라이언트로 새어나갈 수 있음. Provider 키 일부가 에러 본문에 포함되는 시나리오도 존재.

권장: 사용자에게는 사전 정의된 에러 코드/메시지만 반환하고, 상세는 `logger.exception`으로 서버 로그에만 기록.

### 5.3 [MED] 로그가 사용자 입력/응답을 그대로 기록

- `news/services/keyword_extractor.py:202` `logger.debug(f"LLM response: {response_text}")` — debug 레벨이지만 운영 로그 설정에 따라 누설 위험.
- `thesis` 여러 위치 `logger.exception(f"Gemini ...: {e}")` — exception 객체에 프롬프트 일부가 포함될 수 있음.
- `chainsight/views/watchlist_views.py`처럼 사용자 데이터(SavedPath)와 함께 기록될 경우 PII 위험.

권장: 운영 로그 레벨 INFO로 고정, debug 메시지에 프롬프트 본문 포함 금지.

### 5.4 [LOW] DEBUG 모드 처리

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'` — 기본값 False (양호).
- DEBUG 시에만 `ALLOWED_HOSTS=['*']` 으로 설정 — 개발용으로 적절.

---

## 6. 기타

### 6.1 [LOW] DRF Throttle 적용 범위 제한

- `DEFAULT_THROTTLE_RATES`에 `market_pulse_*`만 정의됨. 글로벌 default throttle 미설정.
- chainsight Watchlist만 `AnonRateThrottle 30/min` — 인증 사용자에 대한 쓰기 abuse 방어 부재.
- 권장: `DEFAULT_THROTTLE_CLASSES` 추가 (UserRateThrottle, AnonRateThrottle), 무거운 LLM 호출 view에는 별도 scope.

### 6.2 [INFO] JWT 설정

- `JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or SECRET_KEY` — 분리 가능, 회전 친화적.
- `rest_framework_simplejwt` 사용 — 표준 라이브러리.

---

## 우선 조치 권고 (Top 5)

1. **CRITICAL — chainsight WatchlistViewSet `AllowAny` 제거**: 익명 풀에서 다른 익명 사용자 데이터 조회/삭제 가능. `IsAuthenticated`로 변경 또는 클라이언트 ownership 토큰 도입.
2. **HIGH — 운영용 보안 헤더 추가**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` 등 7~8개 항목.
3. **HIGH — `EODPipelineStatusView`에 `IsAdminUser` 적용**: 운영 로그를 일반 사용자에게 노출 중.
4. **MED — 에러 응답에서 `str(e)` 제거**: rag_analysis/views.py 7곳, users/views.py 3곳, stocks/views_search.py 2곳.
5. **MED — 외부 뉴스 입력의 LLM 프롬프트 sanitization**: keyword_extractor + NewsIssuesView에 sentinel 토큰 + Structured Output 적용.

## 권한 명시 일괄 보강 (LOW, 일관성)

위 1.2 표의 25개 클래스에 `permission_classes = [IsAuthenticated]` 명시 — 기본값 회귀 사고 방지.

---

## 감사 방법론

- `grep -rl 'cursor.execute'` → SQL injection 표면 4건
- `grep -rl 'permission_classes'` → 권한 적용 26개 파일
- `grep -rln 'genai\.Client\|generate_content'` → LLM 호출 29개 파일
- `grep -rn 'AKIA|sk-|AIza|ghp_|xox[baprs]-'` → 하드코딩 시크릿 0건
- `git ls-files .env`, `git log -- .env` → 추적 0건
- 핵심 view/service 파일 라인 단위 검토

본 보고서는 정적 분석 기반이며, 동적 테스트(예: 실제 IDOR 호출)는 포함하지 않습니다. CRITICAL 항목은 staging 환경에서 재현 후 패치하는 것을 권장합니다.
