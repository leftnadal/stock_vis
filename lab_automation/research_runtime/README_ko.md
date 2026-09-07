# Research Runtime Profile v0.1

**Status:** Working / Implementation Candidate  
**Scope:** Shared Lab Automation 위의 Research Lab-specific experiment semantics

## 0. 목적

이 디렉터리는 별도 Research Ledger를 만들지 않는다. 공통 Lab Automation의 Job / Run / Event / Invocation / Artifact 실행 기록을 재사용하고, Research Lab 실험에만 필요한 의미를 참조 형태로 추가한다.

```text
Shared Run Ledger
  -> execution facts / artifacts / invocation history

Research Experiment Profile
  -> experiment purpose / workload / exposure / blinding / independence / evaluation linkage
```

이 profile은 Research Methodology, Evaluation Methodology, Operational Record Specification을 재정의하지 않으며 Research Knowledge나 새로운 epistemic object를 만들지 않는다.

## 1. 최소 객체

- `ExperimentProfile` — 실험 목적, validation question, scope, confounds, interpretation boundary
- `WorkloadProfile` — case/task/instruction/evidence snapshot과 evaluation partition
- `StageProfile` — function, planned runs, completion policy, independence intent
- `RunLink` — shared Run과 exact target/input snapshot 연결
- `ExposureProfile` — 실제로 agent 판단에 영향을 줄 수 있었던 material context
- `EvaluationLink` — Evaluation Methodology에 따른 외부 평가 기록과 shared run 연결

## 2. Integrity preflight

v0.1은 최소한 다음 실패를 탐지할 수 있어야 한다.

- protected expectation leakage
- declared independent stage에서 peer Critic output exposure
- protected holdout의 known contamination
- all-required stage의 incomplete execution

`NO_KNOWN_LEAK_DETECTED`와 `NO_KNOWN_CONTAMINATION`은 완전 무오염 증명이 아니라 현재 기록에서 알려진 누수가 없다는 뜻이다.

## 3. Exposure 원칙

모든 token이나 private chain-of-thought를 저장하지 않는다. 결과 해석을 materially 바꿀 수 있는 context만 reference로 보존한다.

예:

- Evidence snapshot
- prior agent output
- retrieved learning artifact
- material tool result
- 기타 판단에 영향을 줄 수 있는 explicit context

## 4. Holdout

`protected_holdout` Case는 retrieval, training, expectation access와 분리되어야 한다. 실제 격리 정책과 저장소 권한 enforcement는 후속 구현에서 강화하되, v0.1부터 partition과 contamination check를 기록한다.

## 5. First vertical slice

첫 end-to-end Research Runtime pilot은 `SV-RES-RUNTIME-E2E-001`이다.

```text
Researcher fixture
→ independent Critic fixture
→ Revision fixture
→ separated Evaluator fixture
→ Experiment Profile + integrity findings
```

실행:

```bash
poetry run python -m lab_automation.research_runtime.vertical_slice
```

이 pilot은 deterministic synthetic calibration이며 모델 품질을 평가하지 않는다. 목적은 shared Run / Invocation / Artifact 기록과 Research-specific Exposure / target lineage / Evaluation linkage가 하나의 재구성 가능한 흐름으로 연결되는지 확인하는 것이다.

세부 성공 조건과 해석 경계는 [Research Runtime First Vertical Slice v0.1](vertical_slice_ko.md)을 따른다.

## 6. Model-backed vertical slice

두 번째 vertical slice는 `SV-RES-RUNTIME-MODEL-E2E-001`이다.

```text
Researcher command backend
→ Critic command backend
→ Revision command backend
→ separated Evaluator command backend
→ harness benchmark + Experiment Profile
```

공통 backend contract는 `backends.py`에 있으며, v0.1은 stdin prompt → stdout 단일 JSON object를 요구하는 `command_json` backend만 지원한다. role별 command/model identity를 config에서 다르게 지정할 수 있다.

실행 예:

```bash
poetry run python -m lab_automation.research_runtime.model_vertical_slice \
  --config lab_automation/research_runtime/model_backend.example.json
```

이 단계에서도 runtime completion과 epistemic quality를 분리한다. 모델이 정답을 맞추거나 Critic이 개선해야 runtime이 성공하는 것이 아니라, 정확한 input/output/exposure/target lineage와 integrity boundary가 보존되어야 한다.

세부 contract와 해석 경계는 [Research Runtime Model-backed Vertical Slice v0.1](model_vertical_slice_ko.md)을 따른다.
