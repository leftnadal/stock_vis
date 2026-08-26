# Workstream 001 — Exploration Batch 05

## Low-Fidelity Wireflow / Prototype Exploration

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — reversible prototype architecture under approved DL-DR-0001

## 1. Purpose

This batch translates the Batch 04 interaction architecture into low-fidelity user flows. The goal is not visual styling. It is to determine which interaction structure best supports rapid orientation, maintained judgment, evidence traceability, and human–AI authority without creating review fatigue.

The batch compares two prototype families:

- **Prototype A — State-centered + explicit Change Review**
- **Prototype B — Judgment Home + integrated change diff**

and then tests whether a hybrid refinement performs better across five realistic scenarios.

The approved `DL-DR-0001 — Human–AI Judgment Authority Boundary` remains a hard constraint.

## 2. Prototype A — State-Centered + Explicit Change Review

### Core wireflow

```text
Portfolio / Orientation
    ↓ select material change or company
Judgment Snapshot
    ├─ inspect component → Component Detail → Evidence / Trace
    └─ review material change → Focused Change Review
                                ↓
                      adopt / modify / reject /
                      retain / defer / unresolved
                                ↓
                       Updated User Judgment
                                ↓
                             History
```

### Low-fidelity screen contract

#### A1. Orientation

```text
TODAY — 3 ITEMS MAY DESERVE ATTENTION

IREN        -14% price move
             System: no material thesis change detected
             Why look: volatility / valuation changed

NVDA        Earnings
             2 judgment components affected
             Demand ↑ / Margin uncertainty ↑

CEG         Regulatory filing
             1 core risk may have weakened
```

The entry point communicates **why attention is warranted**, not merely event magnitude.

#### A2. Judgment Snapshot

```text
IREN — CURRENT JUDGMENT

AI demand                     Strong / stable
Power advantage               Moderate / stable
Execution                     Moderate / watch
Valuation                     Improved after price decline

Recent material judgment change: None
Open uncertainty: build timing
System ↔ My View divergence: Execution

[Review latest change]   [Explore judgment]
```

#### A3. Focused Change Review

```text
WHAT CHANGED?
Q2 earnings + guidance

WHAT DOES IT BEAR ON?
Demand             strengthened
Execution          weakened
Margins            unresolved

WHY?
[3 supporting inputs] [2 challenging inputs]

SYSTEM SYNTHESIS UPDATE
Demand: stronger
Execution: weaker

MY CURRENT VIEW
Demand: moderate
Execution: unchanged

For material user-state changes only:
[Adopt] [Modify] [Keep my view] [Leave unresolved]
```

### Strengths

- strong separation between event and judgment impact;
- excellent for multi-component changes;
- explicit provenance and update lineage;
- clear point for material human action;
- strong disagreement handling.

### Weaknesses

- creates an extra interaction step for simple changes;
- can become an inbox / approval workflow if overused;
- may over-formalize routine monitoring;
- new-company formation does not naturally begin with a change review.

## 3. Prototype B — Judgment Home + Integrated Diff

### Core wireflow

```text
Portfolio / Search
    ↓
Judgment Home
    ├─ current components
    ├─ recent change badges / inline diffs
    ├─ system ↔ user divergence markers
    └─ expand component → evidence / history / edit
```

There is no separate Change Review by default.

### Low-fidelity screen contract

```text
NVDA — JUDGMENT

Demand       ↑ strengthened
             New: hyperscaler capex evidence
             My view: adopted
             [Why?]

Margins      ? more uncertain
             New: mix / cost evidence conflicts
             My view: unresolved
             [Review evidence]

Execution    stable

Recent event: Q2 earnings
[See full event impact]
```

### Strengths

- fewer transitions;
- judgment remains the organizing object at all times;
- fast for simple changes;
- easier learning model;
- lower risk of review-inbox fatigue.

### Weaknesses

- complex events can scatter across multiple cards;
- users may miss the causal story linking one event to several components;
- material system proposals can visually blend into current judgment;
- history / provenance may become fragmented;
- high-consequence disagreement needs a stronger focused interaction anyway.

## 4. Five-Scenario Stress Test

### Scenario 1 — Sharp price decline, no thesis-changing evidence

**User need:** quickly determine whether the drawdown changes the investment judgment or merely price / valuation / urgency.

**Prototype A**

```text
Orientation: IREN -14%
→ Snapshot: no material thesis change
→ optional focused review only if user wants evidence
```

