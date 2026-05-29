# 보안 감사 보고서 — Stock-Vis

- **감사일**: 2026-05-29
- **범위**: OWASP Top 10 기반 백엔드 정적 감사 (읽기 전용, 코드 수정 없음)
- **대상**: Django REST Framework 백엔드 (`config/`, 13개 앱 view/service 레이어)
- **방법**: 정적 분석 (grep 스윕 + 소스 직접 검토). 동적/런타임 테스트는 미수행.

---

## 0. 요약 (Executive Summary)

이 코드베이스는 이전에 여러 차례 보안 감사(P0 #2/#3/#5/#6)를 거쳤으며, **SQL 인젝션·프롬프트 인젝션·시크릿 관리·기본 인가**는 전반적으로 양호하게 방어되어 있다. **CRITICAL 항목은 발견되지 않았다.**

다만 **레이트리밋(throttle) 미적용으로 인한 비인증 LLM 엔드포인트 비용 남용**이 가장 큰 잔여 리스크다.

| 심각도 | 건수 | 핵심 항목 |
|--------|------|----------|
| CRITICAL | 0 | — |
| HIGH | 1 | H1: 비인증 LLM 엔드포인트(`generate_thesis`) 무제한 호출 → Gemini 비용/DoS |
| MED | 3 | M1: 전역 throttle 비활성 / M2: 익명 ScreenerPreset 풀 무결성 / M3: validation 익명 read |
| LOW | 4 | L1: username 열거 / L2: 비밀번호 변경 강도검증 부재 / L3: 뉴스 간접 인젝션 / L4: CORS origin 하드코딩 |
| INFO | 9 | 양호 확인 항목 (아래 §7) |

---

## 1. 인증 / 인가 (A01:2021 — Broken Access Control)

### 1.1 기본 방어 상태 — 양호 ✅

`config/settings.py:359` 전역 기본값이 **`IsAuthenticated`** 로 설정되어 있다.

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
],
```

→ **`permission_classes`를 명시하지 않은 모든 APIView/ViewSet은 자동으로 인증 강제**된다. 따라서 "권한 누락" 자체는 안전한 기본값으로 흡수되며, 위험은 명시적 `AllowAny`로 공개한 뷰에 집중된다.

타깃 17개 view 파일 권한 분포:

| 앱 / 파일 | 권한 | 평가 |
|-----------|------|------|
| `rag_analysis/views.py` (15 view) | 전부 `IsAuthenticated` | ✅ 양호 |
| `sec_pipeline/views.py` | `IsAdminUser` | ✅ 엄격 |
| `chainsight/api/views.py`, `chainsight/views/watchlist_views.py` | 전역 기본 / `IsAuthenticated` (P0 #2로 IDOR 차단) | ✅ 양호 |
| `stocks/views_*.py` | 대부분 전역 기본, `views_market_movers.py`만 `AllowAny`(공개 시세) | ✅ 의도된 공개 |
| `macro/views.py` (9 view) | `AllowAny` (공개 시세 캐시 read) | ✅ 의도된 공개 |
| `users/views.py` | `LogIn`/`PublicUser`만 `AllowAny`(명시), 나머지 `IsAuthenticated` | ⚠️ §1.3 |
| `validation/api/views.py` (6 view) | 5개 전역 기본, `PeerPreferenceView`만 `IsAuthenticatedOrReadOnly` | ⚠️ M3 |
| `serverless/views.py` (~40 `AllowAny`) | 관리·쓰기 트리거는 `IsAdminUser`(P0 #6) 게이트, 공개 read 다수 | ⚠️ H1/M2 |
| `news/api/views.py` | `market-feed`/`interest-options`만 `AllowAny`(콜드스타트/온보딩) | ✅ read-only |

### 1.2 [MED] M2 — 익명 ScreenerPreset 풀의 수정/삭제 우회

`serverless/views.py:870` `screener_presets_api`(POST)는 `AllowAny` + `@authentication_classes([])` 로 **익명 사용자가 `user=None` 프리셋을 생성**할 수 있다.

`serverless/views.py:925` `screener_preset_detail`(PATCH/DELETE)의 소유권 가드:

```python
elif request.method == 'PATCH':
    if preset.user and preset.user != request.user:   # ← preset.user 가 None이면 가드 통과
        raise PermissionDenied("You can only edit your own presets")
