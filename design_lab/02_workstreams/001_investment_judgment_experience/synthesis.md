# Workstream 001 — Synthesis

**Status:** Working Design Foundation / Research-aligned  
**Synthesized:** 2026-08-27  
**Semantic Alignment:** DL-DR-0002 effective 2026-08-27  
**Owner:** Stock_vis Design Lab

## 1. Executive Synthesis

Workstream 001 explored how Stock_vis can help users form, maintain, revise, compare, and use investment views without allowing information salience or AI synthesis to replace user judgment.

After six exploration batches, adversarial scenario tests, Research-Lab consistency checks, and low-fidelity prototypes, the leading Design direction is:

> **Stock_vis should maintain a traceable and revisable Investment View workspace around each investment, allocate user attention to meaningful changes, support initial formation and ongoing maintenance with adaptive depth, preserve Human–AI authorship boundaries, and combine relevant Understanding / maintained views with Decision Context only when forming downstream Judgment and Decision.**

Forward comparison should reason about plausible futures, growth-path conditions, valuation, uncertainty, and relative opportunity without treating one forecast or one score as the truth.

This is a **Working Design Foundation**, not Approved Product IA, navigation, screen naming, ontology, database schema, or investment-decision rule.

**Overall Recommendation Strength: Strong.**

## 2. Research-Aligned Semantic Boundary

Workstream 001 originally used `Judgment State`, `Judgment Workspace`, and `User Judgment` for a persistent company-level state. Review against the current Approved Research Lab architecture identified a semantic conflict.

Research authority defines:

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

Therefore, under **DL-DR-0002**, Design Lab no longer treats the persistent pre-Decision-Context company state as the cross-Lab `Judgment` object.

The corrected structure is:

```text
Research Knowledge / Understanding
        ↓
System Synthesis
        ↕
Maintained User Investment View
        +
Decision Context
        ↓
Judgment
        ↓
Decision
        ↓
Action
```

`Investment View` is a Working Design label, not yet a governed final term.

Historical Workstream documents may retain earlier Working wording for traceability; downstream reusable Design knowledge must use the aligned semantics.

## 3. Recommended Problem Framing

The core problem is not primarily information scarcity or predicting which stock will rise.

A stronger framing is:

> **Investors must allocate limited attention, interpret changing reality against prior understanding and expectations, maintain a revisable view under uncertainty, preserve why that view changed, and combine that view with a concrete Decision Context when judging whether to act or allocate capital differently.**

Stock_vis should therefore support:

- attention allocation;
- traceable connection from Research / Understanding to user-facing synthesis;
- persistent but revisable Investment View memory;
- explicit uncertainty and unresolved states;
- Human–AI authorship clarity;
- adaptive review of meaningful changes;
- downstream Decision Context;
- forward-looking comparative opportunity; and
- separation of company growth from shareholder / investment value.

## 4. Maintained Investment View Model

The persistent Design-side state may contain, when material:

- important drivers / propositions;
- risks and invalidation conditions;
- dependencies / enabling conditions;
- unresolved questions or alternatives;
- local conviction / uncertainty;
- System–User divergence;
- relevant scenario conditions; and
- revision history / provenance.

A user may legitimately have:

- no explicit view yet;
- a partial view;
- unresolved components;
- agreement with System Synthesis on some components; and
- disagreement on others.

The product should not require a complete user-authored thesis before providing value.

## 5. System Synthesis and User-Owned View

DL-DR-0001 remains in force, interpreted through DL-DR-0002.

AI may autonomously research, structure, summarize, monitor, challenge, and maintain **System Synthesis**. It must not silently attribute that synthesis to the user or overwrite the user's maintained Investment View.

Material user-owned changes require meaningful user control or an explicitly delegated rule that is visible in scope, reversible, and traceable.

System–User disagreement may persist.

A later workstream should distinguish where System Synthesis is merely a presentation / translation of Research Understanding versus where it introduces a new inferential claim that requires legitimate Research epistemic treatment.

