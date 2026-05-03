# 보안 감사 보고서 — 2026-05-03

> **대상**: Stock-Vis (Django 5.1 + DRF, Next.js 16)
> **범위**: OWASP Top 10 기반 백엔드 정적 감사 (읽기 전용)
> **작성**: 코드 수정 없이 취약 지점 식별 + 심각도 평가

---

## 0. Executive Summary

| 심각도 | 건수 | 대표 항목 |
|--------|------|----------|
| **CRITICAL** | 4 | serverless 무인증 admin 작업, screener alerts IDOR, chainsight WatchlistViewSet 무인증 CRUD, stocks sync 무인증 |
| **HIGH** | 3 | Django LogIn 뷰 기능 결함(IsAuthenticatedOrReadOnly POST 차단), PublicUser 사용자 PII 무인증 노출, LLM 사용자 입력 직접 삽입 |
| **MEDIUM** | 5 | LLM 외부 데이터 무 sanitize 삽입(다수), CORS env 토글 검증 부족, CACHES Redis 비밀번호 미설정, FilingDataView 권한 누락, 다수 뷰 permission_classes 명시 누락 |
| **LOW** | 3 | DEFAULT_FROM_EMAIL placeholder, ALLOWED_HOSTS=['*'] DEBUG, EOD/Indicators 등 기본값 상속 |
| **INFO** | 2 | stocks 공개 API에 IsAuthenticated 강제 (제품 결정), git에 .env 미트래킹 |

**가장 시급한 조치**:
1. `serverless/views.py` 의 `# TODO: IsAdminUser` 표시된 endpoints 즉시 보호 — 타인이 운영 trigger·sync·cleanup·screener alerts CRUD 가능.
2. `screener_alert_detail` / `toggle_alert` 의 IDOR 패턴 수정 — 비인증 시 모든 사용자 alert PATCH/DELETE 가능.
3. `stocks/views.py:886` `permission_classes = []` 의 외부 API 동기화 트리거 — DoS·요금 폭증 위험.

---

## 1. 인증 / 인가 (A01: Broken Access Control)

### 1.1 CRITICAL — `serverless/views.py` 다수 무인증 운영 endpoint

전역 기본값은 `IsAuthenticatedOrReadOnly`이지만, 본 파일은 거의 모든 endpoint에 명시적으로 `@permission_classes([AllowAny])` + `# TODO: 프로덕션에서는 IsAdminUser로 변경` 주석을 달고 있음. **TODO 처리되지 않은 채 운영 환경 도달 시** 외부 누구나 다음 작업 수행 가능:

| 라인 | 함수 | 의도된 권한 | 현재 권한 | 영향 |
|------|------|------------|----------|------|
| 165 | `trigger_sync` | IsAdminUser | AllowAny | Celery sync 태스크 임의 트리거 (외부 API 쿼터 소모) |
| 213 | `sync_now` | IsAdminUser | AllowAny | 동기 sync 실행 (서버 블로킹) |
| 381 | (cleanup) | IsAdminUser | AllowAny | 데이터 정리 작업 트리거 |
| 447 | (cleanup) | IsAdminUser | AllowAny | 동일 |
| 780 | (sync) | IsAdminUser | AllowAny | 동일 |
| 967 | (sync) | IsAdminUser | AllowAny | 동일 |
| 3224 | (admin) | IsAdminUser | AllowAny | 동일 |

**조치**: TODO 처리. 또는 settings 분기로 `DEBUG=True`에만 AllowAny 부여.

### 1.2 CRITICAL — `screener_alert_detail` IDOR (인증 우회)

`serverless/views.py:1436-1524` 의 `screener_alert_detail` / `toggle_alert`:

```python
@permission_classes([AllowAny])  # TODO: 프로덕션에서는 IsAuthenticated로 변경
def screener_alert_detail(request, alert_id):
    alert = ScreenerAlert.objects.get(id=alert_id)
    if request.user.is_authenticated and alert.user != request.user:
        return 403
    if request.method == 'PATCH': ...
    elif request.method == 'DELETE': alert.delete()
```

