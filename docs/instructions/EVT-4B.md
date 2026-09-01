# EVT-4B — CORR-4 (거시 시각 UTC 해석) + FE-TUNE-1 (거시 접기 T2) — 소형 2건 연속

전제: EVT-IMPL-4 main 착지(835da979)·런타임 라이브·SHOT 대조 완료(2026-08-31, 디렉터 판정: 시각 계약 통과).
설계 앵커 v1.1 §4·§5 준수. 시각 계약 = `docs/design/evt_phase1_mockups.html` + 본 슬라이스 부록 `docs/design/evt_tune1_options.html`(T2).
범위 밖: 거시 수집기(`apps/market_pulse/tasks/macro.py`) 수정 — **market_pulse 소유, 별건 MP-MACRO-CAL-1**. 원장·수집기(shared)·스트립 구성 규칙 변경 없음.
push는 "푸시" 지시 대기(D-PUSH-DELEG). prod DB 파괴적 작업·원격 브랜치 삭제·.git/hooks·운영 재기동 자율 금지.

## 확정 결정 (2026-08-31 디렉터 사이클 — 재결정 금지, DECISIONS 등재)
- **D-EVT-CORR-4**: `EconomicEvent.event_time`은 **UTC**로 해석한다. 근거 = `apps/market_pulse/tasks/macro.py:183` FMP `date`(UTC 문자열)의 시각을 잘라 그대로 저장, 모델 help_text만 'ET'. 실화면 실측: 모든 거시 시각이 +4h(Chicago Fed 08:30 ET → "12:30 ET / KST 01:30"). 읽기 계층(event_feed)에서 UTC→ET·KST 도출. 원천 필드 의미는 바꾸지 않는다(MP-MACRO-CAL-1과의 계약: 원천은 UTC 유지·help_text만 정정).
- **D-EVT-FE-TUNE-1 = T2 거시 접기**: 관심종목 이벤트·휴장은 항상 펼침, 거시는 날짜 그룹당 "거시 N건 ▸" 한 줄 접힘 + CRITICAL 제목 미리보기. 가중합 T2 4.60 / T4 3.70 / T1 3.65 / T3 3.60, 마진 0.90(사용자 확정). 근거: 실화면 104항목 중 거시 94, "지난 7일"이 거시 34행으로 시작해 IREN miss가 밀림.
- 소손질(동일 결정에 묶음): 거시 행 뱃지·제목 한 줄화 / "세션 미정" 문구 비움 / |서프라이즈| > 200% 시 뱃지는 beat·miss만, 원값을 주표기.

## §0
0-1. `git fetch origin` → sv-evt-1 재사용, origin/main 기준 새 브랜치 `monorepo/sess-evt-6`. EVT-CORR-3(sess-evt-5)가 미착지면 병렬 진행(파일 교집합 0: 5호=shared/stocks/tasks.py, 6호=event_feed+FE). 해시 보고.
0-2. [0번 게이트] `docs/instructions/EVT-4B.md` + `docs/design/evt_tune1_options.html`(디렉터 배치, untracked) 2파일 커밋.
0-3. **UTC 가설 검증(하드)**: EconomicEvent 표본 3건(명확한 ET 발표시각을 아는 지표 — 예: Initial Jobless Claims 08:30 ET, ISM 10:00 ET, FOMC 14:00 ET)의 저장 `event_time`을 인용. 전부 ET+4(EDT) 또는 +5(EST)면 PASS. 하나라도 어긋나면 **HALT**(혼합 저장 의심).
0-4. 재측정: 창 내 거시 중 UTC→ET 변환 시 **날짜가 바뀌는 행 수**(UTC 00:00~04:59 = 전날 ET) / 실제값(actual_value) 비어 있는 과거 7일 거시 수 / importance 분포.

## STEP 1 — CORR-4: event_feed 거시 시각 해석 (BE)
1-1. `_build_macro_items`: `event_time`이 있으면 `datetime.combine(event_date, event_time, tzinfo=UTC)` → ET로 변환해 `event_date_et`·`event_time_et` 도출, KST도 같은 인스턴스에서. `event_time` 없으면 날짜만(기존 규칙). **날짜 그룹·d_day·정렬은 event_date_et 기준**(원천 event_date 아님).
1-2. 창 필터: 경계 날짜 보정 — 원천 event_date 기준 [start−1, end+1]로 조회한 뒤 변환된 ET 날짜로 [start, end] 재필터(자정 경계 누락 방지).
1-3. DTO 필드 추가 없음. `detail.event_time_utc`(원문 HH:MM) 1개만 추가해 감사 가능하게.
1-4. 스트립(`event_strip_service`)은 feed를 쓰므로 자동 반영 — 카드 KST 실측 1건 인용(ADP 08:15 ET → KST 21:15).
1-5. 테스트: UTC→ET(EDT·EST 각 1) / 날짜 경계 이동 케이스 / KST / event_time None 유지 / 기존 event_feed 테스트 회귀.