```

- **문제**: `preset.user`가 `None`(익명 생성분)이면 `if preset.user`가 falsy → 가드를 건너뛴다. 결과적으로 **누구나 익명 풀의 임의 프리셋을 PATCH/DELETE 가능**.
- **완화 요소**: ① 시스템/beginner/intermediate 카테고리 프리셋은 별도 가드로 삭제 차단. ② 인증 사용자 소유 프리셋은 보호됨(`preset.user != request.user`로 익명/타인 차단). ③ 노출 데이터는 스크리너 필터 설정(민감 PII 아님).
- **영향**: 익명 공유 풀의 데이터 무결성·가용성 훼손(타인 프리셋 변조/삭제). 사용자 데이터 유출은 아님.
- **권고**: 익명 생성 프리셋에 대해서도 작성 토큰/소유 식별자 도입, 또는 익명 PATCH/DELETE 차단.

### 1.3 [LOW] L1 — `PublicUser` username 열거

`users/views.py:113` `PublicUser`(`AllowAny`)는 존재하지 않는 사용자에 `NotFound`(404), 존재 시 200을 반환 → **username 열거(enumeration)** 가능.

- **완화 요소**: 노출 직렬화기는 `UserSerializer`(`users/serializers.py:19`)로 **`id, user_name, nick_name, favorite_stock`만** 노출 — **email/권한 플래그는 미포함**(별도 `MyUserSerializer`에만 존재). 즉 PII 유출 범위는 제한적.
- **권고**: 공개 프로필이 의도라면 그대로 두되, 닉네임/선호종목이 비공개여야 한다면 필드 축소 검토.

### 1.4 [MED] M3 — validation `PeerPreferenceView` 익명 read 허용

`validation/api/views.py:461` `IsAuthenticatedOrReadOnly` → 비인증 GET 허용. peer 선호 설정은 사용자별 데이터일 수 있어, 익명 read 노출 범위를 점검 필요. 나머지 5개 validation view는 전역 `IsAuthenticated`로 보호됨.

---

## 2. 인젝션 (A03:2021 — Injection)

### 2.1 SQL 인젝션 — 양호 ✅ (INFO)

지정 4곳 `cursor.execute()` 전수 검토 결과 **전부 안전**:

| 파일:라인 | 쿼리 형태 | 평가 |
|-----------|----------|------|
| `api_request/admin_views.py:300` | `SELECT 1` (정적) | ✅ 헬스체크 |
| `config/views.py:90` | `SELECT 1` (정적) | ✅ 헬스체크 |
| `serverless/services/admin_status_service.py:833` | `pg_stat_user_tables` 조회 (정적 리터럴, 사용자 입력 없음) | ✅ |
| `chainsight/services/seed_selection.py:152` | 파라미터 바인딩 `%s` 사용 (`[market_date, market_date]`) | ✅ |

→ 문자열 포매팅(f-string/`.format`)으로 SQL을 조립하는 곳은 **발견되지 않음**. ORM 외 raw SQL은 모두 정적 또는 파라미터 바인딩.

---

## 3. LLM 프롬프트 인젝션 (A03 확장 / LLM01)

전반적으로 **이전 P0 #3 감사에서 방어가 체계적으로 적용**되어 있다.

### 3.1 방어 적용 확인 — 양호 ✅ (INFO)

| 경로 | 방어 기법 | 위치 |
|------|----------|------|
| RAG 챗 (`rag_analysis/services/llm_service.py:180`) | `</context_data>`/`</user_question>` 닫는 태그 escape + "블록 내 지시 무시" 시스템 지침 + XML 신뢰 경계 | ✅ P0 #3 |
| Thesis 빌더 (`thesis/services/thesis_builder.py:434`) | 입력 500자 제한 + ` ``` `/`---` 구분자 제거 | ✅ |
| Serverless 테제 (`serverless/services/thesis_builder.py:313`) | `</user_note_untrusted>` escape + 신뢰 경계 태그 + "명령 해석 금지" 지침 | ✅ P0 #3 |

세 경로 모두 **사용자 입력을 명령이 아닌 데이터로 명시 격리**하는 패턴을 일관 적용.

### 3.2 [LOW] L3 — 뉴스 키워드 추출의 간접(indirect) 프롬프트 인젝션

`news/services/keyword_extractor.py:262` `_build_user_prompt`는 **외부 뉴스 제목/요약**을 프롬프트에 직접 삽입한다(요약 100자 제한은 있음). 신뢰 경계 태그/escape는 없음.

```python
news_summary.append(
    f"{i}. [{news['source']}] {news['title']}\n"
    f"   요약: {news['summary'][:100]}...\n" ...
)
```

