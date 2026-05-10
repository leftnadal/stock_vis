# Stock-Vis 보안 감사 보고서 — 2026-05-10

- 감사 범위: OWASP Top 10 기반 정적 코드 감사 (읽기 전용)
- 감사자: Claude (자동화 nightly audit)
- 대상 브랜치: `portfolio`
- 코드 수정: 없음 (감사 보고서 생성만)

---

## Executive Summary

| 심각도 | 건수 | 주요 항목 |
|--------|------|----------|
| CRITICAL | 0 | — |
| HIGH | 2 | 비인증 sync 엔드포인트 abuse, 헬스체크 raw 에러 노출 |
| MED | 4 | LLM 프롬프트 인젝션 sanitization 부재, 명시적 permission 누락 8건, 검색 view str(e) 노출, JWT_SIGNING_KEY fallback |
| LOW | 3 | ALLOWED_HOSTS 와일드카드 (DEBUG only), CORS 환경의존, Cypher 동적 depth |
| INFO | 5 | SECRET_KEY/NEO4J_PASSWORD startup 가드 양호, cursor.execute 안전, .env gitignore, 글로벌 IsAuthenticated 디폴트, Admin views 일관된 IsAdminUser |

핵심 결론:
- **글로벌 기본 권한이 `IsAuthenticated`로 설정**되어 있어 (`config/settings.py:353-355`) 명시적 `permission_classes` 누락 view들도 사실상 인증 보호됨. 회귀 위험만 잠재.
- **하드코딩된 시크릿 없음**, `.env`는 `.gitignore` 등록됨.
- **즉시 조치 필요한 노출은 2건** (HIGH-1: `/api/v1/health/`의 raw exception leak, HIGH-2: `StockSyncAPIView` 비인증 외부 API 트리거).

---

## 1. 인증/인가 (OWASP A01: Broken Access Control)

### HIGH-1. `StockSyncAPIView` 비인증 외부 API 트리거 가능

- 파일: `stocks/views.py:878-886`
- 현황: `permission_classes = []` (글로벌 디폴트 우회). POST 요청으로 임의 symbol에 대해 FMP 등 외부 API 호출 트리거 가능.
- 영향: **API 비용 abuse**, 외부 provider rate limit 소진(현재 FMP Starter Plan 300/min, 10,000/day), DoS 인접 영역.
- 증거:
  ```python
  # stocks/views.py:886
  permission_classes = []  # 명시적 비활성화
  def post(self, request, symbol):
      # 외부 API → DB 저장 트리거
  ```
- 권고:
  - 최소: `IsAuthenticated` + `UserRateThrottle`(예: 10/min) 적용.
  - 권장: 관리/배치는 Celery task로 위임하고, 외부 노출은 read-only로 제한.

### HIGH-2. `HealthCheckView` 비인증 + raw exception 노출

- 파일: `api_request/admin_views.py:277-327`, `config/views.py:73-105`
- 현황: 인증 불필요 헬스체크 (모니터링 정당). 그러나 실패 시 `str(e)`로 raw 예외 메시지 응답 본문에 노출.
- 영향: DB host/port/사용자, 캐시 백엔드 정보, 내부 모듈 경로가 외부에 누출 가능. **A09 (Security Logging/Monitoring failures) + A05 (Security Misconfiguration)** 동시 해당.
- 증거:
  ```python
  # api_request/admin_views.py:305-309
  except Exception as e:
      health_status["components"]["database"] = {
          "status": "unhealthy",
          "error": str(e)   # ← raw exception
      }
  # 같은 패턴 line 322-326 (cache)
  ```
- 권고:
  - 외부 헬스 응답은 status enum (`healthy|unhealthy|degraded`)만 노출.
  - 상세 에러는 서버 로그에만 기록.
  - 또는 `/api/v1/health/`는 컴포넌트별 상태 boolean만 반환하고, 디테일은 `IsAdminUser` 보호된 별도 endpoint에 분리.

### MED-1. `chainsight/api/views.py` 8개 APIView 명시적 permission 누락