A full Change Review is unnecessary and would create friction.

**Prototype B**

```text
IREN Judgment Home
Price trigger badge: -14%
Thesis components: unchanged
Valuation: improved
[Why no thesis change?]
```

**Result:** B is better for this low-complexity case.

**Design implication:** not every trigger should open a dedicated review.

---

### Scenario 2 — Mixed earnings: some drivers improve, others weaken

**User need:** understand a single event that affects several judgment components in different directions.

**Prototype A**

A focused Change Review preserves the event as one causal unit, summarizes affected components, then allows component-level drill-down.

**Prototype B**

Inline diffs are fast but the user must reconstruct the cross-component story from separate cards.

**Result:** A is clearly stronger.

**Design implication:** multi-component or conflicting events justify a focused review mode.

---

### Scenario 3 — System and user materially disagree

Example:

```text
System: Execution thesis weakened
User: Execution thesis unchanged
```

**Prototype A**

Focused review can make the disagreement, contrary evidence, and user response explicit without permanently duplicating the full state.

**Prototype B**

A divergence marker works for orientation, but resolving / retaining the disagreement requires a deeper local interaction.

**Result:** A is stronger at the consequential moment; B is sufficient for passive visibility.

**Design implication:** disagreement should be lightweight while dormant and focused when reviewed.

---

### Scenario 4 — Previously unfamiliar company

**User need:** form an initial judgment rather than update a prior one.

**Prototype A**

A change-centric path is awkward unless the user bypasses Change Review and enters a system-generated initial Judgment Snapshot.

**Prototype B**

A Judgment Home naturally supports initial formation: system synthesis proposes drivers, risks, uncertainty, and questions; the user selectively forms a user-owned view.

**Result:** B is stronger for formation.

**Design implication:** initial formation should enter through Judgment Snapshot / guided exploration, not a synthetic “change from nothing” workflow.

---

### Scenario 5 — Morning review across many holdings

**User need:** spend attention only where judgment-relevant change occurred.

The strongest pattern is neither A nor B alone.

```text
PORTFOLIO ORIENTATION

Needs review now
NVDA   Mixed earnings — 3 components affected
CEG    Regulatory change — core risk affected

Worth noting, no judgment action
IREN   -14% — thesis unchanged / valuation improved
MSFT   Filing — no material bearing detected

No meaningful change
12 holdings collapsed
```

The user opens a focused Change Review only for the first category. Low-impact changes remain inline or informational.

**Result:** hybrid is strongest.

## 5. Refined Leading Prototype — Adaptive Change Review

The two prototypes should not be treated as a binary choice.

The strongest current architecture is:

> **Persistent Judgment Home + change-driven orientation + adaptive review depth.**

A change is represented at the lightest depth that preserves its judgment meaning.

### Level 0 — Silent system maintenance

System synthesis updates internally when no user-facing attention is justified. No interruption and no user approval.

### Level 1 — Inline change annotation

Use when impact is simple, low-consequence, or does not materially change user-owned judgment.

```text
Valuation     improved
              because price fell 14%
              thesis components unchanged
```

### Level 2 — Focused Change Review

Use when one event:

- affects multiple judgment components;
- creates meaningful evidence conflict;
- produces material system–user divergence;
- may materially change user-owned judgment;
- materially changes uncertainty / conviction; or
- is difficult to understand safely as a card-level diff.

### Level 3 — Decision Context transition

Only when the user chooses to examine implications for allocation, comparison, rotation, constraints, or action.

```text
Judgment Review
      ↓ user chooses
Decision Context
      ↓
compare / portfolio implications / possible decision
```

Judgment review does not automatically become a buy/sell recommendation.

## 6. Refined Wireflow

```text
                         PORTFOLIO / ORIENTATION
                       "Where should I look?"
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
       no material change    simple bearing     complex/material bearing
              │                   │                   │
              ▼                   ▼                   ▼
       collapsed / quiet     Inline Change       Focused Change
                              Annotation             Review
                                  │                   │
                                  └────────┬──────────┘
                                           ▼
                                  JUDGMENT SNAPSHOT
                               "Where do I stand now?"
                                 │      │       │
                     inspect ────┘      │       └── divergence
                                        │
                                        ▼
                                COMPONENT DETAIL
                                        │
                                        ▼
                              EVIDENCE / PROVENANCE
                                        │
                         optional, user-initiated only
                                        ▼
                                 DECISION CONTEXT
```

