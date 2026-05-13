# Stock-Vis 보안 감사 보고서

- **감사 일시**: 2026-05-13
- **감사 모드**: 읽기 전용 (코드 변경 없음)
- **감사 범위**: OWASP Top 10 (인증/인가, 인젝션, 프롬프트 인젝션, 시크릿, CORS/XSS/에러 노출)
- **대상 브랜치**: main
- **방법**: 정적 분석 (Grep + 파일 정독), 동적 테스트 미실시

---

## 0. 요약 (Executive Summary)

전체 보안 상태는 **중간 수준** — 백엔드 권한 정책의 골격(`DEFAULT_PERMISSION_CLASSES=IsAuthenticated`), SQL 인젝션 방어(파라미터 바인딩 일관 적용), 시크릿 관리 골격(`.gitignore` + 프로덕션 가드)은 잘 잡혀 있다. 그러나 **5건의 CRITICAL/HIGH 사안이 즉시 수정 필요**:

| # | 카테고리 | 발견 | 심각도 |
|---|---------|------|--------|
| C-1 | 인가 | `chainsight/views/watchlist_views.py` `WatchlistViewSet`이 `AllowAny`로 POST/DELETE 허용 — 비로그인 무단 조작 가능 | **CRITICAL** |
| C-2 | LLM 인젝션 | `thesis/services/thesis_builder.py:829-844` 사용자 입력을 정제 없이 `state.history`에 추가해 다음 Gemini 호출의 context로 전달 | **CRITICAL** |
| C-3 | LLM 인젝션 | `thesis/views/conversation_views.py:230-236` 뉴스 제목을 f-string으로 프롬프트에 직접 삽입 (외부 API 신뢰 경계) | **CRITICAL** (조건부) |
| C-4 | 시크릿 | 로컬 `.env`에 6개 실제 작동 API 키 평문 보관 — git 추적은 안 되지만 키 유출 시 즉시 abuse 가능 | **CRITICAL** (운영 환경에서는 H) |
| H-1 | 인증 | JWT signup/login/refresh에 `throttle_classes` 미설정 — credential stuffing/브루트포스 무방비 | **HIGH** |

전 OWASP 카테고리별 결과는 §1~§5 참조.

---

## 1. 인증/인가 (OWASP A01 Broken Access Control / A07 Identification & Authentication)

### 1.1 설정 확인 — 양호

- `config/settings.py` `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']` (양호 — 명시 누락 시 안전 측 기본값).
- 관리자 엔드포인트(`api_request/admin_views.py`, `serverless/views_admin.py`, `sec_pipeline/views.py`, `macro/views.py:DataSyncView`)는 모두 `IsAdminUser` 일관 적용.

### 1.2 CRITICAL 발견

#### [C-1] WatchlistViewSet — AllowAny + POST/DELETE 노출
- **파일**: `chainsight/views/watchlist_views.py:31`
- **상황**:
  ```python
  class WatchlistViewSet(viewsets.ModelViewSet):
      permission_classes = [AllowAny]
      http_method_names = ['get', 'post', 'delete', 'head', 'options']
  ```
- **영향**: 비인증 클라이언트가 `SavedPath` 객체 생성/삭제 가능. 사용자 데이터 무단 조작 + DB 무한 적재(DoS) 표면.
- **심각도**: **CRITICAL**
- **권고 방향**: GET만 공개, 쓰기는 `IsAuthenticated`로 분리 (per-action permission 적용).

### 1.3 HIGH/MED 발견

| 파일:줄 | 클래스 | 이슈 | 심각도 |
|---------|--------|------|--------|
| `stocks/views.py:84, 169, 222, 609, 685, 758, 830` | StockListAPIView 등 7개 | `permission_classes` 명시 누락 — Default 적용으로 인증 강제 (의도가 공개라면 충돌) | LOW |
| `stocks/views_screener.py:58` | StockScreenerView | 공개 스크리너인데 `IsAuthenticated` (UX 영향) | MED |
| `validation/api/views.py:52` | ValidationSummaryView | `permission_classes` 미명시 | MED |

### 1.4 양호 — 사용자 데이터 보호

