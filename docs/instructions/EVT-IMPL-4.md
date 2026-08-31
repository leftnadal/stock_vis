# EVT-IMPL-4 — 연합 읽기(4원천 DTO) + Phase 1 FE (캘린더 페이지 · 홈 이벤트 스트립)

전제: EVT-IMPL-3 완주(보정2 408cb20e · 하네스 9bf6f019 = origin/main, worker 라이브). 설계 앵커
`docs/design/event_calendar_design.md` v1.1 §4·§5 준수, 충돌 시 HALT. 시각 계약 =
`docs/design/evt_phase1_mockups.html`(디렉터 복원판, 2026-08-31 사용자 확정).
범위 밖: Phase 2(EVT-CHAIN·노드 미니 위젯 D-EVT-FE1)·알림 발송(P1-iii는 이음새만)·원장/수집기 변경.
push는 "푸시" 지시 대기(D-PUSH-DELEG). prod DB 파괴적 작업·원격 브랜치 삭제·.git/hooks 편집 금지.

## 확정 결정 (2026-08-31 디렉터 사이클 — 재결정 금지, DECISIONS에 등재할 것)
- **D-EVT-4A 관심종목 = A3**: Monitor(scope=stock, 사용자 스코프) ∪ WatchlistItem(watchlist__user) 합집합.
  행마다 출처 마크(monitor / watchlist / both), 범위 칩(모니터 종목 · 관심목록 · 둘 다, **기본=모니터 종목**).
  가중합 A1 4.30 / A2 2.95 / A3 4.20 → 마진 0.10 타이브레이커 = 사용자 선택(누락 0 우선).
  **user_id 스코프 필수** — SFI-I1 글로벌 무필터 결함(DECISIONS:6587) 재발 금지. 수집 원장은 전량(D-EVT-SCOPE-U), 필터는 읽기 계층만.
- **D-EVT-4B 연합 읽기 위치 = B1**: `apps/monitor/services/event_feed.py` 단일 구현, dashboard 스트립 뷰가 import
  (app→app, dashboard→chain_sight 선례 동형). 가중합 B1 4.65 / B4 3.85 / B2 3.20, 마진 0.80. shared 병합 금지(B3).
- 소결정: 라우트 `/monitor/calendar`(alerts 선례) · 스트립 컴포넌트 **EventStrip**(MacroStrip은 크레딧 신호 선점) ·
  스트립 "관심 어닝 티저" on(최대 2장, D-7 이내) · 세션 UNKNOWN은 뱃지 미표기(EVT-SESSION).

## §0 프리플라이트
0-1. `git fetch origin` → worktree `sv-evt-1` 재사용, **origin/main 기준 새 브랜치 `monorepo/sess-evt-4`**. HEAD·origin/main 해시 보고.
0-2. **[EVT-OBS-1 게이트 — 하드]** 신코드 첫 자동 발화(08-29 17:45 ET) 검증, 증거 = DB 행(last_run_at 아님):
     PeriodicTask runs≥3 / 08-29 21:45 UTC 이후 last_seen_at 갱신 행 수(재관측 다수) / 신규 행 <1% / stale 전이 수 /
     성분별 텔레메트리(depth·extra_calls·nulled·skipped — earnings_fwd_1 완전 적재 여부) / ADTX 2026-09-02 eps_estimated NULL 유지.
     기준선 13,687행(scheduled 12,498·occurred 1,159·stale 30). **FAIL → STEP 1 착수 전 HALT.** PASS → TASKQUEUE [EVT-OBS-1] 종결 기록.
