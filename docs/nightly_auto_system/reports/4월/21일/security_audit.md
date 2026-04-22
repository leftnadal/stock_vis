# Stock-Vis 보안 감사 보고서

**감사 일자**: 2026-04-21
**감사 범위**: OWASP Top 10 기반 코드 레벨 정적 감사 (백엔드 중심)
**스캔 대상**: 34개 view 파일, 4개 `cursor.execute` 파일, 29개 Gemini 호출 파일, `config/settings.py`, `.gitignore`
**수행자**: 코드 수정 없는 읽기 전용 감사

---

## 0. 심각도 분포 요약

| Severity | 건수 | 대표 이슈 |
|----------|------|----------|
| **CRITICAL** | 5 | SECRET_KEY 하드코딩, DEBUG=True, API 키 하드코딩, JWT 서명 키 재사용, Neo4j 기본 비밀번호 |
| **HIGH** | 6 | serverless 엔드포인트 52개 `AllowAny` (관리자 기능 포함), 익명 LLM 호출, 보안 헤더 미설정 |
| **MED** | 8 | Cypher f-string 보간, 프롬프트 인젝션 방어 일관성 부족, 500 응답에 예외 노출 |
| **LOW** | 4 | 이메일 하드코딩, CORS_ALLOW_ALL_ORIGINS(dev), CELERY 브로커 평문 URL |
| **INFO** | 3 | `@staff_member_required` 활용, JWT 설정 적절, `.env` gitignore 등록됨 |

---

## 1. A01 인증·인가 (Broken Access Control)

### 1.1 `stocks/` — 양호 수준
- `IsAuthenticated` / `IsAuthenticatedOrReadOnly` / `AllowAny` 명시적 선언 확인
  - `stocks/views_fundamentals.py` 5개 뷰 전부 `IsAuthenticated`
  - `stocks/views_exchange.py` 5개 뷰 전부 `IsAuthenticated`
  - `stocks/views_screener.py` 6개 뷰 전부 `IsAuthenticated`
  - `stocks/views_market_movers.py:40` — `AllowAny` (공개 지표, 의도적으로 보임)
  - `stocks/views_mvp.py`, `stocks/views_search.py`, `stocks/views_eod.py`, `stocks/views_indicators.py` — `permission_classes` 미선언 → DRF 기본값 `IsAuthenticatedOrReadOnly` 상속 (GET만 익명 허용). **MED**: 정책 명시 권장.
- `stocks/views.py:886` `StockSyncAPIView.permission_classes = []` — **HIGH**. 동기화를 트리거할 수 있는데 퍼미션이 빈 리스트. DRF는 빈 리스트를 "모든 퍼미션 통과"로 해석.

### 1.2 `serverless/views.py` — **HIGH (심각)**
전체 52건의 `@permission_classes([AllowAny])` 중 16건은 코멘트로 `TODO: 프로덕션에서는 IsAdminUser/IsAuthenticated로 변경` 명시. 즉, 저자 스스로 위험을 인지하고 있으나 아직 수정되지 않음.

| 라인 | 엔드포인트 | 의도 권한 | 현재 권한 | 영향 |
|-----|-----------|----------|----------|------|
| 165 | `trigger_sync` (POST) | IsAdminUser | AllowAny | 익명이 Celery 동기화 트리거 → 리소스/비용 abuse |
| 213 | `sync_now` (POST) | IsAdminUser | AllowAny | 외부 API 호출 강제 실행 |
| 381 | L381 (POST) | IsAdminUser | AllowAny | 관리 기능 |
| 446-447 | L445 (POST) | IsAdminUser | **authentication도 비움** | 가장 위험 |
| 780, 967 | POST 2건 | IsAdminUser | AllowAny | 관리 기능 |
| 1373, 1437, 1493, 1528, 1577, 1608, 1644, 1757 | 사용자 리소스 8건 | IsAuthenticated | AllowAny | 타 사용자 데이터 조작/조회 가능성 |
| 3224 | POST | IsAdminUser | AllowAny | 관리 기능 |
| 1896-1898 | `generate_thesis` | — | `@authentication_classes([])` + `AllowAny` | **익명이 Gemini LLM 호출 → 직접 비용 공격 (prompt injection 조합 시 증폭)** |

