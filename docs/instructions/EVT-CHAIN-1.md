# EVT-CHAIN-1 — 관계망 이벤트 타임라인 + 노드 미니 위젯 (Phase 2 슬라이스 1)

전제: Phase 1 완결 계열(4B 35a1550b·CORR 종결 3f539a70·G-EVT-2 1d528a6e). 설계 앵커 v1.1 §6 준수, 충돌 시 HALT.
시각 계약 = **docs/design/evt_chain_mockup_b.html**(목업 B 복원판, 2026-09-03 사용자 확정 — 디렉터 배치, untracked).
범위 밖: 파라미터 변경(잠정값 고정 — 확정은 [EVT-OBS-3] 관찰 게이트 후 디렉터 사이클) · Neo4j 접근 · shared 수정 ·
D군 환류(CompanyEventReaction) · P2-ii. push는 "푸시" 지시 대기. prod DB 파괴·원격 브랜치 삭제·.git/hooks·운영 재기동 자율 금지.

## 확정 결정 (재결정 금지 — DECISIONS 등재)
- Phase 2 첫 슬라이스 = EVT-CHAIN (E1 4.70 / E2 4.00 / E3 2.00, 마진 0.70, 사용자 확정 09-03).
- 화면 = **모니터 상세 `/monitor/[id]` (scope=stock 한정)**, 두 섹션 **附加 전용**: (W) 미니 이벤트 위젯(D-EVT-FE1 동시 출시) + (B) 관계망 이벤트 타임라인. 기존 DOM·컴포넌트 diff = 섹션 삽입 라인만.
- **잠정 파라미터(코드 상수로 명명·집중)**: truth_score ≥ 85 · relation_status = confirmed · top-k 10 · 전파 = EARNINGS만 · **부호 중립**(관계 뱃지 relation_type + truth_score만, 호재/악재 판단·방향 색상 금지).
- 타임라인 범위: 오늘 → 시드 다음 이벤트일(본문), 이후 이웃 이벤트는 "이후 N건 더 ▸" 접힘. 시드 다음 이벤트 없으면 창 = 오늘+90일.
- Postgres 단독 조인(RelationConfidence ⋈ CalendarEvent). 연합 읽기 재사용(event_feed — B1 위치 규율 유지).

## §0
0-1. `git fetch origin` → sv-evt-1 재사용, origin/main 기준 새 브랜치 `monorepo/sess-evt-8`. 해시 보고.
0-2. [0번 게이트] `docs/instructions/EVT-CHAIN-1.md` + `docs/design/evt_chain_mockup_b.html` 2파일 커밋.
0-3. 겸사(보고만): 별건 ⑨ 신규율 수렴 — 최근 2회 발화(09-02·09-03 21:45 UTC) 신규율 실측, <3% 수렴 여부. 3% 이상 지속이면 별건 유지, 조치 없음.
0-4. **재측정 (캐리오버 금지 — 특히 EVT-SURVEY-2 수치)**:
     ⑴ RelationConfidence 좌표(파일:라인)·필드 실명 인용(관계유형·신뢰점수·상태 필드명과 choices — 지시서의 relation_type/truth_score/relation_status는 가칭, **실명이 다르면 실명 채택·보고**).
     ⑵ 총 엣지 수 / confirmed & truth≥85 엣지 수 / symbol_a·b 인덱스 존재.
     ⑶ **User#1 모니터 stock 6종목별**: 임계 적용 후 이웃 수 → top-10 컷 후 수 → 창 내(오늘→시드 다음 이벤트) EARNINGS 행수. **이 표가 [EVT-OBS-3] 파라미터 확정의 기준선.**
     ⑷ FE `app/monitor/[id]/page.tsx` 구조: 섹션 배치 순서·삽입 지점·기존 테스트 위치.
     ⑸ event_feed 재사용 지점(시드 이벤트 pill용 쿼리 — 신규 쿼리 최소화 가능 여부).
     **HALT**: ⑴에서 관계 유형/상태/점수에 해당하는 필드가 없거나 의미가 다르면 착수 전 HALT(파라미터 정의 자체가 흔들림).

