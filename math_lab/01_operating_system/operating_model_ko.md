# Stock_vis Math Lab Operating Model

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.2  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab은 정량 탐색을 폭넓게 위임하되, confirmation·재현성·독립적 challenge를 보호하고 CEO attention은 consequential decision에 집중한다.

> **The Math Lab should maximize delegated quantitative exploration while protecting confirmation, reproducibility, and independent challenge, and concentrating CEO attention on consequential decisions.**

Math Lab 자체도 고정된 운영체계로 취급하지 않는다. 연구 결과, 재현·replication 이력, runtime telemetry, Data Gap, Cross-Lab outcome을 이용해 Lab 자체를 주기적·trigger 기반으로 평가하고, 개선안을 controlled operating experiment로 시험한 뒤 adopt / modify / reject / rollback한다.

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
- Lab Meta-Evaluation routing
- operating improvement hypothesis 관리
- consequential issue의 CEO escalation

Lead는 최초 제안을 방어할 의무가 없으며 자신의 판단만으로 Knowledge를 승격하지 않는다. Lab 운영 개선안 역시 자신의 선호만으로 permanent rule로 승격하지 않는다.

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
- reversible operating experiment

Recommendation Strength와 CEO Criticality는 서로 다른 축으로 유지한다.

## 12. Three-Loop Operating Architecture

Math Lab은 세 개의 서로 다른 loop를 유지한다.

### Loop 1 — Fast Research Loop

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

목적은 quantitative knowledge discovery다.

### Loop 2 — Case-Level Operating Learning Loop

```text
Case Outcome
→ Research Process Evaluation
→ Operating Learning Candidate
→ Cross-Case Validation
→ Prompt / Tool / Harness Improvement Candidate
```

목적은 개별 Case에서 발견한 운영 문제를 재사용 가능한 learning으로 전환하는 것이다.

### Loop 3 — Lab Evolution Loop

```text
Case + Runtime + Knowledge + Data + Cross-Lab History
→ Lab Meta-Evaluation
→ System Weakness / Opportunity
→ Operating Improvement Hypothesis
→ Controlled Operating Experiment
→ Before / After Evaluation
→ Adopt / Modify / Reject / Need More Evidence
→ Monitor
→ Rollback or Further Evolution when warranted
```

목적은 **Math Lab이라는 연구기관 자체의 신뢰성·발견능력·효율·적응성을 지속적으로 개선하는 것**이다.

세 loop는 혼합하지 않는다. 개별 Case의 성공이 Lab 구조를 자동 정당화하지 않고, 운영 KPI 변화가 개별 Quantitative Claim의 truth를 바꾸지도 않는다.

## 13. Lab Meta-Evaluation Triggers

Lab Meta-Evaluation은 `periodic`과 `triggered` 두 경로를 가진다.

### 13.1 Periodic Review

초기 Working default는 충분한 운영 표본이 쌓였을 때 batch 단위로 수행한다. 정확한 calendar frequency는 아직 고정하지 않는다.

주기 점검은 최소한 다음 source를 본다.

- Research Case outcomes
- Candidate → Confirmation → Replication → Knowledge transition history
- reproduction / replication history
- Knowledge revision / restriction / retirement
- Attempt Registry and holdout exposure
- Critic / Evaluator intervention
- runtime cost / latency / handoff
- Data Gap / Opportunity recurrence
- Cross-Lab handoff outcome
- CEO escalation burden

### 13.2 Triggered Review

다음은 조기 Meta-Evaluation을 정당화할 수 있다.

- Knowledge reversal / restriction이 비정상적으로 증가
- replication failure가 반복
- reproducibility failure가 반복
- leakage / contamination defect가 반복
- 동일 Data Gap이 여러 heterogeneous Case에서 반복
- Critic 또는 Evaluator가 반복적으로 같은 failure를 놓침
- agent disagreement가 material하게 증가
- compute / latency / API cost가 급증
- CEO escalation이 과도하거나 반대로 material issue를 놓침
- Cross-Lab handoff가 반복적으로 사용되지 않거나 의미 충돌을 만듦
- 운영 변경 후 downstream quality가 악화
- 새 model/tool capability가 기존 architecture의 필요성을 materially 변경