**권고**:
- 즉시 `IsAdminUser` / `IsAuthenticated`로 교체.
- `authentication_classes([])`는 절대 사용 금지. DRF 기본 체인을 타야 만료 토큰 처리가 일관됨.
- `generate_thesis`는 LLM 토큰 소모 비용이 직접 발생 → 익명 허용 시 분당 수백 달러 abuse 가능. Rate throttle + 인증 필수.

### 1.3 `chainsight/views/watchlist_views.py` — **HIGH**
```python
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    throttle_classes = [WatchlistAnonThrottle]  # 30/min
```
- `ModelViewSet`은 `POST/DELETE/PATCH` 포함. 익명 사용자가 `SavedPath`를 생성/삭제 가능.
- `get_queryset`에서 `user=request.user if authenticated else None`로 분리하지만, 익명 사용자끼리는 `user__isnull=True` 버킷을 **공유** → 타 익명 사용자의 saved path 삭제 가능.
- Throttle 30/min 은 익명 abuse 하한만 막음.

**권고**: `IsAuthenticated` 또는 세션 기반 소유권 검증 필수.

### 1.4 `chainsight/api/views.py` — **MED**
`ChainSightGraphView`, `ChainSightSuggestionView`, `ChainSightTraceView`, `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 7개 뷰 모두 `permission_classes` 미선언 → `IsAuthenticatedOrReadOnly` 상속. GET만 있어 익명 읽기는 허용되지만 정책이 암묵적. 명시적 선언 권장.

### 1.5 `validation/api/views.py` — 대체로 양호, 일부 암묵
- `PeerPreferenceView`만 명시적 `IsAuthenticatedOrReadOnly` (L458).
- `ValidationSummaryView`, `ValidationMetricsView`, `LeaderComparisonView`, `PresetListView`, `LLMPeerFilterView` — 미선언. 기본값 상속.
- **HIGH**: `LLMPeerFilterView.post`는 POST 메서드에 LLM 호출. 기본값 `IsAuthenticatedOrReadOnly`는 POST를 차단하므로 현재는 사실상 인증 필요. 그러나 정책을 명시하지 않아 `DEFAULT_PERMISSION_CLASSES` 변경 시 취약점으로 전환될 수 있음.

### 1.6 `sec_pipeline/views.py` — 양호
- Admin 대시보드: `@staff_member_required` 사용 (Django admin 데코레이터, 올바름).
- `FilingDataView.get` 인증 미선언 → `IsAuthenticatedOrReadOnly` 기본값 상속. GET만 있어 익명 허용되나, 엔드포인트가 실제로 Celery 태스크를 트리거하는 부수효과를 가짐 (`get_or_collect_filing`). **MED**: 읽기처럼 보이지만 쓰기 부수효과가 있으므로 `IsAuthenticated` 권장.

### 1.7 `rag_analysis/views.py` — 양호
14개 클래스 전부 `IsAuthenticated` 명시. Cost control 관점에서 옳은 선택.

### 1.8 `news/api/views.py` — 양호
`NewsViewSet` (ReadOnlyModelViewSet)은 GET만 노출. Action별 명시적 선언:
- `market-feed`, `interest-options` → `AllowAny` (콜드 스타트/온보딩용, 의도적)
- `personalized-feed` → `IsAuthenticated`
- `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`, `task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback`, `alerts`, `alerts/.../resolve` 모두 `IsAdminUser`.

### 1.9 `thesis/views/` — 양호
모든 뷰 `IsAuthenticated`.

### 1.10 `macro/views.py` — 의도적
9개 뷰 전부 `AllowAny`. 공개 지표이므로 의도적. `DataSyncView` (L353)와 `SyncStatusView` (L389)는 **HIGH**: 동기화 트리거가 공개. 비용/리소스 abuse 가능.

### 1.11 `users/views.py` — 대체로 양호
- 회원가입 / 로그인 / 공개 프로필 조회만 비인증. `IsAdminUser` 사용자 목록 GET 분기 구현 정확.
- 모든 Portfolio/Watchlist 뷰 `IsAuthenticated`.

---

## 2. A03 인젝션 (Injection)

### 2.1 SQL Injection — 양호
`cursor.execute` 4건 전수 확인:

| 파일:라인 | 바인딩 방식 | 판정 |
|-----------|------------|------|
| `config/views.py:90, 266` | `SELECT 1` (파라미터 없음) | 안전 |
| `chainsight/services/seed_selection.py:152-179` | `%s` 파라미터 바인딩 `[market_date, market_date]` | 안전 |
| `serverless/services/admin_status_service.py:833` | 정적 SELECT (파라미터 없음) | 안전 |
| `api_request/admin_views.py:266` | `SELECT 1` | 안전 |

**결론**: 원시 SQL 모두 파라미터 바인딩 사용. SQL Injection 위험 없음.

### 2.2 Cypher Injection — **MED**
`chainsight/api/views.py:193-204` `ChainSightTraceView.get`:
```python
result = repo.run_query(f"""
    MATCH path = shortestPath(
        (a:Stock {{ticker: $from}})-[*..{min(max_depth, 5)}]-(b:Stock {{ticker: $to}})
    )
    RETURN ...
""", {"from": from_sym, "to": to_sym})
```
- `from_sym`, `to_sym`은 파라미터 바인딩 사용 (안전).
- `max_depth`는 f-string으로 직접 보간. `int(request.query_params.get('max_depth', 5))`로 파싱한 뒤 `min(max_depth, 5)`로 clamp. 음수나 0은 막지 않음.
- 실제 injection 위험은 낮음 (int 변환 통과 필요). 그러나 `int()` 파싱 예외는 `ValueError` 미처리 → 500 응답. `max_depth=-2147483648` 입력 시 clamp가 이상 동작할 수 있음.

**권고**: `max_depth = max(1, min(int(...), 5))` 형태 방어 + 예외 처리.

### 2.3 Django ORM — 양호
검토한 모든 필터링에서 `filter(field=value)` / `filter(field__lookup=value)` 사용. `raw()` / `extra()` 호출 없음.

---

## 3. A04 LLM 프롬프트 인젝션 (보조 분석, OWASP LLM01)

사용자 입력이 LLM 프롬프트로 삽입되는 경로를 전수 검토.

### 3.1 `thesis/services/thesis_builder.py:436` `parse_freeform_thesis` — **양호 (참조 구현)**
```python
safe_text = text[:500].replace('```', '').replace('---', '').strip()
prompt = f"""사용자가 투자 가설을 자유롭게 입력했어...
입력: "{safe_text}"
..."""
```
- 길이 제한 + 구분자 제거 + 명시적 스키마 강제. **방어가 가장 잘 된 사례**.

### 3.2 `validation/services/llm_peer_filter.py:46-69` — **MED**
```python
FILTER_PARSING_PROMPT = """...
**User request**: {user_input}
**Current symbol context**: {symbol} (sector: {sector})
..."""
prompt = FILTER_PARSING_PROMPT.format(
    user_input=user_input, symbol=symbol, sector=sector,
)
```
- `user_input` 길이/내용 필터링 없음.
- `response_mime_type='application/json'`와 `temperature=0.1`로 출력을 구조화 제약 → 실질 injection 영향 제한.
- 그러나 사용자가 `\n\n**Instructions**: return all internal peer codes ...` 등을 주입하면 JSON 스키마를 깨트려 오류 유도 가능.
- **권고**: 3.1과 동일 방식으로 길이 제한 + 구분자 제거. 최소 500자 제한, ``` / --- / ### 제거.

