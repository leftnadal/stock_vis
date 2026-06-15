# 보안 감사 보고서 — Stock-Vis

- **감사 일시**: 2026-06-15
- **감사 범위**: OWASP Top 10 (+ LLM01) 기반 백엔드 정적 감사
- **모드**: READ-ONLY (코드 수정 없음)
- **브랜치**: main (`da5d992`)
- **감사자**: Claude (자동 야간 감사)

> ⚠️ 정적 코드 감사만 수행. 동적 침투 테스트(DAST)·런타임 검증·인증 우회 실증은 미포함.
> 디렉토리 구조가 monorepo로 재구성되어(`apps/`, `services/`, `packages/shared/`) 지시서의 경로 17개와 실제 경로가 상이 → 실제 경로 30개 뷰 파일 전수 검사로 대체.

---

## 0. 요약 (Executive Summary)

| 카테고리 | 결과 | 최고 심각도 |
|---------|------|-----------|
| A01 인증/인가 | ⚠️ 부분 이슈 | **MED** |
| A03 인젝션 (SQL) | ✅ 안전 | INFO |
| LLM01 프롬프트 인젝션 | ⚠️ 다수 노출 | **HIGH** |
| 시크릿 관리 | ✅ 양호 | INFO |
| A05 CORS/DEBUG/에러노출 | ✅ 양호 | LOW |
| Rate Limiting (DoS 표면) | ⚠️ 전역 미적용 | **MED** |

**핵심 결론**: SQL 인젝션·시크릿·CORS·DEBUG·에러 노출은 모두 안전하게 처리됨(이전 P0 audit 흔적 양호). **가장 실질적인 리스크는 LLM 프롬프트 인젝션** — 신뢰 경계(trust boundary)가 일부 핵심 경로(rag_analysis, serverless/thesis_builder)에만 적용되고, 외부 데이터(뉴스 제목·SEC 본문)를 f-string으로 프롬프트에 직접 삽입하는 호출이 8곳 이상 잔존. 두 번째는 **전역 throttle 클래스 미적용**으로 공개(AllowAny) 엔드포인트에 rate limit이 걸리지 않음.

### 우선 조치 권고 (Top 5)
1. **[HIGH]** 외부 데이터→프롬프트 삽입 경로에 신뢰 경계 태그 + 닫는태그 이스케이프 적용 (conversation_views, news/api/views, llm_relation_extractor, regulatory_service)
2. **[MED]** `DEFAULT_THROTTLE_CLASSES` 전역 설정 — rate는 정의됐으나 클래스 미연결로 미적용
3. **[MED]** `iron_trading/DailyContextView` 무인증 공개 API에 API 키/IP 화이트리스트/throttle 도입
4. **[MED]** Gemini가 생성한 지표 추천을 `INDICATOR_CATALOG` 화이트리스트로 런타임 검증 (현재 프롬프트 지시만 존재, 응답 검증 없음)
5. **[LOW]** admin 성격 뷰(`views_eod`)에 `IsAdminUser` 명시 (현재 기본 `IsAuthenticated` 의존)

---

## 1. 인증/인가 (OWASP A01: Broken Access Control)

