# Stock-Vis 보안 감사 보고서

- **작성일**: 2026-05-23
- **대상 브랜치**: `slice14`
- **범위**: OWASP Top 10 + LLM 프롬프트 인젝션 + 시크릿 관리
- **모드**: 읽기 전용 정적 감사 (코드 수정 없음)
- **감사자**: Claude (자동 감사)

---

## 요약 (Executive Summary)

| 심각도 | 건수 | 비고 |
|--------|-----:|------|
| CRITICAL | **0** |  |
| HIGH | **3** | LLM AllowAny 비용 폭주 / preset IDOR / 글로벌 Throttle 미적용 |
| MED | **5** | 스트림 응답 에러 메시지 노출, IsAuthenticatedOrReadOnly, 등 |
| LOW | **3** | ALLOWED_HOSTS=['*'] (DEBUG 한정), Health 미인증 등 |
| INFO | **4** | 잘된 점 — 운영 가드, 파라미터 바인딩, 프롬프트 정제 |

**전반 평가**: 인증/시크릿/SQL 인젝션 기본기는 양호. 가장 큰 위험은 **인증 없이 호출 가능한 LLM 엔드포인트군**(portfolio coach E1~E6, serverless `generate_thesis`)이며, 글로벌 throttle 미설정과 결합해 외부 LLM 비용 폭주(DoW)와 프롬프트 인젝션 표면을 동시에 노출.

---

## 사전 파악 결과

```
$ grep -rl 'cursor.execute' --include='*.py'
chainsight/services/seed_selection.py
serverless/services/admin_status_service.py
api_request/admin_views.py
config/views.py

$ grep -rl 'permission_classes' --include='*.py' (views*.py) → 26개
```

DRF 기본 권한은 `IsAuthenticated` (config/settings.py:353), 명시적 `[AllowAny]` 또는 `@authentication_classes([])` 없는 뷰는 모두 인증 필요. 이 기반 위에서 예외만 검사함.

---

## 1. 인증/인가 (A01:2021 — Broken Access Control)

### [HIGH-1] LLM 호출 엔드포인트가 무인증 + Throttle 미적용

**위치**:
- `portfolio/api/views.py:51-326` — `coach_e1` ~ `coach_e6` 6개 모두 `@permission_classes([AllowAny])` + `throttle_classes` 미설정
- `serverless/views.py:1598-1708` — `generate_thesis`: `@authentication_classes([])` + `AllowAny`

**문제**:
- 외부 LLM(Anthropic Claude / Gemini) 호출 → **요청당 직접 비용 발생**
- `LLMBudgetExceededError` 처리(429)는 있으나 **요청 전 차단 없이 LLM 호출 진입 → 사후 차단**
- 익명 사용자가 곡선 자동화로 분당 수십~수백 회 호출 시 일일 LLM 예산 소진
- `coach_e5` (`portfolio/api/views.py:200`): adjustment_parser 호출 → 사용자 free-text 파싱 (프롬프트 인젝션 표면 동시 노출)

**영향**: 재무 DoW (Denial of Wallet), 잠재적 프롬프트 인젝션
**권장**:
1. 최소 `IsAuthenticated` 강제 (Anonymous = 호출 자체 차단)
2. 뷰별 `throttle_classes = [...]` 명시 (anon 0/min 권장 또는 별도 LLM scope ScopedRateThrottle)
3. `settings.py:356-362` 의 `market_pulse_llm: 5/min`처럼 LLM 전용 scope 도입 후 portfolio/thesis에도 적용

---

### [HIGH-2] Screener Preset IDOR (소유자 없는 preset의 PATCH/DELETE 무인증 노출)

**위치**: `serverless/views.py:925-973` (`screener_preset_detail`)

**문제 코드**:
```python
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def screener_preset_detail(request, preset_id):
    ...
    elif request.method == 'PATCH':
        if preset.user and preset.user != request.user:   # ← preset.user가 None이면 통과
            raise PermissionDenied("You can only edit your own presets")
```

