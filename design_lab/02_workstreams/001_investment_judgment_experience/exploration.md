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

# Exploration Batch 01 — User Problem and Competing Judgment Models

**Batch status:** Working synthesis candidate, not approved Design Knowledge.  
**Exploration focus:** behavioral evidence, decision-support evidence, current financial-product patterns, competing mental models, scenario stress tests.

## 1. External Evidence — What Problem Actually Needs Design Support?

### 1.1 Scarce attention is a first-order constraint

Behavioral-finance evidence consistently indicates that investors cannot process all available information and allocate attention selectively. Salient or attention-grabbing information can affect trading even when it is not the most fundamental information. This supports treating attention allocation as part of the judgment problem rather than assuming that presenting more information is sufficient.

Relevant evidence reviewed:

- Choi & Choi (2019), *Effects of limited attention on investors' trading behavior* — attention-grabbing stocks attract abnormal trading and less-sophisticated individual investors continue buying them; https://www.sciencedirect.com/science/article/abs/pii/S0927538X18303196
- Andrei et al. (2020), *Limited attention, salience of information and stock market activity* — salient cues influence investor attention under limited processing capacity; https://www.sciencedirect.com/science/article/pii/S0264999318311519
- Hirshleifer & Teoh (2003), *Limited attention, information disclosure, and financial reporting* — information presentation and aggregation matter when investors have limited attention; https://www.sciencedirect.com/science/article/pii/S0165410103000648

**Design implication candidate:** the problem is not merely information availability. Stock_vis may need to help allocate scarce attention toward judgment-relevant change while preserving access to deeper context.

### 1.2 Belief updating is not neutral

Experimental evidence suggests that investment beliefs can be distorted by involvement, position, and favorability of information. Separating information processing / belief formation from immediate decision opportunities, and bundling information, can improve belief formation relative to a Bayesian benchmark.

Relevant evidence reviewed:

- Holzmeister et al. (2023), *Take your time: How delayed information and restricted decision opportunities improve belief formation in investment decisions*; https://www.sciencedirect.com/science/article/pii/S1544612322006195
- Giglio et al. (2021), *Five Facts about Beliefs and Portfolios* — investor beliefs are persistent and heterogeneous, and portfolio sensitivity to beliefs varies with attention and confidence; https://pubs.aeaweb.org/doi/10.1257/aer.20200243
- Frydman et al.-related experimental literature reviewed through *Do you have a choice?: Implications for belief updating and the disposition effect* (2024), which reinforces the role of belief updating in loss-related investment behavior; https://www.sciencedirect.com/science/article/pii/S0167487024000266

**Design implication candidate:** Stock_vis should not collapse understanding, judgment, and action into one immediate recommendation flow. There is value in a distinct space/process for examining evidence and revising judgment before action.

### 1.3 Confidence matters because it affects later revision, but false precision is dangerous

Evidence outside finance shows that explicit confidence representations can influence later changes of mind: lower confidence makes revision more likely when the decision is revisited. This supports preserving confidence / conviction as a meaningful part of judgment state, but does not justify a single precise overall score.

Relevant evidence reviewed:

- Folke et al. (2017), *Explicit representation of confidence informs future value-based decisions*; https://www.nature.com/articles/s41562-016-0002

**Design implication candidate:** conviction is likely useful as a calibration signal for revisability, but should be attached to what the user is confident about and should preserve uncertainty rather than manufacture precision.

### 1.4 Decision support can help while also creating automation bias

Recent and classic decision-support research shows that decision aids can reduce time and improve performance, but users may overuse, underuse, or over-trust them. Explanations alone do not reliably eliminate automation bias and can sometimes increase reliance.

Relevant evidence reviewed:

- *Information shapes decisions: The access and use of decision support* (2026); https://www.sciencedirect.com/science/article/pii/S2451958826000230
- Vered et al. (2023), *The effects of explanations on automation bias*; https://www.sciencedirect.com/science/article/pii/S000437022300098X
- Skitka, Mosier & Burdick (1999), *Does automation bias decision-making?*; https://www.sciencedirect.com/science/article/pii/S1071581999902525

**Design implication candidate:** “show the reasoning” is not enough to preserve user agency. The experience may need structural opportunities to inspect evidence, disagreement, uncertainty, and revise the system-supported judgment rather than simply consume an explained recommendation.

## 2. Current Financial-Product Pattern Review

The current market shows strong tools for data access, monitoring, research acceleration, comparison, and AI synthesis, but the reviewed products do not clearly establish a persistent, user-verifiable investment-judgment state as the primary organizing object.

