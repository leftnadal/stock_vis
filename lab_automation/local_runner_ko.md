# MacBook Local Runner v0.1

**Status:** Implementation Candidate  
**Branch:** `lab-automation/bootstrap-v0.1`

## 0. 한눈에 보는 요약

첫 Local Runner는 다음까지만 자동으로 수행한다.

```text
local/GitHub job file
→ isolated local worktree + candidate branch
→ authority snapshot
→ Codex CLI
→ tests
→ structured result artifacts
→ local candidate commit
→ waiting_for_push_approval
```

다음은 절대 수행하지 않는다.

- `git push`
- PR 생성/merge
- deploy
- main/master 직접 작업
- production DB write
- destructive action

## 1. Runtime State

운영 ledger는 기본적으로 repository 외부에 저장한다.

```text
~/.stockvis-lab-automation/
└── ledger/
    └── <job_id>.jsonl
```

이유:

- Claude Code가 사용하는 기존 checkout을 더럽히지 않는다.
- runtime telemetry와 canonical repository artifact를 분리한다.
- 실패한 run도 repository commit 여부와 무관하게 남긴다.

각 run의 연구 결과물은 candidate worktree 안의:

```text
.lab_automation/runs/<job_id>/<run_id>/
```

에 생성되어 candidate commit에 포함된다.

## 2. Candidate Branch

runner는 원본 job branch를 직접 수정하지 않고 다음과 같은 로컬 branch를 만든다.

```text
lab-run/<job-id>/<run-id-prefix>
```

candidate commit이 만들어진 뒤 worktree는 제거할 수 있지만 로컬 branch는 남는다.

따라서 CEO가 push를 승인하면 **정확한 candidate branch와 SHA**를 대상으로 promotion할 수 있다.

## 3. Dry Run

기본 실행은 dry-run이다.

```bash
python -m lab_automation.local_runner \
  --repo /path/to/stock_vis \
  --job /path/to/job.json
```

이 모드에서는 Codex나 git mutation을 실행하지 않고 contract와 authority loading 흐름을 점검한다.

실제 실행은 명시적으로 `--execute`를 붙여야 한다.

```bash
python -m lab_automation.local_runner \
  --repo /path/to/stock_vis \
  --job /path/to/job.json \
  --execute
```

## 4. First Job

첫 end-to-end candidate는:

`lab_automation/jobs/math_daily_price_readiness.example.json`

이다.

목표는 Math Lab의 DailyPrice readiness probe다.

## 5. Minimum Completion Evidence

성공한 run은 최소한 다음 evidence를 남겨야 한다.

1. intake event
2. exact base SHA
3. candidate branch
4. authority snapshot
5. Codex invocation record
6. declared DB/network policy
7. test results
8. agent report
9. result.json
10. data_gaps.json
11. manifest.json
12. candidate SHA
13. `waiting_for_push_approval`
14. push/merge/deploy=false

## 6. Safety Boundary

v0.1에서 runner는 다음 job을 거부한다.

- `branch=main/master`
- `db_access`가 `none/read_only` 이외
- destructive action 허용
- allowed write paths가 없음

Codex가 allowed path 밖의 파일을 수정하면 candidate commit 전에 runner가 실패한다.

## 7. Known Limitations

현재 구현만으로 OS-level sandbox를 보장하지는 않는다.

특히 다음은 다음 iteration에서 강화해야 한다.

- 실제 read-only DB credential 강제
- shell/network sandbox
- secret 접근 제한
- Codex CLI version capture
- timeout / resource budget
- job polling / locking
- concurrent-run collision handling
- promotion command

따라서 첫 real run은 개발용 MacBook 환경에서 제한된 read-only job으로만 수행한다.

## 8. Evolution

모든 실패와 retry는 ledger에 남긴다. 반복되는 실패는 runner 개선 후보가 되며, 새 runner version은 기존 version과 비교 평가한 뒤 채택 또는 rollback한다.