비인증 요청은 `request.user.is_authenticated == False` → **and 단락 평가로 403 분기 자체 우회** → 임의 사용자의 alert PATCH/DELETE 가능. `toggle_alert`(1492~) 동일 패턴.

**조치**: `@permission_classes([IsAuthenticated])` 부여하거나, 소유자 체크 조건을 `not (request.user.is_authenticated and alert.user == request.user)` 로 강화.

### 1.3 CRITICAL — `chainsight/views/watchlist_views.py:31` 무인증 SavedPath CRUD

`WatchlistViewSet` 의 `permission_classes = [AllowAny]`. `AnonRateThrottle 30/min` 으로 일부 완화되어 있으나:

- 익명 사용자 모두가 `user__isnull=True` 풀을 공유 → 한 익명 사용자가 다른 익명 사용자의 SavedPath 조회/삭제 가능 (모델 구분 없음).
- 의도가 "공개 데모"라면 GET만 허용하고 쓰기는 인증 필요로 분리 권장.

**조치**: ViewSet 분리 또는 `if request.user.is_authenticated` 가드를 create/destroy/archive/resolve 액션에 부여.

### 1.4 CRITICAL — `stocks/views.py:886` 외부 API sync 무인증

```python
class StockSyncAPIView(APIView):
    permission_classes = []  # 빈 리스트 = 모든 사용자 통과
    def post(self, request, symbol):
        sync_service.sync(...)  # FMP API 호출
```

빈 리스트는 DRF에서 인증·권한 검사 모두 우회. Rate limit은 `check_rate_limit('fmp')` 로 자체 처리하나, 외부 사용자가 임의 심볼로 무한 호출 → FMP 일일 쿼터(10,000) 소진 + 다른 정상 작업 차단.

**조치**: `[IsAuthenticated]` 또는 최소 `AnonRateThrottle` 부여.

### 1.5 HIGH — `users/views.py:111` `PublicUser` PII 노출

```python
class PublicUser(APIView):
    def get(self, request, user_name):
        user = User.objects.get(username=user_name)
        serializer = UserSerializer(user)  # email/profile 포함 가능
```

`permission_classes` 미명시 → 기본값 `IsAuthenticatedOrReadOnly` GET 허용. `UserSerializer` 가 email·생년월일 등 PII 노출 가능. 사용자명 기반 enumeration 공격에도 취약.

**조치**: 의도된 공개 필드만 반환하는 별도 serializer 사용 + `IsAuthenticated` 부여 검토.

### 1.6 HIGH — `users/views.py:143` `LogIn` 기능 결함

`LogIn(APIView).post()` 에 `permission_classes` 미명시 → 기본값 `IsAuthenticatedOrReadOnly`. POST는 인증 필요로 평가 → 비로그인 사용자 401. 세션 기반 로그인이 작동하지 않음.

JWT 로그인은 `users/jwt_views.py:CustomTokenObtainPairView` 가 별도로 처리하므로 운영 영향은 적으나, 노출된 endpoint이므로 의도 불명확.

**조치**: `permission_classes = [AllowAny]` 명시, 또는 endpoint 자체 제거.

### 1.7 MEDIUM — `chainsight/api/views.py` 7개 뷰 permission_classes 미명시

