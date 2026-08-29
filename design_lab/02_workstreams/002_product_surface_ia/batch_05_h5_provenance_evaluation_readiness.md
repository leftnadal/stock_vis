# Workstream 002 — Batch 05: H5 Architectural Provenance & Evaluation Readiness

**Status:** Working / Evaluation-Readiness Baseline  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream-local evaluation frame; not Approved Product IA, Design Principle, or Lab-wide Evaluation Methodology

## 1. Why This Batch Exists

Batch 04 produced **H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas** as the strongest current IA hypothesis. CEO feedback identified a material weakness in how the Design Lab was preparing to evaluate it:

> A synthesized architecture is not adequately evaluable merely because its visible components and scenario strengths are documented. Future revision requires knowing **where each component came from, what deeper philosophy / cognitive problem it serves, what was intentionally not transferred from the source domain, and what evidence would justify retaining, narrowing, replacing, or removing it.**

The Design Lab therefore pauses further screen-level convergence and builds an explicit architectural genealogy and falsifiable evaluation frame first.

### Current judgment

The concern is valid. Batch 04 was sufficient for **divergent prototype comparison**, but insufficient for **deep causal evaluation or later architecture revision**.

**Recommendation Strength: Very Strong.**

H5 should not be promoted toward Product IA until component-level provenance, counter-hypotheses, and failure signals are explicit.

---

## 2. Evaluation Philosophy Used Here

This workstream does **not** copy Research Lab Evaluation Methodology into Design governance. However, it adopts several compatible disciplines from current Approved Research methodology:

- evaluation must name its target, version, purpose, scope, evidence, challenge, limitations, and re-evaluation triggers;
- evaluation is structured characterization, not a single score;
- uncertainty / unassessed areas must remain explicit;
- preferred interpretations require effective challenge and competing alternatives;
- exploratory discovery is not confirmation;
- criteria and prior evaluations themselves remain revisable.

This is consistent with:

- `research_lab/01_methodology/research_methodology.md`
- `research_lab/02_evaluation/evaluation_methodology.md`
- `design_lab/01_operating_system/knowledge_lifecycle.md`

The Design translation is:

> **Every material H5 component must remain traceable from rationale to testable design hypothesis and reversal condition.**

---

## 3. Architectural Genealogy Chain

For H5, use the following chain rather than a flat list of features:

```text
Deep Principle / Philosophy
        ↓
Recurring Cognitive / Decision Problem
        ↓
Source-domain Pattern
        ↓
Transfer Boundary
(what must NOT be copied)
        ↓
Stock_vis Design Hypothesis
        ↓
H5 Component / Behavior
        ↓
Expected User Effect
        ↓
Counter-hypothesis
        ↓
Observable Failure Signal
        ↓
Retain / Revise / Narrow / Replace / Remove
```

This chain is the minimum reasoning trace for consequential H5 changes.

---

## 4. Deeper Principle Families Behind H5

### P1 — Reality / Evidence Must Be Able to Change the Model

**Primary roots**
- Stock_vis Research Lab Scientific Philosophy and Research Methodology
- intelligence-analysis traditions that treat mental models as necessary but hazardous and require explicit challenge

**Core belief**

A model is useful only while it remains revisable by reality. More information does not automatically improve judgment; the interpretation frame itself must remain challengeable.

**H5 implication**
- evidence, alternatives, uncertainty, provenance, and revision history cannot be decorative layers;
- System Synthesis must not look like unquestionable product truth;
- present architecture must leave a path from new evidence back to current Investment View and forward assumptions.

### P2 — Attention Is Scarce; Situation Awareness Precedes Good Action

**Primary roots**
- bounded rationality / limited attention
- Human Factors and Situation Awareness, especially the distinction among perceiving relevant signals, comprehending their meaning, and projecting future state
- incident / operations triage patterns

**Core belief**

A user cannot process everything. Good support must help the user notice relevant change, understand significance in context, and preserve enough projection to act deliberately rather than reactively.

**H5 implication**
- Orientation is a real cognitive function, not merely a Dashboard label;
- Triage should allocate attention by potential bearing on the user's maintained view, not raw activity;
- adaptive depth is justified only if it reduces unnecessary processing without hiding material uncertainty.

