# Stock-Vis 보안 감사 보고서 — 2026-04-27

- **범위**: Backend Django 앱 25개 (views, services, settings, .env), 멀티에이전트 산출물
- **방법**: 정적 코드 분석 (read-only). OWASP Top 10 기반 + LLM 프롬프트 인젝션 + 시크릿 관리
- **수정 여부**: 코드 변경 없음. 본 보고서는 발견사항 + 권고사항만 제공
- **이전 감사 대비**: 2026-04-26 이후 SECRET_KEY 하드코딩, NEO4J_PASSWORD 기본값 `stockvis123`, .env 644 권한 등 4건의 CRITICAL이 해결됨. 그러나 `serverless/views.py`의 무인증 트리거 엔드포인트는 그대로 유지됨

---

## 1. Executive Summary

| 심각도 | 개수 | 핵심 항목 |
|--------|------|----------|
| **CRITICAL** | 3 | serverless/views.py 의 운영 트리거 16+개가 익명 호출 가능, chainsight Watchlist CRUD 무인증, stocks 데이터 sync POST 무인증 |
| **HIGH** | 6 | chainsight/api/views.py 7개 클래스 인증 누락, stocks 데이터 GET 사실상 공개, users PublicUser enumeration, validation API 인증 누락, macro 동기화 트리거 AllowAny, HTTPS/Secure cookie 설정 부재 |
| **MED** | 5 | LLM 프롬프트 인젝션 방어 없음, sec_pipeline FilingDataView 인증 누락, 50건 `str(e)` 응답 노출, FMP/Gemini quota 소진 가능, NewsViewSet read-only 무인증 |
| **LOW** | 3 | EMAIL_USE_TLS 하드코딩 (env 미반영), .env.example의 placeholder 명시성, ALLOWED_HOSTS 빈 리스트 + DEBUG=False 시 모든 요청 거부 가능성 |
| **INFO** | 4 | SQL 파라미터 바인딩 OK, .env 권한 600 OK, .gitignore .env 등록 OK, JWT_SIGNING_KEY 분리 OK |

총 발견: **17건** (CRITICAL 3 / HIGH 6 / MED 5 / LOW 3)
긍정적 검증: **4건** (INFO)

---

## 2. CRITICAL 발견사항

### C-1. `serverless/views.py` — 익명 호출 가능한 운영/관리 트리거 (16+개) <a id="c1"></a>

**파일**: `serverless/views.py`

15개의 함수에 `# TODO: 프로덕션에서는 IsAdminUser/IsAuthenticated로 변경` 주석이 있으나 그대로 `AllowAny`. 추가로 명시적으로 `@authentication_classes([])`로 인증을 비활성화한 트리거 다수.

| 라인 | 함수 | 메서드 | 부작용 | 위험 |
|------|------|--------|--------|------|
| 165 | `trigger_sync` | POST | Celery `sync_daily_market_movers.delay()` | FMP API quota 소진, 큐 폭주 |
| 213 | `sync_now` | POST | 동기 MarketMoversSync 실행 | 동기 외부 API 호출, 응답 지연 공격 |
| 381 | `trigger_keyword_generation` | POST | LLM(Gemini) 키워드 생성 큐잉 | **비용 폭주(Gemini 호출)** |
| 447 | `generate_screener_keywords` | POST | LLM 호출 | 비용 폭주 |
| 780 | `trigger_breadth_sync` | POST | Celery breadth 동기화 | 큐 부하 |
| 967 | `trigger_heatmap_sync` | POST | Celery heatmap 동기화 | 큐 부하 |
| 1373 | `screener_alerts_api` | GET/POST | 알림 생성 (anonymous user 가능) | 데이터 무결성 |
| 1437 | `screener_alert_detail` | PATCH/DELETE | 알림 수정/삭제 | 다른 사용자 데이터 조작 |
| 1494 | `toggle_alert` | POST | 알림 활성화 | 데이터 변조 |
| 1577 | `mark_alert_read` | POST | 알림 상태 변경 | 데이터 변조 |
| 1608 | `dismiss_alert` | POST | 알림 dismissal | 데이터 변조 |
| 1645 | `share_preset` | POST | 프리셋 공유 코드 발급 | 무차별 공유 코드 발급 |
| 1757 | `import_preset` | POST | 공유 프리셋 import | 무차별 import |
| 2308 | `trigger_etf_holdings_sync` | POST | ETF CSV 다운로드 트리거 | **외부 URL 다수 요청 → DoS amplification** |
| 2415 | `resolve_etf_csv_url` | POST | ETF CSV URL 자동 복구 | **SSRF 잠재 위험** (`csv_url_resolver` 동작 검증 필요) |
| 2789 | `refresh_theme_matches_api` | POST | 테마 매칭 갱신 | DB 업데이트 트리거 |
| 2823 | `extract_relations_from_news_api` | POST | LLM 관계 추출 batch 트리거 | **비용 폭주(Gemini batch)** |
| 2987 | `sync_llm_relations_api` | POST | LLM 관계 동기화 | 비용 폭주 |
| 3225 | `institutional_sync_api` | POST | 기관 holding 동기화 | FMP API 소진 |
| 1899 | `generate_thesis` | POST | LLM 가설 생성 | **비용 폭주** |