`users/views.py`의 Watchlist/Portfolio/UserInterest 시리즈, `rag_analysis/views.py`의 DataBasket/Session, `thesis/views/*.py`의 ThesisViewSet — 모두 `IsAuthenticated` + `request.user` 필터링 일관 적용. `WatchlistItemAddView`, `WatchlistBulkAddView`는 `atomic()` + `select_for_update()` 트랜잭션 보호 적용 (양호).

---

## 2. 인젝션 (OWASP A03 Injection — SQL)

### 2.1 cursor.execute 4개 파일 정밀 점검 결과 — 전체 안전

| 파일:줄 | 쿼리 형태 | 사용자 입력 | 바인딩 | 심각도 |
|---------|----------|------------|--------|-------|
| `api_request/admin_views.py:300` | `SELECT 1` (health) | 없음 | N/A | INFO |
| `config/views.py:90` | `SELECT 1` (health) | 없음 | N/A | INFO |
| `serverless/services/admin_status_service.py:833` | `pg_stat_user_tables` 정적 쿼리 | 없음 | N/A | INFO |
| `chainsight/services/seed_selection.py:152-179` | CTE + `%s × 2` | `market_date` (date 타입) | ✅ `[market_date, market_date]` 리스트 바인딩 | LOW |
| `marketpulse/api/views/health.py:30` | `SELECT 1` | 없음 | N/A | INFO |

### 2.2 ORM raw/extra 검색 — 사용처 없음
- `grep -rn "\.raw(\|\.extra("`로 검색 시 매치 없음. Django ORM QuerySet API에만 의존 → SQL 인젝션 표면 최소.

### 2.3 결론
SQL 인젝션 표면은 **현 상태에서 안전**. f-string/`.format()`/`%` 문자열 포매팅 + 사용자 입력 조합 패턴 없음. 향후 추가 시 동일 패턴(파라미터 바인딩) 유지 필요.

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01)

### 3.1 CRITICAL 발견

#### [C-2] thesis_builder — 대화 이력에 사용자 입력 직접 누적
- **파일**: `thesis/services/thesis_builder.py:829-844`
- **상황**:
  ```python
  text = user_input if isinstance(user_input, str) else str(user_input)
  ...
  state.history.append(ChatMessage(role='user', content=text))
  ```
- **영향**:
  - `state.history`는 후속 `call_gemini()` (line 535)/ `call_gemini_light()` (line 761~)의 `contents` 배열로 전달됨.
  - 입력 검증 없이 누적되며 `_handle_modify_premise()` (line 1426), `_handle_modify_indicator()` (line 1592)에서 가설 수정·지표 변경 등 부수효과를 트리거.
  - "이전 지시 무시" 식의 jailbreak 후 가설/지표 임의 변조 가능.
- **심각도**: **CRITICAL**

#### [C-3] NewsIssuesView — 뉴스 제목 f-string 직접 삽입
- **파일**: `thesis/views/conversation_views.py:230-236, 271-274`
- **상황**:
  ```python
  title_list = '\n'.join(
      f'{i+1}. {t["title"][:80]}' for i, t in enumerate(titles[:8])
  )
  prompt = f"""... {title_list} ..."""
  ```
- **영향**: 뉴스 제목 출처(Finnhub/Marketaux 외부 API)가 절대 신뢰선 안에 있다고 보기 어려움. 80자 제한은 `\n---` 같은 짧은 구분자 주입을 막지 못함.
- **심각도**: **CRITICAL** (외부 데이터 신뢰 가정에 따라 조건부)

### 3.2 HIGH 발견

| 파일:줄 | 패턴 | 심각도 |
|---------|------|-------|
| `news/services/keyword_extractor.py:275-282` | 뉴스 제목·요약을 f-string 사용자 프롬프트에 직접 포함 (제한 100자) | HIGH |
| `thesis/services/thesis_builder.py:1468-1500` `_modify_premise` | `user_input`을 별도 인자로 분리하나 누적 `history`로 인해 경계 약화 | HIGH |

### 3.3 MED 발견

| 파일:줄 | 패턴 | 심각도 |
|---------|------|-------|
| `serverless/services/llm_relation_extractor.py:370-381` | 뉴스 본문 5000자 잘라 f-string 삽입 (system/user 분리는 됨) | MED |
| `news/services/news_deep_analyzer.py:188-200` | 뉴스 제목/요약 f-string 삽입 (500자 제한) | MED |

### 3.4 양호한 방어