### P3 — Competing Explanations Protect Against Premature Closure

**Primary roots**
- clinical differential diagnosis and diagnostic uncertainty
- Analysis of Competing Hypotheses / intelligence analysis
- Research Lab requirement for competing explanations, contrary evidence, and discriminative value

**Core belief**

Evidence that is compatible with the preferred explanation may be weak if it is also compatible with alternatives. Strong reasoning asks what evidence actually discriminates among plausible explanations.

**H5 implication**
- Differential / competing-scenario lenses are not optional decoration in ambiguous high-consequence cases;
- the system should support `what else could explain this?` and `what evidence would separate them?`;
- H5 must not turn one system narrative into the default truth simply because it is coherent.

### P4 — Stable Semantic Coordinates Reduce Cognitive Reorientation

**Primary roots**
- information architecture / wayfinding and predictable interaction
- object-centered operational systems
- Research Lab process–object separation and Design Lab cross-Lab semantic boundaries

**Core belief**

Dynamic content can change while the user's semantic coordinates remain stable. A system that adapts without stable object / scope / location cues creates reorientation cost and makes learning difficult.

**H5 implication**
- `Scope`, `Mode`, active `Question`, provenance, and return path must remain discoverable;
- stable spaces should represent durable semantic responsibilities, not transient features;
- capabilities such as News, AI, Evidence, Scenario, Relationship, History should not create competing top-level destinations unless they own distinct persistent meaning.

### P5 — Adaptation Should Augment Human Work, Not Seize Control

**Primary roots**
- mixed-initiative HCI
- DL-DR-0001 Human–AI Authority Boundary
- adaptive-interface research emphasizing uncertainty, predictability, user control, and timing

**Core belief**

Automation is valuable when it adds meaningful benefit while preserving understandable control and respecting uncertainty about user goals.

**H5 implication**
- Adaptive Reasoning Canvas may compose relevant lenses, but may not silently change semantic ownership or user Judgment;
- adaptation must be explainable enough to predict and recover from;
- fixed shell + adaptive canvas is preferred over unconstrained generated UI.

### P6 — Expectations Are Temporal and Revisable

**Primary roots**
- forecasting / calibration / revision workflows
- Research Lab predictive-claim boundaries
- decision postmortem / expectation-versus-reality disciplines

**Core belief**

A forward belief should be treated as a time-stamped, conditional expectation that can be revised, reaffirmed, become stale, and later be compared with reality.

**H5 implication**
- Current View, Change, Future Scenario, and Outcome / Learning should be connected rather than isolated feature silos;
- `reviewed and retained` must differ from `not revisited`;
- forecast probability, Research credibility, user conviction, and investment attractiveness must remain distinct.

### P7 — Understanding / View and Decision Context Must Remain Semantically Distinct

**Primary root**
- Approved Research semantic boundary and DL-DR-0002

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

**Core belief**

Company-level understanding or Investment View is not the same object as a portfolio-specific judgment.

**H5 implication**
- Decision Context deserves a distinct semantic responsibility;
- portfolio, valuation, alternatives, horizon, opportunity cost, and constraints must not silently rewrite company truth;
- comparison can consume Investment Views without overwriting them.

---

## 5. H5 Component Genealogy Matrix