**증거**: `permission_classes` 매칭 결과 `serverless/views.py`에서 50+ AllowAny, 그중 15개는 명시적 TODO. POST 트리거 14개 모두 인증 없이 호출 가능.

**원격 영향 시나리오**:
1. 공격자가 `POST /api/v1/serverless/extract-relations`를 batch=true로 반복 호출 → Gemini 호출 비용을 단시간에 폭증.
2. `POST /api/v1/serverless/etf/sync`로 다중 ETF CSV 다운로드를 반복 → SPDR/iShares 측 IP 차단 또는 자체 quota 소진.
3. anonymous로 다른 사용자의 alert를 PATCH/DELETE.

**권고**:
- **모든 `# TODO`가 달린 엔드포인트는 즉시 `IsAdminUser`로 전환**(트리거 류) 또는 `IsAuthenticated`(사용자별 alert/preset).
- 사용자별 자원(alert, preset, history)은 `IsAuthenticated` + queryset에서 `request.user` 필터링까지 같이 검증.
- `resolve_etf_csv_url`은 `IsAdminUser` + URL 도메인 화이트리스트(SPDR, iShares 등) 강제.

---

### C-2. `chainsight/views/watchlist_views.py` — Watchlist CRUD 무인증 노출 <a id="c2"></a>

**파일**: `chainsight/views/watchlist_views.py:30-31`

```python
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
```

`ModelViewSet` 전체 작업(POST/PUT/PATCH/DELETE 포함)이 익명에게 허용. anonymous 사용자가 다른 사용자의 watchlist를 조회/수정/삭제 가능.

**권고**:
- `permission_classes = [IsAuthenticated]` 적용
- `get_queryset`에서 `filter(user=self.request.user)` 적용
- AnonRateThrottle 정의가 코드에 있으나 권한 게이트가 없으면 의미 없음

---

### C-3. `stocks/views.py` — 외부 API 호출 트리거가 무인증 (`StockSyncAPIView`) <a id="c3"></a>

**파일**: `stocks/views.py:878-886`

```python
class StockSyncAPIView(APIView):
    """공개 데이터 동기화이므로 인증 불필요"""
    permission_classes = []

    def post(self, request, symbol):
        ...
        result = sync_service.sync_overview(symbol, force=force)
        # FMP / Alpha Vantage 외부 API 호출 + DB 쓰기
```

POST가 인증 없이 외부 유료 API(FMP)를 임의 심볼에 대해 트리거. Rate limit 체크는 있으나 분당 1회 한도라도 한도 자체를 anonymous가 사용해버려 정상 사용자가 차단됨. `force=true` 전달 시 캐시 무력화.

