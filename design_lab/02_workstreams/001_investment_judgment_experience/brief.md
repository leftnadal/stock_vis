# Workstream 001 — Investment Judgment Experience Foundation

**Status:** Working  
**Version:** 0.1  
**Started:** 2026-08-21  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 workstream; Tier 1 issues must be escalated when discovered

## 1. Purpose

This workstream investigates how Stock_vis should support users in forming, revising, comparing, and calibrating investment judgment.

The objective is not to define screens prematurely. It is to establish a tested working model of the user judgment problem and the information and experience structures needed to support it.

This workstream operates under the current Design Lab working purpose:

> **Better Investment Judgment**

and the broader Stock_vis purpose:

> **Better Investment Decisions**

## 2. Authority and Boundaries

- Research concepts and Research Knowledge remain governed by `research_lab/`.
- This workstream may interpret Research Knowledge for user experience, but must not redefine official Research concepts.
- The Research Lab's approved distinction between Understanding, Judgment, Decision, and Action must be preserved.
- Synthetic personas and agent agreement are exploratory tools, not user evidence.
- Workstream outputs are Working by default and do not become Design Knowledge, Principles, or approved product architecture automatically.

## 3. Core Design Problem

Current working framing:

> Investors struggle to form and continuously update investment judgment in a complex, changing, and uncertain reality.

A particularly important recurring question is:

> What changed, why does it matter, and should my judgment change?

This framing is a hypothesis to test, not an approved final problem definition.

## 4. Scope

The workstream will examine, as one coherent batch:

1. **User Judgment Problems**
   - initial judgment formation;
   - judgment updating after new evidence or events;
   - comparative judgment among alternatives;
   - judgment under uncertainty and conflicting evidence.

2. **Judgment Mental Model**
   - whether investment judgment is better represented as a structured set of claims, drivers, risks, and uncertainties rather than a single score or bullish/bearish label;
   - how conviction relates to judgment without collapsing into false precision.

3. **Judgment Journey**
   - how users notice, contextualize, evaluate, connect, revise, and calibrate judgment;
   - whether one common loop can support both new opportunities and existing holdings.

4. **Information Model**
   - what information structures are required to support judgment;
   - distinctions among state/change, context/relationships, evidence/uncertainty, significance/materiality, and judgment structure.

5. **Logical Experience Architecture**
   - whether a model such as `Orient → Understand → Judge` is useful;
   - whether comparison is a contextual mechanism, a judgment mode, or a distinct experience space.

## 5. Primary Scenarios

At minimum, working models should survive stress tests across:

- a held stock experiencing a sharp price decline;
- an earnings release containing mixed signals;
- discovery of a previously unfamiliar stock;
- comparison between an existing holding and a new opportunity;
- conflicting or incomplete evidence;
- a user under time or attention constraints.

Additional scenarios may be added when they expose materially different judgment problems.

## 6. Working Hypotheses to Challenge

The following are inherited from prior exploratory discussion and must be treated as hypotheses:

- investment judgment is often structured rather than reducible to one score;
- large visible change is not the same as high judgment materiality;
- Fact / Interpretation / Expectation may need to remain distinguishable in the experience;
- a common judgment loop may support both judgment formation and updating;
- comparison is a cross-cutting capability and may also become a comparative judgment mode;
- `Orient → Understand → Judge` may be a useful logical experience model;
- conviction should be calibrated to evidence and uncertainty rather than maximized.

The workstream may retain, revise, narrow, replace, or reject any of these.

## 7. Exploration Perspectives

The Design Lab Lead should compose the minimum useful set of perspectives from:

### Explore
- investor / user problem perspective;
- behavioral and cognitive perspective;
- financial product and information-design benchmarking;
- relevant academic or industry evidence.

### Design
- information architecture;
- interaction and sensemaking;
- information representation and progressive disclosure.

### Challenge
- design critique;
- adversarial / synthetic persona stress test;
- accessibility and cognitive-load review where material;
- Research consistency review.

Perspectives may be added or removed as the work evolves.

## 8. Expected Outputs

The workstream should produce:

- a clearer problem framing;
- major alternatives and rejected framings;
- a recommended working judgment model;
- a recommended working judgment journey or loop, if justified;
- a recommended information model;
- a logical experience architecture only if evidence supports one;
- unresolved questions and validation needs;
- any Research Trigger Candidates;
- any reusable Design Knowledge candidates;
- any Design Lab operating friction discovered during execution.

## 9. Escalation

The Lead should not escalate ordinary exploration or reversible modeling choices.

Escalate when the work reveals a decision that materially changes:

- Design Lab Purpose or Philosophy;
- a core Design Principle;
- the Research–Design authority boundary;
- a major user mental model likely to govern many future product surfaces;
- a major information architecture with durable downstream dependency;
- human / AI judgment authority;
- another high-consequence cross-cutting commitment.

## 10. Completion Condition

The workstream is ready for synthesis when the leading model has been challenged across materially different scenarios and alternatives, key Research boundaries have been checked, major failure conditions are explicit, and remaining uncertainty is clear enough to decide what should proceed to prototype or further validation.
