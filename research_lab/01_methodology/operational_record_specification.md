# Stock_vis Research Lab Operational Record Specification

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-08-28  
**Owner:** Stock_vis Research Lab  
**Approval:** Approved by Project Owner on 2026-08-28  
**Effective Date:** 2026-08-28

## 1. Purpose

The purpose of the Operational Record Specification is to define the minimum semantic contract by which the Stock_vis Research Lab preserves operational research state, epistemic object state, evaluation history, evidence identity, and material relationships in a form that supports continuity, reuse, re-evaluation, lineage, and future machine-readable implementation.

This specification operationalizes recordkeeping obligations already implied by the Research Methodology, Evaluation Methodology, Knowledge and Understanding Framework, and Terminology Governance. It does not redefine Research Claims, Research Knowledge, Understanding, Evaluation, Evidence, or the research lifecycle.

The specification is designed to prevent several recurrent operational failures:

- research state being trapped in transient chat or agent context;
- the same Claim or Understanding being copied into multiple records that later drift apart;
- evaluation rationale being confused with the epistemic object being evaluated;
- source identity being confused with how Evidence bears on a particular Claim;
- historical evaluations being silently overwritten by later evaluations;
- temporal mismatch being hidden when comparing observations or reported metrics;
- unknown, unassessed, or non-comparable outcomes being forced into artificial conclusions;
- provenance and dependency being stored too weakly to reconstruct material warrant or revision impact; and
- implementation choices such as YAML, database tables, or graph technology becoming de facto semantic authority.

## 2. Scope and Authority

The Operational Record Specification governs the minimum semantic responsibilities of operational research records and the boundaries among those records.

This document is the canonical Authority Source for the **minimum operational record semantics and separation rules** defined here. That authority is subordinate to the Primary Authorities that define the substantive meaning of the concepts being recorded.

It governs:

- Research Case records;
- operational records representing epistemic objects;
- Evaluation Records as persistent representations of completed or material evaluations;
- Evidence References;
- qualified material references and dependencies among records;
- minimum temporal distinctions when material;
- version and lineage preservation at the record level;
- reconstructability of Material Warrant Trace views; and
- proportional recording obligations.

This specification does **not** hold substantive authority over the meaning of Research Claim, Research Knowledge, Understanding, Evidence, Evaluation, Research Trigger, Research Problem, Research Question, or other upstream concepts. Those meanings remain governed by their existing Primary Authorities and Authority Sources.

The authority boundary is:

```text
Knowledge & Understanding Framework
→ defines epistemic object meanings and boundaries

Research Methodology
→ defines research lifecycle and process meanings

Evaluation Methodology
→ defines evaluation meanings and requirements

Operational Record Specification
→ defines how material operational meaning is persistently
  separated, referenced, and reconstructable

Future ontology / database / graph / agents / software
→ implement the approved record semantics
```

The Operational Record Specification is implementation-neutral. A future physical representation may vary while remaining compliant with the same semantic contract.

## 3. Governing Principles

### 3.1 One Canonical Operational Home Per Material Information Element

A material piece of operational information should have one canonical operational home. Other records should reference that information rather than maintain competing canonical copies.

This is a **record-resolution rule**, not an assignment of Terminology Governance Primary Authority and not a declaration that the recorded content is scientifically true. Substantive semantic authority and epistemic warrant remain governed by their legitimate upstream authorities.

For example:

- the canonical operational representation of a Claim's current content belongs with the record representing that epistemic object;
- why the Claim was evaluated as strong or weak belongs with the relevant Evaluation Record;
- why the research undertaking exists and where it is in its lifecycle belongs with the Research Case; and
- the identity, location, and provenance of an evidential source belong with the Evidence Reference.

Summaries and labels may be duplicated for readability, but they are non-canonical restatements unless explicitly designated otherwise.

### 3.2 Process, Object, Evaluation, and Evidence Must Remain Distinguishable

Research activity, epistemic objects, evaluation activity/results, and evidential sources are related but distinct.

A Research Case is an operational container and continuity record. It is not itself Research Knowledge or Understanding.

An Epistemic Object Record is a record representation of an epistemic object. It is not a new epistemic category and does not create epistemic status by existence.

An Evaluation Record characterizes a target object/state for a particular evaluation purpose. It is not the target object itself.

An Evidence Reference identifies and preserves material identity and provenance for an evidential item or source artifact. It does not by itself determine how that Evidence bears on a Claim.

### 3.3 Reconstructability Over Exhaustiveness