**권고**:
- `permission_classes = [IsAuthenticated]` 적용
- 정말 공개해야 한다면 RateLimit를 IP/user-agent 기반으로 강화 (현재 'fmp' 키만 글로벌 limit)
- 주석의 "공개 데이터" 정당화는 sync 트리거에는 적용되지 않음 — 데이터는 공개여도 호출 비용은 유료

---

## 3. HIGH 발견사항

### H-1. `chainsight/api/views.py` — 7개 클래스 `permission_classes` 누락 <a id="h1"></a>

**파일**: `chainsight/api/views.py`

| 라인 | 클래스 | 비고 |
|------|--------|------|
| 54 | `ChainSightGraphView` | Neo4j 그래프 탐색 N-depth |
| 104 | `ChainSightSuggestionView` | 카테고리별 탐색 제안 |
| 179 | `ChainSightTraceView` | 추적 |
| 302 | `SeedListView` | 시드 목록 |
| 310 | `SectorGraphView` | 섹터 그래프 |
| 439 | `NeighborGraphView` | 인접 그래프 |
| 618 | `SignalFeedView` | 시그널 피드 |

DRF 기본 `IsAuthenticatedOrReadOnly` 적용 → GET이 무차별 공개. Chain Sight 데이터는 유료 데이터(FMP, Neo4j) 기반이며 LLM 추출 결과 포함. 또한 `ChainSightGraphView`는 `depth` 쿼리파라미터를 `min(depth, 3)`으로만 제한 — Neo4j 쿼리 비용은 max 3에서도 큼.

**권고**:
- 최소 `IsAuthenticated`로 강화
- Neo4j 쿼리 cost 제한 (timeout, node count limit)

---

### H-2. `stocks/views.py` — 다수 데이터 GET이 사실상 공개 <a id="h2"></a>

**파일**: `stocks/views.py`

| 라인 | 클래스 | 영향 |
|------|--------|------|
| 75 | `StockListAPIView` | 종목 리스트 |
| 159 | `StockSearchAPIView` | 검색 |
| 212 | `StockChartDataAPIView` | 차트 데이터 |
| 599 | `StockBalanceSheetAPIView` | 대차대조표 |
| 675 | `StockIncomeStatementAPIView` | 손익계산서 |
| 748 | `StockCashFlowAPIView` | 현금흐름표 |
| 820 | `StockCompleteDataAPIView` | 통합 데이터 |

`permission_classes` 미명시 → DRF DEFAULT_PERMISSION_CLASSES = `IsAuthenticatedOrReadOnly` 적용. GET 요청은 모두 익명 가능.

`StockOverviewAPIView`(line 461)만 명시적으로 `IsAuthenticatedOrReadOnly`. 결과적으로 동일하지만 의도 명시 누락이 보안 의사결정 기록 측면에서 문제.

**권고**:
- 명시적으로 `permission_classes = [IsAuthenticated]` 또는 `[IsAuthenticatedOrReadOnly]` 선언 (의도 명시)
- 재무제표는 FMP 유료 데이터 → 익명 캐시 추출 가능. `IsAuthenticated` 권장

---

### H-3. `users/views.py:111` — `PublicUser` username enumeration <a id="h3"></a>

```python
class PublicUser(APIView):
    def get(self, request, user_name):
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            raise NotFound
```

`permission_classes` 미명시 → 익명에게 GET 허용. 반환되는 `UserSerializer`에 따라 username, email, profile 노출 가능. 또한 404 vs 200으로 username 존재 여부를 외부에서 enumerate 가능.

**권고**:
- 적어도 `IsAuthenticated`
- `UserSerializer` 직접 검증해 PII 필드(이메일, 가입일 등) 제외
- 존재 여부 조회 유스케이스라면 별도 endpoint를 만들고 rate limit + Throttle

---

### H-4. `validation/api/views.py` — 5개 클래스 인증 누락 <a id="h4"></a>

| 라인 | 클래스 | 비고 |
|------|--------|------|
| 52 | `ValidationSummaryView` | LLM/벤치마크 데이터 |
| 173 | `ValidationMetricsView` | 지표 노출 |
| 317 | `LeaderComparisonView` | 대장주 비교 |
| 421 | `PresetListView` | Peer 프리셋 |
| 495 | `LLMPeerFilterView` | **LLM 호출** |