Trigger는 자동 결론이 아니라 review obligation을 생성한다.

## 14. Lab Health Evaluation Dimensions

Meta-Evaluation은 하나의 scalar `Lab Score`를 만들지 않는다. 다음 dimensions를 diagnostic profile로 본다.

### 14.1 Scientific Reliability

- invalid / contaminated result detection
- exploratory finding의 confirmation survival
- replication failure / success pattern
- Knowledge admission 후 material reversal
- hidden multiple-testing discovery
- provenance / holdout violations

낮은 confirmation survival 자체는 자동으로 나쁜 것이 아니다. discovery breadth와 gate rigor를 함께 해석한다.

### 14.2 Discovery Capacity and False-Negative Risk

- 유망 candidate 생성 능력
- 과도한 gate 때문에 exploratory space가 지나치게 축소되는지
- 다양한 model / representation / unit-of-analysis 탐색 여부
- independent negative control과 alternative path가 충분한지
- 반복적으로 `Unknown` 또는 `No Result`로 끝나는 원인이 Reality인지 process bottleneck인지

Math Lab은 false positive 최소화만을 objective로 삼지 않는다.

### 14.3 Reproducibility and Knowledge Durability

- experiment reproduction success
- Data View reconstruction success
- artifact completeness
- admitted Knowledge의 시간경과 후 applicability
- revision / restriction 이유
- regime 또는 source change에 대한 re-evaluation responsiveness

Knowledge가 무너졌을 때 admission failure와 legitimate scope/regime change를 구분한다.

### 14.4 Challenge Value

- Critic intervention이 material defect를 발견했는가
- 결론·scope·next action을 실제로 바꿨는가
- false objection / duplicate challenge burden
- compute / latency 대비 net value
- Evaluator disagreement가 meaningful information을 제공했는가

Critic 호출 횟수 자체를 성공 metric으로 쓰지 않는다.

### 14.5 Agent / Workflow Efficiency

- parallelization benefit
- duplicate work
- handoff loss
- synthesis burden
- retry / failure pattern
- local vs Frontier escalation value
- cost / latency / throughput
- capability mismatch

목표는 최소 비용이 아니라 **과학적 품질을 해치지 않는 효율**이다.

### 14.6 CEO Attention Efficiency

- CEO Critical Decision 수와 질
- routine reversible issue의 불필요한 escalation
- delegated decision 중 뒤늦게 CEO review가 필요해진 비율
- CEO decision reversal / reconsideration cause
- Decision Package가 실제 consequential trade-off를 압축했는지

CEO attention을 적게 쓰는 것이 단독 objective가 아니다. material decision을 놓치지 않는 것과 함께 본다.

### 14.7 Data-System Fitness

- 반복 Data Gap
- point-in-time reconstruction failure
- source provenance defect
- research-blocking data deficiency
- 새 데이터 또는 가공이 여러 Program에 재사용되는 정도
- data cost와 research value

반복되는 Data Gap은 개별 Case limitation이 아니라 StockVis Data Platform improvement candidate가 될 수 있다.

### 14.8 Cross-Lab Research Value

- handoff 수가 아니라 실제 새 Case / Understanding / Quantitative Finding으로 발전했는지
- source authority / version 보존
- operationalization fidelity
- shared ancestry detection
- source revision propagation
- bureaucratic handoff cost 대비 epistemic value

## 15. Metrics Are Diagnostic Signals, Not Optimization Targets

Meta-Evaluation metric은 직접적인 objective function이 아니다.

```text
Metric / Pattern
→ Diagnostic Signal
→ Investigation
→ Explanation
→ Improvement Hypothesis
```

다음과 같은 최적화를 금지한다.