- 파일: `chainsight/api/views.py` (`ChainSightGraphView`, `ChainSightSuggestionView`, `ChainSightTraceView`, `SeedListView`, `SectorGraphView`, `NeighborGraphView`, `SignalFeedView` 등)
- 현황: 모든 view에 `permission_classes` 미선언. 현재는 `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` (`config/settings.py:353-355`)로 보호됨. **즉각적 노출 없음**.
- 영향: 글로벌 디폴트 변경 시 자동 노출되는 회귀 위험.
- 권고:
  - 각 클래스에 `permission_classes = [IsAuthenticated]` 명시.
  - 공개 의도라면 `[AllowAny]` 명시 (현재 `users/views.py:114`처럼 명시 코멘트와 함께).
  - 현재 일관성 깨짐: 같은 디렉토리 `chainsight/views/watchlist_views.py`는 명시되어 있음.

### INFO-1. 명시 디폴트 정상 (false-positive)

- `news/views.py`, `validation/views.py`, `chainsight/views.py`는 빈 placeholder (실제 라우팅 없음). 검사 도구 grep에서 false positive.
- `users/views.py:114` (`UserDetailView`): 명시적 `[AllowAny]` + 코멘트 — audit P0 #5 의도된 공개 프로필. OK.
- `news/api/views.py`의 `market-feed`, `interest-options` action: `[AllowAny]` 명시 + 콜드/온보딩 용도 코멘트. OK.

---

## 2. 인젝션 (OWASP A03: Injection)

### INFO-2. `cursor.execute()` 4건 모두 안전

| 파일 | Line | 내용 | 평가 |
|------|------|------|------|
| `chainsight/services/seed_selection.py` | 152 | `WHERE date = ... <= %s` | %s 파라미터 바인딩 (인자 분리). **안전** |
| `serverless/services/admin_status_service.py` | 833 | `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY ... LIMIT 30` | 정적 SQL, 외부 입력 없음. **안전** |
| `api_request/admin_views.py` | 300 | `SELECT 1` | 정적 SQL. **안전** |
| `config/views.py` | 90 | `SELECT 1` | 정적 SQL. **안전** |

### LOW-1. Neo4j Cypher: 동적 depth f-string (제한됨)

- 파일: `chainsight/api/views.py:199-210` (`ChainSightTraceView`)
- 현황: `*..{min(max_depth, 5)}` — 사용자 입력 `max_depth`를 f-string에 직접 삽입. 단 `min(..., 5)`로 상한 강제 + `int()` 변환되므로 인젝션 표면 없음.
- 추가 검토: 같은 파일 `NeighborGraphView`의 `rel_filter`는 별도 변수로 빌드 후 `{rel_filter}` 삽입 (line 510, 517). `rel_filter` 자체는 고정 문자열만 들어가고, 사용자 값은 `$rel_types` 파라미터 바인딩으로 전달 — **안전**.
- 권고: 가독성을 위해 Cypher의 가변 길이 패턴은 별도 공식 패러미터화 패턴 사용 검토 (현재는 안전).

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01)

### MED-2. 사용자 입력이 system prompt에 sanitization 없이 결합

대다수 prompt 빌더가 사용자 입력(가설 제목/전제 본문/뉴스 제목 등)을 별도 escaping 없이 f-string으로 prompt에 결합한다. 한 곳만 부분적 방어 적용:

- 방어 적용된 곳: `thesis/services/thesis_builder.py:434`
  ```python
  safe_text = text[:500].replace('```', '').replace('---', '').strip()
  ```
  500자 제한 + 코드펜스/구분자 제거. **부분 방어**.

- 방어 누락된 주요 prompt 빌더:
  - `thesis/services/prompt_builder.py:613-688` — `collected.title`, `s.summary`, `p.title`, `p.description` 등 사용자 입력을 sanitization 없이 컨텍스트에 결합.
  - `thesis/services/prompt_builder.py:822` — `build_suggestion_prompt(news_title, keyword, summary, sentiment)` — 뉴스 본문/키워드가 외부 origin인데 escaping 없음.
  - 동일 패턴: `thesis/services/indicator_matcher.py`, `serverless/services/keyword_service.py`, `serverless/services/relationship_keyword_enricher.py` (sanitize 함수 미참조).

영향:
- 최악 시나리오: 사용자가 가설 제목/전제 본문에 prompt 인젝션 페이로드 삽입 → 모델이 system 지시 무시 → 잘못된 JSON 산출 → 잘못된 가설 생성/등록.
- **RCE/SSRF/데이터 유출 표면은 없음** — 응답은 JSON 파싱 후 모델 필드에 저장되며, 다음 외부 시스템 호출 트리거에 영향을 주지 않음.

권고:
1. 공통 sanitizer 함수 추가 (예: `thesis/services/_safe.py`):
   - 길이 제한 (모듈별 256~1024)
   - 코드펜스/system 구분자 제거 (` ``` `, `---`, `<|im_start|>`, `assistant:` 등)
   - 줄바꿈 압축
