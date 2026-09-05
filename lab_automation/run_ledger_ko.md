# StockVis Lab Automation — Run Ledger & Evolution Feedback v0.1

**Status:** Working Candidate  
**Date:** 2026-09-05

## 0. 한눈에 보는 요약

Lab Automation Platform은 작업을 단순 실행하고 끝내는 도구가 아니다. **각 단계의 입력, 상태 변화, 출력, 실패, 승인, 버전과 비용을 기록하고 그 기록을 플랫폼 자체 개선의 근거로 사용하는 learning system**이어야 한다.

기본 원칙:

> If a material stage happened, it should leave a reconstructable operational record.

단, 모든 stdout과 임시 thought를 영구 보존하는 것은 아니다. 미래에 재구성·평가·감사·개선에 필요한 material record만 canonical하게 남긴다.

## 1. Canonical Runtime Object

각 Job은 하나 이상의 Run을 가질 수 있다.

```text
Job
  └─ Run #1
       ├─ intake
       ├─ workspace_prepare
       ├─ authority_load
       ├─ agent_execute
       ├─ test_validate
       ├─ result_package
       ├─ candidate_revision
       └─ approval_wait
```

retry는 원 Run을 덮어쓰지 않고 새로운 attempt/run event로 남긴다.

## 2. Stage Event Contract

각 material stage는 append-only event를 남긴다.

최소 필드:

```text
event_id
job_id
run_id
stage
status
started_at
ended_at
actor
runner_version
agent/model/tool versions
input_refs
output_refs
branch/worktree
base_commit
candidate_commit
commands_or_action_summary
test_summary
failure_summary
resource_usage
approval_ref
parent_event_id
```

`status` 후보:

```text
queued
started
completed
failed
aborted
invalidated
waiting_for_approval
superseded
rolled_back
```

## 3. What Must Be Recorded at Each Stage

### intake

- source Job version
- source Lab
- authority references
- requested goal
- permissions
- expected outputs

### workspace_prepare

- repository
- base commit SHA
- branch
- worktree path or identifier
- dirty-state check
- conflict with concurrent workers

### authority_load

- 실제 읽은 authority document/version
- missing/stale authority
- cross-Lab dependency

### agent_execute

- agent/model/tool versions
- prompt/instruction version
- action/command summary
- retry count
- material tool failures
- network/database access class

Raw private model chain-of-thought는 기록 대상이 아니다.

### test_validate

- test command/version
- passed/failed/skipped
- validation artifacts
- known untested areas

### result_package

- report
- artifact manifest
- changed files
- data gaps
- unresolved risks
- next recommendation

### candidate_revision

- candidate commit SHA
- parent/base SHA
- diff fingerprint
- whether approvals for earlier SHA are now stale

### approval_wait / promotion

- approval action
- approved SHA
- approver
- approval timestamp
- push/merge/deploy result
- resulting remote/main/deployed SHA

## 4. Three Storage Layers

### A. Canonical Run Record

작업의 사실을 재구성하기 위한 작은 structured record.

### B. Artifacts

보고서, test output, generated files, metrics처럼 재검토할 material output.

### C. Telemetry

latency, cost, retry, agent/tool failure 등 플랫폼 진화를 위한 운영 자료.

```text
Run Record ≠ Artifact ≠ Telemetry
```

같은 사실을 여러 곳에서 별도 authority로 중복 유지하지 않는다.

## 5. Immutable History and Corrections

과거 event를 조용히 수정하지 않는다.

오류가 발견되면:

```text
original event
→ correction/superseding event
```

를 연결한다.

따라서 시간이 지나도 당시 runner가 무엇을 알고 무엇을 했는지를 복원할 수 있어야 한다.

## 6. Platform Evolution Feedback

Runtime history는 다음 slow loop의 입력이 된다.

```text
Runs
→ telemetry aggregation
→ recurring failure / friction detection
→ Platform Improvement Candidate
→ controlled runner change
→ versioned pilot
→ before/after evaluation
→ adopt / modify / reject / rollback
```

예시:

- worktree conflict 반복
- Codex retry 과다
- 특정 authority 문서 누락 반복
- test 시간이 급증
- CEO에게 불필요한 push approval 요청 과다
- structured report 누락
- failed run이 terminal record로 남지 않음
- Cross-Lab handoff job이 자주 실패

## 7. Metrics Are Diagnostic, Not Optimization Targets

다음을 직접 최적화 목표로 삼지 않는다.

- jobs/day 최대화
- retry 최소화
- CEO approval 비율 최대화
- merge 비율 최대화
- agent disagreement 최소화

이런 수치는 diagnostic signal이며, 원인을 조사하는 시작점이다.

## 8. Version Every Material Runtime Component

최소한 다음은 versionable해야 한다.

- runner
- job schema
- lab adapter
- prompt/instruction bundle
- permission policy
- result schema
- approval controller
- deployment adapter

그래야 운영 개선 전후를 비교할 수 있다.

## 9. Retention Principle

영구보존 기본값:

- Job/Run/Event canonical records
- approval/promotion/rollback history
- candidate and promoted commit SHAs
- material reports and evaluation artifacts
- failures that affected outcome/status

제한적/회전 보존 가능:

- verbose shell logs
- large intermediate artifacts
- redundant debug output

Secret, credential, private chain-of-thought는 canonical runtime record에 저장하지 않는다.

## 10. First End-to-End Pilot Success Criteria

DailyPrice readiness Job은 다음이 모두 남아야 성공으로 본다.

1. Job intake record
2. exact base SHA
3. isolated worktree/branch record
4. authority refs loaded
5. Codex invocation identity/version
6. DB access = read-only 기록
7. probe/test result artifacts
8. data-gap outputs
9. candidate commit SHA
10. `waiting_for_push_approval` terminal state
11. push가 아직 발생하지 않았음을 확인

이 기록이 다음 runner 버전의 Meta-Evaluation 입력으로 재사용될 수 있어야 한다.
