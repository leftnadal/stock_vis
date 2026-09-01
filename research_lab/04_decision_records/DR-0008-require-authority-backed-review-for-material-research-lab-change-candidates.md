# DR-0008: Require Authority-Backed Review for Material Research Lab Change Candidates

**Record ID:** DR-0008  
**Status:** Approved  
**Decision Type:** Research Methodology / Governance  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-31  
**Approval:** Approved by Project Owner on 2026-08-31  
**Effective Date:** 2026-08-31  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Documents:** [Research Methodology](../01_methodology/research_methodology.md), [Terminology Governance](../01_methodology/terminology_governance.md), [Evaluation Methodology](../02_evaluation/evaluation_methodology.md), [Operational Record Specification](../01_methodology/operational_record_specification.md)

## 1. Context

Operational use of the approved Research Lab architecture revealed a recurring meta-level failure mode: a researcher or agent could identify a legitimate operational friction and too quickly interpret it as a new methodological or architectural gap without first resolving the relevant currently effective Authority Sources.

This failure occurred even though the Research Lab already had explicit Single Source of Truth, semantic-jurisdiction, upstream-consistency, implementation-neutrality, and Reconsideration principles.

Two representative failures exposed the problem.

First, an operational pilot proposed moving changing Research Case state into a separate current-state projection. Re-reading the Operational Record Specification showed that current lifecycle state, unresolved gaps, and next action were already canonical Research Case responsibilities. The proposed redesign therefore reflected an incorrect reinterpretation of existing authority rather than a genuine architecture gap.

Second, a comparative pilot identified the importance of source-defined metric semantics and initially treated this as a possible new Evidence-record requirement. Re-reading the Operational Record Specification showed that material source-defined metric meaning was already an approved Evidence Reference responsibility. The pilot had validated an existing design requirement rather than discovered a new requirement.

The underlying issue was therefore not primarily absence of principles. It was the absence of a sufficiently explicit research-process obligation requiring relevant authority to be re-resolved at the moment a material meta-level finding is advanced toward Research Lab-wide methodological, semantic, or architectural change.

At the same time, an authority review must not turn current documents into doctrine. The Scientific Philosophy requires Reality and better Evidence to remain capable of challenging existing models and current understanding. A legitimate challenge to current methodology or architecture must therefore remain able to trigger Reconsideration.

## 2. Decision

The Stock_vis Research Lab adopts an **authority-backed review obligation for material Research Lab change candidates** as part of Research Methodology v1.2.

### 2.1 Trigger the Review for Material Meta-Level Change Candidates

Before a material finding or proposal is advanced as a formal Research Lab change candidate, authority-backed review is required when the proposal would either:

- establish meaning, rules, responsibilities, or structure intended to apply beyond the current Research Case; or
- move, narrow, expand, replace, or materially reinterpret a responsibility or boundary already assigned by an existing authority, methodology, architecture, or intentional Non-Decision.

Local research judgments, reversible implementation experiments, analytical choices, and exploratory working labels do not require formal authority review merely because they may later prove reusable.

### 2.2 Review the Currently Effective Authority and Existing Architecture

The review must be proportional to consequence and should determine, where material:

- the applicable semantic or methodological jurisdiction and currently effective Authority Sources;
- whether existing authority already covers the finding;
- whether the proposal is consistent with upstream constraints and authority boundaries;
- whether the current architecture can accommodate the need without new normative structure; and
- whether an apparent conflict reflects an incorrect proposal or material Reality/Evidence that justifies possible Reconsideration of current authority.

A material meta-level finding must not be promoted merely because a researcher or agent does not recall existing coverage.

### 2.3 Preserve Reality-Driven Reconsideration

Authority-backed review is not a rule that current authority must always be retained.

When Reality or better Evidence materially challenges a current methodology, architecture, decision, or assumption, the challenge should be routed through the applicable Reconsideration process rather than silently rejected for inconsistency or silently implemented outside governance.

### 2.4 Separate Normative Obligation From Agent Implementation

Research Methodology owns the normative research-process obligation to perform the review when materially required.

Terminology Governance continues to govern semantic jurisdiction, Primary Authority, Authority Sources, upstream consistency, and concept governance within its scope.

Evaluation Methodology continues to govern evaluation and Reconsideration semantics within its scope.

Operational Record Specification continues to govern persistent record semantics and does not gain a new record category from this decision.

