# 보안 감사 보고서 — Stock-Vis

- **감사일**: 2026-04-24
- **범위**: OWASP Top 10 (인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿, CORS/XSS/에러 노출)
- **모드**: 읽기 전용 — 코드 수정 없음
- **근거 파일**: Django settings, DRF 뷰 17+ 파일, `cursor.execute` 4곳, Gemini 호출 55개 파일 중 핵심 경로

## 요약 (Severity 분포)

| 등급 | 건수 | 대표 이슈 |
|------|------|----------|
| CRITICAL | 3 | 하드코딩 `SECRET_KEY` (JWT 서명 공용), `DEBUG=True`, `StockSyncAPIView permission_classes=[]` |
| HIGH | 6 | `ALLOWED_HOSTS=[]`, Neo4j 기본 비밀번호 노출, 익명 Watchlist BOLA, CORS 전면 허용, 하드코딩 이메일, DB_USER 기본값 |
| MED | 6 | 기본 권한 `IsAuthenticatedOrReadOnly` 의존, LLM 프롬프트 인젝션 2건, 로그인 무제한 시도, 에러 스택 노출, 세션+JWT 병행 |
| LOW | 5 | `PublicUser` 열람, 중복 Neo4j 설정, HealthCheck 예외 문자열 공개, 기본 `NewsViewSet` 권한, `gssencmode` 기록 필요 |
| INFO | 4 | `.env` gitignore 적용 ✅, SQL 인젝션 4곳 모두 파라미터 바인딩 ✅, 비밀번호 검증기 활성 ✅, JWT rotation+blacklist ✅ |

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
- **영향**: POST `/api/v1/stocks/sync/{symbol}/` 엔드포인트가 인증 없이 FMP/Alpha Vantage 외부 API 호출 소비. 공격자가 임의 심볼로 루프 호출 시 유료 API 쿼터 고갈 + 서비스 거부.
- **증거**: 라인 917에 `check_rate_limit('fmp')`가 존재하나 IP/사용자 단위 제한이 아니라 전역 FMP rate limit이므로 고갈 시 정상 사용자까지 차단됨.
- **권고**: `permission_classes = [IsAuthenticated]` + 사용자별 `UserRateThrottle` 적용.

### HIGH

#### H-4 `WatchlistViewSet` — 익명 Watchlist 공유 (BOLA)
- **위치**: `chainsight/views/watchlist_views.py:30-46`
  ```python
  class WatchlistViewSet(viewsets.ModelViewSet):
      permission_classes = [AllowAny]
      ...
      def get_queryset(self):
          user = self.request.user if self.request.user.is_authenticated else None
          if user:
              qs = qs.filter(user=user)
          else:
              qs = qs.filter(user__isnull=True)   # ← 익명 사용자 전원이 동일 버킷
  ```
- **영향**: 비로그인 사용자 A가 저장한 `SavedPath`를 비로그인 사용자 B가 GET/DELETE/POST 할 수 있음. `archive`/`resolve`/`recheck`/`expand`/`alternatives` 모든 `@action`이 동일한 익명 풀에서 동작 → IDOR/BOLA.
- **권고**: `permission_classes = [IsAuthenticated]` 또는 최소한 세션 key 기반 필터(`request.session.session_key`)로 분리.

### MED