The Research Lab does not require storage of every intermediate thought, discarded idea, message, or reasoning step.

Records should preserve enough material information that a future researcher or agent can, when necessary:

- understand why the research exists and its current state;
- resolve the current content and state of material epistemic objects;
- determine why a material evaluation reached its conclusion;
- identify important supporting, challenging, qualifying, or dependent warrant;
- reconstruct material lineage and revision impact; and
- determine what should be re-evaluated when a material dependency changes.

### 3.4 Recording Is Proportional

The semantic contract is common, but record depth should be proportional to epistemic consequence, complexity, uncertainty, reuse, and difficulty of reversal.

A simple reported fact may require only lightweight scope, source, evaluation, and re-evaluation information. A complex causal or comparative result may require richer assumptions, alternatives, dependency, normalization, and lineage.

The specification must not become a blank-filling checklist. A semantic obligation that is not material to a particular object or evaluation need not be manufactured merely for apparent completeness.

### 3.5 Historical States Must Not Be Silently Overwritten

Material revisions to epistemic objects, evaluations, and research state must preserve sufficient history for later interpretation.

A completed Evaluation Record should not be materially rewritten merely because new Evidence later changes the assessment. A new evaluation should normally represent the new assessment, while the target object may reference the currently applicable evaluation.

### 3.6 Unknown and Non-Comparable Are Legitimate Recorded Outcomes

The record system must be able to preserve legitimate assessment or research outcomes such as Unknown, Unassessed, Not Material, Out of Scope, and Not Comparable when warranted.

These labels do not all denote the same kind of epistemic state. Their substantive meanings remain governed by the relevant methodology. The record requirement is that they must not be collapsed into false certainty or forced completion.

Missing evidence must not be silently replaced by estimation or inference merely to complete a table or comparison.

## 4. Minimum Logical Record Architecture

The minimum logical architecture is:

```text
Research Case
     │
     ├── references
     ▼
Epistemic Object Records
Claim / Research Knowledge / Understanding
     │
     ├── evaluated by
     ▼
Evaluation Records

Evidence References
     │
     └── bear on epistemic objects
          through qualified material relations

Material relations
     ↓
Material Warrant Trace
(reconstructable / derived view)
```

These are **logical semantic responsibilities**, not a requirement that every ephemeral Claim, every Evidence item, or every lightweight research action instantiate a separate persistent file, row, or graph node. Persistence and record depth remain proportional to materiality and reuse needs.

In particular, an Evidence Reference may later be represented as a shared first-class object, an embedded structured reference, or another physical form, provided its required semantics remain resolvable.

Governance and Decision Records may be linked when research creates material consequential decisions, but this specification does not define the complete CEO Decision Packet or downstream decision-support schema.

## 5. Research Case Record

### 5.1 Function

A Research Case Record answers:

> Why does this research undertaking exist, what is its declared scope, where is it now, and what should happen next?

A Research Case is an operational continuity container. It must not be used as the canonical location for detailed epistemic content or evaluation reasoning.

### 5.2 Minimum Semantic Responsibilities

A persisted material Research Case should make its identity and current framing resolvable. Where applicable and material, it should also make resolvable:

- Case identity and title;
- originating material Research Trigger or Triggers;
- Research Problem;
- Primary Research Question or Questions;
- declared research scope;
- material Research Design choices;
- current lifecycle state;
- references to material Claims, Knowledge, Understandings, Models, or other research outputs;
- important unresolved questions or gaps;
- next action;
- why the next action matters;
- which material objects or questions the next action is expected to affect; and
- material revision history of the Case framing, scope, or design.

Secondary questions, methods, workstreams, assignees, or operational notes may be included where useful but are not universal semantic requirements.

### 5.3 Boundary

The Research Case should not become the canonical home for:

- the exact current content of a Claim, Knowledge item, or Understanding;
- detailed evaluation reasoning;
- complete evidence metadata; or
- downstream decision authority.

Case scope and epistemic-object scope are distinct. An object must not automatically inherit the entire scope of the Case merely because it was produced within that Case.

## 6. Epistemic Object Record

### 6.1 Function

An Epistemic Object Record answers:

> What epistemic content is the Research Lab currently representing, under what scope and conditions, and what is its current relevant status and lineage?

The term **Epistemic Object Record** is an operational record category. It does not introduce a new epistemic object type. The substantive object types remain those authorized by the Knowledge and Understanding Framework and related authorities.

### 6.2 Minimum Semantic Responsibilities

Any persisted Epistemic Object Record must make object identity, substantive object type, and its canonical operational representation resolvable.