- `preset.user` 가 None인 시스템/공용 preset에 대해 `if preset.user and ...` 단락 평가로 권한 체크 미통과 → 익명 사용자가 PATCH/DELETE 가능
- DELETE는 `category in ['system', 'beginner', 'intermediate']` 가드가 있으나, **그 외 카테고리의 `preset.user=None` preset은 익명 삭제 허용**
- `request.user`는 익명일 때 `AnonymousUser` — 동등성 비교가 의도대로 작동하지 않음

**영향**: 공용 preset 무단 수정/삭제, 데이터 무결성 손상
**권장**: `permission_classes=[IsAuthenticated]` 로 변경하거나, PATCH/DELETE 진입 즉시 `if not request.user.is_authenticated: raise PermissionDenied` 추가. None-owner preset은 staff만 수정 가능하게 분기.

---

### [HIGH-3] DRF Throttle 글로벌 미적용

**위치**: `config/settings.py:343-367`

- `DEFAULT_THROTTLE_RATES`는 정의됨 (`user: 60/min`, `anon: 20/min` 등)
- 그러나 `DEFAULT_THROTTLE_CLASSES`가 **REST_FRAMEWORK 딕셔너리에 누락** → rate 정의만 있고 적용 안 됨
- 결과: 뷰가 명시적으로 `throttle_classes`를 선언한 곳(`marketpulse/*`, `users/*` Watchlist, `stocks/views.py:896` 등) 외에는 **익명 호출이든 인증 호출이든 무제한**

**영향**: 자격증명 스터핑, 봇 트래픽, LLM/API 키 소진 모두 노출
**권장**: `'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle', 'rest_framework.throttling.AnonRateThrottle']` 추가. 이미 정의된 rate가 즉시 활성화됨.

---

### [MED-1] StockOverviewAPIView가 IsAuthenticatedOrReadOnly

**위치**: `stocks/views.py:478`

- GET이 무인증 허용 → 종목 개요 무제한 조회 (FMP API fallback 호출 포함)
- FMP API 호출 비용/쿼터에 의존. anon throttle 미적용(HIGH-3) 시 외부 쿼터 소진 가능
- 권장: `IsAuthenticated` 로 변경 또는 anon throttle 강력 적용 + 캐시 우선 정책 강화

### [MED-2] Validation PeerPreferenceView가 IsAuthenticatedOrReadOnly

**위치**: `validation/api/views.py:461`

- POST/DELETE 내부에서 직접 `if not request.user.is_authenticated` 가드는 있으나, **클래스 레벨에서 `IsAuthenticatedOrReadOnly`이므로 GET이 비활성 사용자에게 열림**
- GET 핸들러가 명시적으로 노출되지 않은 듯하나, DRF 메서드 라우팅상 의도 불명확. 권한 정책 정합성 결함
- 권장: `IsAuthenticated` 통일

### [LOW-1] HealthCheckView 무인증 (의도)

**위치**: `api_request/admin_views.py:283` (`permission_classes = []`)

- 의도된 공개 endpoint. DB SELECT 1 / Cache check만 수행. 내부 정보 노출 표면 작음.
- 단, `config/views.py:73 health_check` 도 동일 패턴이 있어 두 곳 중복. 통합 권장 (스코프 정합)

### [LOW-2] AllowAny가 명시된 공개 API군

**위치**:
- `macro/views.py` 10개 view 전부 (`AllowAny`)
- `serverless/views.py` market_movers, sector_heatmap, screener_filters 등 다수

대부분 시장 공개 데이터로 의도된 노출이며 그 자체로 위험은 낮음. **단 HIGH-3 throttle 미적용과 결합 시 외부 API 쿼터 소진 표면**이 됨.

---

## 2. 인젝션 (A03:2021 — Injection)

### [INFO-1] cursor.execute() 4곳 모두 안전

