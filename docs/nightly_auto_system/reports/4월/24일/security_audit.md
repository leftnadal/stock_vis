# 보안 감사 보고서 — Stock-Vis

- **감사일**: 2026-04-24
- **브랜치**: portfolio
- **범위**: OWASP Top 10 (인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿, CORS/XSS/에러 노출)
- **모드**: 읽기 전용 — 코드 수정 없음
- **근거 파일**: `config/settings.py`, 뷰 24개 파일 (`**/views*.py` + `thesis/views/*.py` + `chainsight/views/*.py`), `cursor.execute` 4곳, Gemini 호출 핵심 경로(`rag_analysis/services/llm_service.py`, `news/services/keyword_extractor.py`, `thesis/services/prompt_builder.py`, `thesis/views/conversation_views.py`)

## 요약 (Severity 분포)

| 등급 | 건수 | 대표 이슈 |
|------|------|----------|
| CRITICAL | 4 | 하드코딩 `SECRET_KEY`(JWT 서명 공용), `DEBUG=True`, `StockSyncAPIView permission_classes=[]`, **`serverless/views.py` 관리자/Celery 트리거 다수 공개** |
| HIGH | 7 | `ALLOWED_HOSTS=[]`, Neo4j 기본 비밀번호 노출, 익명 Watchlist BOLA, CORS 전면 허용(+Credentials), 하드코딩 이메일, DB_USER 기본값, `generate_screener_keywords` 인증 완전 비활성화 |
| MED | 6 | 기본 권한 `IsAuthenticatedOrReadOnly` 의존, LLM 프롬프트 인젝션 2건, 로그인 throttle 없음, 에러 스택 노출, 세션+JWT 병행, serverless 공개 엔드포인트 비용 확대 |
| LOW | 5 | `PublicUser` 열람, Neo4j 설정 중복, HealthCheck 예외 노출, 기본 `NewsViewSet` 권한, `gssencmode=disable` 운영 문서화 |
| INFO | 5 | `.env` gitignore ✅ · git history 미노출 ✅, SQL 인젝션 4곳 모두 파라미터 바인딩 ✅, 비밀번호 검증기 4종 활성 ✅, JWT rotation+blacklist ✅, `WatchlistViewSet`에 `AnonRateThrottle 30/min` 적용 ✅ |

---

## 1. 인증/인가 (Authentication & Authorization)

### CRITICAL

#### C-3 `StockSyncAPIView` 인증 우회 (명시적 무권한)
- **위치**: `stocks/views.py:878-886`
  ```python
  class StockSyncAPIView(APIView):
      """공개 데이터 동기화이므로 인증 불필요"""
      permission_classes = []   # ← 명시적 공개
  ```
- **영향**: POST `/api/v1/stocks/sync/{symbol}/` 가 인증 없이 FMP/Alpha Vantage 외부 API 호출을 트리거 → 공격자가 임의 심볼 루프로 **유료 API 쿼터 고갈 + 서비스 거부**.
- **증거**: 라인 917의 `check_rate_limit('fmp')`는 FMP 전역 rate limit 체크일 뿐 IP/사용자 단위 제한 아님 → 정상 사용자까지 동반 차단.
- **권고**: `permission_classes = [IsAuthenticated]` + `UserRateThrottle`(예: `5/min`) 조합.

