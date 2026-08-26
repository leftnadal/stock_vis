# Workstream 001 — Exploration Batch 02: Judgment Update Logic & Information Model

**Status:** Working  
**Date:** 2026-08-25  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; not Approved Design Knowledge or product architecture

> Korean companion: [`batch_02_judgment_update_logic_ko.md`](batch_02_judgment_update_logic_ko.md)

## 1. Batch Question

This batch asks:

> When new evidence, events, changed conditions, or changed decision context appear, what should determine whether and how an existing investment judgment changes?

The purpose is to challenge the earlier candidate sequence:

```text
State & Change
+ Context & Relationships
+ Evidence & Uncertainty
        ↓
Significance / Materiality
        ↓
Judgment Structure + Conviction
```

and the earlier six-step judgment loop.

## 2. Research-Lab Boundary Check

The current approved Research Lab architecture creates several constraints for this Design work.

- Evidence, Claims, Research Knowledge, Understanding, Judgment, Decision, and Action remain distinct.
- Understanding and its credibility are upstream from downstream Judgment.
- Credibility and applicability are distinct.
- Decision-specific relevance or confidence is not an intrinsic property of Understanding; it arises when Understanding is considered together with Decision Context.
- Evaluation preserves distinctions such as `Not Material ≠ Favorable`, `Unassessed ≠ Unfavorable`, and `Unknown ≠ Contradicted`.
- Process and epistemic objects must remain distinguishable.
- Material revisions should preserve lineage.

Therefore Design must not invent a product-side scalar that silently merges evidence quality, research credibility, current applicability, decision relevance, judgment impact, and user conviction.

## 3. External Evidence Relevant to Update Logic

### 3.1 Reference frames materially affect belief updating

Field evidence from financial analysts indicates that expectations can act as reference points: analysts observing nearly identical earnings signals updated differently depending on whether their own forecast was barely exceeded or barely missed.

Reference:
- *Expectational reference points and belief formation: Field evidence from financial analysts* (2025): https://www.sciencedirect.com/science/article/pii/S0167268124004025

**Design implication candidate:** context is necessary, but context is not neutral. The system should make the reference frame explicit rather than presenting one expectation, consensus, prior price, or prior judgment as an invisible truth baseline.

### 3.2 Separating information processing from immediate action can improve belief formation

Investment experiments indicate that lowering involvement and separating belief formation from immediate decision opportunities can move beliefs closer to a Bayesian benchmark, particularly when information is bundled rather than processed reactively one item at a time.

Reference:
- Holzmeister et al. (2023), *Take your time: How delayed information and restricted decision opportunities improve belief formation in investment decisions*: https://www.sciencedirect.com/science/article/pii/S1544612322006195

**Design implication candidate:** the update process should be capable of ending in “judgment revised / retained / unresolved” without forcing an immediate action recommendation.

### 3.3 Confidence is useful for future revision, but local and global confidence are different

Research on metacognition indicates that explicit local confidence affects later changes of mind, while global confidence can be formed by integrating local confidence and feedback over time.

References:
- Folke et al. (2017), *Explicit representation of confidence informs future value-based decisions*: https://www.nature.com/articles/s41562-016-0002
- Rouault et al. (2019), *Forming global estimates of self-performance from local confidence*: https://www.nature.com/articles/s41467-019-09075-3

**Design implication candidate:** conviction should primarily remain attached to the judgment component or proposition it concerns. A global summary may exist, but it should not erase heterogeneous local confidence.

### 3.4 More uncertainty cues do not automatically improve calibrated reliance

Recent LLM decision-support evidence found that visual confidence cues can improve subjective discrimination while simultaneously increasing behavioral over-reliance on incorrect outputs.

Reference:
- *More is not better: Visual uncertainty cues and the fragility of trust calibration in LLM-assisted decision making* (2026): https://www.sciencedirect.com/science/article/pii/S2949882126000587

**Design implication candidate:** uncertainty should not be treated as a decorative badge layer or solved by adding more confidence indicators. It needs to remain tied to the affected claim, evidence, judgment impact, and unresolved decision relevance.

## 4. Major Problem in the Previous Information Model

