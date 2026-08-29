# Workstream 002 — Batch 01: Surface Responsibility & IA Families

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; not Approved Product IA

> Korean companion: [`batch_01_surface_architecture_ko.md`](batch_01_surface_architecture_ko.md)

## 1. Batch Question

> **What should Stock_vis treat as persistent product spaces versus contextual capabilities so that users can orient, understand an investment, maintain an Investment View, explore Research, and enter downstream Decision Context without navigating a collection of disconnected tools?**

## 2. Current Stock_vis Implementation as Evidence, Not Authority

The current frontend has accumulated a feature-oriented navigation model.

Desktop global navigation currently exposes:

- Dashboard;
- Market Pulse;
- Chain Sight;
- News;
- Screener;
- Guide;
- My.

The `My` area then contains:

- Watchlist;
- Monitor;
- Coach;
- Wallet;
- Portfolio.

Mobile navigation similarly exposes Home, Market Pulse, Chain Sight, News, Guide, and My.

This reflects useful product history and working functionality, but it also creates a potential IA failure:

> **the user must understand which feature contains the answer before the product helps answer the investment question.**

The Design Lab should therefore treat existing routes as implementation evidence, migration constraints, and prototype material — not as the desired future IA.

## 3. Current External Benchmark Signals

### AlphaSense

Current AlphaSense documentation describes:

- **Dashboard** as a customizable monitoring interface for a coverage universe; and
- **Company Profile** as a central hub for researching a single company, combining financial data, documents, summaries, commentary, peers, and Generative Search.

This supports a useful separation between **cross-object orientation / monitoring** and **single-company deep work**.

It does not prove Stock_vis should copy the same IA, because AlphaSense optimizes professional research workflows rather than Stock_vis's specific Better Investment Judgment purpose.

### Koyfin

Koyfin currently provides distinct but highly interoperable tools for dashboards, watchlists, portfolios, financial analysis, screeners, news, alerts, and charts. Watchlists can appear in dashboards, portfolio data can be surfaced in watchlists, and alerts connect monitoring to those objects.

This demonstrates the power of composable tools and user customization, but also represents a largely **tool / data-workbench model**. Stock_vis may need a stronger semantic center around maintained Investment Views and downstream Judgment rather than simply offering a richer toolkit.

### FinChat

FinChat's current public developer material emphasizes company data, financial datasets, company-specific AI prompts, generative AI / Copilot interaction, and card-based data rendering.

This is useful evidence that AI / company context can act as a cross-cutting access mechanism. It does not by itself solve persistent user-view continuity or portfolio Decision Context.

## 4. Candidate IA Family A — Surface per Task / Feature

```text
Dashboard
Market
News
Research / Chain
Screener / Discover
Company
Portfolio
Compare
AI
```

### Strengths

- each capability is easy to name and build independently;
- familiar to power users of financial terminals / tools;
- teams can evolve features locally;
- current Stock_vis implementation is already relatively close.

### Failures

- information and context are duplicated across surfaces;
- the user must choose the tool before understanding the problem;
- maintained Investment View continuity is weak;
- change, evidence, research, and comparison can fragment into separate destinations;
- mobile navigation becomes crowded;
- feature growth naturally expands navigation indefinitely.

### Current assessment

**Not preferred as the foundational IA.**

It may remain appropriate for secondary utilities and advanced tools.

## 5. Candidate IA Family B — Company-Centered Workspace

```text
Orientation
   ↓
Company / Investment Workspace
   ├─ View
   ├─ Changes
   ├─ Evidence
   ├─ Financials
   ├─ Relationships
   ├─ Scenarios
   └─ Compare launch
```

### Strengths

- excellent Investment View continuity;
- strong object ownership;
- Research, evidence, change, and history can remain contextual to the company;
- naturally supports progressive disclosure.

### Failures

- weak for cross-company morning orientation;
- industry / macro / relationship exploration may feel trapped inside company context;
- portfolio allocation and rotation are not company-local problems;
- comparison becomes an awkward jump between objects;
- users with 50+ followed companies need a stronger cross-object layer.

### Current assessment

**Strong company-level architecture, insufficient as the whole product IA.**

## 6. Candidate IA Family C — Portfolio / Decision-Centered

```text
Portfolio / Active Decisions
   ↓
Holdings / Opportunities
   ↓
Company Research
```

### Strengths

- directly connected to capital allocation;
- comparison / rotation becomes natural;
- strong for existing investors with active portfolios;
- Decision Context is explicit rather than hidden.

### Failures

- users with no portfolio or only exploratory interest have no natural home;
- risks pushing the product too quickly from Understanding to Decision;
- can distort company information around current holdings;
- new ideas / industry exploration become subordinate to current portfolio;
- may encourage excessive action or turnover.

### Current assessment

**Important downstream mode, not preferred as the universal organizing center.**

## 7. Candidate IA Family D — Object + Context Hybrid

Current leading family:

```text
                    ORIENTATION
             What deserves attention?
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
 INVESTMENT         RESEARCH /       DECISION
 WORKSPACE           EXPLORE          CONTEXT
 company object      contextual       portfolio / compare
       │              capability            │
       │                   ┌─────────────────┘
       └───────────────────┤
                           ▼
                        JUDGMENT
                           ↓
                        DECISION
```

