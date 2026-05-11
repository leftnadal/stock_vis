# 보안 감사 보고서 — Stock-Vis (2026-05-06)

- **범위**: OWASP Top 10 기준 정적 분석 (코드 변경 없음)
- **방법**: 정규식 검색, 뷰 클래스 권한 추출, 프롬프트 빌더 데이터 흐름 추적, settings/시크릿 검토
- **DRF 기본값**: `DEFAULT_PERMISSION_CLASSES = ['IsAuthenticatedOrReadOnly']` (`config/settings.py:346`)
  - 클래스 단위 미지정 뷰는 GET이 익명 허용, POST/PUT/DELETE는 인증 필요라는 점을 전제로 평가했습니다.

---

## 요약 (심각도별 카운트)

| 심각도 | 건수 | 주제 |
|--------|------|------|
| CRITICAL | 1 | 인증 우회: StockSyncAPIView 익명 POST |
| HIGH | 3 | 로그인/회원가입 throttle 부재, 익명 Watchlist 공유 데이터 풀, LLM 프롬프트 인젝션 여지 |
| MED | 5 | 에러 응답에 `str(e)` 노출, 다수 뷰의 명시적 권한 누락(기본값 의존), JWT signup 메시지 누설, anon throttle 단일화, 프롬프트 컨텍스트 외부 입력 |
| LOW | 3 | health 엔드포인트 DB 에러 노출, 인덱스/비밀번호 정책 약함, 로그에 traceback print() |
| INFO | 4 | cursor.execute 모두 안전, 시크릿 관리 적정, .env gitignore, CORS/DEBUG 가드 적정 |

---

## 1. 인증/인가 (A01:2021 — Broken Access Control)

### 1-1. CRITICAL — StockSyncAPIView가 명시적 익명 허용 (`stocks/views.py:878`)

```python
class StockSyncAPIView(APIView):
    permission_classes = []  # 공개 주식 데이터 동기화는 인증 없이 허용

    def post(self, request, symbol):
        # FMP / Alpha Vantage 외부 호출 트리거
```

- **위험**: 익명 공격자가 임의 심볼로 POST 무한 호출 → Alpha Vantage(5/분), FMP(10/분) 레이트 리밋 소진 → 서비스 전체 데이터 동기화 마비.
- **비용 증폭**: FMP 프리미엄 키가 결합돼 있다면 결제 한도 소진 가능.
- **영향**: 가용성/비용. **HIGH→CRITICAL**로 격상한 이유는 `force=true` 파라미터를 통해 캐시 우회 후 외부 호출을 강제할 수 있기 때문 (rate-limit 체크는 자체 캐시이지, 인증 게이트가 아님).
- **권고**:
  - `IsAdminUser` 또는 `IsAuthenticated` + per-user throttle 적용.
  - 백오피스 전용으로 분리하거나, 공개 유지 시 IP throttle (DRF `AnonRateThrottle` 5/min) 강제.

### 1-2. HIGH — 로그인/회원가입 무제한 시도 (`users/views.py:143`, `users/jwt_views.py:49`)

```python
class LogIn(APIView):  # permission_classes 없음 → IsAuthenticatedOrReadOnly 기본값
class JWTSignUpView(APIView):  # AllowAny, throttle 없음
```

- 두 엔드포인트 모두 `throttle_classes` 미설정. `users/views.py`에서 throttle은 Watchlist 계열에만 적용됨.
- `LogIn`은 `IsAuthenticatedOrReadOnly` 기본값 — POST는 사실상 차단되지 않음(IsAuthenticatedOrReadOnly는 `SAFE_METHODS`만 허용 가드를 깸. write이지만 익명 토큰 미요구로 통과).
  - 정확히는 IsAuthenticatedOrReadOnly가 POST에 대해 `request.user.is_authenticated` 검사를 통과해야 하는데, AnonymousUser면 deny. 그러나 `LogIn` 내부 `authenticate()`가 미인증 사용자를 받아 자체 로그인 시도하므로 차단 우회 의도가 명백.
- **위험**: credential stuffing, 사용자명 열거(`'이미 존재하는 사용자명입니다.'` vs `'이미 등록된 이메일입니다.'`).
- **권고**:
  - `AnonRateThrottle('5/min')` 적용.
  - signup 응답에서 username/email 존재 여부를 일반화한 메시지로 변경 (사용자 열거 방지).
  - 비밀번호 정책: `AUTH_PASSWORD_VALIDATORS`에 길이 12자+ 추가 권고.