`ChainSightGraphView`, `ChainSightSuggestionView`, `ChainSightTraceView`, `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 모두 `permission_classes` 미선언 → 기본값 상속. 모두 GET이라면 큰 문제 없으나, 의도 표시가 없어 미래 PR에서 POST 추가 시 즉시 무인증 쓰기.

**조치**: 명시적 `[AllowAny]` 또는 `[IsAuthenticated]` 선언.

### 1.8 MEDIUM — `sec_pipeline/views.py:28` `FilingDataView` 권한 누락

`get(self, request, symbol)` 에서 `get_or_collect_filing(symbol)` 호출 → SEC 파이프라인 트리거. 외부 사용자가 임의 심볼로 SEC 수집 작업을 무한 트리거 가능 → DB·Celery 부하.

**조치**: 캐시된 결과만 반환하는 분기와 수집 트리거 분기 분리, 후자는 `[IsAdminUser]`.

### 1.9 INFO — `stocks/views_exchange.py` 등 11개 공개 데이터 뷰 `[IsAuthenticated]`

모두 FMP 공개 시장 데이터 (시세/지수/섹터/스크리너/펀더멘털)인데 `IsAuthenticated` 강제. 콜드 스타트(랜딩 페이지) 차단. 보안 이슈는 아니나 제품 의도와 어긋날 수 있음.

**조치**: 정책 결정 — 콜드 스타트 허용이면 `AllowAny` + Throttle, 아니면 현 상태 유지.

---

## 2. 인젝션 (A03)

### 2.1 SQL Injection — 안전 (확인 완료)

`grep -rl 'cursor.execute'` 결과 4개 파일 모두 안전:

| 파일 | 라인 | 패턴 | 평가 |
|------|------|------|------|
| `api_request/admin_views.py:266` | `cursor.execute("SELECT 1")` | 하드코딩 | OK |
| `config/views.py:90` | `cursor.execute("SELECT 1")` | 하드코딩 | OK |
| `serverless/services/admin_status_service.py:833` | `pg_stat_user_tables` 조회 | 하드코딩 | OK |
| `chainsight/services/seed_selection.py:152` | `WHERE date <= %s` 파라미터 바인딩 | OK |

ORM 사용은 Django의 자동 escape에 의존하므로 별도 위험 없음. `RawSQL`/`extra` 패턴도 `grep` 결과 0건.

### 2.2 LLM Prompt Injection (CRITICAL/HIGH)

LLM 호출 29개 파일 중 사용자 입력 또는 신뢰 불가 외부 데이터가 prompt에 직접 삽입되는 사례:

| 위치 | 위험도 | 입력 출처 | 영향 |
|------|--------|---------|------|
| `rag_analysis/services/llm_service.py:176` `user_content = f"{context}\n\n질문: {question}"` | **HIGH** | HTTP 요청 user 질문 | LLM 출력만 사용자에게 반환 → 시스템 동작 영향 없음. 다만 면책 우회·외부 정보 노출 가능 |
| `thesis/views/conversation_views.py:170` `process_llm_turn(user_input=user_input, ...)` | **HIGH** | 사용자 대화 입력 | LLM 결과가 **가설 빌더 상태**에 반영 → 자기 데이터 조작 정도 (인증 후) |
| `thesis/views/conversation_views.py:230-261` 뉴스 제목 → prompt 직삽입 | **MED** | 외부 뉴스 API | 분류 결과만 반환, 시스템 동작 변경 없음 |
| `news/services/keyword_extractor.py`, `news_deep_analyzer.py`, `stock_insights.py` | **MED** | NewsArticle.title/summary | LLM 출력이 키워드/관계로 **DB에 저장** → 조작된 키워드 영구 저장 위험 |
| `serverless/services/llm_relation_extractor.py:375` 뉴스 본문 직삽입 → 관계 추출 | **HIGH** | 외부 뉴스 본문 | LLM 출력 → `LLMExtractedRelation` DB 저장 → Chain Sight 그래프 오염 가능 |
| `serverless/services/regulatory_service.py:398` 뉴스 스니펫 직삽입 | **HIGH** | 외부 뉴스 | 동일 (규제 그룹 추출 결과 DB 저장) |

**핵심 위험**: 뉴스/공시 텍스트 → LLM → DB 저장 파이프라인은 공격자가 조작된 뉴스 헤드라인/본문을 통해 **시스템 상태를 영구 오염**시킬 수 있음. Marketaux/Finnhub은 신뢰할 수 있으나, RSS·SEC 풀 텍스트는 외부 통제 가능 영역.

**조치**:
1. 모든 LLM 호출에 `system_instruction`을 분리하고, 사용자/외부 텍스트는 `[USER_INPUT_BEGIN]...[USER_INPUT_END]` 같은 식별 가능한 가드 토큰으로 감싸기.
2. LLM 출력이 DB 저장에 영향을 주는 경로 (관계 추출, 키워드 생성)는 schema 검증 + 화이트리스트 필터 추가 (이미 `feedback_llm_indicator_hallucination` 메모에 카탈로그 외 지표 차단이 있음 — 동일 패턴 다른 영역에도 적용).
3. 입력 길이 상한 (현재 일부만 적용).

---

## 3. 시크릿 관리 (A02: Cryptographic / A05: Misconfig)

### 3.1 OK — `.env` git 미트래킹

```
.gitignore:
.env       (line ~14)
.env       (Environments 섹션, line ~165)
**/id_rsa, *.pem, *.key 등 비밀키 패턴 모두 차단
```

`git ls-files | grep -E '\.env$'` → `.env.example` 만 트래킹. **OK**.

### 3.2 OK — 하드코딩 시크릿 없음

`grep -rEn '("|\x27)(sk-|AIzaSy|ghp_|...){10,}'` → 0 hits.
`grep -rEn 'API_KEY\s*=\s*("|\x27)[A-Za-z0-9]{16,}'` → 0 hits.
`grep -rEn 'password\s*=\s*("|\x27)[^\x27"]{6,}('|")` → 0 hits (테스트 픽스처 제외).

