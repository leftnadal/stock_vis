# StockVis Work → Chat Handoff

## Executive Summary

Replay v0.2A는 승인된 summary-target lineage에서 hard-006 C-original/C-sanitized 각 1회를 완료했다. Historical candidate/critique를 포함한 original arm은 8,192-token budget을 모두 사용하고 final JSON 도중 종료됐고, 이를 제거한 sanitized arm은 valid final을 생성했다. Sanitized final은 기존의 unsupported strengthening을 제거하고 핵심 조건 대부분을 보존했지만, revenue-recognition 조건 E12를 누락하고 source-use provenance 오류를 새로 만들었다. 이 한 쌍은 historical payload 제거가 이 실행의 protocol completion에 유리했다는 방향성 evidence지만, semantic contamination과 9,484 prompt-token의 context burden을 분리하지 못한다. Permanent handoff architecture나 v0.2B 진행 여부는 Chat 판단이 필요하다.

## Current Task

- Lab: Research Lab
- Experiment: Research Evidence Handoff Replay v0.2A
- Case: hard-006, exposed calibration
- Batch: `41ea310a478340c19430a11bcf0bcdc1`
- Execution commit: `7d4ec68a8256bbfaa61c0924b25a0b69bc6566ae`
- Branch: `feature/research-replay-v02a-summary-target`
- Current state: completed working calibration; pending Chat interpretation

## Original Objective

동일 evidence와 frozen summary에서 historical candidate/critique context의 존재 여부가 protocol completion과 epistemic profile에 미치는 차이를 관찰한다. v0.1 hard-006/C 복구나 evidence-selection 실험으로 해석하지 않는다.

## Experiment Setup / Frozen Variables

- 동일 system prompt, frozen summary, evidence 17개와 순서
- 동일 Qwen/Qwen3.5-122B-A10B 및 requested generation config
- temperature 0.6, top_p 0.95, seed 20260909, reasoning enabled
- max_tokens 8192, retry 0, retrieval 없음
- 차이: historical candidate_output 2개 포함 대 제거

## Verified Results

| 항목 | C-original | C-sanitized |
|---|---:|---:|
| Prompt tokens | 14,387 | 4,903 |
| Completion tokens | 8,192 | 2,085 |
| Latency | 53.598s | 16.399s |
| Provider finish | stop | stop |
| Protocol completion | incomplete | complete |
| Final artifact | 없음 | 있음 |

Original은 final JSON 문자열 중 E10 설명을 시작한 지점에서 종료됐다. 따라서 partial text가 일부 condition을 언급했더라도 semantic result로 채점하지 않았다.

## Repair / Preserve / Introduce Profile

Sanitized final은 `Unsupported`를 유지하면서 근거 없는 “달성 가능성이 낮다”를 제거했다. E2, E6, E9, E10, E11, E14의 주요 내용을 보존했고 불확실한 프로젝트 금액·배정·mix에 유보했다.

반면 E12의 표준 장비 출하·검수와 맞춤형 모듈 설치·고객승인 간 revenue-recognition 차이를 누락했다. E13 mix를 적었지만 이 누락과 연결하지 않았다. E8/E13/E17 내용을 사용하면서 source ID를 기록하지 않았고, E5의 supplier allocation을 customer allocation과 묶는 저강도 provenance 오류 및 unsupported precision을 추가했다.

## Evidence Retrieval / Condition Preservation

두 arm 모두 full-context이고 retrieval은 없었다. Sanitized는 installation timing, energization timing, pre-energization shipment possibility, amount-mix unknown을 부분 보존했으나 revenue-recognition timing은 잃었다. 따라서 `Evidence Available → Recognized → Final Conclusion constrained`는 개선됐지만 완결되지 않았다.

## Execution / Cost / Integrity