| H5 component | Immediate job | Main roots | Source-domain pattern | Explicit non-transfer boundary | Main hypothesis | Primary failure signal |
|---|---|---|---|---|---|---|
| **Orientation** | Allocate scarce attention | P2, P1 | portfolio monitoring + incident triage + situation awareness | do not import urgency / incident emotional framing | users can find what deserves review faster without mistaking activity for importance | users chase salient noise, misunderstand Quiet as proven-safe, or still inspect everything |
| **Investment Workspace** | Maintain a continuous company-level view | P1, P4, P7 | company research hub + persistent object view | do not expose enterprise ontology or call the state cross-Lab Judgment | continuity improves understanding and change interpretation | becomes a maintenance burden, anchors users, or duplicates research everywhere |
| **Explore** | Preserve question/theme/relationship inquiry before commitment | P1, P3, P4 | investigation case + object/link exploration | must not become a catch-all for every deep feature or a second Research Lab | open inquiry can move across objects while preserving why the investigation exists | users cannot predict whether work belongs in Investment vs Explore; duplication grows |
| **Decision Context** | Combine view with portfolio-specific constraints | P7, P1 | portfolio allocation / contextual decision support | do not convert into automatic recommendation/execution rules | explicit context produces clearer judgments without corrupting company view | users cannot distinguish company facts/view from portfolio-specific recommendation |
| **Adaptive Reasoning Canvas** | Assemble the reasoning lenses relevant to the active problem | P5, P2, P4 | mixed-initiative UI + contextual AI | must not become unconstrained generated UI | dynamic composition reduces navigation and irrelevant detail while retaining orientation | users cannot predict where information is, reorientation time rises, or AI hierarchy feels authoritative |
| **Scope / Mode / Question / Return Path** | Maintain stable coordinates during adaptation | P4, P2 | wayfinding + predictable UI + situation awareness | labels need not become permanent top-nav items | explicit coordinates preserve location awareness and interruption recovery | users cannot state where they are, what they are doing, or how to resume |
| **Differential / Competing View Lens** | Prevent premature closure | P3, P1 | differential diagnosis + ACH | do not imply mutually exclusive diagnoses or fake probability ranking | alternatives and discriminating evidence improve challenge quality | users receive more complexity without identifying better discriminating evidence; preferred narrative still dominates |
| **Scenario / Future Lens** | Project conditional futures and growth-path conditions | P6, P1 | forecasting + scenario planning | probability must not masquerade as credibility; deterministic future is not default | conditional futures improve forward comparison and revision | false precision, stale forecasts, or users confuse prediction with investment attractiveness |
| **Triage → Focused Review escalation** | Match depth to consequence / ambiguity | P2, P5 | incident triage + adaptive review | not every signal becomes a task or approval request | selective depth reduces burden while preserving consequential review | Focused Reviews become inbox workload or material issues are hidden |
| **Provenance / Lineage** | Preserve why the current state exists and how it changed | P1, P6, P4 | Research provenance + forecast history + incident timeline | provenance should not overwhelm first view | traceable change improves trust, correction, and learning | users ignore it entirely or cannot reconstruct material reasoning when needed |
| **Human–AI authorship separation** | Keep System Synthesis distinct from user-owned View | P5 + DL-DR-0001 | mixed initiative + causal user control | visual simplicity may not erase semantic authorship | AI can do more work without silently becoming the user's belief | users attribute system synthesis to themselves or feel required to agree |

---

## 6. Evaluation Readiness Gap Found in Batch 04

Batch 04 mainly asked:

- Which architecture handled more scenarios?
- Which looked easier to navigate?
- Which preserved context?

That is useful **comparative exploration**, but it is not sufficient causal evaluation because:

1. H5 is a composition of multiple ideas; a good outcome does not identify which component caused it.
2. Source-domain assumptions were not explicit enough to detect cargo-cult transfer.
3. Philosophy-level conflicts could be hidden by locally attractive interaction patterns.
4. Component dependencies were not isolated.
5. User-visible failure signals were not predeclared.
6. H1 / H2 were architecture-level challengers, but there were no **H5 ablations** to test whether individual H5 elements earn their complexity.

Therefore the next prototype should evaluate **components and interactions**, not merely ask whether users prefer H5.

---

## 7. Workstream-Local Design Evaluation Contract v0.1

For each material H5 experiment, record:

```text
Evaluation Target + Version
+ Intended Cognitive Job
+ Scope / User Context
+ Parent Principle / Genealogy
+ Design Hypothesis
+ Main Challenger / Counter-hypothesis
+ Expected Observable Effect
+ Material Failure Signal
+ Unassessed Areas
+ Test / Evidence Method
+ Re-evaluation Trigger
→ Structured Design Evaluation Result
```

This is intentionally **workstream-local**. It is not yet a permanent Design Lab Evaluation Methodology.

If repeated use proves valuable across workstreams, promotion can be considered through the existing Design Knowledge Lifecycle.

---

## 8. Evaluation Dimensions for H5

### E1 — Semantic / Authority Integrity

Questions:
- Can the user distinguish System Synthesis, My Investment View, Decision Context, Judgment, and Decision where material?
- Does any adaptive composition silently promote Research/System output into the user's view?
- Does Explore accidentally claim Research authority?

