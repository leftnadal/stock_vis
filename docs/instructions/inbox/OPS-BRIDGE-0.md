---
track: OPS-BRIDGE-0
status: dispatched 2026-09-16 (Cowork 디렉터)
approved_by: 병진 2026-09-16 "동의해. 진행하자" — 관제판 §08 ①②(즉시 랜딩 2건 + 배포) 승인
approved_sha: b0fadfa3 (CS-S3-1D, 본체 main 직접 커밋분) · e1b8e345 (EOD-TIME-1, monorepo/sess-eod-time1)
---

# OPS-BRIDGE-0 — main 발산 해소 + 즉시 랜딩 2건 + 배포 + 결정 3건 등재

**세션**: ops · cwd = 본체 `~/Desktop/stock_vis`(main 전용 머지 지점). 부트스트랩 체인(CLAUDE.md → STARTUP_CHECKLIST → SESSION_CONTRACT) 준수.
**승인 범위**: 위 `approved_sha` 두 커밋에 한정. **브랜치 HEAD가 그 SHA가 아니면 HALT**(INC-005 — 승인 SHA 이탈 금지).
**디렉터 실측(13:33 KST, 재측정 대상)**: 본체 main=`b0fadfa3`(ahead1/behind5) · origin/main=`bdadd045` · sess-eod-time1=`e1b8e345`(ahead2/behind46) · 런타임 3트리=`2eca515d`.

## S0 — 앵커 (다르면 HALT)
`git fetch origin --prune` → 본체 `main`==`b0fadfa3`, `origin/main`==`bdadd045`(전진했으면 새 해시 보고 후 계속 가능), 본체 tracked dirty 0(`git status --porcelain --untracked-files=no`), `monorepo/sess-cs-s3-1d` **부재** 확인.
본체 `.git/index.lock.stale-cowork-20260916`(0바이트, 디렉터 사고 잔여)는 무해 — 건드리지 않는다.

## S1 — 발산 해소 (내용 판단 없음: 커밋을 브랜치로 옮기고 main을 되돌린다)
1. `git branch monorepo/sess-cs-s3-1d b0fadfa3` → `git merge-base --is-ancestor b0fadfa3 monorepo/sess-cs-s3-1d` 참 확인.
2. `git worktree add ~/worktrees/sv-cs-s3-1d monorepo/sess-cs-s3-1d`.
3. 본체: `git reset --hard origin/main` → `main`==origin/main 확인. (커밋은 1에서 보존됨 — 유실 0. 비추적 29건은 reset 영향 없음.)

## S2 — CS-S3-1D 랜딩 (worktree `sv-cs-s3-1d`)
역머지 `git merge origin/main` → 충돌 시 **HALT**(장부 3파일 충돌만 양쪽 보존 append 허용) → 게이트: `vitest` 전체 · `pytest tests/` 전체 · `tsc --noEmit` **모두 0 failed** 아니면 HALT+실패 목록 → 본체 main no-ff 머지 → 머지 직전 `fetch`로 origin/main 재확인(움직였으면 GUARD-1D 규칙: 흡수 후 1층 재실행) → push → `fetch` 후 ahead 0 확인.

## S3 — EOD-TIME-1 랜딩 (worktree `sv-eod-time1`, HEAD `e1b8e345`)
1. **장부 선기재(이 브랜치에서, 머지 전)**:
   - `docs/instructions/inbox/` 4파일(README·OPS-BRIDGE-0·OPS-GATE-1·OPS-DISPATCH-1)을 본체에서 이 worktree로 복사해 커밋(0번 게이트 사후 충족).
   - `DECISIONS.md` **D-OPS-BRIDGE**: 병진 승인 3건 — ⑴ 지시서 통로 = A 메일박스+디스패처(4.20) 구축, 구축 중 B Remote Control(3.75) 운용 ⑵ 랜딩 게이트 = ⓑ 랜딩 승인 1회(4.25, 타이브레이커 안전) — `approvals/<트랙>.ok`(sha) → 역머지→게이트→머지→push→sync→FE리빌드, HALT는 충돌/RED/마이그·beat·plist·prod-write 동반 3경우, 병진 수동 항목 불변 ⑶ 장부 = ⓑ STATUS 자동생성+회전(4.15). 근거 문서: 프로젝트 `claude/판독_하네스점검_결정3건_20260916.md`. D-PUSH-DELEG (ii)·"푸시 1회 1승인"은 **OPS-GATE-1 착지 시 v2로 대체 예정**(그때까지 현행).
   - `TASKQUEUE.md`: EOD-TIME-1 → LANDED 예정 표기 / 신규 `OPS-GATE-1`·`OPS-DISPATCH-1`·`OPS-STATUS-1` 등재(inbox 참조) / `EOD-FRESH-2` "R1 재측정 선행" 유지.
   - `PROGRESS.md` 갱신 1블록.
2. 역머지 `git merge origin/main`(behind 46+) → 충돌 규칙 S2와 동일 → 게이트 → 본체 no-ff 머지 → 직전 fetch 재확인 → push → ahead 0.

## S4 — 배포 (§H D-DEPLOY-DELEGATE + 위 승인 인용)
`sv sync`(**`~/bin/sv` 래퍼 경유**, worker_sync.sh 직접 호출 금지) → 3트리 HEAD==새 origin/main 확인 → CS-S3-1D에 frontend 변경 있음 → **web 프로덕션 리빌드 = `docs/runbook/DEPLOY.md` §2.2 절차 그대로**(빌드 실패 시 .next.bak 복원·중단) → `:3000` 200 · daphne 401 정상 · `python scripts/health_check.py` ❌ 신규 0.

## 금지
force/force-with-lease · 브랜치·worktree **삭제** · 원격 브랜치 삭제 · prod DB migrate/쓰기 · launchd plist 변경 · beat 엔트리 변경 · 타 세션 브랜치(`sv-dss-asof` 등 활성) 무접근.

## 보고 — `docs/instructions/outbox/OPS-BRIDGE-0_보고.md` (커밋) + 채팅 답신, **25줄 이내**
① 판정 1줄(합격/불합격/HALT) ② 해시 표: 본체 main·origin/main **전/후**, 3트리, 새 머지 커밋 2개 ③ 게이트 숫자(vitest/pytest/tsc × 2회) ④ 배포 확인 3종(:3000·daphne·health) ⑤ 장부 추기 커밋 ⑥ HALT였다면 지점·원인·디렉터에게 묻는 질문 1줄.