- `thesis/services/indicator_matcher.py:175-183` `_sanitize_for_prompt()` — `---`, ``` ``` `` 구분자 제거 + 길이 제한 적용 (참고 구현).
- `rag_analysis/services/context_compressor.py:140` `.format(document=...)` 사용 + 1000자 제한.
- Gemini Structured Output(JSON 스키마 + enum) 사용처(`call_gemini()` line 574 등)는 응답 변조 위험 낮음.
- `thesis/views/conversation_views.py:40-108` `_sanitize_conversation_state()` — state 화이트리스트 + 50KB/history 20개 제한.

### 3.5 결론
LLM 표면은 **CRITICAL 2건이 시급**. 특히 대화형 ThesisBuilder는 부수효과(가설/지표 변경)와 결합되어 jailbreak의 실질 피해가 큼. 입력 정제는 `indicator_matcher._sanitize_for_prompt()` 패턴을 `state.history` 누적 직전에도 동일하게 적용하는 방향이 명확함(설계 결정은 별도).

---

## 4. 시크릿 관리 (OWASP A02 Cryptographic Failures / A05 Security Misconfiguration)

### 4.1 양호한 부분

- **`.gitignore`**: `.env`, `.env.local`, `.env.production` 등록 확인 (`/Users/byeongjinjeong/Desktop/stock_vis/.gitignore:10, 138`).
- **`.env.example`**: 더미 placeholder만 포함, 실제 값 없음.
- **Django 프로덕션 가드** (`config/settings.py:143-170`):
  ```python
  if not DEBUG:
      if SECRET_KEY == _SECRET_KEY_DEV_FALLBACK:
          raise ImproperlyConfigured(...)
      if not NEO4J_PASSWORD:
          raise ImproperlyConfigured(...)
  ```
- **test 설정** (`config/settings_test.py`): 더미 SECRET_KEY, Neo4j는 `localhost:1`로 격리.
- **frontend `.env.local`**: `NEXT_PUBLIC_*`만 포함, 백엔드 키 노출 없음.
- **`git ls-files`로 `.env` 추적 여부 확인**: 미추적 (양호).

### 4.2 CRITICAL 발견

#### [C-4] 로컬 `.env`에 6개 실제 작동 키 평문 보관
- **파일**: `/Users/byeongjinjeong/Desktop/stock_vis/.env`
- **발견된 키** (마스킹):

| 변수 | 마스킹 값 | 식별 |
|------|----------|------|
| `FMP_API_KEY` | `KF9E…q0p9` | FMP Starter Plan |
| `MARKETAUX_API_KEY` | `vJlt…p3BP` | Marketaux |
| `FINNHUB_API_KEY` | `d4ra…g710` | Finnhub |
| `FRED_API_KEY` | `588a…c18a` | FRED |
| `ANTHROPIC_API_KEY` | `sk-ant-api03-KLCO…qgAA` | Anthropic (prefix로 식별) |
| `GEMINI_API_KEY` | `AIza…jvt-s` | Google AI (prefix로 식별) |
| `SECRET_KEY` | `metsr^=…wzm` | Django SECRET_KEY (line 47) |
| `NEO4J_PASSWORD` | `stockvis123` (개발 디폴트) | Neo4j 약한 비밀번호 |

- **위험**:
  - `.gitignore`에 등록되어 있어 git 유출 위험은 낮으나, 로컬 머신 침해/백업 유출/노트북 분실 시 즉시 abuse 가능.
  - `.env` 라인 22-25에 **주석 처리된 Aura 클라우드 자격증명**(`NEO4J_URI=neo4j+s://328caeb4...`, `NEO4J_PASSWORD=7D4T…`) — 주석이라도 평문 보관 자체가 위험. **이 키들은 별도 유효성 검토 + 회전 권고**.
- **심각도**: **CRITICAL** (개발 머신 침해 시 즉시 영향) / **HIGH** (운영 환경 가정 시).

### 4.3 MED 발견

#### docker-compose dev 약한 fallback
- **파일**: `docker/docker-compose.yml:17-18, 57`
- **상황**:
  ```yaml
  POSTGRES_PASSWORD: ${DB_PASSWORD:-stockvis_password}
  NEO4J_AUTH: ${NEO4J_PASSWORD:-password}
  ```
