# Workstream 001 — Batch 06 Addendum

> **한국어 Companion 문서**  
> 원문: [`batch_06_future_opportunity_comparison_addendum.md`](batch_06_future_opportunity_comparison_addendum.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 CEO-approved semantic intent와 관련 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — Comparison / Decision Context의 working refinement

## Future Opportunity Comparison과 Rotation Context

## 1. 배경

CEO feedback에서 Batch 06 Comparison의 중요한 공백이 확인됐다.

> 투자자는 단순히 현재 두 회사 중 누가 더 좋은지만 비교하지 않는다. 앞으로 현실이 어떻게 변할지 생각하고, 그 조건에서 어느 회사가 더 크게 성장하거나 더 나은 투자 가치를 만들 수 있는지, 그리고 그 차이가 실제로 자본을 옮길 만큼 충분한지를 판단하려 한다.

Design Lab은 이 방향에 동의한다. 다만 **기업 성장률이 더 높다는 것과 더 좋은 투자기회라는 것은 동일하지 않다.** 현재 valuation, 성장 실현 가능성, 시점, downside, uncertainty, capital requirement, portfolio context에 따라 투자 결과는 달라질 수 있기 때문이다.

추가 refinement로, 미래 성장 역시 opportunity가 자동으로 realized growth가 되는 것처럼 보여서는 안 된다. Experience는 **무엇이 성장을 가능하게 하고, 가속하고, 제한하거나 지연시키고, 시나리오를 깨며, 그 성장이 실제 주주가치로 전환될 수 있는지**를 드러내야 한다.

## 2. 수정된 Comparison 질문

더 강한 Comparison 질문은 다음과 같다.

> **앞으로 가능한 현실들을 고려했을 때 현재 조건에서 어느 투자가 더 강한 forward opportunity를 가지며, 무엇이 잘되어야 하고 무엇이 그 기회를 방해할 수 있으며, 최종적인 상대적 차이가 portfolio allocation이나 rotation을 검토할 만큼 충분히 크고 신뢰할 만한가?**

이는 기존 maintained judgment를 대체하지 않고 확장한다.

## 3. 수정된 Comparison Architecture

```text
Company A Current Judgment
        ↓
가능한 Future Scenarios
        ↓
Growth Opportunity
        ↓
Growth-Path Conditions
  ├─ Enablers
  ├─ Accelerators
  ├─ Bottlenecks / Delays
  ├─ Invalidation Conditions
  └─ Value-Capture Conditions
        ↓
Growth / Value Outcomes
        ┐
        │
        ├── Relative Future Opportunity
        │
        ┘
Company B Current Judgment
        ↓
        동일 구조

            +
Current Valuation
Uncertainty / credibility
Time Horizon
Portfolio Context
Constraints / switching cost
            ↓
Relative Opportunity Gap
            ↓
Rotation을 검토할 만큼 차이가 큰가?
```

따라서 Comparison은 `현재 A가 B보다 강하다`에서 끝나면 부족하고, 시장 opportunity에서 곧바로 성장률로 뛰어가서도 안 된다.

## 4. Future Scenario Layer

하나의 정밀한 미래 예측보다 여러 plausible future를 비교할 수 있어야 한다.

예:

```text
Base scenario
IREN — AI infrastructure 증설 지속, power advantage 유지
NBIS — neocloud 확장 지속, utilization 유지

Upside scenario
IREN — 대형 계약 + 전력 희소성 재평가
NBIS — 빠른 capacity 확대 + 높은 utilization 지속

Downside scenario
IREN — build delay / financing pressure
NBIS — hyperscaler 경쟁 / capital intensity / concentration risk
```

정확한 scenario 개수와 생성 methodology는 이번 Design 작업에서 확정하지 않는다.

Design이 보여줘야 할 핵심은:

- 어떤 미래 상태를 가정하는가
- 그 미래가 성립하려면 어떤 조건이 필요한가
- 무엇이 scenario의 applicability를 낮추거나 무효화하는가
- 각 회사가 그 현실에서 어떻게 반응하는가
- 성장 / 가치 결과가 어디에서 갈리는가
- 어떤 uncertainty 때문에 강한 확신을 피해야 하는가

이다.

## 5. Growth-Path Conditions

미래 시장 opportunity는 자동으로 기업 성장으로 전환되지 않는다. Comparison은 opportunity가 realized value로 이어지는 경로에서 역할이 다른 조건을 구분해야 한다.

### 5.1 Opportunity

시장 수요, 산업 확장, 희소성, 규제 변화, 기술 채택 등 성장을 가능하게 하는 외부 / 구조적 기회.

### 5.2 Enablers

회사가 opportunity를 실제로 가져가기 위해 충분히 존재해야 하는 조건.

예를 들면 capacity, power, customer, financing access, supply, technology, permits, distribution, organization capability 등이 있을 수 있다.

### 5.3 Accelerators

Base path보다 성장의 속도, 규모, economics를 더 높일 수 있는 조건.

### 5.4 Bottlenecks / Delay Conditions

Underlying opportunity 자체를 없애지는 않지만 성장 크기나 시점을 제한하는 조건.

Bottleneck과 thesis-invalidating failure는 구분해야 한다. 1년의 건설 지연과 고객 수요 자체의 소멸은 같은 종류의 문제가 아니다.

### 5.5 Invalidation Conditions

성장을 조금 늦추는 수준이 아니라 scenario 또는 핵심 growth mechanism 자체를 materially 약화시키는 조건 / observation.

### 5.6 Value-Capture Conditions

기업의 매출·규모 성장이 실제로 지속 가능한 투자자 가치로 전환되는지를 결정하는 조건.

Margin, capital intensity, dilution, financing cost, competitive pass-through, reinvestment burden, per-share value creation 등이 중요할 수 있다.

개념적으로:

```text
Market / Structural Opportunity
        ↓
회사가 실제로 가져갈 수 있는가?
        ↓
필요한 속도 / 규모로 실행할 수 있는가?
        ↓
무엇이 제한, 지연, 무효화하는가?
        ↓
성장이 durable shareholder value로 전환되는가?
        ↓
Growth / Value Outcome
```

정확한 taxonomy는 Working Design structure이며 Approved Research ontology가 아니다.

## 6. Monitoring과의 연결

Growth-path conditions는 Future Comparison과 기존 Judgment maintenance를 자연스럽게 연결한다.

Scenario를 만든 뒤 매번 뉴스 전체를 처음부터 해석하기보다 condition-relative signal로 monitoring할 수 있다.

예:

```text
Growth scenario

Enablers
✓ demand evidence 강화
✓ power secured
△ execution capacity

Bottlenecks
! construction timing
△ financing / dilution risk

Invalidation
? 현재 material evidence 없음

Value capture
△ margin / capital efficiency unresolved
```

새로운 Evidence는 어떤 Enabler를 강화했는지, Bottleneck을 악화시켰는지, Invalidation condition에 가까워졌는지, Value Capture를 개선 / 약화했는지를 기준으로 해석할 수 있다. 이 구조는 별도 prediction UI logic을 만들기보다 기존 Judgment-Bearing Relation과 Update Trace에 연결해야 한다.

## 7. Growth Alone이 아니라 Relative Opportunity

더 빠르게 성장할 것으로 예상되는 회사가 항상 더 좋은 투자는 아니다.

개념적으로 최소한 다음을 구분해야 한다.

```text
Expected business growth
+ growth-path conditions / durability
+ 현재 valuation에 얼마나 반영됐는가
+ capital requirement / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity`는 working Design 표현이며 Approved Research Concept가 아니다.

제품은 하나의 성장률 예측을 예상 투자수익과 동일시해서는 안 된다.

## 8. False Precision보다 Conditions

현재 더 선호되는 표현은:

```text
Possible Future
→ Opportunity
→ Enablers / Accelerators / Bottlenecks / Invalidation / Value Capture
→ Company-specific response
→ Relative outcome
→ 어떤 evidence가 이 미래 쪽으로 또는 반대쪽으로 이동시키는가?
```

이고, 기본값으로 다음처럼 압축하지 않는다.

```text
IREN growth = 31.5%
NBIS growth = 47.2%
→ NBIS 승리
```

Research methodology가 충분히 warrant하는 경우 정밀한 forecast를 사용할 수는 있지만, forecast probability와 uncertainty, epistemic credibility는 서로 구분되어야 한다.

## 9. Rotation Threshold / Relative Opportunity Gap

Comparison은 실제로 다음 질문까지 지원해야 한다.

> **대안이 조금 더 좋아 보이는가, 아니면 현재 포트폴리오를 바꿀 만큼 충분히 더 좋은가?**

Working interaction concept는 `Relative Opportunity Gap`이다.

예:

```text
Alternative가 조금 더 좋음
→ 현재 holding 유지도 충분히 합리적

Alternative가 materially 더 좋음
+ supporting evidence 충분
+ valuation도 여전히 매력적
→ rotation deeper review 가치 있음

Alternative가 훨씬 좋아질 가능성
하지만 uncertainty 높음
→ watch / wait / 추가 evidence

현재 holding 약화
+ alternative opportunity 강화
→ rotation case 강해짐
```

아직 investment-decision rule이나 threshold methodology는 아니다.

## 10. Research Lab과의 Boundary

Design Lab은 다음의 authoritative methodology를 임의로 정의하지 않는다.

- scenario construction
- predictive probability
- forecast calibration
- expected growth / return estimation
- valuation-outcome mapping
- probability weighting
- uncertainty aggregation
- proposed growth-path condition의 causal / predictive status
- predictive / comparative Claim의 epistemic evaluation

Research Lab Evaluation Methodology는 이미 predictive Claim 안의 probability와 그 Claim의 credibility가 다르다고 명시하고 있으며, predictive model에는 purpose/context에 맞는 calibration 및 out-of-sample evaluation 등이 필요할 수 있음을 규정한다.

따라서 이번 작업은 다음 **Research Trigger Candidate**를 만든다.

> **향후 scenario, growth-path condition, predictive growth/value outcome, relative opportunity comparison을 downstream Design과 portfolio decision support에 사용할 만큼 충분히 강하게 생성·평가하려면 Research Lab에 어떤 methodology가 필요한가?**

Design은 이러한 output을 사용자가 어떻게 이해하고 비교해야 하는지는 계속 탐색할 수 있지만, 그 epistemic methodology 자체를 조용히 만들어서는 안 된다.

## 11. Working Findings

### 11.1 Comparison은 forward-looking이어야 한다

현재 상태 비교만으로는 실제 rotation 판단을 충분히 지원하지 못한다.

**Recommendation Strength: Strong**

### 11.2 하나의 deterministic future보다 scenario structure가 우세하다

Conditional future를 여러 개 보존하면 uncertainty와 failure condition을 더 잘 드러낼 수 있다.

**Recommendation Strength: Strong**

### 11.3 Growth Path Conditions를 명시적으로 구분한다

Opportunity, realization condition, bottleneck, invalidation, value capture를 하나의 generic risk list로 합치지 않는 쪽이 더 강하다.

**Recommendation Strength: Strong**

### 11.4 Growth 하나만 optimization variable로 두지 않는다

Relevant object는 raw business growth보다 현재 가격과 uncertainty를 포함한 forward investment opportunity에 더 가깝다.

**Recommendation Strength: Strong**

### 11.5 Rotation에는 meaningful relative gap이 필요하다

작은 apparent advantage가 자동으로 portfolio churn으로 이어져서는 안 된다.

**Recommendation Strength: Strong**

## 12. Failure / Reversal Conditions

다음이 확인되면 이 방향을 수정한다.

- scenario 표현이 transparency보다 false confidence를 더 크게 만듦
- growth-path condition taxonomy가 판단 개선 없이 complexity만 늘림
- conditional future 비교가 사용자에게 지나치게 어렵거나 느림
- 더 단순한 forward metric으로도 동일한 judgment quality를 훨씬 낮은 cognitive cost로 제공 가능
- relative-opportunity framing이 과도한 portfolio turnover를 유도
- valuation / uncertainty를 함께 보여줄 때 scalar compression 없이 이해하기 어려움
- Research methodology가 forward comparison에 대해 materially 다른 epistemic structure를 제시

## 13. CEO Critical Decision

**현재 없음.**

CEO는 future-looking growth, future-state comparison, explicit growth-blocking conditions가 Comparison 문제에 포함되어야 한다는 working direction에 동의했다. 아직 이를 Stock_vis의 최상위 Product optimization principle로 승인한 것은 아니다.

향후 Stock_vis Portfolio Experience를 `continuous relative-opportunity optimization` 중심으로 정의하려는 제안이 나오면 장기 Product / Design 방향에 영향이 크므로 CEO Critical Decision으로 다시 올린다.