- **벡터**: 악의적 뉴스 소스가 제목/본문에 LLM 지시문을 심으면 키워드 추출 결과 오염 가능(indirect injection).
- **영향 낮음**: ① 사용자 직접 입력이 아닌 수집 뉴스 ② 결과물이 "키워드 10개" 구조화 JSON으로 제한 ③ 파급 효과가 권한/데이터로 이어지지 않음.
- **권고**: §3.1과 동일하게 뉴스 블록도 신뢰 경계 태그로 감싸고 "데이터로만 취급" 지침 추가.

---

## 4. 시크릿 관리 (A02:2021 / A05:2021)

### 4.1 양호 확인 ✅ (INFO)

- **하드코딩 시크릿**: 소스 전수 스윕(`api_key|secret|password|token = "16자+"`) 결과 **0건** (테스트 placeholder 제외).
- **`.env` 관리**: `.gitignore`에 `.env` 등록(line 10, 138), `git ls-files` 결과 **`.env` 미트래킹**. `.env.example`만 커밋됨(양호).
- **SECRET_KEY 운영 가드** (`config/settings.py:147~176`):
  - dev fallback 사용 시 `DEBUG=False`에서 `ImproperlyConfigured` 발생 → **운영 배포 차단**.
  - `os.getenv('SECRET_KEY') or fallback` 으로 빈 문자열도 미설정 처리.
  - `NEO4J_PASSWORD` 누락 시 운영에서 동일하게 즉시 실패.
- **JWT 서명키 분리** (`settings.py:153`): `JWT_SIGNING_KEY`를 `SECRET_KEY`와 분리(공격 표면 축소), env로 별도 회전 가능.

---

## 5. 레이트리밋 / 비용 남용 (A04:2021 — Insecure Design)

### 5.1 [HIGH] H1 — 비인증 LLM 엔드포인트 무제한 호출

`serverless/views.py:1598` `generate_thesis`:

```python
@api_view(['POST'])
@authentication_classes([])           # 인증 완전 비활성
@permission_classes([AllowAny])
def generate_thesis(request):
    ...
    user_notes = request.data.get('user_notes', '')   # 자유 텍스트
    # → ThesisBuilder.generate() → Gemini 2.5 Flash 동기 호출
```