Where applicable and material, it should also make resolvable:

- object identity;
- substantive object type, such as Research Claim, Research Knowledge, or Understanding;
- canonical content or canonical structural representation appropriate to the object type;
- object/content version or state identity;
- current admission, lifecycle, or epistemic status **where such a status is defined by the applicable upstream authority**;
- scope;
- material conditions and boundaries;
- references to current or material Evaluation Records;
- material lineage, including prior state, revision, restriction, split, merge, supersession, or replacement when applicable;
- material dependencies when applicable; and
- applicability, modality, role, or other routing metadata when materially necessary.

This specification does not define a new exhaustive lifecycle or epistemic-state vocabulary.

Short labels, aliases, display summaries, and convenience metadata may be stored, but they must not silently replace canonical content.

### 6.3 Content, Object Type, Research Role, Admission Status, and Evaluation Conclusion

For bounded assertions, the canonical record should preserve the assertion at a strength and scope that can be independently evaluated and revised.

The following must remain distinguishable when material:

```text
semantic content
≠ substantive object type
≠ research role
≠ admission / lifecycle status
≠ evaluation conclusion
```

For example, a Research Claim may take a Hypothesis role, later receive an Evaluation conclusion such as Strongly Supported, and may subsequently have its bounded content admitted into Research Knowledge under the applicable methodology. These distinctions must not be collapsed into one field or label.

### 6.4 Understanding

An Understanding representation may require more than one sentence. Where material, it should preserve or reference:

- the current explanatory or reasoning structure;
- its admitted Research Knowledge warrant base;
- material relationships among components;
- important conditions and boundary conditions;
- unresolved alternatives;
- important uncertainty and gaps; and
- material dependencies.

The exact physical representation of Understanding remains a Non-Decision.

### 6.5 Boundary

The Epistemic Object Record should not become the canonical home for:

- the full reasoning of every evaluation;
- detailed evidence-source metadata;
- Research Case workflow state; or
- downstream consequential decisions.

## 7. Evaluation Record

### 7.1 Function

An Evaluation Record answers:

> Why was this particular target object/state evaluated this way for this purpose, scope, and time?

Evaluation meaning and profiles remain governed by Evaluation Methodology. This specification governs the durable separation and referencing of the resulting record.

### 7.2 Minimum Semantic Responsibilities

A material Evaluation Record should make resolvable, consistent with Evaluation Methodology:

- Evaluation identity;
- target object identity and exact version/state;
- Evaluation Purpose;
- evaluation time;
- applicable Evaluation Methodology/profile/criteria version where material;
- declared evaluation scope and context;
- material supporting findings;
- material weaknesses and limitations;
- material alternatives or conflicts when applicable;
- unknown, unassessed, or out-of-scope areas when applicable;
- material assumptions and dependencies;
- evaluation conclusion;
- material Evidence and warrant references;
- the degree or form of challenge when material; and
- Re-evaluation conditions.

Evaluation provenance, including agent, reviewer, model, or process identity, should be preserved when material to reproducibility, accountability, or later review.

### 7.3 Versioned History

A completed material Evaluation Record should normally remain historically stable. A materially changed assessment caused by new Evidence, new object state, changed scope, changed Evaluation Purpose, or changed criteria should normally create a new Evaluation Record rather than silently rewriting the historical evaluation.

Prior evaluations remain reusable only when compatibility with the current target state, purpose, context, criteria, and Evidence remains adequate under Evaluation Methodology.

### 7.4 Boundary

The Evaluation Record should reference rather than duplicate the target object's canonical content when a stable object/version reference is available.

It must not become the canonical source for Research Case lifecycle state or Evidence identity.

## 8. Evidence Reference

### 8.1 Function

An Evidence Reference answers:

> What evidential item or source artifact is being referenced, where did it come from, what exactly can be retrieved, and what material provenance or transformation history does it have?

An Evidence Reference is a record/reference representation. Its existence does not itself create Evidence, establish evidential quality, or require that every Evidence item become a standalone persisted object.

### 8.2 Minimum Semantic Responsibilities

When an Evidence Reference is material, it should make resolvable:

- reference identity where needed for reuse;
- evidential item, source, or artifact identity;
- Evidence kind or modality where useful;
- source version, reporting period, or publication date when material;
- exact retrievable locator, such as URL, repository path, document/page/table/section, dataset/version, or another stable locator;
- provenance and source ancestry when material;
- observation, retrieval, or access time when temporally material;
- material transformation or computation chain when the Evidence has been derived or transformed;
- the source-defined measurement or metric definition when interpretation depends materially on that definition; and
- the relevant fragment, field, range, or location when necessary for reproducibility.