## STEP 1 — BE (`apps/monitor/services/chain_feed.py`, B1 위치)
1-1. `build_chain_feed(user, symbol) -> ChainFeed`: `{seed, seed_events[], seed_next_event, neighbors[{symbol, relation_type, truth_score}], items[], after_count, params}`.
     - neighbors: RelationConfidence에서 (symbol_a=시드 OR symbol_b=시드) AND confirmed AND truth≥85, truth 내림차순 top-10. 상대 심볼 정규화(시드가 a든 b든 상대편).
     - items: CalendarEvent(EARNINGS, symbol∈이웃, event_date∈[오늘, 시드 다음 이벤트일]) — EventItem DTO 재사용(P1-ii 신뢰 라벨·d_day 포함) + `relation{type, truth_score}` 확장 필드. after_count = 창 이후 90일 내 이웃 어닝 수.
     - seed_events: event_feed 경로 재사용(시드 심볼 단독, kinds={earnings, dividend}) — 위젯 pill 재료.
     - **부호 중립 하드 규칙**: 방향/센티먼트 필드 생성 금지(DTO에 존재 자체가 위반).
     - 파라미터는 모듈 상수 `CHAIN_PARAMS`(dict 1곳) — [EVT-OBS-3] 확정 시 이 상수만 바뀌도록.
     - 캐시 15분(`monitor:chain_feed:v1:{symbol}`— 사용자 무관 데이터이므로 심볼 키; 응답에 user 데이터 없음 확인).
1-2. 테스트(`tests/unit/monitor/test_chain_feed.py`): 이웃 필터(임계·상태)·top-k 컷·a/b 정규화·창 경계(시드 이벤트 유/무)·after_count·이웃 0 → neighbors [] ·부호 중립(DTO 키 검사)·캐시. `pytest tests/architecture` GREEN(shared 무수정).

## STEP 2 — API
2-1. `GET /api/v1/monitor/calendar/chain/?symbol=` (APIView, IsAuthenticated, monitor urls의 calendar/ 옆) — 응답 = ChainFeed 그대로. symbol 검증(대문자 심볼 형식), 미존재 심볼 = 빈 응답(404 아님).
2-2. 테스트: 인증·파라미터 검증·빈 응답 shape.

## STEP 3 — FE
3-1. `components/monitor/chain/{UpcomingEventsWidget,ChainTimeline,RelationBadge}.tsx` + `services`·`hooks`(TanStack 키 `monitorKeys` 패턴 확장)·타입.
3-2. `app/monitor/[id]/page.tsx`: **scope=stock일 때만** 기존 섹션 아래에 W → B 순서로 삽입(삽입 라인 외 diff 0). 목업 B 준수:
     위젯 = "다가오는 이벤트" pill(어닝 D-N·날짜·EPS 예상·신뢰 뱃지 / 배당락, 없으면 "예정 이벤트 없음") + "캘린더에서 보기 →"(`/monitor/calendar`).
     타임라인 = 시드 배너("다음 이벤트 D-N") → 이웃 어닝 행(심볼·관계 뱃지·truth·EPS 예상·신뢰 뱃지·D-day) → "이후 N건 더 ▸" 접힘 → 시드 행(강조 배경). 이웃 0이면 섹션 자체 비표시.
     관계 뱃지 한글 라벨 매핑은 ⑴ 실측 choices 기준(미지 유형은 원문 표기 — 날조 금지).
3-3. 테스트(vitest): scope!=stock 미렌더·이웃 0 비표시·접힘 카운트·부호 중립(방향 색상 클래스 부재 검사)·pill 없음 상태·기존 [id] 테스트 회귀. tsc 0 · lint 순증 0.
3-4. 행위보존: 변경 기존 파일 = `[id]/page.tsx` 삽입 + monitor urls + hooks/키 1건. 그 외 diff 0 입증. 홈·캘린더·스트립 무접촉.

## STEP 4 — 검증·보고·관찰 게이트
4-1. pytest(monitor·architecture) GREEN · vitest 전체 GREEN · tsc/lint 0.
4-2. 실데이터 스모크(goid545): 모니터 6종목 각각 chain API 호출 → 종목별 이웃 수·표시 행수·응답 시간 표(= 0-4⑶ 대조).
4-3. **[EVT-OBS-3] 등재(TASKQUEUE)**: 파라미터 확정 게이트 — 2주 사용(≈09-17) 후 기준: 시드별 표시 행 0이 과반이면 truth 임계 인하 검토 / 행 >15 시드 존재하면 top-k·창 재검토 → 디렉터 결정 사이클(D-EVT-CHAIN-THRESH 확정).
4-4. 하네스: DECISIONS(시각 계약 확정·잠정 파라미터·E1 근거) · TASKQUEUE(EVT-CHAIN-1 완료, OBS-3, D군 환류·P2-ii는 후속 후보 유지) · PROGRESS. 커밋 로컬까지, push는 "푸시" 대기(착지 후 :3000 재빌드 필요 명기 — 사용자 지시).

## 보고 형식: §0 실측(⑴~⑸ 표) / 변경 파일 / 게이트 표 / 4-2 실데이터 표 / 지시서와 달랐던 점(실측 우선).
## HALT: 0-4⑴ 필드 부재·의미 상이 / 시각 계약 충돌 / architecture RED / 3-4 diff 초과 / 예상 밖 일체.