0-3. [0번 게이트] `docs/instructions/EVT-IMPL-4.md` + `docs/design/evt_phase1_mockups.html`(디렉터가 worktree에 배치, untracked) 2파일 명시 add 커밋(D-DOCS-PERSIST).
0-4. health baseline 기록. foreground·기계 시계·-A 금지.
0-5. **재측정 (지시서 수치 캐리오버 금지)** — 보고서에 값 명기:
     ⑴ 사용자 #1: Monitor(stock) 활성 종목 수 / WatchlistItem 종목 수 / 교집합·합집합 크기.
     ⑵ CalendarEvent scheduled 행의 `date_observed_count` 분포(min·p25·p50·p75·max) → **P1-ii 안정 임계 N = max(3, p50 반올림)** 로 확정해 상수화(근거 병기).
     ⑶ EconomicEvent: 향후 45일·90일 창 importance∈{critical,high} 건수, event_time null 비율, forecast/actual 문자열 형식 표본 3건(숫자 파싱 가능성).
     ⑷ `ALL_NYSE_HOLIDAYS` 자료형(날짜만 vs 이름 포함)·향후 90일 내 휴장일 목록. 이름 없으면 "NYSE 휴장"만 표기.
     ⑸ 4원천 좌표(파일:라인) 인용: CalendarEvent(packages/shared/stocks/models.py) · EconomicEvent(macro/models/indicators.py) ·
        StockSplit(packages/shared/stocks/models.py) · trading_calendar(apps/credit_signals/trading_calendar.py).

## STEP 1 — 연합 읽기 서비스 (BE, `apps/monitor/services/event_feed.py`)
1-1. 공개 함수 `build_event_feed(user, *, start: date, end: date, scope: Literal["monitor","watchlist","both"]="monitor",
     kinds: set[str] | None=None, include_stale: bool=False, macro_min_importance: str="high") -> EventFeed`.
     반환 `EventFeed{as_of, start, end, scope, symbols: {monitor: [...], watchlist: [...]}, counts: {kind: n}, items: [EventItem]}`.
     정렬: (event_date, 시간대 대표시각, kind 순서 holiday→macro→earnings→dividend→split→split_effective, symbol).
1-2. 심볼 집합: monitor = `Monitor.objects.filter(user=user, scope=STOCK, status∈{active, setting_up, paused})` target_ref(대문자) ;
     watchlist = `WatchlistItem.objects.filter(watchlist__user=user)` stock_id. scope에 따라 집합 선택, 항목 `sources`에 소속 마크.
1-3. 원천 매핑(앵커 §4) — 각각 독립 쿼리, 병합은 파이썬:
     ① `CalendarEvent` symbol∈집합, event_date∈[start,end], status∈{scheduled,occurred} (+stale은 include_stale). kind = earnings|dividend|split.
     ② `EconomicEvent` country='US', importance ≥ macro_min_importance(critical>high>medium>low), event_date∈창. kind=macro. 심볼 없음.
     ③ `StockSplit` stock∈집합, date∈창. kind=split_effective(참고 표시).
     ④ `trading_calendar` 창 내 휴장일 → kind=holiday 행(날짜만). `warn_if_coverage_expiring` 경고를 로그로 전달.
1-4. `EventItem` 공통 필드(§4 계약, TypedDict/dataclass): `kind, symbol|None, title, event_date_et, event_time_et|None, session|None,
     event_dt_kst(ISO)|None, d_day(int, 기준=ET 오늘), badges[str], detail{유형별}, surprise{pct, direction}|None,
     date_trust ∈ {stable, fluid, unconfirmed}|None, sources[str], status`.
     - session: CalendarEvent.session이 UNKNOWN이면 **None**(FE 미표기).
     - KST: 대표시각 규칙 — BMO 08:00 ET · AMC 16:30 ET · UNKNOWN/배당/분할 = 날짜만(event_dt_kst None, FE는 ET 날짜+"KST 익일" 규칙 표기) ·
       macro = event_time(없으면 날짜만) → `zoneinfo("Asia/Seoul")` 변환. 감사 로그는 UTC 앵커.
     - surprise(P1-i): 어닝 = eps_actual·eps_estimated 둘 다 존재 & |est|>0 → (act−est)/|est|; 거시 = actual_value·forecast_value 숫자 파싱(%,쉼표,단위 제거) 성공 시. 실패·미발표 = None. **저장 금지.**
     - date_trust(P1-ii): status stale → unconfirmed; date_observed_count ≥ N(0-5⑵) → stable; 그 외 fluid. 뱃지 문구에 관측 횟수 포함 재료(count) 동봉.
