# StockVis Work → Chat Handoff

## Executive Summary

승인된 Jinja correction은 성공했지만 Replay v0.2A.1은 strict exact-count gate에서
다시 중단됐다. 기존 wheel 27개와 tokenizer asset 5개는 모두 검증됐고,
`Jinja2==3.1.6` 및 `MarkupSafe==3.0.2`도 정확히 고정·설치됐다. 그러나 historical
short/original request의 local count가 각각 `2`로 계산되어 provider 기록
`4,903`/`14,387`을 재현하지 못했다. 이는 작은 accounting 차이가 아니라 수천~수만 자
본문이 local chat-template rendering에 포함되지 않았을 가능성을 강하게 시사하지만,
현재 evidence만으로 원인을 확정하지 않는다. Gate가 정상 차단했으며 model invocation은
0회다.

## Current Task

- Lab: Research Lab
- Experiment: Research Evidence Handoff Replay v0.2A.1
- Correction lineage: `jinja2-pinned-001`
- Branch: `feature/research-replay-v02a1-context-volume-control`
- Preparation commit: `03833a6c3ab797903f3a6b9c0941fa5e6ccb87f9`
- Evidence commit: `067e29d834fb2b38191d93fd014d25fe5ca6a839`
- Current state: `blocked_tokenizer_accounting_mismatch`

## Original Objective

기존 blocked acquisition을 변경하지 않고 별도 격리 환경에서 누락된 official
chat-template dependency를 정확히 고정한 뒤, historical provider counts를 local
tokenizer가 재현할 때만 S-short/S-long-control 각 1회를 실행하는 것이었다.

## What Was Done

- correction 준비 checksum 통과
- 관련 회귀 테스트 9개 통과
- 원 acquisition checksum 재검증
- 기존 wheel 27개 identity/size/SHA-256 검증
- 기존 tokenizer asset 5개 identity/size/SHA-256 검증
- official PyPI acquisition command 1회
- `Jinja2==3.1.6`, `MarkupSafe==3.0.2` wheel 2개 획득 및 hash 기록
- 새 isolated environment에 기존 stack과 correction dependency offline 설치
- exact freeze 검증
- immutable Qwen tokenizer snapshot을 offline/local-only로 로드
- historical short/original request exact-count gate 실행
- mismatch 발견 즉시 모델 호출 없이 중단 및 evidence push

## Verified Facts

- Corrected environment: ready
- Transformers: `5.16.1`
- Tokenizers: `0.23.2`
- Jinja2: `3.1.6`
- MarkupSafe: `3.0.2`
- Tokenizer: fast `Qwen2Tokenizer`
- Tokenizer backend SHA-256: `ffb7a28b27dabcc333662fd3e0b0005d9e79a1c22e31453ab5a3017fbd5f25c0`
- Immutable tokenizer revision: `dc4d348443bc740c68e2d77492492c11606384d5`
- Historical short: local `2`, provider `4,903`
- Historical original: local `2`, provider `14,387`
- S-short input generated: false
- S-long-control generated: false
- Model-visible new arm generated: false
- Model invocations: 0
- Retry/alternative tokenizer search: false
- Historical artifacts modified: false

`PyTorch was not found` 경고는 tokenizer/config-only 실행에서 발생한 비차단 경고다.
실제 blocker는 `local_tokenizer_does_not_reproduce_provider_reference_counts`다.

## What Was Unexpected

Jinja2 누락을 고친 뒤에도 두 historical request가 모두 `2` tokens로 계산됐다. 저장된
visible request는 system/user string content를 포함하며, 파일 크기는 short 약 12.8 KB,
original 약 44.6 KB다. 따라서 `2`는 본문 전체에 대한 정상 token count로 해석할 수 없다.

현재 가장 유력한 working hypothesis는 raw provider message의 string content 표현과
official Qwen chat template가 기대하는 content 표현 사이의 rendering incompatibility다.
그러나 다음은 아직 unassessed다.

- provider가 내부적으로 string content를 다른 구조로 normalize하는지
- official Qwen template가 이 입력에서 실제로 어떤 text를 렌더링했는지
- provider가 동일한 template/revision을 사용하는지
- local count를 provider count와 일치시키는 authoritative preprocessing contract가 있는지