## STEP 2 — FE-TUNE-1: T2 거시 접기 (FE)
2-1. `DateGroup`: 항목을 `watch`(earnings·dividend·split·split_effective)·`holiday`·`macro`로 분할. watch·holiday 행은 항상 렌더. macro는 **`MacroFoldRow`** 1행: "거시 N건 ▸" + CRITICAL 제목 최대 3개 미리보기(제목 · ET 시각 · KST) + 펼치기. 펼치면 기존 거시 행들이 그 자리에 렌더(접힘 상태는 그룹별 useState, 기본 접힘).
2-2. 접기 적용 규칙: 유형 필터가 **거시 단독**이면 접지 않는다(사용자가 거시를 보려는 의도). 그 외(전체·혼합)는 접는다.
2-3. "지난 7일 발표됨": watch 결과(occurred 어닝 등) 먼저(최근순), 그 뒤 `MacroFoldRow` — 미리보기는 `actual_value`가 있는 CRITICAL만 "제목 실제 (예상)" 형식. 실제값 있는 행이 0이면 미리보기 대신 "실제값 미수신 N건"(MP-MACRO-CAL-1 전까지의 정직 표기).
2-4. 거시 행(`EventRow` macro 변형): 뱃지+제목을 **한 줄**로(현재 뱃지 위·제목 아래 2줄 → 1줄), 열 정렬은 어닝 행과 동일 그리드. 행 높이 어닝 행과 동급.
2-5. 세션 셀: `session`이 None이고 시각도 없으면 **빈 칸**("세션 미정" 문구 제거). 값 있을 때만 BMO/AMC 뱃지·시각.
2-6. 서프라이즈: |pct| > 200%면 뱃지 문구를 "beat"/"miss"만, 상세 열에 "EPS −1.89 vs 예상 −0.55"를 주표기(현재도 있음 — 순서만 앞으로). ≤200%는 기존 "EPS −24.3% miss" 유지.
2-7. 상단 보조 컨트롤 1개: "거시 모두 펼치기 / 접기" 토글(칩 줄 우측, 세션 상태만 — 저장 안 함).
2-8. 테스트(vitest): 접힘 행 카운트·CRITICAL 미리보기 / 클릭 펼침 / 거시 단독 필터 시 펼침 / watch·휴장 항상 표시 / 지난 7일 순서·실제값 미수신 문구 / 세션 빈 칸 / 서프라이즈 200% 규칙 / 기존 캘린더·스트립 테스트 회귀. tsc 0 · lint 순증 0.
2-9. 행위보존: 변경 파일 = `apps/monitor/services/event_feed.py`(+테스트), `frontend/components/monitor/calendar/*`, `app/monitor/calendar/page.tsx`. 홈 `app/page.tsx`·`EventStrip.tsx`·BE API 무변(diff 0 입증).

## STEP 3 — 검증·보고
3-1. pytest(monitor·dashboard·architecture) GREEN · vitest 전체 GREEN · tsc 0 · eslint 0.
3-2. 실데이터 API 스모크(goid545 read-only): 캘린더 both — 거시 표본 3건의 ET/KST가 0-3 기대값과 일치 / 스트립 카드 KST 1건.
3-3. 하네스: DECISIONS(D-EVT-CORR-4 · D-EVT-FE-TUNE-1 원문) / TASKQUEUE(EVT-4B 완료, **MP-MACRO-CAL-1 별건 등재 — market_pulse 소유**, EVT-IMPL-4-SHOT 완료: 증적 = 2026-08-31 디렉터 채팅 첨부 5장·판정 통과) / PROGRESS / common-bugs("외부 캘린더 시각은 원문 시간대를 먼저 실측 — 필드 라벨을 믿지 않는다").
3-4. 커밋은 로컬 브랜치까지. 보고: §0 실측(0-3 표본표·0-4 값) / 변경 파일 / 게이트 표 / 3-2 스모크 / 지시서와 달랐던 점.

## HALT: 0-3 혼합 저장 / 시각 계약 충돌 / architecture RED / 2-9 범위 초과 / 예상 밖 일체.