### 3.3 OK — `SECRET_KEY` / `NEO4J_PASSWORD` 운영 가드

`config/settings.py:160-179` 에 `DEBUG=False` 시 두 키가 누락되면 `ImproperlyConfigured` raise. **양호**.

### 3.4 MEDIUM — Redis 비밀번호 없음

```python
# config/settings.py:427
'LOCATION': 'redis://127.0.0.1:6379/1',  # 인증 없음
```

로컬 개발은 정상이지만 운영 컨테이너 배포 시 Redis ACL 설정이 환경변수화되지 않음 (코드 하드코딩). `REDIS_URL` 환경변수 도입 권장.

### 3.5 INFO — 알림 수신 이메일 하드코딩

```python
# config/settings.py:464-467
CELERY_ERROR_RECIPIENTS = [
    'goid545@naver.com',
    'jinie545@gmail.com',
]
```

PII (개인 이메일) 가 코드에 포함되어 git 이력에 남음. 환경변수화 권장.

### 3.6 INFO — `DEFAULT_FROM_EMAIL = 'stockvis@example.com'` placeholder

운영 배포 시 미설정이면 placeholder가 발신자로 사용됨 (이메일 발송 실패 가능). DEBUG 가드 또는 운영 검증 필요.

---

## 4. CORS / Hosts (A05: Misconfig)

| 항목 | 설정 | 평가 |
|------|------|------|
| `CORS_ALLOWED_ORIGINS` | localhost:3000, 127.0.0.1:3000 | OK (개발) |
| `CORS_ALLOW_ALL_ORIGINS` | env `DJANGO_CORS_ALLOW_ALL=False` 기본 | OK — DEBUG 의존 제거된 명시적 토글 (좋은 패턴) |
| `CORS_ALLOW_CREDENTIALS` | True | 주의 — `ALL_ORIGINS=True` 와 결합 시 위험. 토글 가드 필요 |
| `ALLOWED_HOSTS` | DEBUG=True 시 `['*']`, False 시 env 의존 | OK |
| `DEBUG` | `os.getenv('DJANGO_DEBUG', 'False')` | OK |

**MEDIUM**: `CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True` 동시 설정은 모든 origin에 인증된 요청을 허용 → Cookie 탈취 위험. 운영 배포 시 두 값을 동시에 True로 두면 즉시 실패하는 가드 추가 권장:

```python
if not DEBUG and CORS_ALLOW_ALL_ORIGINS and CORS_ALLOW_CREDENTIALS:
    raise ImproperlyConfigured("Unsafe CORS combination")
```

---

## 5. 에러 / 정보 노출 (A04, A09)

### 5.1 MEDIUM — `Response({"error": str(e)})` 패턴 다수

`api_request/admin_views.py` 와 `serverless/views.py` 등에서 예외를 `str(e)` 로 그대로 응답. DEBUG=False여도 내부 메시지(쿼리 텍스트, 파일 경로) 가 외부에 노출 가능.