## Why This Requires Chat

현재 승인 계약은 exact historical count mismatch 시 alternative search 없이 중단하도록
정했다. String content를 content-block 형태로 바꾸거나 provider-native count를 사용하는
것은 evaluation input preprocessing을 새로 정의하는 일이다. 이는 단순 dependency fix가
아니므로 Work가 임의로 수행할 수 없다.

## Options

### Option A — v0.2A.1을 blocked/inconclusive로 종결

장점:

- strict one-attempt 및 exact-count contract를 가장 엄격하게 지킨다.
- 추가 비용과 실험 변수가 없다.

단점:

- context-volume effect는 계속 미해결이다.
- local count `2`의 기술적 의미가 설명되지 않는다.

### Option B — no-network/no-model rendering diagnostic 1회

현재 보존된 corrected environment에서 historical request를 `tokenize=False`로 렌더링해
system/user marker와 본문이 결과에 포함되는지 확인한다. Raw string 표현은 변경하지
않고 rendered text length/hash, marker presence, exception과 tokenizer identity만 기록한다.

장점:

- 추가 package, tokenizer asset, provider/model call 없이 `2`의 직접 원인을 좁힐 수 있다.
- 새로운 연구 결과를 만들지 않고 implementation boundary만 진단한다.

단점:

- 원인을 확인해도 대체 preprocessing을 자동 승인하지 않는다.
- provider 내부 normalization은 여전히 확인되지 않을 수 있다.

### Option C — provider-native counting/preprocessing contract 조사

DeepInfra 또는 Qwen의 authoritative contract에서 hosted endpoint가 message content를 어떻게
normalize하고 count하는지 확인한 뒤 새 gate를 설계한다.

장점:

- hosted 실행과 가장 가까운 기준을 확보할 가능성이 있다.

단점:

- 공식 count endpoint/세부 contract 제공 여부가 미확인이다.
- 새 provider interaction 또는 새로운 gate 의미가 필요할 수 있다.

## Work Recommendation

추천: Option B

추천 강도: Strong

근거: 두 입력이 내용과 크기가 크게 다른데도 동일하게 `2` tokens인 결과는 단순한
tokenizer 버전 오차가 아니다. 기존 corrected environment를 변경하지 않는 단일 rendering
diagnostic이면 비용과 실험 오염 없이 가장 가까운 원인을 확인할 수 있다.

추천이 부적절할 수 있는 조건: CEO가 v0.2A.1의 추가 정보 가치가 낮아졌다고 판단하거나,
provider가 이미 authoritative preprocessing/count contract를 제공한다면 각각 Option A 또는
Option C가 더 적절하다.

## Decision Needed From Chat / CEO

1. 현재 mismatch evidence를 보존하고 no-network/no-model raw rendering diagnostic 1회를
   진행할 것인가?
2. Diagnostic에서 raw string 본문 미포함이 확인되면, 다음 단계는 자동 변환하지 않고
   authoritative content-normalization 근거를 먼저 요구할 것인가?
3. Authoritative 근거를 확보하지 못하면 v0.2A.1을 blocked/inconclusive로 종결할 것인가?

## References

- Preparation: `03833a6c3ab797903f3a6b9c0941fa5e6ccb87f9`
- Evidence: `067e29d834fb2b38191d93fd014d25fe5ca6a839`
- Path: `research_lab/work_reviews/2026-09-10-replay-v02a1-context-volume-control/acquisition_runs/official-pinned-001/continuations/jinja2-pinned-001/`
- Gate result: `gate/preflight_result.json`
- Dependency provenance: `correction_dependency_manifest.json`
- Integrity: `GATE_SHA256SUMS`

## Current Safety State

- model/provider invocations: 0
- fixed arms executed: 0/2
- retry/selective rerun: false
- alternative tokenizer/dependency search: false
- historical artifacts modified: false
- review branch push: true
- merge/main/deploy/promotion: false
- approval required: any rendering diagnostic, input normalization, provider count interaction, or model execution