- model invocations: 2, retry: 0
- 총 prompt/completion: 19,290 / 10,277 tokens
- 기록 latency 합: 69.997s
- actual cost: unknown
- requested/returned model identity: match
- hidden reasoning saved/recovered: false
- GitHub artifact SHA-256: 8 checked / 0 failed
- credential material launcher check: passed
- historical artifacts modified: false

## Unexpected Finding

실험 독립 변수는 historical context presence지만, 그 제거는 동시에 prompt를 9,484 tokens 줄였다. 따라서 observed difference가 historical instruction/reasoning의 semantic contamination 때문인지 context-size burden 때문인지, 또는 둘의 interaction인지 분리할 수 없다. 또한 original에 final artifact가 없어 양 arm의 semantic net effect를 대칭 비교할 수 없다.

## What This Supports

- 이 한 실행에서 historical payload 제거 후 protocol completion이 달성됐다.
- Sanitized full-evidence answer가 unsupported strengthening을 피하면서 useful scoped result를 낼 수 있었다.
- Protocol completion과 semantic correctness/provenance completeness는 별도 검증해야 한다.

## What This Does Not Support

- Sanitized handoff를 permanent 표준으로 채택
- C가 항상 B/A보다 우월하다는 결론
- 모델·Critic role·agent topology·memory/runtime adoption
- semantic contamination과 token burden 중 원인 확정
- held-out generalization 또는 production validation

## Options

### Option A — v0.2A를 directional calibration으로 종료하고 confound 분리 설계를 Chat에서 먼저 정의

장점: 현재 evidence보다 강한 결론을 피하고, 다음 실행이 semantic contamination과 context burden을 구분하도록 설계할 수 있다.

단점: 새 control/held-out case 설계가 필요하며 즉시 v0.2B로 가지 않는다.

### Option B — historical payload를 content+length의 운영상 하나의 package로 보고 v0.2B evidence-selection 논의로 이동

장점: 실제 handoff 비용 전체를 독립 변수로 보는 실용적 접근이다.

단점: 왜 실패했는지 분리하지 못한 채 architecture 선택에 영향을 줄 위험이 있다.

### Option C — 추가 replay 없이 v0.2A를 보존하고 broader held-out validation 단계까지 결정 보류

장점: exposed case 반복과 추가 비용을 피한다.

단점: contamination 가설과 context burden 가설 모두 미해결로 남는다.

## Work Recommendation

추천: Option A. v0.2B를 바로 실행하지 말고, length/content confound를 어떻게 다룰지 Chat에서 먼저 정한다.

추천 강도: Moderate

근거: protocol 차이는 크지만 n=1이며 original final이 없다. 이 상태로 permanent evidence-access 설계나 evidence-selection 단계에 연결하면 실행 안정성 효과를 epistemic-quality 효과로 과대해석할 수 있다.

추천이 틀릴 수 있는 조건: Research Lab이 원인 분리보다 실제 payload 전체의 운영 성능만을 우선 평가하기로 명시적으로 결정한다면 Option B가 더 효율적이다.

## Decision Needed From Chat / CEO

1. v0.2A를 content+length가 결합된 directional calibration evidence로 종료할 것인가?
2. v0.2B 전에 semantic contamination과 context burden을 구분하는 새 control/held-out 설계를 승인할 것인가?
3. 아니면 원인 분리를 보류하고 evidence-selection v0.2B 논의로 이동할 것인가?

## References

- Branch: `feature/research-replay-v02a-summary-target`
- Preparation base: `748c842611b4e8c55b4f3fcda7a69cac4284008f`
- Execution commit: `7d4ec68a8256bbfaa61c0924b25a0b69bc6566ae`
- Batch: `41ea310a478340c19430a11bcf0bcdc1`
- Path: `research_lab/work_reviews/2026-09-10-replay-v02a-summary-target/`

## Current Safety State

- review branch push: true
- main modified: false
- merge/deploy: false
- Approved/Effective promotion: false
- methodology/runtime/role/model/memory adoption: false
- selective rerun: false
- further model invocation after batch: false
