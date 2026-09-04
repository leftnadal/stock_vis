# Stock_vis Math Lab Operating Model

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab은 정량 탐색을 폭넓게 위임하되, confirmation·재현성·독립적 challenge를 보호하고 CEO attention은 consequential decision에 집중한다.

> **The Math Lab should maximize delegated quantitative exploration while protecting confirmation, reproducibility, and independent challenge, and concentrating CEO attention on consequential decisions.**

## 1. 역할은 physical agent가 아니라 기능이다

핵심 기능은 다음과 같다.

1. CEO / Project Owner
2. Math Lab Lead / AI Co-researcher
3. Quant Researcher / Experimenter
4. Quant Critic / Auditor
5. Verifier / Replicator
6. Evaluator
7. Specialist-on-Demand

한 runtime agent가 여러 기능을 수행할 수 있고, 하나의 기능을 여러 agent가 병렬 수행할 수도 있다. 중요한 것은 epistemic function의 분리다.

## 2. CEO / Project Owner

CEO는 다음에 대한 최종 authority를 가진다.

- Purpose / Scope / core Principle
- Lab 간 authority boundary
- major Research Program priority
- 큰 데이터·compute·인프라 투자
- production / user exposure
- irreversible 또는 long-term dependency
- material cross-Lab composition

CEO는 특정 p-value, leakage 여부, hyperparameter, 재현 성공 여부를 직접 truth verdict로 정하는 기본 reviewer가 아니다. material concern이 있으면 re-evaluation을 요구할 수 있다.

## 3. Math Lab Lead

Lead는 다음을 담당한다.

- Problem / Case framing
- prediction target과 unit-of-analysis 분해
- minimum useful agent team 구성
- exploration / confirmation posture 구분
- experiment sequence와 resource allocation
- Critic / Replicator / Evaluator routing
- synthesis와 unresolved gap 유지
- Data Gap / Opportunity routing
- consequential issue의 CEO escalation

Lead는 최초 제안을 방어할 의무가 없으며 자신의 판단만으로 Knowledge를 승격하지 않는다.

## 4. Researcher / Experimenter

Researcher는 탐색, feature construction, statistics, model building, baseline, simulation, negative finding, candidate claim 생성을 수행한다.

Researcher는 자신의 결과의 최종 confirmation 또는 admission authority가 아니다.

## 5. Critic / Auditor

Critic은 결과가 틀렸거나 과대평가됐다고 가정하고 material weakness를 찾는다.

주요 attack surface:

- look-ahead / target leakage
- survivorship / selection bias
- multiple testing / data snooping
- hyperparameter / seed / benchmark overfitting
- invalid temporal or panel split
- point-in-time provenance failure
- ChainSight graph timing / edge ancestry failure
- transaction-cost / turnover omission
- metric cherry-picking
- failed attempts omission
- alternative explanation

Critic의 목적은 objection 수를 늘리는 것이 아니라 결과 status를 바꿀 수 있는 defect를 찾는 것이다.

## 6. Verifier / Replicator

### Reproduction

같은 material data, code, environment, parameter로 결과를 다시 만들 수 있는지 확인한다.

### Replication

다른 time, universe, implementation, researcher/agent, model family, source ancestry에서 핵심 finding이 유지되는지 확인한다.

`seed만 바꿈`, `같은 데이터에서 재실행`은 강한 replication이 아니다.

## 7. Evaluator

Evaluator는 declared Evaluation Purpose 아래 무엇이 실제로 지지되는지 구조화한다.

다음을 구분한다.

```text
Model ≠ Model Use ≠ Run / Output ≠ Quantitative Claim ≠ Tradable Signal
```

Evaluator는 다음을 기술한다.

- supported
- weak / limited
- conflicting
- unknown / unassessed
- invalid
- failure condition
- re-evaluation condition

Evaluation은 score certification이 아니라 critical characterization이다.

## 8. Minimum Epistemic Team

| Research state | Minimum functional separation |
|---|---|
| low-consequence exploration | Lead + Researcher, self-critique 허용 |
| material candidate | Researcher + separated Critic |
| confirmation | Builder와 protected evaluation function 분리 |
| replication candidate | sufficiently independent Replicator |
| Knowledge admission | formal Evaluation + provenance + replication warrant |
| production handoff | downstream governance 별도 |

Invariant:

> **The function that discovers and tunes a result must not be the only function that confirms and evaluates it.**

## 9. Exploration–Confirmation Firewall

Exploration은 feature, model, horizon, visualization을 자유롭게 탐색할 수 있다. 그러나 discovery data에서 발견한 결과는 그 자체로 confirmation이 아니다.

Confirmation에는 material하게 다음을 frozen 또는 predeclared procedure로 고정한다.

- target / horizon
- universe / unit of analysis
- Data View
- feature rule
- baseline
- temporal split
- primary metric
- search budget / selection rule
- failure criteria
- material cost assumption

holdout 확인 후 material redesign이 발생하면 기존 confirmation warrant는 오염된 것으로 처리하고 새 confirmation이 필요하다.

## 10. Holdout Permission Boundary

Builder는 sealed holdout의 raw outcome과 detailed metric을 기본적으로 직접 볼 수 없다. Holdout Executor는 frozen protocol을 실행하고 허용된 결과만 반환한다.

`Holdout Exposure`는 다음을 기록한다.

- actor
- holdout
- purpose
- revealed information
- reveal time
- redesign after exposure
- contamination consequence

## 11. Batch Consensus와 CEO Escalation

기본 운영 단위는 micro-approval이 아니라 coherent research / architecture batch다.

### CEO Critical Decision

- Purpose / Principle 변경
- long-term authority boundary
- large data purchase / backfill
- major production schema change
- permanent core role 또는 large infrastructure
- product deployment / user exposure
- material value trade-off

### Delegated Decision

- reversible feature engineering
- experimental model choice
- local research export
- small adapter / validation
- pilot-level schema candidate

Recommendation Strength와 CEO Criticality는 서로 다른 축으로 유지한다.

## 12. Fast Loop와 Slow Evolution Loop

### Fast Research Loop

```text
Trigger
→ Problem / Case
→ Fresh Question
→ Prior Attempt Review
→ Data Eligibility
→ Research
↕ Critic
→ Candidate Claim
→ Confirmation / Replication
→ Evaluation
→ Lifecycle Action
```

### Slow Lab Evolution Loop

```text
Case Outcome
→ Research Process Evaluation
→ Operating Learning Candidate
→ Cross-Case Validation
→ Prompt / Tool / Harness improvement
or Authority Reconsideration
```

다음을 구분한다.

```text
Observed agent behavior
≠ validated operating learning
≠ deployed harness behavior
≠ permanent Math Lab rule
```

## 13. Local-first / Frontier-on-Exception

현재 Working runtime preference는 local-first / frontier-on-exception이다.

```text
Local
→ better context / retry
→ stronger or independent local attempt
→ specialist
→ Frontier when materially unresolved
```

Frontier output은 모델 origin 때문에 더 높은 authority를 갖지 않는다.

## 14. Telemetry Boundary

Runtime telemetry에는 agent/model/prompt version, routing, retries, failures, critic intervention, tool path, cost, latency, handoff가 포함될 수 있다.

Telemetry는 자동으로 Quantitative Knowledge가 되지 않는다. 모든 hidden chain-of-thought를 보존하는 것도 요구하지 않는다.
