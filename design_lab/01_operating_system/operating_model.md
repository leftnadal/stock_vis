# Stock_vis Design Lab Operating Model

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-20  
**Owner:** Stock_vis Design Lab  
**Operational Use:** Approved as a working bootstrap baseline by Project Owner on 2026-08-20

## 1. Core Operating Principle

> **The Design Lab should maximize delegated exploration while concentrating CEO attention on consequential decisions.**

The Design Lab is not organized around continuous CEO approval of small design choices. It is organized so that exploration, comparison, critique, synthesis, and reversible execution are delegated by default, while consequential decisions receive focused Project Owner attention.

## 2. Roles

### CEO / Project Owner

The CEO / Project Owner retains final authority over consequential Design Lab decisions, especially those that materially shape long-term purpose, principles, user mental models, major information architecture, authority boundaries, cross-Lab meaning, or durable dependencies.

The CEO should receive prepared decision packages rather than unfiltered intermediate exploration.

### Design Lab Lead / AI Co-researcher

The Design Lab Lead frames problems, decomposes work, selects specialist perspectives, delegates exploration, compares alternatives, tests counterarguments, checks Research consistency, synthesizes findings, determines decision consequence, escalates when required, and autonomously executes work within approved boundaries.

The Lead is not required to defend its initial proposal. Better alternatives should replace weaker proposals when evidence or critique justifies revision.

### Specialist Agents

Specialist Agents perform bounded research, design, critique, simulation, validation, or documentation tasks under a Lead-defined brief.

Agent outputs inform synthesis. They do not become authoritative decisions or Design Knowledge merely because an agent produced them.

## 3. Batch Consensus by Default

The normal collaboration unit is a coherent design question or architecture boundary, not an isolated micro-decision.

The default pattern is:

```text
Coherent Design Problem
→ delegated exploration
→ alternatives and counterarguments
→ failure / edge-case review
→ Research and Design consistency review
→ Lead synthesis
→ recommendation with recommendation strength
→ CEO decision when required
→ autonomous execution within the approved boundary
```

Micro-consensus may still be useful when a single semantic choice is itself consequential, but it is not the default working mode.

## 4. Decision Tiers

Decision tiers are determined primarily by consequence, not by labels or predefined categories. Examples are heuristics.

### Tier 1 — CEO Direct Decision

Use Tier 1 when a decision materially shapes the long-term Design Lab or Stock_vis experience and requires explicit Project Owner judgment.

Typical signals include:

- Purpose or Philosophy change;
- core Design Principle;
- major user mental model;
- major information architecture;
- human / AI authority boundary;
- material interpretation of Research Knowledge;
- cross-Lab semantic impact;
- high irreversibility or long-term dependency;
- reversal of an existing major approved direction.

Process:

```text
Explore
→ compare alternatives
→ critique and stress-test
→ synthesize
→ direct CEO discussion
→ explicit decision
```

### Tier 2 — Batch Decision

Use Tier 2 for important structural choices that benefit from broad exploration but do not require the CEO to approve every sub-decision separately.

The Lead explores and integrates the related decisions into one coherent Decision Package. CEO approval of the major direction delegates reversible detail beneath that boundary.

### Tier 3 — Delegated Decision

Use Tier 3 for reversible choices that naturally follow from approved Purpose, Principles, architecture, and guardrails.

The Lead decides and proceeds without requesting repeated approval.

If a Tier 3 task reveals a higher-consequence issue, it must be reclassified and escalated.

## 5. Consequence-Based Escalation

Escalation should consider:

- **Consequence** — how much downstream work or user experience depends on the decision;
- **Uncertainty** — how weak or contested the current basis is;
- **Irreversibility** — how difficult or costly reversal would be;
- **Semantic Reach** — how broadly the decision changes meaning across Design Knowledge or product behavior;
- **Long-term Dependency** — how many later decisions may inherit it;
- **Cross-Lab Impact** — whether Research, Product, Engineering, or other authority boundaries are affected.

Escalation is especially required when:

1. an existing approved meaning must materially change;
2. a new core Design Concept or Principle appears necessary;
3. Approved Research Knowledge may be contradicted or misrepresented;
4. a major mental model, IA boundary, or authority boundary must change;
5. a durable schema, ontology, Design System, or other long-term dependency is introduced;
6. major alternatives require an important value judgment;
7. recommendation strength is low while decision consequence is high; or
8. new evidence materially challenges a CEO-approved direction.

## 6. Recommendation Strength

Important recommendations should include an explicit strength when doing so helps the CEO interpret the recommendation.

- **Very Strong** — clearly preferred under current evidence and higher-level constraints; unlikely to reverse without important new evidence.
- **Strong** — currently preferred, but meaningful refinement or reversal remains possible through later design or testing.
- **Moderate** — preferred direction exists, but credible alternatives remain and validation may change the choice.
- **Weak / Tentative** — exploratory working proposal with limited evidence or unresolved structure.

Important recommendations should normally state:

- Recommendation;
- Recommendation Strength;
- Why;
- Main Alternative(s);
- Key Trade-offs;
- Failure / Reversal Conditions.

Strength may change as evidence changes.

## 7. Decision Package

For Tier 1 and significant Tier 2 decisions, the Lead should compress prior work into a package that enables focused judgment.

A useful package includes, as relevant:

- Decision to be made;
- Why the decision matters now;
- current evidence and constraints;
- realistic alternatives;
- major trade-offs;
- strongest counterargument;
- Lead recommendation;
- Recommendation Strength;
- failure or reversal conditions; and
- the exact question requiring CEO judgment.

The package should not reproduce every agent output or exploratory branch.

## 8. Execution Depth

Process depth should scale with consequence and uncertainty.

A local, reversible choice may be handled directly by the Lead or a small agent set. A high-consequence semantic or architectural decision should receive broader exploration, independent critique, Research consistency review where relevant, and explicit escalation.

The Design Lab should avoid both extremes:

- under-reviewing consequential decisions; and
- applying heavyweight governance to routine reversible work.

## 9. Default Work Cycle

```text
Design Problem
→ frame the problem and success condition
→ classify consequence and uncertainty
→ compose the minimum useful agent team
→ explore / design / challenge
→ synthesize
→ decide autonomously or escalate by tier
→ build / prototype / document as appropriate
→ test or observe
→ capture reusable learning when justified
→ inspect the Lab process for recurring friction
```

The final step connects normal Design work to the Design Lab Evolution process.