### 8.3 Evidence Identity Is Distinct From Evidence–Claim Relation

An Evidence Reference must not treat `supports Claim C1` or `challenges Claim C2` as an intrinsic property of the Evidence.

The same Evidence may support one Claim, qualify another, challenge a third, or be irrelevant to another depending on scope and inference.

How Evidence bears on a Claim belongs in a qualified material relation or the relevant Evaluation Record, under Evaluation Methodology.

### 8.4 Evidence Reference Does Not Confer Credibility

Source identity, publication, institutional reputation, or record presence does not by itself establish evidential quality or Research Knowledge status.

Evidence evaluation remains governed by Evaluation Methodology.

## 9. Qualified Material Relations

The record architecture must preserve material relationships sufficiently for epistemic dependencies and warrant paths to be reconstructed.

Material relationships may include, when appropriate:

- an Evaluation Record evaluating a specific object version;
- Evidence bearing on a Claim or Knowledge item;
- one epistemic object materially depending on another;
- a Claim or other object state being revised from a prior state;
- Knowledge contributing to an Understanding;
- a Model or Model Output materially contributing to Evidence or a Claim; and
- a material downstream object depending on an upstream state.

The exact relation vocabulary is a Non-Decision of v1.0. Where a relation is material, its meaning, source, target, scope/context, and basis should be resolvable enough to prevent ambiguous or circular interpretation.

### 9.1 Evidence–Claim Relations Are Qualified

When Evidence bears on a Claim, the relation should preserve material context such as support, challenge, qualification, scope fit, directness, or discriminative role as required by Evaluation Methodology.

The relation belongs neither to the Evidence alone nor to the Claim alone. It is a qualified epistemic relation between them in a stated evaluation context.

### 9.2 Comparative and Normalization Relations

Where comparison or normalization introduces new epistemic structure, the comparison basis should be recoverable when material, including such elements as:

- compared objects/entities;
- metric or measurement meaning;
- measurement period;
- unit or currency normalization;
- temporal alignment;
- inclusion/exclusion rules; and
- material transformation or normalization operation.

These are conditional requirements, not universal fields for all research.

## 10. Material Warrant Trace as a Derived View

Material Warrant Network remains the conceptual cross-layer backbone defined by Evaluation Methodology.

This specification does not require a separate authoritative `Warrant Trace` document for every research undertaking.

A Material Warrant Trace should be reconstructable, when needed, from canonical records and qualified material relations, for example:

```text
Evidence P1
  ↓ bears on
Research Claim C1 v2
  ↓ evaluated by
Evaluation E3
  ↓ may support an admission action concerning the bounded content
Research Knowledge K1
  ↓ contributes to
Understanding U1
```

This diagram expresses traceable relationships among distinct records and epistemic roles. It does **not** imply that one persistent object literally transforms from Research Claim into Research Knowledge.

The derived view may be rendered as text, graph, table, database query, or another representation. The view itself does not become a competing source of truth unless explicitly designated by future approved work.

## 11. Temporal Semantics

Operational records must not silently collapse materially different time concepts.

Where relevant, the architecture should distinguish such temporal meanings as:

- Research As-of Date;
- Evidence publication or observation date;
- measurement or reporting period;
- object version/effective time;
- Evaluation time; and
- validity or applicability period.

Not every record requires every time field. The requirement is that material temporal differences remain resolvable and are not hidden by one generic timestamp.

## 12. Common Core and Conditional Extensions

The four logical record categories share a minimum semantic core, but research-type-specific needs may require conditional extensions.

Examples include:

- causal research: competing explanations, causal bridges, boundary scenarios;
- comparative research: source-defined metric meaning, normalization, comparison basis, temporal alignment;
- predictive research: horizon, target definition, forecast vintage, calibration context;
- model-derived research: Model version, Model Use, input state, run configuration, and output uncertainty.

The existence of conditional extensions does not justify expanding the universal core until every possible research modality is represented.

## 13. Governance and Decision References

When sufficiently evaluated research creates a material consequential governance issue, Research Cases or epistemic objects may reference the relevant CEO governance artifact or Decision Record.

This specification does not define the complete CEO Decision Packet schema. Consequential governance remains governed by Research Methodology and DR-0006.

A CEO governance artifact must not become a substitute for epistemic Evaluation or overwrite the canonical state of Research Knowledge or Understanding.

