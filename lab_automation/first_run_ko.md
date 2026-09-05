# StockVis Lab Automation — MacBook First Run v0.1

**Status:** Working / Execution Guide  
**Target job:** `SV-MATH-DP-READINESS-001`  
**Promotion boundary:** local candidate commit까지만. Push/Merge/Deploy 금지.

## 0. 한눈에 보는 요약

첫 실행의 목적은 DailyPrice 연구결과 자체보다 **자동화 loop가 안전하게 한 번 끝까지 도는지** 검증하는 것이다.

```text
preflight
→ dry-run
→ restricted real run
→ local lab-run/* candidate branch
→ structured artifacts + append-only ledger
→ waiting_for_push_approval
```

첫 real run이 성공해도 자동 push하지 않는다.

## 1. Required local state

Repository의 automation checkout은 `lab-automation/bootstrap-v0.1`을 사용한다. 실제 작업 worktree는 Job이 선언한 `math-lab/data-eligibility-v0.1`에서 별도로 만들어진다.

필수 도구:

- git
- Python 3.12 compatible environment
- Poetry
- Codex CLI
- PostgreSQL connectivity

프로젝트 의존성은 `pyproject.toml`에 선언된 Poetry 환경을 사용한다.

## 2. DB safety

StockVis Django settings는 PostgreSQL 연결에 `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`를 사용한다.

첫 run에서는 launcher가 child process에 다음을 강제한다.

```text
PGOPTIONS=-c default_transaction_read_only=on ...
STOCKVIS_LAB_DB_ACCESS=read_only
```

가능하면 더 강한 방어선으로 전용 PostgreSQL read-only role을 사용한다.

로컬 secret은 Git에 넣지 않는다. 필요하면 shell environment에만 둔다.

```bash
export STOCKVIS_LAB_DB_USER="<read-only-role>"
export STOCKVIS_LAB_DB_PASSWORD="..."
export STOCKVIS_LAB_DB_HOST="localhost"
export STOCKVIS_LAB_DB_PORT="5432"
```

전용 role이 아직 없다면 real run 전 Data Platform 작업으로 생성 여부를 검토한다. 현재 launcher의 read-only session guard는 방어층이지 privileged DB user의 권한 자체를 제거하는 장치는 아니다.

## 3. Codex safety note

Codex CLI configuration은 실행 시점의 로컬 `~/.codex/config.toml` 및 조직 정책을 따른다.

현재 Codex CLI에서는 과거 `approval_policy = "untrusted"`가 더 이상 지원되지 않는다. 로컬 Codex 설정은 현재 지원되는 approval/sandbox 정책을 사용해야 한다.

Runner 자체는 Codex가 어떤 설정으로 실행되더라도 다음을 별도로 강제/검사한다.

- main/master Job 거부
- destructive action Job 거부
- DB write policy 거부
- allowed write path 밖 변경 시 실패
- push/merge/deploy 구현 없음
- local candidate branch만 생성

## 4. Step A — checkout automation branch

Claude Code가 쓰는 기존 작업폴더를 변경하지 않는 별도의 checkout/worktree를 권장한다.

예시:

```bash
cd <stock_vis repo>
git fetch origin
git worktree add ../stock_vis_lab_automation lab-automation/bootstrap-v0.1
cd ../stock_vis_lab_automation
poetry install
```

이미 해당 branch checkout이 있다면 새로 만들 필요 없다.

## 5. Step B — doctor

먼저 환경만 검사한다.

```bash
poetry run python -m lab_automation.doctor \
  --repo "$(pwd)" \
  --branch math-lab/data-eligibility-v0.1
```

Expected:

```text
git OK
python OK
poetry OK
codex OK
job branch exists
PostgreSQL probe: transaction_read_only=on
Overall: READY
```

`source_checkout_clean`은 warning으로 취급한다. 다만 실제 automation checkout은 깨끗하게 유지하는 것을 권장한다.

## 6. Step C — runner unit tests

```bash
poetry run python -m pytest \
  lab_automation/test_contracts.py \
  lab_automation/test_ledger.py \
  lab_automation/test_local_runner.py \
  lab_automation/test_doctor.py \
  -q
```

하나라도 실패하면 real run으로 가지 않는다.

## 7. Step D — dry-run

스크립트 실행권한을 부여하지 않아도 `bash`로 직접 실행할 수 있다.

```bash
bash lab_automation/run_first_job.sh
```

Dry-run에서는:

- Codex 실제 호출 없음
- worktree 생성 없음
- candidate commit 없음
- push 없음

하지만 Job parsing, authority refs, contract flow와 dry-run ledger를 점검한다.

## 8. Step E — restricted real run

Doctor와 tests, dry-run을 검토한 뒤에만:

```bash
bash lab_automation/run_first_job.sh --execute
```

Expected behavior:

1. `math-lab/data-eligibility-v0.1`에서 별도 worktree 생성
2. `lab-run/SV-MATH-DP-READINESS-001/<run-prefix>` local branch 생성
3. authority refs snapshot
4. Codex CLI execution
5. DailyPrice read-only readiness 작업
6. declared tests 실행
7. write-scope 확인
8. structured artifacts 저장
9. local candidate commit 생성
10. worktree 제거
11. candidate branch는 local repo에 보존
12. ledger 최종 상태 `waiting_for_push_approval`

## 9. Required result inspection

실행 후 반드시 확인한다.

### Local candidate

```bash
git branch --list 'lab-run/*'
git log -1 --oneline <candidate-branch>
git diff <base-sha>..<candidate-sha> --stat
```

### Ledger

기본 위치:

```text
~/.stockvis-lab-automation/ledger/SV-MATH-DP-READINESS-001.jsonl
```

다음 stage가 남아 있어야 한다.

```text
intake
authority_load
agent_execution
tests
candidate_revision: waiting_for_push_approval
```

실패 시에는 기존 events 뒤에 `terminal: failed`가 append되어야 한다.

### Candidate artifacts

candidate commit 안에 최소한:

```text
.lab_automation/runs/<job>/<run>/authority_snapshot/*
agent_report.md
result.json
data_gaps.json
codex_invocation.json
tests.json
manifest.json
```

이 있어야 한다.

## 10. Hard stop conditions

다음 하나라도 보이면 push approval을 요청하지 않고 run을 실패/보류한다.

- DB read-only verification 실패
- main/master 수정
- allowed write path violation
- test failure
- Codex non-zero return
- authority ref 누락
- candidate SHA 불명확
- manifest에서 push/merge/deploy=true
- ledger 단계 누락
- production schema/data 변경 정황
- secret이 artifact/commit에 포함됨

## 11. CEO review package after first run

첫 run 후 ChatGPT/Lead에게 다음만 전달하면 된다.

```text
Job ID
Run ID
base SHA
candidate branch
candidate SHA
changed paths
test summary
agent report
data gaps
ledger final state
```

Lead가 GitHub에 push하기 전 결과를 평가하고 CEO에게 다음 중 하나를 권고한다.

```text
Push 승인
수정 후 재실행
폐기
추가 검증
```

## 12. What this first run validates

이번 run의 성공 기준은 좋은 DailyPrice 결과가 아니다.

- MacBook runner가 격리되어 작동하는가
- 실제 authority를 읽는가
- DB가 read-only인가
- 기록이 단계별로 남는가
- 실패가 숨겨지지 않는가
- candidate branch/SHA가 보존되는가
- promotion boundary에서 정확히 멈추는가

이것이 확인된 뒤에만 GitHub polling과 Push Approval executor를 다음 vertical slice로 추가한다.
