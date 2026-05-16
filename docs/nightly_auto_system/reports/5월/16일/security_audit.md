# 보안 감사 보고서 (Stock-Vis) — 2026-05-16

- 감사 범위: OWASP Top 10 + LLM 프롬프트 인젝션 + 시크릿 관리
- 모드: 읽기 전용 (코드 수정 없음)
- 감사자: 자동 감사 파이프라인 (nightly_auto_system)
- 기준 시각: 2026-05-16 (KST)
- 대상 브랜치: `slice8`

---

## 0. 요약 (Executive Summary)

| 등급 | 건수 | 핵심 키워드 |
|------|------|------------|
| CRITICAL | 1 | LLM 비용 증폭 (`extract_relations_from_news_api` AllowAny + Celery + LLM) |
| HIGH | 3 | Screener Preset BOLA, ETF Sync 무인증 트리거, Thesis Generate 무인증 |
| MED | 4 | LLM 프롬프트 인젝션 부분 방어, anon 20/min 한도, ALLOWED_HOSTS=`*` (DEBUG), 자유 입력→LLM |
| LOW | 3 | 외부 뉴스→LLM 간접 인젝션 표면, HealthCheckView 정보 노출 검토 |
| INFO | 5 | 글로벌 IsAuthenticated 의존(명시 permission 누락), 운영 가드 정상 등 |

**전체 평가**: 글로벌 `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` 가드와 운영 ImproperlyConfigured 가드는 매우 잘 잡혀 있다. SQL 인젝션 4곳은 모두 안전(파라미터 바인딩 또는 정적 쿼리). 시크릿은 `.env` 격리(권한 0600, gitignore) + Dev 폴백 차단으로 양호. **즉시 조치 권고는 `serverless/views.py` 다수의 `AllowAny` POST/CRUD 엔드포인트 (특히 LLM·Celery·BOLA 표면 5건)** 에 집중된다.

---

## 1. OWASP A01 — 인증/인가 (Broken Access Control)

### 1.1 글로벌 정책 (Good)

- `config/settings.py:348-367`: `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']` 명시
- `config/settings.py:344-347` 주석: audit P0 #5 (2026-04-29)에서 `IsAuthenticatedOrReadOnly` → `IsAuthenticated` 로 강화한 이력 확인
- 결과: views 파일에서 `permission_classes` 누락이라도 익명 GET 무차별 노출은 차단됨

### 1.2 17개 뷰 파일 매핑 결과

| 파일 | APIView/Func 수 | permission_classes 명시 | 글로벌 의존 | 의도된 공개(AllowAny) |
|------|----------------|---------------------|------------|--------------------|
| stocks/views.py | 9 | 4 | 5 (글로벌 IsAuthenticated) | 0 |
| stocks/views_screener.py | 5 | 5 | 0 | 0 |
| stocks/views_market_movers.py | 1 | 1 | 0 | 1 (Market Pulse 공개) |
| stocks/views_eod.py | 3 | 0 | 3 | 0 |
| stocks/views_indicators.py | 3 | 0 | 3 | 0 |
| stocks/views_search.py | 3 | 0 | 3 | 0 |
| stocks/views_fundamentals.py | 5 | 5 | 0 | 0 |
| stocks/views_mvp.py | 4 | 0 | 4 | 0 |
| stocks/views_exchange.py | 5 | 5 | 0 | 0 |
| users/views.py | 25+ | 25 | 0 | 2 (LogIn/PublicUser 명시 AllowAny) |
| macro/views.py | 10 | 10 | 0 | 9 (거시 공개) + 1 IsAdminUser |
| news/api/views.py | 1 ViewSet | 부분 action만 | 글로벌 | 2 (`market-feed`, `interest-options`) |
| news/views.py | 0 | — | — | — |
| rag_analysis/views.py | 15 | 15 | 0 | 0 |
| serverless/views.py | 60+ 함수 | 60 (대부분 AllowAny) | 0 | **다수 (아래 1.4 참조)** |
| serverless/views_admin.py | 12 | 12 (전부 IsAdminUser) | 0 | 0 |
| validation/views.py | 0 (모듈 비어있음) | — | — | — |
| validation/api/views.py | 1 (IsAuthenticatedOrReadOnly) | 1 | 다수 | — |
| chainsight/views.py | 0 (Django template 미사용) | — | — | — |
| chainsight/api/views.py | 7 APIView | **0** | **7 (글로벌 IsAuthenticated 자동 적용)** | 0 |
| sec_pipeline/views.py | 1 | 1 IsAdminUser | 0 | 0 |

