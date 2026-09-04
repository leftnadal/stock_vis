# Stock_vis Math Lab Evaluation Methodology

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.2  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab Evaluation의 목적은 결과를 한 점수로 인증하는 것이 아니라, **무엇이 지지되고, 무엇이 약하며, 무엇이 미평가됐고, 어디서 실패할 수 있는지**를 명시하는 것이다.

Evaluation은 연구 process와 result를 모두 보지만 둘을 합치지 않는다. 높은 backtest score는 높은 epistemic credibility와 같지 않다.

Math Lab 자체도 평가 대상이다. Lab Meta-Evaluation은 개별 연구결과가 아니라 **연구 시스템이 신뢰성, 발견능력, 재현성, 효율, 데이터 적합성, Cross-Lab 가치 측면에서 제대로 작동하고 있는지**를 평가한다. Meta-Evaluation metric은 최적화 KPI가 아니라 diagnostic signal이다.

## 1. Common Evaluation Contract

material evaluation은 다음을 식별할 수 있어야 한다.

```text
Evaluation Target + Version
+ Evaluation Purpose
+ Declared Scope
+ Epistemic Consequence
+ Applicable Profile
+ Material Evidence / Artifacts / Provenance
+ Effective Challenge
→ Structured Evaluation Result
```

결과에는 필요에 따라 다음을 포함한다.

- supported findings
- weakness / limitation
- conflict / alternative
- unknown / unassessed
- assumption / dependency
- failure condition
- evaluation rigor
- evaluation time
- re-evaluation condition

`Not Material`, `Unassessed`, `Unknown`, `Unsupported`, `Contradicted`, `Invalid`, `Out of Scope`, `No Longer Applicable`을 가능한 경우 구분한다.

## 2. Object-Relative Evaluation

다음은 별도 평가 대상이다.

1. Data / Evidence Item
2. Data–Claim / Evidence–Claim relation
3. Evidence / Experiment body
4. Candidate Quantitative Claim
5. Composition
6. Research Process
7. Model
8. Model Use
9. Model Run / Output
10. Quantitative Knowledge candidate
11. downstream signal / deployment suitability
12. Math Lab Operating System / Lab Evolution candidate

하나의 평가를 다른 객체에 자동 상속하지 않는다.

## 3. Data / Evidence Evaluation

### Provenance Integrity

원천, derivation, source ancestry, material transformation을 추적할 수 있는가.

### Generation Reliability

수집·측정·계산·모델 생성 과정이 intended inference에 충분히 신뢰 가능한가.

### Point-in-Time Fidelity

해당 값이 prediction / decision 시점에 실제 이용 가능했는가. 현재 값이 과거 상태를 소급하지 않는가.

### Information Fidelity

가공 과정에서 material information이 손실·왜곡되지 않았는가.

## 4. Claim-Level Evaluation

Candidate Claim의 핵심 profile은 다음과 같다.

### Evidential Sufficiency

material experiments와 evidence body가 stated scope와 strength를 정당화하는가.

### Inferential Soundness

metric에서 claim으로 이동하는 논리가 정당한가. correlation을 causation으로 변환하지 않았는가.

### Scope Calibration

시장, universe, time, horizon, regime, data origin의 범위를 실제 evidence보다 넓히지 않았는가.

### Challenge Resilience

counterevidence, alternative model, data leakage test, robustness, replication 후에도 claim이 살아남는가.

### Selection / Search Burden

Attempt Registry가 보여주는 multiple testing, hyperparameter, seed, subgroup, horizon search를 고려했는가.

## 5. Predictive Claim Extensions

예측 claim에는 필요에 따라 다음을 본다.

- out-of-sample performance
- calibration
- rank / direction / magnitude suitability
- temporal stability
- cross-sectional stability
- regime dependence
- residual dependence
- target overlap
- turnover / cost sensitivity
- benchmark improvement
- abstention behavior

정확한 metric 목록은 problem-specific profile로 둔다.