| 파일 | 위치 | 패턴 | 결과 |
|---|---|---|---|
| `config/views.py:90` | health check | `cursor.execute("SELECT 1")` | 정적 SQL, 안전 |
| `api_request/admin_views.py:300` | health check | `cursor.execute("SELECT 1")` | 정적 SQL, 안전 |
| `serverless/services/admin_status_service.py:833` | DB 사이즈 통계 | `cursor.execute("SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 30")` | 정적 SQL, 안전 (관리자 전용 view) |
| `chainsight/services/seed_selection.py:152-179` | 거래량 급등 seed | `cursor.execute("""...""", [market_date, market_date])` | **파라미터 바인딩 사용, 안전** |

ORM 우회 raw SQL은 `seed_selection.py` 한 군데만 사용되며 `%s` 자리표시자 + 인자 list로 정상 바인딩. **SQL 인젝션 위험 없음.**

### [INFO-2] ORM 사용 패턴 양호

`Stock.objects.get(symbol=symbol.upper())` 등 모든 검색은 ORM. `symbol.upper()` 정규화도 일관 적용. `Q()`/`filter()`에 raw f-string 삽입 없음.

---

## 3. LLM 프롬프트 인젝션

### [HIGH-1과 결합] 인증 없는 LLM 엔드포인트의 프롬프트 인젝션 표면

- `serverless/views.py:1598 generate_thesis`: `stocks`, `filters`, `user_notes`가 모두 사용자 입력 → `ThesisBuilder.build_thesis()` 로 전달
- `portfolio/api/views.py:200 coach_e5`: 사용자 free-text → `e5_adjustment_parser`로 LLM 파싱
- 인증 부재(HIGH-1)와 결합 → 외부 익명 사용자가 프롬프트 인젝션 시도 가능

### [INFO-3] 사용자 입력 정제 패턴 존재

**잘 된 곳**:
- `thesis/services/indicator_matcher.py:175-183` — `_sanitize_for_prompt()` 함수: 길이 제한(500), `\`\`\`` / `---` 등 구분자 제거
- `thesis/views/conversation_views.py:40-108` — `_sanitize_conversation_state`, `_sanitize_llm_state`: 허용 키 화이트리스트, `MAX_STATE_SIZE=50_000`, `MAX_HISTORY_LENGTH=20`, `turn_count` 범위 검증
- LLM 호출 시 `system_instruction=system_prompt` 패턴(예: `news/services/keyword_extractor.py:194`, `thesis/services/prompt_builder.py:570/799/966`) — system/user 메시지 분리 → 인젝션 저항도 ↑

### [MED-3] 정제 미적용 영역

**대상**:
- `serverless/services/thesis_builder.py` — `stocks[*].company_name`, `user_notes` 등을 LLM prompt에 어떤 정제 없이 삽입하는지 미확인. (`generate_thesis` 진입점)
- `news/services/news_deep_analyzer.py` — 외부 뉴스 제목/요약을 LLM에 직접 주입 (외부 적대 입력 → 간접 prompt injection 표면)
- `rag_analysis/views.py:475 ChatStreamView.post`: `message = request.data.get('message', '').strip()` → 빈값 검증만 있고 길이 상한 / 제어문자 필터 없음. 인증은 있어 위험도 ↓

**권장**:
- LLM에 사용자 텍스트를 넣는 모든 경로에 `_sanitize_for_prompt` 공통 유틸을 통과시키기 (현재 indicator_matcher에만 있음)
- system_instruction 분리 + JSON-only 응답 강제 (이미 일부 적용됨)
- 사용자 입력은 prompt 내 명확한 구분자(`<USER_INPUT>...</USER_INPUT>`) 안에 캡슐화

---

## 4. 시크릿 관리

### [INFO-4] 시크릿 관리 양호