### 1-3. HIGH — Chain Sight Watchlist 익명 공유 풀 (`chainsight/views/watchlist_views.py:32-46`)

```python
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        ...
        else:
            qs = SavedPath.objects.filter(user__isnull=True)
```

- 모든 익명 사용자가 `user=NULL` 단일 버킷을 공유 → 임의 익명 사용자가 다른 익명 사용자의 SavedPath 조회·삭제·archive·resolve 가능.
- 30/min Anon throttle은 IP 기반 → 다중 IP 사용 시 무력화.
- **권고**: 익명 사용에 세션 키 또는 anon-token 컬럼을 도입하거나 `IsAuthenticated` 강제. 최소한 DELETE는 인증 필요로 한정.

### 1-4. MED — 명시적 `permission_classes` 누락으로 기본값 의존

다음 뷰들은 클래스 단위 권한 미지정. 기본 `IsAuthenticatedOrReadOnly`로 동작하므로 GET은 익명 허용.

| 파일 | 클래스 |
|------|--------|
| `chainsight/api/views.py` | ChainSightGraphView, ChainSightSuggestionView, ChainSightTraceView, SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView |
| `sec_pipeline/views.py` | FilingDataView (POST가 없으나 GET이 collection 트리거) |
| `stocks/views.py` | StockListAPIView, StockSearchAPIView, StockChartDataAPIView, StockBalanceSheetAPIView, StockIncomeStatementAPIView, StockCashFlowAPIView, StockCompleteDataAPIView |
| `stocks/views_eod.py` | EODDashboardView, EODSignalDetailView, EODPipelineStatusView |
| `stocks/views_indicators.py` | TechnicalIndicatorView, IndicatorSignalView, IndicatorComparisonView |
| `stocks/views_mvp.py` | StockMVPListView, StockMVPDetailView, StockRAGContextView, SectorListView |
| `stocks/views_search.py` | SymbolSearchView, SymbolValidateView, PopularSymbolsView |
| `validation/api/views.py` | ValidationSummaryView, ValidationMetricsView, LeaderComparisonView, PresetListView, LLMPeerFilterView |

- **특히 위험**: `LLMPeerFilterView`는 자연어 → Gemini LLM 호출. 익명 GET이면 비용 증폭(OWASP A04 Insecure Design + cost). 사용자별 throttle 없이 LLM 비용 노출.
  - 메서드가 POST면 IsAuthenticatedOrReadOnly가 막아주지만, `validation/api/views.py:495` LLMPeerFilterView 정의를 보면 권한 명시 없음 — 메서드 가드만으로 안전 여부 판단.
- **권고**: 명시적 `permission_classes` 부여(`IsAuthenticated` 기본 + 공개 의도면 `AllowAny` 명시). 특히 `EODPipelineStatusView`, `LLMPeerFilterView`, `FilingDataView`는 인증 강제.

### 1-5. MED — `FilingDataView` 익명 GET이 SEC 수집 트리거 (`sec_pipeline/views.py:28`)

```python
class FilingDataView(APIView):  # 권한 없음
    def get(self, request, symbol):
        result = get_or_collect_filing(symbol)
```

- GET임에도 부수효과(수집 큐 enqueue) 발생. CRSF 무관, 비용 증폭.
- **권고**: GET → 캐시 조회만, 수집 트리거는 별도 인증 POST 분리. 또는 IP throttle.

### 1-6. INFO — 정상적으로 보호된 그룹

- `users/views.py`의 Portfolio/Watchlist/UserInterest 계열 26개 뷰: 모두 `IsAuthenticated`.
- `serverless/views_admin.py`의 12개 Admin 뷰: 모두 `IsAdminUser` + (별도 admin URL 분리 권고).
- `api_request/admin_views.py` 5개 뷰: `IsAdminUser`.
- `rag_analysis/views.py` 15개 뷰: 모두 `IsAuthenticated`.
- `thesis/views/*` 8개 뷰: 모두 `IsAuthenticated`.

---

## 2. 인젝션 (A03:2021)

### 2-1. INFO — `cursor.execute()` 4건 모두 안전

| 위치 | 형태 | 평가 |
|------|------|------|
| `chainsight/services/seed_selection.py:152` | 멀티라인 정적 SQL + `[market_date, market_date]` 파라미터 바인딩 | 안전 |
| `serverless/services/admin_status_service.py:833` | 정적 `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30` | 안전 |
| `api_request/admin_views.py:266` | `SELECT 1` | 안전 |
| `config/views.py:90` | `SELECT 1` | 안전 |