특히 `LLMPeerFilterView`는 LLM 호출을 트리거할 가능성이 높음(`validation/services/llm_peer_filter.py` 참조). 익명 호출 시 비용 노출.

`PeerPreferenceView`(line 458)만 `IsAuthenticatedOrReadOnly` 명시 — 일관성 부재.

**권고**:
- 모든 클래스에 `IsAuthenticated` 명시
- LLMPeerFilterView는 throttle 추가 권장

---

### H-5. `macro/views.py` — DataSyncView/SyncStatusView 가 AllowAny <a id="h5"></a>

**파일**: `macro/views.py:353, 389`

```python
class DataSyncView(APIView):
    permission_classes = [AllowAny]
class SyncStatusView(APIView):
    permission_classes = [AllowAny]
```

거시 데이터 자체는 공개여도 sync 트리거는 외부 API quota 소진. 다른 GET 엔드포인트가 AllowAny인 것은 의도가 보이나 DataSync는 별개로 다뤄야 함.

**권고**:
- `DataSyncView`: `IsAdminUser`
- 그 외 macro GET은 현행 유지 가능(공개 데이터 정책에 따라)

---

### H-6. HTTPS/HSTS/Secure Cookie 설정 부재 <a id="h6"></a>

**파일**: `config/settings.py`

