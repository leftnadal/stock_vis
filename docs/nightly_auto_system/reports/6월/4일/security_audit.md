# Stock-Vis 보안 감사 보고서 (OWASP Top 10 기반)

- **감사 일시**: 2026-06-04 23:09 KST
- **대상 커밋**: `7d8f7a7` (branch: main)
- **감사 범위**: 인증/인가, 인젝션(SQL/LLM), 시크릿 관리, CORS/XSS/에러 노출
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **심각도 체계**: CRITICAL / HIGH / MED / LOW / INFO

---

## 0. 요약 (Executive Summary)

| 영역 | 결과 | 최고 심각도 |
|------|------|------------|
| 1. 인증/인가 | ⚠️ 약점 3건 | **MED** |
| 2. SQL 인젝션 | ✅ 통과 | — |
| 3. LLM 프롬프트 인젝션 | ⚠️ 표면 존재, 영향 제한적 | **LOW-MED** |
| 4. 시크릿 관리 | ✅ 양호 | INFO |
| 5. CORS / XSS / 에러 노출 | ⚠️ 에러 메시지 노출 패턴 | **MED** |

**총평**: 기존 보안 감사(audit P0 #2/#5/#6/#11/#14)의 결과가 코드 전반에 반영되어 있어 기반은 견고하다. `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` 기본 차단, 운영 배포 가드(`ImproperlyConfigured`), SECRET_KEY/JWT 키 분리, SQL 파라미터 바인딩 전수 준수 등은 모범적이다. 다만 **`serverless` 프리셋 엔드포인트의 `AllowAny` 뮤테이션**, **`iron_trading` 무인증 데이터 노출**, **`{"error": str(e)}` 형태의 내부 에러 메시지 노출**이 개선 대상이다. CRITICAL/HIGH 결함은 발견되지 않았다.

---

## 1. 인증 / 인가 (A01: Broken Access Control)

### 1.1 기본 권한 정책 — ✅ 양호

`config/settings.py:355-374`에서 DRF 전역 기본 권한이 `IsAuthenticated`로 설정되어 있다.

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
],
```

→ **`permission_classes`를 명시하지 않은 모든 APIView는 기본적으로 인증을 요구**한다. 따라서 stocks/users/validation/rag_analysis 등 다수의 뷰가 명시적 권한 선언이 없어도 안전하게 보호된다(예: `stocks/views.py`의 `StockListAPIView`, `StockSearchAPIView`, `views_eod.py`, `views_indicators.py` 등). 이는 "기본 차단(fail-closed)" 원칙을 만족한다.

전수 검사 결과 **`permission_classes` 누락으로 인해 의도치 않게 노출되는 뷰는 없음**(기본값이 인증 요구이므로).

### 1.2 [MED] serverless 프리셋 PATCH — 시스템 프리셋 무인증 수정 가능

**위치**: `services/serverless/views.py:977-1025` (`screener_preset_detail`)

```python
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def screener_preset_detail(request, preset_id):
    ...
    elif request.method == "PATCH":
        # 소유자만 수정 가능
        if preset.user and preset.user != request.user:   # ← preset.user가 None이면 통과
            raise PermissionDenied("You can only edit your own presets")
        serializer = ScreenerPresetSerializer(preset, data=request.data, partial=True, ...)
        serializer.is_valid(raise_exception=True)
        serializer.save()
```

**문제**: `AllowAny`이며 소유권 검사가 `if preset.user and preset.user != request.user`이다. **시스템/공개 프리셋은 `user=None`**이므로 이 조건이 단락(short-circuit)되어 검사를 건너뛴다. 결과적으로 **익명 사용자가 시스템 프리셋(beginner/intermediate/system)을 PATCH로 수정**할 수 있다.

- DELETE 경로는 `if preset.category in ["system","beginner","intermediate"]: raise PermissionDenied`로 시스템 프리셋 삭제를 막지만, **PATCH 경로에는 동일한 카테고리 가드가 없다.**
- 영향: 모든 사용자에게 노출되는 공용 스크리너 프리셋의 필터 조건/이름이 비인증 공격자에 의해 변조될 수 있음(무결성 훼손).

**권고**: PATCH 경로에도 시스템 카테고리 가드 추가 + 해당 엔드포인트를 `IsAuthenticated`로 승격하고, `preset.user is None`(시스템 프리셋)은 관리자만 수정 가능하도록 변경.

### 1.3 [LOW-MED] serverless 프리셋 생성 — 익명 생성 허용

**위치**: `services/serverless/views.py:916-974` (`screener_presets_api`)

```python
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def screener_presets_api(request):
    ...
    elif request.method == "POST":
        serializer = ScreenerPresetCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        preset = serializer.save()
