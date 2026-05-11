# 보안 감사 보고서 — Stock-Vis

- **감사일**: 2026-04-25
- **브랜치**: portfolio (HEAD `1d3386e`)
- **범위**: OWASP Top 10 — 인증/인가, 인젝션(SQL/Cypher/LLM), 시크릿 관리, CORS/XSS/에러 노출
- **모드**: 읽기 전용 — 코드 수정 없음
- **베이스라인**: `docs/nightly_auto_system/reports/4월/24일/security_audit.md`
- **델타 검증 대상**: `git log --since=2026-04-23` 5건의 커밋 (`1d3386e`, `3d00fb1`, `df85496`, `147170a`, `d96e434`) + 신규 `portfolio/` 앱
- **근거 파일**: `config/settings.py`, 뷰 27개(`**/views*.py`), `cursor.execute` 4곳, Gemini 호출 핵심 경로, `.gitignore`

---

## 0. 베이스라인 대비 변동 요약 (2026-04-24 → 2026-04-25)

| 항목 | 변동 | 근거 |
|------|------|------|
| `config/settings.py` | **변동 없음** | `git diff HEAD~5 HEAD -- config/settings.py` 결과 0 바이트 |
| `serverless/views.py` | 28라인 변경, **권한/인증 변경 없음** | `timezone.now().date()` → `timezone.localdate()` 일괄 치환(#29) |
| `stocks/views.py` | 변동 없음 — `StockSyncAPIView.permission_classes = []` 그대로 (line 886) | grep 확인 |
| `chainsight/views/watchlist_views.py` | 변동 없음 — `AllowAny` + `WatchlistAnonThrottle 30/min` 유지 | grep 확인 |
| `.gitignore` | **개선** — SSH 비밀키 패턴 21줄 추가(`**/id_rsa`, `*.pem`, `*.key`, `/dlswnl545*` 등) | `d96e434` |
| Alpha Vantage Provider | **공격 표면 축소** — provider 코드 제거(`df85496`). `news/models.py:33,285`에 enum 라벨만 잔재(런타임 영향 없음) | grep |
| `portfolio/` 신규 앱 | **API 미노출** — `views.py`/`urls.py` 없음. models/schemas/prompts/tests만 존재 | `find portfolio -name "views*.py" -o -name "urls*.py"` 결과 0건 |
| 신규 발견 | M-7 — `macro/views.py:DataSyncView` 익명 POST가 `_run_data_sync` 스레드 트리거(베이스라인 미명시) | 본 보고서 §5 |

**결론**: 4/24 보고서의 CRITICAL 4건·HIGH 7건은 코드 상에서 **모두 그대로 유효**. 시크릿 위생(SSH 키)·외부 의존(Alpha Vantage)은 소폭 개선. 신규 `portfolio/` 앱은 현재 보안 표면을 늘리지 않음.

---

## 요약 (Severity 분포)

| 등급 | 건수 | 대표 이슈 |
|------|------|----------|
| CRITICAL | 4 | 하드코딩 `SECRET_KEY`(JWT 서명 공용), `DEBUG=True`, `StockSyncAPIView permission_classes=[]`, `serverless/views.py` 관리자/Celery 트리거 다수 공개 |
| HIGH | 7 | `ALLOWED_HOSTS=[]`, Neo4j 기본 비밀번호 노출, 익명 Watchlist BOLA, CORS 전면 허용+Credentials, 하드코딩 이메일, DB_USER 기본값, `generate_screener_keywords` 인증 완전 비활성화 |
| MED | 7 | 기본 권한 `IsAuthenticatedOrReadOnly` 의존, LLM 프롬프트 인젝션 2건, 로그인 throttle 없음, 에러 스택 노출, 세션+JWT 병행, **`macro/sync` 익명 트리거(M-7 신규)** |
| LOW | 5 | `PublicUser` 열람, Neo4j 설정 중복, HealthCheck 예외 노출, 기본 `NewsViewSet` 권한, `gssencmode=disable` 운영 문서화 |
| INFO | 7 | `.env` gitignore ✅ + git history 미노출 ✅, SQL 4곳 모두 파라미터 바인딩 ✅, 비밀번호 검증기 4종 ✅, JWT rotation+blacklist ✅, `WatchlistViewSet` AnonRateThrottle ✅, **SSH 비밀키 차단 추가(I-7 신규)** ✅, **Alpha Vantage provider 제거(I-8 신규)** ✅ |

---

## 1. 인증/인가 (Authentication & Authorization)

### CRITICAL

#### C-3 `StockSyncAPIView` 인증 우회 (그대로)
- **위치**: `stocks/views.py:885-887`
  ```python
  class StockSyncAPIView(APIView):
      """공개 데이터 동기화이므로 인증 불필요"""
      permission_classes = []   # ← 명시적 공개
  ```
- **상태**: 4/24 동일. POST `/api/v1/stocks/sync/{symbol}/`이 비인증으로 FMP 외부 API 호출 트리거 → 쿼터 고갈/DoS.
- **권고**: `[IsAuthenticated]` + `UserRateThrottle 5/min`.

#### C-4 `serverless/views.py` 관리자/Celery 트리거 다수 공개 (그대로)
- **위치**: `serverless/views.py` — 80+ 엔드포인트가 `@permission_classes([AllowAny])`. 그 중 **쓰기·비용 발생** 10+개:

  | 라인 | 함수 | 위험 |
  |------|------|------|
  | 165 | `trigger_sync` | Celery `sync_daily_market_movers.delay()` |
  | 213 | `sync_now` | 동기 강제 동기화 |
  | 381 | `trigger_keyword_generation` | `keyword_generation_pipeline.delay()` (Gemini 비용) |
  | 446-448 | `generate_screener_keywords` | `@authentication_classes([])` + AllowAny — H-7 |
  | 780 | `trigger_breadth_sync` | Celery 호출 |
  | 967 | `trigger_heatmap_sync` | Celery 호출 |
  | 1373, 1437, 1493, 1528, 1577, 1608, 1644, 1757 | 키워드/관계 그래프/태그/Chain Sight 편집 8종 | 데이터 변조 |
  | 2308 | `trigger_etf_holdings_sync` | ETFHolding Celery 파이프라인 |
  | 2789 | `refresh_theme_matches_api` | ThemeMatch 재계산 |
  | 2987 | `sync_llm_relations_api` | LLM 관계 추출 (Gemini 비용) |

- **검증**: `grep -nE "TODO.*프로덕션" serverless/views.py` 결과 10건의 `# TODO: 프로덕션에서는 IsAdminUser/IsAuthenticated로 변경` 주석이 **모두 미반영 상태**.
- **권고**: 일괄 `IsAdminUser` 이관, `# TODO: 프로덕션` 주석 grep으로 PR 분리 추천.

### HIGH

#### H-4 `WatchlistViewSet` BOLA (그대로)
- **위치**: `chainsight/views/watchlist_views.py:26-46`
  ```python
  class WatchlistAnonThrottle(AnonRateThrottle): rate = '30/minute'
  class WatchlistViewSet(viewsets.ModelViewSet):
      permission_classes = [AllowAny]
      throttle_classes = [WatchlistAnonThrottle]
      ...
      qs = qs.filter(user__isnull=True)   # ← 익명 사용자 전원이 동일 풀
  ```
- **영향**: 비로그인 A의 `SavedPath`를 비로그인 B가 GET/DELETE/POST — `archive`/`resolve`/`recheck`/`expand`/`alternatives` 모두 동일.
- **완화**: AnonRateThrottle 30/min 활성(대량 스캔 차단).
- **권고**: `IsAuthenticated` 강제 또는 `request.session.session_key` 기반 분리. DELETE는 소유 검증 필수.

#### H-7 `generate_screener_keywords` 인증 완전 비활성화 (그대로)
- **위치**: `serverless/views.py:445-448`
  ```python
  @api_view(['POST'])
  @authentication_classes([])  # TODO: 프로덕션에서는 인증 추가
  @permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
  def generate_screener_keywords(request):
  ```
- **영향**: `@authentication_classes([])`이 **JWT 자체를 우회** — 추후 권한만 바꾼다고 `UserRateThrottle`이 식별되지 않음. 임의 symbol 배열을 즉시 Gemini로 보낼 수 있는 배치 경로.
- **권고**: 데코레이터 두 줄 모두 제거 + `[IsAdminUser]`. 입력 `stocks` 배열 길이 상한 명시.

### MED

#### M-1 기본 `IsAuthenticatedOrReadOnly` 의존 (그대로)
- **위치**: `config/settings.py:326-328`
- **명시 누락 뷰** (모두 GET 익명 허용 — 재무제표·스크리너·Chain Sight 그래프가 비회원 노출):
  - `validation/api/views.py`: `ValidationSummaryView`, `ValidationMetricsView`, `LeaderComparisonView`, `PresetListView`, `LLMPeerFilterView` (단, `PeerPreferenceView`는 `IsAuthenticatedOrReadOnly` 명시)
  - `sec_pipeline/views.py:FilingDataView`
  - `news/api/views.py:NewsViewSet` (클래스 레벨 미설정, 단 모든 `@action`은 명시)
  - `stocks/views_indicators.py` 3종, `stocks/views_eod.py` 3종
  - `stocks/views.py:StockSearchAPIView/StockChartDataAPIView/StockBalanceSheetAPIView/StockIncomeStatementAPIView/StockCashFlowAPIView/StockCompleteDataAPIView`
  - `stocks/views_search.py` 3종, `stocks/views_mvp.py` 4종
  - `chainsight/api/views.py` 7종 (`ChainSightGraphView`, `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 등)
- **권고**: 뷰 레벨에서 `[AllowAny]` 또는 `[IsAuthenticated]` 명시. 최소한 재무제표·LLM 사용 엔드포인트는 `[IsAuthenticated]`.

#### M-5 세션+JWT 동시 활성화 (그대로)
- **위치**: `config/settings.py:321-329`, `users/views.py:143-168`(`LogIn` Django 세션 로그인)
- **권고**: `DEFAULT_AUTHENTICATION_CLASSES`에서 `SessionAuthentication` 제거. `LogIn` 폐기, `users/jwt_views.py`로 일원화.

#### M-6 로그인 무제한 시도 (Credential Stuffing) (그대로)
- **위치**: `users/views.py:LogIn` (143-168), `users/jwt_views.py` 전체
- **증거**: `DEFAULT_THROTTLE_RATES` 미설정. `AnonRateThrottle` 적용 사례는 `chainsight/views/watchlist_views.py` 1건뿐.
- **권고**: `ScopedRateThrottle 5/min` + django-axes 도입.

#### M-7 `macro/sync/` 익명 POST → 백그라운드 스레드 트리거 (**신규**)
- **위치**: `macro/views.py:353-386`
  ```python
  class DataSyncView(APIView):
      permission_classes = [AllowAny]
      def post(self, request):
          ...
          thread = threading.Thread(target=_run_data_sync, daemon=True)
          thread.start()
  ```
- **영향**: `cache.get(SYNC_STATUS_KEY) == 'running'` 가드는 동시 1회만 막고, 익명 사용자가 작업 종료 직후 즉시 재트리거하여 거시경제 데이터 수집 사이클을 임의로 시작 가능. ASGI/Daphne 환경에서 OS 스레드 누적 위험 + provider 호출 비용 발생. 4/24 보고서가 누락.
- **권고**: `[IsAdminUser]` + `ScopedRateThrottle '1/hour'` (또는 Celery `rate_limit`). 수동 트리거가 필요하면 management command 권장.

### LOW

#### L-4 `PublicUser` 사용자 열람 (그대로)
- **위치**: `users/views.py:111-118`
- **권고**: `[IsAuthenticated]` 또는 `UserSerializer` 필드 축소.

---

## 2. SQL / NoSQL / Command Injection

### INFO (안전 확인)

`cursor.execute` 4곳 **전부 파라미터 바인딩 또는 정적 쿼리**. 인젝션 위험 없음.

| 파일 | 라인 | 형태 | 평가 |
|------|------|------|------|
| `chainsight/services/seed_selection.py:151-179` | CTE + JOIN | `%s` + `[market_date, market_date]` | ✅ |
| `serverless/services/admin_status_service.py:832-837` | `pg_stat_user_tables` 정적 쿼리 | 파라미터 없음 | ✅ |
| `api_request/admin_views.py:266` | `SELECT 1` | 정적 | ✅ |
| `config/views.py:90` | `SELECT 1` | 정적 | ✅ |

> 코드 리뷰 가드 제안: `cursor.execute(f"...")`/`.format(`/`% (variable)` 패턴 차단 (정규식 `cursor\.execute\(["'].*\{|cursor\.execute\(.*%\s*\(`).

Neo4j Cypher: `chainsight/api/views.py:118` 등 표본 확인 시 `$param` 프레이스홀더 사용. **전수 감사 후속 권고** (`chainsight/graph/`, `news/services/*neo4j*`, `rag_analysis/services/neo4j_*`).

---

## 3. LLM 프롬프트 인젝션

### MED

#### M-2 `rag_analysis/services/llm_service.py` 사용자 질문 직접 concat (그대로)
- **위치**: `rag_analysis/services/llm_service.py:173-186`
  ```python
  user_content = f"{context}\n\n질문: {question}"
  stream = await self.client.aio.models.generate_content_stream(
      model=self.MODEL, contents=user_content, config=config,
  )
  ```
- **평가**: `system_instruction` 분리는 적용. `question`(자유 입력)·`context`(DataBasket 요약, 사용자 영향) 모두 델리미터 이스케이프 없음.
- **권고**: `<user_query>...</user_query>` 고정 델리미터 + 동일 태그 이스케이프, `<suggestions>` 응답 화이트리스트 검증, 면책 조항 강제 삽입.

#### M-3 외부 뉴스 콘텐츠가 프롬프트로 흘러들어감 (그대로)
- **위치**:
  - `news/services/keyword_extractor.py:270-282` — `news['title']`, `news['summary'][:100]` f-string
  - `thesis/views/conversation_views.py:231` — `t["title"][:80]` 직접 삽입 (`NewsIssuesView._convert_to_korean_issues`)
  - `thesis/services/prompt_builder.py:625-673` — `article.title`, `article.content[:300]` 직접 삽입
  - 추가 표본(2026-04-25 검증): `thesis/services/thesis_builder.py:1673` — `f"""현재 가설: 제목="{state.collected.title}", 방향=..."""`
- **영향**: 뉴스 공급자 또는 사용자가 입력한 가설 제목이 프롬프트 변형 → 키워드/감성/가설이 오염되어 EOD·관제실 알림에 전파.
- **권고**: 제목/요약을 `<news index="1">...</news>` XML 블록으로 감싸고 동일 태그 이스케이프, 출력 JSON 스키마 검증, 제어문자/유니코드 bidi 필터링.

> 동일 리스크가 `news/services/news_deep_analyzer.py`, `news/services/stock_insights.py`, `serverless/services/keyword_generator*.py`, `serverless/services/llm_relation_extractor.py`, `rag_analysis/services/entity_extractor.py`에도 존재. 본 감사는 표본 4곳만 확인.

### 관찰 (방어 확인)

- `thesis/services/prompt_builder.py:428-450` — INDICATOR_CATALOG 외 지표 생성 금지 명시(환각 방지) + `response_schema` Structured Output.
- `thesis/views/conversation_views.py:26-74` — `_sanitize_conversation_state`/`_sanitize_llm_state`가 클라이언트 state 화이트리스트/타입 검증. 프로퍼티 인젝션 방어.

---

## 4. 시크릿 관리

### CRITICAL

#### C-1 하드코딩 `SECRET_KEY` (그대로)
- **위치**: `config/settings.py:140`
  ```python
  SECRET_KEY = 'django-insecure-hvwb-ms8%a@fh7_pf@obr@edq6(h41bj+$yetj#h!wg7#(b(&8'
  ```
- **추가 위협**: `SIMPLE_JWT.SIGNING_KEY = SECRET_KEY` (line 342) — **노출 = JWT 위조**, 세션 쿠키 서명·CSRF 토큰·비밀번호 리셋 토큰·signed URL 전부 영향권.
- **권고**: `os.getenv('DJANGO_SECRET_KEY')` 필수화 + 누락 시 `ImproperlyConfigured`. 즉시 rotate + JWT blacklist flush 필요.

### HIGH

#### H-2 Neo4j 기본 비밀번호 `stockvis123` (그대로)
- **위치**: `config/settings.py:32`, `config/settings.py:119` (중복 정의 — `NEO4J_PASSWORD` 두 번)
- **권고**: 기본값 제거, 누락 시 startup 실패. 중복 정의도 제거.

#### H-3 DB_USER 기본값 개인 OS 계정명 (그대로)
- **위치**: `config/settings.py:225` — `'USER': os.getenv('DB_USER', 'byeongjinjeong')`
- **영향**: 다른 환경(CI, 다른 개발자)이 의도치 않게 개인 DB에 접속 시도 + 개인 식별 노출.
- **권고**: 기본값 제거 또는 `postgres`.

#### H-6 `CELERY_ERROR_RECIPIENTS` 하드코딩 이메일 (그대로)
- **위치**: `config/settings.py:444-447`
  ```python
  CELERY_ERROR_RECIPIENTS = ['goid545@naver.com', 'jinie545@gmail.com']
  ```
- **권고**: `.env`에서 콤마 구분으로 로드, `settings.py` 기본값은 빈 리스트.

### INFO

#### I-1 `.env` gitignore 및 history 미노출 (확인)
- `.gitignore:10` `.env`, `.gitignore:138` 중복 명시(harmless), `.env.example`만 커밋.
- `git log --all -- .env` → 이력 없음.

#### I-7 SSH/비밀키 차단 패턴 추가 (**신규 — 2026-04-25 개선**)
- **커밋**: `d96e434` — `.gitignore` 21줄 추가
  ```
  **/id_rsa, **/id_dsa, **/id_ecdsa, **/id_ed25519
  **/*_rsa, **/*_ed25519, **/*_ecdsa
  *.pem, *.key, *.p12, *.pfx, *.crt, *.cer
  /dlswnl545*, /heaven545*  # 잘못된 위치에 생성된 OpenSSH 키 차단
  ```
- **평가**: 시크릿 위생 개선. `*.key` 패턴은 일부 정당한 자산(예: API key sample)을 차단할 수 있으니 false positive 모니터링 필요.

#### I-8 Alpha Vantage Provider 제거 (**신규 — 2026-04-25 개선**)
- **커밋**: `df85496 refactor: Alpha Vantage provider 전면 제거`
- **잔재**: `news/models.py:33,285` 및 `news/migrations/0005_*.py`의 `('alpha_vantage', 'Alpha Vantage')` enum 라벨만 남음(런타임 보안 영향 없음).
- **평가**: 외부 의존 1종 제거 → 공격 표면 축소(쿼터 고갈·키 유출 표면 -1).

---

## 5. CORS / XSS / 에러 메시지 노출

### CRITICAL

#### C-2 `DEBUG = True` (그대로)
- **위치**: `config/settings.py:143`
- **연쇄 영향**: 500 에러 시 settings·쿼리·트레이스백 풀 노출 + `CORS_ALLOW_ALL_ORIGINS=True` 자동 활성(L289-291) + `ALLOWED_HOSTS=[]`와 결합 Host Header Injection.
- **권고**: `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'`. 가능하면 `settings_prod.py` 분리.

### HIGH

#### H-1 `ALLOWED_HOSTS = []` (그대로)
- **위치**: `config/settings.py:145`
- **위협**: DEBUG=False 전환 시 모든 요청이 DisallowedHost. DEBUG=True 상태에서는 Host Header Injection으로 비밀번호 리셋 링크 변조 가능.
- **권고**: `ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')`.

#### H-5 `CORS_ALLOW_ALL_ORIGINS=True` + `CORS_ALLOW_CREDENTIALS=True` (그대로)
- **위치**: `config/settings.py:289-297`
- **위협**: DEBUG 분기로 자동 활성. `CORS_ALLOW_CREDENTIALS=True`는 분기 무관하게 항상 True → 모든 origin이 쿠키/Authorization 첨부 요청 가능. M-5(세션+JWT 병행)과 결합 시 실제 리스크 상승.
- **권고**: `CORS_ALLOWED_ORIGIN_REGEX = r'^http://localhost:\d+$'` 등 화이트리스트로 대체.

### MED

#### M-4 에러 응답에 예외 문자열 반환 (그대로)
- **위치 표본**:
  - `api_request/admin_views.py:68-70, 87-90, 109-114, 131-135, 161-165, 208-212, 237-240, 272-275, 289-292, 302-306`
  - `config/views.py:85-93, 96-104`
  - `stocks/views.py:965-975`
  - `serverless/views.py:201-208, 434-442` 외 다수
- **위협**: `Response({"error": str(e)}, status=500)`. DEBUG=True 조합 시 풀 트레이스백 + 내부 경로 노출.
- **권고**: `{"error": "internal_error", "trace_id": "..."}` 표준 + `logger.exception`. DRF `EXCEPTION_HANDLER` 중앙화.

### LOW

#### L-5 `HealthCheckView` 공개 + 예외 노출 (그대로)
- **위치**: `api_request/admin_views.py:243-308` — `permission_classes = []`. DB/Redis/Provider 실패 시 `str(e)` 반환 가능.
- **권고**: 헬스체크 자체 공개는 허용 가능. 단, 컴포넌트별 에러 디테일은 은닉(예: status만, error 필드 제거).

---

## 6. 기타 관찰

### LOW

- **L-2 `gssencmode=disable` 하드코딩**: `config/settings.py:231` — macOS fork 크래시 회피. 프로덕션 PostgreSQL `sslmode=require` 분리 문서화 필요.
- **L-3 Neo4j 설정 중복 정의**: settings.py L30-32 vs L117-119 — `NEO4J_USER` vs `NEO4J_USERNAME` 변수명 혼재. 한쪽이 오버라이드되어 변경 시 실수 유발.
- **L-1 `NewsViewSet` 클래스 레벨 권한 미명시**: `news/api/views.py:42` — 모든 `@action`은 명시되어 동작 안전. 가독성 위해 클래스 레벨 명시 권장.

### INFO (안전 확인)

- **I-2 SQL 4곳 파라미터 바인딩** (§2 참조).
- **I-3 비밀번호 검증기 4종**: `AUTH_PASSWORD_VALIDATORS` (유사/최소길이/일반/숫자전용) 활성.
- **I-4 JWT 모범 구성**: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, `UPDATE_LAST_LOGIN=True`. ACCESS 60분 / REFRESH 7일.
- **I-5 `WatchlistViewSet` Throttle**: `AnonRateThrottle 30/min` 적용. BOLA는 여전하지만 대량 크롤 완화.
- **I-6 thesis state sanitize**: `_sanitize_conversation_state`/`_sanitize_llm_state` 화이트리스트 동작 확인.
- **I-7 SSH/비밀키 gitignore 강화** (§4 참조, 2026-04-25 신규).
- **I-8 Alpha Vantage Provider 제거** (§4 참조, 2026-04-25 신규).

### 신규 앱 — `portfolio/` 보안 평가

- 앱 구성: `models.py`, `schemas/`, `prompts/`, `metrics/`, `tests/`, `migrations/0001_initial.py`만 존재.
- **`views.py`/`urls.py` 부재** → 현재 외부에 노출되는 API 엔드포인트 없음. URL 라우터 미등록.
- 향후 `views.py` 생성 시 다음 점검 필수:
  1. `permission_classes` 명시(기본값 의존 금지).
  2. LLM 호출 prompt 빌더(`portfolio/prompts/`)가 사용자 입력을 직접 concat할 경우 §3 가이드 적용.
  3. 입력 schema(`portfolio/schemas/`) 검증이 boundary에서 강제되는지 확인.

---

## 7. 우선순위 조치 권고 (Top 9)

1. **[CRITICAL] C-1 `SECRET_KEY` 즉시 rotate** + `.env` 로드 전환, JWT 전체 강제 만료.
2. **[CRITICAL] C-2 `DEBUG=False` 환경변수화** → H-1 `ALLOWED_HOSTS`, H-5 CORS 동반 수정.
3. **[CRITICAL] C-3 `StockSyncAPIView` 인증 추가** — `IsAuthenticated` + `UserRateThrottle`.
4. **[CRITICAL] C-4 `serverless/views.py` 관리자 엔드포인트 일괄 보호** — `# TODO: 프로덕션` 주석 10건 일괄 PR.
5. **[HIGH] H-2/H-3 Neo4j·DB 기본값 제거** + Neo4j 중복 정의(L-3) 정리, 누락 시 startup 실패.
6. **[HIGH] H-4 `WatchlistViewSet` 권한 변경** — `IsAuthenticated` 또는 session_key 기반 분리.
7. **[HIGH] H-7 `generate_screener_keywords` 인증 데코레이터 제거** + `IsAdminUser`, 배치 크기 상한.
8. **[MED] M-7 `macro/sync` 익명 POST 차단** (신규) — `IsAdminUser` + ScopedRateThrottle.
9. **[MED] M-2/M-3 LLM 프롬프트 델리미터/입력 sanitization** + M-6 로그인 throttle + M-5 세션 인증 제거로 인증 흐름 일원화.

---

## 8. 감사 범위 외 / 후속 조사 제안

- **Neo4j Cypher 인젝션 전수조사**: `chainsight/graph/`, `rag_analysis/services/neo4j_*`, `news/services/*neo4j*` 전 쿼리 `$param` 여부.
- **Celery 태스크 입력 검증**: `*/tasks.py` 외부 입력 신뢰(티커 화이트리스트) 재확인.
- **WebSocket(`*/consumers.py`) 권한**: Channels 레이어와 JWT 연결 검증.
- **업로드/파싱 경로**: `serverless/services/csv_url_resolver.py`, XLSX 파서(`PK\x03\x04`) ZIP slip / 경로 탐색.
- **`serverless/views.py` 3300+ 줄 권한 매트릭스화**: 어떤 GET은 공개 유지, 어떤 POST/DELETE는 관리자 전환 필요한지 URL 매핑 표.
- **LLM 전수 프롬프트 인젝션 감사**: `rag_analysis/services/entity_extractor.py`, `news/services/news_deep_analyzer.py`, `serverless/services/llm_relation_extractor.py`, `serverless/services/keyword_generator*.py`, **`thesis/services/thesis_builder.py:1673` 등 thesis 빌더**.
- **`portfolio/` 앱 views 출현 시점 재감사** (현재는 API 미노출 상태).

---

**감사 수행 방식**: 정적 코드 분석·`git diff HEAD~5 HEAD`·grep만 수행. 실행/네트워크 테스트·시크릿 rotation·코드 수정은 일절 수행하지 않음.

**본 보고서가 베이스라인(2026-04-24) 대비 추가/수정한 항목**:
- §0 베이스라인 대비 변동 요약 신설(diff 기반).
- M-7 `macro/sync` 익명 POST → 백그라운드 스레드 트리거 **신규 발견**.
- I-7 SSH/비밀키 gitignore 강화 **개선 확인**.
- I-8 Alpha Vantage provider 제거 **개선 확인**.
- §6 신규 `portfolio/` 앱 보안 평가 추가 (현재 API 미노출).
- M-3에 `thesis/services/thesis_builder.py:1673` 표본 1건 추가.