### Koyfin

Koyfin emphasizes customizable watchlists, dashboards, alerts, charts, financial analysis, company snapshots, screening, and portfolio monitoring. Its strength is flexible data orientation and monitoring.

Reference: https://www.koyfin.com/features/

**Observed gap relevant to this workstream:** powerful information configuration does not by itself solve how evidence changes a maintained investment view.

### FinChat

FinChat combines financial data, company-specific KPIs, dashboards, comparison, notifications, and AI research. It explicitly emphasizes research efficiency and using AI to automate repetitive research while leaving thinking to humans.

Reference: https://finchat.io/

**Observed gap relevant to this workstream:** the workflow strongly supports understanding and research acceleration, but the reviewed public positioning does not make a persistent structured judgment / revision state the central user object.

### AlphaSense

AlphaSense currently integrates exploration, deep research, financial data, monitoring, alerts, cited AI outputs, company profiles, and workflow agents. Its 2026 platform has explicit investment-thesis research agents and continuous portfolio / watchlist monitoring.

References:

- https://www.alpha-sense.com/platform/
- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/42623871994131-Company-Profiles

**Observed implication:** the competitive bar for research synthesis and monitoring is already high. Stock_vis differentiation should therefore not be assumed to come from “AI summarizes research” alone. A stronger opportunity may lie in maintaining traceable judgment structure across time, evidence changes, and alternatives.

This competitive interpretation remains provisional and should not be treated as a final product-strategy conclusion.

## 3. Competing Mental Model Stress Test

### 3.1 Question-driven model

**Strengths**
- natural entry point for users;
- strong under time and attention constraints;
- can reduce cognitive load by matching recurring questions such as “what changed?” or “does this matter?”.

**Failure modes**
- does not provide durable memory of the investment view;
- repeated questions can produce disconnected answers;
- weak representation of how evidence accumulates or conflicts over time.

**Current judgment:** useful interaction / access layer, weak as the foundational judgment model.

### 3.2 Claim-centered model

**Strengths**
- strong traceability from evidence to belief;
- supports conflicting evidence and partial strengthening / weakening;
- works well for mixed earnings and thesis revision.

**Failure modes**
- can atomize the experience into too many claims;
- does not alone express attention priority, decision context, or portfolio opportunity cost;
- risks forcing users to maintain a research ontology manually.

**Current judgment:** strongest structural backbone candidate, but insufficient alone.

### 3.3 Change-centered model

**Strengths**
- very strong for monitoring existing holdings;
- naturally supports alerts and “what changed?” orientation;
- helps counter information overload when change is filtered by materiality.

**Failure modes**
- weak for a previously unknown company with no prior baseline;
- stable but important structural facts can disappear because they did not recently change;
- salience can leak back in if “change” becomes synonymous with magnitude.

**Current judgment:** strong update / monitoring mechanism, not a complete model.

### 3.4 Decision-context model

**Strengths**
- essential for comparison, opportunity cost, horizon, portfolio constraints, and rotation questions;
- explains why the same evidence can have different judgment materiality for different users.

**Failure modes**
- can prematurely organize research around action choices;
- risks crossing from judgment support into decision prescription;
- user portfolio context can distort the representation of underlying company reality if mixed too early.

**Current judgment:** necessary contextual layer, but should not replace the underlying judgment structure.

### 3.5 Hybrid model

The strongest current model combines different roles rather than forcing one abstraction to do everything.

Working formulation:

> **Investment judgment is a maintained and revisable state with internal structure, updated through an evidence-driven process under a decision context.**

This implies three distinct but connected aspects:

1. **Judgment State / Structure** — the current investment view, including important claims or drivers, risks, unresolved uncertainty, and calibrated confidence.
2. **Judgment Update Process** — new evidence or change is contextualized, assessed for significance, mapped to affected parts of the judgment, and used to revise confidence or structure.
3. **Decision Context** — horizon, portfolio state, alternatives, constraints, and opportunity cost shape relevance and comparison without redefining the underlying Research reality.

A question-driven layer may provide a lightweight user entry into this structure without becoming the underlying semantic model.

**Current recommendation strength:** Strong, not yet Very Strong. Real-user validation is still missing, and the correct user-visible depth of the structured model remains unresolved.

## 4. Scenario Stress Test of the Leading Hybrid

### Held stock with sharp price decline

The model separates salient price movement from judgment materiality and asks which structural claims or risks are actually affected. Decision context can modify urgency without automatically treating price as evidence that the thesis failed.

**Result:** survives.

