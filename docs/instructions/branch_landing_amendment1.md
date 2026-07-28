# 개정문 1: 브랜치 랜딩 — B안(no-ff 머지) 승인

- 발행: 감독 세션, 2026-07-28
- 배경: `sess-CN-repair`·`sess-MP-unify-s0`가 낡은 base 위라 origin/main에 ff push 불가(비-fast-forward 거부 확증). ff-only 원 지시로는 HALT.
- 결정: **B안 = no-ff 머지로 랜딩.** 원격 force push는 **여전히 절대 금지**. rebase 대신 병합 커밋으로 계보 보존.

## 절차 (엄수)

- **①** `git fetch` → main 추적 worktree에서 `git merge --no-ff monorepo/sess-CN-repair`
  - 충돌 시 **즉시 HALT**(해소 금지, 충돌 파일 목록 보고).
  - 무충돌이면 머지 결과에서 전체 스위트: **4050 GREEN / 13 사전존재(Neo4j-env attention6+leadership7) 기준 신규 실패 0** 확인.
  - 아톰 push → 같은 shell에서 origin/main 신 해시 재조회.
- **②** ① 착지 확인 후: `git diff --stat origin/main..monorepo/sess-MP-unify-s0`로 **docs-only 확증**(코드 파일 포함 시 HALT) → 동일 절차로 no-ff 머지·push.
- **③** 양쪽 완료 후 `health_check` 재실행 + 보고: 최종 origin/main 해시, 스위트 1줄, 머지 커밋 2건 해시.

## 불변

- 원격 force push 절대 금지. rebase 금지(B안=머지). 충돌 자가 해소 금지(HALT 보고).
- 브랜치 삭제 안 함 — 삭제 후보 보고만(병진 수동).