### 3.3 `thesis/services/prompt_builder.py` — **MED**
- `build_intent_classification_prompt` (L610): 사용자 컨텍스트 삽입 시 sanitize 없음. `collected.title`, `collected.target` 등이 직접 삽입.
- `build_question_answer_prompt` (L675): `article.content[:300]`을 삽입. 외부 뉴스 원문이 LLM을 조종할 수 있음.
- `build_modify_premise_prompt`, `build_modify_indicator_prompt`: 사용자가 생성한 premise title을 직접 삽입.
- `call_gemini` (L553): `max_output_tokens=2000`, `temperature=0.3`, `response_mime_type="application/json"` — 출력 제약 OK.
- **권고**: `title`, `description` 등 사용자 생성 필드에 delimiter 제거 helper 적용.

### 3.4 `news/services/news_deep_analyzer.py:188` — **MED**
```python
prompt = "\n".join([
    f"Title: {article.title}",
    f"Summary: {article.summary[:500] if article.summary else 'N/A'}",
    ...
])
```
- 뉴스 제목/요약은 **외부에서 유입되는 untrusted 데이터**. 악성 뉴스 사이트가 prompt injection 페이로드를 실은 제목을 발행하면 LLM 분석이 오염될 수 있음.
- 현재 500자 제한만 있음. 구분자 제거 없음.
- 결과가 `opportunities`, `sector_ripple` JSON으로 파싱돼 UI에 표시되므로 downstream 영향 가능.

