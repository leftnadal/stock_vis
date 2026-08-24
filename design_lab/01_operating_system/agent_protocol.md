# Stock_vis Design Lab Agent Protocol

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-22  
**Owner:** Stock_vis Design Lab  
**Use Status:** Active Working Baseline (authorized for operational use by Project Owner)

## 1. Purpose

This protocol defines how the Design Lab Lead composes and uses specialist agent perspectives without turning the Design Lab into a fixed or bureaucratic agent organization.

The objective is not to maximize the number of agents. It is to obtain the minimum set of distinct perspectives needed to explore, design, challenge, and synthesize a Design problem well.

## 2. When to Use Specialist Agents

The Lead may handle simple local work directly.

Specialist agents are especially useful when a task requires one or more of the following:

- distinct domain or user perspectives;
- broad research or benchmarking;
- multiple plausible design alternatives;
- specialized IA, interaction, visualization, content, accessibility, or prototype work;
- independent critique or adversarial review;
- persona or scenario stress-testing;
- Research Lab consistency review; or
- parallel exploration that would otherwise narrow the Lead's search prematurely.

Agent use is a means of improving exploration and judgment, not an end in itself.

## 3. Dynamic Composition

The Design Lab does not require a permanent roster of specialist agents.

The Lead composes task-specific roles according to the problem. A useful default is to ask which of three functions are needed:

### Explore

Discover relevant reality, user behavior, constraints, prior art, benchmarks, possibilities, and alternative framings.

Possible temporary roles include User Research, Product Strategy, Competitive Research, Domain Research, or Persona Simulation.

### Design

Translate the problem into structures, interactions, representations, content, prototypes, or other design artifacts.

Possible temporary roles include Information Architecture, Interaction Design, Visualization, UX Writing, Visual Design, Design System, or Prototype roles.

### Challenge

Search for reasons the current framing or proposal may fail.

Possible temporary roles include Design Critic, Accessibility Review, Adversarial Persona, Research Liaison, Consistency Review, or Failure-Mode Analysis.

The labels are functional aids, not governed permanent job titles.

## 4. Minimum Useful Team

The Lead should prefer the smallest team that provides materially different useful perspectives.

More agents do not automatically increase confidence. Redundant agents can produce false consensus, excessive synthesis cost, and repeated reasoning.

For low-consequence tasks, one specialist perspective may be enough. For major architectural or semantic work, exploration and critique should normally be separated so that the proposal is challenged independently.

## 5. Agent Task Brief

A specialist agent should receive enough context to work independently without being asked to reinterpret the entire Design Lab.

A useful brief includes, as relevant:

- **Problem** — what needs to be understood, designed, or challenged;
- **Context** — the minimum Stock_vis, Research, Design, user, or product context needed;
- **Goal** — the specific result the agent should produce;
- **Constraints** — approved or active Working Purpose, Principles, authority boundaries, scope limits, or requirements;
- **Authority References** — relevant `research_lab/` or `design_lab/` sources when semantic precision matters;
- **Expected Output** — the form and depth useful for Lead synthesis.

Agents should not invent new meanings for official Research or Design concepts when authority already exists.

## 6. Output Contract

Agent outputs should be concise enough to synthesize and explicit enough to challenge.

Useful fields include:

- Key Findings;
- Evidence / Observations;
- Alternatives;
- Risks / Failure Modes;
- Recommendation;
- Confidence or Uncertainty;
- Open Questions.

Not every task requires every field. The Lead may adapt the contract to the task rather than forcing template completion.

## 7. Exploration and Critique

For important work, the agent or perspective that develops a proposal should not be the only perspective that evaluates it.

A useful pattern is:

```text
Explore
→ Design / formulate alternatives
→ independent Challenge
→ Lead synthesis
```

Critique should attack assumptions, missing evidence, user failure modes, accessibility, Research consistency, long-term dependencies, and alternative explanations as appropriate.

The objective is not to produce disagreement for its own sake. It is to reduce confirmation bias and expose consequential weaknesses before commitment.

## 8. Persona and Synthetic Stress Tests

Persona simulation may be used to probe whether a design model fails under different goals, experience levels, portfolio contexts, attention constraints, or decision situations.

Synthetic personas are exploratory instruments, not user evidence.

Findings from synthetic persona tests should therefore be treated as hypotheses or failure candidates until supported by real user observation, stronger evidence, or repeated design validation.

## 9. Research Liaison

When a task depends materially on Research Knowledge or risks altering Research meaning, the Lead should include a Research consistency check at a stage early enough to avoid expensive rework.

The Research Liaison role does not redefine Research concepts. It checks the Design interpretation against the relevant Research authority and surfaces conflicts or Research Trigger Candidates.

## 10. Agent Authority

> **Agent output is input, not authority.**

Agent agreement is not equivalent to evidence, validation, or approval.

The Design Lab Lead is responsible for comparing agent outputs, resolving or preserving disagreements, checking higher-level constraints, and producing the final synthesis.

Consequential decisions remain subject to the Operating Model's decision tiers and escalation rules.

## 11. Protocol Evolution

If agent composition, task briefs, output contracts, critique timing, or synthesis repeatedly create friction, the protocol should be revised through the Design Lab Evolution process.

One-off inconvenience should normally be handled locally rather than immediately creating a permanent rule.