**Hard failure:** violation of DL-DR-0001 or DL-DR-0002.

### E2 — Orientation & Wayfinding

Questions:
- Can users identify current Scope, Mode, Question and return path?
- After interruption, can they resume without reconstructing the entire path?
- Can they predict where a task belongs without knowing internal feature names?

### E3 — Attention Allocation

Questions:
- Does Orientation reduce unnecessary inspection?
- Can users understand why an item was prioritized?
- Do they distinguish low current priority from `proven unimportant`?

### E4 — Sensemaking / Understanding

Questions:
- Can users explain what changed and why it matters to the current Investment View?
- Can they connect evidence to affected drivers / risks / conditions?
- Does persistent state reduce repeated reconstruction without excessive anchoring?

### E5 — Alternative / Challenge Quality

Questions:
- Do users consider plausible alternatives when ambiguity is material?
- Can they identify evidence that discriminates among alternatives?
- Does the Differential lens reduce premature closure rather than merely add cards?

### E6 — Future Reasoning & Calibration

Questions:
- Can users distinguish current state, future scenario, scenario conditions, and later outcome?
- Can they distinguish probability from credibility and attractiveness?
- Can they recognize stale versus reaffirmed expectations?

### E7 — Adaptive UI Safety

Questions:
- Does adaptation materially reduce irrelevant navigation / detail?
- Is the composition predictable enough to learn?
- Can users understand why a lens appeared?
- Does the adaptive canvas preserve user control and authorship?

### E8 — Context Transfer & Continuity

Questions:
- Can an investigation move `Explore → Investment` without losing question/evidence provenance?
- Can `Investment → Decision Context` preserve company View without mutating it?
- Is information duplicated or coherently referenced?

### E9 — Cognitive Cost / Complexity Budget

Questions:
- Does each added lens earn its complexity?
- Is H5 materially better than the simpler H1 challenger on real tasks?
- Does novice performance collapse while expert flexibility improves?

### E10 — Learning / Revision Value

Questions:
- Can users reconstruct why a View changed?
- After reality unfolds, can they identify which assumption / scenario / interpretation failed?
- Does history improve future judgment rather than create archival clutter?

---

## 9. Challenger and Ablation Set

Do not test only `H5 vs H1 vs H2`.

The next prototype program should include:

### C0 — H1 Minimal Challenger

Tests whether H5 complexity is actually necessary.

### C1 — H5 Full

Stable spaces + Scope / Mode / Question + adaptive canvas.

### C2 — H5 without explicit Mode

Tests whether Mode materially improves orientation or merely adds jargon.

### C3 — H5 with Fixed Canvas

Same semantic spaces, but no question-driven dynamic lens composition.

Tests whether adaptation adds value beyond good conventional IA.

### C4 — H5 without explicit Explore space

Theme/question investigation appears contextually from Orientation / Investment.

Tests whether Explore earns permanent semantic status.

### C5 — H5 without Differential lens

Tests whether competing-explanation structure materially improves mixed/ambiguous cases.

Not all variants need full implementation simultaneously. Use the smallest experiment that isolates a material hypothesis.

---

## 10. Evaluation Ladder

### Stage 0 — Semantic / Authority Preflight

Before user testing:
- Research ↔ Design semantic consistency
- authorship boundary
- component genealogy review
- obvious contradiction / duplication audit

### Stage 1 — Expert / Persona Adversarial Walkthrough

Use intentionally different reasoning styles:
- discretionary investor / analyst
- trader / fast-monitoring user
- quant / structured evidence user
- diagnostic-style reasoner
- novice retail investor
- skeptical Design Critic / Accessibility reviewer

Goal: find structural failure, not vote on preference.

### Stage 2 — Task-level Prototype Test

Examples:
- 3-minute morning review
- first-time company understanding
- mixed earnings
- theme investigation
- rotation comparison
- mobile interruption / resume

Measure observable navigation / comprehension failures before visual polish.

### Stage 3 — Component Ablation Tests

Compare H5 Full against targeted removal variants to determine whether complexity earns measurable value.

### Stage 4 — Judgment-Support Stress Test

Use ambiguous cases where:
- salient evidence is misleading;
- system and user disagree;
- two explanations fit the same evidence;
- important evidence is missing;
- a future scenario becomes stale;
- portfolio context changes while company Understanding does not.