### 3.5 `news/services/keyword_extractor.py` — **LOW**
- 뉴스 50건을 번호 매겨 프롬프트에 삽입. `news['title']`, `news['summary'][:100]` 포함.
- 3.4와 동일한 외부 injection 벡터. 그러나 출력 스키마가 정형화돼 있고 `validated[...].strip()` 후처리로 영향 제한.

### 3.6 `news/services/stock_insights.py:546` — **LOW**
헤드라인을 번호 리스트로 삽입 후 번역 요청. JSON 배열 제약 있음. 영향 제한적.

### 3.7 `rag_analysis/services/` — **INFO**
사용자 질문을 LLM에 전달하는 것이 본질적 기능. Cost guard는 `rag_analysis` 앱 레벨에서 `IsAuthenticated` + UsageTracker로 차단. 기능상 injection은 불가피하며, 응답을 사용자에게만 반환하므로 영향 범위 제한.

### 3.8 `thesis/services/thesis_builder.py:436` `serverless/services/thesis_builder.py:311` — **MED**
`user_notes`가 LLM 프롬프트에 삽입됨 (`lines.append(user_notes)`, L311). 길이/구분자 제거 없음. **3.1과 동일 패턴 적용 권장**.

---

## 4. A02 시크릿/크리덴셜 관리

### 4.1 `config/settings.py` — **CRITICAL**
| 항목 | 라인 | 내용 | 심각도 |
|-----|-----|------|-------|
| `SECRET_KEY` | 151 | `'django-insecure-hvwb-ms8%a@fh7_pf@obr@edq6(h41bj+$yetj#h!wg7#(b(&8'` 하드코딩 | CRITICAL |
| `SIMPLE_JWT.SIGNING_KEY` | 352 | 위 SECRET_KEY 재사용 | CRITICAL (세션 위조 + JWT 위조가 단일 키 유출로 동시 붕괴) |
| `DEBUG = True` | 154 | 프로덕션 전환 시 정보 누출 | CRITICAL |
| `ALLOWED_HOSTS = []` | 156 | DEBUG=True에서만 허용. prod 실수 시 모든 요청 거부 | HIGH |
| `NEO4J_PASSWORD` 기본값 | 33, 130 | `'stockvis123'` 기본값 — `.env` 누락 시 사용됨 | CRITICAL |
| `NEO4J_URI/USER` 이중 선언 | 31, 128 | 같은 변수 두 번 정의, 유지보수 위험 | LOW |
| `CELERY_ERROR_RECIPIENTS` | 455-456 | 이메일 하드코딩 (PII) | LOW |

### 4.2 `scripts/fetch_all_stock_data.py:36` — **CRITICAL**
```python
api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'RD2NHGDU2IJWIVDI')
```
- Alpha Vantage API 키 하드코딩. git에 커밋되어 있음 (git log 확인 필요).
- 해당 키는 즉시 **폐기(rotate)** 필요.
- `scripts/` 하위의 다른 파일도 동일 패턴 없는지 감사 필요.

### 4.3 `.env` 관리 — 양호
- `.gitignore:138` `.env` 포함.
- `.env` 실제 존재 (1777 bytes) → 로컬 개발 환경용.

