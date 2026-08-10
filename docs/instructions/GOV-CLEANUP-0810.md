# 【지시서 GOV-CLEANUP-0810】 INC-002 등재 + D-BRANCH-DELETE-MANUAL 명문화 + 장부 정합

> 등재일: 2026-08-10 (machine clock) · 세션: 하네스 거버넌스 쓰기(문서 전용)
> 격리 worktree `~/worktrees/sv-govcleanup0810` [monorepo/sess-govcleanup0810], base origin/main `49f1db6f` (사전 승인)

## ■ 세션 계약
- 종류: 하네스 쓰기 세션 (문서 전용 — 코드·설정·DB 변경 없음)
- 범위: INCIDENTS.md / session_isolation_guide.md / DECISIONS.md / TASKQUEUE.md / common-bugs.md / 지시서 파일. 6종 외 변경 금지.
- HALT-0. behind>0 조우 시 D-PUSH-DELEG 공통 가드대로 무조건 HALT.

## ■ 격리 (사전 승인)
- 브랜치 monorepo/sess-govcleanup0810 + 격리 worktree 신설 예외 승인(D-GOVPUSH Q4 동일 근거).
- 사후 정리는 D-BRANCH-DELETE-MANUAL대로 병진 수동 — TASKQUEUE 등재만, CC 실행 절대 금지.

## ■ STEP 0 — ground truth 재실측
0-1. origin/main fetch → base 실측(실측 정본). 격리 브랜치는 실측 origin/main에서 분기.
0-2. status clean / health_check (악화 편차만 HALT, 개선 편차는 보고 후 진행).
0-3. 편집 대상 실측 + 채번 자격 판정(D-NUMBERING-MGMT-ONLY 문언). 자격 있으면 일괄 실번호, 없으면 채번 후보. 모호 시 HALT.
0-4. GOVPUSH-CLEANUP·D-PUSHDELEG-PROVE 현재 문구 확인.

## ■ 작업 — 커밋 2건
[커밋 1] 지시서 등재 → docs/instructions/GOV-CLEANUP-0810.md
[커밋 2] 본체:
  (A) INCIDENTS.md INC-002 = GOVPUSH-CLEANUP-EXEC (경위 3 / 손상 0 / 처분 / 교훈)
  (B) session_isolation_guide.md §D-BRANCH-DELETE-MANUAL 신설
  (C) DECISIONS.md D-BRANCH-DELETE-MANUAL (배경/선택지/가중합 A 4.45·B 3.30 마진 1.15/왜)
  (D) common-bugs 2건 (채번 자격대로)
  (E) TASKQUEUE GOVPUSH-CLEANUP→done·PROVE 2차 실증·GOVCLEANUP-0810 정리 신규

### [D-BRANCH-DELETE-MANUAL] 파괴적 브랜치 삭제 수동 고정 (2026-08-10)
1. 브랜치 삭제(-d/-D)·worktree 제거·원격 브랜치 삭제는 **위임 불가 — 병진 수동 고정**. 세션 내
   예외 승인으로도 CC 집행 불가(승인 실체와 집행 주체는 별개 층위 — 삭제는 저빈도·비가역이라 위임 실익 없음).
2. CC는 삭제 후보 목록 + 안전 실측(origin/main..브랜치 카운트)까지만 보고하고 대기.
3. `git branch -d` 거부("not fully merged") 조우 시 무조건 HALT — **-D 자가 전환 절대 금지**.
   무해 실측은 보고 내용이지 진행 근거가 아님.

## ■ 금지 사항
- push: D-PUSH-DELEG 절차, "push/푸시" 명시 지시 대기, 가드 (i)~(iv), behind>0 무조건 HALT.
- 브랜치·worktree 정리 실행 금지(신설 승인은 생성에만 유효).
- 코드·scripts·tests 변경 금지 / 날짜는 machine clock만(#89).

## ■ STEP 0 판정 결과 (실행 시 기록)
- base origin/main = `49f1db6f` · status clean · health 15/0/0(참조 동일)
- 채번 자격 = **없음**(거버넌스 세션, mgmt 아님) → common-bugs 전부 **채번 후보**
