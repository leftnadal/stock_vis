# 지시서: Slice 20b-f2 — GOAL-CREATE-UI (B안: 전용 목표 생성 폼)

## 세션 계약 헤더
- 세션 종류: 실행(기능 슬라이스) — worktree에서 시작, 브랜치 monorepo/sess-X
- 범위: UserGoal 생성 POST + 온보딩 폼 화면 + 거버넌스 등재. 그 외 일절 확장 금지
- **절대 규칙:** dev DB = prod DB — migrate·shell 쓰기 = prod-write = 병진 수동 유보.
  라이브 확인용 데이터 생성은 병진 수동 + 세션 내 삭제·증명 의무(캡처 데모 규약)

## Part 0 — 지시서 repo 배치
- 이 지시서 전문을 docs/portfolio/coach/SLICE20BF2_INSTRUCTION.md로 커밋(첫 커밋).

## Part A — 거버넌스 등재 4건 (코드 작업 전 선행 커밋)
1. DECISIONS: 랜딩 관례 2건 — 게이트 캐리오버(전진분 disjoint 증명 시 게이트 유지
   + 착지 후 사후 3축 1회) / push 임시 권한(상시 금지, 경합 랜딩 한정·즉시 회수)
2. DECISIONS: **D-f2-0** = GOAL-CREATE-UI를 B안(전용 폼)으로 확정(병진, 07-31) +
   **D-f2-1** = 생성은 POST 단일 경로, PATCH는 엄격 유지(upsert 금지) +
   **D-f2-2** = GoalForm 단일 컴포넌트 2모드(create/edit) — 입력 표면 1벌 원칙
3. common-bugs.md: "화면 ✓ ≠ DB 영속" — 상태 생성 체크는 확인 쿼리 동반 필수
4. TASKQUEUE: RUN-TOTAL-PERSIST(run별 total_krw 미보존 — 동일 ET-date upsert 덮어씀
   + AdvisoryRun.output에 total 없음; SIGNAL-FORWARD-INFRA 합류 후보) 등재
   + GOAL-CREATE-UI 항목은 본 슬라이스로 종결 처리

## STEP 0 — ground truth 측정 게이트 (전부 실측, 추정 금지)
1. worktree·origin/main HEAD·기존 브랜치 확인.
2. UserGoal 모델 실측: 필드·검증·기본값·unique 제약(user당 1개?), 시리얼라이저 현황.
3. 20a/20b REST 표면 실측: 목표 부재 시 읽기 API 응답(404 vs null 필드), knobs PATCH의
   404 경로, DRF 라우터 구조 — POST를 어디에 얹을지 결정 근거.
4. 프론트 실측: 손잡이 패널 컴포넌트 구조(폼 코어 추출 가능성), /advisory의 목표 부재
   렌더 경로, react-query·MSW·vitest 기존 패턴.
5. **HALT 조건:** user당 UserGoal이 1개 제약이 아니거나(복수 목표 구조), 폼 코어 추출이
   행위보존 불가 구조면 → 정지 후 보고.

## Part 1 — 백엔드: POST 생성 엔드포인트
- POST(목표 생성): 목표수익률·기간·성향 수령, 이미 존재 시 409(생성 경로 단일 원칙).
  D0 가산 전용 — 기존 필드·PATCH 의미 무변경. 기존 시리얼라이저 최대 재사용.
- pytest: 생성 성공 / 중복 409 / 검증 실패 / PATCH 404 유지(회귀) 케이스.

## Part 2 — 프론트: GoalForm 추출 + 온보딩 화면
- Step 2a (행위보존 리팩터): 손잡이 패널에서 폼 코어를 GoalForm(mode="edit")으로 추출.
  기존 vitest 전부 green = 행위보존 증명. 이 시점 분리 커밋.
- Step 2b: 목표 부재 시 /advisory가 온보딩 카드(제목·설명 + GoalForm mode="create")를
  렌더. 생성 성공 → 권유 화면으로 전환(react-query invalidate).
- MSW 핸들러(POST·409) + vitest: 부재 렌더 / 생성 전환 / 409 처리.

## Part 3 — 라이브 확인 (병진 수동 구간)
- Claude Code는 절차서만 출력: ① 병진이 shell로 일회용 테스트 유저 생성(prod-write 수동)
  ② 그 계정으로 온보딩 폼 → 생성 → 권유 화면 전환 확인 ③ **확인 쿼리로 DB 영속 검증**
  (화면 ✓ ≠ DB 영속) ④ 병진이 테스트 유저 cascade 삭제 + 삭제 증명 쿼리 출력.
- goid545(실계정)는 목표 보유 상태이므로 건드리지 않는다.

## Closing 게이트
- pytest·vitest 전체 green / health_check 통과 / 경계 가드 통과(신규 위반 0)
- 비용 원장(cost_ledger.jsonl) 기입 / PROGRESS·TASKQUEUE 갱신
- 의미 단위 분리 커밋(Part A / STEP 0 기록 / Part 1 / 2a / 2b) 확인 후 닫기 보고
- **게이트 실패 = 즉시 정지 후 보고**(되돌리기 금지)