#### M-1 기본 `IsAuthenticatedOrReadOnly` 의존
- **위치**: `config/settings.py:336-338` — DRF `DEFAULT_PERMISSION_CLASSES = ['IsAuthenticatedOrReadOnly']`
- **미설정 뷰** (명시 없음 → 기본값 적용): `validation/api/views.py` 5종, `sec_pipeline/views.py:FilingDataView`, `news/api/views.py:NewsViewSet`, `stocks/views_indicators.py` 3종, `stocks/views_eod.py` 3종, `stocks/views.py:StockSearchAPIView/StockChartDataAPIView/StockBalanceSheetAPIView/StockIncomeStatementAPIView/StockCashFlowAPIView/StockCompleteDataAPIView`, `stocks/views_search.py` 3종, `stocks/views_mvp.py` 4종, `chainsight/api/views.py` 7종.
- **영향**: 전부 GET는 미인증 허용. 과거 프리미엄 FMP 응답·재무제표·Chain Sight 관계 그래프가 비회원에게 공개됨. 비즈니스적 데이터 보호는 제품 정책에 달림.
- **권고**: 뷰마다 `permission_classes`를 명시(`[AllowAny]` 또는 `[IsAuthenticated]`)하여 기본값 의존 제거. 최소한 파이낸셜(`StockBalanceSheetAPIView`, `StockIncomeStatementAPIView`, `StockCashFlowAPIView`, `AllFundamentalsView 계열`)은 `IsAuthenticated` 검토.

#### M-5 세션+JWT 동시 활성화
- **위치**: `config/settings.py:331-339`
  ```python
  'DEFAULT_AUTHENTICATION_CLASSES': (
      'rest_framework_simplejwt.authentication.JWTAuthentication',
      'rest_framework.authentication.SessionAuthentication',
  ),
  ```
- **영향**: 세션 인증은 CSRF 검증 필수지만, JWT 인증은 CSRF를 우회. 동일 엔드포인트가 두 인증을 수용하면 세션 로그인 사용자의 토큰이 다른 도메인에서 CSRF로 탈취될 수 있고(CSRF 적용 대상 판별이 애매), SimpleJWT 블랙리스트와 Django 세션이 별개로 관리돼 로그아웃 일관성이 깨짐.
- **권고**: REST API는 JWT만 남기고 세션 인증 제거. `LogIn`은 별도 관리자 경로로 격리하거나 제거.

#### M-6 `LogIn` 엔드포인트 무제한 시도 (Credential Stuffing)
- **위치**: `users/views.py:143-168`
- **증거**: 전역 `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` 미설정. `AnonRateThrottle` 적용 뷰는 `chainsight/views/watchlist_views.py` 1건뿐. 로그인에 throttle 없음.
- **영향**: 브루트포스/스터핑 공격에 무방비. `users.jwt_views`의 JWT 로그인도 동일 여부 검증 필요.
- **권고**: `LogIn`, `jwt login`에 `AnonRateThrottle` (예: `5/min`) + 실패 카운터 + django-axes 등을 고려.

### LOW

#### L-4 `PublicUser` 사용자 열람
- **위치**: `users/views.py:111-118` — GET `/users/{username}` 으로 사용자 존재 확인 + `UserSerializer` 응답 (`id, user_name, nick_name, favorite_stock`).
- **영향**: 사용자 이름 열거(Username Enumeration) 가능. 개인정보 노출은 제한적이나 ID/닉네임으로 소셜 엔지니어링 유도 가능.
- **권고**: 최소한 `permission_classes = [IsAuthenticated]` 적용 또는 serializer 필드 축소.

---

## 2. SQL / NoSQL / Command Injection

### INFO (안전 확인)

`cursor.execute` 사용처 **4곳 전부 파라미터 바인딩(`%s`)** 사용 — 인젝션 위험 없음.

| 파일 | 라인 | 형태 | 평가 |
|------|------|------|------|
| `chainsight/services/seed_selection.py:151-179` | CTE + JOIN | `%s` + `[market_date, market_date]` | ✅ |
| `serverless/services/admin_status_service.py:833-837` | 정적 쿼리 (`pg_stat_user_tables`) | 파라미터 없음, 하드코딩 | ✅ |
| `api_request/admin_views.py:266` | `SELECT 1` | 하드코딩 | ✅ |
| `config/views.py:90` | `SELECT 1` | 하드코딩 | ✅ |

> 주의: 향후 `f"... {variable}"` 형태로 쿼리를 조립하지 않도록 코드리뷰 체크리스트에 고정.