### 1.1 기본 정책 (양호)
`config/settings.py:367-369`
```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
```
- 기본값이 `IsAuthenticated` → permission_classes 미선언 뷰는 자동으로 인증 필수. (2026-04-29 P0 #5에서 `IsAuthenticatedOrReadOnly`→`IsAuthenticated` 강화 이력 확인)
- 공개 read 화이트리스트(NEWS-AUTH 2026-06-12)는 명시적 `[AllowAny]`로만 개방하는 원칙 문서화됨.

### 1.2 IDOR 검사 — ✅ 안전
사용자별 데이터 뷰 전수 `request.user` 스코프 확인:

| 뷰 | 격리 방식 | 결과 |
|----|----------|------|
| `apps/chain_sight/views/watchlist_views.py` WatchlistViewSet | `get_queryset`: `SavedPath.objects.filter(user=self.request.user)` | ✅ |
| `services/rag_analysis/views.py` DataBasketDetailView | `get_object(pk, user)` | ✅ |
| `thesis/views/thesis_views.py` ThesisViewSet | `get_queryset`: `Thesis.objects.filter(user=...)` | ✅ |
| `thesis/views/monitoring_views.py` DashboardView | `get_object_or_404(Thesis, id=..., user=request.user)` | ✅ |
| `apps/portfolio/api/views.py` coach_e1~e6 | `@permission_classes([IsAuthenticated])` 6개 전부 | ✅ |

→ **URL pk를 무필터로 신뢰하는 IDOR 패턴 미발견.**

### 1.3 발견 이슈

#### [MED] `integrations/iron_trading/views.py:19-26` — 무인증 공개 API
```python
class DailyContextView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []   # 인증 전역 비활성화
```
- URL 연결 확인: `config/urls.py:46` → `/api/v1/iron-trading/daily-context`
- read-only 시장 스냅샷(사용자 데이터·쓰기 없음)이라 노출 데이터 민감도는 낮으나, **완전 무인증 + throttle 없음** → 외부 봇용이지만 누구나 호출 가능. 데이터 무단 수집·DoS 표면.
- **권고**: API 키 헤더 검증 또는 IP 화이트리스트 + ScopedRateThrottle.

#### [MED] 공개(AllowAny) 거시/무버스 엔드포인트 — throttle 부재
`apps/market_pulse/views.py`의 MarketPulse/FearGreed/InterestRates/Inflation/GlobalMarkets/EconomicCalendar/VIX/SectorPerformance/SyncStatus (8~9개), `packages/shared/stocks/views_market_movers.py` MarketMoversView, `services/serverless/views.py:47,119` market_movers_api / market_mover_detail.
- 공개 거시 데이터(FRED/FMP 공개 출처)라 개방은 비즈니스 의도로 판단되나, 외부 API 호출을 트리거하는 엔드포인트가 throttle 없이 열려 있어 비용·부하 증폭 및 심볼 열거(enumeration) 가능.
- **참고**: `DataSyncView`(`market_pulse/views.py:359`)는 `IsAdminUser`로 올바르게 보호됨.

#### [LOW] `packages/shared/stocks/views_eod.py` EODDashboardView — admin 성격이나 IsAdminUser 누락
- permission_classes 미선언 → 기본 `IsAuthenticated`만 적용. 운영/디버그용 대시보드라면 `IsAdminUser` 명시 권장(심층 방어).

#### [INFO] News read 엔드포인트
`services/news/api/views.py` NewsViewSet / stock_news 등은 기본 `IsAuthenticated`. NEWS-AUTH 화이트리스트(all/daily-keywords/trending 등)는 공개 의도이므로 해당 액션에 명시적 `[AllowAny]` 부여 여부를 정책과 정렬할 것(현 상태도 보안상 안전, 단지 UX 정책 정합 이슈).

### 1.4 정정 — Agent 1차 오탐
- `services/serverless/views_admin.py`: 1차 스윕에서 "권한 누락 의심(HIGH)"으로 보고됐으나 **재검증 결과 11개 뷰 전부 `permission_classes = [IsAdminUser]` 적용 확인**(149~756라인). → **이슈 아님(OK)**.

### 1.5 관리자 엔드포인트 — ✅ 양호
- `packages/shared/api_request/admin_views.py`: 전부 `IsAdminUser` (HealthCheckView만 공개 헬스체크, 의도적)
- `services/serverless/views_admin.py`: 전부 `IsAdminUser`
- `services/sec_pipeline/views.py` FilingDataView: `IsAdminUser` (비용 발생 API 보호)
- `apps/market_pulse/api/views/health.py`: `IsAdminUser`

---

## 2. 인젝션 (OWASP A03: Injection — SQL) — ✅ 안전

`cursor.execute()` 4곳 전수 검사:

| # | 위치 | 쿼리 | 바인딩 | 판정 |
|---|------|------|--------|------|
| 1 | `config/views.py:90` | `SELECT 1` | 정적, 사용자 입력 없음 | ✅ 안전 |
| 2 | `packages/shared/api_request/admin_views.py:318` | `SELECT 1` | 정적(헬스체크) | ✅ 안전 |
| 3 | `apps/chain_sight/services/seed_selection.py:159` | 거래량 CTE 쿼리 | **파라미터 바인딩** `%s` + `[market_date, market_date]` (187-188라인) | ✅ 안전 |
| 4 | `services/serverless/services/admin_status_service.py:892` | `pg_stat_user_tables` 조회 | 정적 문자열, 사용자 입력 없음 | ✅ 안전 |

- **결론**: 문자열 포매팅(f-string/`.format`/`+`)으로 raw SQL을 구성하는 곳 없음. #3은 `%s` 플레이스홀더 + 파라미터 리스트로 올바르게 바인딩. ORM 외 raw SQL 4곳 모두 SQL 인젝션 표면 없음.
- 나머지 DB 접근은 Django ORM 사용 → 파라미터화 자동 적용.

---

## 3. LLM 프롬프트 인젝션 (OWASP LLM01) — ⚠️ MEDIUM~HIGH

**전체 수준: MEDIUM~HIGH.** 신뢰 경계 방어가 2개 핵심 경로에만 적용되고, 외부/사용자 데이터를 f-string으로 직접 삽입하는 호출이 다수 잔존.

### 3.1 방어된 경로 — ✅ 모범 사례
| 위치 | 방어 |
|------|------|
| `services/rag_analysis/services/llm_service.py:178-193` | `<context_data>`/`<user_question>` 신뢰 경계 태그 + 닫는태그 이스케이프 + "데이터로만 취급" 시스템 지시. 테스트 존재 |
| `services/serverless/services/thesis_builder.py:305` | `<user_note_untrusted>` 태그 + `replace()`로 닫는태그 이스케이프 + 명시 지시. `tests/unit/security/test_prompt_injection_guards.py` 커버 |

### 3.2 미방어 / 부분방어 — 발견 목록

| 심각도 | 위치 | 사용자입력 출처 | 방어 |
|--------|------|----------------|------|
| **HIGH** | `thesis/views/conversation_views.py:237` `get_news_issues()` | 외부 뉴스 제목(`title_list`) | ❌ 없음 |
| **HIGH** | `services/news/api/views.py:830` `_summarize_keyword_articles()` | 키워드 + 외부 기사 제목 | ❌ 없음 |
| **HIGH** | `services/serverless/services/llm_relation_extractor.py:379` `_call_llm()` | SEC/뉴스 본문(`truncated_text`) | ⚠️ 절단만(`[:5000]`), 구분자 `---` 스푸핑 가능 |
| **HIGH** | `services/serverless/services/regulatory_service.py:479` | 뉴스/공시 텍스트(`text_snippets`) | ❌ 없음 |
| **HIGH** | `thesis/services/prompt_builder.py:873` `get_suggestion_prompts()` | 외부 키워드/요약(`context`) | ❌ 없음 |
| **HIGH** | `thesis/services/indicator_matcher.py:206` `match_by_gemini()` | 사용자 전제(premise) + thesis 제목/타깃 | ⚠️ `_sanitize_for_prompt()`가 ``` `, `---`만 제거 |
| **MED** | `services/news/services/keyword_extractor.py:293` | 뉴스 제목/요약 | ❌ 없음 |
| **MED** | `services/news/services/stock_insights.py:598` | 영문 헤드라인 | ❌ 없음 |
| **MED** | `services/serverless/services/csv_url_resolver.py:355` | ETF 심볼(파라미터) + 외부 HTML | ⚠️ HTML script/style만 제거 |
| **MED** | `thesis/services/thesis_builder.py:448` `_parse_free_input()` | 사용자 가설 자유입력 | ⚠️ `[:500]` + ``` `,`---` 제거 (대체 구분자 우회 가능) |

> 위 라인 번호는 1차 Explore 스윕 결과로, 일부는 근사치일 수 있음. 수정 착수 시 해당 함수명으로 재확인 권장.

### 3.3 다운스트림 리스크 평가
- **외부 데이터 경로**(뉴스 제목·SEC 본문 → 이슈 라벨/요약): 주 영향은 **출력 오염(UX)**. LLM 출력이 코드/쿼리로 실행되지 않으면 직접 RCE 위험은 낮음.
- **지표 추천 경로**(가장 우려): premise → Gemini가 지표 매칭 → `indicator.data_source`/`data_params` DB 저장 → 후속 데이터 페치 파이프라인 사용. CLAUDE.md는 "카탈로그 외 지표 생성 금지"를 **프롬프트 지시로만** 강제(`prompt_builder.py`), **응답에 대한 런타임 화이트리스트 검증 부재**. 프롬프트 인젝션으로 카탈로그 외 `data_source`/`data_params` 주입 시 잘못된 API 호출 유발 가능 → **HIGH**.

### 3.4 권고
1. 3.2의 HIGH 경로에 신뢰 경계 태그 + 닫는태그 이스케이프 + "데이터로만 취급" 지시 적용 (3.1 패턴 재사용).
2. `_sanitize_for_prompt()` 공용 유틸로 승격 + 길이 제한/제어문자 화이트리스트/추가 구분자(`~~~`,`===`,`<|`,`>>>`) 차단 보강.
3. `indicator_matcher`에서 Gemini 응답 지표를 `INDICATOR_CATALOG` ID로 런타임 검증·필터.
4. `tests/unit/security/test_prompt_injection_guards.py`에 신규 경로(뉴스 제목 주입 등) 테스트 추가.

---

## 4. 시크릿 관리 — ✅ 양호

| 항목 | 결과 |
|------|------|
| `.env` gitignore 등록 | ✅ `.gitignore:10, 138`에 `.env` |
| `.env` git 추적 여부 | ✅ 추적 안 됨 (`git ls-files`에 없음, `.env.example`만 추적) |
| 하드코딩 시크릿(API키/비번/토큰) | ✅ 코드 스캔 결과 미발견 (전부 `os.getenv`/`settings.` 경유) |
| `SECRET_KEY` 관리 | ✅ env 우선, dev fallback은 placeholder. **운영 가드**: `DEBUG=False`인데 fallback이면 `ImproperlyConfigured` raise (`settings.py:164-171`) |
| `JWT_SIGNING_KEY` 분리 | ✅ SECRET_KEY와 분리(위조 표면 축소), 미설정 시 fallback |
| `NEO4J_PASSWORD` 운영 가드 | ✅ `DEBUG=False`에서 미설정 시 raise (`settings.py:172-176`) |

- `.env` 파일 권한도 `-rw-------`(600)로 적절.
- **참고**: 시크릿 출력 시 마스킹 정책(`len=N, head=XXXX***`)은 본 보고서에 시크릿 값 미포함으로 준수.

---

## 5. CORS / XSS / DEBUG / 에러 노출 (OWASP A05: Security Misconfiguration) — ✅ 양호

### 5.1 CORS — ✅ 양호
`config/settings.py:317-348`
- `CORS_ALLOWED_ORIGINS`: `localhost:3000`, `127.0.0.1:3000`만 허용 (화이트리스트).
- `CORS_ALLOW_ALL_ORIGINS`: **기본 False**, `DJANGO_CORS_ALLOW_ALL` env로만 명시 개방 (DEBUG 의존 제거 — 운영 의도치 않은 전체 허용 방지). ✅
- `CORS_ALLOW_CREDENTIALS = True`이나 origin이 화이트리스트로 제한되어 안전.
- **참고**: 운영 배포 시 실제 프론트 도메인을 `CORS_ALLOWED_ORIGINS`에 추가하되 와일드카드 금지 — 현 구조는 이를 강제함.

### 5.2 DEBUG — ✅ 양호
- `DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'true'` → **기본 False**.
- `ALLOWED_HOSTS`: DEBUG일 때만 `['*']`, 운영은 env 필수(미설정 시 `[]` → Django가 요청 거부).

### 5.3 에러/스택트레이스 노출 — ✅ 양호
- `config/exception_handler.py`: 커스텀 핸들러가 `{detail, code, errors, status_code}` 표준 envelope만 반환. **내부 예외 메시지/스택트레이스 미노출** (DRF 기본 핸들러 경유, 비DRF 예외는 `response is None` → Django 기본 처리, DEBUG=False에서 일반 500 페이지).
- ValidationError도 필드 단위 에러만 반환, 내부 구현 누출 없음.

### 5.4 XSS
- 백엔드는 JSON API(DRF) → 서버측 HTML 렌더링 없음. XSS 1차 책임은 프론트(Next.js/React, 기본 이스케이프). **본 백엔드 감사 범위에서 직접 위험 없음** (단, LLM 출력을 프론트에서 `dangerouslySetInnerHTML` 등으로 렌더하면 §3 인젝션과 연계 — 프론트 별도 점검 권장).

---

## 6. Rate Limiting (DoS 표면) — ⚠️ MED

#### [MED] `DEFAULT_THROTTLE_CLASSES` 미설정
`config/settings.py:370-376`
```python
'DEFAULT_THROTTLE_RATES': {
    'user': '60/min', 'anon': '20/min',
    'market_pulse_user': '60/min', 'market_pulse_user_hour': '1000/hour',
    'market_pulse_llm': '5/min',
},
```
- **rate는 정의됐으나 `DEFAULT_THROTTLE_CLASSES`가 없음** → `user`/`anon` 전역 throttle이 **자동 적용되지 않음**. 각 뷰가 `throttle_classes`를 명시한 경우(ScopedRateThrottle 등)에만 적용됨.
- 결과: §1.3의 AllowAny 공개 엔드포인트 + iron_trading 무인증 API가 **rate limit 없이** 노출 → DoS/비용 증폭/열거 공격 표면.
- **권고**: `DEFAULT_THROTTLE_CLASSES`에 `AnonRateThrottle`/`UserRateThrottle` 추가하거나, 최소한 공개·무인증·외부API-트리거 뷰에 ScopedRateThrottle 개별 적용.

---

## 7. 심각도별 종합

### CRITICAL
- 없음.

### HIGH
| 위치 | 이슈 |
|------|------|
| §3.2 LLM 6개 경로 | 외부/사용자 데이터를 신뢰 경계 없이 프롬프트에 직접 삽입 (프롬프트 인젝션) |
| `indicator_matcher` 응답 검증 | Gemini 지표 추천을 카탈로그로 런타임 검증하지 않음 (다운스트림 페치 오염 가능) |

### MEDIUM
| 위치 | 이슈 |
|------|------|
| `settings.py:370` | `DEFAULT_THROTTLE_CLASSES` 미설정 → 전역 rate limit 미적용 |
| `iron_trading/views.py:19` | 무인증 공개 API + throttle 없음 |
| 공개 macro/movers 뷰 | AllowAny + throttle 없음 (열거/부하) |
| §3.2 LLM 4개 경로 | 부분 방어/미방어 (MED 등급) |

### LOW
| 위치 | 이슈 |
|------|------|
| `views_eod.py` | admin 성격 뷰가 `IsAdminUser` 대신 기본 `IsAuthenticated` 의존 |
| CORS credentials | 화이트리스트로 안전하나 운영 도메인 추가 시 와일드카드 금지 주의 |

### INFO
- SQL 인젝션 4곳 전수 안전(정적/파라미터화).
- 시크릿 관리 양호(.env 미추적, 하드코딩 없음, 운영 가드 존재).
- News read 엔드포인트 AllowAny 정책 정합(보안 무해, UX 정책 정렬 권장).

---

## 8. 감사 한계 및 후속 권고

- **정적 감사 한정**: 인증 우회·실제 인젝션 페이로드 실행·세션 관리·CSRF 토큰 흐름은 동적 테스트 미수행. DAST/통합 테스트로 보강 권장.
- **라인 번호 근사**: §3 LLM 경로 일부 라인 번호는 1차 Explore 스윕 기반 — 수정 착수 시 함수명으로 재확인.
- **프론트엔드 범위 외**: XSS·LLM 출력 렌더링·토큰 저장 방식은 `frontend/` 별도 감사 필요.
- **다음 회차 권고**: ① LLM 신뢰 경계 일괄 retrofit + 테스트, ② 전역 throttle 도입, ③ iron_trading 인증, ④ 지표 카탈로그 런타임 검증.

---

*본 보고서는 읽기 전용 정적 감사 결과이며 코드 변경을 포함하지 않습니다.*