### 1.3 [INFO] 명시적 permission_classes 누락 (글로벌 의존)

다음 클래스는 `permission_classes`가 코드에 명시되어 있지 않다. 글로벌 기본 `IsAuthenticated`가 적용되므로 **현재는 안전**하지만, 향후 글로벌 정책 변경 시 무방비로 노출될 수 있다.

- `stocks/views_eod.py`: `EODDashboardView`(L20), `EODSignalDetailView`(L51), `EODPipelineStatusView`(L110)
- `stocks/views_indicators.py`: `TechnicalIndicatorView`(L16), `IndicatorSignalView`(L200), `IndicatorComparisonView`(L297)
- `stocks/views_search.py`: `SymbolSearchView`(L18), `SymbolValidateView`(L91), `PopularSymbolsView`(L146)
- `stocks/views_mvp.py`: `StockMVPListView`(L17), `StockMVPDetailView`(L69), `StockRAGContextView`(L142), `SectorListView`(L190)
- `stocks/views.py`: `StockListAPIView`(L84), `StockSearchAPIView`(L169), `StockChartDataAPIView`(L222), `StockBalanceSheetAPIView`(L609), `StockIncomeStatementAPIView`(L685), `StockCashFlowAPIView`(L758), `StockCompleteDataAPIView`(L830)
- `chainsight/api/views.py`: `ChainSightGraphView`(L58), `ChainSightSuggestionView`(L109), `ChainSightTraceView`(L185), `SeedListView`(L309), `SectorGraphView`(L318), `NeighborGraphView`(L448), `SignalFeedView`(L628)

**권장**: 의도된 인증 요구 여부를 각 클래스 머리에 `permission_classes = [IsAuthenticated]`로 명시 (defense-in-depth).

### 1.4 [CRITICAL/HIGH] serverless/views.py AllowAny 다수 노출

`config/settings.py:344-347` 주석에 audit P0 #6 후속 정리가 있으나 일부 비용 증폭/BOLA 위험 엔드포인트가 여전히 `AllowAny`로 노출되어 있다.

#### [CRITICAL] LLM·Celery 비용 증폭 표면

- `serverless/views.py:2392-2395` `extract_relations_from_news_api` — `@authentication_classes([])` + `AllowAny` POST
  - 본문 `news_id` 또는 `batch=true,hours,limit` 으로 **Gemini LLM 추출 Celery 태스크**를 누구나 트리거 가능
  - LLM 호출 비용 (Gemini Free 15 RPM/1500 RPD) 또는 유료 키 사용분이 **공격자에 의해 소모** → 비용 증폭 + 다른 정당한 작업 RPM 고갈
  - **즉시 조치 권장**: `IsAdminUser` 또는 최소 `IsAuthenticated` + 명시적 throttle

#### [HIGH] BOLA — Screener Preset CRUD 무인증

- `serverless/views.py:870-927`
  - `screener_presets_api` GET/POST (`AllowAny`)
  - `screener_preset_detail` GET/PATCH/DELETE (`AllowAny`) — `preset_id` 만으로 다른 사용자 preset 수정/삭제 가능 위험
- `serverless/views.py:976-978` `execute_preset` POST `AllowAny` — 임의 preset 실행
- `serverless/views.py:1092-1095` `advanced_screener_api` POST `AllowAny` — 임의 필터 무인증 실행 (DoS 표면)

#### [HIGH] 외부 API 호출 트리거 무인증

- `serverless/views.py:1931-1934` `trigger_etf_holdings_sync` POST `AllowAny` — FMP/외부 ETF CSV 호출 트리거
- `serverless/views.py:2033-2036` `resolve_etf_csv_url` POST `AllowAny`
- `serverless/views.py:2363-2366` `refresh_theme_matches_api` POST `AllowAny`

#### [HIGH] 사용자별 Thesis 무인증 생성·조회