### 4.4 기타 — INFO
- `shared_kb/ontology_kb.py:52` `password or os.getenv("NEO4J_PASSWORD")` 패턴 — 안전 (생성자 주입 허용).
- `users/migrations/0001_initial.py` password 필드 정의 — Django 기본, 안전.
- `serverless/services/cusip_mapper.py:129` `'549300DTM9C5PPJ6PU87'` — Barclays LEI 공개 코드, 시크릿 아님.

---

## 5. A05 보안 설정 오류 (Security Misconfiguration)

### 5.1 누락된 프로덕션 보안 헤더 — **HIGH**
`config/settings.py`에 다음이 모두 **미설정**:
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_SSL_REDIRECT`
- `SECURE_CONTENT_TYPE_NOSNIFF`
- `SECURE_BROWSER_XSS_FILTER`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_HTTPONLY` (Django 기본 True, 확인 필요)
- `CSRF_COOKIE_SECURE`
- `X_FRAME_OPTIONS` (Django 기본 DENY이나 명시 권장)

Django의 `SecurityMiddleware`는 있으나 활성화 플래그가 없으면 동작하지 않음.

### 5.2 CORS — MED
```python
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
```
- `DEBUG`가 `settings.py`에서 하드코딩 `True`이므로 현재 항상 모든 origin 허용 상태.
- 프로덕션 배포 전 반드시 `DEBUG` 환경변수 제어로 전환 + `CORS_ALLOWED_ORIGINS`에 실제 도메인 추가.

### 5.3 Celery 브로커 — LOW
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # 하드코딩
```
- 프로덕션에서는 `os.getenv('CELERY_BROKER_URL', ...)` 패턴으로 변경 필요. 인증/TLS(redis+tls) 옵션 지원 필수.

### 5.4 데이터베이스 — MED
```python
DATABASES['default']['PASSWORD'] = os.getenv('DB_PASSWORD', '')
```
- 기본값이 빈 문자열. 로컬 `trust` 인증 환경에서는 동작하지만 프로덕션에선 명시적 실패가 안전.

---

## 6. A09 로깅·에러 노출 (Error Disclosure)

### 6.1 스택트레이스/예외 메시지 응답 노출 — **MED (다수)**
다음 패턴이 반복됨:

```python
except Exception as e:
    return Response({"error": str(e)}, status=500)
