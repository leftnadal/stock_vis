# Workstream 001 — Synthesis

**Status:** Working Synthesis / Awaiting CEO decision on foundation promotion  
**Synthesized:** 2026-08-27  
**Owner:** Stock_vis Design Lab

## 1. Executive Synthesis

Workstream 001 began with a broad question: how should Stock_vis help a user form, maintain, revise, compare, and use an investment judgment without replacing that judgment?

Across six exploration batches, adversarial scenarios, Research-Lab boundary checks, and two low-fidelity prototypes, the strongest surviving direction is:

> **Stock_vis should maintain a traceable, revisable judgment workspace around each investment, help the user allocate attention to judgment-bearing change, support initial formation and ongoing revision with adaptive depth, preserve Human–AI authorship boundaries, and move comparison / portfolio reasoning into a downstream Decision Context that can include forward scenarios and relative opportunity.**

This is a **Design mental-model and logical experience architecture**, not final Product IA, navigation, screen naming, or implementation schema.

**Overall Recommendation Strength: Strong.**

It is not Very Strong because real-user validation is still limited, the right user-visible granularity remains unresolved, and future-scenario / relative-opportunity methodology depends on Research Lab work that Design Lab must not invent.

## 2. Recommended Problem Framing

### Recommended framing

The core problem is not primarily information scarcity or predicting which stock will rise.

A stronger formulation is:

> **Investors must allocate limited attention, interpret new information against prior expectations and context, revise beliefs under uncertainty, preserve why their view changed, and compare current holdings with future alternatives without allowing salience or AI synthesis to silently become their judgment.**

Stock_vis therefore should help with:

- attention allocation;
- evidence-to-judgment traceability;
- belief / judgment revision;
- explicit uncertainty and unresolved states;
- persistent judgment memory;
- Human–AI authorship clarity;
- forward-looking comparison under Decision Context; and
- distinguishing company growth from investment value.

### Framings that were rejected or narrowed

#### More information is the main solution

Rejected as insufficient. More information can increase overload, salience bias, and reactive decision behavior.

#### News / event feed as the primary organizing object

Narrowed to an orientation / trigger role. Events matter because of their bearing on maintained judgment, not merely because they occurred recently or moved price.

#### Judgment = a single score or bullish / bearish state

Rejected as a default. Important components can move in different directions and carry different uncertainty / conviction.

#### A fixed linear user journey

Narrowed. A sequence such as `Orient → Understand → Judge` remains useful shorthand but did not survive as a mandatory screen flow.

## 3. Recommended Judgment Model

### 3.1 Investment Judgment is a maintained and revisable state

The strongest model is not `state vs structure vs process` as an exclusive choice.

Investment Judgment is better treated as:

> **a maintained state with internal structure, revised through an update process, whose downstream relevance changes with Decision Context.**

A maintained state may include, when material:

- important drivers / claims;
- risks and invalidation conditions;
- dependencies / conditions;
- unresolved questions or alternatives;
- local conviction / uncertainty;
- System–User divergence; and
- material revision history.

### 3.2 Semantic model and update process must remain distinct

The workstream found that earlier models mixed objects, relations, evaluations, and processes.

The recommended split is:

1. **Judgment Semantic Model** — what exists and how it relates.
2. **Judgment Update Logic** — how a trigger changes, retains, qualifies, or leaves unresolved the maintained state.

This also aligns with Research Lab's process–object separation.

### 3.3 System Synthesis and User Judgment remain semantically distinct

This is already Approved in `DL-DR-0001 — Human–AI Judgment Authority Boundary`.

The AI may autonomously research, synthesize, challenge, monitor, and update **System Synthesis**. It must not silently attribute or overwrite a material **User-owned Judgment**.

The absence of an explicit user view is a valid state. A user may have:

- no explicit view yet;
- a partial view;
- unresolved components;
- agreement with the system on some components; and
- disagreement on others.