1-5. **P1-iii 이음새**: 필터 인자 형태를 alerting 구독 축과 호환되게 유지 — `symbols[]`, `kinds[]`, 그리고 전이 판정 헬퍼
     `classify_trigger(item, prev)`(D-N 도래 / occurred 전이 / stale 전이) 시그니처만 정의(발송 미구현, docstring에 Phase 1.5 표기).
1-6. 서버 캐시: `cache` 키 `monitor:event_feed:v1:user:{uid}:{start}:{end}:{scope}:{kinds}:{stale}:{imp}` TTL 15분(strip_service 선례).
1-7. 테스트 `tests/unit/monitor/test_event_feed.py`: 타 유저 종목 누출 0 / scope 3종 & sources 마크 / 서프라이즈 계산·None 케이스 /
     date_trust 임계 / stale 기본 제외·include 시 unconfirmed / 휴장 인터리브·정렬 / 세션 UNKNOWN→None / KST 변환(BMO·AMC·macro time) /
     캐시 키 분리. `pytest tests/architecture` GREEN(shared 무수정 — shared→apps 0 유지).

## STEP 2 — API
2-1. `GET /api/v1/monitor/calendar/` (APIView, IsAuthenticated) — `apps/monitor/api/urls.py`에 `path("calendar/", ...)` router 앞 등록.
     쿼리: `from`(기본 ET 오늘−7) · `to`(기본 +90) · `scope` · `kinds`(csv) · `include_stale` · `macro_min_importance`. 응답 = EventFeed 그대로(serializer 명시).
     범위 상한 120일, 초과 400. 존재 API·URL 무변.
2-2. `GET /api/dashboard/event-strip/` (dashboard BFF 선례 news-strip) — `apps/dashboard/api/views.py` + urls. **event_feed import(B1)**.
     창 = ET 오늘 .. +45일, scope=both, kinds={macro(critical·high), holiday} + 관심 어닝 티저(earnings, D-7 이내, 최대 2장, 출처 마크 유지).
     응답 `{as_of, window_days: 45, items[≤12]}` 날짜 오름차순. 실패 시 5xx가 아니라 `{items: []}`(FE 실패 격리 동형 — 로그는 남김).
2-3. 테스트: 두 엔드포인트 인증 필수 / 파라미터 검증 / 빈 응답 shape / 티저 상한 2. spectacular enum 등록 필요 시 `config/spectacular_enums.py` 준수.

## STEP 3 — FE (Next.js, `frontend/`)
3-1. 타입 `types/eventCalendar.ts` · 서비스 `services/eventCalendarService.ts`(calendar=authAxios /api/v1, strip=ORIGIN 절대경로 — stripService 선례) ·
     훅 `hooks/useEventCalendar.ts`(TanStack Query, `eventCalendarKeys` 패턴 = useMonitor.ts 동형, staleTime 5분).
3-2. 페이지 `app/monitor/calendar/page.tsx`(AuthGuard) — 목업 A 준수: 헤더(관심종목 수·ET/KST 표기·갱신 시각) → 유형 칩(전체/어닝/배당락/분할/거시/휴장, 카운트) →
     범위 칩(모니터 종목·관심목록·둘 다, 기본 모니터) → "지난 7일 발표됨" 섹션(서프라이즈 뱃지 beat/miss) → 날짜 그룹(D-day, 휴장 빗금 행, 거시 인터리브) →
     행 = 심볼·유형 뱃지·(세션 뱃지: 값 있을 때만)·상세(컨센서스/배당/비율)·신뢰 뱃지(안정·관측 N회 / 유동 / 미확정)·시간(ET + KST) · 출처 마크.
     stale 토글(기본 off). 빈 상태 문구("관심종목이 없습니다 → 모니터 만들기 / 관심목록").
     컴포넌트 `components/monitor/calendar/{EventRow,DateGroup,KindBadge,TrustBadge,SurpriseBadge,ScopeChips}.tsx`. `data-guide="monitor.calendar"` 루트 앵커만(GUIDE 규약, 콘텐츠는 별도).
