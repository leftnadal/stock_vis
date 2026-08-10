# 【지시서 GOV-PUSHDELEG-0810】 push 조건부 위임 규칙 명문화 + CLOSE-0808-PUSH 인시던트 등재

> 등재일: 2026-08-10 (machine clock) · 세션: 하네스 거버넌스 쓰기(문서 전용)
> 격리 worktree `~/worktrees/sv-govpush0810` [monorepo/sess-govpush0810], base origin/main `66338026` (Q4 예외 승인)

## ■ 세션 계약
- 종류: 하네스 쓰기 세션 (문서 전용 — 코드·설정·DB 변경 없음)
- 범위: CLAUDE.md(또는 부트스트랩 체인 내 규약 정본 위치) / DECISIONS.md / common-bugs.md /
  인시던트 대장 / TASKQUEUE / 지시서 파일. 이 외 파일 변경 금지.
- HALT-0 기본 적용. behind > 0 조우 시 이 지시서가 박는 바로 그 규칙대로 무조건 HALT
  (자가 rebase 절대 금지 — 이번 세션부터 즉시 적용).

## ■ STEP 0 — ground truth 재실측 (쓰기 전 필수)
0-1. git worktree list → origin/main 추적 트리 확인
0-2. git fetch 후 branch/HEAD/ahead·behind 실측 — behind > 0이면 HALT, 전진분 목록만 보고.
0-3. git status clean 확인 (dirty 시 HALT)
0-4. scripts/health_check.py 실행·기록 (참조: 14 OK / 1 WARN 동일 항목이면 통과)
0-5. 편집 대상 실측: 규약 정본 위치 / 인시던트 대장 위치·번호 / common-bugs 최신 번호 / DECISIONS 형식.

## ■ 작업 내용 — 의미 단위 커밋 2건
[커밋 1] 지시서 등재 → docs/instructions/GOV-PUSHDELEG-0810.md
[커밋 2] 규칙 명문화 + 기록 본체:
  (A) 규약 정본에 [D-PUSH-DELEG] 규칙 등재 (아래 전문)
  (B) DECISIONS.md D-PUSH-DELEG 등재 (배경/선택지/가중합/왜)
  (C) 인시던트 대장 CLOSE-0808-PUSH 등재
  (D) common-bugs 등재 (HALT 자가해제 불가)
  (E) TASKQUEUE 실증 게이트 등재

### [D-PUSH-DELEG] CC push 조건부 위임 규칙 (2026-08-10 확정)
1. CC는 병진의 세션 내 명시 지시가 있을 때에 한해 origin/main push를 실행할 수 있다.
   - "명시 지시" 정의(협의): "push"/"푸시" 단어를 포함한 직접 지시문만 유효.
     ("마무리해줘"·"올려줘"·"끝내줘" 등은 승인 아님 — push 명령어 후보만 보고하고 대기.)
   - 승인은 push 1회분에만 유효 (세션 단위 포괄 승인 불가).
2. push 실행 전 필수 가드 (순서 고정):
   (i)   git fetch 후 behind 재실측
   (ii)  behind > 0 → 무조건 HALT. rebase·merge 등 흡수 전략의 자가 판단·자가 실행 절대 금지.
         전진분 커밋 목록 + 충돌 위험 파일 교집합을 실측 보고하고 병진의 흡수 전략 승인을 별도로 받는다.
         ※ HALT는 자가 해제 불가 — 해제 권한은 병진 채팅 지시만.
         ※ 무충돌 실측(교집합 0)은 진행 근거가 아니라 보고 내용이다.
   (iii) force / force-with-lease 계열 전면 금지 (위임 대상 아님)
   (iv)  push 후 착지 검증 (fetch → ahead 0 확인 → origin/main 해시 보고)
3. 대체되는 것: "CC push 전면 금지" → 위 조건부 위임. 대체 안 되는 것: worker 재시작·launchctl·
   파괴적 브랜치 삭제 등 기타 병진 수동 집행 항목은 전부 현행 유지.

## ■ 디렉터 판정 (2026-08-10, HALT 해제 조건)
- Q1: health 15/0/0 수용·진행 승인 + common-bugs에 "참조 대비 개선 편차도 보고 필수·진행 가능" 1줄.
- Q2: 인시던트 대장 = docs/harness/INCIDENTS.md 신규 생성(이 1건 한해 생성 금지 해제). INC-001 번호제,
      형식 [경위/결과 손상/처분/교훈]. INC-001 = CLOSE-0808-PUSH.
- Q3: D-PUSH-DELEG 정본 = docs/harness/session_isolation_guide.md 신규 등재 + 기존 L11에 참조만 연결(삭제 금지).
      SESSION_CONTRACT에는 포인터 1줄. 지시서 "교체"→"신규 등재+참조 연결"로 정정 소비.
      DECISIONS에 "전면 금지 문언은 repo에 부재·본 결정이 최초 명문화" 발견 1줄.
- Q4: 격리 worktree 신설(가중합 자동, 마진 1.25). 브랜치 monorepo/sess-govpush0810 예외 승인.
      사후 정리는 TASKQUEUE 병진 수동 항목 등재만·실행 금지.
- 추가: DECISIONS·TASKQUEUE D-PUSH-DELEG에 "08-10 behind=3 및 다중 편차 HALT 2회 준수 실증(GREEN)" 반영.

## ■ 금지 사항
- push: 새 규칙 절차 준수 — 커밋 완료 보고 후 대기, "push/푸시" 명시 지시 시에만 가드 (i)~(iv).
- 코드·scripts·tests 변경 금지 / 브랜치 생성·삭제·rebase·merge 금지(Q4 예외 브랜치 1건 제외)
- 날짜는 machine clock만 사용 (규칙 #89)
