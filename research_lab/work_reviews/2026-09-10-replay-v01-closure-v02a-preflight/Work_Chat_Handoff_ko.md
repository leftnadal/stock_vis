# StockVis Work → Chat Handoff

## Executive Summary

Replay v0.1은 승인대로 semantic output 5건과 execution failure 1건으로 종료 기록했다. hard-006/C는 재실행하지 않았다. Runtime completion validator는 transport, provider finish state, protocol final artifact, semantic review state를 분리하도록 구현하고 회귀 검증했다. Replay v0.2A preflight에서 historical primary candidate artifact가 최종 답변 없이 26,732자의 reasoning-like 텍스트로 끝나는 사실을 확인했다. 이 전체를 제거하면 candidate answer identity 보존이 깨지고, 일부를 추출하면 새로운 target을 만드는 판단이 필요하므로 model invocation 전에 중단했다.

## Current Task

- Lab: Research Lab
- Experiment: Replay v0.1 Closure / Runtime Hardening / Replay v0.2A Preflight
- Base candidate: `52fe0279a25aa78da8e3b12a9c8c99a3d52ab94d`
- v0.1 batch: `0b5220e04007446695d092f763b72020`
- v0.1 state: closed calibration, 5 semantic outputs + 1 execution failure
- v0.2A state: blocked_before_model_invocation

## What Was Done

- v0.1 closure record 작성
- hard-006/C historical failure 유지 및 선택적 재실행 없음
- completion validator와 4개 회귀 테스트 작성
- hard-006 full-context document inventory 검사
- evidence document 17개의 identity/body 보존 계획과 hash 기록
- historical primary candidate fragment의 final-answer 분리 가능성 검사
- v0.2A input 생성과 provider 호출을 차단

## Verified Facts

- 원 primary candidate fragment는 `Thinking Process:`로 시작한다.
- 길이는 26,732 characters다.
- `Final Answer` 또는 `최종 답변` 표지가 없다.
- fragment는 반복적인 evidence-ID 선택 검토 중 끝난다.
- 원 critic fragment에는 수정된 연구 결과가 있으나 critic issue, Frontier 필요성 등 다른 historical content도 함께 있다.
- 모든 evidence body 17개는 그대로 유지할 수 있다.
- candidate answer identity는 현재 artifact만으로 reasoning residue와 분리하여 보존할 수 없다.
- v0.2A model invocation은 0회다.

## Runtime Hardening Result

새 working completion contract는 다음을 분리한다.

- transport_status
- provider_finish_state
- protocol_completion
- protocol_failure_reason
- semantic_review_state
- visible_content_state
- reasoning_like_visible_content
- output_budget_fully_used

`finish_reason=stop`이더라도 final action/JSON이 없으면 protocol incomplete다. reasoning-like detection은 user-visible content concern만 기록하며 hidden reasoning을 저장하거나 복원하지 않는다. 이는 experiment-local candidate이고 공통 runtime contract 채택이 아니다.

## New Finding / Problem

승인된 C-sanitized는 evidence body, candidate answer identity, model/config/prompt를 유지하면서 historical instruction/reasoning residue만 제거해야 한다. 그러나 현재 primary candidate artifact에는 독립된 final answer가 없다. 따라서 sanitized input을 만들려면 evaluation target의 정의를 바꿔야 한다.

## Why This Requires Chat

어떤 텍스트를 current evaluation target으로 삼을지는 단순 serialization 수정이 아니다. Frozen summary를 target으로 삼을지, critic 결과의 일부를 derived target으로 만들지, 별도 historical final answer를 확보할지에 따라 실험 질문과 비교 가능성이 달라진다. Work가 임의로 선택하면 historical-context sanitization 외의 변수가 함께 바뀐다.

## Options

### Option A — Frozen summary를 evaluation target으로 사용

장점: 이미 A/B/C에 공통으로 사용된 frozen identity가 있고 새 문구를 만들지 않는다. 모든 evidence body를 유지하면서 candidate_output documents 전체를 historical residue로 제거할 수 있다.

단점: 원 C가 평가한 candidate/critique context와 대상이 달라진다. v0.2A는 original C의 직접 복제가 아니라 summary-target full-evidence experiment가 된다.

### Option B — Critic의 `수정된 연구 결과`와 `Unknown/Unassessed` 부분을 derived target으로 사용

장점: 분리 가능한 결론 텍스트가 존재하고 hard-006의 material issue를 포함한다.

단점: Work가 historical artifact 일부를 선택하여 새 target을 만든다. Selection bias와 새로운 artifact lineage가 생긴다.

### Option C — 별도로 attested된 historical final candidate answer 확보

장점: candidate answer identity 보존 요구에 가장 충실하다.

단점: 해당 artifact가 실제로 존재하는지 현재 확인되지 않았다. 확보되지 않으면 실험이 계속 중단된다.

## Work Recommendation

추천: Option A

추천 강도: Moderate

근거: frozen summary는 이미 동일 case의 모든 v0.1 조건에 공통으로 사용됐고 hash가 고정돼 있다. Evidence를 선택하거나 answer-key를 추가하지 않으며, historical candidate/critique document 전체 제거라는 명확하고 재현 가능한 sanitization이 가능하다. 다만 evaluation target이 달라지므로 v0.1 C의 repaired rerun으로 부르지 말고 별도 `summary-target C-original/C-sanitized` calibration lineage로 정의해야 한다.

추천이 틀릴 수 있는 조건: 원 primary run의 최종 candidate answer가 별도 artifact로 존재하고 동일성을 검증할 수 있는 경우 Option C가 우선이다.

## Decision Needed From Chat / CEO

1. v0.2A의 evaluation target을 frozen summary로 고정하고 historical candidate/critique documents 전체를 removable context로 정의할 것인가?
2. 그렇다면 original C failure는 historical comparator로만 유지하고, 새 실험에서는 summary-target C-original과 C-sanitized를 같은 새 lineage에서 함께 실행할 것인가?

## Current Safety State

- provider/model calls for v0.2A: 0
- hard-006/C selective rerun: false
- historical files modified: false
- sanitized input created: false
- push: review feature branch only
- merge/deploy/main modification: false
- methodology/role/memory/runtime adoption: false