2. 모든 사용자 입력 결합 지점에서 sanitizer 일관 적용.
3. JSON 응답 파싱 실패 시 `_fallback_parse` 호출 패턴 (`thesis_builder.py:466,470,476`)은 잘 되어 있음 — 유지.
4. KB에 LESSON 추가 권장: "LLM prompt에 사용자 입력 직접 결합 금지 — `_safe_text()` 헬퍼 경유".

---

## 4. 시크릿 관리 (OWASP A02: Cryptographic Failures / A05)

### INFO-3. 시크릿 관리 양호

- `.env` 권한: `-rw-------` (소유자 전용) ✓
- `.gitignore`: `.env` 등록 ✓
- `.env.example`: placeholder만 (실제 키 없음) ✓
- `config/settings.py:158-170` — DEBUG=False에서 `SECRET_KEY`/`NEO4J_PASSWORD` 미설정 시 `ImproperlyConfigured` raise. **운영 startup 가드 우수**.
- 하드코딩된 API 키/비밀번호: 발견 안 됨.
- `CELERY_ERROR_RECIPIENTS`에 개인 이메일 2개 노출 (`config/settings.py:528-531`) — 운영 정보로는 의도된 값으로 보이나, 외부 공개 저장소면 PII 우려.

### MED-3. `JWT_SIGNING_KEY`가 `SECRET_KEY`로 fallback

- 파일: `config/settings.py:148`
  ```python
  JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or SECRET_KEY
  ```
- 현황: 분리 의도("위조 공격 표면 축소") 코멘트 있으나 fallback이 되어있어, 운영에서 `JWT_SIGNING_KEY`를 별도 설정하지 않으면 사실상 동일 키 사용.
- 영향: SECRET_KEY 누설 시 JWT 서명까지 자동 노출. 키 회전 시 두 시크릿이 결합.
- 권고: 운영 startup 가드(`if not DEBUG`)에 `JWT_SIGNING_KEY` 미설정 경고 추가, 또는 별도 `ImproperlyConfigured` raise.

---

## 5. CORS / Headers / DEBUG (OWASP A05)

### LOW-2. `ALLOWED_HOSTS = ['*']` (DEBUG=True 한정)

- 파일: `config/settings.py:153-155`
  ```python
  ALLOWED_HOSTS = [...env...] or (['*'] if DEBUG else [])
  ```
- 평가: DEBUG=True에서만 와일드카드, 운영(DEBUG=False)에서는 환경변수 강제 → 정상.
- 권고: 현 구조 유지. `.env` 가이드에 `DJANGO_ALLOWED_HOSTS` 필수 표기 명확화.

### INFO-4. CORS 설정

- `CORS_ALLOWED_ORIGINS`: localhost:3000만 명시 (`config/settings.py:311-314`).
- `CORS_ALLOW_ALL_ORIGINS`: env로 명시 제어 (`DJANGO_CORS_ALLOW_ALL`, default False) — DEBUG 의존 끊고 별도 토글로 유지. **양호**.
- `CORS_ALLOW_CREDENTIALS=True` + 명시 origin list — **양호** (와일드카드 + credentials 조합 위험 없음).

### MED-4. 검색 view에서 raw exception 노출

- 파일: `stocks/views_search.py:86, 141`
  ```python
  return Response({'error': f'서버 오류: {str(e)}'}, status=500)
  ```