- `.env` 는 `.gitignore`에 포함 (root `.gitignore` 11~12행 `# API KEY` → `.env`)
- `git ls-files | grep .env` → 결과 없음. **커밋 이력에도 .env 부재**
- `.env.example` 만 트래킹됨 (4814 bytes)
- 모든 키는 `os.getenv()` 호출 (FMP, ANTHROPIC, GEMINI, FRED, NEO4J, EMAIL, DB) — 하드코딩 없음
- 운영 가드: `DEBUG=False`에서 `SECRET_KEY`, `NEO4J_PASSWORD` 누락 시 `ImproperlyConfigured`로 즉시 실패 (`config/settings.py:158-170`)
- `JWT_SIGNING_KEY` 가 `SECRET_KEY`와 분리됨 → 키 회전 분리 가능 (`config/settings.py:148`)

### [LOW-3] 개발용 SECRET_KEY fallback이 코드에 존재

**위치**: `config/settings.py:143`
```python
_SECRET_KEY_DEV_FALLBACK = 'django-insecure-DEV-ONLY-DO-NOT-USE-IN-PRODUCTION-' + 'x' * 30
```

- 운영 가드가 즉시 차단하므로 실질적 위험 없음
- 그러나 코드에 fallback 패턴이 보이면 사회공학적 / 운영 실수 표면(env 누락 + DEBUG=True 배포)이 됨
- 권장: dev 환경도 `os.getenv` 필수화 + `python manage.py runserver` 시작 스크립트가 randomized key 주입

---

## 5. CORS / XSS / 에러 노출 (A05:2021 — Security Misconfiguration)

### [INFO-5] CORS 설정 양호

- `CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']` (`settings.py:311-314`)
- `CORS_ALLOW_ALL_ORIGINS`은 별도 env(`DJANGO_CORS_ALLOW_ALL`)로 명시 제어. DEBUG 의존 제거됨 (settings.py:316-318) → **운영 배포 시 실수로 전체 허용 가능성 차단됨**
- `CORS_ALLOW_CREDENTIALS = True` + `CORS_ALLOWED_ORIGINS` 화이트리스트 → 정상 패턴

### [LOW-4] DEBUG 모드에서 ALLOWED_HOSTS=['*']

**위치**: `config/settings.py:151-155`
```python
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [...env...] or (['*'] if DEBUG else [])
```

- 운영 default가 `False`이므로 안전. 그러나 DEBUG=True로 배포 시 `*`로 열림.
- DEBUG=False에서 `DJANGO_ALLOWED_HOSTS` 누락 시 빈 리스트 → Django가 모든 요청 400 반환 (안전한 fail-closed)

### [MED-4] ChatStreamView 에러 메시지가 그대로 클라이언트로 전송

**위치**: `rag_analysis/views.py:516-532`
```python
except Exception as e:
    events.append({'phase': 'error', 'error': {'code': 'PIPELINE_ERROR', 'message': str(e)}})
```

- 파이프라인 내부 예외 메시지(`str(e)`)가 SSE 스트림으로 그대로 응답됨
- DB 컬럼명, 내부 경로, 네오포지 쿼리 정보 등이 노출될 수 있음
- 권장: 사용자에게는 일반 메시지(`내부 오류가 발생했습니다`), 상세는 로깅만

### [MED-5] generate_thesis fallback에서 예외 메시지 노출

**위치**: `serverless/views.py:1700-1704`
```python
'warning': f'LLM 생성 실패로 기본 테제가 생성되었습니다. (에러: {type(e).__name__}: {str(e)[:100]})',
```

- 예외 클래스명 + 메시지 100자 슬라이스를 응답에 포함
- 100자 제한이 있어 노출도 제한적이나 API 키 만료/네트워크 에러 등 운영 정보 일부 누출
- 권장: 사용자 응답에서 `type(e).__name__: str(e)` 제거, 로그만

### [INFO-6] DRF Exception Handler 양호

`config/exception_handler.py` — 표준 envelope(`{detail, code?, errors?, status_code}`) 생성. `ValidationError` 외에는 메시지 일반화. 스택트레이스 노출 없음.

---

## 6. 그 외 관찰

### [INFO-7] DEFAULT_PERMISSION_CLASSES = IsAuthenticated (잘된 결정)

