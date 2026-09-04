# Stock_vis Math Lab Evaluation Methodology

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab Evaluation의 목적은 결과를 한 점수로 인증하는 것이 아니라, **무엇이 지지되고, 무엇이 약하며, 무엇이 미평가됐고, 어디서 실패할 수 있는지**를 명시하는 것이다.

Evaluation은 연구 process와 result를 모두 보지만 둘을 합치지 않는다. 높은 backtest score는 높은 epistemic credibility와 같지 않다.

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