#### C-4 `serverless/views.py` — 관리자/Celery 트리거 다수 공개 (**신규 발견**)
- **위치**: `serverless/views.py` — 80+ 엔드포인트가 `@permission_classes([AllowAny])` + `@authentication_classes([])`. 이 중 10개가 **쓰기·비용 발생 관리자 작업**임.

  | 라인 | 함수 | 작업 내용 | 주석 |
  |------|------|----------|------|
  | 165-166 | `trigger_sync` | `sync_daily_market_movers.delay()` Celery 호출 | `# TODO: 프로덕션에서는 IsAdminUser로 변경` |
  | 213-214 | `sync_now` | 동기화 강제 트리거 | `# TODO: 프로덕션에서는 IsAdminUser로 변경` |
  | 381-382 | `trigger_keyword_generation` | `keyword_generation_pipeline.delay()` (Gemini 유료 호출) | `# TODO: 프로덕션에서는 IsAdminUser로 변경` |
  | 446-448 | `generate_screener_keywords` | `@authentication_classes([])` + AllowAny, 배치 LLM 키워드 | `# TODO: 프로덕션에서는 인증 추가` |
  | 780-781 | `trigger_breadth_sync` | `calculate_daily_market_breadth.delay()` | `# TODO` |
  | 967-968 | `trigger_heatmap_sync` | heatmap Celery 재계산 | `# TODO` |
  | 1373, 1437, 1493, 1528, 1577, 1608, 1644 | 키워드/관계 그래프 · 태그 편집 엔드포인트 7종 | 데이터 생성/수정 | `# TODO: 프로덕션에서는 IsAuthenticated로 변경` |
  | 1757 | Chain Sight 관련 데이터 수정 | | `# TODO` |
  | 2308 | `trigger_etf_holdings_sync` | ETFHolding Celery 파이프라인 | (주석 없음, AllowAny) |
  | 2789 | `refresh_theme_matches_api` | ThemeMatch 재계산 | AllowAny |
  | 2987 | `sync_llm_relations_api` | LLM 관계 추출 Celery 호출 (Gemini 비용) | AllowAny |

- **영향**:
  1. **유료 API/LLM 비용 고갈** — 외부(비인증) 공격자가 FMP Starter/Gemini 쿼터를 소진 가능.
  2. **서비스 거부** — `force=true`·임의 날짜 파라미터로 워커 점유.
  3. **데이터 오염** — 편집성 엔드포인트가 익명에게 열려 테마/관계 그래프·키워드 레코드 조작 가능.
- **권고**: 해당 관리자 엔드포인트에 일괄 `IsAdminUser` 적용(또는 `IsAuthenticated` + 관리자 체크). 읽기 전용 공개 엔드포인트(`market_breadth_history` 등)와 분리된 URL 접두사 권장(`/api/v1/serverless/admin/*`). `# TODO` 주석 문자열 grep으로 일괄 이관 가능.

### HIGH

#### H-4 `WatchlistViewSet` — 익명 Watchlist 공유 (BOLA)
- **위치**: `chainsight/views/watchlist_views.py:26-46`
  ```python
  class WatchlistAnonThrottle(AnonRateThrottle):
      rate = '30/minute'

  class WatchlistViewSet(viewsets.ModelViewSet):
      permission_classes = [AllowAny]
      throttle_classes = [WatchlistAnonThrottle]
      ...
      def get_queryset(self):
          user = self.request.user if self.request.user.is_authenticated else None
          if user:
              qs = qs.filter(user=user)
          else:
              qs = qs.filter(user__isnull=True)   # ← 익명 사용자 전원이 동일 버킷
  ```
- **영향**: 비로그인 사용자 A가 저장한 `SavedPath`를 비로그인 사용자 B가 GET/DELETE/POST 할 수 있음. `archive`/`resolve`/`recheck`/`expand`/`alternatives` 모든 `@action`이 동일한 익명 풀에서 동작 → IDOR/BOLA.
- **완화 인자**: `AnonRateThrottle 30/minute` 걸려 있어 대량 스캔은 속도 제한됨(**기존 보고서 대비 정확도 수정**).
- **권고**: `IsAuthenticated` 강제 또는 `request.session.session_key` 기반 분리. DELETE는 소유 검증 필수.

#### H-7 `generate_screener_keywords` — 인증 완전 비활성화 (**신규 발견**)
- **위치**: `serverless/views.py:445-448`
  ```python
  @api_view(['POST'])
  @authentication_classes([])  # TODO: 프로덕션에서는 인증 추가
  @permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAdminUser로 변경
  def generate_screener_keywords(request):
      """스크리너 종목들의 AI 키워드 일괄 생성 (Celery 비동기)"""
  ```