`SECURE_PROXY_SSL_HEADER`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT` 모두 미설정.

JWT 토큰을 Authorization 헤더로 운반하므로 HTTPS 미보장 시 토큰 탈취 위험.

**권고**:
- 운영 배포 환경에 다음 추가:
  ```python
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  SECURE_SSL_REDIRECT = not DEBUG
  SESSION_COOKIE_SECURE = not DEBUG
  CSRF_COOKIE_SECURE = not DEBUG
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  ```

---

## 4. MED 발견사항

### M-1. LLM 프롬프트 인젝션 방어 부재 <a id="m1"></a>

**파일**: `thesis/services/prompt_builder.py`, `thesis/views/conversation_views.py`, `news/services/keyword_extractor.py`, `validation/services/llm_peer_filter.py` 등 32개 Gemini 호출 파일

**현황**:
- `call_gemini`/`call_gemini_light`/`call_gemini_suggestions`는 `response_schema` (Structured Output)를 사용 → **출력**은 JSON 강제
- 그러나 사용자/외부 입력은 system prompt와 user prompt에 직접 삽입:
  - `thesis/views/conversation_views.py:230-261` — `NewsArticle.title`을 `f"{i+1}. {t['title'][:80]}"`로 prompt에 삽입(외부 RSS, 위험은 낮으나 0은 아님)
  - `thesis/services/prompt_builder.py:806-859` (`build_suggestion_prompt`) — `news_title`, `keyword`, `summary`를 직접 system prompt에 삽입
  - `prompt_builder.py:610-622` (`build_intent_classification_prompt`) — collected.title, target, premises 등 사용자 직접 입력 데이터를 prompt에 삽입
- 출력 길이 제한(`max_output_tokens=2000`), 입력 슬라이싱(`title[:80]`, `summary[:300]`) 일부 적용. 이는 토큰 비용 방어이지 인젝션 방어 아님.

**위험**:
- Structured Output이 JSON 형식은 강제하지만 enum/필드 값 자체에 인젝션된 지시를 삽입할 수 있음
- 더 큰 위험은 `call_gemini_light`(line 745) — `response_mime_type` 미지정, 자유 형식 응답. 사용자 메시지가 system_prompt를 우회할 수 있음

**권고**:
- 사용자 입력 영역과 시스템 지시를 명확히 구분 (예: `<<USER_INPUT>>...<<END>>`)
- 사용자 입력에 등장하는 “이전 지시 무시”, “system prompt 출력해” 같은 패턴 탐지/차단
- LLM 응답을 절대 직접 실행하지 말고 enum 검증 (현재 schema enum 적용 중인 것은 양호)
- 외부 데이터 출처별 trust level 구분 (RSS 뉴스 vs 사용자 입력)

---

### M-2. `sec_pipeline/views.py:28` — `FilingDataView` 인증 누락 <a id="m2"></a>

`FilingDataView`는 GET으로 SEC EDGAR filing 데이터 조회 + 미수집 시 collection trigger(`get_or_collect_filing`). collection trigger는 무인증 유발 시 외부 SEC API 호출 폭주 가능.

**권고**: `IsAuthenticated` 또는 `IsAdminUser`. 상위 admin dashboard는 `staff_member_required`로 보호되나 API는 별도.

---

### M-3. 응답에 raw exception 메시지 노출 — 50건 <a id="m3"></a>

**파일**: 8개 view 파일에서 `Response({"error": str(e)}, status=500)` 패턴 50건 발견

| 파일 | 건수 |
|------|------|
| `serverless/views.py` | 19 |
| `stocks/views.py` | 8 |
| `serverless/views_admin.py` | 8 |
| `users/views.py` | 3 |
| `rag_analysis/views.py` | 8 |
| `stocks/views_search.py` | 2 |
| `chainsight/api/views.py` | 1 |
| `macro/views.py` | 1 |

`str(e)`에는 Django ORM에서 SQL 일부, 컬럼명, 외부 API 응답 일부가 포함될 수 있어 정보 누출 위험. 스택트레이스 자체는 응답에 포함되지 않음(traceback 호출 없음) — DEBUG=False에서 Django 기본 500 페이지 노출은 차단됨.

**권고**:
- 통일된 error handler 미들웨어 또는 `rest_framework.views.exception_handler` 커스텀
- 운영(`DEBUG=False`)에서는 generic 메시지("Internal Server Error") + correlation ID, 상세는 로그로

---

### M-4. FMP/Gemini API quota 소진 — 인증 + Rate Limit 결합 부재 <a id="m4"></a>

`api_request/rate_limiter.py`는 provider별 글로벌 limit만 관리. `serverless/views.py`/`stocks/views.py`의 sync 트리거는 anonymous IP-throttle/사용자별 throttle이 없어 단일 IP에서 분당 한도 즉시 소진 가능.

**권고**:
- DRF `AnonRateThrottle` + `UserRateThrottle` 클래스를 sync/LLM 호출 view에 명시
- 현재 `users/views.py:39 WatchlistRateThrottle`만 정의 — 다른 곳도 활용

---

### M-5. `news/api/views.py` — `NewsViewSet` 인증 미명시 <a id="m5"></a>

ReadOnlyModelViewSet이라 GET만 가능. DRF 기본은 `IsAuthenticatedOrReadOnly`라 익명 GET 허용. Marketaux/Finnhub 라이선스 약관에 따라 raw article 재배포 제한 가능 → 인증 사용자만 노출 권장.

**권고**: 라이선스 검토 후 `IsAuthenticated` 적용 검토

---

## 5. LOW 발견사항

### L-1. `EMAIL_USE_TLS = True` 하드코딩 <a id="l1"></a>

`config/settings.py:452`. SMTP 환경에 따라 STARTTLS/SMTPS가 다를 수 있음. `EMAIL_USE_SSL`도 미설정.

**권고**: `EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'`

---

### L-2. `.env.example`의 placeholder가 실제 값처럼 보임 <a id="l2"></a>

```
ALPHA_VANTAGE_API_KEY="your_alpha_vantage_api_key_here"
```

placeholder가 명확하나, `DJANGO_DEBUG=True`로 적혀있어 .env로 그대로 복사하면 운영에서도 DEBUG=True로 시작 가능.

**권고**: `.env.example`에서 `DJANGO_DEBUG=False` 기본 + 주석으로 `# 개발: True로 변경` 안내

---

### L-3. `ALLOWED_HOSTS` 빈 리스트 위험 <a id="l3"></a>