## 6. Recommended Information / Relationship Model

The experience should distinguish different semantic functions rather than flatten them into peer information layers.

### 6.1 Maintained Investment View
The current user-owned structured company view.

### 6.2 System Synthesis
The current Stock_vis-generated synthesis available to support or challenge the user's view.

### 6.3 Update Trigger / Signal
Something that makes reconsideration potentially worthwhile: new evidence, event, price move, time decay, regime change, new competing opportunity, portfolio-context change, or user question.

A trigger is not automatically evidence against a company view.

### 6.4 Reference / Interpretive Context
The baseline used to interpret information: prior state, expectation, management guidance, consensus, historical range, peer, regime, or another relevant reference.

### 6.5 Epistemic Input
Research Knowledge / Understanding and relevant Research-side credibility, applicability, conflict, uncertainty, scope, and limitations.

Design consumes and represents this characterization; it does not create a competing epistemic authority.

### 6.6 View-Bearing Relation
Working replacement for earlier `Judgment-Bearing Relation` language at the persistent-view layer:

> **Which part of the current Investment View does this information actually bear on?**

An input may support, challenge, qualify, narrow, broaden, introduce uncertainty, create a new component, or have no meaningful bearing.

### 6.7 View Impact
Working replacement for earlier `Judgment Impact` at the persistent-view layer.

Impact is relational, not an intrinsic score attached to an information item. Strong evidence can have low View Impact if peripheral; weak conflicting evidence can mainly increase uncertainty in a central component rather than immediately reverse direction.

### 6.8 Conviction and Uncertainty
Remain distinct from Research credibility and from eventual Decision confidence. They should usually remain local to the component they concern before any global summary.

### 6.9 Update Trace / Lineage
Material change should preserve what changed, why, based on what, under which reference, and through whose action or authority.

### 6.10 Decision Context
Portfolio exposure, horizon, alternatives, valuation, constraints, opportunity cost, switching costs, and other decision-specific conditions combine downstream with relevant Understanding / maintained views to support Judgment.

## 7. Maintained-View Update Logic

The leading analytical maintenance loop is:

```text
Current Investment View
+ Trigger / Signal
+ relevant Research Knowledge / Understanding
        ↓
Orient
        ↓
Contextualize
        ↓
Link to affected View component
        ↓
Assess View Impact
        ↓
Revise / Retain / Mark Unresolved
        ↓
Recalibrate local conviction / uncertainty
        ↓
Preserve update trace
        ↓
Updated Investment View
```

This is not a mandatory UI sequence.

Valid outcomes include strengthen, weaken, retain after review, qualify, narrow, broaden, split into conditions, add/remove a component, increase/reduce uncertainty, unresolved, suspend view, and not assessed.

`Retained after review` must remain distinguishable from `not reviewed`.

## 8. Logical Experience Architecture

The leading architecture becomes:

> **Persistent Investment View Workspace + Attention-Oriented Orientation + Formation / Maintenance + Adaptive Review + downstream Decision Context.**

```text
                       ORIENTATION
                "Where should I look?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company   Decision need
         │                │                │
         ▼                ▼                ▼
     FORMATION        MAINTENANCE      DECISION CONTEXT
         │                │           comparison / portfolio
         │       simple change → inline      │
         │       complex/material → review   │
         │                │                   │
         └───────────────┬┘                   │
                         ▼                    │
              INVESTMENT VIEW WORKSPACE      │
                         │                    │
          evidence / provenance / history    │
                         │                    │
                         └──────────────┬─────┘
                                        ▼
                                     JUDGMENT
                                        ↓
                                     DECISION
```

### Orientation guardrail

Orientation prioritizes **review value / likely bearing**, not epistemic proof of importance.

`Low priority` must not imply `proven irrelevant`, and Quiet items should remain inspectable.

### Adaptive review depth

- no material user-facing review value → silent system maintenance;
- simple / low-consequence bearing → inline annotation;
- multi-component, conflicting, consequential, or material System–User divergence → focused review;
- allocation / rotate / add / reduce question → explicit Decision Context and downstream Judgment.