- **영향**: C-4와 중복되지만 `@authentication_classes([])`로 **JWT 자체를 무시** — 설령 throttle/permission이 바뀌어도 토큰 없는 호출을 인식하지 못해 `UserRateThrottle`이 무력화됨. 임의 symbol 배열 수백 개를 즉시 Gemini로 보낼 수 있는 배치 경로.
- **권고**: `@authentication_classes([])` 제거 + `[IsAdminUser]` 또는 `[IsAuthenticated, IsAdminUser]`. 배치 크기(`stocks` 배열) 상한 명시(현재는 무제한).

### MED

#### M-1 기본 `IsAuthenticatedOrReadOnly` 의존
- **위치**: `config/settings.py:337-339` — `DEFAULT_PERMISSION_CLASSES = ['IsAuthenticatedOrReadOnly']`
- **미설정(기본값) 뷰**: `validation/api/views.py` 5종 중 4종(프리셋/필터/요약/메트릭), `sec_pipeline/views.py:FilingDataView`, `news/api/views.py:NewsViewSet`(상속, 단 개별 `@action`은 오버라이드됨), `stocks/views_indicators.py` 3종, `stocks/views_eod.py` 3종, `stocks/views.py:StockSearchAPIView/StockChartDataAPIView/StockBalanceSheetAPIView/StockIncomeStatementAPIView/StockCashFlowAPIView/StockCompleteDataAPIView`, `stocks/views_search.py` 3종, `stocks/views_mvp.py` 4종, `chainsight/api/views.py` 7종(`SeedListView`, `ChainSightGraphView` 등).
- **영향**: 전부 GET 미인증 허용. 프리미엄 FMP 응답·재무제표·Chain Sight 관계 그래프가 비회원에 공개. 비즈니스적 가치 데이터 보호 정책 필요.
- **권고**: 뷰마다 `permission_classes` 명시(`[AllowAny]` 또는 `[IsAuthenticated]`). 최소한 재무제표(`StockBalanceSheetAPIView`, `StockIncomeStatementAPIView`, `StockCashFlowAPIView`, `AllFundamentalsView 계열`)는 `IsAuthenticated` 검토.

#### M-5 세션+JWT 동시 활성화
- **위치**: `config/settings.py:331-340`
- **영향**: 세션 인증은 CSRF 필수, JWT는 CSRF 우회 → 두 인증 수용 시 세션 로그인 사용자 토큰이 CSRF로 탈취될 수 있고, SimpleJWT 블랙리스트와 Django 세션 관리가 이원화되어 로그아웃 일관성 붕괴. `users/views.py:143`의 `LogIn`이 Django 세션 로그인을 계속 사용 중.
- **권고**: REST API는 JWT만 남기고 세션 인증 제거. `LogIn`(`users/views.py:143-168`) 대신 `users/jwt_views.py` 기반으로 일원화.

#### M-6 `LogIn`/`jwt login` 엔드포인트 무제한 시도 (Credential Stuffing)
- **위치**: `users/views.py:143-168`, `users/jwt_views.py` (throttle 미설정)
- **증거**: 전역 `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` 미설정. `AnonRateThrottle` 적용 뷰는 `chainsight/views/watchlist_views.py` 1건뿐.
- **권고**: `AnonRateThrottle` (예: `5/min`) + 실패 카운터(django-axes) 도입. REST Framework 설정에 `DEFAULT_THROTTLE_RATES = {'login': '5/min'}` + 해당 뷰에 `throttle_classes = [ScopedRateThrottle]`.

### LOW

#### L-4 `PublicUser` 사용자 열람
- **위치**: `users/views.py:111-118` — GET `/users/{username}` 으로 존재 확인 + `UserSerializer` 응답.
- **영향**: Username Enumeration. ID/닉네임 기반 소셜 엔지니어링 유도 가능.
- **권고**: `permission_classes = [IsAuthenticated]` 또는 serializer 필드 축소(이름/프로필만).