## 6. Statistical Validity ≠ Economic Utility ≠ Deployability

다음 단계는 별도 claim이다.

```text
Statistical Structure
→ Predictive Validity
→ Economic Utility
→ Operational Deployability
```

통계적으로 유의하더라도 거래비용 후 가치가 없을 수 있다. 경제적 backtest가 좋아도 process가 invalid할 수 있다. production 가능성은 또 별도다.

## 7. Probability ≠ Credibility

예:

```text
P(drawdown > 10%) = 17%
```

라는 forecast probability와 그 17% 추정치를 얼마나 믿을 수 있는지는 다른 값이다.

forecast probability, calibration quality, model/claim credibility를 하나의 confidence score로 합치지 않는다.

## 8. Composition Evaluation

여러 feature, model, Lab output을 결합할 때 구성요소가 각각 유효하다는 이유로 합성 결과가 자동 유효해지지 않는다.

```text
Input Units
+ Composition Operation
+ New Assumptions / Interfaces
→ Candidate Composite Result
```

평가 concern:

- operation validity
- interface compatibility
- source ancestry / dependency
- circularity
- scope / condition propagation
- emergent interaction
- double counting

component credibility를 평균·최소·곱으로 자동 계산하지 않는다.

## 9. Research Process Evaluation

process evaluation은 다음을 본다.

- Question–Design alignment
- exploration / confirmation 혼합 여부
- data / source / universe selection bias
- Attempt Registry completeness
- material alternatives
- protocol compliance
- point-in-time integrity
- reproducibility
- material deviation
- holdout exposure
- failed run preservation

엄격한 process가 null result를 만들 수 있고, 약한 process가 우연히 맞는 result를 만들 수도 있다. process와 result를 구분한다.

## 10. Model / Model Use / Run

### Model

일반적인 모델 구조와 capability.

### Model Use

특정 target, feature, horizon, universe, cost context에서의 사용.

### Run / Output

특정 data, code, parameter, time에서의 한 실행.

좋은 Run 하나가 Model Use 전체를 검증하지 않는다.

## 11. Critique, Reproduction, Replication, Evaluation

- **Critique** — material weakness를 찾는다.
- **Reproduction** — 같은 실험을 다시 만들 수 있는지 본다.
- **Replication** — 다른 조건에서 finding이 유지되는지 본다.
- **Evaluation** — 현재 전체 evidence가 무엇을 정당화하는지 판단한다.

서로 대체하지 않는다.

## 12. Knowledge Admission

Knowledge admission에는 claim-level structured evaluation이 필요하다.

최소 warrant 후보:

1. valid Experimental Result
2. reproduction status
3. material critique
4. replication profile 또는 explicit restricted exception
5. source provenance / ancestry
6. scope / condition / limitation
7. re-evaluation trigger

정확한 숫자 threshold나 replication count는 현재 고정하지 않는다.

## 13. Negative / Null Knowledge

잘 설계된 반복 연구에서 특정 model/feature가 baseline을 이기지 못한다는 bounded finding도 Knowledge 후보가 될 수 있다.

단 low-power null을 `효과 없음`으로 자동 승격하지 않는다.

## 14. Re-evaluation

다음은 review trigger가 될 수 있다.

- source data revision
- entity/universe change
- graph relation / score version change
- model / feature implementation change
- new conflicting replication
- regime materially changed
- downstream use changed
- source Lab Understanding revision

변화는 결론을 자동 뒤집는 것이 아니라 재평가 의무를 만든다.

## 15. Lab Meta-Evaluation Purpose

Lab Meta-Evaluation은 Math Lab의 개별 Quantitative Claim을 평가하는 것이 아니라 **Math Lab Operating System이 intended purpose를 제대로 수행하는지**를 평가한다.

주요 질문은 다음과 같다.