Goal: test reasoning quality and semantic boundaries, not investment return accuracy.

### Stage 5 — Longitudinal / Repeated-use Test

Only after earlier stages survive.

Test whether:
- Investment View continuity remains useful over weeks;
- alerts / Focused Reviews become workload;
- users learn the IA;
- adaptive composition becomes more predictable or remains confusing;
- provenance and history provide real learning value.

---

## 11. Philosophy-Mutation Guard for Future H5 Changes

When modifying H5, classify the change:

### Type A — Representation detail

Example: card ordering, icon, local disclosure.

If the cognitive job and semantic boundary remain unchanged, delegated modification is appropriate.

### Type B — Mechanism change

Example: replacing explicit Scope with automatic inference; removing Differential; merging Explore into Investment.

Required review:
1. Which H5 hypothesis changes?
2. Which source principle / cognitive problem was that mechanism serving?
3. Is the original problem no longer material, or is another mechanism serving it better?
4. What new failure mode appears?
5. Which evaluation must be repeated?

### Type C — Philosophy / Authority change

Examples:
- system prediction becomes the default user View;
- Decision Context is merged into company truth;
- alternatives are removed because one model is `best`;
- adaptive AI controls navigation without stable recovery.

These may affect Approved cross-Lab / Human–AI boundaries or Design Purpose and require escalation rather than local UI iteration.

---

## 12. Current Evaluation Readiness Assessment

### Before this Batch

**Not sufficiently ready for H5 promotion evaluation.**

The Design Lab had a strong hypothesis and good cross-domain ingredients, but insufficient genealogy and component-level falsification structure.

### After this Batch

**Conditionally ready for controlled H5 prototype evaluation.**

Ready to test:
- component necessity;
- interaction mechanisms;
- semantic boundaries;
- wayfinding;
- challenge quality;
- adaptation safety.

Not yet ready to claim:
- final Product IA;
- proven improvement in real investment outcomes;
- universal novice/expert fit;
- durable Design Knowledge promotion;
- an Approved Design Lab Evaluation Methodology.

---

## 13. Recommendation

Pause screen-detail convergence and run the next prototype as an **evaluation instrument**, not as a near-final product mockup.

The next prototype should make H5's genealogy testable by explicitly implementing:

1. stable semantic spaces;
2. visible Scope / Mode / Question / return path;
3. adaptive vs fixed canvas variants;
4. Explore-present vs Explore-absent variant where useful;
5. Differential-present vs Differential-absent ambiguous case;
6. interruption / resume state;
7. clear System / User / Decision Context boundaries.

**Recommendation Strength: Very Strong.**

---

## 14. CEO Critical Decision

**None in this Batch.**

This Batch improves Design Lab evaluation preparedness under already approved boundaries. It does not change Product IA, Design Purpose, or Human–AI authority.

---

## 15. Reference Roots

Internal authority:
- `research_lab/01_methodology/research_methodology.md`
- `research_lab/02_evaluation/evaluation_methodology.md`
- `design_lab/01_operating_system/knowledge_lifecycle.md`
- `design_lab/04_decision_records/DL-DR-0001_human_ai_judgment_authority.md`
- `design_lab/04_decision_records/DL-DR-0002_cross_lab_judgment_semantic_boundary.md`

External conceptual roots used for genealogy:
- Mica Endsley, *Toward a Theory of Situation Awareness in Dynamic Systems* (Human Factors, 1995): https://doi.org/10.1518/001872095779049543
- Richards J. Heuer Jr., *Psychology of Intelligence Analysis* (CIA Center for the Study of Intelligence): https://www.cia.gov/resources/csi/books-monographs/psychology-of-intelligence-analysis-2/
- Clinical reasoning / uncertainty review: https://pmc.ncbi.nlm.nih.gov/articles/PMC8015765/
- Eric Horvitz, *Principles of Mixed-Initiative User Interfaces* (CHI 1999): https://doi.org/10.1145/302979.303030
- W3C WCAG 2.2, Predictable interaction: https://www.w3.org/WAI/WCAG22/Understanding/predictable.html

Product-pattern sources remain documented in Batch 02 and Batch 03.