Neo4j Cypher 쿼리 쪽도 샘플 확인 시 `$t` 같은 프레이스홀더를 사용(예: `chainsight/api/views.py:118`). 전수 조사 권고.

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
- **평가**: `system_instruction`으로 시스템 프롬프트를 분리하므로 시스템 오버라이드 난이도는 상승. 그러나 `question`은 사용자가 자유롭게 제어하며 `context`(DataBasket 요약) 역시 일부 사용자 입력이 흘러들어올 수 있음. 델리미터 이스케이프/입력 sanitization 없음 → 면책 조항 우회, 시스템 역할 유출, 추천 종목 `<suggestions>` 태그 조작 등 가능.
- **권고**: (1) 사용자 질문을 `<user_query>...</user_query>` 등 고정 델리미터로 감싸고 동일 태그가 입력에 있으면 제거/이스케이프, (2) 응답에서 `<suggestions>` 파싱 시 길이/심볼 화이트리스트 검증, (3) 면책 조항은 응답 검증 단계에서 강제 삽입.

#### M-3 외부 뉴스 콘텐츠가 프롬프트로 흘러들어감
- **위치**:
  - `news/services/keyword_extractor.py:262-282` — `news['title']`, `news['summary'][:100]` f-string.
  - `thesis/views/conversation_views.py:213-261` (`NewsIssuesView._convert_to_korean_issues`) — `t["title"][:80]` 직접 삽입.
  - `thesis/services/prompt_builder.py:625-672` (`build_question_answer_prompt`) — `article.title`, `article.content[:300]` 직접 삽입.
- **영향**: 뉴스 공급자(Finnhub/Marketaux) 또는 공격자가 제어 가능한 기사 제목이 프롬프트를 변형 → 잘못된 키워드/감성/투자 가설이 저장되어 다운스트림(EOD, Thesis Control, 관제실 알림)이 오염됨.
- **권고**: (1) 제목/요약을 `<news index="1">...</news>` XML 블록으로 감싸고 동일 태그 이스케이프, (2) 출력 JSON 스키마 검증(`symbol` 정규식, 감성 enum), (3) 뉴스 본문 길이와 제어문자 필터링.

> 참고: 동일 리스크가 `news/services/news_deep_analyzer.py`, `news/services/stock_insights.py`, `serverless/services/keyword_generator*.py`, `serverless/services/llm_relation_extractor.py`, `rag_analysis/services/entity_extractor.py` 등에도 존재 — 본 감사에서는 샘플 3곳 확인. 전체 검토를 별도 티켓으로 권고.

#### 관찰 — `thesis/services/prompt_builder.py:428-450` 은 INDICATOR_CATALOG 외 지표 생성 금지를 명시 (환각 방지), `response_schema`로 Structured Output 적용. 방어가 어느 정도 걸려 있음.

---

## 4. 시크릿 관리

### CRITICAL

#### C-1 하드코딩 `SECRET_KEY`
- **위치**: `config/settings.py:151`
  ```python
  SECRET_KEY = 'django-insecure-hvwb-ms8%a@fh7_pf@obr@edq6(h41bj+$yetj#h!wg7#(b(&8'
  ```
- **추가 영향**: 같은 값이 `SIMPLE_JWT.SIGNING_KEY`로 재사용(L352) → **SECRET_KEY 노출 = 모든 JWT 위조 가능**. 세션 쿠키 서명, CSRF 토큰, `PasswordResetTokenGenerator`, 사인드 URL 전부 영향권.
- **권고**: `SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')` + 누락 시 startup 실패. 커밋된 값은 즉시 rotate, JWT는 사용자 전원 재로그인 유도(blacklist flush).

### HIGH

#### H-2 Neo4j 기본 비밀번호 `stockvis123`
- **위치**: `config/settings.py:33`, `config/settings.py:130` (중복 정의)
  ```python
  NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'stockvis123')
  ```