- `serverless/views.py:1598-1601` `generate_thesis` POST `AllowAny` — LLM thesis 생성. 사용자 식별 없이 비용 발생
- `serverless/views.py:1786-1788` `get_shared_thesis` `AllowAny` — 공유 코드로만 보호 (공유 코드 추측 가능 여부 점검 필요)

#### [INFO] 의도된 공개로 보이는 GET (검토만)

- `market_movers_api`, `market_breadth_api`, `sector_heatmap_api`, `etf_holdings_api`, `theme_list_api` 등 GET — 시장 데이터 공개 정책으로 합리적
- `trending_presets` GET `AllowAny` — 공개 트렌딩 보드 의도로 보임

### 1.5 [MED] anon throttle 20/min

- `config/settings.py:356-362`: `'anon': '20/min'` — 1.4의 무인증 POST 표면에서 분당 20회 비용 증폭이 가능. 비용 증폭 대상은 throttle만으로 부족. 인증 필수화 권장.

### 1.6 [MED] `validation/api/views.py:461` `IsAuthenticatedOrReadOnly`

- DELETE/POST는 인증 필요, GET은 공개. 검증 데이터 (peer 비교 등) 공개 의도 확인 필요. 공개여도 도메인상 큰 위험은 없음.

---

## 2. OWASP A03 — 인젝션 (SQL Injection)

### 2.1 cursor.execute 4곳 검토 결과 — 전부 안전

| 위치 | 패턴 | 결론 |
|------|------|------|
| `chainsight/services/seed_selection.py:152-179` | `cursor.execute("WITH latest AS (... WHERE date = (SELECT MAX(date) FROM stocks_daily_price WHERE date <= %s) ... LIMIT 10", [market_date, market_date])` | ✅ 파라미터 바인딩 (`%s`), `market_date`는 Python `date` 객체. 안전 |
| `serverless/services/admin_status_service.py:833-837` | `cursor.execute("SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30")` | ✅ 정적 쿼리. 사용자 입력 없음. 안전 |
| `api_request/admin_views.py:300` | `cursor.execute("SELECT 1")` (HealthCheck) | ✅ 정적. 안전 |
| `config/views.py:90` | `cursor.execute("SELECT 1")` (HealthCheck) | ✅ 정적. 안전 |

### 2.2 ORM 사용 패턴 점검

- `Stock.objects.filter(symbol__icontains=...)`, `Q(stock_name__icontains)` 등은 Django ORM 파라미터화 — 안전
- `symbol.upper()` + `get_object_or_404(Stock, symbol=symbol.upper())` 규칙(CLAUDE.md)이 일관 적용됨

**SQL 인젝션 등급: 모두 PASS. 결함 없음.**

---

## 3. LLM 프롬프트 인젝션

### 3.1 [MED] `thesis/services/thesis_builder.py:422-483` `_parse_free_input`

- 사용자 자유 입력 → Gemini 프롬프트에 `f"입력: \"{safe_text}\""` 로 직접 삽입
- **방어**:
  - L435: `safe_text = text[:500].replace('```', '').replace('---', '').strip()` (길이 + 일부 구분자 제거)
  - L455-456: `temperature=0.3`, `max_output_tokens=1000`
  - L475: `re.search(r'\{.*\}', response_text, re.DOTALL)` 로 JSON 추출
- **남은 위험**:
  - `"`, 줄바꿈, 다른 escape, "Ignore previous instructions" 류 자연어 인젝션 미차단
  - 응답 JSON 파싱 후 `direction`, `target_type` 등을 그대로 사용 — 다운스트림에서 enum 검증 필요(현재는 fallback에서 기본값 사용으로 부분 완화)
- **권장**: system prompt 분리(가능 시) + 응답 enum 화이트리스트 강제 + 사용자 입력 escape (`"` → `\"`) 추가

### 3.2 [MED] `thesis/views/conversation_views.py:191-303` `NewsIssuesView`

- 외부 뉴스 제목 8개를 `prompt = f"""... {title_list} ..."""` 로 LLM에 주입
- **방어**: `t["title"][:80]` 길이 컷, `response_mime_type="application/json"`, `temperature=0.2`
- **남은 위험**: 뉴스 제목 자체가 인젝션 페이로드일 수 있음 (간접 인젝션, Indirect Prompt Injection). 제3자 뉴스 소스 신뢰 정도에 의존.
- **등급**: 사용자 직접 주입 아님 → 본질적으로는 LOW이지만 다운스트림 effect(가설 생성)가 크므로 MED 유지