- false-positive finding을 충분히 차단하는가
- 동시에 discovery capacity를 지나치게 죽이지 않는가
- experiment와 Knowledge를 시간이 지나도 재구성할 수 있는가
- Critic / Replicator / Evaluator가 실제로 net value를 만드는가
- agent architecture와 tool routing이 과도한 비용·latency·handoff loss를 만들지 않는가
- CEO attention이 consequential decision에 집중되는가
- 반복 Data Gap이 research bottleneck으로 남지 않는가
- Cross-Lab interface가 실제 새 연구·Understanding을 만드는가
- 기존 rule이 새 model/tool/data capability 아래에서도 여전히 필요한가

Meta-Evaluation은 Lab 전체, 특정 operating change, agent topology, tool/harness, permission system, data workflow, Cross-Lab process 등을 target으로 할 수 있다.

## 16. Lab Meta-Evaluation Contract

material Lab Meta-Evaluation은 가능한 경우 다음을 식별한다.

```text
Operating Target + Version
+ Review Trigger / Period
+ Intended Operating Purpose
+ Relevant Case Cohort
+ Runtime / Evaluation / Knowledge / Data Evidence
+ Counterfactual or Baseline where feasible
+ Costs / Failure Modes / Unknowns
→ Structured Operating Assessment
```

결과에는 최소한 필요에 따라 다음을 포함한다.

- observed pattern
- likely mechanism / alternative explanation
- affected scope
- evidence quality and denominator
- material benefit
- material harm / trade-off
- unknown / confounding factor
- improvement hypothesis
- recommended action
- rollback / re-evaluation condition

단순 metric 변화만으로 operating conclusion을 만들지 않는다.

## 17. Lab Health Profile

Lab Health는 하나의 scalar score가 아니다. 다음 profile을 상황에 맞게 평가한다.

### 17.1 Scientific Reliability

Concern:

- invalid / contaminated result detection
- confirmation survival pattern
- replication failure / success pattern
- Knowledge admission 후 reversal / restriction
- hidden multiple testing 발견
- provenance / holdout violation

Interpretation rule:

- 낮은 confirmation survival은 높은 exploration breadth의 정상 결과일 수도 있다.
- 높은 replication success는 쉬운 문제만 선택한 결과일 수도 있다.
- reversal은 admission failure일 수도 있고 legitimate regime / scope change일 수도 있다.

### 17.2 Discovery Capacity / False-Negative Risk

Concern:

- candidate generation diversity
- unexplored research space
- repeated premature closure
- excessive `Unknown` / `No Result`
- high-value hypothesis가 governance cost 때문에 실행되지 않는지
- simple baseline을 넘어 새로운 representation을 탐색할 capacity가 있는지

Interpretation rule:

False positive 감소와 discovery capacity를 함께 본다. `Knowledge가 적다` 또는 `많다` 자체는 health verdict가 아니다.

### 17.3 Reproducibility / Knowledge Durability

Concern:

- reproduction success
- Data View reconstruction
- artifact / environment completeness
- admitted Knowledge의 시간 경과 후 applicability
- revision / retirement의 원인
- re-evaluation latency

Knowledge durability는 영구적으로 맞는다는 뜻이 아니라, scope·condition·change가 추적 가능하다는 의미까지 포함한다.

### 17.4 Challenge Value

Concern:

- Critic이 material defect를 발견하는가
- scope / conclusion / next action을 실제로 바꾸는가
- false objection / duplicate review burden
- Evaluator disagreement의 정보가치
- challenge가 비용·latency 대비 net positive인가

`Critic 호출 수`, `objection 수`를 quality proxy로 쓰지 않는다.

### 17.5 Agent / Workflow Efficiency

Concern:

- parallelization benefit
- duplicate work
- retries / failures
- handoff / synthesis loss
- tool mismatch
- local / Frontier escalation quality
- cost / latency / throughput

Efficiency는 scientific quality를 해치지 않는 조건에서 평가한다.

### 17.6 CEO Attention Efficiency

Concern:

- routine reversible issue의 over-escalation
- material issue의 under-escalation
- Decision Package quality
- delegated decision reversal
- CEO decision reconsideration cause

`CEO escalation 최소화`를 단독 목표로 사용하지 않는다.

### 17.7 Data-System Fitness

Concern:

- repeated Data Gap
- point-in-time failure
- provenance weakness
- source reconstruction failure
- data request reuse across programs
- data cost vs research value

반복 Data Gap은 StockVis Data Platform improvement candidate가 될 수 있다.

### 17.8 Cross-Lab Research Value

Concern:

- handoff가 새 Case / Quantitative Finding / Understanding으로 발전하는가
- source authority와 version이 보존되는가
- operationalization fidelity
- shared ancestry / circularity detection
- source revision propagation
- interface overhead vs epistemic value

handoff 수 자체는 success metric이 아니다.

## 18. Metrics Are Diagnostics, Not Objectives

Meta-Evaluation metric은 다음 방식으로 사용한다.

```text
Metric / Trend / Outlier
→ Diagnostic Signal
→ Investigation
→ Explanation
→ Operating Hypothesis
```

다음과 같은 direct optimization은 기본적으로 금지한다.

- maximize Knowledge admission count
- maximize replication success
- minimize CEO escalation
- minimize Critic disagreement
- maximize experiment throughput
- minimize research cost independent of epistemic consequence

Goodhart-type behavior를 막기 위해 metric은 cohort, denominator, consequence, regime, research difficulty와 함께 해석한다.

## 19. Operating Change Evaluation

Operating Improvement Hypothesis는 가능한 경우 baseline과 비교한다.

예:

```text
Current Workflow
vs
Experimental Workflow
```

평가 concern:

- material defect detection
- false-positive / false-negative risk
- reproducibility
- downstream reversal
- cost / latency / compute
- duplicate work
- handoff burden
- CEO / human burden
- new failure surface

Randomized A/B가 항상 필요한 것은 아니다. staged rollout, shadow mode, matched heterogeneous Cases, retrospective simulation, interrupted time comparison, qualitative process evaluation을 사용할 수 있다.

평가 설계 자체의 selection bias와 non-comparability를 명시해야 한다.

## 20. Operating Change Decision States

Meta-Evaluation 결과는 다음 lifecycle action 후보를 가질 수 있다.

- `Adopt`
- `Modify`
- `Reject`
- `Need More Evidence`
- `Rollback`
- `Retire / Merge`

이 state는 epistemic truth label이 아니라 operating governance action이다.

Material adoption에는 가능한 경우 다음을 기록한다.

- previous version / baseline
- effective scope
- rationale
- evaluation evidence
- known trade-off
- monitoring plan
- rollback path
- re-evaluation trigger

## 21. Meta-Evaluation Must Itself Be Challenged

Lab Meta-Evaluation도 오류 가능하다.

다음 위험을 명시적으로 고려한다.

- metric gaming
- survivorship of easy research cases
- cohort mismatch
- regression to the mean
- learning curve / tool upgrade confounding
- market-regime confounding
- evaluator self-justification
- cost accounting omission
- hidden opportunity cost
- delayed harm

운영 개선을 평가한 evaluator 또는 Lead가 자신의 architecture를 방어하는 방향으로 편향될 수 있으므로, material change에는 독립적이거나 충분히 분리된 challenge를 비례적으로 적용한다.

## 22. Meta-Evaluation and Authority Boundary

Lab Meta-Evaluation은 다음을 자동 수행하지 않는다.

- Foundation / Purpose 변경
- permanent authority boundary 변경
- permanent core role 확정
- major infrastructure purchase
- product deployment
- Research Lab / Design Lab meaning 변경

이런 consequential change는 applicable CEO / Authority Review로 escalation한다.

반대로 reversible prompt, routing, small harness, pilot-level workflow improvement는 현재 approved boundary 안에서 delegated operating experiment로 수행할 수 있다.
