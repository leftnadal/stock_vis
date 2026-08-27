# Workstream 001 — Exploration Batch 06

## Generalization Stress Test — Formation, Morning Review, and Comparison

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — reversible interaction-architecture refinement under approved DL-DR-0001

## 1. Purpose

This batch tests whether the current leading architecture from Batch 05 generalizes beyond the narrow case of updating an existing holding.

Three scenarios are used as adversarial tests:

1. **First-time company / initial judgment formation** — there is no prior maintained user judgment.
2. **Three-minute morning portfolio review** — the user must allocate attention across many holdings quickly.
3. **Comparison / possible rotation** — two investments must be evaluated relative to each other under decision context.

The goal is not to finalize product navigation or screen names. It is to determine whether one coherent judgment architecture can support formation, maintenance, updating, monitoring, and comparison without collapsing them into one overloaded surface.

`DL-DR-0001 — Human–AI Judgment Authority Boundary` remains an approved constraint.

## 2. Evidence and Pattern Review

### 2.1 Portfolio monitoring products already optimize alerts and watchlists

Current investment platforms already provide watchlist / portfolio alerts, configurable dashboards, and side-by-side comparison. Koyfin supports alerts across portfolios and watchlists, custom watchlist views, and investment comparison. AlphaSense has expanded automated monitoring, large-watchlist generative search, and investment-thesis workflow agents.

References:

- https://www.koyfin.com/features/alerts/
- https://www.koyfin.com/features/watchlists/
- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026

**Working implication:** Stock_vis should not treat alert aggregation or side-by-side metric comparison as the distinctive core. The stronger hypothesis remains prioritizing changes by judgment bearing and preserving a traceable judgment state across time.

### 2.2 Comparison support must match task complexity

Decision-support research suggests that comparison aids help when they reduce scattered information and structure relevant dimensions, but overly strong or poorly matched decision support can reduce elaboration or encourage simplistic strategies.

References:

- Tan, Teo & Benbasat, *Assessing Screening and Evaluation Decision Support Systems: A Resource-Matching Approach*, Information Systems Research (2010).
- Frontiers in Psychology (2025), computer-based decision aids and cognitive load: https://doi.org/10.3389/fpsyg.2025.1576319

**Working implication:** Stock_vis comparison should reduce extraneous comparison effort without replacing the user's trade-off judgment with a single automatic ranking.

## 3. Scenario A — First-Time Company / Judgment Formation

### Problem

The user opens a company with no prior personal judgment. A change-centric architecture has nothing to update.

### Failure of a literal Adaptive Change Review model

If the product begins with `What changed?`, the interaction assumes a prior state that does not exist. Creating an artificial "initial change" would distort the mental model.

### Stronger formation flow

```text
Discovery / Search
      ↓
Initial System Synthesis
      ↓
Judgment Formation Workspace
      ├─ material drivers / claims
      ├─ risks / invalidation conditions
      ├─ unresolved uncertainty
      ├─ important evidence / provenance
      └─ questions worth exploring
      ↓
User explores / challenges / asks questions
      ↓
Optional partial User Judgment formation
      ↓
Maintained Judgment State
```

### Critical interaction finding

**The absence of an explicit User Judgment must be a valid state.**

The user should not be forced to manufacture a thesis merely because the system has synthesized one. The system may maintain an Initial System Synthesis while the user remains:

- no explicit view yet;
- partially formed view;
- unresolved on selected components; or
- explicitly disagreeing with the system.

This preserves DL-DR-0001 without imposing manual thesis maintenance.

### Progressive formation

The first view should not expose the full semantic structure. A stronger starting pattern is:

```text
What matters most?
What could break the case?
What remains unknown?
What changed recently that matters?
```

These are access questions into the underlying structure, not the structure itself.

### Result

**The architecture survives only if "Change Review" is treated as one adaptive mode inside a broader Judgment Workspace, not as the foundation itself.**

## 4. Scenario B — Three-Minute Morning Portfolio Review

### Problem

A user with many holdings cannot open a full Judgment Home for every company each morning.

The core task is not deep judgment formation. It is **attention allocation**.

### Leading orientation model

```text
MORNING REVIEW

Needs judgment review now
NVDA   Mixed earnings — 3 material components affected
CEG    Regulatory change — core risk may be altered

Worth noting, no judgment action implied
IREN   -14% — thesis unchanged / valuation improved
MSFT   Filing — no material bearing detected

Quiet
12 holdings — no meaningful judgment-bearing change
```

### Why this is different from an alert inbox

The primary sorting criterion is not event recency or price magnitude. It is:

- bearing on current maintained judgment;
- unresolved conflict / uncertainty becoming more consequential;
- new material system–user divergence;
- user-defined monitoring condition; and
- decision-context change when relevant.

### Key contract

**Attention item ≠ task ≠ approval request.**

Most morning-review items should be dismissible through understanding alone. A focused review opens only when the underlying change is complex or potentially material to user-owned judgment.

### Result

The architecture generalizes well if **Orientation is treated as a first-class cross-company layer** above individual Judgment Workspaces.

## 5. Scenario C — Comparing Two Investments / Possible Rotation

### Problem

The user is not merely asking whether Company A is good. The question may be:

> Is A sufficiently better than B, given my current portfolio, horizon, constraints, and opportunity cost, to justify reallocating attention or capital?

This is not the same object as either company's maintained judgment.

### Failure of naive side-by-side judgment cards

A simple matrix can create false symmetry. Two companies may have different causal structures, different key risks, and different reasons for attractiveness.

Example:

```text
IREN                         NBIS
Power advantage              Customer concentration
Build execution              AI cloud demand
Capital intensity            GPU supply access
Valuation                    Valuation
```

Forcing every component into identical rows may erase what actually matters.

### Leading comparison architecture

Comparison should be a **Decision Context / Comparison Lens** that consumes two maintained judgments without overwriting them.

```text
Judgment A ─────┐
                ├── Comparison / Decision Context
Judgment B ─────┘        │
                         ├─ shared relevant dimensions
Portfolio / horizon ─────┤
Constraints ─────────────┤
Opportunity cost ────────┘
                         ↓
              Relative trade-off structure
```

### Comparison should prioritize decision-relevant questions

Instead of a universal score, the experience should help answer:

- Where does A have a meaningful advantage over B?
- Where does B have a meaningful advantage over A?
- Which differences are actually relevant to this user's decision context?
- Which uncertainties prevent a strong comparison?
- What must be true for A to be preferable to B?
- Is the difference large enough to matter, or are both within the same practical decision range?

### Shared dimensions + asymmetric dimensions

A comparison can use common dimensions when genuinely comparable, while preserving company-specific material components separately.

```text
Shared comparison
Demand durability        A > B
Execution confidence     B > A
Valuation                A > B
Uncertainty              mixed

A-specific concern
Power / build dependency

B-specific concern
Customer concentration
```

### Avoid false scalar certainty

A single `A = 82 / B = 76` score would compress heterogeneous trade-offs and uncertainty into a seemingly objective answer. The current Design direction therefore favors **relative trade-off structure before aggregate ranking**.

An aggregate recommendation may later be explored inside Decision Context, but should remain traceable to component-level reasoning and uncertainty.

### Result

The architecture generalizes if Comparison is **not forced into the Judgment Home**. It should be a downstream, cross-cutting Decision Context capability that uses maintained judgments as inputs.

## 6. Architecture Revision

The name `Adaptive Change Review` is now too narrow to describe the foundational experience.

The stronger generalized architecture is:

> **Persistent Judgment Workspace + Attention-Oriented Orientation + Adaptive Review + Decision Context**

Working logical architecture:

```text
                       ORIENTATION
              "Where should I look?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company   Cross-company need
         │                │                │
         ▼                ▼                ▼
   FORMATION MODE    MAINTENANCE MODE   DECISION CONTEXT
         │                │            comparison / portfolio
         │       ┌────────┴────────┐
         │       │                 │
         │   simple change    complex/material
         │       │                 │
         │    inline           focused review
         │       │                 │
         └───────┴────────┬────────┘
                          ▼
                  JUDGMENT WORKSPACE
                   maintained state
                          │
                 evidence / provenance
                          │
                  update trace / history
```

### What is stable across modes

The same underlying semantic model can support:

- initial formation;
- ongoing maintenance;
- evidence-driven revision;
- system–user disagreement;
- monitoring; and
- downstream comparison.

What changes is **entry point, disclosure depth, and interaction objective**, not the foundational judgment semantics.

## 7. Strong Working Findings

### 7.1 User judgment may be absent or partial

A user should not need a complete explicit view before Stock_vis can be useful.

**Recommendation Strength:** Strong.

### 7.2 Orientation is attention allocation, not a news feed

Morning review should compress quiet holdings and prioritize judgment-bearing changes rather than raw activity.

**Recommendation Strength:** Strong.

### 7.3 Comparison belongs downstream in Decision Context

Comparison should consume maintained judgments and portfolio / horizon / opportunity-cost context rather than redefining the underlying company judgment.

**Recommendation Strength:** Strong.

### 7.4 Comparison should preserve asymmetric structure

Standardized common dimensions are useful, but company-specific material drivers / risks must remain visible where necessary.

**Recommendation Strength:** Strong.

### 7.5 Avoid default total scoring

Relative trade-offs, uncertainty, and decision relevance should be legible before any aggregate rank or recommendation.

**Recommendation Strength:** Moderate–Strong.

A future prototype may show that a carefully designed aggregate layer helps orientation, but it should not erase the underlying structure.

## 8. Failure / Reversal Conditions

The generalized architecture should be revised if prototype or user testing shows that:

- users cannot understand the difference between Formation, Maintenance, and Decision Context;
- the system feels fragmented because users must move between too many modes;
- users strongly prefer one universal company page with contextual modules and can maintain orientation without explicit modes;
- morning triage hides material changes too aggressively;
- judgment-based comparison is slower or less useful than conventional metric comparison for most real decisions;
- asymmetric comparison makes evaluation harder rather than clearer; or
- users need a much more explicit recommendation / ranking layer to make practical decisions.

## 9. Batch Consensus

The current leading hypothesis should be refined from `Adaptive Change Review` to:

> **A persistent Judgment Workspace that supports Formation and Maintenance, with attention-oriented Orientation above it, adaptive review depth for changes, and Comparison / Portfolio reasoning downstream as Decision Context.**

**Recommendation Strength:** Strong.

This is still Working architecture, not approved Product IA.

## 10. CEO Critical Decision

**None in this batch.**

The batch broadens and stress-tests a reversible Tier 2 interaction architecture under the already-approved Human–AI authority boundary. No new long-term authority or major Product IA is being locked.

## 11. Deferred / AI-Owned

- final naming of Judgment Workspace / Formation / Maintenance;
- whether Formation and Maintenance are explicit modes or contextual states inside one surface;
- exact morning-review grouping and thresholds;
- comparison visual layout;
- exact shared comparison dimensions;
- whether any aggregate comparison summary is useful;
- mobile interaction details; and
- component / button naming.