### 3.3 [LOW] `news/services/keyword_extractor.py:184-199`

- 뉴스 본문 요약 100건을 LLM에 주입. 사용자 직접 통제 불가 → 간접 인젝션 표면.
- `summary[:300]` 컷으로 일부 완화.

### 3.4 [GOOD] 입력 검증 모범 사례

- `thesis/views/conversation_views.py:40-108`: `_sanitize_conversation_state`, `_sanitize_llm_state`가 매우 견고
  - 허용 키 화이트리스트, entry_source 화이트리스트, history 길이 제한(20), `MAX_STATE_SIZE=50_000`, turn_count 범위 0–50
  - JSON serialization 후 크기 측정으로 폭주 차단
- 다른 LLM 호출 영역에서도 동일 패턴 채택 권장

---

## 4. 시크릿 관리

| 항목 | 상태 | 근거 |
|------|------|------|
| `.env` 권한 | ✅ `-rw-------` (0600) | `ls -la .env` |
| `.env` gitignore | ✅ 포함 | `.gitignore:7-9` `# API KEY\n.env` |
| SECRET_KEY 운영 가드 | ✅ Dev 폴백 + `if not DEBUG` 시 `ImproperlyConfigured` | `config/settings.py:142-165` |
| JWT_SIGNING_KEY 분리 | ✅ `SECRET_KEY`와 분리, fallback만 동일 | `config/settings.py:148` |
| NEO4J_PASSWORD 운영 가드 | ✅ DEBUG=False에서 누락 시 즉시 실패 | `config/settings.py:166-170` |
| 코드 내 하드코딩 시크릿 | ✅ 검색 결과 무 | `grep -rE "API_KEY|PASSWORD|SECRET|TOKEN"` → 모두 `os.getenv`/Histogram label 등 무관 항목 |
| DB_PASSWORD 기본값 | ✅ `os.getenv('DB_PASSWORD', '')` (빈 문자열 fallback — 로컬 trust 인증 호환) | `config/settings.py:254` |

**시크릿 관리 등급: 양호**. 단, **로그 출력 시 시크릿 마스킹 정책**은 별도 점검 가치 있음 (이번 감사 범위 밖).

---

## 5. CORS / DEBUG / 에러 노출

### 5.1 [GOOD] CORS

- `config/settings.py:311-318`:
  - `CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']`
  - `CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False').lower() == 'true'`
  - DEBUG 의존 제거 (주석에 의도 명시) → 운영 의도치 않은 전체 허용 차단 ✅

### 5.2 [GOOD] DEBUG

- `config/settings.py:151`: `DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'` — 기본값 False ✅

### 5.3 [MED] ALLOWED_HOSTS DEBUG-only wildcard

- `config/settings.py:153-155`:
  ```python
  ALLOWED_HOSTS = [...] or (['*'] if DEBUG else [])
  ```
- DEBUG=True 환경에서 wildcard 허용 — 개발 의도. 운영(DEBUG=False)에서는 환경변수 미설정 시 빈 리스트 → Django가 403 응답. 안전 가드 동작.
- **권장**: 운영 배포 가드에 `if not ALLOWED_HOSTS: raise ImproperlyConfigured(...)` 추가하면 누락 즉시 인지 가능.

### 5.4 [LOW] 에러 메시지에 원본 예외 노출

여러 view에서 `except Exception as e: return Response({'error': str(e) or f'... {str(e)}'})` 패턴 발견:

- `stocks/views.py:215-218` (Search), `:332-336` (Chart), `:594-606` (Overview details에 `original_error: str(e)`), `:677-681` (BalanceSheet), `:751-755` (Income), `:823-827` (Cash flow)
- `api_request/admin_views.py:77, 104, 127, 155, 184, 237, 273`: `{"error": str(e)}`

내부 예외 메시지가 응답에 그대로 노출되면 스택 정보·내부 경로·라이브러리 버전이 유출될 수 있다. `EXCEPTION_HANDLER = 'config.exception_handler.custom_exception_handler'`(L366)가 envelope을 표준화하지만 위 view 들은 직접 `Response({'error': str(e)})`를 반환하므로 envelope 우회 가능.

