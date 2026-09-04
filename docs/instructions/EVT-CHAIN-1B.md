# EVT-CHAIN-1B — 이벤트 위젯 상단 이동 + 앵커 (소형 FE, P1)

전제: EVT-CHAIN-1(+1a) 착지·라이브(런타임 04ec8bf7 계열). 시각 계약 = docs/design/monitor_detail_ux.html §(a) **P1**(2026-09-04 사용자 확정: P1 4.50 / P2 4.10 / P3 4.00).
범위: FE만. **모니터 소유 컴포넌트(상태 카드 등) 수정 금지** — 附加·삽입 라인만. BE·API·파라미터 무변. push는 "푸시" 대기.

## §0
0-1. `git fetch origin` → sv-evt-1 재사용, origin/main 기준 새 브랜치 `monorepo/sess-evt-9`. 해시 보고.
0-2. [0번 게이트] `docs/instructions/EVT-CHAIN-1B.md` + `docs/design/monitor_detail_ux.html`(디렉터 배치, untracked) 2파일 커밋.
0-3. 실측: `[id]/page.tsx` 현재 섹션 순서·ChainSection 삽입 지점, 상태 카드 컴포넌트 경계(수정 금지 대상 확정).

## STEP 1 — P1 구현
1-1. `UpcomingEventsWidget`을 **한 줄 pill 밴드**로 변형해 상태 카드 바로 아래로 이동(신규 얇은 컨테이너, 기존 카드 컴포넌트 무접촉): 어닝 pill(D-N·날짜·EPS 예상) + 배당락 pill + **"관계망 N ↓"** 요약 pill(이웃 수, 클릭 시 하단 타임라인 앵커 스크롤). 이벤트 없으면 밴드 자체 비표시.
1-2. 하단은 타임라인(배너+이웃 행)만 남김 — 위젯 중복 제거. 앵커 id 부여, smooth scroll.
1-3. 테스트(vitest): 밴드 렌더·이벤트 없음 비표시·관계망 pill 카운트·앵커 존재·scope!=stock 미렌더·기존 chain 테스트 회귀. tsc 0·lint 순증 0.
1-4. 행위보존: 기존 파일 diff = `[id]/page.tsx` 삽입 위치 이동분에 한정. 상태 카드·사다리·신호·근거·일지 diff 0 입증.

## STEP 2 — 검증·하네스
vitest 전체 GREEN. DECISIONS: D-EVT-CHAIN-1B(P1, 가중합·근거 = 9/3 실화면 "이벤트 섹션 하단 매몰" 피드백). TASKQUEUE: 완료 반영 + **MON-JOURNAL-1 초안 전달 사실**(모니터 트랙 소유) 등재. 커밋 로컬까지 → 보고 → "푸시" → :3000 재빌드(사용자 지시).

## 보고: 0-3 실측 / diff 목록 / 게이트 표. HALT: 상태 카드 수정 필요 판명(→P3 영역, 중단·보고) / 예상 밖.