## 4. Recommended Information Model

The minimum useful structure is not a list of peer information layers. It is a set of semantically different objects and relations.

### Maintained Judgment State

The current structured view.

### Update Trigger / Signal

Something that makes reconsideration potentially worthwhile. Price movement, news, time decay, a new competitor, a portfolio-context change, or a user question may all be triggers.

A trigger is not automatically evidence against a thesis.

### Reference / Interpretive Context

The baseline against which information is interpreted: prior judgment, prior expectation, management guidance, consensus, peers, historical range, regime, or another relevant reference.

### Epistemic Input

Research Knowledge / Understanding and its relevant Research-side credibility, applicability, conflict, uncertainty, and limitations.

Design consumes this characterization; it must not silently create a competing epistemic authority.

### Judgment-Bearing Relation

The explicit relation answering:

> **Which part of the current judgment does this information actually bear on?**

An input may support, challenge, qualify, narrow, broaden, create uncertainty, introduce a component, or have no meaningful bearing.

### Judgment Impact

The preferred Working Design interpretation of earlier `Significance / Materiality` language.

Judgment Impact is **relational**, not an intrinsic score attached to an information item. Highly credible evidence can have low judgment impact if peripheral; weak conflicting evidence can affect a central driver mainly by increasing uncertainty rather than immediately changing direction.

### Conviction and Uncertainty

They remain distinct from judgment direction and should usually be local to the component they concern before any global summary.

### Update Trace / Lineage

Material change should preserve enough history to answer what changed, why, based on what, under which reference, and through whose action / authority.

### Decision Context

Portfolio, horizon, alternatives, constraints, opportunity cost, switching cost, and other decision-specific conditions remain downstream from the maintained company judgment.

## 5. Recommended Judgment Update Logic

The strongest analytical loop is:

```text
Current Judgment State
+ Trigger / Signal
+ relevant Research Knowledge / Understanding
+ Decision Context when needed
        ↓
Orient
        ↓
Contextualize
        ↓
Link to Judgment
        ↓
Assess Judgment Impact
        ↓
Revise / Retain / Mark Unresolved
        ↓
Recalibrate Conviction & Uncertainty
        ↓
Preserve Update Trace
        ↓
Updated Judgment State
```

This is **not** a mandatory screen sequence.

Important outcomes include:

- strengthen;
- weaken;
- retain after review;
- add / remove / qualify;
- narrow / broaden;
- split into conditional cases;
- increase / reduce uncertainty;
- mark unresolved;
- suspend judgment; and
- not assessed.

`Retained after review` must remain distinguishable from `not reviewed`.

## 6. Recommended Logical Experience Architecture

The original `Adaptive Change Review` hypothesis survived, but only as one mode inside a broader architecture.

The current leading architecture is:

> **Persistent Judgment Workspace + Attention-Oriented Orientation + Formation / Maintenance + Adaptive Review + downstream Decision Context.**

```text
                       ORIENTATION
                "Where should I look?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company   Cross-company need
         │                │                │
         ▼                ▼                ▼
     FORMATION        MAINTENANCE      DECISION CONTEXT
         │                │          comparison / portfolio
         │       simple change → inline
         │       complex/material → focused review
         │                │
         └───────────────┬┘
                         ▼
                JUDGMENT WORKSPACE
                  maintained state
                         │
              evidence / provenance
                         │
               update trace / history
```

### Orientation is attention allocation, not a news feed

Cross-company orientation should prioritize judgment-bearing change, consequential unresolved uncertainty, material System–User divergence, and user-defined monitoring conditions.

`Attention item ≠ task ≠ approval request.`

### Adaptive review depth

- no user-facing relevance → silent system maintenance;
- simple / low-consequence bearing → inline annotation;
- multi-component, conflicting, consequential, or material System–User divergence → focused review;
- portfolio / allocation / rotation reasoning → user-initiated Decision Context.

This avoids both alert-inbox fatigue and an overloaded universal company screen.

