# MacBook Local Runner v0.2

**Status:** Implementation Candidate  
**Branch:** `lab-automation/bootstrap-v0.1`

## 0. 한눈에 보는 요약

Local Runner는 다음까지만 자동으로 수행한다.

```text
local/GitHub job file
→ isolated local worktree + candidate branch
→ authority snapshot
→ immutable agent input snapshot
→ Codex CLI Invocation
→ content-addressed raw artifact storage
→ output contract check
→ tests
→ structured review artifacts
→ one local candidate commit
→ waiting_for_push_approval
```

다음은 절대 수행하지 않는다.

- `git push`
- PR 생성/merge
- deploy
- main/master 직접 작업
- production DB write
- destructive action

## 1. Runtime State and Artifact Store

운영 ledger와 raw artifact store는 기본적으로 repository 외부에 저장한다.

```text
~/.stockvis-lab-automation/
├── ledger/
│   └── <job_id>.jsonl
├── artifacts/
│   └── sha256/...
└── dry_runs/
```

이유:

- Claude Code가 사용하는 기존 checkout을 더럽히지 않는다.
- runtime execution history와 canonical repository artifact를 분리한다.
- 실패한 run도 repository commit 여부와 무관하게 남긴다.
- 성공한 worktree가 제거된 뒤에도 raw input/output을 복원할 수 있다.
- 실패한 real-run worktree는 조사할 수 있도록 보존하고 terminal event에 경로를 기록한다.

Artifact는 filesystem path가 아니라 `artifact://sha256/<digest>` logical URI로 식별한다. `--state-root`를 다른 디스크로 옮겨도 logical identity는 유지된다.

## 2. Candidate Review Artifacts

실제 run에서는 작은 reviewable 결과를 candidate worktree의 다음 경로에 만든다.

```text
.lab_automation/runs/<job_id>/<run_id>/
```

예:

- authority snapshot copy
- `agent_report.md`
- `result.json`
- `data_gaps.json`
- `codex_invocation.json`
- `tests.json`
- `manifest.json`

그러나 ledger의 canonical artifact reference는 이 temporary worktree path가 아니라 external content-addressed Artifact Store의 logical URI다.

## 3. Run and Invocation

Run은 logical work unit이고 Invocation은 actual backend attempt다.

```text
Run
  ├─ Invocation primary
  ├─ Invocation retry       # 필요 시
  └─ Invocation replication # 필요 시
```

v0.2 first runner는 primary Codex Invocation 하나를 기록하지만, shared contract는 retry/replication을 별도 identity로 확장할 수 있다.

## 4. Immutable Input Snapshot

Codex 호출 전에 다음을 external artifact로 보존한다.

- exact prompt
- Job envelope + raw Job
- base SHA
- authority snapshot artifact refs
- runner version

따라서 실제 실행 후 prompt를 현재 runner 코드에서 다시 추정하지 않는다.

## 5. Output Provenance and Contract

실제 `--execute` run에서 runner는 required agent file을 대신 만들지 않는다. executor가
`agent_report.md`, `result.json`, `data_gaps.json` 세 파일을 모두 직접 만들어야 한다.
report는 비어 있지 않아야 하고 두 JSON 파일은 실제로 parse되어야 하며,
`result.json`의 빈 object (`{}`)는 거부한다. gap이 없으면 executor가
`data_gaps.json`에 `[]`를 쓴다.

Origin 예:

```text
agent_generated
missing
dry_run_placeholder
runner_generated
```

Dry-run은 executor를 호출하지 않으므로 `dry_run_placeholder`만 만들며 파일 내용과
ledger stage를 모두 dry-run 전용으로 명시한다. 이 placeholder는 real output으로
취급되지 않는다.

## 6. Candidate SHA

candidate manifest에는 최종 candidate SHA를 canonical field로 쓰지 않는다.

```text
manifest content
→ commit hash에 영향
```

때문에 manifest가 자기 commit SHA를 포함하려 하면 자기참조가 생긴다.

최종 candidate SHA는 external append-only Run Ledger의 `candidate_revision` event에 기록한다.

## 7. Candidate Branch

runner는 원본 job branch를 직접 수정하지 않고 다음과 같은 로컬 branch를 만든다.

```text
lab-run/<job-id>/<run-id-prefix>
```

candidate commit이 만들어진 성공 run은 worktree를 제거할 수 있지만 로컬 branch는
남는다. 실패한 real run은 worktree와 내부 artifact를 보존하고 terminal event의
`preserved_worktree_path`에 위치를 남긴다. Git commit 실패는 command, stdout,
stderr, return code를 `command_failure` artifact로 보존하고 그 logical URI를 같은
terminal event에서 참조한다. CEO가 push를 승인하면 정확한 candidate branch와
external ledger의 final SHA를 대상으로 promotion한다.

## 8. Dry Run

기본 실행은 dry-run이다.

```bash
python -m lab_automation.local_runner \
  --repo /path/to/stock_vis \
  --job /path/to/job.json
```

Dry-run 결과물은 repository가 아니라 `state_root/dry_runs/` 아래에 둔다.

실제 실행은 명시적으로 `--execute`를 붙인다.

```bash
python -m lab_automation.local_runner \
  --repo /path/to/stock_vis \
  --job /path/to/job.json \
  --execute
```

## 9. Safety Boundary

v0.2에서도 runner는 다음 job을 거부한다.

- `branch=main/master`
- `db_access`가 `none/read_only` 이외
- destructive action 허용
- allowed write paths가 없음

Codex가 allowed path 밖의 파일을 수정하면 candidate commit 전에 runner가 실패한다.
Codex가 exit code 0을 반환해도 Job의 `allowed_write_paths` 아래에 실제 workload 변경이
하나 이상 없으면 실패한다. runner가 만든 `.lab_automation` 파일은 이 판정에서 제외한다.

## 10. Known Limitations

현재 구현만으로 OS-level sandbox를 보장하지는 않는다.

특히 다음은 후속 iteration에서 강화해야 한다.

- 실제 read-only DB credential 강제
- shell/network sandbox
- secret 접근 제한
- Codex CLI / actual model identity 강한 capture
- timeout / resource budget
- job polling / locking
- concurrent-run collision handling
- retry controller
- promotion command
- multi-backend Artifact Replica 관리

따라서 real run은 제한된 read-only job으로만 수행한다.
