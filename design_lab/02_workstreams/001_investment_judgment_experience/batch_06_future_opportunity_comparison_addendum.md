# Workstream 001 — Batch 06 Addendum

## Future Opportunity Comparison and Rotation Context

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — working refinement to Comparison / Decision Context

## 1. Origin

CEO feedback identified an important gap in Batch 06 Comparison:

> Investors do not compare only the current quality of two companies. They also try to reason about how future conditions may evolve, which company may grow or create more investment value under those conditions, and whether the difference is large enough to justify rotating capital.

The Design Lab agrees with this direction, with one qualification: **higher company growth is not identical to a better investment opportunity** because valuation, probability, timing, downside, uncertainty, capital requirements, and portfolio context may materially change the investment result.

A second refinement followed: future growth should not be shown as if opportunity automatically converts into realized growth. The experience should expose **what enables, accelerates, constrains, delays, or invalidates the growth path, and whether company growth can actually translate into shareholder value.**

## 2. Refined Comparison Question

The stronger Comparison question is:

> **Given plausible future states of Reality, which investment has the stronger forward opportunity from current conditions, what must go right or could block that opportunity, and is the resulting relative opportunity gap large and credible enough to matter for portfolio allocation or rotation?**

This extends, rather than replaces, the current maintained judgments.

## 3. Refined Comparison Architecture

```text
Company A Current Judgment
        ↓
Plausible Future Scenarios
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
        same structure

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

Comparison therefore should not stop at `A is stronger than B today`, and should not jump directly from market opportunity to a growth forecast.

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
- what would make the scenario less applicable or invalidate it;
- how each company responds under that state;
- where growth / value outcomes diverge;
- and what uncertainty prevents overconfidence.

## 5. Growth-Path Conditions

A future market opportunity does not automatically become company growth. The comparison should distinguish conditions that play different roles in the path from opportunity to realized value.

### 5.1 Opportunity

The external or structural room for growth: market demand, industry expansion, scarcity, regulation, technology adoption, or another future state that creates potential value.

### 5.2 Enablers

Conditions that must be sufficiently present for the company to capture the opportunity.

Examples may include capacity, power, customers, financing access, supply, technology, permits, distribution, or organizational capability.

### 5.3 Accelerators

Conditions that can increase the speed, scale, or economics of growth beyond the base path.

### 5.4 Bottlenecks / Delay Conditions

Conditions that constrain the size or timing of growth without necessarily destroying the underlying opportunity.

A bottleneck should remain distinguishable from a thesis-invalidating failure. A one-year construction delay and the disappearance of customer demand are not the same type of problem.

### 5.5 Invalidation Conditions

Conditions or observations that materially undermine the scenario or a central growth mechanism rather than merely delaying it.

### 5.6 Value-Capture Conditions

Conditions that determine whether company growth becomes durable investor value rather than only larger operations or revenue.

Relevant issues may include margins, capital intensity, dilution, financing cost, competitive pass-through, reinvestment burden, and per-share value creation.

Conceptually:

```text
Market / Structural Opportunity
        ↓
Can the company capture it?
        ↓
Can it execute at the required speed / scale?
        ↓
What constrains, delays, or invalidates the path?
        ↓
Can growth convert into durable shareholder value?
        ↓
Growth / Value Outcome
```

The precise taxonomy is Working Design structure, not an approved Research ontology.

## 6. Monitoring Link

Growth-path conditions create a natural bridge between future comparison and ongoing Judgment maintenance.

A scenario can be monitored through condition-relative signals rather than reinterpreting every event from scratch.

Example:

```text
Growth scenario

Enablers
✓ demand evidence strengthening
✓ power secured
△ execution capacity

Bottlenecks
! construction timing
△ financing / dilution risk

Invalidation
? no material evidence yet

Value capture
△ margin / capital efficiency unresolved
```

New evidence can then be interpreted as strengthening an enabler, worsening a bottleneck, moving toward an invalidation condition, or improving / weakening value capture. This should connect to the existing Judgment-Bearing Relation and Update Trace rather than create an independent prediction UI logic.

## 7. Relative Opportunity, Not Growth Alone

A company expected to grow faster is not automatically the better investment.

Comparison should distinguish at least conceptually:

```text
Expected business growth
+ growth-path conditions and durability
+ current valuation already priced in
+ capital requirements / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity` is a working Design phrase, not an approved Research concept.

The product should avoid presenting a single growth forecast as equivalent to expected investment return.

## 8. Conditions Rather Than False Precision

The preferred representation is currently:

```text
Possible Future
→ Opportunity
→ Enablers / Accelerators / Bottlenecks / Invalidation / Value Capture
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

## 9. Rotation Threshold / Relative Opportunity Gap

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

## 10. Design Boundary with Research Lab

Design Lab should not define the authoritative methodology for:

- scenario construction;
- predictive probability;
- forecast calibration;
- expected growth / return estimation;
- valuation-outcome mapping;
- probability weighting;
- uncertainty aggregation;
- causal or predictive status of proposed growth-path conditions; or
- the epistemic evaluation of predictive / comparative claims.

The Research Lab Evaluation Methodology already states that probability in a predictive Claim is not equivalent to credibility, and that predictive models may require calibration and out-of-sample evaluation appropriate to purpose and context.

Therefore this work creates a **Research Trigger Candidate**:

> **What Research methodology should produce and evaluate future scenarios, growth-path conditions, predictive growth/value outcomes, and relative opportunity comparisons strongly enough for downstream Design and portfolio decision support?**

Design can continue exploring how such outputs should be understood and compared, but must not silently invent their epistemic methodology.

## 11. Working Findings

### 11.1 Comparison must be forward-looking

Current judgment comparison alone is insufficient for realistic investment rotation decisions.

**Recommendation Strength:** Strong.

### 11.2 Scenario structure is preferable to one deterministic future

Multiple conditional futures preserve uncertainty and make the reasoning easier to challenge and update.

**Recommendation Strength:** Strong.

### 11.3 Growth path conditions should be explicit

Opportunity, realization conditions, bottlenecks, invalidation, and value capture should not be collapsed into one generic risk list.

**Recommendation Strength:** Strong.

### 11.4 Growth should not be the sole optimization variable

The relevant object is closer to forward investment opportunity under current price and uncertainty than raw business growth.

**Recommendation Strength:** Strong.

### 11.5 Rotation requires a meaningful relative gap

A small apparent advantage should not automatically imply portfolio churn.

**Recommendation Strength:** Strong.

## 12. Failure / Reversal Conditions

Revise this direction if later Research or user testing shows that:

- scenario representations create more false confidence than transparency;
- growth-path condition taxonomy adds complexity without improving judgment;
- users cannot compare conditional futures efficiently;
- simpler forward metrics provide equivalent judgment quality with much lower cognitive cost;
- relative-opportunity framing encourages excessive portfolio turnover;
- current valuation / uncertainty cannot be combined legibly without misleading scalar compression; or
- Research methodology indicates a materially different epistemic structure for forward comparison.

## 13. CEO Critical Decision

**None at this stage.**

The CEO has agreed that forward-looking growth, future-state comparison, and explicit growth-blocking conditions should be included in the Comparison problem. This remains a Working Comparison architecture rather than an approved top-level product optimization principle.

A future proposal to define Stock_vis Portfolio Experience around continuous relative-opportunity optimization would be consequential enough to require explicit CEO review.