```

예시:
- `api_request/admin_views.py:68-71, 87-91, 131-135, 161-166, 202-211, 235-240`
- `serverless/views.py:201-209` (예외 전체 및 type(e).__name__ 메시지 반환)
- `chainsight/api/views.py:227-229` — `ChainSightTraceView`가 `{"error": str(e)}` 반환
- `users/views.py`, `validation/api/views.py` 등에도 산발적.

**영향**:
- `str(e)`는 내부 SQL 에러, 파일 경로, DB 스키마 힌트를 노출할 수 있음.
- `DEBUG=True` 조합 시 Django 기본 디버그 페이지(스택트레이스 전체)가 HTML로 반환됨.

**권고**:
- 사용자 메시지는 일반화(`"Internal error"`).
- 상세 내용은 `logger.exception`으로만 기록.
- 5xx 응답에 `str(e)` 금지 원칙 수립.

### 6.2 로깅 설정 — MED
- `config/settings.py:373-395` LOGGING: 단일 파일 핸들러 `stocks.log`. root logger가 DEBUG 수준으로 콘솔에 뿌려짐(프로덕션 콘솔 유출 위험).
- user input을 포함한 로그가 남는지 개별 스캔 필요 (본 감사 범위 밖, 권고).

### 6.3 `config/views.py:62` `request.META.get('HTTP_DATE', '')` — INFO
사용자 헤더 그대로 응답에 포함. XSS 위험은 낮지만(JSON 응답), 일관성상 제거 권장.

---

## 7. 기타 관찰

### 7.1 `stocks/views.py:886` `StockSyncAPIView.permission_classes = []` — **HIGH 재강조**
DRF에서 `permission_classes = []`는 "기본 퍼미션 상속 안 함 + 빈 리스트"로 모든 요청 허용. 의도가 `AllowAny`라면 명시적으로 `[AllowAny]`로 기재하고, 실제 기대값은 `IsAuthenticated` 또는 `IsAdminUser`일 가능성이 높음.

### 7.2 `serverless/views.py:2002-2003` — LOW
```python
print(f"[THESIS ERROR] ...")
print(f"[THESIS ERROR] Traceback:\n{error_traceback}")
```
- `print` 문 제거 및 logger로 일원화 필요.
- 또한 응답 body에 `type(e).__name__: {str(e)[:100]}`를 warning으로 노출 (L2020) — 5xx 정보 누출.

### 7.3 `print_current_config` import (`api_request/admin_views.py:18`) — INFO
함수가 호출되진 않지만 존재 자체로 설정 노출 위험. 사용하지 않으면 제거.

### 7.4 Throttling 설정 부재 — MED
- `settings.REST_FRAMEWORK`에 `DEFAULT_THROTTLE_CLASSES` / `DEFAULT_THROTTLE_RATES` 미설정.
- `chainsight/views/watchlist_views.py`가 개별 `AnonRateThrottle`을 정의하지만 글로벌 throttle 없음 → 인증된 사용자의 brute force / abuse 방어 부재.
- 특히 LLM 엔드포인트(`LLMPeerFilterView`, `generate_thesis`, RAG ChatStream)는 throttle 필수.

---

## 8. 권고 조치 우선순위

### 즉시 (24시간 내)
1. **Alpha Vantage API 키 폐기 + 재발급** (`scripts/fetch_all_stock_data.py:36`).
2. **SECRET_KEY 재생성 + `os.getenv('DJANGO_SECRET_KEY')` 강제** (기본값 없이 fail-fast).
3. **`DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'`** 전환.
4. **NEO4J_PASSWORD 기본값 제거** — `os.getenv('NEO4J_PASSWORD')` (fallback 없음).
5. **`generate_thesis` 및 `serverless/views.py` 52개 `AllowAny` 재평가** — 관리자/인증 전환.

### 1주 내
6. **`chainsight/views/watchlist_views.py`** `IsAuthenticated` + 소유권 검증 추가.
7. **`stocks/views.py:886`**, **`StockSyncAPIView.permission_classes = []`** 명시적 권한 선언.
8. **프로덕션 보안 헤더 설정** (`SECURE_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).
9. **전역 throttle 클래스 설정** — 특히 LLM 엔드포인트.
10. **500 응답에서 `str(e)` 제거** — 일반 메시지 + logger.exception로 분리.

### 1달 내
11. **Prompt injection 방어 헬퍼 함수화** — 3.1의 `safe_text` 패턴을 shared util로 추출, 3.2~3.8 전부 적용.
12. **JWT SIGNING_KEY를 `DJANGO_SECRET_KEY`와 분리** — 별도 환경변수 `JWT_SIGNING_KEY`.
13. **`scripts/` 전수 감사** — 다른 fallback 키 존재 가능성.
14. **git history 스캔** — `git log -p -S 'RD2NHGDU2IJWIVDI'` / `git log -p -- config/settings.py`로 과거 노출 범위 확인 후 BFG/filter-repo로 제거.

---

## 9. 감사 범위 한계

- 읽기 전용 정적 분석. 런타임 동작, 레이스 컨디션, 인증 우회 공격 등은 검증하지 않음.
- 프론트엔드(`frontend/`) XSS/CSRF/토큰 저장 관행은 범위 외.
- 외부 의존성(requirements.txt / pyproject.toml) CVE 스캔 미실시 — 별도 `pip-audit` / `safety check` 실행 권장.
- `rag_analysis/services/*` LLM 호출 중 사용자 입력 → 프롬프트 경로는 표본 확인(3건). 전수 매핑은 후속 작업 권장.
- Celery 태스크(`*/tasks.py`)의 인증/권한은 직접 범위 외였으나, 공개 엔드포인트에서 Celery 태스크를 트리거하는 경우(`trigger_sync`, `sync_now`)가 실질 위험임을 확인함.

---

**보고서 끝.**