- 영향: 외부 provider 응답/내부 모듈 경로/네트워크 정보가 응답 본문으로 누출 가능.
- 권고: `f'서버 오류'`만 반환하고 `logger.exception(...)`로 서버 로그만 남기기.

### INFO-5. Admin views 일관성

- `api_request/admin_views.py`의 5개 view: `IsAdminUser` 일관 적용.
- `serverless/views_admin.py`의 13개 view: 모두 `IsAdminUser` ✓.
- `news/api/views.py`의 ML/관리 endpoint 13개: `IsAdminUser` ✓.

---

## 6. 기타 위험성 점검

### LOW-3. RAG/Chain Sight 응답에 `str(e)` 포함

- `rag_analysis/views.py`: `create_error_response("XXX_ERROR", str(e))` 패턴 다수 (line 593, 604, 676, 732, 763, 835).
- `chainsight/api/views.py:235`: `"error": str(e)` 포함.
- 모두 `IsAuthenticated` 보호되므로 외부 익명자에게 노출되진 않으나, 인증된 사용자에게 내부 traceback fragment 누출.
- 권고: 로그에만 raw 예외, 응답에는 코드 + 사용자 친화 메시지.

### INFO-6. Watchlist/Portfolio/Thesis 등 사용자 자원 view

- 빠르게 스폿 체크한 범위 내에서 `request.user` 기반 ownership 체크 양호.
- 본 audit 깊이로는 IDOR(Insecure Direct Object Reference) 전수조사 미실시 — **다음 nightly 권장 대상**.

---

## Severity 별 조치 우선순위

| 우선 | 항목 | 추천 PR |
|------|------|---------|
| 1 | HIGH-1 `StockSyncAPIView` 인증 추가 + 사용량 throttle | `permission_classes=[IsAuthenticated]` + `UserRateThrottle` |
| 2 | HIGH-2 `HealthCheck`에서 `str(e)` 제거 (응답에서) | error detail은 logger.exception, 응답엔 status enum만 |
| 3 | MED-2 LLM prompt sanitizer 공통 헬퍼 도입 | `thesis/services/_safe.py` + 호출 지점 일괄 적용 |
| 4 | MED-1 chainsight 8개 view에 명시 `permission_classes` | 회귀 방지, 한 번에 패치 |
| 5 | MED-4 `views_search.py` 응답 마스킹 | 2 line 수정 |
| 6 | MED-3 `JWT_SIGNING_KEY` 운영 가드 | settings.py if not DEBUG 블록에 추가 |
| 7 | LOW-3 RAG/Chain Sight error 응답 마스킹 | 일괄 메시지 표준화 |

---

## Appendix A. 검사 커맨드 트레일

```bash
# 1. cursor.execute 전수
grep -rl 'cursor.execute' --include='*.py' .
# → 4건 모두 정적 SQL/%s 파라미터 바인딩 확인

# 2. permission_classes 누락 후보
grep -rL 'permission_classes' --include='views*.py' \
  stocks/ users/ news/ macro/ rag_analysis/ \
  serverless/ validation/ chainsight/ sec_pipeline/
# → 8건 후보 → 빈 파일 3건 false positive 제외 → 5건 분석

# 3. 하드코딩 시크릿
grep -rnE "(api_key|password|secret).{0,20}=.{0,5}['\"][A-Za-z0-9]{16,}['\"]" \
  --include='*.py' . | grep -v os.getenv
# → 0건

# 4. .env 권한
ls -la .env  # rw------- 0600 OK

# 5. DEBUG/CORS 설정
grep -nE 'DEBUG|ALLOWED_HOSTS|CORS' config/settings.py
```

## Appendix B. 글로벌 디폴트 인증 정책 (참고)

```python
# config/settings.py:353-355
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
],
```

이 디폴트 덕에 `permission_classes` 미선언 view도 사실상 보호됨. 본 보고서의 MED-1은 **회귀 방지 차원** 권고.

---

감사 완료 — 즉시 조치 필요 2건 (HIGH), 단기 조치 4건 (MED).