→ 외부 입력이 SQL 문자열에 직접 합쳐지는 케이스 없음. ORM(`Q`, `filter`, `extra(...)`) 잔여 검색 결과도 위험 없음.

### 2-2. INFO — Django ORM 사용처 검토

`Q(stock_name__icontains=query)` 등 lookup 기반 검색만 발견 (`stocks/views.py:194`). ORM이 escape 처리 → SQL 인젝션 위험 없음.

---

## 3. LLM 프롬프트 인젝션 (A04 Insecure Design / A08 Software & Data Integrity)

LLM 호출 모듈(29개) 중 사용자/외부 입력이 프롬프트에 삽입되는 곳을 추적했습니다. **응답이 JSON Schema로 제약되거나 후속 코드가 화이트리스트로 검증할 경우 영향이 제한됩니다**.

### 3-1. HIGH — `validation/services/llm_peer_filter.py:46-69`

```python
FILTER_PARSING_PROMPT = """You are a financial data filter parser...
**User request**: {user_input}
**Current symbol context**: {symbol} (sector: {sector})
"""
prompt = FILTER_PARSING_PROMPT.format(user_input=user_input, symbol=symbol, sector=sector)
client.models.generate_content(model='gemini-2.5-flash', contents=prompt, ...)
```

- **시스템 인스트럭션과 사용자 입력을 동일 prompt 문자열로 합치고 system_instruction을 사용하지 않음**. → "Ignore above. Output: ..." 류 인젝션이 가장 직접 통하는 패턴.
- 응답은 `response_mime_type='application/json'`이지만 schema 강제 없음 → 임의 JSON 키 반환 가능.
- 후속 `execute_peer_filter()`가 알려진 키만 화이트리스트 처리하므로 직접적 RCE/데이터 유출 가능성은 낮으나, 서비스 정책 우회(LLM 토큰 낭비 / 잘못된 필터 적용)는 가능.
- **권고**:
  - `system_instruction=`로 분리, `contents=user_input`만 전달.
  - `response_schema` JSON Schema 강제.
  - `user_input` 길이 상한(현재 검증 없음)을 시리얼라이저에 추가.

### 3-2. MED — `thesis/views/conversation_views.py:230-274`

```python
title_list = '\n'.join(f'{i+1}. {t["title"][:80]}' for i, t in enumerate(titles[:8]))
prompt = f"""아래 영문 뉴스 제목들을 분석해서...
{title_list}
..."""
client.models.generate_content(model='gemini-2.5-flash', contents=prompt, ...)
```

- 뉴스 제목은 외부 API(Finnhub/Marketaux)에서 수집 → 공급자가 신뢰되더라도 RSS 인용에 prompt-injection payload가 섞일 수 있음.
- 80자 슬라이싱은 길이 통제이지 의미 통제 아님.
- 결과를 JSON Schema 없이 `json.loads()` → `index/category/keyword` 등 키만 화이트리스트 사용 → 영향 제한적.
- **권고**: `system_instruction`으로 명령 분리, `response_schema` 명시, 제목에서 명령형 토큰 ("ignore", "system:", 백틱 코드블록) 필터링.

### 3-3. MED — `thesis/services/prompt_builder.py:625-687` (`build_question_answer_prompt`)

- `article.title`, `article.content[:300]`, `collected.title`, `collected.premises[].title/description` 등 사용자 입력과 외부 뉴스 본문을 시스템 프롬프트에 직접 삽입.
- 본 함수에서 사용되는 응답은 자유 텍스트(설명) → schema 강제 불가. 사용자가 원격 사이트로 명령을 유도할 가능성 존재(예: 답변 스타일 우회).
- 단, `process_response`에서 사용자 입력은 `validate_user_input`을 통과한다 (≤1000자, list ≤20). 시리얼라이저가 prompt-injection 토큰 자체를 차단하지는 않음.
- **권고**: 시스템 프롬프트와 외부 데이터 사이에 명확한 separator(`<<<USER_DATA_START>>>...<<<USER_DATA_END>>>`)를 두고, 그 영역의 명령은 무시하도록 시스템 프롬프트에 명시.

### 3-4. MED — `news/services/keyword_extractor.py:185-202`