This removes the assumption that every change deserves its own page or confirmation step.

## 7. Material Interaction Contract

The prototype should preserve the following distinctions.

### 7.1 Attention ≠ Approval

A surfaced item means `this deserves attention`, not `please approve the AI's conclusion`.

### 7.2 System update ≠ User judgment update

The system may update System Synthesis without asking the user. A material user-owned state change must respect DL-DR-0001.

### 7.3 No response ≠ agreement

If the user does not review a system proposal, the product must not silently mark it as user-adopted.

### 7.4 Retain is meaningful

`I reviewed the evidence and kept my view` must remain distinguishable from `not reviewed`.

### 7.5 Unresolved is a legitimate state

The user or system may conclude that evidence is currently insufficient or conflicting. The interface must not force strengthen / weaken when unresolved is the more faithful state.

## 8. Prototype Information Priority

### Portfolio / Orientation

Default priority:

1. changes with material bearing on current judgment;
2. unresolved conflict / uncertainty that became more consequential;
3. system–user divergence that is newly material;
4. user-requested monitoring conditions;
5. raw price / news / filing activity only when useful as context or trigger.

This is intentionally different from a chronological news feed.

### Judgment Snapshot

Default priority:

1. current material components;
2. what materially changed since last meaningful review;
3. unresolved / weak areas;
4. material system–user divergence;
5. deeper evidence and history on demand.

## 9. Competitive Implication

Current research platforms increasingly support alerts, automated monitoring, thesis checking, cited synthesis, and agentic research workflows. AlphaSense, for example, now exposes thesis validation / refresh / postmortem agents and automatically updated outputs; Koyfin supports watchlist / portfolio alerts integrated with the research workflow.

References:

- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/53942181071123-AlphaSense-Product-Updates-July-2026
- https://www.koyfin.com/features/alerts/

Therefore, Stock_vis should not assume differentiation from alerts or AI synthesis alone. The more distinctive interaction hypothesis remains **maintaining a traceable judgment state and translating new information into explicit judgment impact over time**.

This remains a product hypothesis, not an approved competitive claim.

## 10. Failure / Reversal Conditions

The adaptive architecture should be revised if prototype testing shows that:

- users cannot understand the difference between inline annotation and focused review;
- adaptive review depth makes the interface feel unpredictable;
- users miss important changes because the system hides too much;
- too many items are classified as focused reviews, recreating an inbox;
- a single integrated Judgment Home communicates complex change just as well with materially lower interaction cost;
- users cannot tell whether a system proposal was adopted into their own view;
- initial formation and ongoing monitoring require fundamentally different surfaces rather than a shared Judgment model.

## 11. Batch Consensus

### Recommended Working Prototype

Adopt **Persistent Judgment Home + Change-Driven Orientation + Adaptive Change Review** as the leading low-fidelity prototype direction.

**Recommendation Strength:** Strong.

### Why

It preserves the strongest benefits of both tested architectures:

- low friction for simple or non-material changes;
- focused causal understanding for complex / consequential changes;
- maintained judgment as the durable organizing object;
- strong compatibility with DL-DR-0001;
- no requirement to create a product-level approval inbox;
- natural support for both initial formation and ongoing monitoring.

### Main Alternative

A single Judgment Home with all changes expressed inline remains the strongest simplification candidate and should be retained as a prototype comparator.

### Deferred / AI-Owned

- exact thresholds for Level 1 vs Level 2 review;
- exact card / page / drawer representation;
- default number of visible components;
- labels such as `Review`, `Impact`, `My View`, `System View`;
- mobile vs desktop transition patterns;
- animation, iconography, color, and visual system;
- exact microcopy for adopt / retain / unresolved states.

## 12. CEO Critical Decision

**None in this batch.**

The architecture remains a reversible prototype direction within the already approved Human–AI judgment authority boundary.

## 13. Next Prototype Step

The next step should move from abstract wireflow to **one concrete end-to-end low-fidelity prototype scenario**, using realistic but non-authoritative sample data.

Recommended first prototype scenario:

> **A held stock experiences a sharp price decline followed by mixed earnings evidence.**

This single scenario tests:

- low-impact trigger handling;
- transition from inline annotation to focused review;
- multi-component judgment change;
- uncertainty;
- system–user disagreement;
- evidence drill-down;
- user-owned revision; and
- update lineage.

A second comparator prototype should implement the same scenario using the simplified all-inline Judgment Home.