`config/settings.py:353` — 화이트리스트 패턴. 명시 안 한 view는 자동으로 잠김. **이전 감사 P0 #5**의 결과로 보이며 적절.

### [INFO-8] Watchlist IDOR 패치 확인됨

기존 common-bugs #21 영역(`users/views.py:587~`) — 모든 Watchlist view가 `Watchlist.objects.get(pk=pk, user=request.user)` 로 항상 user-scoped lookup. IDOR 해소됨.

### Throttle scope 정책 미일관

- marketpulse만 자체 scope 적용 (`MarketPulseUserThrottle`, `MarketPulseHourThrottle`, `market_pulse_llm`)
- Watchlist는 `WatchlistRateThrottle`
- portfolio coach / serverless generate_thesis 등 LLM 호출 endpoint는 throttle 없음
- 일관된 LLM-throttle scope (예: `llm_anon: 5/min`, `llm_user: 30/min`)를 settings에 정의하고 모든 LLM 엔드포인트에 일괄 적용 권장

---

## 우선순위별 조치 권장 (Action Items)

### 즉시 (HIGH)
1. **HIGH-1**: `portfolio/api/views.py` 6개 + `serverless/views.py:1599 generate_thesis` → `IsAuthenticated` 강제 + LLM 전용 throttle scope 도입
2. **HIGH-2**: `serverless/views.py:925 screener_preset_detail` → PATCH/DELETE 진입 즉시 `request.user.is_authenticated` 가드 + None-owner preset은 staff만 수정
3. **HIGH-3**: `config/settings.py` REST_FRAMEWORK 딕셔너리에 `'DEFAULT_THROTTLE_CLASSES'` 추가 (UserRateThrottle + AnonRateThrottle)

### 1주 내 (MED)
4. **MED-1**: `stocks/views.py:478 StockOverviewAPIView` → IsAuthenticated 전환 또는 anon throttle 5/min
5. **MED-2**: `validation/api/views.py:461 PeerPreferenceView` → `IsAuthenticated` 통일
6. **MED-3**: `serverless/services/thesis_builder.py`, `news/services/news_deep_analyzer.py` 의 LLM 입력 정제 (`_sanitize_for_prompt` 공통화)
7. **MED-4**: `rag_analysis/views.py:516` 에러 메시지 일반화
8. **MED-5**: `serverless/views.py:1700` warning에서 예외 메시지 제거

### 검토 (LOW)
9. **LOW-1/4**: 운영 가드 점검 — HealthCheck endpoint 통합, DEBUG=True 배포 차단 검증
10. **LOW-3**: dev SECRET_KEY fallback 제거, 시작 스크립트로 randomized key 주입

---

## 부록 A — 사용 도구 & 명령

```bash
grep -rl 'cursor.execute' --include='*.py' .                 # 4 hits (모두 안전)
grep -rl 'permission_classes' --include='*.py' (views) .     # 26 files
grep 'AllowAny|@authentication_classes' --include='*.py' .   # serverless 17, macro 10, portfolio 6
git ls-files | grep -E '\.env$|credentials|secret'           # 0 hits (커밋 없음)
```

## 부록 B — 검증되지 않은 영역 (Out-of-Scope / Limitations)

- **Celery tasks.py / consumers.py 보안**: 본 감사에서 다루지 않음
- **Frontend XSS**: Next.js 측 정적 분석 미포함
- **Neo4j Cypher 인젝션**: rag_analysis/neo4j_service.py, chainsight/services/neo4j_*.py 의 Cypher 쿼리 별도 점검 권장
- **JWT 토큰 lifetime**: ACCESS 60min / REFRESH 7d. rotate + blacklist 활성. 정상이나 짧은 access(15분) 권장 검토
- **운영 인프라**: 컨테이너/네트워크/시크릿 매니지먼트는 별도 인프라 감사 대상

---

**감사 종료**. 본 보고서는 정적 코드 감사 결과이며, 동작 검증/펜테스트는 별도 수행 권장.