---

## 2. SQL / NoSQL / Command Injection

### INFO (안전 확인)

`cursor.execute` 사용처 **4곳 전부 파라미터 바인딩** — 인젝션 위험 없음.

| 파일 | 라인 | 형태 | 평가 |
|------|------|------|------|
| `chainsight/services/seed_selection.py:151-179` | CTE + JOIN | `%s` + `[market_date, market_date]` | ✅ |
| `serverless/services/admin_status_service.py:832-837` | 정적 쿼리 (`pg_stat_user_tables`) | 파라미터 없음, 하드코딩 | ✅ |
| `api_request/admin_views.py:266` | `SELECT 1` | 하드코딩 | ✅ |
| `config/views.py:90` | `SELECT 1` | 하드코딩 | ✅ |

> 체크리스트 추가 제안: 코드 리뷰 시 `cursor.execute(f"..."`) 또는 `.format(` / `% (variable)` 패턴 차단.

Neo4j Cypher 쿼리는 `$param` 프레이스홀더 사용 확인(예: `chainsight/api/views.py:118`). 전수 검사 권고(아래 §7).

---

## 3. LLM 프롬프트 인젝션

### MED

#### M-2 `rag_analysis/services/llm_service.py` — 사용자 질문 직접 concat
- **위치**: L173-186
  ```python
  user_content = f"{context}\n\n질문: {question}"
  stream = await self.client.aio.models.generate_content_stream(
      model=self.MODEL,
      contents=user_content,
      config=config,   # system_instruction 별도
  )
  ```
- **평가**: `system_instruction`으로 시스템 프롬프트를 분리(난이도 상승). 그러나 `question`은 사용자 자유 제어, `context`(DataBasket 요약)에도 사용자 입력이 유입 가능. 델리미터 이스케이프/sanitization 없음 → 면책 조항 우회, `<suggestions>` 태그 조작 등 가능.
- **권고**: (1) `<user_query>...</user_query>` 고정 델리미터 + 동일 태그 입력 시 이스케이프, (2) `<suggestions>` 파싱 시 길이/심볼 화이트리스트 검증, (3) 면책 조항은 응답 검증 단계에서 강제 삽입.

#### M-3 외부 뉴스 콘텐츠가 프롬프트로 흘러들어감
- **위치**:
  - `news/services/keyword_extractor.py:270-282` — `news['title']`, `news['summary'][:100]` f-string.
  - `thesis/views/conversation_views.py:231` (`NewsIssuesView._convert_to_korean_issues`) — `t["title"][:80]` 직접 삽입.
  - `thesis/services/prompt_builder.py:625-673` (`build_question_answer_prompt`) — `article.title`, `article.content[:300]` 직접 삽입.
- **영향**: 뉴스 공급자(Finnhub/Marketaux) 또는 악의적 기사 작성자가 제어 가능한 제목이 프롬프트를 변형 → 잘못된 키워드/감성/가설이 저장되어 다운스트림(EOD, Thesis Control, 관제실 알림)이 오염.
- **권고**: (1) 제목/요약을 `<news index="1">...</news>` XML 블록으로 감싸고 동일 태그 이스케이프, (2) 출력 JSON 스키마 검증(`symbol` 정규식, 감성 enum), (3) 제어문자/유니코드 bidi 필터링.

> 동일 리스크가 `news/services/news_deep_analyzer.py`, `news/services/stock_insights.py`, `serverless/services/keyword_generator*.py`, `serverless/services/llm_relation_extractor.py`, `rag_analysis/services/entity_extractor.py` 등에도 존재. 본 감사는 샘플 3곳 확인. 전체 검토 별도 티켓 권고.

