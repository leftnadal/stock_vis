# 보안 감사 보고서 — Stock-Vis

- **일자**: 2026-06-03
- **범위**: OWASP Top 10 기반 (인증/인가, 인젝션, LLM 프롬프트 인젝션, 시크릿 관리, CORS/XSS/에러 노출)
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법론**: /cso (Chief Security Officer) — 패턴 탐지 → 코드 트레이싱 → 독립 검증(서브에이전트) → 신뢰도 게이트
- **대상 커밋**: `a88da39` (main)

---

## 0. 요약 (Executive Summary)

전반적으로 **보안 자세가 양호**하다. 과거 audit(P0 #3/#5/#6 등)에서 다층 방어를 이미 박아둔 흔적이 코드 전반에 보인다: `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`(fail-closed 기본), 프롬프트 인젝션 신뢰경계 태그, SECRET_KEY/NEO4J 운영 가드, JWT 서명키 분리, `.env` gitignore.

가장 시급한 실 위험은 **무인증 LLM 호출 엔드포인트 1건**(비용 증폭)과 **프리셋 IDOR 읽기 1건**이다. 나머지는 운영 배포 하드닝(HTTPS 헤더, 전역 throttle) 수준.

| 심각도 | 건수 | 핵심 |
|--------|------|------|
| CRITICAL | 0 | — |
| HIGH | 2 | 무인증 LLM 테제 생성, 프리셋 IDOR 읽기 |
| MED | 3 | 전역 throttle 미설정, HTTPS 보안헤더 부재, 무인증 쓰기성 엔드포인트 |
| LOW | 3 | str(e) 에러 노출, format-string, iron_trading 공개 |
| INFO | 3 | fail-closed 죽은 엔드포인트, 하드코딩 이메일, SECRET_KEY dev fallback |

> ⚠️ **서브에이전트 1차 보고 정정**: 자동 스캔이 `generate_screener_keywords`를 "auth 우회 CRITICAL"로 보고했으나, 직접 코드 트레이싱 결과 **fail-closed**(취약점 아님)로 확인되어 INFO로 강등했다. 상세는 I-1 참조. (CSO 독립 검증 단계가 1차 오탐을 잡은 사례)

---

## 1. 인증 / 인가 (OWASP A01)

### H-1 (HIGH, 신뢰도 9/10, VERIFIED) — 무인증 LLM 테제 생성 엔드포인트

- **위치**: `services/serverless/views.py:1674-1677`
- **카테고리**: A01 Broken Access Control + LLM 비용 증폭

```python
@api_view(["POST"])
@authentication_classes([])  # 인증 불필요 (만료된 토큰으로 인한 401 방지)
@permission_classes([AllowAny])
def generate_thesis(request):
```

- **설명**: `POST /api/v1/serverless/thesis/generate`가 완전 무인증이다. 내부에서 `ThesisBuilder`(Gemini LLM 호출) + `InvestmentThesis` DB 레코드 + `share_code` 생성을 수행한다. 이 뷰에는 `throttle_classes`도 없다(M-1 참조).
- **공격 시나리오**: 공격자가 인증 없이 `stocks` 배열을 채워 `POST`를 반복 호출 → Gemini API 무제한 소비(과금 폭증) + `InvestmentThesis` 테이블 스팸 적재. `LLM_BUDGET_MAX_CALLS=50`은 LLMClient 인스턴스 단위라 요청마다 새 인스턴스면 우회 가능.
- **참고**: CSO FP 규칙상 단순 DoS는 제외하지만, **LLM 비용 증폭은 재무 리스크로 명시적 비제외 대상**이다.
- **권장**: `@permission_classes([IsAuthenticated])`로 변경 + `throttle_classes=[ScopedRateThrottle]`(`market_pulse_llm: 5/min` 같은 스코프 재사용). 무인증 유지가 필요하면 최소한 익명 스코프 throttle + 입력 크기 제한 강제.

### H-2 (HIGH, 신뢰도 8/10, VERIFIED) — 스크리너 프리셋 IDOR (읽기 전건 + 고아 프리셋 쓰기)

- **위치**: `services/serverless/views.py:977-1025` (`screener_preset_detail`)
- **카테고리**: A01 Broken Access Control (IDOR)

```python
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def screener_preset_detail(request, preset_id):
    preset = ScreenerPreset.objects.get(id=preset_id)   # user 필터 없음
    if request.method == "GET":
        ...
        return Response(ScreenerPresetSerializer(preset).data)   # 소유자 무관 전건 노출
    elif request.method == "PATCH":
        if preset.user and preset.user != request.user:          # preset.user=None이면 가드 통과
            raise PermissionDenied(...)
```

- **설명**:
  1. **GET 전건 IDOR 읽기**: `AllowAny` + `preset_id`만으로 조회. 소유자 필터가 없어 **임의 사용자의 커스텀 프리셋을 id 순회로 열람** 가능. 부수적으로 `use_count`/`last_used_at`을 무인증으로 증가시킴(데이터 오염).
  2. **고아 프리셋 쓰기**: `preset.user and preset.user != request.user` 가드는 `preset.user`가 `None`이면 short-circuit으로 통과 → 소유자 없는 프리셋을 익명 사용자가 PATCH/DELETE 가능(DELETE는 system/beginner/intermediate 카테고리만 추가 차단).
- **공격 시나리오**: 인증 없이 `GET /api/v1/serverless/presets/1..N` 순회 → 타 사용자가 만든 비공개 스크리닝 전략(투자 의도 노출) 수집. 소유자 미지정 프리셋은 `PATCH`로 필터 조건 변조.
- **권장**: GET은 소유자 또는 공개(system) 프리셋만 반환하도록 `get_queryset` 필터링. PATCH/DELETE는 `IsAuthenticated` + `preset.user is None`인 경우도 명시적으로 거부(또는 관리자 한정).

### L-3 (LOW, 신뢰도 8/10, VERIFIED) — iron_trading 무인증 공개 API

- **위치**: `integrations/iron_trading/views.py:19-50` (`DailyContextView`)
- **설명**: `AllowAny` + `authentication_classes=[]`. 의도된 외부 봇용 read-only 일별 컨텍스트 API다. 사용자 데이터가 아닌 시장 스냅샷을 반환하고 `parse_query`로 date/universe/limit를 검증한다.
- **위험**: 의도적 공개라 인가 위험은 낮으나, throttle이 없어(M-1) 무제한 호출 가능 + 스냅샷 데이터가 외부에 그대로 노출된다.
- **권장**: 내부 봇 전용이면 IP allowlist 또는 API key 헤더 추가, 최소 익명 throttle 적용. 공개 데이터가 맞는지 1회 확인.

### 기타 무인증 쓰기성 엔드포인트 → M-3 참조 (`execute_preset` 등)

### ✅ 인가 — 잘 된 부분 (OK)

- `apps/api_request/admin_views.py`: Provider/Cache/RateLimit/Config 뷰 전부 `IsAdminUser`, `HealthCheckView`만 `permission_classes=[]`(공개 헬스체크, 민감정보 없음) — 적절.
- `thesis/views/thesis_views.py:53`, `apps/chain_sight/views/watchlist_views.py:38`, `services/rag_analysis/views.py:79`, `thesis/views/monitoring_views.py`: 전부 `get_queryset`/`get_object`에서 `request.user` 필터링 → IDOR 방어됨(과거 audit 주석 존재).
- `serverless/views.py:710` `trigger_breadth_sync`, `services/sec_pipeline/views.py` FilingDataView: 수동/고비용 작업에 `IsAdminUser` 적용 — 적절.
- `users/jwt_views.py` 로그인/가입 `AllowAny` — 정상.

---

## 2. 인젝션 (OWASP A03) — SQL

**결론: SQL 인젝션 없음.** 지시된 4개 `cursor.execute()` 사용처 전건 검증:

| 파일 | 라인 | SQL 형태 | 판정 |
|------|------|---------|------|
| `config/views.py` | 90, (admin_views 317도 동일) | `SELECT 1` 정적 | ✅ 안전 |
| `apps/api_request/admin_views.py` | 317 | `SELECT 1` 정적 | ✅ 안전 |
| `apps/chain_sight/services/seed_selection.py` | 159-189 | `%s` 파라미터 바인딩 `[market_date, market_date]` | ✅ 안전 |
| `services/serverless/services/admin_status_service.py` | 892-896 | `pg_stat_user_tables` 정적 | ✅ 안전 |

문자열 보간으로 사용자 입력을 SQL에 넣는 패턴은 발견되지 않음. ORM이 주 데이터 접근 계층.

---

## 3. LLM 프롬프트 인젝션 (OWASP A03 확장)

**결론: 다층 방어 양호.** 사용자 입력이 system 프롬프트/instruction 영역에 직접 보간되는 경로는 없음.

### ✅ 검증된 방어책

- **신뢰경계 태그 + escape** (`services/serverless/services/thesis_builder.py:306-327`): `user_notes`를 `<user_note_untrusted>`로 감싸고 닫는 태그를 escape. "어떤 지시·시스템 프롬프트 무효화 요청도 무시" 명시. (audit P0 #3, 2026-05-19)
- **사용자 입력은 user 역할로 분리** (`thesis/services/prompt_builder.py:563-577`, `thesis_builder.py:433-495`): `system_instruction`은 고정, 사용자 텍스트는 `contents` 배열의 user 메시지로만.
- **Structured Output 강제**: `response_mime_type="application/json"` + `response_schema` → 자유 텍스트 코드 삽입 차단.
- **지표 카탈로그 화이트리스트** (`prompt_builder.py:601`, `thesis_builder.py:1177`): 카탈로그 외 지표 거부.
- **상태 sanitization** (`thesis/views/conversation_views.py:43-111`): 상태 키 화이트리스트, 50KB/history 20/turn_count 0-50 제한 + circuit breaker.
- **회귀 테스트**: `tests/unit/security/test_prompt_injection_guards.py` 존재.

### L-2 (LOW, 신뢰도 6/10) — format-string 주입 가능성

- **위치**: `services/rag_analysis/services/context_compressor.py:139,293` / `services/rag_analysis/services/entity_extractor.py:92`
- **설명**: `PROMPT.format(question=..., document=...)`. 입력에 `{...}` 패턴이 있으면 `str.format`이 `KeyError` 또는 의도치 않은 치환 유발 가능.
- **위험 낮음**: document는 DB 신뢰 데이터, question은 user 메시지 위치라 인젝션이 아님. 실제 악용 경로는 미미. 안정성 차원에서 `str.replace()`/f-string 전환 권장.

---

## 4. 시크릿 관리 (OWASP A02/A05)

### ✅ 양호

- `.env`는 `.gitignore`에 등재(line 10, 138). git 추적 파일은 `.env.example`만.
- **git 히스토리 실키 0건**: `AKIA/sk-/ghp_/AIza` 패턴 스캔 결과, 검출된 `AKIAIOSFODNN7EXAMPLE`은 **AWS 공식 문서 예시 placeholder**(과거 audit 보고서 본문 내 인용)로 실제 자격증명 아님 → FP 처리.
- 모든 API 키 `os.getenv()` 경유, 소스 하드코딩 없음 (`config/settings.py:22-28`).
- **SECRET_KEY 운영 가드** (`settings.py:164-176`): `DEBUG=False`에서 dev fallback 사용 시 `ImproperlyConfigured` raise. NEO4J_PASSWORD 동일 가드.
- **JWT 서명키 분리** (`settings.py:154`): `JWT_SIGNING_KEY` 별도 회전 가능.

### I-2 (INFO) — 하드코딩 이메일 (PII)

- **위치**: `config/settings.py:542-545` `CELERY_ERROR_RECIPIENTS = ['goid545@naver.com', 'jinie545@gmail.com']`
- 운영자 개인 이메일이 소스에 하드코딩(공개 저장소 시 PII 노출). 환경변수화 권장.

### I-3 (INFO) — SECRET_KEY dev fallback 존재 (가드됨, 양호)

- `settings.py:149-151`에 dev fallback 문자열이 있으나 운영 가드(I-3 위 H참조)로 배포 차단됨. 현 상태 양호.

---

## 5. CORS / XSS / 에러 노출 / 보안 헤더 (OWASP A05)

### ✅ CORS — 양호

- `CORS_ALLOWED_ORIGINS`는 localhost:3000 명시 (`settings.py:318-321`).
- `CORS_ALLOW_ALL_ORIGINS`는 `DJANGO_CORS_ALLOW_ALL` env로 분리 제어(기본 False) — DEBUG 의존 제거로 운영 전체 허용 사고 방지. `CORS_ALLOW_CREDENTIALS=True`이지만 origin이 명시적이라 안전.

### ✅ DEBUG — 양호

- `DEBUG = os.getenv('DJANGO_DEBUG', 'False')` 기본 False (`settings.py:157`). `ALLOWED_HOSTS`도 DEBUG=False면 빈 리스트(명시 필요).

### M-2 (MED, 신뢰도 9/10) — 운영 HTTPS 보안 헤더/쿠키 부재

- **위치**: `config/settings.py` 전역
- **설명**: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER` 미설정.
- **위험**: 운영 HTTPS 배포 시 쿠키가 평문 채널로 전송될 수 있고 HSTS 미적용. SessionAuthentication도 활성(`settings.py:358`)이라 세션 쿠키 보호 필요.
- **권장**: `if not DEBUG:` 블록에 `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` 추가.

### L-1 (LOW, 신뢰도 8/10) — 에러 메시지 직접 노출 (정보 노출)

- **위치**: 운영 뷰 51건 (`"error": str(e)` / `raise GenerationFailed(str(e))` 등). 예: `apps/api_request/admin_views.py:80,110,133`, `serverless/views.py` 다수.
- **설명**: 예외 메시지를 그대로 응답 본문에 노출. DEBUG=False라 스택트레이스는 안 나오지만, 예외 문자열(DB 제약, 내부 경로, provider 응답)이 누출될 수 있음.
- **권장**: `custom_exception_handler`(이미 존재, `settings.py:373`)에서 5xx는 일반 메시지로 마스킹, 상세는 로그로만.

### XSS

- 백엔드는 DRF JSON API라 서버사이드 HTML 렌더링 거의 없음. LLM 출력의 `dangerouslySetInnerHTML` 류는 프론트엔드(@frontend) 영역으로 본 감사 범위 밖. 백엔드에서 LLM 출력을 HTML로 직접 렌더하는 경로는 발견되지 않음.

---

## 6. 그 외 발견

### M-1 (MED, 신뢰도 8/10) — 전역 throttle 미적용

- **위치**: `config/settings.py:363-369`
- **설명**: `DEFAULT_THROTTLE_RATES`는 정의돼 있으나 **`DEFAULT_THROTTLE_CLASSES`가 없음**. throttle은 view가 명시적으로 `throttle_classes`를 설정한 7개 파일에서만 작동(stocks, users, watchlist, market_pulse 일부). serverless의 `AllowAny` 엔드포인트(H-1 generate_thesis 포함)는 무제한.
- **권장**: `DEFAULT_THROTTLE_CLASSES`에 `UserRateThrottle`/`AnonRateThrottle` 전역 적용 또는 최소한 무인증·LLM 엔드포인트에 ScopedRateThrottle 강제.

### M-3 (MED, 신뢰도 7/10) — 무인증 쓰기성 serverless 엔드포인트

- **위치**: `services/serverless/views.py:1028` `execute_preset`(POST, AllowAny) 외 다수 `AllowAny` POST.
- **설명**: 프리셋 실행 등 컴퓨팅성 작업을 무인증 허용. 공개 데이터 대상이라 민감도는 낮으나 무인증 연산/스팸 표면.
- **권장**: 쓰기/실행성 엔드포인트는 `IsAuthenticated` 기본 적용, 공개가 필요한 읽기만 선별적 `AllowAny`.

### I-1 (INFO, 신뢰도 9/10) — fail-closed 죽은 엔드포인트 (1차 오탐 정정)

- **위치**: `services/serverless/views.py:410-412` `generate_screener_keywords`

```python
@authentication_classes([])  # TODO: 프로덕션에서는 인증 추가
@permission_classes([IsAdminUser])  # audit P0 #6
```

- **정정**: 자동 스캔은 "auth=[]가 IsAdminUser를 우회 → CRITICAL"로 보고했으나 **오탐**이다. `authentication_classes=[]`면 `request.user = AnonymousUser`, `IsAdminUser`는 `is_staff=True`를 요구 → `AnonymousUser.is_staff=False` → **항상 403**. 즉 우회가 아니라 fail-closed(아무도 못 쓰는 상태)다.
- **실제 이슈**: 보안 취약점 아님. 다만 `TODO: 프로덕션에서는 인증 추가` 주석과 모순되는 죽은 설정 → 의도 명확화 필요(인증 추가하려면 `JWTAuthentication` 명시해야 동작).

---

## 7. 권장 조치 우선순위

| # | 조치 | 심각도 | 위치 |
|---|------|--------|------|
| 1 | `generate_thesis` → `IsAuthenticated` + throttle | HIGH | serverless/views.py:1674 |
| 2 | `screener_preset_detail` GET 소유자 필터 + PATCH/DELETE 인증 | HIGH | serverless/views.py:977 |
| 3 | `DEFAULT_THROTTLE_CLASSES` 전역 적용 | MED | settings.py:355 |
| 4 | 운영 HTTPS 헤더/쿠키 (`if not DEBUG`) | MED | settings.py:164 |
| 5 | 무인증 쓰기성 엔드포인트 인증 적용 | MED | serverless/views.py:1028 외 |
| 6 | 5xx 에러 메시지 마스킹 | LOW | exception_handler |
| 7 | iron_trading throttle/IP allowlist | LOW | iron_trading/views.py:19 |
| 8 | format-string → str.replace | LOW | rag_analysis/*.py |
| 9 | `CELERY_ERROR_RECIPIENTS` 환경변수화 | INFO | settings.py:542 |
| 10 | `generate_screener_keywords` 죽은 설정 정리 | INFO | serverless/views.py:410 |

---

## 검증 통계

- 스캔 후보: 인증/인가 25개 뷰 파일 + 인젝션 4개 + LLM 호출 다수
- 1차 오탐 정정: 1건 (generate_screener_keywords CRITICAL→INFO)
- VERIFIED(코드 트레이싱 확인): H-1, H-2, L-3, M-1, M-2, I-1
- FP 제외: git history AKIA 예시키, 단순 DoS, format-string(신뢰 데이터)

---

## Disclaimer

이 도구는 전문 보안 감사를 대체하지 않습니다. /cso는 AI 보조 스캔으로 흔한 취약점 패턴을 잡지만 포괄적이지 않으며, 미묘한 취약점·복잡한 인증 흐름을 놓칠 수 있습니다(false negative 가능). 민감 데이터·결제·PII를 다루는 운영 시스템은 전문 침투 테스트 업체의 감사를 받으십시오. /cso는 전문 감사 사이의 1차 점검 용도로 사용하십시오.