- **영향**: `.env` 미설정 시 약한 디폴트 비밀번호로 컨테이너 기동. dev 한정이지만 노출 시 위험.
- **심각도**: MED

### 4.4 양호 (LOW/INFO)
- 테스트 픽스처(`tests/unit/macro/test_fred_client.py:30`, `tests/unit/news/test_providers.py:23, 233`) — 더미 키만 사용.
- 프로덕션 `docker-compose.prod.yml:57`은 `.env.production` 참조, 레포 내 미존재 (의도된 분리).

---

## 5. CORS / XSS / 에러 노출 / 헤더 / Rate Limit (OWASP A05 Security Misconfiguration)

### 5.1 CORS — 양호

- **`config/settings.py:310-320`**:
  ```python
  CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
  CORS_ALLOW_CREDENTIALS = True
  CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'
  ```
- 명시 origin + credentials 조합으로 안전. `CORS_ALLOW_ALL_ORIGINS`는 환경변수로만 토글, DEBUG 의존 없음 (양호).

### 5.2 DEBUG / ALLOWED_HOSTS

- **`.env:48`** `DJANGO_DEBUG=True` — dev 한정 (양호).
- **`config/settings.py:153-155`**:
  ```python
  ALLOWED_HOSTS = [...] or (['*'] if DEBUG else [])
  ```
  → **MED**: DEBUG 시 `['*']` 폴백. Host header 인젝션 표면. dev에서도 `localhost,127.0.0.1` 명시 권장.

### 5.3 에러 노출 — `str(e)` 다발

| 파일:줄 | 패턴 | 심각도 |
|---------|------|-------|
| `chainsight/api/views.py:233-235` | `Response({"error": str(e)})` (Neo4j/DB 예외 전체 노출) | **MED-HIGH** |
| `users/jwt_views.py:116-120` | `f'회원가입 중 오류가 발생했습니다: {str(e)}'` — 회원가입 실패 시 DB 제약/유저 존재 여부 leak | **MED-HIGH** |
| `chainsight/views/watchlist_views.py:232-233` | `Response({'detail': str(e)})` | MED |
| `rag_analysis/views.py:360-362` | `snapshot['error'] = str(e)` | MED |
| `rag_analysis/tasks.py` (multiple) | `{'status':'error', 'error': str(e)}` (Celery 태스크 결과) | MED |

`config/exception_handler.custom_exception_handler`가 envelope 형식만 표준화, traceback 자체는 가리지만, 위 명시 `str(e)` 노출은 별도 경로.

### 5.4 보안 헤더 — 프로덕션 미설정

다음이 `config/settings.py`에서 **미설정** — 프로덕션 배포 시 즉시 HIGH:

| 설정 | 상태 | 영향 |
|------|------|------|
| `SECURE_SSL_REDIRECT` | ✗ | HTTPS 강제 없음 |
| `SECURE_HSTS_SECONDS` | ✗ | downgrade 공격 가능 |
| `SESSION_COOKIE_SECURE` | ✗ | 평문 전송 위험 |
| `CSRF_COOKIE_SECURE` | ✗ | CSRF 쿠키 평문 |
| `SECURE_CONTENT_TYPE_NOSNIFF` | ✗ | MIME sniffing |
| `SECURE_BROWSER_XSS_FILTER` | ✗ | (Legacy) |
| `X_FRAME_OPTIONS` | (default `DENY`) | 양호 |
| `CSRF_TRUSTED_ORIGINS` | ✗ | 프록시 환경에서 CSRF 우회 가능 |

**현 dev 환경**에서는 영향 없으나 **프로덕션 진입 직전 HIGH로 승격**.

### 5.5 JWT 설정 — 양호