The previous model mixed several different semantic functions into one apparent hierarchy.

For example:

- **State / Judgment State** is an object or maintained condition.
- **Evidence** is an epistemic input.
- **Context / Reference** is relational information used for interpretation.
- **Materiality** is an assessment of impact or relevance.
- **Judgment revision** is a process / operation.
- **Conviction** is a meta-level property of a judgment or component.

Treating all of these as peer “information types” risks confusing objects, relationships, evaluations, and update operations.

**Working conclusion:** separate the **Judgment Semantic Model** from the **Judgment Update Logic**.

## 5. Recommended Working Judgment Semantic Model

The current leading semantic model contains the following distinct elements.

### 5.1 Maintained Judgment State

The current investment view that may be revised over time.

It may contain, where useful:
- important claims / drivers;
- risks or failure conditions;
- unresolved alternatives or questions;
- relevant conditions / dependencies;
- local conviction or confidence annotations;
- historical lineage of material revisions.

This does not imply that every element must be shown simultaneously in the UI.

### 5.2 Update Trigger / Signal

Something that makes reconsideration potentially worthwhile.

A trigger can arise from:
- new Evidence or Research Knowledge;
- a material event or observation;
- changed conditions or regime;
- passage of time / stale applicability;
- a new competing opportunity;
- changed portfolio or Decision Context;
- a user question or explicit reconsideration request.

A price movement is therefore a trigger or observation by default, not automatic proof that a fundamental claim changed.

### 5.3 Reference & Interpretive Context

Information needed to understand what a trigger means.

Possible references include:
- prior state;
- prior judgment;
- prior expectation;
- management guidance;
- market consensus;
- historical distribution;
- peer / industry comparison;
- stated boundary conditions;
- time horizon or regime.

The reference frame should remain identifiable because different reference points can lead to different belief updates.

### 5.4 Epistemic Input / Profile

The warranted Research-side content available to judgment, including relevant limitations, conflict, uncertainty, credibility, and applicability.

Design should consume or represent Research-side epistemic characterization rather than silently re-evaluating Research objects under a new product definition.

### 5.5 Judgment-Bearing Relation

A critical missing relationship in the earlier model:

> **What part of the maintained judgment does this input actually bear on?**

An input may:
- support;
- challenge;
- qualify;
- narrow;
- broaden;
- introduce a new component;
- create an unresolved conflict; or
- have no meaningful bearing on a particular judgment component.

The same input may bear differently on multiple judgment components.

### 5.6 Judgment Impact

The current preferred Design term for what was previously called `Significance / Materiality`.

Judgment Impact is not an intrinsic property of an information item. It is a relation / assessment concerning whether the new input warrants a meaningful change to the current judgment under relevant context.

Material factors can include, without being reduced to a formula:
- which judgment component is affected;
- how central or dependency-heavy that component is;
- direction and magnitude of the warranted change;
- epistemic strength and current applicability of the input;
- conflict or alternative explanations;
- persistence / reversibility of the changed condition;
- current Decision Context when downstream relevance is being considered.

The term `materiality` may remain useful in natural language, but `Judgment Impact` currently better avoids implying a fixed information attribute or colliding with Research Evaluation's own materiality semantics.

### 5.7 Decision Context

Decision Context remains downstream and distinct from intrinsic Research meaning.

It may include:
- investment horizon;
- portfolio exposure / concentration;
- available alternatives;
- constraints;
- opportunity cost;
- liquidity, tax, or other decision-relevant conditions when appropriate.

A Decision Context change can alter action relevance even when the underlying company judgment does not change.

### 5.8 Update Trace / Lineage

Material changes should preserve enough trace to answer:

- what the prior judgment was;
- what new input arrived;
- what reference/context was used;
- which judgment component was affected;
- why the component changed, did not change, or became more uncertain;
- what uncertainty remains.

This is important both for user verification and for reducing hindsight reconstruction.

## 6. Recommended Working Judgment Update Logic

The current leading process is non-linear in use but can be represented analytically as:

```text
Current Judgment State
+ Update Trigger / Signal
+ relevant Research Knowledge / Understanding
+ Decision Context when needed
        ↓
1. Select / Orient
        ↓
2. Contextualize
        ↓
3. Establish Judgment Bearing
        ↓
4. Assess Judgment Impact
        ↓
5. Revise / Retain / Mark Unresolved
        ↓
6. Recalibrate Conviction & Uncertainty
        ↓
7. Preserve Update Trace
        ↓
Updated Judgment State
        ↓
optional downstream Decision evaluation
```

### 6.1 Select / Orient

Determine whether a trigger deserves scarce user attention.

This must not equate salience, price magnitude, headline volume, or recency with judgment relevance.

### 6.2 Contextualize

Determine the appropriate comparison / reference and whether the relevant Research understanding is currently applicable.

Multiple reference frames may need to remain visible where they materially disagree.

### 6.3 Establish Judgment Bearing

Identify which claim, driver, risk, condition, or unresolved question the input bears on.

This step prevents generic “good news / bad news” interpretation from becoming the primary update mechanism.

### 6.4 Assess Judgment Impact

Ask whether the bearing is important enough and warranted enough to change the maintained judgment.

The output should not be forced into one scalar.

Useful states may include:
- material positive impact;
- material negative impact;
- qualifying / scope-changing impact;
- uncertainty increase;
- uncertainty reduction;
- currently no material impact;
- unresolved / conflicting;
- not assessed.

The exact labels remain Working.

### 6.5 Revise / Retain / Mark Unresolved

A valid update outcome is not always “change the thesis.”

Possible operations include:
- retain;
- strengthen;
- weaken;
- add;
- remove;
- reframe;
- split into conditional cases;
- narrow / broaden scope;
- mark unresolved;
- suspend judgment when warrant is inadequate.

`Retain after evaluation` should remain distinguishable from `not evaluated`.

### 6.6 Recalibrate Conviction & Uncertainty

Conviction should primarily be local to the affected component.

New evidence may:
- change direction without much confidence change;
- change confidence without changing directional judgment;
- leave the central judgment intact while increasing unresolved uncertainty.

Therefore direction, confidence, and uncertainty must remain separable.

### 6.7 Preserve Update Trace

The system should make material revision inspectable rather than silently rewriting the current view.

This supports learning, accountability, comparison over time, and later challenge.

## 7. Stress Tests

### 7.1 Sharp price decline with no fundamental new information

**Naive model:** large change → high materiality → thesis weakened.

**Recommended model:** price decline is a trigger. It may change valuation, market-sentiment, liquidity, or risk-related components, but it does not automatically challenge operating or demand claims.

**Result:** process-object separation prevents salience from becoming evidence.

### 7.2 Earnings beat but guidance deteriorates

Different inputs bear on different components. Historical execution may strengthen while forward demand or margin expectations weaken.

**Result:** a single event can create multi-directional judgment updates without forcing an overall bullish/bearish answer.

### 7.3 Same earnings result vs different expectation reference

A result may appear strong relative to prior company guidance but weak relative to market consensus, or vice versa.

**Result:** explicit reference frames are necessary. One invisible baseline would manufacture false objectivity.

### 7.4 Strong evidence that only affects a peripheral component

Highly credible evidence can still have low Judgment Impact if it bears on a peripheral or non-dependency-heavy part of the current view.

**Result:** epistemic strength and judgment impact remain distinct.

### 7.5 Weak / conflicting evidence affecting a central thesis driver

The centrality is high but warrant is weak.

**Recommended update:** may increase uncertainty or create an unresolved challenge rather than immediately weaken the thesis.

**Result:** high potential importance does not require premature revision.

### 7.6 Decision Context changes without company judgment changing

Portfolio concentration rises because another holding falls, or a superior alternative becomes available.

**Result:** decision relevance can change while maintained company judgment remains stable, confirming the need to keep Decision Context separate.

### 7.7 Previously unknown company

There is no prior maintained judgment to update.

**Result:** the same semantic model can support initial formation by creating a first Judgment State, but the update process should not pretend that every workflow begins with a prior thesis.

## 8. What Happens to the Earlier Six-Step Journey?