- **영향**: `.env`가 누락된 환경에서 Neo4j 기본 비밀번호가 코드에 박힌 약한 값으로 고정. Docker/CI/CD 기본값이 프로덕션까지 전파될 위험.
- **권고**: 기본값 제거, 누락 시 ImproperlyConfigured raise.

#### H-3 DB_USER 기본값 `byeongjinjeong` (개인 계정명)
- **위치**: `config/settings.py:235` — `'USER': os.getenv('DB_USER', 'byeongjinjeong')`
- **영향**: 개인 OS 사용자명이 기본값. `.env`에 DB_* 미설정이라는 메모리(`MEMORY.md`)와 일치 → 다른 개발자/CI 환경에서 의도치 않게 개인 DB에 접속 시도 가능. 또한 개인정보성 노출.
- **권고**: `DB_USER` 기본값 제거 또는 `postgres`로 변경.

#### H-6 `CELERY_ERROR_RECIPIENTS` 하드코딩 이메일
- **위치**: `config/settings.py:454-457`
  ```python
  CELERY_ERROR_RECIPIENTS = ['goid545@naver.com', 'jinie545@gmail.com']
  ```
- **영향**: 개인 이메일이 공개 저장소에 노출. 피싱/스팸 타깃. 운영자 변경 시 리포지토리 수정 필요.
- **권고**: `.env`의 `CELERY_ERROR_RECIPIENTS`(콤마 구분) 로드로 전환, `settings.py` 기본값은 빈 리스트.

### INFO

#### I-1 `.env` gitignore 정상
- `.gitignore` L8 `.env` 포함. `.env.example`만 커밋되어 있음 (OK).
- `ls -la` 결과 `.env` 현재 워킹트리에 존재(size 1777 bytes) — 커밋 이력 확인 권고(`git log -- .env`는 이번 감사 범위 외).

---

## 5. CORS / XSS / 에러 메시지 노출

### CRITICAL

#### C-2 `DEBUG = True`
- **위치**: `config/settings.py:154`
- **영향**: (1) 500 에러 시 Django 기술적 예외 페이지가 settings·쿼리·트레이스백을 노출, (2) `CORS_ALLOW_ALL_ORIGINS = True`가 자동 활성화(L299-304), (3) `ALLOWED_HOSTS = []`와 결합하여 임의 호스트 헤더로 접근 가능.
- **권고**: `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'`. 프로덕션은 명시적으로 False.

### HIGH

#### H-1 `ALLOWED_HOSTS = []`
- **위치**: `config/settings.py:156`
- **영향**: DEBUG=False 전환 시 모든 요청이 DisallowedHost로 차단되어 배포 직후 장애. DEBUG=True 상태에서는 `*` 허용과 동일 → Host Header Injection 공격(비밀번호 리셋 링크 변조 등) 가능.
- **권고**: `ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')` 처럼 환경변수화.

#### H-5 `CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True`
- **위치**: `config/settings.py:301, 307`
- **영향**: DEBUG=True 분기로 자동 활성. 모든 오리진에서 쿠키/Authorization 헤더 첨부 요청 가능 → CSRF/세션 탈취, JWT를 XHR로 읽을 수 있다면 토큰 탈취. 세션 인증이 공존하는 현재 설정(M-5)과 결합되어 실제 리스크 상승.
- **권고**: DEBUG이라도 `CORS_ALLOW_ALL_ORIGINS` + `CORS_ALLOW_CREDENTIALS` 동시 True 금지. 개발에서는 `CORS_ALLOWED_ORIGIN_REGEX = r'^http://localhost:\d+$'`.

### MED

#### M-4 에러 응답에 예외 문자열 반환
- **위치**:
  - `api_request/admin_views.py:68-70, 87-90, 109-114, 131-135, 161-165, 208-212, 237-240, 272-275, 289-292, 302-306`
  - `config/views.py:85-93, 96-104`
  - `stocks/views.py:965-975` 등
