# EVT-CORR-3 — 재관측 시 stale→scheduled 복원 + 일괄 치유 (보정3, 소형·수집기 견고화)

전제: EVT-IMPL-4 push 완료 후 착수(origin/main = 4호 머지 커밋). 설계 앵커 v1.1 §2 "날짜 이동 v1 = 소실 감지" 준수.
근거: 4호 0-5⑹ 실측 — `record_observation`은 defaults만 갱신(status 무변), `_persist_event`는 occurred 상향만.
→ 한 번 stale이 된 행은 FMP가 다시 돌려줘도 영원히 stale(캘린더 기본 숨김에 갇힘). 소실 감지에는 **복원 짝**이 필요.
범위 밖: 원장 스키마·FE·연합 읽기 변경. push는 "푸시" 지시 대기.

## §0
0-1. `git fetch origin` → sv-evt-1 재사용, origin/main 기준 새 브랜치 `monorepo/sess-evt-5`. 해시 보고.
0-2. [0번 게이트] `docs/instructions/EVT-CORR-3.md` 1파일 커밋.
0-3. 실측(수치 캐리오버 금지): stale 전량을 last_seen_at 날짜별로 분해(≤08-28 / 08-29 / 08-30 / 08-31 / 이후) × event_date≥오늘 여부.
     **결함 행 = stale AND last_seen_at ≥ 최근 성공 run 시작 시각**(= 최신 fetch에 포함됐는데 복원 안 된 행). 수와 심볼 표본 5개 보고.
     (last_seen이 그 이전인 stale 행은 최신 fetch에 없었던 것 → 정당한 stale, 치유 대상 아님.)

## STEP A — 복원 배선
A-1. `_persist_event`(또는 record_observation 호출부): 재관측 시 `status == stale` → `scheduled` 복원. eps_actual/실적 등장 시 occurred 상향 규칙은 그대로 우선. occurred는 복원 대상 아님(다운그레이드 없음 유지).
A-2. 텔레메트리: 성분별 `revived` 카운터 + 심볼 로그. 기존 nulled/skipped/depth 텔레메트리 형식과 동형.
A-3. 테스트: stale 행 재관측 → scheduled·count+1 / occurred 행 재관측 → occurred 유지 / revived 카운터 / 기존 30+ 회귀 GREEN.

## STEP B — 일괄 치유 (foreground 1회)
B-1. 0-3 "결함 행" 집합만 `status=scheduled`로 갱신(updated_at 갱신, last_seen 무변). 전후 count SQL 인용.
B-2. **HALT**: 결함 행 > scheduled 전체의 5% 또는 0-3 분해가 가설(최근 run 포함 행만 결함)과 어긋나면 치유 전 HALT.
B-3. 익일 게이트 [EVT-OBS-2]: 다음 발화 후 revived 텔레메트리 존재 + 결함 행 재발 0 — TASKQUEUE 등재(검증 예정일 명시).

## STEP C — 하네스
DECISIONS: D-EVT-CORR-3(복원 규칙, 근거 실측) / common-bugs: "외부 원장 소실 감지(stale)는 복원(revive) 짝 없이는 단방향 함정 — 재관측 시 반드시 복원" / TASKQUEUE: EVT-CORR-3 완료·EVT-OBS-2 등재 / PROGRESS.

## 보고: 0-3 분해표 · 변경 파일 · 테스트 표 · B-1 전후 count · 하네스 요지. HALT: B-2 / 예상 밖 일체.
