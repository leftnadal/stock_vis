# Workstream 001 — Batch 06 Addendum

## Future Opportunity Comparison and Rotation Context

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — working refinement to Comparison / Decision Context

## 1. Origin

CEO feedback identified an important gap in Batch 06 Comparison:

> Investors do not compare only the current quality of two companies. They also try to reason about how future conditions may evolve, which company may grow or create more investment value under those conditions, and whether the difference is large enough to justify rotating capital.

The Design Lab agrees with this direction, with one qualification: **higher company growth is not identical to a better investment opportunity** because valuation, probability, timing, downside, uncertainty, and portfolio context may materially change the investment result.

## 2. Refined Comparison Question

The stronger Comparison question is:

> **Given plausible future states of Reality, which investment has the stronger forward opportunity from current conditions, and is the relative opportunity gap large and credible enough to matter for portfolio allocation or rotation?**

This extends, rather than replaces, the current maintained judgments.

## 3. Refined Comparison Architecture

```text
Company A Current Judgment
        ↓
Plausible Future Scenarios
        ↓
Growth / Value Outcomes
        ┐
        │
        ├── Relative Future Opportunity
        │
        ┘
Company B Current Judgment
        ↓
Plausible Future Scenarios
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
Is rotation worth considering?
```

Comparison therefore should not stop at `A is stronger than B today`.

## 4. Future Scenario Layer

The experience should support multiple plausible futures rather than one precise future forecast.

For example:

```text
Base scenario
IREN — AI infrastructure expansion continues; power advantage remains relevant
NBIS — neocloud expansion continues; utilization remains strong

Upside scenario
IREN — major contracts + power scarcity revaluation
NBIS — rapid capacity expansion + sustained utilization

Downside scenario
IREN — build delays / financing pressure
NBIS — hyperscaler competition / capital intensity / concentration risk
```

The exact number and methodology of scenarios are not fixed by this Design work.

The Design goal is to make visible:

- what future state is being considered;
- which conditions must hold;
- what would make the scenario less applicable;
- how each company responds under that state;
- where growth / value outcomes diverge;
- and what uncertainty prevents overconfidence.

## 5. Relative Opportunity, Not Growth Alone

A company expected to grow faster is not automatically the better investment.

Comparison should distinguish at least conceptually:

```text
Expected business growth
+ durability / probability of that growth
+ valuation already priced in
+ capital requirements / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity` is a working Design phrase, not an approved Research concept.

The product should avoid presenting a single growth forecast as equivalent to expected investment return.

## 6. Conditions Rather Than False Precision

The preferred representation is currently:

```text
Possible Future
→ Conditions
→ Company-specific response
→ Relative outcome
→ What evidence is moving us toward / away from this future?
```

rather than defaulting to:

```text
IREN growth = 31.5%
NBIS growth = 47.2%
→ NBIS wins
```

Precise forecasts may be used where Research methodology warrants them, but their probability, uncertainty, and epistemic credibility must remain distinguishable.

## 7. Rotation Threshold / Relative Opportunity Gap

Comparison should support a practical downstream question:

> **Is the alternative merely somewhat better, or better enough to justify changing the portfolio?**

A working interaction concept is `Relative Opportunity Gap`.

Possible qualitative states:

```text
Alternative slightly better
→ current holding may remain reasonable

Alternative materially better
+ sufficiently strong supporting evidence
+ valuation remains attractive
→ rotation deserves deeper review

Alternative potentially much better
but uncertainty high
→ watch / wait / gather evidence

Current holding weakens
+ alternative opportunity strengthens
→ rotation case becomes stronger
```

This is not yet an investment-decision rule or threshold methodology.

## 8. Design Boundary with Research Lab

Design Lab should not define the authoritative methodology for:

- scenario construction;
- predictive probability;
- forecast calibration;
- expected growth / return estimation;
- valuation-outcome mapping;
- probability weighting;
- uncertainty aggregation; or
- the epistemic evaluation of predictive / comparative claims.

The Research Lab Evaluation Methodology already states that probability in a predictive Claim is not equivalent to credibility, and that predictive models may require calibration and out-of-sample evaluation appropriate to purpose and context.

Therefore this work creates a **Research Trigger Candidate**:

> **What Research methodology should produce and evaluate future scenarios, predictive growth/value outcomes, and relative opportunity comparisons strongly enough for downstream Design and portfolio decision support?**

Design can continue exploring how such outputs should be understood and compared, but must not silently invent their epistemic methodology.

## 9. Working Findings

### 9.1 Comparison must be forward-looking

Current judgment comparison alone is insufficient for realistic investment rotation decisions.

**Recommendation Strength:** Strong.

### 9.2 Scenario structure is preferable to one deterministic future

Multiple conditional futures preserve uncertainty and make the reasoning easier to challenge and update.

**Recommendation Strength:** Strong.

### 9.3 Growth should not be the sole optimization variable

The relevant object is closer to forward investment opportunity under current price and uncertainty than raw business growth.

**Recommendation Strength:** Strong.

### 9.4 Rotation requires a meaningful relative gap

A small apparent advantage should not automatically imply portfolio churn.

**Recommendation Strength:** Strong.

## 10. Failure / Reversal Conditions

Revise this direction if later Research or user testing shows that:

- scenario representations create more false confidence than transparency;
- users cannot compare conditional futures efficiently;
- simpler forward metrics provide equivalent judgment quality with much lower cognitive cost;
- relative-opportunity framing encourages excessive portfolio turnover;
- current valuation / uncertainty cannot be combined legibly without misleading scalar compression; or
- Research methodology indicates a materially different epistemic structure for forward comparison.

## 11. CEO Critical Decision

**None at this stage.**

The CEO has agreed that forward-looking growth and future-state comparison should be included in the Comparison problem. This remains a Working Comparison architecture rather than an approved top-level product optimization principle.

A future proposal to define Stock_vis Portfolio Experience around continuous relative-opportunity optimization would be consequential enough to require explicit CEO review.