```text
maximize Knowledge count
maximize replication success rate
minimize CEO escalation count
minimize Critic disagreement
maximize experiment throughput
```

이런 metric을 직접 target으로 삼으면 쉬운 연구만 선택하거나 admission 기준을 왜곡하거나 material challenge를 억제할 수 있다.

Metric은 context, denominator, cohort, regime, consequence와 함께 해석한다.

## 16. Operating Improvement Hypothesis

Lab의 운영 변경은 가능한 경우 명시적 hypothesis로 표현한다.

예:

> `Independent Critic을 material confirmatory work에 추가하면 false-positive promotion을 줄이면서 compute/latency 증가를 정당화할 만큼 material defect detection이 개선된다.`

Hypothesis에는 필요에 따라 다음을 포함한다.

- observed weakness / opportunity
- proposed mechanism
- affected workflow / agent / tool / data layer
- expected benefit
- possible harm / trade-off
- evaluation plan
- rollback condition
- authority consequence

## 17. Controlled Operating Experiment

운영 개선을 permanent rule로 바로 적용하지 않는다.

가능한 경우 다음 형태로 시험한다.

```text
Current Workflow / Baseline
vs
Experimental Workflow
```

비교 가능한 concern:

- material defect detection
- false-positive / false-negative risk
- reproducibility
- downstream reversal
- time / cost / latency
- duplicate work
- handoff burden
- user / CEO burden

모든 operating experiment에 randomized A/B가 필요한 것은 아니다. Case heterogeneity와 consequence를 고려해 matched comparison, staged rollout, shadow mode, retrospective simulation, qualitative process evaluation을 사용할 수 있다.

운영 실험 결과는 quantitative research result가 아니며 Quantitative Knowledge로 승격되지 않는다.

## 18. Adoption, Monitoring, and Rollback

Operating experiment의 lifecycle은 다음 중 하나로 종료한다.

- `Adopt`
- `Modify`
- `Reject`
- `Need More Evidence`

Adopt된 변경도 영구 불변이 아니다.

Material operating change는 가능한 경우 다음을 보존한다.

- previous behavior / version
- change rationale
- evidence / evaluation
- effective scope
- rollout mode
- monitoring signals
- reversal / rollback path
- reconsideration trigger

새 workflow가 품질을 악화하거나 비용·복잡성이 disproportionate하면 rollback할 수 있어야 한다.

## 19. Promotion Boundary

다음을 구분한다.

```text
Observed agent behavior
≠ Process Finding
≠ Operating Learning Candidate
≠ Validated Operating Learning
≠ Experimental Harness Change
≠ Active Runtime Default
≠ Permanent Math Lab Rule
```

Permanent rule 또는 core role 변경은 heterogeneous evidence와 authority consequence에 비례한 review를 요구한다.

새로운 permanent agent role은 반복적이고 material하며 기존 role/tool/prompt/routing으로 충분히 처리되지 않고 독립 실행의 net benefit이 확인될 때만 고려한다.

## 20. Local-first / Frontier-on-Exception

현재 Working runtime preference는 local-first / frontier-on-exception이다.

```text
Local
→ better context / retry
→ stronger or independent local attempt
→ specialist
→ Frontier when materially unresolved
```

Frontier output은 모델 origin 때문에 더 높은 authority를 갖지 않는다.

Local-first 자체도 Meta-Evaluation 대상이며 비용·품질·failure pattern에 따라 수정될 수 있다.

## 21. Telemetry Boundary

Runtime telemetry에는 agent/model/prompt version, routing, retries, failures, critic intervention, tool path, cost, latency, handoff가 포함될 수 있다.

Telemetry는 자동으로 Quantitative Knowledge가 되지 않는다. 모든 hidden chain-of-thought를 보존하는 것도 요구하지 않는다.

Lab Meta-Evaluation은 telemetry를 사용할 수 있지만, metric과 telemetry가 연구 semantics나 Authority Source를 조용히 재정의해서는 안 된다.