The earlier sequence remains directionally useful but should be revised.

Earlier:
1. detect change / opportunity;
2. understand against reference;
3. distinguish material / non-material;
4. evaluate evidence / uncertainty;
5. form or update judgment structure;
6. recalibrate conviction.

Current critique:
- evidence evaluation belongs primarily upstream in Research and should not be recreated as a Design-side epistemic authority;
- materiality is relational rather than an intrinsic information classification;
- the missing `Judgment Bearing` relation is necessary;
- revision outcomes need more than strengthen / weaken;
- lineage / update trace is missing;
- formation and updating share a semantic model but are not identical processes.

Current replacement candidate:

```text
Orient
→ Contextualize
→ Link to Judgment
→ Assess Impact
→ Revise / Retain / Resolve Uncertainty
→ Recalibrate
→ Trace
```

This is an analytical update logic, not a mandatory screen flow.

## 9. Implications for the Earlier Information Model

### Retain, but reinterpret

- **State & Change** → split into maintained state and update trigger / signal.
- **Context & Relationships** → retain as explicit reference / interpretive context, plus judgment-bearing relationships.
- **Evidence & Uncertainty** → retain as upstream epistemic input, but preserve Research authority and distinguish uncertainty from downstream conviction.
- **Judgment Structure + Conviction** → retain, but conviction is a local meta-property rather than simply a final stage.

### Replace

- **Significance / Materiality as an information layer** → replace with **Judgment Impact as a relational assessment**.

### Add

- **Judgment-Bearing Relation** — explicit mapping from new information to affected judgment components.
- **Update Trace / Lineage** — explicit preservation of material judgment revision.
- **Decision Context separation** — downstream overlay rather than intrinsic company truth.

## 10. Current Working Recommendation

### Recommendation

Proceed with a two-model architecture:

1. **Judgment Semantic Model** — maintained judgment state, epistemic inputs, references/context, judgment-bearing relations, Decision Context, conviction/uncertainty annotations, and update trace.
2. **Judgment Update Logic** — Orient → Contextualize → Link → Assess Impact → Revise/Retain/Unresolved → Recalibrate → Trace.

Treat `Judgment Impact` as relational and context-bound rather than as a fixed information property or scalar materiality score.

### Recommendation Strength

**Strong**

### Why not Very Strong

- the semantic model has not yet been validated with real investors;
- the correct granularity of maintained judgment components remains unresolved;
- user-visible vs system-side depth is not yet decided;
- the exact role of user-authored versus AI-synthesized judgment is still open.

### Main alternatives

- retain the earlier linear information hierarchy;
- use a pure claim/evidence graph as both semantic and interaction model;
- reduce the experience to event triage and episodic Q&A without persistent judgment state.

All remain simpler in some respects, but currently fail more important scenarios or erase distinctions needed for traceable revision.

### Failure / Reversal Conditions

Revise this model if later testing shows that:
- explicit judgment-bearing links are too expensive or artificial to maintain;
- users cannot make meaningful use of revision lineage;
- `Judgment Impact` cannot be made interpretable without recreating an opaque scoring model;
- system-side structuring causes more anchoring than useful revision;
- user decision context cannot be separated from maintained investment judgment in practice.

## 11. Batch Consensus / CEO Critical / AI-Owned

### Batch Consensus Candidate

- Process and semantic object models should be separated.
- Materiality should be treated as a judgment-relative impact relation, not an intrinsic information property.
- Judgment-bearing linkage is a necessary missing relation.
- Conviction and uncertainty should remain localized and separable from directional judgment.
- Update lineage should be preserved for material revisions.
- Decision Context should remain separable from the intrinsic company/research view.

### CEO Critical Decision

**None at this stage.**

These remain Working architecture findings. They become CEO-critical only if the Design Lab proposes adopting them as a durable Stock_vis-wide user mental model, cross-surface information architecture, or human/AI judgment-authority boundary.

### Deferred / AI-Owned

- exact naming of `Judgment Impact` versus alternatives;
- exact update-state labels;
- whether local conviction is categorical, verbal, visual, or numeric;
- representation details for update history;
- interaction order and progressive-disclosure details.