## 14. Operational Validation Basis and Limitation

The minimum architecture in this specification was developed and challenged through two heterogeneous pre-specification operational pilots before formal proposal:

1. a causal/composite research pilot involving evolving Claims, competing explanations, Understanding synthesis, and re-evaluation dependencies; and
2. a comparative corporate research pilot involving cross-entity metric normalization, temporal alignment, source-defined metric meaning, and legitimate `Not Comparable` outcomes.

Across both pilots, the following elements remained repeatedly necessary:

- Research Case continuity;
- separate records for epistemic objects;
- versioned Evaluation Records;
- Evidence identity/provenance preservation;
- material relationship traceability;
- scope and condition preservation;
- lineage and re-evaluation conditions; and
- proportional rather than uniform record depth.

These pilots occurred **before** the proposed specification existed and therefore were not persisted under the specification they helped generate. Their role is design-validation evidence for cross-case usefulness, not proof that the specification is complete or implementation-ready.

Further operational use after adoption remains necessary to challenge the specification, refine conditional extensions, and detect maintenance or handoff failures.

Pilot-specific factual details are not normative examples in this specification and may evolve independently as new Evidence arrives.

## 15. Re-evaluation and Reconsideration

Evaluation Methodology remains the canonical Authority Source for Re-evaluation Trigger and Reconsideration Trigger.

Changes in Evidence, object state, scope, criteria, or dependencies may trigger re-evaluation of affected records without automatically changing downstream conclusions.

The Operational Record Specification itself should be reconsidered if operational evidence shows, for example:

- record maintenance burden materially exceeding continuity, reuse, or re-evaluation value;
- repeated inability to reconstruct material warrant or dependency despite nominal compliance;
- persistent duplicate or conflicting canonical operational representations;
- a substantially simpler structure providing equivalent epistemic protection;
- repeated agent handoff failure caused by missing required semantics; or
- implementation experience demonstrating that a current semantic separation is unnecessary or incorrect.

A Reconsideration Trigger does not require revision. It requires review under the applicable governance process.

## 16. Boundaries and Non-Decisions

Operational Record Specification v1.0 intentionally does not decide:

- identifier formats or numbering schemes;
- Markdown, YAML, JSON, RDF, relational, property-graph, or other physical representation;
- repository directory layout for individual operational records;
- database tables or persistence technology;
- exact graph or relation vocabulary;
- whether every Evidence Reference must be persisted as a first-class database object;
- automatic versioning algorithms;
- synchronization or cache design;
- agent write permissions;
- exact admission workflow, reviewer counts, voting rules, or consensus algorithms;
- exact CEO escalation thresholds;
- CEO Decision Packet schema;
- user-interface representation;
- vector database or graph database use;
- ontology language; or
- investment decision rules.

Future implementations must preserve the approved semantic contract rather than silently redefine it.

## 17. Dependencies and Related Documents

This specification depends on and must remain consistent with:

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](research_methodology.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [DR-0006: Separate Epistemic Authority from Consequential Governance](../04_decision_records/DR-0006-separate-epistemic-authority-consequential-governance.md)
- [DR-0007: Adopt the Stock_vis Research Lab Operational Record Specification v1](../04_decision_records/DR-0007-adopt-operational-record-specification-v1.md)

Its adoption decision is recorded in DR-0007.

## 18. Change Log

### 1.0 — 2026-08-28

- Approved by Project Owner and made effective as the minimum implementation-neutral operational record semantic contract.
- Adopted the validated draft architecture without expanding its substantive semantic scope.
- Preserved all physical schema, identifier, graph, storage, agent, workflow, and UI choices as Non-Decisions.

### 1.0-draft — 2026-08-28

- Proposed a minimum implementation-neutral operational record architecture challenged across two heterogeneous research pilots.
- Distinguished Research Case, Epistemic Object Record, Evaluation Record, and Evidence Reference responsibilities without requiring one physical object per logical category.
- Established one canonical operational home per material information element while preserving upstream semantic authority.
- Defined Material Warrant Trace as a reconstructable derived view of canonical records and qualified material relations without implying literal Claim-to-Knowledge object transformation.
- Preserved versioned evaluation history, material temporal distinctions, explicit unknown/non-comparable outcomes, and proportional recording.
- Added conditional support for source-defined metric definitions and comparison/normalization basis without expanding the universal core.
- Recorded the limitation that pre-specification pilots validate cross-case usefulness but not completeness or implementation readiness.
- Preserved physical schema, identifier, graph, storage, agent, and UI choices as Non-Decisions.