## 7. Formation, Maintenance, and Comparison

### 7.1 Formation

A new company has no prior user judgment. The product should begin from System Synthesis and guided exploration, not fabricate an artificial `change`.

Useful access questions include:

- What matters most?
- What could break the case?
- What remains unknown?
- What has recently changed that matters?

The user may form only part of a view and leave the rest unresolved.

### 7.2 Maintenance

Existing holdings benefit from change-driven orientation and adaptive review depth. The system should preserve the continuity of the maintained state across time.

### 7.3 Comparison belongs in Decision Context

Comparison should consume maintained judgments without overwriting them.

It should preserve both:

- genuinely comparable shared dimensions; and
- asymmetric company-specific drivers / risks.

Default comparison should not collapse immediately into a total score.

## 8. Forward-Looking Comparison and Rotation

The workstream identified that realistic comparison is inherently forward-looking.

The key question is not only `Which company looks stronger today?`, but:

> **Across plausible future states, which investment has the stronger forward opportunity, what must go right or could block it, and is the relative gap large and credible enough to justify reallocating capital?**

### 8.1 Future scenario structure

Prefer conditional scenarios to one deterministic future where possible:

```text
Possible Future
→ Growth Opportunity
→ Growth-Path Conditions
→ Company-specific response
→ Growth / Value Outcome
→ Relative Future Opportunity
```

### 8.2 Growth-path conditions

A market opportunity should not be assumed to convert automatically into company growth.

The Working Design structure distinguishes:

- **Opportunity** — external / structural room for growth;
- **Enablers** — conditions required to capture it;
- **Accelerators** — conditions that increase speed / scale / economics;
- **Bottlenecks / Delays** — constraints on size or timing without necessarily destroying the thesis;
- **Invalidation Conditions** — conditions that materially break the scenario or central growth mechanism;
- **Value-Capture Conditions** — whether business growth becomes durable shareholder / per-share value; and
- **Monitoring Signals** — evidence showing whether those conditions are strengthening or weakening.

This structure also connects future scenarios back to ongoing judgment maintenance: new evidence can strengthen an enabler, worsen a bottleneck, approach an invalidation condition, or change value capture.

### 8.3 Growth is not the optimization target by itself

Conceptually:

```text
Business growth
+ growth-path durability / conditions
+ current valuation
+ capital requirements / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity` remains a Working Design phrase, not Approved Research terminology.

### 8.4 Relative Opportunity Gap

Comparison should ask whether an alternative is merely somewhat better or sufficiently better to justify deeper rotation review.

A small apparent advantage should not automatically produce portfolio churn.

No investment-decision threshold or rotation rule is defined by this workstream.

## 9. What Changed from Starting Hypotheses

### Retained

- better judgment, not more information, as the Design objective;
- persistent judgment structure;
- importance of change, context, evidence, uncertainty, and conviction;
- need for progressive disclosure;
- comparison as an important capability; and
- Design should support rather than replace judgment.

### Revised

- `Judgment = Structure` → **maintained state + internal structure + update process under Decision Context**;
- `Materiality` as an information layer → **Judgment Impact as a relation**;
- linear six-step journey → **analytical update loop, non-linear in the interface**;
- `Adaptive Change Review` as the foundation → **adaptive review inside a broader Judgment Workspace**;
- comparison of current state → **forward scenario / relative opportunity comparison**;
- generic growth risks → **explicit growth-path conditions**.

### Rejected as defaults

- chronological news feed as the primary experience;
- universal bullish / bearish label;
- one scalar conviction / attractiveness score as the main representation;
- always-visible System vs User dual columns;
- every change requiring review / approval;
- forcing the user to author a complete thesis before receiving value;
- raw growth rate as equivalent to investment opportunity; and
- deterministic future forecast as the default comparison model.

## 10. Design Knowledge Candidates

