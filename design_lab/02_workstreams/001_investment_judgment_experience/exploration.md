# Workstream 001 — Exploration Log

**Status:** Working  
**Started:** 2026-08-21  
**Owner:** Stock_vis Design Lab

## Purpose

This document records the exploration needed to challenge and refine the Investment Judgment Experience Foundation workstream.

It is intentionally a working space. Content here is not approved Design Knowledge unless promoted through the Design Lab Knowledge Lifecycle.

## Starting Inputs from Prior Discussion

The following inputs are carried forward only as working hypotheses:

### User problem

Investors may struggle not simply because information is unavailable, but because changing reality makes it difficult to determine:

- what actually changed;
- what is important rather than merely salient;
- how new information relates to an existing or emerging investment view;
- how much confidence is justified;
- whether comparison with another opportunity changes the judgment.

### Candidate judgment loop

A prior exploratory model proposed a sequence approximately equivalent to:

1. detect a change or opportunity;
2. understand it against an appropriate reference;
3. distinguish material from non-material change;
4. evaluate evidence and uncertainty;
5. form or update the judgment structure;
6. recalibrate conviction.

This sequence must be tested rather than preserved by default.

### Candidate information model

A prior exploratory model grouped information as:

- **State & Change**;
- **Context & Relationships**;
- **Evidence & Uncertainty**;
- **Significance / Materiality**;
- **Judgment Structure + Conviction**.

A possible layered interpretation was:

```text
State & Change
+ Context & Relationships
+ Evidence & Uncertainty
        ↓
Significance / Materiality
        ↓
Judgment Structure + Conviction
```

This remains provisional.

### Candidate logical experience model

A prior hypothesis compressed the experience into:

```text
Orient
→ Understand
→ Judge
```

This is a logical model, not a navigation or screen architecture. It must be tested against alternate structures and realistic user tasks.

### Comparison hypothesis

Comparison may play two roles:

- a context mechanism used to understand a number, event, or state; and
- a comparative judgment mode in which two or more investment alternatives are evaluated against one another.

A dedicated comparison surface is not assumed.

## Known Important Insight Candidates

The following prior findings deserve explicit challenge:

### Visible magnitude is not judgment materiality

A large price move, accounting miss, headline, or numerical change may have little effect on the core investment judgment, while a small change may materially weaken or strengthen a core driver.

The workstream should test whether this distinction is robust enough to become reusable Design Knowledge and how user-specific context changes materiality.

### Judgment may be structured

New evidence may strengthen one part of an investment view while weakening another. This suggests that a single bullish/bearish label or overall score may erase important judgment structure.

The workstream should test competing representations rather than assume a thesis graph or component model is required.

### Uncertainty must survive simplification

Useful compression should not make unverified claims, management narratives, forecasts, model inferences, and observed facts appear epistemically identical.

The workstream should examine whether distinctions such as Fact / Interpretation / Expectation are the right design abstraction or whether another representation is better.

## Planned Challenge Matrix

Each candidate model should be challenged across at least the following dimensions:

| Dimension | Questions |
|---|---|
| New vs existing judgment | Does the model work with no prior thesis as well as with a mature holding? |
| Event type | Does it work for earnings, price movement, industry change, regulatory events, and new opportunities? |
| Evidence conflict | Can it preserve disagreement and uncertainty without becoming unusable? |
| Time horizon | Does a long-term investor need a different materiality model from a short-horizon investor? |
| Comparison | Can it support opportunity cost and rotation without duplicating the entire architecture? |
| Attention | Can a time-constrained user orient quickly without losing access to necessary depth? |
| Expertise | Does it help without oversimplifying for experienced users or overwhelming less experienced users? |
| Behavioral risk | Does salience, loss aversion, anchoring, confirmation bias, or recency distort the journey? |
| Research boundary | Does any Design abstraction silently redefine an official Research concept? |
| Action boundary | Does judgment support remain distinguishable from decision prescription? |

## Alternative Framings to Explore

The Lead should not treat the current model as the only candidate. At minimum, exploration should consider alternatives such as:

1. **Question-driven model** — organize the experience around a small set of recurring investor questions rather than a sequential journey.
2. **Claim-centered model** — organize around claims and the evidence that supports or challenges them.
3. **Change-centered model** — organize around material changes to drivers and risks.
4. **Decision-context model** — organize around user portfolio context, alternatives, horizon, and constraints.
5. **Hybrid model** — separate orientation, deep understanding, judgment state, and decision context while allowing non-linear movement.

The final synthesis may combine or reject these.

## Evidence and Benchmarking Needs

Further exploration should seek evidence or strong prior art relevant to:

- investor information overload and selective attention;
- belief updating and confirmation bias;
- uncertainty and confidence calibration;
- comparison and choice architecture;
- progressive disclosure for complex information;
- decision-support systems that preserve user agency;
- financial products that separate raw information, interpretation, and user judgment;
- how professional and retail investors monitor thesis change over time.

External examples should be treated as evidence about patterns and trade-offs, not copied as product architecture.

## Initial Research Consistency Check

The approved Research Lab Knowledge and Understanding Framework distinguishes Understanding from downstream Judgment, Decision, and Action. This workstream should therefore treat Research Knowledge and Understanding as upstream inputs and focus on the user experience of forming judgment under decision context.

Any need to redefine Understanding, Evidence, Research Knowledge, or other Research concepts must be surfaced as a Research Trigger Candidate rather than solved locally.

## Open Questions

- Is “investment judgment” best modeled as a state, structure, process, or combination of these?
- Is conviction a property of the whole judgment, individual claims, or both?
- How much user context is required before judgment materiality can be evaluated responsibly?
- Can a common architecture support both discovery and monitoring without forcing one mental model onto both?
- Does a sequential journey help users, or is it primarily an analytical model for the Design Lab?
- Which parts of the model must be visible to users and which should remain system-side reasoning?
- Where should the boundary between synthesized interpretation and user-authored judgment sit?

## Design Lab Evolution Observations

This section will record recurring operating friction discovered while running the workstream. One-off inconvenience should be handled locally and not automatically converted into Lab governance.

_No recurring operating issue recorded yet._
