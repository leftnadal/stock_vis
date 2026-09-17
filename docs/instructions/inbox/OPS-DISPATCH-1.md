---
track: OPS-DISPATCH-1
status: queued — 착수 조건 OPS-GATE-1 착지
decision: D-OPS-BRIDGE ⑴ 메일박스 + Mac 상주 디스패처(A 4.20) — 병진 승인 2026-09-16
---

# OPS-DISPATCH-1 — inbox 감시 디스패처 (`claude -p` 헤드리스) + STATUS 갱신

**세션**: ops 구현 · `wt-open ops-dispatch1`. **참조 모델**: `~/stock-vis-nightly/`의 tier3(`claude -p` 헤드리스·lockfile·타임스탬프 로그) + `auto_agent_system/dogfood/com.stockvis.dogfood.plist`(런타임 트리 기준 실행). 디렉터 사전 실측은 봉인 — STEP 0에서 실측.

## S1 — `scripts/ops/dispatch.sh`
1. 트리거: launchd `WatchPaths` = `~/Desktop/stock_vis/docs/instructions/inbox/`(+ 05분 간격 폴링 폴백). lockfile로 단일 실행. 2. 대상 = `status: dispatched`이고 `outbox/<트랙>_보고.md`가 없는 inbox 파일(가장 오래된 1건). 3. `wt-open <트랙소문자>`(이미 있으면 재사용) → `cd` → `claude -p "$(cat inbox/<트랙>.md)" --permission-mode acceptEdits --allowedTools "<STEP0 실측으로 확정: Read,Edit,Write,Grep,Glob,Bash(git *),Bash(pytest *),Bash(npx *),Bash(python *),Bash(scripts/ops/land.sh *)>" --max-turns <N> --output-format json` → 세션ID를 `outbox/<트랙>.session` 저장(HALT 후 `--resume`용). 4. 종료 후 outbox 보고 존재 확인 → 없으면 `outbox/<트랙>_보고.md`에 "판정 불능 — 실행자 보고 미생성 + 로그 경로" 자동 기재. 5. `python scripts/ops/status.py`(OPS-STATUS-1 전이면 skip) → 커밋은 실행자 브랜치에. 6. 로그 `~/Library/Logs/stockvis/dispatch_<날짜>.log`.
- **디렉터 재개**: HALT 보고에 답할 때 디렉터가 `inbox/<트랙>.md` 하단에 `## 재개 지시 <ISO>` 절을 추가 → 디스패처가 `--resume <세션ID>`로 이어 간다.
- 훅(OPS-GATE-1)이 헤드리스에도 적용됨을 확인(`.claude/settings.json` 추적 파일).

## S2 — plist **초안** `scripts/ops/launchd/com.stockvis.dispatch.plist.proposed`
WorkingDirectory·ProgramArguments = 런타임 트리 기준(D-LAUNCHD-RUNTIME-TREE) — 단 dispatch.sh는 본체 inbox를 읽는다(경로 상수 1곳). `plutil -lint` 통과. **등록(bootstrap)은 병진 수동 1회** — 상신 문장 1줄을 보고에.

## S3 — health_check 2항목
`H-INBOX-STALE`: `dispatched` 후 24h 내 outbox 없음 → WARN, 48h → ERROR. `H-OUTBOX-UNGRADED`: outbox 보고에 디렉터 판정(`verdict:` 줄) 없음 3일 → WARN. 기존 항목 구조·exit code 불변.

## S4 — 검증
가짜 inbox 1건(`echo`만 시키는 지시서)으로 end-to-end 1회: 감지 → worktree → 헤드리스 실행 → outbox 생성 → 로그. `--dry-run` 시 명령만 출력. 유닛: 대상 선택(오래된 1건·이미 보고 있음 제외)·lock·세션ID 저장 3건.

## 금지·보고
launchd 등록 자기 집행 금지(초안+상신만) · 병진 개인 자격증명 요구 금지(D-AUTO-NO-PERSONAL-CREDS) · prod DB 무접촉. 보고 = outbox 25줄: 판정 · 파일 · e2e 로그 요지 · plist 상신 1줄 · health 2항목 실기 결과 · 랜딩(`approvals/OPS-DISPATCH-1.ok` 대기).
