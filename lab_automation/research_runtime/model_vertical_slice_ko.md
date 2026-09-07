# Research Runtime Model-backed Vertical Slice v0.1

**Status:** Implementation Candidate  
**Experiment ID:** `SV-RES-RUNTIME-MODEL-E2E-001`  
**Scope:** controlled synthetic calibration with configurable command backends

## 0. 목적

이 단계는 deterministic fixture를 실제 command-backed model/tool invocation으로 교체하면서도, 기존 Research Experiment Profile의 provenance / exposure / target lineage / evaluation separation이 그대로 유지되는지 확인한다.

```text
Synthetic Task + Evidence
        ↓
Researcher backend
        ↓
Critic backend
        ↓
Revision backend
        ↓
Separated Evaluator backend
        ↓
Harness benchmark + Experiment Profile
```

이 pilot은 특정 모델의 일반적 우수성을 증명하지 않는다.

## 1. Backend contract

v0.1 backend는 subprocess command를 사용한다.

- stdin: role-specific prompt
- stdout: **정확히 하나의 JSON object**
- stderr: raw execution artifact로 보존
- non-zero exit / timeout / invalid JSON: fail-closed

모델/provider 선택은 configuration이며 Research Lab의 epistemic authority가 아니다.

각 역할은 같은 command를 쓸 수도 있고, role별로 다른 command / model identity를 지정할 수도 있다.

## 2. Example config

기본 예시는 `model_backend.example.json`이다.

```json
{
  "backend_type": "command_json",
  "default": {
    "command": ["codex", "exec", "-"],
    "backend_name": "codex_cli",
    "requested_identity": "codex-cli/default",
    "identity_assurance": "requested_only",
    "timeout_seconds": 300
  },
  "roles": {
    "researcher": {},
    "critic": {},
    "revision": {},
    "evaluator": {}
  }
}
```

이 config는 **연결 후보**다. 실제 Codex CLI가 final stdout을 순수 JSON으로 내보내지 않으면 runtime은 성공으로 간주하지 않고 `invalid_output`으로 기록한다. 관찰된 실제 CLI 출력 형식에 맞춰 adapter를 보강해야 하며, 현재 단계에서 추정 parser를 넣지 않는다.

Local MLX / llama.cpp / 기타 local model은 stdin prompt를 받고 stdout에 JSON object 하나를 출력하는 작은 wrapper command를 통해 동일 contract에 연결할 수 있다.

Secret / credential은 config 파일에 저장하지 않는다. 필요한 인증은 process environment 또는 별도 secret mechanism을 사용한다.

## 3. 실행

```bash
poetry run python -m lab_automation.research_runtime.model_vertical_slice \
  --config lab_automation/research_runtime/model_backend.example.json
```

별도 state root:

```bash
poetry run python -m lab_automation.research_runtime.model_vertical_slice \
  --config /path/to/backend.json \
  --state-root /path/to/runtime-state
```

Artifact Store root는 state root 아래이므로, Mac Studio internal 2TB에 종속되지 않는다. 향후 외장 NVMe/NAS 경로를 state root로 지정해도 logical `artifact://sha256/...` identity는 바뀌지 않는다.

## 4. Model-visible material과 protected material

모델에게 보이는 것은 각 role에 필요한 Task / Evidence / prior output뿐이다.

Harness-only protected expectation(`24%`)은 별도 artifact로 저장하지만 model exposure에는 넣지 않는다.

Evaluator는 다음만 본다.

```text
Evidence
+ baseline Researcher output
+ revised output
```

Critic reasoning/output은 Evaluator에게 직접 전달하지 않는다.

## 5. Harness benchmark

모든 model invocation이 끝난 뒤에만 deterministic harness가 synthetic ground truth를 사용한다.

Harness는 최소한 다음 delta를 계산한다.

- Researcher baseline이 24%와 맞는가
- Revision이 baseline 오류를 고쳤는가
- 원래 맞던 Segment A 60%를 보존했는가
- 새로운 오류를 만들었는가
- unresolved 오류가 남았는가

이 benchmark는 model Evaluator를 대체하지 않는다. Model Evaluator output과 harness benchmark를 함께 남겨 이후 Evaluator calibration 자료로 사용할 수 있다.

## 6. 성공/실패 의미

Runtime `completed`는 다음을 뜻한다.

- 네 role invocation이 모두 valid JSON contract를 충족함
- protected expectation leakage가 알려진 exposure에 없음
- Critic stage의 declared independence 위반 없음
- Evaluator가 Critic output에 직접 노출되지 않음
- required stage가 모두 완료됨

`completed`는 다음을 뜻하지 않는다.

- Researcher가 정답을 맞춤
- Critic이 반드시 개선함
- Evaluator가 반드시 harness와 일치함
- 특정 model이 Research Lab 역할에 적합함

즉 execution integrity와 epistemic quality를 분리한다.

## 7. 다음 단계

첫 실제 command-backed run 결과를 보고 다음을 결정한다.

```text
Codex/local command output behavior 관찰
→ adapter 보강 필요 여부
→ 동일 workload 반복/replication
→ role별 model 분리
→ Critic delta 및 Evaluator alignment 축적
→ legacy experiment import
→ Mac Studio 도착 후 direct local-model backend / runtime benchmark
```

특히 첫 real run에서 parser 편의를 위해 raw stdout을 버리거나 자동으로 정답을 추정해서는 안 된다. 실패도 그대로 artifact와 ledger에 남긴다.