### 관찰 (방어 확인)
- `thesis/services/prompt_builder.py:428-450`은 INDICATOR_CATALOG 외 지표 생성 금지를 명시(환각 방지), `response_schema` Structured Output 적용.
- `thesis/views/conversation_views.py:26-74`의 `_sanitize_conversation_state`·`_sanitize_llm_state`가 클라이언트 state 필드를 화이트리스트/타입 검증. state 주입 경로는 방어되어 있음.

---

## 4. 시크릿 관리

### CRITICAL

#### C-1 하드코딩 `SECRET_KEY`
- **위치**: `config/settings.py:151`
  ```python
  SECRET_KEY = 'django-insecure-hvwb-ms8%a@fh7_pf@obr@edq6(h41bj+$yetj#h!wg7#(b(&8'
  ```
- **추가 영향**: 같은 값이 `SIMPLE_JWT.SIGNING_KEY`로 재사용(L353) → **SECRET_KEY 노출 = 모든 JWT 위조 가능**. 세션 쿠키 서명, CSRF 토큰, 비밀번호 리셋 토큰, signed URL 전부 영향권.
- **권고**: `SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')` + 누락 시 `ImproperlyConfigured`. 커밋된 값은 즉시 rotate, JWT blacklist flush로 전체 재로그인 유도.

### HIGH

#### H-2 Neo4j 기본 비밀번호 `stockvis123`
- **위치**: `config/settings.py:33`, `config/settings.py:130` (중복 정의)
  ```python
  NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'stockvis123')
  ```
- **영향**: `.env` 누락 환경에서 기본 비밀번호가 약한 값으로 고정. Docker/CI/CD 기본값이 프로덕션까지 전파될 위험.
- **권고**: 기본값 제거, 누락 시 `ImproperlyConfigured`.

#### H-3 DB_USER 기본값 `byeongjinjeong` (개인 계정명)
- **위치**: `config/settings.py:236` — `'USER': os.getenv('DB_USER', 'byeongjinjeong')`
- **영향**: 개인 OS 사용자명이 기본값. `MEMORY.md`에 ".env에 DB_* 없음(settings 기본값 의존)"이 명시되어 있어 현재 워크플로우가 이 값을 실제로 사용. 다른 개발자/CI 환경에서 의도치 않게 개인 DB에 접속 시도 가능 + 개인 식별 노출.
- **권고**: `DB_USER` 기본값 제거, `.env` 필수화 또는 `postgres`로 변경.

#### H-6 `CELERY_ERROR_RECIPIENTS` 하드코딩 이메일
- **위치**: `config/settings.py:455-458`
  ```python
  CELERY_ERROR_RECIPIENTS = [
      'goid545@naver.com',
      'jinie545@gmail.com',
  ]
  ```
- **영향**: 개인 이메일이 공개/사설 저장소에 평문 노출. 피싱/스팸 타깃. 운영자 변경 시 리포지토리 수정 필요.
- **권고**: `.env`의 `CELERY_ERROR_RECIPIENTS`(콤마 구분) 로드로 전환, `settings.py` 기본값은 빈 리스트.

### INFO

#### I-1 `.env` gitignore 및 git history 미노출
- `.gitignore` L9 `.env` 포함, `.env.example`만 커밋.
- `git log --all --oneline -- .env` → 이력 없음 (이번 감사 시점 확인). `.env`는 로컬 워킹트리에만 존재(size 1777 bytes, mtime 2026-04-01).

---

## 5. CORS / XSS / 에러 메시지 노출

### CRITICAL

#### C-2 `DEBUG = True`
- **위치**: `config/settings.py:154`
- **영향**: (1) 500 에러 시 Django 기술 예외 페이지가 settings·쿼리·트레이스백 노출, (2) `CORS_ALLOW_ALL_ORIGINS = True`가 자동 활성화(L300-302), (3) `ALLOWED_HOSTS = []`와 결합하여 임의 호스트 헤더 접근 가능(Host Header Injection).
- **권고**: `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'`. 프로덕션 명시적 False + `settings_prod.py` 분리 고려.