The labels above are conceptual roles, not final navigation labels.

### Persistent spaces / objects

#### 1. Orientation space

Owns:

- what deserves attention now;
- cross-company meaningful change;
- unresolved / divergence escalation;
- quiet state compression;
- entry into relevant company / research / decision context.

It should not become a generic market-news dashboard by default.

#### 2. Investment / Company Workspace

Owns:

- System Synthesis;
- user-owned Investment View;
- Formation / Maintenance;
- change review;
- drivers / conditions / risks / uncertainty;
- evidence and provenance access;
- revision history;
- company-local scenarios and relationships.

This is the strongest persistent semantic object found so far.

#### 3. Portfolio / Decision Context space

Owns decision-specific context rather than intrinsic company truth:

- holdings / exposure;
- time horizon;
- constraints;
- alternatives;
- opportunity cost;
- valuation in the current decision question;
- allocation / rotate / add / reduce questions;
- comparative Judgment preparation.

### Contextual capabilities, not necessarily top-level spaces

#### Research / Explore

May open from any object / question and include:

- evidence;
- documents;
- relationship / Chain exploration;
- industry context;
- scenarios;
- AI questions;
- deep search.

A later stress test must determine whether cross-object exploration is important enough to deserve its own persistent global space.

#### Comparison

Current hypothesis: **a mode / workspace created around a Decision Context**, not a permanent top-level destination by default.

A comparison may be launched from a company, portfolio, opportunity, or research result.

#### Change Review

Adaptive interaction inside Orientation / Investment Workspace rather than a universal inbox.

#### Discovery / Screener

Currently better treated as an opportunity-generation capability rather than automatically as top-level IA. However, this is still weakly tested and could require a distinct Explore / Discover space.

## 8. Scenario Stress Test

| Scenario | A Task/Feature | B Company | C Portfolio | D Hybrid |
|---|---|---|---|---|
| 3-min morning review | Moderate | Weak | Strong for holdings | **Strong** |
| New company | Moderate | **Strong** | Weak | **Strong** |
| Mixed earnings maintenance | Fragmented | **Strong** | Moderate | **Strong** |
| Deep evidence / chain investigation | Strong but separate | Moderate–Strong | Weak | **Strong if contextual exploration works** |
| Holding vs alternative rotation | Moderate | Weak–Moderate | **Strong** | **Strong** |
| No portfolio yet | Strong | Strong | Weak | **Strong** |
| 50+ watch names | Moderate | Weak | Moderate | **Strong orientation layer** |
| Mobile | Weak as features grow | Moderate | Moderate | **Potentially strongest** |
| System–User divergence | Fragmented | Strong | Moderate | **Strong** |

This table is a Design Lab synthesis, not user-test evidence.

## 9. Strongest Counterargument to the Hybrid

The hybrid risks becoming conceptually elegant but operationally vague.

If `Research / Explore`, `Comparison`, `Change Review`, and `Discovery` are all contextual capabilities, users may struggle to predict where to find them, and implementation may create many hidden modes inside a few overloaded surfaces.

A simpler feature-oriented IA can sometimes improve findability because every tool has a stable named destination.

Therefore the hybrid should only survive if the next prototype can demonstrate:

- predictable entry points;
- stable object identity;
- low hidden-mode confusion;
- efficient cross-object exploration; and
- mobile viability.

## 10. Current Working Recommendation

### Recommendation

Advance **Object + Context Hybrid** as the leading IA family while retaining two explicit challengers:

1. **Company-Centered + dedicated Explore**;
2. **Hybrid + a persistent Explore / Discover global space**.

### Recommendation Strength

**Strong**

### Why

It best preserves Workstream 001's semantic architecture while avoiding a top navigation that expands with every feature.

It also gives distinct ownership to the three major purposes that repeatedly survived stress tests:

- cross-object **Orientation**;
- persistent **Investment / Company View**;
- downstream **Decision Context**.

Research, evidence, change review, AI, comparison, and discovery can then be tested as capabilities around those purposes rather than assumed to require separate top-level destinations.

## 11. Failure / Reversal Conditions

Revise the recommendation if prototypes show that:

- contextual capabilities are difficult to discover;
- the Investment Workspace becomes a monolithic overloaded page;
- cross-object Research / Chain exploration lacks a stable home;
- users repeatedly want a dedicated discovery workflow;
- Decision Context cannot remain understandable without a persistent Comparison destination;
- mobile navigation needs a materially different information architecture rather than a responsive form of the same one; or
- existing implementation migration cost materially outweighs the expected judgment benefit.

## 12. CEO Critical Decision

**None in Batch 01.**

The recommendation is a reversible IA family hypothesis. A future decision about the major persistent product spaces or top-level navigation may become CEO Critical after prototype and scenario validation.

## 13. Next Exploration

Create a low-fidelity **IA map / navigation prototype** that compares:

- **D1 — Hybrid without dedicated Explore**; and
- **D2 — Hybrid with Explore / Discover as a fourth persistent space**.

Stress both against:

- morning review;
- new-company research;
- cross-company relationship exploration;
- holding-vs-alternative comparison; and
- mobile navigation.
