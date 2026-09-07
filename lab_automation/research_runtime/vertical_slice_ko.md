# Research Runtime First Vertical Slice v0.1

**Status:** Implementation Candidate  
**Experiment ID:** `SV-RES-RUNTIME-E2E-001`  
**Scope:** deterministic synthetic calibration only

## 0. 목적

첫 vertical slice는 모델 품질을 측정하지 않는다. Shared Run Ledger + Research Experiment Profile이 다음 흐름을 실제 runtime record로 연결할 수 있는지를 검증한다.

```text
Researcher
→ Critic
→ Revision
→ Evaluator
→ Research Experiment Profile
→ Integrity findings
```

Synthetic Case는 denominator alignment 오류를 의도적으로 포함한다.

- Segment A = total revenue의 60%
- Customer Z = Segment A revenue의 40%
- 초기 Researcher fixture는 이를 total revenue의 40%로 잘못 해석한다.
- Critic fixture는 denominator mismatch를 찾아 24%라는 bounded repair를 제안한다.
- Revision fixture는 올바른 60% 정보는 보존하면서 해당 오류만 수정한다.
- Evaluator fixture는 Critic reasoning을 직접 보지 않고 baseline, revision, Evidence를 비교한다.

## 1. 검증하는 것

- Researcher / Critic / Revision / Evaluator 각각의 shared Run 및 Invocation 기록
- exact input snapshot과 output artifact 연결
- `artifact://sha256/...` 기반 content-addressed provenance
- Exposure Profile
- target run / target artifact hash lineage
- protected expectation이 agent exposure에 들어가지 않았는지
- Critic stage의 declared independence
- all-required stage completion
- Evaluator가 Critic output에 직접 노출되지 않았는지
- Critic delta를 `repaired / preserved / introduced / unresolved`로 분리할 수 있는지
- 반복 실행이 기존 runtime history를 덮어쓰지 않는지

## 2. 검증하지 않는 것

이 pilot으로 다음을 주장하면 안 된다.

- 특정 local / Frontier LLM의 Researcher 또는 Critic 품질
- 실제 뉴스/공시 Evidence acquisition 품질
- Research Lab-wide 자동화 준비 완료
- production research admission readiness
- Mac Studio 성능 또는 model residency 성능

Fixture backend는 runtime plumbing을 deterministic하게 검증하기 위한 장치다.

## 3. 실행

```bash
poetry run python -m lab_automation.research_runtime.vertical_slice
```

별도 state root를 사용하려면:

```bash
poetry run python -m lab_automation.research_runtime.vertical_slice \
  --state-root /path/to/stockvis-runtime-state
```

기본 state root는 `~/.stockvis-lab-automation`이다.

## 4. 결과 위치

각 실행은 새로운 `execution_id`를 만든다.

```text
<state-root>/
├── artifacts/sha256/...
├── ledger/
│   └── SV-RES-RUNTIME-E2E-001-<execution-id>.jsonl
└── research_runtime/
    └── SV-RES-RUNTIME-E2E-001/
        └── <execution-id>/
            └── summary.json
```

따라서 같은 experiment를 반복 실행해도 이전 run history를 덮어쓰지 않는다.

## 5. 성공 조건

성공한 summary는 최소한 다음을 보여야 한다.

- `status = completed`
- `blocking_failures = []`
- evaluation conclusion = `improved`
- repaired error = `customer_z_total_share denominator mismatch`
- preserved correct content = `segment_a_total_share`
- introduced errors = `[]`
- unresolved errors = `[]`
- evaluator exposure에 Critic output 없음
- 모든 required stage completion PASS
- known expected-answer leakage 없음
- Critic stage independence PASS

## 6. 다음 단계

이 deterministic vertical slice가 실제 branch checkout에서 통과하면 다음 순서는:

```text
fixture backend
→ controlled external/local model backend
→ same synthetic workload
→ Critic delta evaluation
→ legacy experiment import
→ Mac Studio local runtime benchmark
```

모델을 바꾸더라도 상위 Research Experiment Profile과 artifact / exposure / evaluation lineage는 동일하게 유지하는 것이 목표다.