### HIGH

#### H-1 `ALLOWED_HOSTS = []`
- **위치**: `config/settings.py:156`
- **영향**: DEBUG=False 전환 시 모든 요청이 DisallowedHost로 차단되어 배포 직후 장애. DEBUG=True 상태에서는 Django가 `localhost`, `127.0.0.1`, `[::1]`만 내부적으로 허용하지만 Host Header Injection을 통한 비밀번호 리셋 링크 변조 가능성.
- **권고**: `ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')` 처럼 환경변수화.

#### H-5 `CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True`
- **위치**: `config/settings.py:300-308`
- **영향**: DEBUG=True 분기로 자동 활성. `CORS_ALLOW_CREDENTIALS=True`는 DEBUG와 무관하게 항상 True이므로, 모든 오리진에서 쿠키/Authorization 첨부 요청 가능 → CSRF/세션 탈취, JWT XHR 탈취. 세션 인증 병행(M-5)과 결합 시 실제 리스크 상승.
- **권고**: DEBUG이라도 `CORS_ALLOW_ALL_ORIGINS` + `CORS_ALLOW_CREDENTIALS` 동시 True 금지. 개발 환경에서도 `CORS_ALLOWED_ORIGIN_REGEX = r'^http://localhost:\d+$'` 권장.

### MED

#### M-4 에러 응답에 예외 문자열 반환
- **위치**:
  - `api_request/admin_views.py:68-70, 87-90, 109-114, 131-135, 161-165, 208-212, 237-240, 272-275, 289-292, 302-306`
  - `config/views.py:85-93, 96-104`
  - `stocks/views.py:965-975`
  - `serverless/views.py:201-208, 434-442, ...` 다수
- **영향**: `Response({"error": str(e)}, status=500)` 패턴. DEBUG=True에서는 풀 스택트레이스. 내부 경로·라이브러리 버전·SQL 단편 유출.
- **권고**: 클라이언트에는 `{"error": "internal_error", "trace_id": "..."}` 형태만, 실제 예외는 `logger.exception`. DRF `EXCEPTION_HANDLER` 중앙화.

### LOW

#### L-5 `HealthCheckView` 공개 + 예외 노출
- **위치**: `api_request/admin_views.py:243-308` — `permission_classes = []` 주석상 공개, 실패 시 `str(e)` 반환.
- **영향**: 외부에서 내부 DB/Redis/Provider 스택 파악 가능. 헬스체크 공개 자체는 허용 가능하지만 에러 디테일은 은닉해야 함.

---

## 6. 기타 관찰

### LOW

- **L-2 `gssencmode=disable` 하드코딩**: `config/settings.py:242` — macOS fork 크래시 회피용. 프로덕션 PostgreSQL SSL(`sslmode=require`) 설정 문서화 필요.
- **L-3 Neo4j 설정 중복 정의**: L31-33 vs L128-131 — `NEO4J_USER` vs `NEO4J_USERNAME` 변수명 혼재. 한쪽이 오버라이드되어 변경 시 실수 유발.
- **L-1 `NewsViewSet` 권한 미명시**: `news/api/views.py:42` — 클래스 레벨 `permission_classes` 없음(기본값 의존). 다만 모든 `@action`은 명시(`AllowAny`/`IsAuthenticated`/`IsAdminUser`) → 현재 동작은 안전. 가독성 위해 클래스 레벨 명시 권장.

### INFO (안전 확인)

- **I-2 SQL 인젝션 4곳 파라미터 바인딩** (§2 참조).
- **I-3 비밀번호 검증기 4종** (`AUTH_PASSWORD_VALIDATORS`: 유사/최소길이/일반/숫자전용) 활성.
- **I-4 JWT**: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, `UPDATE_LAST_LOGIN=True` — 모범 구성. ACCESS 60분 / REFRESH 7일.
- **I-5 `WatchlistViewSet` Throttle**: `AnonRateThrottle` 30/min 적용(기존 보고서 미반영 수정). BOLA는 여전하지만 대량 크롤 완화.
- **I-6 `thesis conversation_views` state sanitize**: 화이트리스트 기반 `_sanitize_conversation_state` / `_sanitize_llm_state` 동작 확인. 프로퍼티 인젝션 방어.

