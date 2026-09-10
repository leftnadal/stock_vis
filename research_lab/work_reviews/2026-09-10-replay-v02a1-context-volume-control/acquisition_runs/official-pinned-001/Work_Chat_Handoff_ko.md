# StockVis Work → Chat Handoff

## Executive Summary

Replay v0.2A.1의 승인된 official pinned acquisition 1회를 완료했다. 공식 PyPI에서
`transformers==5.16.1`, `tokenizers==0.23.2`와 resolver-selected dependencies를
격리 환경에 확보·offline 설치했고, 공식 Qwen repository의 immutable revision에서
tokenizer/config 5개 파일만 확보했다. Tokenizer는 fast `Qwen2Tokenizer`로 local-only
로드됐지만 historical request의 첫 `apply_chat_template` count에서 `ImportError`가
발생했다. 따라서 4,903/14,387 exact reproduction은 평가되지 않았고, 승인된 stop
condition에 따라 model invocation 0회로 `blocked_tokenizer_integrity_failure` 종료했다.

## Current Task

- Experiment: Research Evidence Handoff Replay v0.2A.1
- Purpose: Context-Volume Control
- Case: hard-006 exposed calibration
- Acquisition: `official-pinned-001` (허용된 1회 사용 완료)
- Branch: `feature/research-replay-v02a1-context-volume-control`
- Evidence commit: `5f59646e8ad7371f7f948e1bf06f75357a24535c`
- Current state: `blocked_tokenizer_integrity_failure`

## Original Objective

공식 exact-model tokenizer stack으로 historical provider prompt counts 4,903과 14,387을
모두 정확히 재현하고, 성공한 경우에만 S-short/S-long-control을 각각 1회 실행하는
것이었다.

## What Was Done

- preparation checksum 7/7 및 회귀 테스트 13/13 통과
- repository 밖 experiment-local Python 3.12.2 venv 생성
- official PyPI exact pins와 transitive wheels 27개 download 및 offline install
- package filename/version/index/SHA-256/freeze/platform/environment path 기록
- official `Qwen/Qwen3.5-122B-A10B` repository identity 확인
- immutable revision `dc4d348443bc740c68e2d77492492c11606384d5` pin
- tokenizer/config 5개만 획득하고 각 SHA-256 및 canonical locator 기록
- model weight 미다운로드
- 이후 `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` 적용
- `local_files_only=True`, `trust_remote_code=False`, `use_fast=True`로 tokenizer 로드
- terminal evidence 및 checksum을 review branch에 push

## Verified Facts

- Direct packages: `transformers==5.16.1`, `tokenizers==0.23.2`
- Package source/index: official PyPI, `https://pypi.org/simple`
- Installed tokenizer class: `Qwen2Tokenizer`
- Fast tokenizer: true
- `apply_chat_template` callable: true
- Vocab size: 248,044
- Backend tokenizer SHA-256: `ffb7a28b27dabcc333662fd3e0b0005d9e79a1c22e31453ab5a3017fbd5f25c0`
- Tokenizer revision: `dc4d348443bc740c68e2d77492492c11606384d5`
- Acquired files: `chat_template.jinja`, `config.json`, `generation_config.json`,
  `tokenizer.json`, `tokenizer_config.json`
- Model weights downloaded: false
- Count-stage blocker: `compatible_chat_template_count_failed`
- Safe error type: `ImportError`
- Historical 4,903 reproduction: unassessed; count not produced
- Historical 14,387 reproduction: unassessed; count not produced
- New model invocations: 0
- Alternative tokenizer/version/template search: false

## What Was Unexpected

Tokenizer identity, fast backend, chat-template API와 asset provenance는 확인됐지만,
실제 `apply_chat_template(..., tokenize=True)` 호출이 `ImportError`로 실패했다. Persisted
evidence는 exception type만 보존하므로 누락된 module/package의 정확한 이름은 현재
artifact만으로 확인할 수 없다. PyTorch 부재 경고는 tokenizer-only 사용 안내이며,
기록된 exception과 동일 원인이라고 단정할 근거는 없다.

## New Problem / Question

현재 pinned direct stack만으로 chat-template token accounting runtime이 완결되지 않은
것인지, 혹은 다른 environment-specific import 문제가 있었는지 구분할 진단 증거가
부족하다. 이를 밝히려면 기존 격리 환경에 대한 no-network diagnostic 또는 새 optional
dependency acquisition 권한이 필요하다.