**조치**: 운영에서는 `"error": "Internal error", "request_id": uuid` 패턴으로 변경, 상세는 로그.

### 5.2 LOW — `LOGGING` 핸들러 단일 파일

```python
'filename': 'stocks.log'  # working dir에 평문
```

권한 분리·로테이션 없음. journald 또는 외부 로그 시스템으로 전송 권장.

### 5.3 OK — `DEBUG` traceback 응답

DRF는 DEBUG=False에서 traceback 노출 안 함 (기본 동작). settings.py에 별도 위반 없음.

---

## 6. JWT 설정 (참고)

| 항목 | 값 | 평가 |
|------|-----|------|
| `ALGORITHM` | HS256 | OK |
| `SIGNING_KEY` | `JWT_SIGNING_KEY` (env로 SECRET_KEY와 분리) | OK — 회전 가능 |
| `ACCESS_TOKEN_LIFETIME` | 60분 | 다소 길지만 허용 범위 |
| `REFRESH_TOKEN_LIFETIME` | 7일 | OK |
| `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` | True/True | OK — 모범 사례 |

---

## 7. 권장 우선순위 (Action Plan)

### Sprint 0 (즉시, 1일 내)
1. **serverless/views.py** TODO 표시된 13개 endpoint 권한 부여. 일괄 패치.
2. **screener_alert_detail / toggle_alert** IDOR 패턴 수정 (or 권한만 IsAuthenticated 부여로 자동 해결).
3. **stocks/views.py:886** `permission_classes = []` → `[IsAuthenticated]` 또는 Throttle 추가.
4. **chainsight WatchlistViewSet** 쓰기 액션을 IsAuthenticated 분리.

### Sprint 1 (1주 내)
5. **PublicUser** serializer 노출 필드 축소 + 권한 검토.
6. **LogIn / 기타 미명시 뷰** permission_classes 명시 추가 (chainsight/api/views.py 7개, sec_pipeline FilingDataView, EOD/Indicators).
7. **LLM prompt** 사용자/외부 입력 가드 토큰 도입 + DB 저장 경로에 schema 검증.

### Sprint 2 (운영 직전)
8. **Redis URL** env 화 (인증 포함).
9. **CORS_ALLOW_ALL + CREDENTIALS** 동시 가드.
10. **`Response({"error": str(e)})`** 패턴을 에러 헬퍼로 통일.
11. **CELERY_ERROR_RECIPIENTS** env 화.

---

## 8. 검사 명령 재현

```bash
# SQL 호출 위치
grep -rl 'cursor.execute' --include='*.py' . | head -10

# 권한 명시 누락 의심
grep -rEnL 'permission_classes' stocks/views_*.py users/*.py news/api/views.py rag_analysis/views.py serverless/views_admin.py thesis/views/*.py

# AllowAny + TODO 패턴
grep -rn 'AllowAny.*TODO\|TODO.*AllowAny' --include='*.py' .

# 시크릿 패턴
grep -rEn '("|\x27)(sk-|AIzaSy|ghp_|github_pat_|xoxb-|xoxp-)[A-Za-z0-9_\-]{10,}' --include='*.py' --include='*.ts' .

# .env 추적 여부
git ls-files | grep -E '\.env$|\.env\.'
```

---

## 9. 미감사 영역 (후속)

- **CSRF 면제 여부**: DRF + JWT 환경에서 SessionAuthentication 병행 사용 중 (settings.py:344). `csrf_exempt` 사용 위치 별도 감사 필요.
- **Frontend XSS**: Next.js `dangerouslyInnerHTML` 사용처 미감사. `frontend/` 별도 감사 필요.
- **파일 업로드**: 현재 코드베이스에 명시적 업로드 없으나, MEDIA_URL/UPLOAD_HANDLER 미선언 — 확인 필요.
- **의존성 CVE**: `poetry.lock` 의 패키지 버전 별도 `pip-audit` 실행 권장.
- **Celery task 인자 신뢰성**: tasks.py 가 본 감사 범위 외 (@infra 담당).

---

**보고서 끝**