3-3. 스트립 `components/strip/EventStrip.tsx` — 목업 S 준수: 헤더 한 줄("다가오는 이벤트 · 45일 · 거시 HIGH 이상 · 휴장 포함" + "캘린더 전체 →" 링크) + 가로 카드(D-day·날짜·제목·중요도/EPS 예상·KST).
     CRITICAL은 D-day semantic red, 휴장 카드 dashed, 관심 어닝 카드 강조 테두리. **실패 격리 동형: 에러·빈 응답 → null.**
     홈 `app/page.tsx`: `<MacroStrip />`과 `<NewsStrip />` 사이 `<EventStrip />` **1줄 삽입**만.
3-4. 진입 동선: `/monitor` 페이지 헤더에 "이벤트 캘린더" 링크 1건(AlertBell/alerts 선례, 기존 NAV_ITEMS·칩 무변).
3-5. 테스트 vitest: `__tests__/monitor/eventCalendar.test.tsx`(렌더·유형/범위 필터·stale 숨김·세션 없음→뱃지 미렌더·휴장 행·서프라이즈 부호) ·
     `__tests__/strip/EventStrip.test.tsx`(실패→null · 빈→null · 카드 순서·티저 상한). tsc 0 · lint 순증 0.
3-6. 행위보존: 기존 파일 diff는 ③ `app/page.tsx` 1줄 · ④ `/monitor` 링크 1건 · BE urls 등록 2건 · dashboard views 추가에 한정. 그 외 기존 파일 무변(diff 목록으로 입증).

## STEP 4 — 검증·보고
4-1. pytest 전체 GREEN(선존 동결 외 0 failed) · `pytest tests/architecture` GREEN · vitest 전체 GREEN · health 신규 이상 0.
4-2. 라이브(:3100 dev 허용): `/monitor/calendar` 실데이터 렌더 + 홈 EventStrip 스크린샷 증적(허브 1 + 캘린더 2: 기본/둘 다 범위). 캡처 불가 시 2회 내 중단, 잔여 등재.
4-3. 실측 보고: 사용자 #1 기준 캘린더 항목 수(kind별)·스트립 카드 수·응답 시간(캐시 miss/hit) — Phase 2 파라미터(D-EVT-CHAIN-THRESH) 재료.
4-4. 하네스: DECISIONS(D-EVT-4A · D-EVT-4B · 소결정, 가중합·마진·근거 원문) / TASKQUEUE(EVT-IMPL-4 완료, [EVT-OBS-1] 종결, P1-iii 알림 이음새 Phase 1.5 등재,
     Phase 2 진입 게이트 G-EVT-2 유지, GUIDE 콘텐츠 `monitor.calendar` 앵커 등재) / PROGRESS / common-bugs(신규 함정 시). 커밋은 로컬 브랜치까지, main 머지·push는 "푸시" 지시 후.

## 보고 형식
1. §0 실측(0-1 해시 · 0-2 EVT-OBS-1 표 · 0-5 ⑴~⑸ 값) 2. 변경 파일 목록(신규/수정, 수정은 diff 규모) 3. 테스트·게이트 표 4. 스크린샷 증적 or 잔여 5. 실측 4-3 6. 하네스 기록 요지 7. 지시서 가정과 달랐던 점(정정은 실측 기준).
## HALT: 0-2 FAIL / 설계 앵커·시각 계약 충돌 / architecture 테스트 RED / 기존 파일 diff가 3-6 범위 초과 / 예상 밖 일체.