## Why This Requires Chat

승인서는 tokenizer load/count failure를 즉시 stop/handoff 조건으로 정했고, 한 번의
official pinned acquisition 후 다른 조합·dependency 탐색을 금지했다. 따라서 Work가
추가 package를 설치하거나 동일 gate를 재실행하면 one-attempt experiment contract를
변경하게 된다.

## Options

### Option A — 현재 lineage를 blocked/inconclusive로 종결

장점:

- 승인된 one-attempt 및 stop contract를 그대로 지킨다.
- outcome fitting이나 dependency 탐색을 피한다.

단점:

- context-volume 가설은 계속 미평가 상태다.
- ImportError의 구체 원인은 남는다.

### Option B — 기존 격리 환경의 no-network diagnostic만 별도 승인

정확한 traceback/module identity만 수집하고 package 설치·count 재실행·model 호출은
하지 않는다.

장점:

- current failure 원인을 좁히면서 기존 acquisition을 변경하지 않는다.
- 다음 설계 판단에 필요한 최소 증거를 만든다.

단점:

- diagnostic도 현재 승인 범위 밖의 새 lineage다.
- 원인을 알아도 v0.2A.1을 재개할 권한은 별도로 필요하다.

### Option C — 진단 후 새 pinned optional-dependency acquisition lineage 승인

장점:

- exact-count gate를 다시 평가할 가능성이 생긴다.

단점:

- 현재 one-attempt 결과와 분리된 새 실험이어야 한다.
- optional dependency 선택이 historical outcome fitting으로 변하지 않도록 사전 pin이 필요하다.

## Work Recommendation

추천: Option B를 먼저 수행하고, 결과를 본 뒤 Option A 또는 C를 결정한다.

추천 강도: Moderate

근거: 현재 failure는 count mismatch가 아니라 import-stage failure이며, exception type만으로
원인을 단정할 수 없다. 기존 environment를 변경하지 않는 no-network diagnostic은 가장
작은 추가 증거다. 다만 CEO가 one-attempt 종결성을 더 중시하면 Option A가 적절하다.

추천이 부적절할 수 있는 조건: historical tokenizer accounting의 추가 검증 가치가 낮거나,
격리 환경을 더 보존할 필요가 없다고 판단하는 경우.

## Consistency / Impact

- Founding / Philosophy: 현실의 실패 증거를 보존했다는 점에서 정합
- Methodology: 변경 없음
- Evaluation: exact-count gate 미도달; context-volume effect 미평가
- Model / Runtime: experiment-local stack일 뿐 공통 runtime 채택 아님
- Other Labs: Not Material
- Automation: terminal blocker artifact publication 정상 동작
- Long-term scalability: optional dependency completeness를 preflight에서 분리 검증할 필요가
  있을 수 있으나 공통 contract 변경은 결정하지 않음

## Decision Needed From Chat / CEO

1. Replay v0.2A.1을 현재 blocked/inconclusive로 최종 종결할 것인가?
2. 기존 격리 환경을 변경하지 않는 no-network ImportError diagnostic을 별도 승인할 것인가?
3. 진단 결과가 명백한 missing official dependency라면 새 pinned acquisition lineage를
   검토할 것인가?

## References

- Branch: `feature/research-replay-v02a1-context-volume-control`
- Preparation: `d5bd2bce13e45278567db323e77ea0ffc90d0dc3`
- Evidence: `5f59646e8ad7371f7f948e1bf06f75357a24535c`
- Path: `research_lab/work_reviews/2026-09-10-replay-v02a1-context-volume-control/acquisition_runs/official-pinned-001/`
- Result: `acquisition_result.json`
- Gate: `gate/preflight_result.json`
- Dependency provenance: `dependency_manifest.json`
- Tokenizer provenance: `tokenizer_asset_manifest.json`
- Integrity: `SHA256SUMS`

## Current Safety State

- model_invocations: 0
- retries: 0
- selective_rerun: false
- alternative_search: false
- historical_artifacts_modified: false
- tokenizer/model binaries committed: false
- review_branch_push: true
- main_modified: false
- merge_performed: false
- deploy_performed: false
- methodology/runtime/role/memory adoption: false
- approval_required: any diagnostic, new dependency acquisition, gate rerun, or promotion