**권장**: `str(e)` 노출 금지 — 로그에만 남기고 응답은 일반화된 메시지 + 트레이스 ID.

### 5.5 [LOW] HealthCheck 정보 노출

- `api_request/admin_views.py:277-344` `HealthCheckView`(permission_classes=[]): DB/Redis/Provider 상태를 비인증 조회. 내부 구성요소 식별 정보 노출.
- 운영망 외부 노출 여부에 따라 등급 조정. 보통 internal load-balancer 헬스체크에 한정한다.

---

## 6. 추가 점검: Cost Amplification (OWASP A04 — Insecure Design)

- 1.4 의 LLM 트리거 무인증 (CRITICAL) + Celery 태스크 무인증 트리거가 가장 큰 운영 위험
- `stocks/views.py:888-895` `StockSyncAPIView`는 명시적으로 `IsAuthenticated` + `UserRateThrottle` (cost amplification 가드) — 모범 사례
- 동일 패턴을 serverless `trigger_*`, `extract_*`, `generate_*` 엔드포인트에 적용해야 함

---

## 7. 우선순위별 권고 액션

### 즉시 (CRITICAL) — 24h 내 권장

1. `serverless/views.py:2392-2395` `extract_relations_from_news_api`: `permission_classes = [IsAdminUser]` 또는 최소 `IsAuthenticated` + 커스텀 throttle
2. `serverless/views.py:1598-1601` `generate_thesis`: 인증 필수화

### HIGH — 1주 내

3. `serverless/views.py:870-1095` Screener Preset CRUD (`screener_presets_api`, `screener_preset_detail`, `execute_preset`, `advanced_screener_api`): `IsAuthenticated` + `request.user` 기반 owner 체크 (BOLA 차단)
4. `serverless/views.py:1931, 2033, 2363` ETF/Theme 트리거 POST 3종: `IsAdminUser`
5. `serverless/views.py:1786` `get_shared_thesis`: 공유 코드 추측 가능성 점검 (UUID 길이/엔트로피 확인)

### MED — 2주 내

6. `thesis/services/thesis_builder.py:435` LLM 인젝션 가드 강화: `"` escape + system prompt 분리 + 응답 enum 화이트리스트
7. 7개 stocks/views_* + chainsight/api/views.py 의 `APIView`에 명시적 `permission_classes` 추가 (defense-in-depth)
8. 직접 `Response({'error': str(e)})` 반환하는 view → custom_exception_handler 위임으로 통일
9. `ALLOWED_HOSTS` 운영 빈 리스트일 때 ImproperlyConfigured 가드 추가

### LOW — 다음 정기 PR

10. 외부 뉴스→LLM 간접 인젝션 모니터링 로그 추가
11. `HealthCheckView` 외부망 노출 정책 결정

---

## 8. 변경되지 않아도 좋다고 판단된 항목 (False Positive)

- macro/views.py 9개 `AllowAny`: 거시경제 데이터는 공개 정책으로 의도된 노출
- stocks/views_market_movers.py:40 `AllowAny`: Market Pulse 공개 정책
- HealthCheckView 의 `permission_classes = []`: 의도된 헬스체크
- 4개 cursor.execute: 파라미터 바인딩 또는 정적 쿼리로 안전

---

## 9. 부록 — 점검 명령 재현

```bash
# SQL 인젝션 후보 위치
find . -name '*.py' -not -path './.venv/*' | xargs grep -l 'cursor.execute' | head

# 17개 views 권한 매핑
for f in <17 files>; do
  grep -nE 'class .*(APIView|ViewSet)|permission_classes|@permission_classes' "$f"
done

# 시크릿 하드코딩 (false positive 필터링)
grep -rE '(API_KEY|PASSWORD|SECRET|TOKEN)' --include='*.py' . | \
  grep -v 'os.getenv\|os.environ\|settings\.\|getattr\|getenv' | \
  grep -vE '\.env|test_|migrations/|node_modules'

# LLM 호출 파일
grep -rl 'genai\|gemini\|GEMINI' --include='*.py' .
```

---

**감사 종료**. 본 보고서는 읽기 전용 감사 결과이며 코드는 수정되지 않았다. 다음 정기 감사(2026-05-17)에서 위 액션 진행률을 비교 추적할 것.
