---
track: OPS-GATE-1
status: queued — 착수 조건 OPS-BRIDGE-0 착지
decision: D-OPS-BRIDGE ⑵ 랜딩 승인 1회(ⓑ 4.25) — 병진 승인 2026-09-16
---

# OPS-GATE-1 — 랜딩 승인 게이트: `land.sh` + push 훅 + D-PUSH-DELEG v2

**세션**: ops 구현 · `bash scripts/wt-open.sh ops-gate1 "랜딩 승인 게이트"` → `~/worktrees/sv-ops-gate1`.
**목적**: "병진 승인 1회 = 흡수→게이트→머지→push→sync→(FE)리빌드"를 **문서가 아니라 스크립트+훅**이 지키게 한다. INCIDENTS 6건 중 4건(001·002·003·006)이 문서 규칙을 실행자가 어긴 사건이다.

## S1 — `approvals/` 규약
`approvals/<트랙>.ok` — 키=값 4줄: `track=` `sha=`(승인 시점 브랜치 HEAD, 필수) `approved_by=병진` `at=<ISO>` `via=cowork`. 디렉터가 커밋한다. `.ok`는 소비 후 삭제하지 않고 `used_by=<머지커밋>` 1줄 추기(이력).

## S2 — `scripts/ops/land.sh <worktree> <branch> [--dry-run]`
순서 고정, 각 단계 실측을 stdout에 표로:
1. `.ok` 존재 + `sha`==브랜치 HEAD(아니면 **exit 3 "승인 SHA 이탈"**) 2. `fetch` → 역머지 `git merge origin/main`(충돌 → exit 4, 충돌 파일 목록; 장부 3파일만 union 자동 허용) 3. 게이트 `vitest`·`pytest tests/`·`tsc --noEmit` 0 failed(아니면 exit 5 + 실패 목록) 4. 마이그·beat·plist·prod-write 동반 감지(`git diff origin/main --name-only`에 `*/migrations/*`·`*.plist`·`config/celery*`·beat 등록 코드 → exit 6 "병진 수동 항목 동반 — HALT") 5. 본체 main ff→origin/main, no-ff 머지 6. 머지 직전 `fetch` 재확인(움직였으면 2~3 중 1층만 재실행, GUARD-1D 규칙) 7. push → ahead 0 8. `sv sync` → 3트리 정렬 9. `frontend/` 변경 있으면 DEPLOY.md §2.2 리빌드 10. `.ok`에 `used_by=` 추기 + `outbox/<트랙>_보고.md` 골격 생성.
`--dry-run` = 1~4·6 검사만. **force 계열·삭제 명령은 스크립트에 존재하지 않는다.**

## S3 — PreToolUse 훅 (`.claude/hooks/guard_bash.sh`, `.claude/settings.json`에 등록 — repo 추적)
`tool_input.command`를 검사해 **deny**: `git push`(단, 명령이 `scripts/ops/land.sh`로 시작하면 허용) · `--force`/`--force-with-lease` · `git branch -D` · `git push … --delete`/`:refs` · `git worktree remove` · `launchctl bootout|bootstrap|load|unload` · `manage.py migrate`(테스트 settings 제외). deny 메시지는 "왜 막혔고 무엇을 하면 되는지"(Error Message as Teaching) 1줄.
`.claude/settings.local.json`(비추적) allow에서 `Bash(git push:*)`·`Bash(git reset:*)`·`Bash(pkill:*)` 제거 — 측정 후 목록 보고.

## S4 — 규약 문구 (단일 출처만 고침, 복제 금지)
- `docs/harness/session_isolation_guide.md` §D-PUSH-DELEG → **v2**: "push·머지·sync·리빌드는 `approvals/<트랙>.ok`가 가리키는 SHA에 대해 `land.sh`로만. behind>0는 HALT 사유가 아니라 land.sh의 역머지 입력이다. HALT = 충돌/RED/수동항목 동반. 병진 수동 항목(prod migrate·영구/강제 삭제·원격 브랜치 삭제·plist·beat 등록) 불변." INC-001 참조 유지.
- `SESSION_CONTRACT.md` §H·§E: 포인터 갱신 + §E의 `git add -A` 제거(금지 규칙과 충돌) + §B worktree 경로를 `~/worktrees/sv-*`(wt-open)로.
- `CLAUDE.md` Harness Protocol에 1줄: "랜딩·배포 = approvals + scripts/ops/land.sh (D-PUSH-DELEG v2)".
- `scripts/hooks/pre-commit`: `EXPECTED_PATH` 경고 → "런타임 트리(sv-*-runtime)·본체 main 직접 커밋 금지" 검사로 교체, 사어 slice8~17 목록 제거.

## S5 — 검증·첫 적용
유닛: `.ok` 부재/SHA 불일치/충돌/RED/수동항목 동반 5분기 → 올바른 exit code(가짜 repo 픽스처). 훅: deny 7패턴·허용 1패턴. **첫 실적용 = 이 브랜치 자신**(디렉터가 `approvals/OPS-GATE-1.ok` 커밋 후 `land.sh ~/worktrees/sv-ops-gate1 monorepo/sess-ops-gate1`). `sv-dss-asof`는 후보(활성 세션 — 그 트랙의 `.ok` 필요).

## 금지·보고
구현 전 push 금지(첫 push가 land.sh 자체 검증). 보고 = outbox `OPS-GATE-1_보고.md` 25줄: 판정 · 파일 목록 · 5분기+훅 테스트 결과 · settings.local 정리 diff · 규약 변경 diff 요지 · 자기 랜딩 해시.

## 실측 반영 2026-09-17 (OPS-BRIDGE-0 1차 실행에서 관측)
- **관측 1**: 자동 권한 분류기가 inbox 파일에서 온 지시로 본체 `git merge`를 실행하는 것을 "Instruction Poisoning → Modify Shared Resources"로 2회 거부. → **`land.sh`가 곧 해법**: 분류기가 보는 것은 `Bash(scripts/ops/land.sh <wt> <branch>)` 한 줄이며, `.ok`(승인 SHA) 검증이 스크립트 안에 있다. `.claude/settings.json` allow에 `Bash(scripts/ops/land.sh:*)`를 추적 파일로 등재.
- **관측 2**: 본체(main 전용 머지 지점)를 병렬 세션이 동시에 사용 — 실행자의 `reset --hard origin/main`(11:05) 1.5분 뒤 다른 세션이 같은 본체에서 sess-guide-macro 머지·push(11:06). INC-005 유형 near-miss. → land.sh S2 단계 앞에 **본체 락**(`.git/land.lock`, noclobber, 소유자·시각·pid 기록, stale 30분 초과 시 경고 후 HALT) + `MERGE_HEAD` 부재 + `main==origin/main` 3중 확인을 필수로. `reset --hard`는 land.sh에 넣지 않는다(발산 해소는 별도 명시 승인 절차).