### Mixed earnings release

Revenue, guidance, margin, execution, and demand evidence can strengthen and weaken different parts of the maintained view simultaneously.

**Result:** survives better than a single-score or change-only model.

### Previously unfamiliar company

A change-only model performs poorly because no prior baseline exists. The hybrid can build an initial structured judgment from current state, context, evidence, and unresolved questions, while question-driven orientation helps the user ramp quickly.

**Result:** survives; supports the need to distinguish formation from update while sharing an underlying structure.

### Existing holding vs new opportunity

The same maintained judgment structures can be compared under a decision context rather than building a separate comparison ontology. Opportunity cost and constraints belong to comparative judgment rather than to the intrinsic company representation.

**Result:** survives conceptually; practical comparison dimensions still need exploration.

### Conflicting or incomplete evidence

The model can preserve unresolved disagreement within the structure rather than forcing one answer.

**Result:** survives, provided the interface does not collapse conflicts into an overall score.

### Time-constrained user

The full structure would be too expensive to inspect every time. Question-driven entry, prioritization, and progressive disclosure are therefore required above the deeper model.

**Result:** survives only as a layered / progressive experience, not as an always-visible full structure.

## 5. Refined Core User-Problem Framing

The initial framing “investors struggle to form and update judgment in complex, changing, uncertain reality” remains directionally useful but is too broad.

A stronger working framing is:

> **Investors must allocate scarce attention, interpret evidence in context, and revise heterogeneous beliefs under uncertainty without letting salience, existing positions, or automated synthesis prematurely collapse the judgment into an action.**

Stock_vis's Design problem may therefore be less about maximizing information delivery and more about supporting:

- attention allocation;
- evidence-to-judgment traceability;
- structured belief revision;
- uncertainty / conviction calibration;
- comparison under explicit decision context; and
- preservation of user agency.

This remains a Working Finding, not an approved Design Principle or product architecture.

## 6. What Changed From the Starting Hypotheses

### Strengthened

- judgment appears meaningfully structured rather than reducible to one score;
- visible magnitude and judgment materiality should remain distinct;
- evidence / uncertainty must survive synthesis;
- comparison is better modeled as a judgment mode / context overlay than as an entirely separate information ontology;
- user agency requires more than merely explaining AI recommendations.

### Revised

- “Judgment = structure” is too narrow. Current evidence favors **state + structure + update process + decision context**.
- the candidate sequential journey should not yet be treated as the core user mental model. It may be more useful as an internal update logic.
- `Orient → Understand → Judge` remains plausible as a high-level experience shorthand, but the evidence so far favors non-linear access rather than a strict sequence.

### Weakened / Rejected as standalone foundations

- question-driven model alone;
- change-centered model alone;
- a single scalar conviction / attractiveness score as the primary judgment representation;
- an AI-explanation-first model in which transparency alone is expected to prevent over-reliance.

## 7. Reversal / Validation Conditions

The leading model should be revised if real-user work shows that:

- investors do not naturally benefit from a persistent structured view and prefer episodic question-answer support;
- maintaining structured judgment creates more cognitive or interaction cost than it removes;
- system-generated structure anchors users more strongly than it helps them revise beliefs;
- decision context dominates judgment relevance so strongly that a company-centered maintained state becomes misleading;
- expert and less-experienced users require fundamentally different models rather than different disclosure depths; or
- comparison cannot reuse the same judgment structure without forcing artificial common dimensions.

## 8. Current Batch Position

**Leading recommendation:** continue Workstream 001 using the hybrid formulation — maintained judgment state/structure + evidence-driven update process + explicit decision context, with question-driven access as a likely experience layer.

**Recommendation Strength:** Strong.

**CEO Critical Decision:** None at this stage. The model remains Working and should be tested further before becoming a durable user mental model or major product architecture.

## Open Questions

- Which parts of the maintained judgment structure should be user-authored, system-synthesized, or jointly editable?
- Is conviction a property of the whole judgment, individual claims, or both?
- How much user context is required before judgment materiality can be evaluated responsibly?
- Can a common architecture support both discovery and monitoring without forcing one mental model onto both?
- Does the six-step candidate journey remain useful as internal update logic after the hybrid model revision?
- Which parts of the model must be visible to users and which should remain system-side reasoning?
- Where should the boundary between synthesized interpretation and user-authored judgment sit?

## Design Lab Evolution Observations

This section will record recurring operating friction discovered while running the workstream. One-off inconvenience should be handled locally and not automatically converted into Lab governance.

_No recurring operating issue recorded yet._
