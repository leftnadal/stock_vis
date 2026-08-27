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

Design Lab은 이 방향에 동의한다. 다만 **기업 성장률이 더 높다는 것과 더 좋은 투자기회라는 것은 동일하지 않다.** 현재 valuation, 성장 실현 가능성, 시점, downside, uncertainty, portfolio context에 따라 투자 결과는 달라질 수 있기 때문이다.

## 2. 수정된 Comparison 질문

더 강한 Comparison 질문은 다음과 같다.

> **앞으로 가능한 현실들을 고려했을 때 현재 조건에서 어느 투자가 더 강한 forward opportunity를 가지며, 그 상대적 차이가 portfolio allocation이나 rotation을 검토할 만큼 충분히 크고 신뢰할 만한가?**

이는 기존 maintained judgment를 대체하지 않고 확장한다.

## 3. 수정된 Comparison Architecture

```text
Company A Current Judgment
        ↓
가능한 Future Scenarios
        ↓
Growth / Value Outcomes
        ┐
        │
        ├── Relative Future Opportunity
        │
        ┘
Company B Current Judgment
        ↓
가능한 Future Scenarios
        ↓
Growth / Value Outcomes

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

따라서 Comparison은 `현재 A가 B보다 강하다`에서 끝나면 부족하다.

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
- 무엇이 그 scenario의 applicability를 낮추는가
- 각 회사가 그 현실에서 어떻게 반응하는가
- 성장 / 가치 결과가 어디에서 갈리는가
- 어떤 uncertainty 때문에 강한 확신을 피해야 하는가

이다.

## 5. Growth Alone이 아니라 Relative Opportunity

더 빠르게 성장할 것으로 예상되는 회사가 항상 더 좋은 투자는 아니다.

개념적으로 최소한 다음을 구분해야 한다.

```text
Expected business growth
+ 성장의 durability / probability
+ 현재 valuation에 얼마나 반영됐는가
+ capital requirement / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity`는 working Design 표현이며 Approved Research Concept가 아니다.

제품은 하나의 성장률 예측을 예상 투자수익과 동일시해서는 안 된다.

## 6. False Precision보다 Conditions

현재 더 선호되는 표현은:

```text
Possible Future
→ Conditions
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

## 7. Rotation Threshold / Relative Opportunity Gap

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

## 8. Research Lab과의 Boundary

Design Lab은 다음의 authoritative methodology를 임의로 정의하지 않는다.

- scenario construction
- predictive probability
- forecast calibration
- expected growth / return estimation
- valuation-outcome mapping
- probability weighting
- uncertainty aggregation
- predictive / comparative Claim의 epistemic evaluation

Research Lab Evaluation Methodology는 이미 predictive Claim 안의 probability와 그 Claim의 credibility가 다르다고 명시하고 있으며, predictive model에는 purpose/context에 맞는 calibration 및 out-of-sample evaluation 등이 필요할 수 있음을 규정한다.

따라서 이번 작업은 다음 **Research Trigger Candidate**를 만든다.

> **향후 scenario, predictive growth/value outcome, relative opportunity comparison을 downstream Design과 portfolio decision support에 사용할 만큼 충분히 강하게 생성·평가하려면 Research Lab에 어떤 methodology가 필요한가?**

Design은 이러한 output을 사용자가 어떻게 이해하고 비교해야 하는지는 계속 탐색할 수 있지만, 그 epistemic methodology 자체를 조용히 만들어서는 안 된다.

## 9. Working Findings

### 9.1 Comparison은 forward-looking이어야 한다

현재 상태 비교만으로는 실제 rotation 판단을 충분히 지원하지 못한다.

**Recommendation Strength: Strong**

### 9.2 하나의 deterministic future보다 scenario structure가 우세하다

Conditional future를 여러 개 보존하면 uncertainty와 failure condition을 더 잘 드러낼 수 있다.

**Recommendation Strength: Strong**

### 9.3 Growth 하나만 optimization variable로 두지 않는다

Relevant object는 raw business growth보다 현재 가격과 uncertainty를 포함한 forward investment opportunity에 더 가깝다.

**Recommendation Strength: Strong**

### 9.4 Rotation에는 meaningful relative gap이 필요하다

작은 apparent advantage가 자동으로 portfolio churn으로 이어져서는 안 된다.

**Recommendation Strength: Strong**

## 10. Failure / Reversal Conditions

다음이 확인되면 이 방향을 수정한다.

- scenario 표현이 transparency보다 false confidence를 더 크게 만듦
- conditional future 비교가 사용자에게 지나치게 어렵거나 느림
- 더 단순한 forward metric으로도 동일한 judgment quality를 훨씬 낮은 cognitive cost로 제공 가능
- relative-opportunity framing이 과도한 portfolio turnover를 유도
- valuation / uncertainty를 함께 보여줄 때 scalar compression 없이 이해하기 어려움
- Research methodology가 forward comparison에 대해 materially 다른 epistemic structure를 제시

## 11. CEO Critical Decision

**현재 없음.**

CEO는 future-looking growth와 future-state comparison이 Comparison 문제에 포함되어야 한다는 working direction에 동의했다. 아직 이를 Stock_vis의 최상위 Product optimization principle로 승인한 것은 아니다.

향후 Stock_vis Portfolio Experience를 `continuous relative-opportunity optimization` 중심으로 정의하려는 제안이 나오면 장기 Product / Design 방향에 영향이 크므로 CEO Critical Decision으로 다시 올린다.