- `ACCESS_TOKEN_LIFETIME=60min`, `REFRESH_TOKEN_LIFETIME=7days`, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` — 모범 설정.
- 단, **JWT 엔드포인트에 throttle 미적용**:

#### [H-1] JWT signup/login/refresh에 throttle_classes 없음
- **파일**: `users/urls.py:9-15`, `users/jwt_views.py:JWTSignUpView/LogIn/JWTLogoutView`
- **영향**: credential stuffing, 회원가입 무한 시도 가능. 글로벌 `DEFAULT_THROTTLE_RATES` (`user=60/min, anon=20/min`)이 있지만 비인증 엔드포인트에 throttle class 명시가 안 되어 적용 여부 불명확.
- **심각도**: **HIGH**

### 5.6 XSS

- **frontend `dangerouslySetInnerHTML` 사용처**: 0 (양호).
- 명시적 `innerHTML` 직접 조작: 검색 미발견.

### 5.7 Serializer 노출

- `fields = '__all__'` 사용처: `serverless/serializers.py:144, 151, 158`, `stocks/serializers.py:316, 324, 333` — 모두 비민감 시세/재무 모델.
- **`users/serializers.py`는 명시 필드 리스트** (`UserSerializer: ['id', 'user_name', 'nick_name', 'favorite_stock']`) — 양호.

### 5.8 Rate Limit 일반

- DRF `DEFAULT_THROTTLE_RATES` (`user=60/min, anon=20/min, market_pulse_llm=5/min`) 설정됨.
- 단, 인증/회원가입/refresh 같은 anon 진입점에 throttle class 명시 여부 미확인 — §5.5 참조.

---

## 6. 심각도별 종합

### 6.1 CRITICAL — 즉시 조치 권장 (4건)

| ID | 파일 | 내용 |
|----|------|------|
| C-1 | `chainsight/views/watchlist_views.py:31` | WatchlistViewSet AllowAny + POST/DELETE |
| C-2 | `thesis/services/thesis_builder.py:829-844` | 대화 이력에 사용자 입력 정제 없이 누적 |
| C-3 | `thesis/views/conversation_views.py:230-236` | 뉴스 제목 f-string 직접 프롬프트 삽입 |
| C-4 | `.env` (로컬) | 6개 실제 API 키 + Django SECRET_KEY 평문 보관 (git 미추적이지만 머신 침해 시 즉시 위험) |

### 6.2 HIGH (3건)

| ID | 파일 | 내용 |
|----|------|------|
| H-1 | `users/urls.py`, `users/jwt_views.py` | JWT signup/login/refresh throttle 미설정 |
| H-2 | `news/services/keyword_extractor.py:275-282` | 뉴스 제목·요약 직접 프롬프트 삽입 |
| H-3 | `config/settings.py` | 프로덕션 보안 헤더(SSL/HSTS/Cookie Secure) 미설정 — 현재는 dev라 INFO지만 prod 배포 시 HIGH |

### 6.3 MED (8건)

| ID | 파일 | 내용 |
|----|------|------|
| M-1 | `config/settings.py:153-155` | ALLOWED_HOSTS=['*'] DEBUG 폴백 |
| M-2 | `chainsight/api/views.py:233-235` | `str(e)` Response 노출 |
| M-3 | `users/jwt_views.py:116-120` | 회원가입 실패 시 str(e) — DB 제약/유저 존재 leak |
| M-4 | `chainsight/views/watchlist_views.py:232-233` | `str(e)` Response |
| M-5 | `rag_analysis/views.py:360-362`, `rag_analysis/tasks.py:*` | task error str(e) |
| M-6 | `serverless/services/llm_relation_extractor.py:370-381` | 뉴스 본문 LLM 프롬프트 직접 삽입 (5000자) |
| M-7 | `news/services/news_deep_analyzer.py:188-200` | 뉴스 컨텍스트 직접 삽입 (500자) |
| M-8 | `docker/docker-compose.yml:17-18, 57` | dev 약한 fallback 비밀번호 |
| M-9 | `stocks/views_screener.py:58`, `validation/api/views.py:52` | 공개 데이터인데 권한 명시 누락/IsAuthenticated |

### 6.4 LOW (3건)

| ID | 파일 | 내용 |
|----|------|------|
| L-1 | `stocks/views.py:84, 169, 222, 609, 685, 758, 830` | 공개 조회 엔드포인트 `permission_classes` 명시 누락 (default IsAuthenticated 적용) |
| L-2 | `thesis/services/indicator_matcher.py:175-183` | 구분자 sanitization이 `---`, ``` ``` `` 한정 (`##`, `````json`은 통과) |
| L-3 | `serverless/`, `stocks/` Serializer `fields='__all__'` | 비민감 모델이라 LOW |

### 6.5 INFO (양호)

