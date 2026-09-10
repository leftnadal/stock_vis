# StockVis Work → Chat Handoff

## Executive Summary

Replay v0.2A.1 Context-Volume Control은 승인된 strict tokenizer gate에서 model invocation 전에 중단됐다. Mac 환경에서 exact requested model과 호환되는 local-only tokenizer stack을 불러오지 못했고 safe error type은 `ModuleNotFoundError`였다. 새 dependency나 tokenizer asset을 내려받지 않았으며 문자·byte 근사도 사용하지 않았다. 따라서 context-volume effect에 대한 실행 evidence는 아직 없고 v0.2B도 계속 보류한다. 다음 진행에는 tokenizer dependency/asset을 어떤 권한·출처·버전·checksum으로 확보할지 Chat 결정이 필요하다.

## Experiment Identity

- Lab: Research Lab
- Experiment: Research Evidence Handoff Replay v0.2A.1
- Purpose: Context-Volume Control
- Case: hard-006 exposed calibration
- Branch: `feature/research-replay-v02a1-context-volume-control`
- Preparation commit: `84ae6cbd6bb59de823038f8f90f73666f6370d3d`
- Preflight evidence commit: `6abe796efe2a72f1558cac2574e48ece77c280da`
- State: blocked_before_model_invocation

## Token-Matching Method

계획된 gate는 exact model ID의 fast tokenizer를 `local_files_only=True`, `trust_remote_code=False`로 로드한 뒤 historical v0.2A request 두 개를 chat template에 적용하는 방식이다. Local tokenizer가 provider-reported 4,903과 14,387을 모두 정확히 재현해야만 opaque control 생성으로 진행한다. 이후 S-long-control도 local 14,387 tokens와 정확히 일치해야 한다.

## Tokenizer Identity

- Requested model: `Qwen/Qwen3.5-122B-A10B`
- Compatible local tokenizer identity/version: unavailable
- Safe error type: `ModuleNotFoundError`
- Network acquisition attempted: false
- Provider tokenizer/count call attempted: false

정확히 어느 모듈 이름이 누락됐는지는 safe artifact에 저장되지 않아 unassessed다.

## Token Counts

- Historical target provider prompt tokens: 14,387
- Historical sanitized provider prompt tokens: 4,903
- S-short local input tokens: unassessed
- S-long-control local input tokens: unassessed
- Provider-reported new prompt tokens: 없음

## Exact Input Difference / Control Identity

두 신규 input은 생성되지 않았다. 따라서 planned difference는 정의돼 있지만 실제 sealed input difference, control item count, control SHA와 full input SHA는 존재하지 않는다.

## Preflight Integrity

- 준비 artifact checksum: passed
- regression tests before preflight: 4 passed
- historical candidate/critique included in generated arms: not applicable; arms not generated
- protected expectation leakage: model-visible input 미생성
- character/byte approximation used: false
- historical artifacts modified: false
- model invocations: 0

## Execution Results / Protocol Completion

실제 S-short/S-long-control 실행은 없었다. Run ID, batch ID, completion tokens, latency, provider finish state와 protocol completion은 모두 not assessed다.

## Semantic Profile / E12/E13 / Provenance

Valid final output이 없으므로 semantic assessment를 수행하지 않았다. E12/E13 preservation, source-use provenance, unsupported strengthening, introduced error와 conclusion calibration은 모두 unassessed다.

## Unexpected Finding

Blocked evidence의 자동 저장 과정에서 publisher의 tuple prefix 결합 오류가 발생했다. Preflight 결과 자체와 무관한 implementation defect다. Staged file이 정확히 `preflight_result.json` 하나이고 invocation count가 0임을 확인한 candidate-commit-only recovery로 저장했다. Publisher는 tuple prefix를 개별 확장하도록 수정하고 in-scope/out-of-scope 회귀 테스트를 추가했다.

## Interpretation Matrix Position

Case 1~4 중 어느 곳에도 해당하지 않는다. 두 arm이 실행되지 않았으므로 context-volume directional evidence는 생성되지 않았다.

## What This Supports

- 현재 Mac runtime에는 승인 gate를 통과시킬 준비가 된 compatible local tokenizer stack이 없었다.
- Strict gate가 불충분한 token matching을 model call 전에 차단했다.
- Execution failure와 research result absence, publisher defect는 구분돼야 한다.

## What This Does Not Support

- Context volume이 protocol failure의 원인이라는 결론
- Historical semantic contamination이 원인이라는 결론
- Opaque padding architecture의 적절성
- Sanitized/Full Context architecture 채택
- v0.2B 실행 또는 held-out validation
- 특정 tokenizer package/version 설치 승인

## Options

### Option A — 격리·고정된 tokenizer dependency/asset acquisition 승인

공식 또는 검증 가능한 출처에서 exact model-compatible tokenizer와 최소 runtime dependency를 격리 환경에 version-pin하고 파일 checksum을 보존한다. 기존 exact historical count gate는 완화하지 않는다.

장점:
- 승인된 v0.2A.1 질문을 그대로 유지할 가능성이 가장 높다.
- Provider count와 불일치하면 model call 전에 다시 안전하게 차단된다.

단점:
- 새로운 network dependency/asset acquisition 권한이 필요하다.
- Official tokenizer가 provider chat template/count를 정확히 재현한다는 보장은 없다.
- Dependency provenance와 장기 유지 범위를 정해야 한다.

### Option B — Provider의 공식 token-count 기능을 별도 preflight로 사용

Provider가 비생성 token-count endpoint나 공식 계산 도구를 제공하는지 확인한 뒤 사용한다.

장점:
- 실제 hosted inference token accounting과 가까울 수 있다.

단점:
- 지원 여부가 미확인이다.
- 새 provider interaction과 contract가 필요하다.
- 호출 자체의 비용·기록·privacy 경계를 정해야 한다.

### Option C — v0.2A.1을 blocked calibration으로 종료

추가 dependency를 도입하지 않고 context-volume question을 미해결로 보존한다.

장점:
- 새 의존성과 비용이 없다.
- 현재 safety boundary를 그대로 유지한다.

단점:
- v0.2A의 content/length confound가 해소되지 않는다.
- v0.2B 또는 architecture 논의 전 evidence gap이 남는다.

## Work Recommendation

추천: Option A를 제한적으로 승인하되, isolated environment, exact package/asset version, source URL, file checksum, no model call before exact 4,903/14,387 reproduction을 필수 조건으로 둔다.

추천 강도: Moderate

추천이 틀릴 수 있는 조건: exact model tokenizer가 공식적으로 배포되지 않았거나 provider가 다른 비공개 template/token accounting을 사용한다면 acquisition을 반복하지 말고 Option C로 종료해야 한다.

## Decision Needed From Chat / CEO

1. Exact compatible tokenizer를 위한 격리된 dependency/asset acquisition을 승인할 것인가?
2. 승인한다면 허용 출처, version pin, checksum/provenance 및 최대 설치 범위는 무엇인가?
3. Exact historical count를 재현하지 못하면 추가 우회 없이 v0.2A.1을 종료할 것인가?

## Current Safety State

- model/provider invocations: 0
- tokenizer/dependency download: false
- generated model-visible inputs: false
- execution batch: 없음
- historical artifacts modified: false
- review feature branch push: true
- merge/main/deploy/promotion: false
- v0.2B/held-out progression: false
- methodology/runtime/role/memory adoption: false