`config/settings.py:149-151`:
```python
ALLOWED_HOSTS = [...] or (['*'] if DEBUG else [])
```

운영 환경(DEBUG=False)에서 `DJANGO_ALLOWED_HOSTS` 미설정 시 빈 리스트가 되어 모든 요청이 400으로 거부됨. 의도는 안전하지만, 실수 시 서비스 전체 다운.

**권고**: SECRET_KEY/NEO4J_PASSWORD처럼 ALLOWED_HOSTS도 누락 시 `ImproperlyConfigured` 명시

---

## 6. INFO (검증 완료 — 문제 없음)

### I-1. SQL 인젝션 — 파라미터 바인딩 OK <a id="i1"></a>

| 파일 | 위치 | 검증 |
|------|------|------|
| `chainsight/services/seed_selection.py:152-179` | volume seeds | `%s` 바인딩 사용, market_date 두 번 |
| `serverless/services/admin_status_service.py:833` | DB table sizes | 정적 쿼리, 입력 변수 없음 |
| `api_request/admin_views.py:266` | health check | 정적 `SELECT 1` |
| `config/views.py:90` | health check | 정적 `SELECT 1` |

모두 안전. `cursor.execute()` 외 ORM 코드에서도 `extra(...)` / `raw(...)` 사용 발견 없음.

---

### I-2. 시크릿 관리 — 다층 방어 적용됨 <a id="i2"></a>

- `.env` 권한: **600** (owner-only). 안전.
- `.gitignore`에 `.env` 등록됨 (line 138).
- `git ls-files .env` 결과: 추적 안됨.
- `config/settings.py`:
  - SECRET_KEY 운영 가드(line 153-161): DEBUG=False + dev fallback 사용 시 `ImproperlyConfigured`
  - NEO4J_PASSWORD 운영 가드(line 162-166): DEBUG=False + 빈 값 시 `ImproperlyConfigured`
  - `JWT_SIGNING_KEY` SECRET_KEY와 분리 (line 144) — 회전 가능
  - 이전 보고서(4월 14/21/22/24/25/26일)의 하드코딩 이슈 4건 모두 해결됨

소스 코드에서 평문 시크릿 패턴 grep 결과: 테스트 파일 1건(`tests/unit/macro/test_fred_client.py:30`의 더미 키 `test_fred_key_secret_123`) — false positive.

---

### I-3. CORS 설정 — 명시적 origin 화이트리스트 <a id="i3"></a>

- `CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']`
- `CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False')` (DEBUG와 분리)
- `CORS_ALLOW_CREDENTIALS = True` (명시 origin과 함께라면 OK)
- `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS` 명시적 화이트리스트

운영 배포 시 `CORS_ALLOWED_ORIGINS`에 실제 도메인 추가 필요. 현재 설정은 안전.

---

### I-4. JWT 설정 — 표준 권장 사항 적용 <a id="i4"></a>

`SIMPLE_JWT`:
- `ACCESS_TOKEN_LIFETIME = 60min`, `REFRESH_TOKEN_LIFETIME = 7days` (적절)
- `ROTATE_REFRESH_TOKENS = True`, `BLACKLIST_AFTER_ROTATION = True` (보안 양호)
- `ALGORITHM = HS256`, `SIGNING_KEY = JWT_SIGNING_KEY` (SECRET_KEY와 분리)
- `token_blacklist` 앱 등록됨

JWKS 없는 단일 키 환경에서는 표준 구성. RS256 마이그레이션은 추후 확장 옵션.

---

## 7. 우선순위 액션 플랜 (권고)

### 즉시 (24시간 이내)
1. **C-1**: `serverless/views.py`의 16+개 트리거 엔드포인트에 `IsAdminUser`/`IsAuthenticated` 적용. 특히 LLM 호출(`extract_relations_from_news_api`, `generate_thesis`, `trigger_keyword_generation`, `generate_screener_keywords`, `sync_llm_relations_api`)은 즉시.
2. **C-2**: `WatchlistViewSet permission_classes = [IsAuthenticated]` + queryset user 필터.
3. **C-3**: `StockSyncAPIView permission_classes = [IsAuthenticated]`.