- **영향**: `Response({"error": str(e)}, status=500)` 패턴. DEBUG=True에서는 풀 스택트레이스까지 제공. 내부 경로·라이브러리 버전·SQL 단편이 유출.
- **권고**: 클라이언트에는 `{"error": "internal_error", "trace_id": "..."}` 형태만, 실제 예외는 `logger.exception`으로만 남기도록 DRF exception handler로 중앙화.

### LOW

#### L-5 `HealthCheckView` 공개 + 예외 노출
- **위치**: `api_request/admin_views.py:243-308` — `permission_classes = []` 주석상 공개, 내부적으로 DB/Redis/Provider 상태 + 실패 시 `str(e)` 반환.
- **영향**: 외부에서 내부 스택 파악 가능. 헬스체크 자체는 공개해도 되지만 에러 디테일은 숨겨야 함.

---

## 6. 기타 관찰

### LOW

- **L-2 `gssencmode=disable` 하드코딩**: `config/settings.py:241` — macOS 이슈 회피용. 프로덕션 PostgreSQL SSL 설정 문서화 필요 (`sslmode`).
- **L-3 Neo4j 설정 중복 정의**: L31-33 vs L128-131 — `NEO4J_USER` vs `NEO4J_USERNAME` 변수명 혼재. 한쪽이 오버라이드되어 변경 시 실수 유발.
- **L-1 `NewsViewSet` 권한 미명시**: `news/api/views.py:42` — 명시적 `permission_classes` 없음. ReadOnly지만 명시 필요.

### INFO (안전 확인)

- **I-2 SQL 인젝션 4곳 파라미터 바인딩** (위 §2 참조).
- **I-3 비밀번호 검증기 4종** (`AUTH_PASSWORD_VALIDATORS`) 활성.
- **I-4 JWT**: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` — 모범 구성.

---

## 7. 우선순위 조치 권고 (Top 7)

1. **[CRITICAL] C-1 `SECRET_KEY`를 즉시 rotate** 후 `.env` 로드로 전환. JWT 모든 세션 강제 만료.
2. **[CRITICAL] C-2 `DEBUG=False` 강제 + 환경변수화**. 이어서 `ALLOWED_HOSTS`, `CORS_ALLOW_ALL_ORIGINS` 동반 수정(H-1, H-5).
3. **[CRITICAL] C-3 `StockSyncAPIView` 인증 추가** — `IsAuthenticated` + 사용자별 Throttle.
4. **[HIGH] H-2/H-3 Neo4j·DB 기본값 제거**, 누락 시 startup 실패 유도.
5. **[HIGH] H-4 `WatchlistViewSet` 권한 변경** — 익명 허용 제거 혹은 session_key 분리.
6. **[MED] M-6 로그인 Throttle 적용** + M-5 세션 인증 제거.
7. **[MED] M-2/M-3 LLM 프롬프트 델리미터/입력 sanitization 도입**, 특히 뉴스 제목·사용자 질문 경로.

---

## 8. 감사 범위 외 / 후속 조사 제안

- **Celery 태스크 입력 검증**: `*/tasks.py` 전체에서 외부 입력 신뢰 여부(티커 대소문자·화이트리스트) 재확인.
- **Neo4j Cypher 인젝션 전수조사**: `chainsight/graph/`, `rag_analysis/services/neo4j_*` 전 쿼리 `$param` 사용 여부.
- **WebSocket (`*/consumers.py`) 권한 검사**: Channels 채널 레이어와 JWT 인증 연결 여부.
- **업로드/파싱 경로**: `serverless/services/csv_url_resolver.py`, XLSX 파싱(`PK\x03\x04`) 경로의 ZIP slip/경로 탐색 여부.
- **`.env` 커밋 이력**: `git log --all -- .env` 로 과거 노출 여부 확인(본 감사는 읽기 전용 워킹트리만 확인).

---

**감사 수행 방식**: 코드 정적 분석 및 파일 읽기만 수행. 실행/네트워크 테스트·비밀 rotation·코드 수정은 **일체 수행하지 않음**.