The following findings have survived enough scenarios to be candidates for reusable Design Knowledge, but promotion is **not automatic**.

1. **Investment judgment should be represented as maintained and revisable rather than episodic.** — Strong
2. **Semantic objects and update processes should be separated.** — Strong
3. **Judgment relevance / impact is relational, not an intrinsic information score.** — Strong
4. **Orientation should allocate attention by judgment bearing rather than raw activity.** — Strong
5. **Review depth should be consequence-adaptive.** — Strong
6. **User judgment may be absent, partial, unresolved, or disagree with System Synthesis.** — Strong; authorship boundary itself is already Approved via DL-DR-0001.
7. **Decision Context should remain distinguishable from underlying company judgment.** — Strong
8. **Comparison should preserve both shared and asymmetric structure.** — Strong
9. **Forward comparison should expose scenario conditions and growth-path blockers rather than only forecast outcomes.** — Strong
10. **Default scalar ranking should remain subordinate to traceable relative trade-offs and uncertainty.** — Moderate–Strong

A later promotion step should decide which of these deserve `03_design_knowledge/` and whether any need CEO-level approval.

## 11. Research Trigger Candidates

### Trigger 1 — Future Scenario / Relative Opportunity Methodology

> **What Research methodology should produce and evaluate future scenarios, growth-path conditions, predictive growth/value outcomes, and relative opportunity comparisons strongly enough for downstream Design and portfolio decision support?**

This includes, where appropriate:

- scenario construction;
- predictive probability;
- forecast calibration;
- expected growth / return estimation;
- valuation-outcome mapping;
- probability weighting;
- uncertainty aggregation;
- causal / predictive status of growth-path conditions; and
- epistemic evaluation of predictive / comparative Claims.

Design Lab may design the experience for these outputs, but must not define their epistemic authority.

### Trigger 2 — Downstream Decision-Support Methodology

Research Lab Evaluation Methodology currently recognizes Decision-Support Evaluation as a later downstream family. If Stock_vis progresses from judgment support toward comparative / portfolio decision support, Research may need to define how such downstream reasoning is warranted and evaluated without collapsing Research truth into a product recommendation rule.

## 12. Failure Modes / Reversal Conditions

Revise the architecture if real-user or Research evidence shows that:

- a persistent judgment structure creates anchoring stronger than the benefits of continuity;
- users cannot distinguish System Synthesis from their own view despite authorship treatment;
- progressive / adaptive depth feels unpredictable or hides important information;
- focused reviews become a new inbox burden;
- judgment-bearing links are too artificial or expensive to maintain;
- revision lineage is not useful enough to justify complexity;
- Formation / Maintenance / Decision Context feels fragmented compared with one universal contextual page;
- structured future scenarios create false confidence rather than calibrated understanding;
- growth-path condition taxonomy is cognitively too heavy;
- relative-opportunity framing causes unnecessary portfolio churn; or
- Research Lab develops a materially different structure for predictive / comparative reasoning.

## 13. Design Lab Evolution Findings

The Design Lab operating model performed adequately in this workstream.

Useful operational learnings:

- Batch-level exploration reduced CEO micro-consensus without losing consequential escalation.
- Separating exploration files by batch became necessary once the workstream grew; one monolithic exploration file would be harder to review.
- Korean companion documents materially improved CEO review speed and should remain standard for consequential Design Lab documents.
- Prototype artifacts were valuable for revealing interaction failures that remained hidden in conceptual discussion, especially the limitation of a literal Change Review architecture.
- No new permanent governance or agent taxonomy is justified by this workstream.

No structural Design Lab operating change is currently required.

## 14. Decision Package

### Recommended Structure

Use the following as the leading **Investment Judgment Experience Foundation** for downstream Product Surface / IA exploration:

> **Persistent and revisable Judgment Workspace**  
> + **attention-oriented Orientation**  
> + **Formation and Maintenance using the same underlying judgment semantics**  
> + **consequence-adaptive review depth**  
> + **traceable Research / Evidence / authorship / revision lineage**  
> + **Decision Context kept downstream from company judgment**  
> + **forward-looking Comparison using scenarios, growth-path conditions, valuation, uncertainty, and relative opportunity.**

### Recommendation Strength

**Strong**

### Why

This model survived the widest range of scenarios tested so far:

- no prior user judgment;
- sharp price movement without thesis change;
- mixed earnings;
- material Human–AI disagreement;
- multi-holding morning review;
- cross-company comparison; and
- possible portfolio rotation.

It also preserves the approved Research–Design boundary and DL-DR-0001 Human–AI authority boundary.

### Main Alternatives

1. **Event / Feed-centered product** — simpler orientation, but weak judgment continuity and differentiation.
2. **One integrated universal Judgment Home** — lower navigation cost, but risks overload during complex multi-component change and comparison.
3. **AI-maintained single shared thesis** — lower user effort, but conflicts with approved semantic authorship unless very carefully constrained.
4. **Score / ranking-centered comparison** — efficient, but risks false symmetry, false precision, and hidden trade-offs.

### Key Trade-offs

- continuity vs anchoring;
- traceability vs complexity;
- adaptive disclosure vs predictability;
- user agency vs interaction burden;
- structured comparison vs cognitive load;
- forward-looking usefulness vs false precision;
- opportunity optimization vs portfolio churn.

## 15. Batch Consensus

The Design Lab Lead recommends carrying the following forward as **Working Consensus** unless contradicted by CEO decision, user evidence, or Research authority:

- maintained / revisable judgment as the core mental model;
- semantic model separated from update process;
- Judgment-Bearing Relation and relational Judgment Impact;
- local conviction / uncertainty rather than default global scalar;
- traceable update lineage;
- attention-oriented Orientation;
- adaptive review depth;
- System Synthesis distinct from User Judgment per DL-DR-0001;
- Decision Context separated from underlying company judgment;
- forward-looking comparison with explicit growth-path conditions; and
- no default total score or automatic rotation rule.

## 16. CEO Critical Decision — Foundation Promotion

### Decision

Should the synthesized core mental model above be accepted as the **Working Design Foundation for the next Product Surface / IA workstream**, without yet promoting every component to Approved Design Knowledge or final Product IA?

### Design Lab Lead Recommendation

**Approve it as the next-workstream foundation, while keeping the architecture explicitly Working and falsifiable.**

### Recommendation Strength

**Strong**

### Why this deserves CEO attention

This is no longer a local interaction detail. It determines the organizing mental model from which later Dashboard / company surface / comparison / portfolio / monitoring IA may be derived.

However, approving it as a **Working Foundation** is intentionally weaker than freezing a permanent Product IA or approving every term as durable Design Knowledge.

### Strongest Counterargument

The system may be over-structuring investment judgment before real users demonstrate that they want or can effectively use a persistent judgment model. A simpler AI research + alert + comparison experience may provide most of the value with much lower learning cost.

### Failure / Reversal Conditions

Approval should be revisited if prototypes / user tests show that persistent structured judgment:

- creates harmful anchoring;
- feels like maintenance work;
- is not understood distinctly from AI opinion;
- does not improve actual comparison / revision quality; or
- is materially less useful than a simpler episodic experience.

## 17. Deferred / AI-Owned

The following remain delegated / reversible unless they become consequential:

- final naming of Judgment Workspace, Formation, Maintenance, Change Review, Judgment Impact, Relative Opportunity Gap;
- exact component taxonomy and visible component count;
- visual treatment of conviction, uncertainty, provenance, and divergence;
- exact adaptive-review thresholds;
- whether modes are explicit navigation or contextual states in one surface;
- morning-review grouping and ranking details;
- comparison layout;
- exact growth-path condition labels;
- whether an aggregate comparison summary is useful;
- mobile layout and interaction; and
- implementation / storage schema.