Future agent or software workflows may implement retrieval, classification, dependency resolution, routing, or automation, but those implementations do not become semantic authority merely by use.

## 3. Rationale

The adopted structure addresses the observed failure with the smallest normative change.

It preserves exploratory freedom because ordinary Claims, Evidence acquisition, Research Question refinement, analytical choices, and local experiments remain under normal Research and Evaluation processes.

It reduces semantic and architectural drift because material cross-case changes cannot progress merely from transient conversational context or agent memory.

It preserves evolvability because current authority remains open to Reality- and Evidence-backed Reconsideration.

It also aligns with the existing separation between epistemic work and consequential governance: routine authority checks can resolve or correct many apparent gaps without CEO involvement, while material methodology or architecture changes may proceed to consequential governance only after existing authority has been properly examined.

## 4. Alternatives Considered

### 4.1 No Additional Methodological Obligation

Under this alternative, existing Terminology Governance, Research Methodology, Evaluation Methodology, and Operational Record Specification principles would remain sufficient in theory, while researchers and agents would be expected to remember to apply them.

This was not preferred because operational pilots demonstrated that the existence of correct authority does not guarantee timely retrieval and application during active reasoning.

### 4.2 Agent-Workflow-Only Guardrail

Under this alternative, authority checks would exist only in prompts, orchestration, or future software.

This was not preferred because implementation behavior could then change independently of the normative Research Methodology, making an important research-integrity obligation dependent on a particular agent implementation.

### 4.3 Full Methodology-Level Execution Procedure

Under this alternative, Research Methodology would prescribe detailed retrieval sequences, classification labels, agent actions, and escalation mechanics.

This was not preferred because it would prematurely fix implementation details that remain intentionally unresolved and would make Research Methodology unnecessarily procedural and brittle.

### 4.4 Separate Authority-Checkpoint Governance System

Under this alternative, a new standalone authority, methodology, or record category would govern the checkpoint.

This was not preferred because the required semantic authorities already exist. The missing element is a lightweight process obligation connecting research-generated meta-findings to those authorities, not a new layer of semantic governance.

## 5. Expected Consequences

Expected benefits include:

- fewer duplicate concepts, record categories, and methodological rules created from already-covered operational frictions;
- earlier detection of proposals that silently displace existing semantic responsibilities;
- stronger consistency across sessions, researchers, and future sub-agents;
- reduced need for the Project Owner / CEO to manually audit whether a proposal conflicts with existing official documents;
- clearer distinction between validating an existing design, identifying a local implementation issue, and discovering a genuine change candidate; and
- preservation of Reality-driven methodological evolution through explicit Reconsideration.

Expected costs include:

- additional retrieval and review work for material meta-level proposals; and
- the need for future agent workflows to reliably resolve relevant current Authority Sources rather than rely only on memory or cached summaries.

These costs should remain proportional because ordinary case-level research does not automatically trigger authority review.

## 6. Non-Decisions

This decision does not establish:

- a new semantic authority or governance hierarchy;
- a new epistemic object type;
- a new Operational Record category;
- a fixed label such as `Authority Checkpoint` as a governed Research Lab-wide concept;
- an exhaustive taxonomy of meta-level findings;
- exact authority-retrieval algorithms;
- exact document-search or dependency-resolution procedures;
- fixed classification labels for authority-review outcomes;
- agent counts, voting, consensus, or reviewer rules;
- exact CEO escalation thresholds;
- automation or workflow-engine design; or
- any change to the existing principle that Reality and better Evidence may justify Reconsideration of current authority.

## 7. Required Follow-on Work

Subsequent operational work should:

- implement and test a lightweight retrieval-backed authority-review workflow for future research agents;
- test the obligation across additional research and meta-research cases;
- observe false-positive burden and missed-drift failures;
- refine implementation only when operational evidence justifies greater specificity; and
- reconsider the obligation if it creates material bureaucracy without proportional reduction in semantic or architectural drift.

## 8. Related Documents

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](../01_methodology/research_methodology.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [Stock_vis Research Lab Operational Record Specification](../01_methodology/operational_record_specification.md)
- [DR-0006: Separate Epistemic Authority from Consequential Governance](DR-0006-separate-epistemic-authority-consequential-governance.md)
- [DR-0007: Adopt the Stock_vis Research Lab Operational Record Specification v1](DR-0007-adopt-operational-record-specification-v1.md)