### 단기 (1주)
4. **H-1, H-2, H-4**: 권한 미명시 클래스 모두 `[IsAuthenticated]` 명시.
5. **H-3**: `PublicUser` 인증화 + serializer PII 제거.
6. **H-6**: HTTPS/HSTS/Secure cookie settings.

### 중기 (2~4주)
7. **M-1**: LLM 입력 sanitization 미들웨어 + trust boundary 명시.
8. **M-3**: 통일된 exception handler.
9. **M-4**: DRF Throttle 적용 (LLM/sync 트리거).
10. **L-3**: ALLOWED_HOSTS 가드 추가.

---

## 8. 부록 — 검토한 파일 목록

### 인증/인가 검토 대상 view 파일 (24개)
```
stocks/views.py
stocks/views_fundamentals.py
stocks/views_screener.py
stocks/views_market_movers.py
stocks/views_exchange.py
stocks/views_eod.py
stocks/views_indicators.py
stocks/views_search.py
stocks/views_mvp.py
users/views.py
users/jwt_views.py
news/views.py
news/api/views.py
macro/views.py
rag_analysis/views.py
serverless/views.py
serverless/views_admin.py
validation/views.py
validation/api/views.py
chainsight/views.py
chainsight/api/views.py
chainsight/views/watchlist_views.py
sec_pipeline/views.py
thesis/views/thesis_views.py
thesis/views/conversation_views.py
thesis/views/monitoring_views.py
config/views.py
api_request/admin_views.py
graph_analysis/views.py
metrics/views.py
marketpulse/api/views/__init__.py
```

### SQL 직접 쿼리 (4개)
- `chainsight/services/seed_selection.py`
- `serverless/services/admin_status_service.py`
- `api_request/admin_views.py`
- `config/views.py`

### LLM (Gemini) 호출 (32개 파일)
- 주요: `thesis/services/prompt_builder.py`, `thesis/services/thesis_builder.py`, `thesis/views/conversation_views.py`
- `news/services/keyword_extractor.py`, `news/services/news_deep_analyzer.py`, `news/services/stock_insights.py`
- `rag_analysis/services/llm_service.py`, `rag_analysis/services/adaptive_llm_service.py`, `rag_analysis/services/entity_extractor.py`, `rag_analysis/services/context_compressor.py`
- `serverless/services/keyword_generator.py`, `serverless/services/keyword_generator_v2.py`, `serverless/services/llm_relation_extractor.py`, `serverless/services/thesis_builder.py`, `serverless/services/csv_url_resolver.py`, `serverless/services/regulatory_service.py`, `serverless/services/relationship_keyword_enricher.py`, `serverless/services/keyword_service.py`
- `validation/services/llm_peer_filter.py`
- `marketpulse/tasks/briefing.py`, `marketpulse/briefing/client.py`
- `sec_pipeline/intelligence.py`, `sec_pipeline/extractor.py`
- `stocks/services/korean_overview_service.py`

---

## 9. 본 감사의 한계

- **정적 분석만 수행** — 런타임 실제 동작 검증 안 함. 일부 view가 URL 라우팅에서 제외되어 도달 불가능할 수 있음(검증 권장).
- **인증 우회 경로 미검증** — JWT 토큰 위조, refresh token replay 등은 별도 동적 테스트 필요.
- **의존성 SCA 미수행** — `poetry.lock` / `package-lock.json` CVE 스캔은 별도 요구 시 진행.
- **Docker/CI/CD 미검토** — `.github/workflows/`, `docker/`는 본 감사 범위 외.
- **Frontend 검토 미수행** — `frontend/` XSS/CSP/cookie 처리는 별도 감사 필요.

---

**작성**: Claude (Opus 4.7) — 2026-04-27 자동 감사
**검증 권장**: @qa-architect 가 본 보고서의 CRITICAL 항목을 통합 테스트로 재현(미인증 POST 요청)하여 실제 영향 확인.