---

## 7. 우선순위 조치 권고 (Top 8)

1. **[CRITICAL] C-1 `SECRET_KEY` 즉시 rotate** + `.env` 로드 전환, JWT 전체 세션 강제 만료.
2. **[CRITICAL] C-2 `DEBUG=False` 환경변수화** → H-1 `ALLOWED_HOSTS`, H-5 `CORS_ALLOW_ALL_ORIGINS` 동반 수정.
3. **[CRITICAL] C-3 `StockSyncAPIView` 인증 추가** — `IsAuthenticated` + `UserRateThrottle`.
4. **[CRITICAL] C-4 `serverless/views.py` 관리자 엔드포인트 일괄 보호** — `# TODO: 프로덕션에서는 IsAdminUser로 변경` 주석 10+ 개를 실제로 `IsAdminUser`로 이관. `@authentication_classes([])` 제거(H-7 포함).
5. **[HIGH] H-2/H-3 Neo4j·DB 기본값 제거**, 누락 시 startup 실패 유도.
6. **[HIGH] H-4 `WatchlistViewSet` 권한 변경** — `IsAuthenticated` 또는 session_key 분리(BOLA 차단).
7. **[MED] M-6 로그인 Throttle 적용** (`LogIn`, `jwt login`) + M-5 세션 인증 제거로 인증 흐름 일원화.
8. **[MED] M-2/M-3 LLM 프롬프트 델리미터/입력 sanitization 도입** — 사용자 질문, 뉴스 제목·본문 경로.

---

## 8. 감사 범위 외 / 후속 조사 제안

- **Neo4j Cypher 인젝션 전수조사**: `chainsight/graph/`, `rag_analysis/services/neo4j_*`, `news/services/*neo4j*` 전 쿼리 `$param` 여부.
- **Celery 태스크 입력 검증**: `*/tasks.py` 전체 외부 입력 신뢰(티커 화이트리스트) 재확인.
- **WebSocket (`*/consumers.py`) 권한 검사**: Channels 레이어와 JWT 연결 검증.
- **업로드/파싱 경로**: `serverless/services/csv_url_resolver.py`, XLSX 파서(`PK\x03\x04`) 경로의 ZIP slip/경로 탐색.
- **`serverless/views.py` 3300+ 줄 개별 권한 매트릭스화**: 어떤 GET은 공개 유지, 어떤 POST/DELETE는 관리자 전환 필요한지 URL 매핑 표 작성.
- **LLM 전수 프롬프트 인젝션 감사**: `rag_analysis/services/entity_extractor.py`, `news/services/news_deep_analyzer.py`, `serverless/services/llm_relation_extractor.py`, `serverless/services/keyword_generator*.py` 등.

---

**감사 수행 방식**: 코드 정적 분석 및 파일 읽기만 수행. 실행/네트워크 테스트·비밀 rotation·코드 수정은 **일체 수행하지 않음**. `git log --all -- .env` 이력 조회는 수행(결과: 없음).

**본 보고서 대비 이전 버전에서 수정된 항목**:
- C-4, H-7(serverless 관리자 엔드포인트) **신규 CRITICAL/HIGH 추가**.
- H-4 `WatchlistViewSet`에 throttle 30/min 적용 사실 반영(완화 인자).
- I-5, I-6 안전 확인 추가(WatchlistViewSet throttle, thesis state sanitize).
- M-1 미설정 뷰 목록에서 `news/api/views.py:NewsViewSet`은 실제로는 `@action` 오버라이드로 방어됨을 명시.
