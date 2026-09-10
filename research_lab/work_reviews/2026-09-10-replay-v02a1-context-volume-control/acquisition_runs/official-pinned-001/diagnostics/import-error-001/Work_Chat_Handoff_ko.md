# StockVis Work → Chat Handoff

## Executive Summary

승인된 no-network diagnostic에서 Replay v0.2A.1 count-stage `ImportError`의 원인을
`jinja2` 미설치로 확정했다. 기존 tokenizer asset은 checksum을 통과했고 fast
`Qwen2Tokenizer`로 정상 로드됐다. 공식 Transformers v5.16.1 소스에서도 chat-template
기능은 기본 dependency가 아닌 `chat_template` extra의 `jinja2>=3.1.0`을 요구하며,
미설치 시 관측된 것과 동일한 ImportError를 발생시킨다. 진단은 network/package
installation/historical count rerun/model invocation 모두 0으로 완료됐다. 추가 설치와
exact-count gate 재개는 새로운 Chat 승인 없이는 수행하지 않는다.

## Current Task

- Experiment: Research Evidence Handoff Replay v0.2A.1
- Diagnostic: `import-error-001`
- Branch: `feature/research-replay-v02a1-context-volume-control`
- Diagnostic evidence: `1090f6ebbf87d445f7986838abcb76e2de3b029a`
- Current state: root cause diagnosed; original gate remains blocked

## Original Objective

기존 official-pinned-001 환경을 변경하지 않고 count-stage ImportError의 정확한
traceback과 누락 module identity만 확인하는 것이었다.

## What Was Done

- diagnostic preparation checksum 4/4 통과
- diagnostic regression tests 4/4 통과
- 기존 acquisition evidence checksum 4/4 재검증
- existing tokenizer asset 5개의 SHA-256 재검증
- offline/local-only tokenizer 로드
- historical request가 아닌 최소 chat-template 호출 1회
- traceback, exception message, installed package list 기록
- diagnostic evidence checksum 및 review branch 저장

## Verified Facts

- Exception type: `ImportError`
- Exception message: `apply_chat_template requires jinja2 to be installed.`
- Candidate missing module: `jinja2`
- Candidate module importable: false
- Asset integrity: passed
- Tokenizer: fast `Qwen2Tokenizer`
- Transformers: `5.16.1`
- Tokenizers: `0.23.2`
- Network attempts: 0
- Package installations: 0
- Historical count gate reruns: 0
- Provider/model invocations: 0
- Historical artifacts modified: false

## Official Source Confirmation

Transformers v5.16.1의 official source는 다음을 명시한다.

- `jinja2>=3.1.0`
- `chat_template` extra가 Jinja2를 포함
- Jinja2는 기본 `install_requires`에는 포함되지 않음
- `_cached_compile_jinja_template`은 Jinja2 부재 시 현재 관측된 동일한 ImportError 발생

Sources:

- `https://github.com/huggingface/transformers/blob/v5.16.1/setup.py`
- `https://github.com/huggingface/transformers/blob/v5.16.1/src/transformers/dependency_versions_table.py`
- `https://github.com/huggingface/transformers/blob/v5.16.1/src/transformers/utils/chat_template_utils.py`

## New Finding / Problem

official-pinned-001은 tokenizer core packages를 정확히 pin했지만 승인된 작업에 필요한
chat-template optional dependency를 포함하지 않았다. 따라서 기존 failure는 tokenizer
asset integrity 문제나 historical token-count mismatch가 아니라 experiment dependency
contract incompleteness다.

## Why This Requires Chat

현재 lineage는 one-attempt acquisition을 이미 사용했다. Jinja2 설치, version pin,
dependency artifact acquisition, gate rerun은 기존 환경을 변경하고 새 실행 lineage를
만드므로 Work가 임의로 계속할 수 없다.

## Options

### Option A — v0.2A.1을 blocked/inconclusive로 종결

장점:

- one-attempt contract를 가장 엄격하게 유지한다.

단점:

- 원인이 명백하고 수정 가능하지만 context-volume experiment를 평가하지 못한다.

### Option B — 새 continuation lineage에서 공식 chat-template dependency 추가

기존 official-pinned-001을 보존하고 새 isolated environment 또는 immutable clone에
`jinja2>=3.1.0`의 사전 고정 exact version과 필요한 transitive dependency만 공식 PyPI에서
한 번 획득한다. 새 provenance를 기록한 뒤 historical 4,903/14,387 exact gate를 처음부터
실행한다.

장점:

- official Transformers contract에 근거한 좁은 defect correction이다.
- tokenizer/version/template를 historical 결과에 맞춰 탐색하지 않는다.

단점:

- Jinja2 exact version을 실행 전 고정해야 한다.
- 새 acquisition/gate lineage가 필요하다.

## Work Recommendation

추천: Option B

추천 강도: Strong

근거: 원인이 official source와 실제 traceback 양쪽에서 일치하며, 추가 대상은 임의의
tokenizer 조합이 아니라 Transformers가 공식 선언한 chat-template dependency다. 기존
실패를 덮어쓰지 않고 새 lineage로 분리하면 one-attempt evidence도 보존된다.

추천이 부적절할 수 있는 조건: v0.2A.1 context-volume 실험의 추가 가치가 낮아졌거나,
어떤 추가 acquisition도 one-attempt 정신에 어긋난다고 CEO가 판단하는 경우.

## Decision Needed From Chat / CEO

1. 기존 official-pinned-001을 blocked evidence로 보존하면서 Jinja2 correction을 별도
   continuation lineage로 진행할 것인가?
2. 진행한다면 official PyPI의 Jinja2 exact version과 transitive dependencies를 실행 전에
   고정하는 limited acquisition을 승인할 것인가?
3. corrected historical exact-count gate 성공 시 기존 승인된 S-short/S-long-control 각 1회
   실행까지 다시 허용할 것인가?

## References

- Acquisition evidence: `5f59646e8ad7371f7f948e1bf06f75357a24535c`
- Initial assessment: `b93d9d3e46e9c9519bc39de6f1e46c84b5f35aff`
- Diagnostic preparation: `4923ef04f8f094f22f5991b4dab1e2c6bcf19432`
- Diagnostic evidence: `1090f6ebbf87d445f7986838abcb76e2de3b029a`
- Path: `research_lab/work_reviews/2026-09-10-replay-v02a1-context-volume-control/acquisition_runs/official-pinned-001/diagnostics/import-error-001/`

## Current Safety State

- network attempts: 0
- package installations: 0
- historical count reruns: 0
- model invocations: 0
- historical artifacts modified: false
- review branch push: true
- main/merge/deploy: false
- approval required: any Jinja2 acquisition, environment mutation, count gate rerun, or model execution