- SQL: cursor.execute 4개 파일 + health 1개 모두 안전한 정적/파라미터 바인딩 쿼리. raw/extra ORM 미사용.
- CORS: 명시 origin 화이트리스트, `CORS_ALLOW_ALL_ORIGINS` 환경변수 게이팅.
- JWT: 수명 + rotation + blacklist 모범 설정.
- Frontend: `dangerouslySetInnerHTML` 미사용.
- Production guard (`if not DEBUG: raise ImproperlyConfigured`) 적용.
- `.gitignore`에 `.env*` 등록, `git ls-files`로 `.env` 미추적 확인.
- DRF `EXCEPTION_HANDLER` 표준 envelope.
- Watchlist/Portfolio 쓰기에 `atomic()` + `select_for_update()` 적용.

---

## 7. 우선순위 조치 가이드

> 본 보고서는 읽기 전용이므로 코드 변경 없음. 아래는 차후 조치 방향 참고용.

### P0 (즉시 / 24시간 내)
1. **C-4**: `.env`의 6개 API 키 회전. 특히 `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`는 비용 abuse 위험. 주석 처리된 Aura 자격증명도 회전 후 라인 자체 삭제.
2. **C-1**: `WatchlistViewSet`을 per-action permission 또는 `IsAuthenticated` (GET만 AllowAny) 분리.
3. **H-1**: JWT signup/login/refresh에 `throttle_classes = [AnonRateThrottle]` 명시.

### P1 (1주 내)
4. **C-2/C-3**: `state.history` append 전 `_sanitize_for_prompt()` (구분자 + 길이 제한) 적용. 뉴스 제목/요약은 system/user 메시지 명확 분리 + 구분자 escape.
5. **M-2/M-3**: `str(e)` Response 노출 제거 (로깅만 하고 generic 메시지 반환).
6. **M-1**: `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1` `.env` 명시 + `or ['*']` 폴백 제거.

### P2 (배포 전 필수)
7. **H-3**: 프로덕션 settings에 `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `CSRF_TRUSTED_ORIGINS` 추가.
8. **H-2**: 뉴스 키워드 추출에서 외부 입력 정제 강화 (Structured Output 적용 검토).

### P3 (지속 개선)
9. `_sanitize_for_prompt()`의 구분자 패턴 확장 (`##`, `````json`, `<|`, `</`).
10. `dangerouslySetInnerHTML` 등을 막는 lint rule (`react/no-danger`) 도입.
11. pre-commit hook으로 `git-secrets`/`truffleHog` 적용.

---

## 8. 부록 — 검사 매트릭스

### 8.1 OWASP Top 10 (2021) 매핑

| OWASP | 카테고리 | 본 보고서 §  | 발견 |
|-------|---------|-------------|------|
| A01 | Broken Access Control | §1 | C-1, MED M-9, LOW L-1 |
| A02 | Cryptographic Failures | §4 | C-4 (시크릿 평문) |
| A03 | Injection (SQL) | §2 | 모두 INFO/LOW |
| A04 | Insecure Design | §3, §5 | C-2/C-3 (LLM 부수효과) |
| A05 | Security Misconfiguration | §5 | H-3, M-1/M-8 |
| A06 | Vulnerable Components | 미검사 (의존성 SCA는 별도 잡) | - |
| A07 | Identification & Auth Failures | §1, §5.5 | H-1 (JWT throttle 없음) |
| A08 | Software/Data Integrity Failures | (LLM 응답 검증) §3.4 | Structured Output 일부 양호 |
| A09 | Security Logging & Monitoring Failures | 미검사 | - |
| A10 | SSRF | 미검사 (api_request/ 외부 호출 검토 필요) | - |

### 8.2 추가 권장 후속 감사

- **A06**: `poetry show --outdated` + `safety check` 로 의존성 취약점 SCA.
- **A09**: 로그 PII 마스킹, 감사 로그 일관성 검토.
- **A10**: `requests.get()` 사용처 중 사용자 입력 URL이 들어가는 경로 정밀 검사 (특히 `api_request/`, `serverless/services/`).
- **Frontend 별도 감사**: `next.config.js`의 CSP 헤더, `middleware.ts` 권한 게이팅, JWT 저장 위치(localStorage vs httpOnly cookie).

---

**보고서 끝.** 본 감사는 정적 분석 한계가 있으며, 동적 펜테스트(Burp/ZAP) + 의존성 SCA + 컨테이너 이미지 스캔으로 보완 권장.