- `_build_user_prompt(news_data, target_date)`로 뉴스 제목/요약(외부 입력)을 user prompt에 삽입.
- system_instruction은 분리되어 있어 1차 방어선 존재. JSON 응답이므로 후속 파서가 강건하면 영향 제한적.
- **권고**: `response_schema` 추가, 뉴스 본문에 prompt-injection 토큰 sanitize.

### 3-5. INFO — 안전한 패턴

- `serverless/services/llm_relation_extractor.py:375-411`: system_instruction 분리, JSON 응답 + 후속 화이트리스트 검증.
- `news/services/news_deep_analyzer.py:122-149`: system_instruction 분리.
- `thesis/services/prompt_builder.py:957-975` (`call_gemini_suggestions`): `response_schema` 강제.

---

## 4. 시크릿 관리 (A02:2021 — Cryptographic Failures, A05 Misconfiguration)

### 4-1. INFO — 적정

- `.env` 권한 `0600`, `.gitignore`에 등록됨, `.env.example` 제공(`.env.example` 4254 bytes).
- 코드 내 하드코딩된 실제 시크릿 발견 없음 (`tests/`의 `'test_finnhub_key'` 등은 더미).
- `SECRET_KEY` (`config/settings.py:142-145`): `_SECRET_KEY_DEV_FALLBACK`을 두지만 `DEBUG=False`에서 `ImproperlyConfigured` 발생 → 운영 배포 가드 정상.
- `JWT_SIGNING_KEY` 분리(`config/settings.py:148`).
- `NEO4J_PASSWORD` 누락 시 운영에서 즉시 실패.

### 4-2. LOW — DB_PASSWORD 기본값 빈 문자열 (`config/settings.py:251`)

- 운영에서 빈 비밀번호로 DB 접속 시도 → 즉시 인증 실패하므로 시크릿 누설은 아님. 다만 `DEBUG=False`에서도 경고 없이 통과 → 부팅 가드에 추가 권고.

### 4-3. LOW — `JWTSignUpView` 응답에 예외 메시지 그대로 노출 (`users/jwt_views.py:117-121`)

```python
return Response({'error': f'회원가입 중 오류가 발생했습니다: {str(e)}'}, status=500)
```

- 5xx 경로에서 DB IntegrityError 등 메시지를 클라이언트에 그대로 노출 → 정보 누수.

---

## 5. CORS / XSS / 에러 노출

### 5-1. INFO — CORS 설정 적정 (`config/settings.py:308-338`)

- `CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']`.
- `CORS_ALLOW_ALL_ORIGINS`은 별도 env(`DJANGO_CORS_ALLOW_ALL`) 명시 시에만 활성. DEBUG 의존 제거됨 — 우수.
- `CORS_ALLOW_CREDENTIALS=True` + 화이트리스트 origin → 안전.
- 운영 origin 추가는 env로 주입 필요 (현재 코드에 운영 도메인이 없으니 별도 origin env 추가 점검 권고).

### 5-2. INFO — DEBUG/ALLOWED_HOSTS 가드

- `DEBUG=False` 기본, `ALLOWED_HOSTS`는 env 없으면 `[]` (DEBUG=True일 때만 `['*']`). → 운영 환경에서 `DJANGO_ALLOWED_HOSTS` 미설정 시 모든 호스트 거부 → 안전한 기본값.

### 5-3. MED — 에러 응답에 `str(e)` 노출 (3건)

| 파일 | 라인 | 영향 |
|------|------|------|
| `users/views.py:513` | `RefreshPortfolioDataView` 500 응답 `'detail': str(e)` | 내부 에러 메시지 노출 |
| `users/views.py:558` | `RefreshStockDataView` 500 응답 `'detail': str(e)` | 동일 |
| `chainsight/views/watchlist_views.py:233` | 400 응답 `'detail': str(e)` | 동일 |
| `chainsight/api/views.py:229` | 200 응답 본문 `error: str(e)` | trace path 추측 가능 |
| `users/jwt_views.py:117` | 500 응답 `error: f'... {str(e)}'` | DB 에러 노출 |

- **권고**: 클라이언트에 `error_code`만 반환, 상세는 logger에만 기록. 또는 `DEBUG=True`일 때만 detail 포함.

### 5-4. LOW — `serverless/views.py:1999-2003` traceback print()

```python
error_traceback = traceback.format_exc()
logger.error(...)
print(f"[THESIS ERROR] Traceback:\n{error_traceback}")  # 콘솔 출력
```