- **문제**: **비인증·무제한**으로 Gemini API를 호출하는 엔드포인트. 공격자가 반복 호출 시 **Gemini 쿼터 소진 / 과금 폭증 / 서비스 거부**.
- 프롬프트 인젝션 자체는 §3.1(serverless thesis_builder P0 #3 방어)로 차단됨 → **남는 위험은 "비용/가용성"**.
- **연계**: §5.2(M1) throttle 미적용으로 레이트 방어선이 전무.
- **권고**: ① 익명 호출에 IP 기반 `AnonRateThrottle`(예: `market_pulse_llm` 5/min 재사용) 강제, 또는 ② 인증 필수로 전환. 키워드/테제 생성 같은 비용 발생 엔드포인트는 최소한 throttle 게이트 필요.

### 5.2 [MED] M1 — 전역 `DEFAULT_THROTTLE_CLASSES` 미설정

`config/settings.py:362`에는 `DEFAULT_THROTTLE_RATES`(user 60/min, anon 20/min, market_pulse_llm 5/min 등)가 **정의만 되어 있고**, **`DEFAULT_THROTTLE_CLASSES`가 없다**.

- **결과**: DRF는 throttle 클래스가 지정되지 않으면 레이트를 적용하지 않는다. 따라서 **정의된 rate들은 개별 뷰가 `throttle_classes`를 명시한 경우(예: `chainsight` watchlist 30/min)에만 적용**되고, 그 외 대부분의 엔드포인트는 **무제한**.
- **권고**: `'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle', 'rest_framework.throttling.AnonRateThrottle']` 추가하여 정의된 rate를 전역 활성화. (이미 rate는 준비되어 있어 한 줄 변경으로 H1·M1 동시 완화 가능.)

---

## 6. CORS / XSS / 에러 노출 (A05:2021 / A03)

### 6.1 CORS — 대체로 양호 ✅ / [LOW] L4

`config/settings.py:317~326`:

- `CORS_ALLOW_ALL_ORIGINS`은 `DEBUG` 의존을 제거하고 **별도 env(`DJANGO_CORS_ALLOW_ALL`)로 명시 제어**, 기본 `False` → 운영에서 의도치 않은 전체 허용 방지(양호).
- `CORS_ALLOW_CREDENTIALS = True`.
- **[LOW] L4**: `CORS_ALLOWED_ORIGINS`가 `http://localhost:3000`/`127.0.0.1:3000`으로 **하드코딩**. 운영 도메인 추가 시 코드 변경 필요 → env 기반(`DJANGO_CORS_ALLOWED_ORIGINS`)으로 외부화 권고. (현 상태로 운영 배포 시 프론트 origin이 차단되거나, 임시로 ALLOW_ALL을 켜는 안티패턴 유발 가능.)

### 6.2 DEBUG / 에러 노출 — 양호 ✅ (INFO)

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'true'` → **기본 False**.
- `config/exception_handler.py`: DRF 예외를 `{detail, code, errors, status_code}` envelope로 표준화하며 **스택트레이스/내부 경로를 응답에 포함하지 않음**. 비-DRF 예외는 `None` 반환 → Django 기본 핸들러로 위임(`DEBUG=False`에서 generic 500, 스택트레이스 비노출).
- **참고**: `DEBUG=True`(개발)에서는 Django 기본 동작상 스택트레이스가 노출되나 운영 가드(`DEBUG=False` 강제)로 차단됨.

### 6.3 XSS

백엔드는 JSON API(DRF)로 응답하며 서버 렌더링 HTML이 없어 reflected/stored XSS 표면이 작다. 실제 XSS 위험은 프론트엔드(Next.js) 렌더링 단에서 평가 필요 — **본 감사 범위(백엔드) 밖**. (프론트 `dangerouslySetInnerHTML` 사용 여부 별도 점검 권고.)

---

## 7. 양호 확인 항목 (INFO)

1. **I1** — raw SQL 4곳 전부 정적/파라미터 바인딩, SQL 인젝션 없음.
2. **I2** — 하드코딩 시크릿 0건.
3. **I3** — `.env` gitignore + 미트래킹, `.env.example`만 커밋.
4. **I4** — DEBUG 기본 False + 운영 배포 가드(SECRET_KEY/NEO4J_PASSWORD `ImproperlyConfigured`).
5. **I5** — JWT 서명키를 SECRET_KEY와 분리.
6. **I6** — 전역 `IsAuthenticated` 기본값 → 권한 누락 뷰도 안전 기본값으로 흡수.
7. **I7** — 관리·Celery 트리거 엔드포인트(sync/keyword 생성 등)는 `IsAdminUser`(P0 #6)로 게이트.
8. **I8** — RAG/Thesis/Serverless 3개 LLM 경로 모두 프롬프트 인젝션 방어(P0 #3) 적용.
9. **I9** — 에러 응답 envelope 표준화, 스택트레이스 비노출.

---

## 8. 권고 우선순위 (조치 순서)

| 순위 | 항목 | 조치 | 예상 난이도 |
|------|------|------|------------|
| 1 | H1 + M1 | `DEFAULT_THROTTLE_CLASSES` 전역 추가 + `generate_thesis`에 익명 LLM throttle(5/min) 적용 | 낮음 (설정 1~2줄) |
| 2 | M2 | 익명 ScreenerPreset PATCH/DELETE 차단 또는 작성 토큰 도입 | 중 |
| 3 | M3 | `PeerPreferenceView` 익명 read 노출 범위 검토 → 필요 시 `IsAuthenticated` | 낮음 |
| 4 | L4 | `CORS_ALLOWED_ORIGINS` env 외부화 | 낮음 |
| 5 | L3 | 뉴스 키워드 추출 프롬프트에 신뢰 경계 태그 추가 | 낮음 |
| 6 | L1/L2 | username 열거·비밀번호 강도 검증 정책 결정 | 낮음 |

---

## 9. 감사 한계 (Scope & Limitations)

- **정적 분석 only**: 런타임 동작, 실제 인증 흐름, 레이스 컨디션, 비즈니스 로직 권한 우회는 미검증.
- **프론트엔드 제외**: XSS/CSRF/토큰 저장 방식 등 Next.js 단 평가 미포함.
- **인프라 제외**: Celery 태스크, Redis, Neo4j 접근 제어, 컨테이너/배포 설정은 본 감사 범위 밖.
- **의존성 취약점(A06)**: 패키지 CVE 스캔(pip-audit/npm audit) 미수행 — 별도 C 보안 트랙 참조.
- 코드 수정은 일절 수행하지 않았으며 본 문서는 읽기 전용 산출물이다.

---

*감사 수행: Claude (읽기 전용 모드) — 2026-05-29*
