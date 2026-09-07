# Research Runtime — First Codex-backed Synthetic Run Guide v0.1

**Status:** Execution Guide / Implementation Candidate  
**Branch:** `lab-automation/bootstrap-v0.1`  
**Experiment:** `SV-RES-RUNTIME-MODEL-E2E-001`

## 0. 목적

이 절차의 목적은 특정 모델의 품질을 평가하는 것이 아니라, 실제 Mac의 Codex CLI가 Research Runtime의 command backend contract와 어떻게 상호작용하는지 처음 관찰하는 것이다.

첫 실행에서는 실패도 정상적인 관찰 결과다. 특히 Codex CLI stdout이 순수 JSON object가 아니면 runtime은 `invalid_output`으로 fail-closed하고 raw stdout/stderr, input snapshot, invocation record, ledger를 보존한다.

## 1. 전제

전용 `stock_vis_lab_automation` worktree에서 실행한다. 기존 Claude Code main 작업공간은 사용하지 않는다.

```bash
cd <stock_vis_lab_automation 경로>
git branch --show-current
```

Expected:

```text
lab-automation/bootstrap-v0.1
```

작업공간이 깨끗한지 확인한다.

```bash
git status --short
```

출력이 없어야 한다.

## 2. 최신 branch 동기화

```bash
git fetch origin lab-automation/bootstrap-v0.1
git status -sb
git log -1 --oneline
git log -1 --oneline origin/lab-automation/bootstrap-v0.1
```

local branch가 remote보다 뒤처져 있고 local 변경이 없다면:

```bash
git pull --ff-only origin lab-automation/bootstrap-v0.1
```

merge commit을 만들지 않는다.

## 3. 도구 확인

```bash
poetry --version
poetry run python --version
codex --version
```

필요하면 의존성을 동기화한다.

```bash
poetry install
```

Codex 인증/설정은 로컬 Codex 환경을 사용한다. secret은 repository의 backend config에 넣지 않는다.

## 4. Config 확인

기본 연결 후보:

```text
lab_automation/research_runtime/model_backend.example.json
```

현재 기본값은 네 역할 모두:

```text
codex exec -
```

을 사용한다. timeout은 300초다.

이 파일은 연결 후보이지 성공이 보장된 adapter가 아니다. Codex가 stdout에 진행 로그나 Markdown을 섞으면 첫 run은 의도적으로 실패한다.

## 5. 자동 launcher 사용 — 권장

다음 한 명령을 권장한다.

```bash
bash lab_automation/research_runtime/run_model_vertical_slice.sh
```

이 script는 순서대로:

1. branch 확인
2. clean worktree 확인
3. Poetry / Codex 확인
4. 관련 unit tests 실행
5. deterministic fixture sanity check
6. 실제 Codex-backed synthetic vertical slice 실행
7. latest summary / ledger / artifact 위치 출력

을 수행한다.

이 script는 push, merge, deploy를 하지 않는다.

별도 runtime 저장장치를 사용하려면 예를 들어:

```bash
export STOCKVIS_LAB_STATE_ROOT="/Volumes/StockVisResearch/runtime"
bash lab_automation/research_runtime/run_model_vertical_slice.sh
```

이 경우 logical `artifact://sha256/...` identity는 저장장치 위치와 독립적이다.

## 6. 수동 실행이 필요한 경우

먼저 tests:

```bash
poetry run python -m pytest \
  lab_automation/test_artifact_store.py \
  lab_automation/test_execution_records.py \
  lab_automation/test_ledger.py \
  lab_automation/test_local_runner.py \
  lab_automation/research_runtime/test_preflight.py \
  lab_automation/research_runtime/test_profile_io.py \
  lab_automation/research_runtime/test_vertical_slice.py \
  lab_automation/research_runtime/test_backends.py \
  lab_automation/research_runtime/test_model_vertical_slice.py \
  -q
```

Fixture check:

```bash
poetry run python -m lab_automation.research_runtime.vertical_slice
```

실제 command-backed run:

```bash
poetry run python -m lab_automation.research_runtime.model_vertical_slice \
  --config lab_automation/research_runtime/model_backend.example.json
```

## 7. 성공했을 때 볼 것

CLI 마지막 JSON과 다음 파일을 본다.

```text
~/.stockvis-lab-automation/research_runtime/
  SV-RES-RUNTIME-MODEL-E2E-001/
    <execution_id>/summary.json
```

우선 확인:

```text
status
blocking_failures
benchmark
model evaluator output
integrity_findings
run_ids
```

`completed`는 실행 integrity가 통과했다는 뜻이지 모델이 좋다는 뜻이 아니다.

## 8. 실패했을 때 볼 것

가장 최근 ledger:

```bash
ls -t ~/.stockvis-lab-automation/ledger/SV-RES-RUNTIME-MODEL-E2E-001-*.jsonl | head -1
```

마지막 event:

```bash
tail -10 <ledger path>
```

Artifact Store:

```text
~/.stockvis-lab-automation/artifacts/sha256/
```

첫 run에서 특히 관찰할 실패:

- command not found
- timeout
- non-zero return code
- stdout invalid JSON
- required output shape invalid

raw stdout/stderr와 input snapshot을 보존한 채 원인을 확인한다. 실패 artifact를 삭제하고 다시 성공한 것처럼 만들지 않는다.

## 9. 첫 run에서 하지 말 것

- parser를 임의로 느슨하게 만들어 Markdown 속 JSON을 자동 추정하지 않는다.
- protected expectation 24%를 prompt에 넣지 않는다.
- Critic output을 Evaluator input에 넣지 않는다.
- 첫 한 번의 결과로 Codex/특정 모델의 Researcher 또는 Critic 적합성을 결론내리지 않는다.
- 실패한 ledger/artifact를 삭제하지 않는다.

## 10. 결과를 공유할 때

다음 세 가지를 채팅에 붙이면 다음 adapter 보강을 정확히 할 수 있다.

1. launcher 전체 terminal output 또는 오류 부분
2. latest ledger의 마지막 5~10행
3. 생성된 `summary.json`이 있으면 그 내용

secret/token/password가 terminal output에 노출됐다면 붙이기 전에 제거한다.

## 11. 첫 결과 후 분기

### A. 순수 JSON으로 정상 완료

동일 config를 2~3회 replication하여 output variance와 evaluator alignment를 본다.

### B. Codex는 성공했지만 stdout contract 실패

raw stdout 형식을 기반으로 Codex-specific adapter를 최소 변경으로 추가한다.

### C. 특정 role output schema 실패

role prompt/schema contract를 수정하되 hidden expectation을 추가하지 않는다.

### D. runtime integrity failure

model 품질 실험으로 넘어가지 않고 exposure/target/lineage 문제를 먼저 수정한다.
