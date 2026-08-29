# DR-0007: Adopt the Stock_vis Research Lab Operational Record Specification v1

**Record ID:** DR-0007  
**Status:** Approved  
**Decision Type:** Research Operations / Record Architecture  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-28  
**Approval:** Approved by Project Owner on 2026-08-28  
**Effective Date:** 2026-08-28  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Documents:** [Operational Record Specification](../01_methodology/operational_record_specification.md), [Research Methodology](../01_methodology/research_methodology.md), [Evaluation Methodology](../02_evaluation/evaluation_methodology.md)

## 1. Context

Research Methodology v1.1 and Evaluation Methodology v1.1 establish material traceability, versioned evaluation, epistemic separation, lineage, and re-evaluation requirements while intentionally leaving physical storage representation unresolved.

Operational use exposed a more specific need: research could be performed and evaluated successfully, yet important state remained distributed across transient conversational context. Without a minimum persistent record contract, future researchers or agents could struggle to determine:

- why a research undertaking exists and its current lifecycle state;
- the exact current content and scope of a Claim, Knowledge item, or Understanding;
- why a specific object/version received a particular evaluation;
- which evidential artifact was actually used and how it was defined;
- which upstream changes should trigger downstream review; and
- which historical evaluation or object state supported an earlier research or governance decision.

Two heterogeneous operational pilots were used to challenge candidate record structures before formalization.

The first involved causal/composite research with evolving Claims, competing explanations, Understanding synthesis, and material re-evaluation dependencies.

The second involved cross-company comparative research with metric normalization, temporal mismatch, source-defined measurement semantics, and legitimate `Not Comparable` outcomes.

Across both pilots, the same minimum separations repeatedly proved useful: Research Case continuity, epistemic-object state, Evaluation Records, Evidence identity/provenance, and qualified material relationships.

These pilots preceded the specification and were not persisted under it. They therefore provide design-validation evidence that the architecture generalizes beyond one research shape, but they do not establish that the specification is complete, implementation-ready, or already proven at scale.

The Research Lab therefore adopts an implementation-neutral operational record contract that preserves these semantics without prematurely fixing database, graph, ontology, or agent implementation.

## 2. Decision

The Stock_vis Research Lab adopts **Operational Record Specification v1.0** as the normative operational specification for minimum research-record semantics.

### 2.1 Adopt Four Minimum Logical Record Categories

The minimum logical record architecture is:

1. **Research Case** — preserves why a research undertaking exists, its declared scope, current lifecycle state, material unresolved issues, and next action.
2. **Epistemic Object Record** — preserves the canonical operational representation of a Research Claim, Research Knowledge item, Understanding, or other legitimately defined epistemic object without creating a new epistemic category.
3. **Evaluation Record** — preserves a versioned, purpose-bound evaluation of a specific target object/version/state.
4. **Evidence Reference** — preserves the identity, retrievable location, provenance, and material source-defined meaning of evidential items or artifacts.

These categories are **logical semantic responsibilities**, not a requirement that every instance become a standalone persistent file, database row, or graph node. Physical persistence and record depth remain proportional to materiality and reuse needs.

### 2.2 Adopt One Canonical Operational Home Per Material Information Element

A material operational information element should have one canonical operational home. Other records should reference rather than maintain competing canonical copies.

This is a record-resolution convention. It does not assign Terminology Governance Primary Authority and does not make the record itself an epistemic truth authority.

This principle is intended to prevent semantic drift as research scales across researchers, agents, documents, and future software.

### 2.3 Keep Evidence Identity Separate From Evidence–Claim Meaning

Evidence identity and provenance belong with the Evidence Reference.

Whether Evidence supports, challenges, qualifies, or is otherwise material to a particular Claim depends on the Evidence–Claim relation and evaluation context. That relation must not be stored as an intrinsic property of the Evidence itself.

### 2.4 Preserve Content, Role, Status, and Evaluation Separation

The record architecture must preserve the existing upstream distinction among:

```text
semantic content
≠ substantive object type
≠ research role
≠ admission / lifecycle status
≠ evaluation conclusion
```

An operational record must not imply that a Research Claim literally transforms into Research Knowledge merely because the same bounded content progresses through research and admission.

### 2.5 Preserve Versioned Evaluation and Epistemic History

Material historical evaluations and object states must remain reconstructable.

A later evaluation should not silently overwrite a materially different prior Evaluation Record merely because new Evidence or changed scope produces a new conclusion.

Material revision lineage should remain traceable in proportion to consequence.

### 2.6 Treat Material Warrant Trace as a Derived View

Material Warrant Network remains the conceptual cross-layer backbone defined by Evaluation Methodology.

Operational Record Specification v1.0 does not require a separate authoritative Warrant Trace document for every research undertaking.

Instead, Material Warrant Trace should be reconstructable from canonical records and qualified material relationships when needed for evaluation, reuse, impact analysis, or re-evaluation.

### 2.7 Preserve Proportionality and Legitimate Incompleteness

The same semantic contract applies across research types, but record depth is proportional to materiality, complexity, uncertainty, reuse, and consequence.

The architecture must preserve legitimate outcomes such as Unknown, Unassessed, Out of Scope, and Not Comparable rather than force artificial completion.

### 2.8 Preserve Implementation Neutrality

The decision does not fix identifier format, Markdown/YAML/JSON structure, folder layout, database tables, graph technology, relation taxonomy, ontology language, agent permissions, or UI.

Future implementations must implement the approved semantics rather than become the source of semantic authority.

## 3. Authority Boundary

Operational Record Specification v1.0 is subordinate to existing conceptual and methodological authorities.

It does not redefine:

- Research Claim, Research Knowledge, or Understanding;
- Evidence or Evaluation;
- Research Trigger, Research Problem, Research Question, or Research Design;
- Knowledge admission criteria; or
- consequential governance authority.

The Operational Record Specification is the canonical Authority Source only for the minimum **operational record semantics and separation rules** within its scope.

The authority structure is:

```text
Knowledge & Understanding Framework
→ epistemic object meaning

Research Methodology
→ research lifecycle meaning

Evaluation Methodology
→ evaluation meaning

Operational Record Specification
→ minimum persistent record semantics and separation

Future implementation
→ physical representation
```

## 4. Alternatives Considered

### 4.1 One Monolithic Research Document Per Case

Under this alternative, each research undertaking would store Case framing, Claims, Evidence, Evaluations, and Understanding in one document.

This approach is simple and human-readable but was not preferred because canonical Claim content, evaluation history, and Evidence metadata would be repeatedly copied when objects are reused across Cases. Long-term reuse and revision impact would become increasingly difficult.

### 4.2 Full First-Class Object Graph From the Start

Under this alternative, every Claim, Evidence item, relation, evaluation, dependency, and activity would immediately become a first-class graph object with fixed relation semantics.

This approach could provide strong machine readability but was not preferred because two pilots do not justify locking an ontology, relation taxonomy, storage model, or graph technology. Premature formalization could make implementation convenience silently determine research semantics.

### 4.3 Keep Records Informal Until Agent Architecture Is Built

Under this alternative, researchers and agents would continue using conversational summaries and ad hoc notes until the future agent workflow is defined.

This was not preferred because operational pilots already demonstrated that agent handoff, re-evaluation, and reuse require stable semantic separation before orchestration mechanics can be responsibly designed.

### 4.4 Separate Research Record and Evaluation Record Specifications

Under this alternative, record semantics would be split across separate Research and Evaluation specifications.

This remains possible in the future, but a unified Operational Record Specification is preferred for v1 because material research continuity depends on the interfaces among Case state, epistemic objects, evaluations, Evidence, and provenance. The document must nevertheless preserve the distinct upstream authorities of Research Methodology and Evaluation Methodology.

## 5. Rationale

The adopted architecture is the smallest structure that survived two materially different operational research pilots without requiring a technology commitment.

It supports:

- research continuity across sessions and agents;
- canonical operational representation of epistemic-object state;
- historical evaluation reproducibility;
- Evidence provenance and source-defined metric preservation;
- safe comparative and compositional reasoning;
- targeted re-evaluation after upstream change;
- future Knowledge and Understanding reuse; and
- later migration into document, relational, graph, ontology, or hybrid implementations.

It also preserves the Research Lab's existing principle that traceability should be sufficient to reconstruct material warrant and impact without storing every intermediate thought.

The pre-specification pilots are evidence of cross-case usefulness, not a claim of final completeness. Further operational use remains necessary and may trigger revision or reconsideration.

## 6. Expected Consequences

The Operational Record Specification is the minimum semantic contract for future operational record design.

Expected benefits include:

- less dependence on transient chat or agent memory;
- reduced duplication and semantic drift;
- clearer handoff among researchers and agents;
- easier identification of re-evaluation obligations;
- improved historical reproducibility;
- safer reuse of Research Knowledge and Understanding; and
- a more stable foundation for future agent workflow, ontology, and storage engineering.

Expected costs include:

- additional record maintenance;
- the need to preserve identity/version references across records; and
- some operational complexity compared with one free-form research note.

These costs should remain proportional and are themselves subject to future Reconsideration if maintenance burden exceeds epistemic value.

## 7. Operational Validation Evidence and Limitation

The specification was challenged through two pre-adoption pilots with different research structures.

The causal/composite pilot required:

- evolving Claim versions;
- competing explanations;
- material dependency tracking;
- Understanding synthesis; and
- re-evaluation triggers from new upstream Evidence.

The comparative pilot required:

- source-defined metric semantics;
- temporal alignment;
- cross-entity normalization;
- comparison-specific inference; and
- explicit preservation of non-comparable outcomes.

The same minimum logical record categories remained useful in both cases, while pilot-specific semantics could be handled as conditional extensions rather than universal fields.

Because both pilots predated this specification, they were not formally persisted using the adopted record contract. Their evidence is therefore sufficient to motivate a v1 semantic contract, but not sufficient to validate exact implementation, scaling behavior, maintenance burden, or completeness across all research modalities.

## 8. Non-Decisions

This decision does not establish:

- identifier formats or numbering schemes;
- Markdown, YAML, JSON, RDF, relational, property-graph, or other physical format;
- repository folder structure for operational records;
- database tables or storage engine;
- exact relation vocabulary or graph edge taxonomy;
- whether every Evidence Reference must become a first-class persisted database object;
- automatic versioning algorithms;
- exact agent write permissions;
- agent voting, reviewer counts, or admission consensus rules;
- exact CEO escalation thresholds;
- CEO Decision Packet schema;
- vector or graph database use;
- ontology language;
- user-interface design; or
- investment decision rules.

## 9. Required Follow-on Work

Subsequent operational work should:

- exercise the specification on additional research types;
- determine a lightweight human-readable representation for early use;
- test agent handoff using only canonical records and material references;
- identify the minimum relation vocabulary needed in practice;
- evaluate whether Evidence References should become universally first-class persisted objects;
- design storage and automation only after the semantic contract remains stable under further use; and
- revisit the specification if maintenance burden or handoff failures create a Reconsideration Trigger.

## 10. Related Documents

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](../01_methodology/research_methodology.md)
- [Stock_vis Research Lab Operational Record Specification](../01_methodology/operational_record_specification.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [DR-0006: Separate Epistemic Authority from Consequential Governance](DR-0006-separate-epistemic-authority-consequential-governance.md)