# Stock_vis Research Lab Research Candidate Registry

**Status:** Working / Operational Registry  
**Version:** 0.1  
**Last Updated:** 2026-09-04  
**Owner:** Stock_vis Research Lab  
**Normative Status:** None — this is an operational index, not Research Knowledge, an approved Research Case, a methodology, a priority commitment, or a start-date commitment  
**Canonical Role:** Current candidate discovery and operational disposition; substantive candidate content remains in the linked candidate document  
**Korean Companion:** [`research_candidate_registry_ko.md`](research_candidate_registry_ko.md)

## 1. Purpose

This registry preserves material Research Trigger Candidates and other potential research paths that should remain retrievable but are not currently active Research Cases.

A legitimate Trigger may be important enough to retain but not yet sufficiently validated, scoped, feasible, or timely to open as a Research Case. Leaving such candidates only in chat or an isolated handoff risks loss. Calling every retained candidate a backlog item or roadmap commitment risks implying approval, priority, and scheduling that have not occurred.

The registry therefore records, proportionally:

- the source candidate;
- its current operational disposition;
- whether a Research Case has been opened;
- why it is retained, deferred, merged, or closed;
- the conditions that should trigger renewed review; and
- any interim constraints that matter before research begins.

## 2. Interpretation and Boundaries

An entry means that a candidate has been recognized and intentionally retained for later review. Registry inclusion does **not** mean that:

- the proposed Research Problem has been validated;
- the candidate has been accepted as an approved Research Case;
- the proposed decomposition or terminology has been adopted;
- research has been scheduled or resourced;
- the candidate has priority over active work; or
- any candidate conclusion has entered Research Knowledge.

The linked candidate document is the canonical home for the candidate's substantive content and source observations. This registry is the canonical operational home for the candidate's current retention and disposition state.

Disposition wording in this v0.1 registry is operational and descriptive. It does not establish a fixed Research Methodology lifecycle vocabulary, identifier scheme, numerical priority scale, service-level commitment, or automated state machine.

Activation requires renewed triage under the then-current Research Methodology, review of applicable Authority Sources, confirmation that the underlying Evidence remains retrievable and representative enough for the intended inquiry, and a proportional Research Design when a Research Case is opened.

## 3. Current Registry

| Candidate | Origin | Current disposition | Research Case status | Review / activation condition | Canonical candidate record |
| --- | --- | --- | --- | --- | --- |
| News Evidence Quality and Processing Coverage | Stock_vis Design Lab | Retained; deferred for future Research Lab triage | Not opened and not approved | Revisit when sub-agent automation and Lab / cross-Lab operations are stable enough for a reproducible bounded audit, and when the news pipeline and Evidence handoff are sufficiently auditable | [English](news_evidence_quality_research_trigger_candidate.md) · [한국어](news_evidence_quality_research_trigger_candidate_ko.md) |

## 4. Candidate Detail — News Evidence Quality and Processing Coverage

**Registered:** 2026-09-04  
**Observed in:** NVDA / VRT Company Workspace real-data design pass  
**Trigger classes represented:** Failure, Knowledge Gap, User Need  
**Importance:** Material candidate; not a current research priority  
**Project Owner disposition:** Preserve the candidate and defer research until sub-agent automation and Lab operations are sufficiently stable  
**Epistemic implication:** None — this disposition does not validate the broad Research Problem or approve a Research Case

### 4.1 Why It Is Retained

The Design Lab observed opposite failure patterns that may matter to Research, Engineering, and Design:

- high processed volume can coexist with questionable apparent company relevance; and
- meaningful raw company events can coexist with very low processed coverage.

The observation is consequential because raw availability, processing coverage, company relevance, materiality, and decision usefulness can be mistaken for one another. The candidate also identifies interim Design guardrails that reduce harm while the issue remains unresolved.

### 4.2 Why It Is Deferred

The current sample does not establish whether the root cause is a localized Engineering defect, a serving/query problem, a data limitation, or a broader semantic and evaluation gap. Building a universal framework before a bounded audit would risk premature architecture.

The quality of that audit also depends on reproducible Evidence handoff, pipeline observability, stable cross-Lab responsibilities, and enough sub-agent operating maturity to preserve provenance, challenge initial interpretations, and distinguish Engineering remediation from Research work.

### 4.3 Conditions for Renewed Review

The candidate should be reviewed again when one or more of the following becomes true:

1. Sub-agent automation and Research Lab operating routines are stable enough to run and preserve a bounded, reproducible audit.
2. Cross-Lab handoff, provenance, data snapshots, and relevant news-pipeline stages are sufficiently accessible and auditable.
3. The relevance / coverage mismatch recurs across fresh companies or samples.
4. The mismatch becomes a material blocker for Company Workspace, Research Evidence use, or Engineering quality control.
5. A focused Engineering audit leaves unresolved semantic questions about company association, event identity, materiality, Claim-relative bearing, or abstention.

These are review conditions, not automatic start instructions. Renewed review may still result in reframing, merging, continued deferral, narrow Engineering remediation, or closure.

### 4.4 First Intended Action After Reactivation

The first action should remain the bounded pipeline and error audit recommended by the candidate, not immediate construction of a universal News Evidence framework.

The audit should:

1. reproduce the issue with fresh, stratified samples, including both processed and unprocessed records;
2. map relevant pipeline and serving stages while preserving provenance;
3. distinguish localized Engineering, data, ranking, and semantic-definition failure modes;
4. determine whether a genuine Research Problem remains; and
5. only then frame an approved Research Case, Question, and Research Design if warranted.

### 4.5 Interim Guardrails

Until renewed review:

- do not interpret raw-news count as Evidence quality;
- do not interpret processed-intelligence count as company relevance, materiality, or decision usefulness;
- keep raw availability and processing coverage distinguishable;
- do not claim that no news exists merely because processed coverage is sparse;
- do not automatically revise a user-owned Investment View from a news record alone; and
- preserve source, publication time, provenance, relevance limitations, and legitimate abstention where material.

## 5. Dependencies and Related Authorities

This registry and its current entry must remain consistent with:

- [Research Methodology](01_methodology/research_methodology.md)
- [Evaluation Methodology](02_evaluation/evaluation_methodology.md)
- [Operational Record Specification](01_methodology/operational_record_specification.md)
- [Sub-Agent Research Operating Model — Candidate](01_methodology/subagent_research_operating_model_candidate.md)
- [News Evidence Quality Research Trigger Candidate](news_evidence_quality_research_trigger_candidate.md)

The approved methodologies govern any future research activity. The Sub-Agent Research Operating Model remains experimental and is a readiness dependency, not a normative prerequisite created by this registry.

## 6. Maintenance Rule

A new registry entry should have, at minimum, a retrievable source artifact, current disposition, Research Case status, reason for retention or deferral, and review conditions.

When a candidate is activated, reframed, merged, deferred again, or closed, the registry should be updated without erasing material history. Detailed research state should move to the applicable Research Case record once a Case is opened rather than turning this registry into a substitute Research Case.

## 7. Change Log

### 0.1 — 2026-09-04

- Created the Research Candidate Registry as a non-normative operational index.
- Registered the Design Lab's News Evidence Quality and Processing Coverage candidate.
- Recorded the Project Owner's instruction to preserve the candidate and defer research until sub-agent automation and Lab operations are sufficiently stable.
- Defined condition-based review, bounded-audit-first reactivation, and interim guardrails without approving a Research Case or a universal News Evidence framework.