- `print()`는 stdout으로 흐르므로 컨테이너 stdout 수집 시 PII/Token 누출 위험. `logger.exception` 일원화 권고. 응답 본문에 노출되지는 않으므로 LOW.

### 5-5. LOW — `HealthCheckView` DB 에러 노출 (`api_request/admin_views.py:271-274`)

```python
health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
```

- `permission_classes = []` (익명 허용) + DB 연결 문자열/사용자명 일부가 메시지에 포함될 수 있음. Cache/Celery 컴포넌트도 동일 패턴.
- **권고**: 익명 헬스체크는 status 코드만 반환, 상세는 `IsAdminUser` 전용 엔드포인트로.

---

## 6. 추가 관찰 사항

### 6-1. MED — `validate_user_input`이 JSONField 깊이 미검증 (`thesis/serializers/conversation_serializers.py:22-32`)

```python
user_input = serializers.JSONField()

def validate_user_input(self, value):
    if isinstance(value, str) and len(value) > 1000:
        raise serializers.ValidationError(...)
    if isinstance(value, list) and len(value) > 20:
        raise serializers.ValidationError(...)
    return value
```

- `dict`, 중첩 list, 깊이/총 노드 수 검증 없음 → JSON polluting / DoS payload 가능.
- 또한 `conversation_state`가 `DictField`로 전체 통과 → 클라이언트가 보낸 임의 dict가 LLM 컨텍스트로 들어감.
- **권고**: 깊이 ≤ 5, 총 노드 ≤ 100 등 가드 추가.

### 6-2. LOW — `AUTH_PASSWORD_VALIDATORS`에 길이 정책 명시 안 됨 (`config/settings.py:265-278`)

```python
{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
```

- `OPTIONS`로 길이 미지정 → 기본값 8자. 12자 + 복잡도 룰 추가 권고.

### 6-3. INFO — JWT Lifetime/Rotation

- Access 60분, Refresh 7일, `ROTATE_REFRESH_TOKENS=True`, 블랙리스트 활성. → 표준적이고 적정.

### 6-4. LOW — Watchlist anon throttle 단일 풀

- `WatchlistAnonThrottle.rate = '30/minute'`이 익명 전체에 단일 적용. 다중 IP 봇넷에 약함.
- **권고**: 익명 비활성화 후 인증 사용자 per-user throttle.

---

## 7. 우선순위 권고

1. **CRITICAL**: `StockSyncAPIView`(`stocks/views.py:878`) 권한 강화 + IP throttle.
2. **HIGH**:
   - `LogIn`, `JWTSignUpView`에 `AnonRateThrottle('5/min')` 적용, signup 응답 메시지 일반화.
   - `WatchlistViewSet` 익명 모드 제거 또는 anon-token 도입.
   - `llm_peer_filter.py` system_instruction 분리 + `response_schema` 강제.
3. **MED**:
   - 명시적 권한 누락 뷰들에 `permission_classes` 부여 (특히 `LLMPeerFilterView`, `FilingDataView`, `EODPipelineStatusView`).
   - 에러 응답 `str(e)` 제거(3개 파일 5건).
   - 뉴스 본문/타이틀 → 프롬프트 삽입 경로 sanitize + system_instruction 사용.
   - `ConversationResponseSerializer`에 JSON 깊이/노드 가드.
4. **LOW**:
   - `HealthCheckView`: 익명에는 status만, 상세는 admin only.
   - `AUTH_PASSWORD_VALIDATORS` 길이 12자+ 명시.
   - `serverless/views.py:1999-2003` `print()` 제거, `logger.exception` 사용.
   - DB_PASSWORD 빈 값 운영 가드 추가.

---

## 8. 검증 방법 메모

- 권한 매트릭스: 각 view 파일별 클래스 정의 라인 → 동일 클래스 본문에서 첫 `permission_classes = ...`까지 스캔.
- LLM 호출 식별: `genai.Client | GenerativeModel | generate_content | gemini` (대소문자 무시) 79개 파일.
- `cursor.execute` 4건 전수 확인.
- 시크릿 패턴: `(api[_-]?key|secret|password|token)\s*=\s*['"][A-Za-z0-9+/=_-]{16,}['"]` — 테스트 더미만 매치.
- DEBUG/CORS/SECRET_KEY: `config/settings.py` 100-380 라인 검토.
