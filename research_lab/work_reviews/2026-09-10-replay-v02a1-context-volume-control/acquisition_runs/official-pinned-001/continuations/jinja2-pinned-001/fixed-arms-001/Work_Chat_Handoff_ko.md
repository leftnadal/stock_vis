# StockVis Work → Chat Handoff

## Executive Summary

Replay v0.2A.1의 counting repair 근거를 보존한 뒤 hard-006 S-short와 S-long-control을 각 1회 실행했다. 두 arm 모두 local/provider prompt token이 정확히 일치했고, 요청 모델과 valid final JSON이 확인되어 protocol complete였다. 두 답변은 E6 기간 오류를 고치고 주요 불확실성을 대체로 보존했지만, E12의 매출 인식 경계와 E13의 미확정 금액 mix를 결론에 충분히 반영하지 않은 채 Unsupported를 “달성 가능성이 낮다”로 강화했다. 실행 무결성은 확인됐으나 context volume의 순 epistemic effect와 영구 handoff 구조의 우열은 확인되지 않았다.

## Current Task

- Lab: Research Lab
- Experiment: Research Evidence Handoff Replay v0.2A.1
- Case: hard-006, exposed calibration
- Batch: `33d5bf9a24bd4d70a0bd1ca50721cfee`
- Branch: `feature/research-replay-v02a1-context-volume-control`
- Preflight commit: `52973d80d47737fdf6a55bae7915b14e2603c7ab`
- Execution commit: `d4050de5e050e1c5f8312785da8b02f836281d3f`
- State: execution complete; semantic review recorded; no promotion

## Verified Facts

| Item | S-short | S-long-control |
|---|---:|---:|
| Local/provider prompt tokens | 4,940 / 4,940 | 14,387 / 14,387 |
| Protocol | complete | complete |
| Model identity | match | match |
| Latency | 98.516 s | 72.860 s |
| Completion tokens | 6,196 | 4,720 |

- Model invocations: 2/2 approved
- Retry/selective rerun: 0 / false
- Same summary, 17 evidence items, prompt, and generation config
- Only model-visible difference: `context_volume_control`
- Historical candidate/critique absent in both arms
- Opaque control not used as evidence
- Credential scan passed; historical artifacts unchanged
- Actual cost: unknown

## Semantic Findings

Both arms repaired the frozen summary’s E6 period error and preserved E9/E10 timing, E11/E13 uncertainty, and E14 downside. Both nevertheless changed an evidence-support judgment into an uncalibrated probability judgment: “Unsupported” became “low likelihood.”

E12 distinguishes standard equipment recognition after shipment/inspection from customized-module recognition after installation/customer approval. E13 states that LG-4/4B contain both but their value mix is unknown. The answers mentioned part of this uncertainty but did not let it sufficiently constrain the final conclusion.

Profile for both arms:

- Existing Error Repaired: supported
- Correct Content Preserved: supported
- Unsupported Strengthening: present
- Material Condition Preserved: partial
- Appropriate Abstention: partial
- Final Conclusion Scope Calibration: unsupported
- Execution Failure/Truncation: absent

Evidence attribution also remains weak. S-short declares 11 used sources; S-long-control declares all 17, beyond the sources demonstrably connected to each final argument.

## What This Supports

- Counting repair and exact local/provider token accounting
- Fixed two-arm execution and protocol completion
- A shared semantic failure boundary in this exposed pair
- Separation of execution integrity from semantic quality

## What This Does Not Support

- A causal or general context-volume effect
- A permanent evidence-handoff architecture
- A permanent Critic/Evaluator topology
- Model, memory, runtime, or methodology adoption
- A monotonic latency relationship

## Options

### Option A — Close as inconclusive calibration

Proceed to the already approved record-reconstruction pilot preparation.

### Option B — Design a separate held-out validation

Requires new case, evaluator-independence, repetition, and cost decisions.

### Option C — Open evidence-attribution contract research

Separately study available evidence versus actually used evidence; this may become a shared output-contract issue.

## Work Recommendation

Recommendation: Option A.

Recommendation strength: Strong.

Reason: execution integrity is established, both arms share the same material semantic failure, and one stochastic run per arm cannot justify generalization. Further execution would exceed the approved minimum comparison.

Recommendation failure conditions:

- Chat decides that context-volume effect must be estimated now and approves held-out cases, repetition, and cost.
- Exact source-use attribution becomes a mandatory gate for the next stage.

## Decision Needed From Chat / CEO

1. Close Replay v0.2A.1 as an inconclusive calibration?
2. Register held-out context-volume validation as a separate future candidate or hold it?
3. Register evidence availability versus actual use as a separate contract-research candidate?

## References

- Semantic review: `fixed-arms-001/semantic_review.json`
- Execution record: `fixed-arms-001/execution_record.json`
- Manifest: `fixed-arms-001/executions/33d5bf9a24bd4d70a0bd1ca50721cfee/manifest.json`

## Current Safety State

- Additional model/evaluator calls: 0
- Main modified: false
- Merge/deploy: false
- Methodology/runtime/role/memory adoption: false
- Further execution or promotion requires separate approval
