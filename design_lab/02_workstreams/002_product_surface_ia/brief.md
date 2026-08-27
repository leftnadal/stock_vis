# Workstream 002 — Product Surface / Information Architecture Exploration

**Status:** Active / Working  
**Opened:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 by default; escalate major mental-model / IA commitments when consequential

> Korean companion: [`brief_ko.md`](brief_ko.md)

## 1. Purpose

Translate the Research-aligned Workstream 001 Design Foundation into a coherent **Product Surface and Information Architecture** without prematurely fixing screen names, navigation, or implementation.

The workstream asks:

> **Which user purposes, objects, and transitions should be owned by distinct product surfaces, and which should remain integrated, so that Stock_vis supports orientation, maintained Investment Views, Research exploration, comparison, and downstream Judgment / Decision with the lowest necessary cognitive fragmentation?**

## 2. Upstream Constraints

This workstream must respect:

- Stock_vis Ultimate Purpose — `Better Investment Decisions`;
- Design Lab working direct purpose — `Better Investment Judgment`;
- Workstream 001 Research-aligned Working Design Foundation;
- `DL-DR-0001 — Human–AI Judgment Authority Boundary`;
- `DL-DR-0002 — Cross-Lab Judgment Semantic Boundary`;
- Research Lab semantic authority, especially:

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

The persistent pre-Decision-Context Design-side object is currently referred to as **Investment View** only as a Working label.

## 3. Problems to Resolve

### 3.1 Orientation

Where does a user answer:

- What deserves attention now?
- What changed materially?
- What is quiet?
- Which unresolved issue is becoming consequential?

### 3.2 Company / Investment Workspace

Where does a user:

- understand a company;
- inspect System Synthesis;
- form or maintain an Investment View;
- inspect drivers, risks, uncertainty, conditions, provenance, and history;
- review material changes?

### 3.3 Research Exploration

Should deeper evidence, relationships, scenarios, industries, and chains be embedded in the company workspace, opened as contextual layers, or live in a separate exploratory surface?

Historical names such as `ChainSight` remain hypotheses, not commitments.

### 3.4 Portfolio and Decision Context

Where should portfolio exposure, horizon, alternatives, constraints, opportunity cost, switching costs, valuation, and other decision-specific context enter the experience?

The IA must not silently treat portfolio context as intrinsic company truth.

### 3.5 Comparison / Opportunity

Where should users compare:

- current company views;
- future scenarios;
- growth-path conditions;
- valuation / uncertainty;
- asymmetric risks;
- relative opportunity; and
- whether a gap is large enough to justify deeper rotation judgment?

### 3.6 Discovery

Does discovery require its own surface, or should it emerge through search, relationships, comparison, watchlists, and opportunity-oriented orientation?

## 4. Starting Surface Hypotheses — Not IA Decisions

Prior Stock_vis discussions mentioned:

- Dashboard;
- Company / Thesis-like surface;
- Portfolio;
- Comparison / Discovery;
- ChainSight / relationship exploration;
- News / Evidence Context.

None are assumed to deserve independent top-level navigation.

The workstream should test whether some are:

- primary surfaces;
- modes within another surface;
- cross-cutting capabilities;
- contextual overlays;
- or unnecessary duplication.

## 5. Candidate IA Families to Explore

At minimum, challenge these competing families:

### A. Surface-per-Task

Dashboard / Company / Research / Portfolio / Compare / Discover as distinct destinations.

### B. Company-Centered Workspace

Company workspace is the dominant object; most research, view maintenance, evidence, and comparison launch from it.

### C. Portfolio / Decision-Centered

Portfolio and active decision questions become the main organizing layer; company research is subordinate.

### D. Object + Context Hybrid

A small number of persistent objects / workspaces — likely Orientation, Investment / Company, Portfolio / Decision Context — with Research, Comparison, Evidence, and Change Review operating as contextual capabilities rather than independent destinations by default.

No family is preferred in advance.

## 6. Stress-Test Scenarios

The IA should be tested against at least:

1. 3-minute morning portfolio review;
2. opening a company for the first time;
3. maintaining a long-held company view after mixed earnings;
4. investigating why a material change occurred;
5. comparing current holding vs new alternative;
6. exploring an industry / relationship chain that spans multiple companies;
7. user has no portfolio yet;
8. user follows 50+ names but actively holds only a few;
9. mobile constrained-attention use;
10. System Synthesis and user-owned view materially disagree.

## 7. Evaluation Dimensions

Compare IA alternatives on:

- orientation speed;
- continuity of Investment View;
- context switching / navigation cost;
- duplication of information;
- clarity of object ownership;
- Research ↔ Design semantic consistency;
- progressive disclosure;
- novice / expert scalability;
- comparison / rotation support;
- portfolio-context separation;
- mobile adaptability;
- risk of AI authority confusion;
- long-term extensibility.

## 8. Research / Evidence Boundary

This workstream may benchmark current financial research / investment products and relevant IA patterns.

It must not infer that competitor prevalence establishes correctness.

If IA exploration exposes a missing Research concept or methodology, record it as a Research Trigger Candidate rather than redefining Research semantics.

## 9. Expected Outputs

- competing IA architectures;
- surface responsibility map;
- entry / transition model;
- scenario stress-test;
- low-fidelity IA / navigation prototypes where useful;
- recommended working architecture;
- explicit retained alternatives and reversal conditions;
- CEO Critical Decision only if a major product mental model / IA boundary needs commitment.

## 10. Non-Decisions

Opening this workstream does not approve:

- a final Dashboard;
- top navigation labels;
- final Company page architecture;
- a permanent Thesis surface;
- ChainSight as a top-level product surface;
- Portfolio as the universal home;
- a final Comparison screen;
- final mobile navigation;
- visual design or design-system architecture.

## 11. Working Principle

> **Create separate surfaces only when they own a meaningfully distinct user purpose, persistent object, or interaction mode that cannot be served clearly with lower fragmentation inside an existing surface.**

This is a Working IA heuristic, not yet Approved Design Knowledge.
