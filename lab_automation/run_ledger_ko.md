# StockVis Lab Automation — Run Ledger & Evolution Feedback v0.2

**Status:** Working Candidate  
**Date:** 2026-09-07

## 0. 한눈에 보는 요약

Lab Automation Platform은 작업을 단순 실행하고 끝내는 도구가 아니다. **각 단계의 입력, 상태 변화, 출력, 실패, 승인, 버전과 비용을 기록하고 그 기록을 플랫폼 자체 개선의 근거로 사용하는 learning system**이어야 한다.

기본 원칙:

> If a material stage happened, it should leave a reconstructable operational record.

단, 모든 stdout과 임시 thought를 영구 보존하는 것은 아니다. 미래에 재구성·평가·감사·개선에 필요한 material record만 canonical하게 남긴다.

## 1. Canonical Runtime Objects

각 Job은 하나 이상의 Run을 가질 수 있다. Run은 logical work unit이고, 실제 model/tool/backend 호출은 Invocation으로 분리한다.

```text
Job
  └─ Run #1
       ├─ intake
       ├─ authority_load
       ├─ Invocation #1
       │    └─ physical agent/backend attempt
       ├─ Invocation #2 (retry/replication when needed)
       ├─ test_validate
       ├─ result_package
       └─ candidate_revision
```

```text
Run ≠ Invocation
```

retry, replication, accidental duplicate는 원 실행을 덮어쓰지 않고 별도 Invocation identity로 남긴다.

## 2. Stage Event Contract

각 material stage는 append-only event를 남긴다.

최소 필드:

```text
event_id
schema_version
job_id
run_id
stage
status
actor
runner_version
base_sha
candidate_sha when final and external
artifact_refs
invocation_ids when applicable
input_snapshot_ref when applicable
output_ref when applicable
test_summary
failure_summary
supersedes_event_id
```

과거 event를 조용히 수정하지 않는다. 오류가 발견되면 correction/superseding event를 append한다.

## 3. Invocation Contract

Invocation은 physical execution attempt를 표현한다.

최소 의미:

```text
invocation_id
run_id
actor/backend
execution_intent
parent_invocation_id
input_snapshot_ref
output_ref
requested_identity
returned_identity when known
identity_assurance
started_at / ended_at
status / returncode / finish_reason
```

`execution_intent`는 최소한 `primary`, `retry`, `replication`, `accidental_duplicate`, `unknown`을 구분할 수 있어야 한다.

동일 request/hash가 반복되었다는 사실만으로 duplicate failure라고 판단하지 않는다. 의도된 replication일 수 있기 때문이다.

## 4. Artifact Identity and Storage

Artifact의 canonical identity는 현재 filesystem path가 아니다.

```text
artifact logical identity
  = content hash + logical URI

physical location
  = replica metadata
```

v0.2 local implementation은 다음 형태를 사용한다.

```text
artifact://sha256/<digest>
```

현재 기본 physical store:

```text
~/.stockvis-lab-automation/
├── ledger/
└── artifacts/
    └── sha256/...
```

`--state-root`를 외장 NVMe/NAS mount 등으로 바꾸더라도 artifact logical identity는 바뀌지 않는다. 내부 SSD 2TB는 architecture constraint가 아니라 deployment choice다.

Retention class:

```text
irreplaceable
reconstructable
redownloadable
ephemeral
```

저장공간 부족을 이유로 irreplaceable raw input/output/evaluation artifact를 먼저 삭제하지 않는다.

## 5. Input Snapshot

agent/model invocation 전에 실제 입력을 immutable artifact로 만든다.

최소한 다음을 재구성할 수 있어야 한다.

- exact prompt reference
- source Job state
- base SHA
- authority snapshot references
- runner version

실제 agent가 받은 입력을 나중에 현재 코드나 현재 Job에서 추정해서는 안 된다.

## 6. Output Provenance

파일 존재와 agent 생성은 동일하지 않다.

```text
agent_generated
runner_placeholder
runner_generated
derived
```

같은 origin 구분을 보존한다.

`agent_report.md`와 `result.json`처럼 required output이 runner placeholder라면 execution process가 정상 종료했더라도 output contract는 실패로 기록한다.

```text
execution success ≠ output contract success ≠ epistemic quality
```

## 7. Candidate SHA Boundary

최종 candidate commit SHA는 commit 내부 manifest의 canonical field로 저장하지 않는다.

manifest에 SHA를 쓰면 manifest content가 commit hash에 영향을 주어 자기참조가 발생하기 때문이다.

따라서:

- candidate manifest: base SHA, run identity, artifact refs, changed paths, promotion state
- external append-only Run Ledger: final candidate SHA

로 분리한다.

## 8. Three Storage Layers

### A. Canonical Run Record

작업의 사실을 재구성하기 위한 작은 structured append-only record.

### B. Artifacts

prompt/input snapshot/raw output/report/test/evaluation처럼 재검토할 material output.

### C. Telemetry

latency, cost, retry, agent/tool failure 등 플랫폼 진화를 위한 운영 자료.

```text
Run Record ≠ Artifact ≠ Telemetry
```

같은 사실을 여러 곳에서 별도 authority로 중복 유지하지 않는다.

## 9. Platform Evolution Feedback

```text
Runs / Invocations
→ telemetry aggregation
→ recurring failure / friction detection
→ Platform Improvement Candidate
→ controlled runner change
→ versioned pilot
→ before/after evaluation
→ adopt / modify / reject / rollback
```

Metrics는 diagnostic signal이지 직접 optimization target이 아니다.

## 10. Retention and Privacy

영구보존 기본값:

- Job/Run/Event canonical records
- material Invocation records
- exact material input snapshots
- approval/promotion/rollback history
- candidate and promoted commit SHAs
- material reports and evaluation artifacts
- failures that affected outcome/status

제한적/회전 보존 가능:

- verbose redundant debug output
- reconstructable derived views
- redownloadable model cache
- ephemeral runtime buffer

Secret, credential, private model chain-of-thought는 canonical runtime record에 저장하지 않는다.

## 11. Research Runtime Profile Boundary

Research Lab의 Critic independence, exposure, blinding, holdout, evaluation linkage 같은 의미는 Shared Run Ledger에 넣지 않는다.

```text
Shared Run Ledger
→ execution facts

Research Experiment Profile
→ research experiment semantics
```

`research_runtime/` profile은 기존 Research/Evaluation Methodology와 ORS를 재정의하지 않는다.