## 9. Formation and Maintenance

### Formation

For a new company, System Synthesis may first expose what appears important without fabricating a user view. Useful guided questions include:

- What matters most?
- What could break the case?
- What remains unknown?
- What conditions must hold for the opportunity to develop?

The user may adopt, modify, or leave components unresolved.

### Maintenance

For an existing company, new information should connect to the maintained view rather than force the user to reconstruct the investment case from a chronological feed.

Simple changes may remain inline; complex changes may justify focused review.

## 10. Forward-Looking Comparison and Decision Context

Comparison should not ask only which company looks stronger today.

The stronger downstream question is:

> **Across plausible future states, which investment has the stronger forward opportunity, what conditions enable or block that path, and is the relative gap sufficiently meaningful and credible to matter for allocation or rotation?**

A Working representation is:

```text
Company A Understanding / Investment View
        ↓
Plausible Future Scenarios
        ↓
Opportunity
→ Enablers
→ Accelerators
→ Bottlenecks / Delays
→ Invalidation Conditions
→ Value-Capture Conditions
        ↓
Possible Growth / Value Outcomes
        ┐
        │
        ├── Relative Future Opportunity
        │
        ┘
Company B ... same structure

            +
Current Valuation
Uncertainty / credibility
Time Horizon
Portfolio Context
Opportunity Cost
Constraints / switching costs
            ↓
Comparative Judgment
            ↓
Decision
```

### Growth is not enough

Business growth is not equivalent to investment value.

The experience should preserve, where material:

- durability and conditions of growth;
- timing;
- capital needs and dilution;
- downside / failure conditions;
- current valuation;
- uncertainty; and
- whether business growth converts into durable shareholder / per-share value.

### No default deterministic winner

Conditional futures and traceable conditions are preferred to an unwarranted precise forecast or one total score.

`Relative Opportunity Gap` remains a Working interaction concept, not a decision threshold or Research term.

## 11. What Was Retained, Revised, and Rejected

### Retained

- better judgment, not more information, as the Design objective;
- persistent company-level state;
- progressive disclosure;
- adaptive review;
- authorship provenance;
- unresolved states and disagreement;
- traceable revision history;
- comparison as a key capability; and
- forward scenario / growth-path conditions.

### Revised

- `Persistent Judgment State` → **Maintained Investment View / equivalent Design concept**;
- `Judgment Workspace` → **Investment View Workspace** as current Working label;
- `Judgment Impact` at the persistent-state layer → **View Impact** Working wording;
- `Decision Context downstream from company Judgment` → **Decision Context combines with Understanding / maintained views before cross-Lab Judgment**;
- fixed six-step journey → non-linear analytical maintenance loop;
- Change Review as foundation → Adaptive Review inside a broader workspace;
- current-state comparison → future scenario / relative opportunity comparison;
- generic risks → explicit growth-path conditions.

### Rejected as defaults

- chronological news feed as the primary experience;
- universal bullish / bearish label;
- one scalar attractiveness / conviction score as the main representation;
- every change requiring review or approval;
- always-visible dual System / User columns;
- forced complete user thesis creation;
- raw business growth as equivalent to investment opportunity;
- deterministic future forecast as the default; and
- a Design-local redefinition of cross-Lab `Judgment`.

## 12. Design Knowledge Candidates

Candidates for later promotion, not automatic Approved knowledge:

1. A persistent and revisable company-level Investment View is useful for judgment support. — **Strong**
2. Semantic objects and update processes should remain distinct. — **Strong**
3. Relevance / impact is relational rather than an intrinsic information score. — **Strong**
4. Orientation should allocate attention by likely bearing / review value rather than raw activity. — **Strong**
5. Review depth should be consequence-adaptive. — **Strong**
6. A user-owned view may be absent, partial, unresolved, or differ from System Synthesis. — **Strong**; authorship boundary already Approved via DL-DR-0001.
7. Decision Context must remain semantically distinct and precede downstream Judgment. — **Very Strong**, Approved semantic boundary via DL-DR-0002.
8. Comparison should preserve shared and asymmetric company structure. — **Strong**
9. Forward comparison should expose scenario conditions and growth-path blockers rather than only forecast outcomes. — **Strong**
10. Default scalar ranking should remain subordinate to traceable trade-offs and uncertainty. — **Moderate–Strong**