```

**문제**: `authentication_classes([])` + `AllowAny`로 인증 컨텍스트 자체가 제거되어 **익명 사용자가 프리셋을 무제한 생성**할 수 있다(스팸/리소스 남용). `request.user`가 `AnonymousUser`이므로 소유자 없는(`user=None`) 프리셋이 누적될 수 있다.

**권고**: POST는 `IsAuthenticated`로 분리하거나, 익명 생성 시 throttle(`anon: 20/min`은 적용되나 누적 방지 안 됨) + 소유자 강제. GET만 공개 유지.

> 참고: `execute_preset`(line 1028, `AllowAny`)은 읽기성 실행이나 `use_count`/`last_used_at`를 증가시키는 부수 효과(write)가 있다. 데이터 무결성 영향은 경미하므로 **INFO**.

### 1.4 [MED] iron_trading 무인증 데이터 노출

**위치**: `integrations/iron_trading/views.py:19-50` (`DailyContextView`)

```python
class DailyContextView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        ...
        payload = build_daily_context(params)
        return Response(payload, status=200)
```

**문제**: 외부 봇(iron_trading)이 일별 "결정보드 입력"을 받기 위한 read-only API이나, **인증·API 키·토큰·전용 rate limit이 전혀 없다.** URL만 알면 누구나 일별 트레이딩 컨텍스트 스냅샷(종목 유니버스, 시그널 등)을 조회할 수 있다.

- 노출 데이터가 단순 공개 시장 데이터라면 영향이 낮으나, 내부 시그널/스코어가 포함되면 **사업 로직 정보 유출**에 해당한다(`build_daily_context` 페이로드 점검 필요).

**권고**: 최소한 정적 API 키 헤더 검증 + IP allowlist 또는 전용 throttle 적용. 외부 봇 전용이므로 `AllowAny` 대신 커스텀 `HasValidBotKey` 권한 클래스 권장.

### 1.5 의도된 공개 엔드포인트 — ✅ 적절 (INFO)

다음은 설계상 공개이며 적절히 `AllowAny`/`AllowAny+주석`으로 명시됨:

- `users/views.py`: `LogIn`(149), `PublicUser`(114) — audit P0 #5 주석으로 명시. 로그인/공개 프로필은 비인증 호출 필요.
- `stocks/views_market_movers.py:43` `MarketMoversView` — 공개 시장 데이터.
- `apps/market_pulse/views.py`(macro 레거시): 8개 뷰 전부 `AllowAny` — 거시경제 공개 대시보드 데이터. (단, 신규 `apps/market_pulse/api/views/*`는 `IsAuthenticated`로 일관되게 보호됨 — 레거시/신규 혼재 정리 권장 INFO.)
- `serverless/views.py`: 다수 GET이 `AllowAny`(market movers/screener/chain sight 공개 읽기). **뮤테이션(sync 등)은 모두 `IsAdminUser`(audit P0 #6)** 로 적절히 보호됨.
- `news/api/views.py`: 브리핑 콜드스타트(958)·온보딩 관심사(1002)만 `AllowAny`, 나머지 관리 작업은 `IsAdminUser`.

### 1.6 IDOR 방어 — ✅ 양호

- `rag_analysis/views.py:537` `ChatStreamView`: `AnalysisSession.objects.get(pk=pk, user=request.user)`로 소유자 스코프 강제.
- `chain_sight/views/watchlist_views.py:31-33`: audit P0 #2 주석 — 이전 `AllowAny + user__isnull=True` IDOR를 `IsAuthenticated`로 수정 완료.
- `users/views.py` Portfolio/Watchlist 계열 전부 `IsAuthenticated` + 본인 객체 스코프.

---

## 2. SQL 인젝션 (A03: Injection) — ✅ 통과

`cursor.execute()` 사용처 4곳을 전수 확인했다. **모두 안전**하다.

| # | 위치 | 쿼리 | 판정 |
|---|------|------|------|
| 1 | `config/views.py:90` | `SELECT 1` (정적, 헬스체크) | ✅ 안전 |
| 2 | `packages/shared/api_request/admin_views.py:318` | `SELECT 1` (정적, 헬스체크) | ✅ 안전 |
| 3 | `apps/chain_sight/services/seed_selection.py:159-189` | 멀티라인 CTE, `%s` 파라미터 바인딩 `[market_date, market_date]` | ✅ 안전 |
| 4 | `serverless/services/admin_status_service.py:892-896` | `SELECT relname, n_live_tup FROM pg_stat_user_tables ...` (정적, 사용자 입력 없음) | ✅ 안전 |

- 문자열 포매팅(`f"...{user_input}..."`)으로 SQL을 구성하는 패턴 **없음**.
- #3의 동적 쿼리는 `market_date`를 `%s` 위치 파라미터로 바인딩하여 드라이버가 이스케이프함 → 인젝션 불가.
- 그 외 데이터 접근은 Django ORM(QuerySet)을 사용하므로 자동 파라미터화됨.

---

## 3. LLM 프롬프트 인젝션 (A03 확장) — ⚠️ LOW-MED

Gemini 호출 파일 다수에서 **사용자 입력 및 외부 뉴스 콘텐츠가 f-string으로 프롬프트에 직접 삽입**된다. 다만 다층 방어가 존재해 실질 영향은 제한적이다.

### 3.1 직접 삽입 표면 (확인됨)

- **`thesis/services/prompt_builder.py`**
  - `build_question_answer_prompt`(644): 뉴스 원문 제목/내용(`article.title`, `article.content[:300]`), 사용자 가설 제목·전제가 컨텍스트로 삽입. 규칙 #2가 명시적으로 *"답변은 컨텍스트에 국한하지 말고 당신이 아는 모든 지식을 활용"* 을 지시 → 탈옥(jailbreak)에 관대한 개방형 어시스턴트.
  - `build_intent_classification_prompt`(610), `build_suggestion_prompt`(825): 뉴스 제목/키워드/요약 삽입.
  - 사용자 메시지는 `call_gemini_light(... user_message ...)`로 별도 content에 전달(시스템 프롬프트와 분리)되나, 구분자(delimiter)/이스케이프 없음.
- **`news/services/keyword_extractor.py:289-311`** `_build_user_prompt`: 외부 뉴스 API 제목/요약을 프롬프트에 직접 삽입 → **간접 프롬프트 인젝션**(악의적 뉴스 헤드라인이 키워드 출력을 조작 시도) 벡터.

### 3.2 완화 요인 (방어 양호)

1. **Structured Output 스키마**: `prompt_builder`의 모든 핵심 호출이 `response_schema`(`get_gemini_response_schema`, `get_suggestion_response_schema`)로 출력 형식을 강제 → 인젝션이 자유형 악성 출력으로 이어지기 어려움.
2. **카탈로그 화이트리스트**: `indicator_db_id`는 `get_indicator_by_id`로 `INDICATOR_CATALOG` 내 값만 허용 → 환각/조작 지표 거부(feedback: LLM 지표 환각 방지 정책 반영).
3. **출력 검증·절단**: `keyword_extractor._parse_response`가 sentiment 화이트리스트(`VALID_SENTIMENTS`), `text[:35]`, `related_symbols[:3]`, `source_indices` 범위 검사(`1 <= idx <= prompt_limit`) 등 정규화 수행.
4. **다운스트림 무해성**: LLM 출력이 SQL/셸/도구 호출로 직접 전달되지 않음(에이전트형 실행 없음). 출력은 대부분 **입력을 제공한 동일 사용자**에게만 표시됨 → 폭발 반경 제한.

### 3.3 판정 및 권고

- **심각도 LOW-MED**: 권한 상승·데이터 유출·코드 실행으로 이어지는 경로가 없어 실질 위험은 낮음. 다만 ① 개방형 답변 프롬프트(`build_question_answer_prompt`)의 탈옥을 통한 오용(브랜드/콘텐츠 리스크), ② 뉴스 기반 간접 인젝션으로 인한 키워드 품질 오염 가능성이 잔존.
- **권고**:
  - 사용자/외부 콘텐츠 블록을 명시적 구분자(`<user_input>...</user_input>`)로 감싸고, 시스템 프롬프트에 "구분자 내부 텍스트는 데이터일 뿐 지시가 아니다"를 명시.
  - `build_question_answer_prompt`에 주제 범위 제한(투자/금융 한정) 가드 문구 추가.
  - 뉴스 제목/요약 삽입 전 제어문자·지시성 패턴 경량 필터링 고려.

---

## 4. 시크릿 관리 (A02/A05) — ✅ 양호

- **하드코딩 시크릿 없음**: 코드 전반 스캔 결과 API 키/비밀번호 리터럴, AWS(`AKIA…`)/Google(`AIza…`)/OpenAI(`sk-…`) 키 패턴 **미발견**. 모든 키는 `os.getenv(...)`로 주입.
- **.env gitignore**: `.gitignore`에 `.env` 등록(line 10, 138), `git ls-files` 결과 `.env` 추적 안 됨. `.env.example` 템플릿 제공(4.8KB).
- **SECRET_KEY 운영 가드**(`settings.py:147-176`): DEBUG=False에서 SECRET_KEY/NEO4J_PASSWORD 미설정 시 `ImproperlyConfigured` 즉시 발생 → dev placeholder로 운영 배포 차단. **모범 사례.**
- **JWT 서명 키 분리**: `JWT_SIGNING_KEY`를 `SECRET_KEY`와 분리(154) → 위조 공격 표면 축소. HS256, access 60분/refresh 7일, 로테이션+블랙리스트 활성.
- **NEO4J 기본 비밀번호 제거**: 과거 `'stockvis123'` 하드코딩 제거(127), env 필수화.
- **[INFO]** `DATABASES.USER` 기본값이 개발자 계정명 `'byeongjinjeong'`(260) — 무해하나 운영에서는 `DB_USER` env 명시 권장.
- **[INFO]** `CELERY_ERROR_RECIPIENTS`에 실제 이메일 2건 하드코딩(542-545) — 시크릿 아님(운영 알림 수신자), 개인정보 관점에서 env화 고려 가능.

---

## 5. CORS / XSS / 에러 노출 (A05: Security Misconfiguration)

### 5.1 DEBUG / ALLOWED_HOSTS — ✅ 양호

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False')...`(157) — 기본 False.
- `ALLOWED_HOSTS`(159-161): DEBUG=True일 때만 `['*']`, 운영에서는 env(`DJANGO_ALLOWED_HOSTS`) 기반 → 운영에서 와일드카드 노출 없음.

### 5.2 CORS — ✅ 양호

- `CORS_ALLOWED_ORIGINS`(318-321): `localhost:3000`/`127.0.0.1:3000` 명시 화이트리스트.
- `CORS_ALLOW_ALL_ORIGINS`(325): **DEBUG 의존이 아닌** 별도 env(`DJANGO_CORS_ALLOW_ALL`, 기본 False)로 제어 → 운영 배포 시 의도치 않은 전체 허용 방지(주석에 의도 명시).
- `CORS_ALLOW_CREDENTIALS=True`(327)이나 origin이 명시 화이트리스트라 안전(와일드카드+credentials 조합 아님).
- **[INFO/권고]** 운영 origin(프로덕션 프론트 도메인)이 코드에 없음 → 배포 시 env 주입 또는 리스트 추가 필요. 운영에서 `DJANGO_CORS_ALLOW_ALL=True` 설정은 절대 금지(credentials와 결합 시 위험).

### 5.3 에러 메시지 노출 — ⚠️ MED

- **커스텀 예외 핸들러**(`config/exception_handler.py`): DRF 인식 예외를 `{detail, code, errors, status_code}` envelope로 표준화. **트레이스백 미노출**. 처리되지 않은 예외는 `response is None` → Django 기본 핸들러로 폴백(DEBUG=False면 일반 500, 트레이스백 없음). ✅ 양호.
- **그러나** `serverless/views.py`·`api_request/admin_views.py`의 다수 핸들러가 `try/except`에서 **`return Response({"error": str(e)}, status=500)`** 패턴으로 **내부 예외 문자열을 클라이언트에 직접 노출**한다(envelope 우회). 예:
  - `admin_views.py:78-81, 107-111, 161-164, 247-251, 287-291`
  - `rag_analysis/views.py:582` 파이프라인 에러 `{"code":"PIPELINE_ERROR","message": str(e)}` → SSE로 사용자 전달.
- **영향**: DB/외부 API/내부 모듈의 예외 메시지(테이블명, 경로, 라이브러리 내부 정보 등)가 누출되어 정찰(reconnaissance)에 활용될 수 있음. 트레이스백 전체는 아니므로 MED.
- **권고**: 내부 예외는 서버 로그로만 남기고(`logger.exception`), 클라이언트에는 일반화된 메시지("일시적 오류가 발생했습니다") + 상관관계 ID 반환. `str(e)` 직접 반환 제거.

### 5.4 XSS — INFO (API 서버 특성상 표면 작음)

- 백엔드는 JSON API 중심이며 사용자 입력을 HTML로 렌더링하는 경로는 `config/views.py`의 `api_root.html` 템플릿(정적) 정도. SSE 응답은 `json.dumps(..., ensure_ascii=False)`로 직렬화되어 JS 컨텍스트 주입 위험 낮음.
- 실제 XSS 위험은 프론트엔드(`frontend/`)의 LLM 출력·뉴스 콘텐츠 렌더링 시 `dangerouslySetInnerHTML` 사용 여부에 좌우됨 → **본 백엔드 감사 범위 밖이나, 프론트 별도 점검 권장**(LLM이 생성한 마크다운/HTML을 sanitize 없이 렌더링하면 §3 인젝션과 결합해 stored XSS 가능).

---

## 6. 조치 우선순위

| 우선순위 | 항목 | 위치 | 심각도 |
|---------|------|------|--------|
| 1 | 프리셋 PATCH 시스템 프리셋 가드 + 인증 승격 | `serverless/views.py:1004` | MED |
| 2 | iron_trading 무인증 노출 → API 키/throttle | `iron_trading/views.py:25` | MED |
| 3 | `{"error": str(e)}` 내부 에러 노출 제거 | `serverless/views.py`, `admin_views.py` 다수 | MED |
| 4 | 프리셋 POST 익명 생성 차단 | `serverless/views.py:919` | LOW-MED |
| 5 | LLM 프롬프트 구분자/범위 가드 | `thesis/prompt_builder.py`, `news/keyword_extractor.py` | LOW-MED |
| 6 | 운영 CORS origin env 주입, macro 레거시 뷰 정리 | `settings.py`, `market_pulse/views.py` | INFO |

---

## 7. 검사 메타데이터

- **검사한 views 파일**: 37개(`packages/shared/`, `apps/`, `services/`, `integrations/`, `config/`, `thesis/` 전수)
- **cursor.execute 검사**: 4/4 안전
- **Gemini 호출 파일**: 29개 중 사용자/외부입력 삽입 핵심 3개 정밀 분석(thesis prompt_builder, news keyword_extractor, rag_analysis ChatStreamView)
- **하드코딩 시크릿 스캔**: 코드 전체(마이그레이션/테스트 제외) — 0건
- **주의**: 본 보고서는 정적 분석 기반이며 런타임 동작(실제 throttle 적용 여부, build_daily_context 페이로드 민감도)은 검증 대상에서 제외됨. CRITICAL/HIGH 결함 미발견.

> 본 감사는 읽기 전용으로 수행되었으며 코드 변경은 없습니다.