## 13. Research Trigger Candidates

### Trigger 1 — Future Scenario / Relative Opportunity Methodology

What Research methodology should produce and evaluate future scenarios, growth-path conditions, predictive growth/value outcomes, and relative opportunity comparisons strongly enough for downstream Design and portfolio decision support?

This may require work on scenario construction, predictive probability, forecast calibration, expected growth / return estimation, valuation-outcome mapping, causal / predictive status of growth-path conditions, and comparative-claim evaluation.

### Trigger 2 — Decision-Support Evaluation

As Stock_vis moves from maintained-view support toward comparative / portfolio decision support, Research may need to further define how downstream reasoning is warranted and evaluated without collapsing Research truth into product recommendation rules.

### Trigger 3 — System Synthesis Epistemic Boundary

When does a user-facing System Synthesis merely restate / organize an existing Research Understanding, and when does it create a new inferential Claim or epistemic structure requiring Research treatment?

## 14. Failure / Reversal Conditions

Revise this foundation if real-user or Research evidence shows that:

- persistent Investment Views create harmful anchoring or maintenance burden;
- users cannot distinguish System Synthesis from their own view;
- progressive / adaptive depth hides material information or feels unpredictable;
- focused reviews become inbox work;
- view-bearing relations or update lineage are too artificial / expensive;
- Formation, Maintenance, and Decision Context feel fragmented;
- scenario structures create false confidence;
- growth-path conditions are cognitively too heavy;
- relative-opportunity framing causes excessive churn; or
- Research Lab formally changes the relevant semantic or predictive architecture.

## 15. Design Lab Evolution Findings

The operating model performed adequately.

- Batch-level exploration reduced CEO micro-consensus.
- Separate batch documents improved reviewability.
- Korean companion documents materially improved CEO review speed.
- Prototypes exposed conceptual failures earlier than text-only discussion.
- Cross-Lab semantic review should occur before promoting a Design mental model that reuses Research-adjacent terminology.

No additional permanent governance layer is currently required.

## 16. Decision Package

### Recommended Working Foundation

Use the following for downstream Product Surface / IA exploration:

> **Persistent and revisable Investment View Workspace**  
> + **attention-oriented Orientation**  
> + **Formation / Maintenance with adaptive review depth**  
> + **traceable Research / evidence / authorship / revision lineage**  
> + **System Synthesis kept distinct from user-owned view**  
> + **Understanding / maintained views + Decision Context → Judgment → Decision**  
> + **forward-looking Comparison using scenarios, growth-path conditions, valuation, uncertainty, and relative opportunity.**

**Recommendation Strength: Strong**

### Main Alternative

A simpler episodic research assistant centered on search, alerts, and ad-hoc AI Q&A without a persistent Investment View.

It has lower interaction and maintenance cost but currently performs worse on continuity, revision traceability, longitudinal learning, and comparison of changing opportunities.

### CEO Critical Decision

**None remaining for Workstream 001 at this stage.**

DL-DR-0001 and DL-DR-0002 contain the consequential authority / semantic decisions already approved by the CEO.

### Deferred / AI-Owned

- final name of the persistent Design-side state;
- component taxonomy and count;
- final View Impact wording / taxonomy;
- screen and navigation structure;
- inline vs drawer vs dedicated review presentation;
- exact authorship controls;
- visual system;
- comparison layout;
- scalar summaries, if any;
- prototype implementation details.

## 17. Next Step

Open **Workstream 002 — Product Surface / Information Architecture Exploration** using this corrected Working Design Foundation as an upstream constraint, while continuing to challenge it rather than treating it as final Product Architecture.
