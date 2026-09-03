# Stock_vis Research Lab Sub-Agent Research Operating Model — Candidate

**Status:** Experimental / Candidate  
**Version:** 0.1  
**Last Updated:** 2026-09-03  
**Owner:** Stock_vis Research Lab  
**Normative Status:** Not approved as Research Methodology or Research Lab-wide operating architecture  
**Repository Checkpoint:** Approved by Project Owner on 2026-09-03

## 1. Purpose

This document preserves the current experimental operating model for future sub-agent research within the Stock_vis Research Lab.

It exists to make material operational learning reconstructable before implementation moves from conversational pilots toward an actual local / hybrid multi-agent runtime.

This document is **not** a new normative methodology, semantic authority, epistemic object type, Operational Record category, or Decision Record. It does not modify or supersede the approved Research Methodology, Evaluation Methodology, Operational Record Specification, Terminology Governance, Knowledge and Understanding Framework, or existing Decision Records.

The currently approved authorities remain controlling. Where this candidate conflicts with a currently effective Authority Source, the Authority Source governs unless and until an approved Reconsideration changes it.

## 2. Authority Boundary and Candidate Status

The approved Research Methodology defines the general lifecycle and intentionally leaves exact agent orchestration, reviewer counts, voting rules, automation, and escalation mechanics as implementation-level or operational Non-Decisions.

The approved Evaluation Methodology defines evaluation meaning and effective challenge, including Research Process Evaluation and meta-evaluation, without prescribing a fixed agent topology.

The Operational Record Specification defines persistent record semantics and does not require every intermediate agent thought, critique, or discarded idea to become a canonical record.

DR-0008 requires material Research Lab-wide change candidates to be reviewed against currently effective Authority Sources before they are promoted into normative structure.

Accordingly, this document records an **operational implementation candidate under existing approved authority**. Its elements may be revised, narrowed, merged, retired, or replaced as further evidence accumulates.

## 3. Operational Pilot Evidence to Date

The candidate is informed by a sequence of operational research pilots rather than by a single design exercise.

| Pilot | Material operational learning |
| --- | --- |
| Salesforce | A direct-evidence ceiling should not automatically end research when alternative approaches may still advance the underlying Problem. Discussion / synthesis can legitimately reopen research. |
| HP | Discussion / synthesis is not only an expansion mechanism; it can also justify closure when further work has low expected epistemic value. |
| AMD | Larger delegated batches can work when research state and evaluation remain sufficiently controlled; batching itself is not a new epistemic role. |
| Meta | A calibrated `Unknown` can still represent premature epistemic sufficiency when material counterfactual, mediator, or alternative-identification work remains. Independent criticism materially improved the research path. |
| Micron | Question framing materially changed downstream evidence search and reasoning. Attribution, mechanism, resilience, and synthesis questions can serve different epistemic functions. A false dichotomy between apparently competing explanations was also exposed. |
| Boeing | Question Critic and selective reuse of prior critic learning transferred to a different business topology. `Operating recovery vs customer advances` was better understood as interacting parts of one cash-cycle mechanism. |
| Amazon | A learning-enabled branch opened materially different research space from a memory-blind branch, especially around demand shock, capital reversibility, utilization, and cash economics. The result is operational evidence for learning reuse, not causal proof of superiority. |

These pilots do not establish universal workflow rules. They provide evidence for the current candidate and for the validation agenda below.

## 4. Current Candidate Core Functions

The current minimal functional decomposition is:

1. **Case Lead**
2. **Researcher**
3. **Critic**
4. **Evaluator**

These are **core functions**, not a requirement that exactly four physical agents or four model instances always run.

### 4.1 Case Lead

The Case Lead maintains operational continuity across the Research Case. Candidate responsibilities include:

- preserving Trigger → Problem → Question continuity;
- maintaining current scope, unresolved gaps, dependencies, and next actions;
- decomposing and routing research work;
- coordinating parallel Researcher instances;
- deciding when additional Critic, Evaluator, or Specialist work is operationally warranted;
- integrating discussion / synthesis without becoming the default epistemic truth authority; and
- routing material structural findings toward applicable Authority Review.

### 4.2 Researcher

The Researcher executes Investigation. Candidate responsibilities include:

- Evidence acquisition and source examination;
- provenance-preserving extraction;
- comparison, quantitative analysis, modeling, simulation, or document synthesis when appropriate;
- alternative research approaches when current methods do not resolve the Question;
- generation and revision of candidate Claims; and
- explicit preservation of material uncertainty and missing Evidence.

A Research Case may use multiple parallel Researcher instances without introducing new core roles.

### 4.3 Critic

The Critic provides independent or sufficiently separated challenge to framing, inference, and research sufficiency. Candidate concerns include:

- hidden assumptions;
- premature Question commitment;
- competing explanations;
- false dichotomies or causal dependence among explanations;
- counterfactuals and mediators where material;
- missing alternative identification paths;
- premature `Unknown` or premature closure;
- excessive research without proportional epistemic value; and
- new attack surfaces not already encoded in accumulated institutional memory.

The Critic is intended to find material blind spots, not to maximize the number of objections.

### 4.4 Evaluator

The Evaluator applies the approved Evaluation Methodology to the latest relevant object state and declared Evaluation Purpose. Candidate implementation responsibilities include:

- Evidence–Claim alignment;
- evidential sufficiency;
- inferential soundness;
- scope calibration;
- challenge resilience;
- explicit uncertainty and unassessed areas; and
- consequence-proportional rigor.

Critic and Evaluator are functionally distinct even when one runtime agent may perform both functions in low-consequence work.

## 5. Candidate Fast Research Loop

The current experimental fast loop is:

```text
Reality / Trigger
      ↓
Research Problem
      ↓
Fresh Question Formation
      ↓
Relevant Learning Retrieval
      ↓
Question / Design Critic
      ↓
Research / Investigation
      ↕
Inference / Alternative Critic
      ↓
Evaluation
      ↓
Discussion / Synthesis
      ↓
Closure Critic
      ↓
Lifecycle / Admission Action
```

This is an orchestration candidate, not a replacement for the approved Research Methodology lifecycle.

### 5.1 Fresh Reasoning Before Institutional Memory

The current candidate prefers **fresh reasoning first, institutional memory second** for material Question formation and novel framing.

The purpose is to reduce institutional anchoring. Prior Learning Artifacts, Critic Checkpoints, and Approach memories should normally be retrieved after an initial fresh framing has been generated, then used to challenge, revise, broaden, narrow, or reject that framing.

Important or novel work may additionally use a memory-blind or differently contextualized challenger where proportional.

### 5.2 Critic Gates Are Proportional

The three shown Critic locations are functional opportunities for challenge, not mandatory heavyweight reviews in every Case.

Low-consequence work may consolidate functions. High-consequence, high-reuse, novel, or materially disputed work may justify stronger separation, additional independent challenge, or Specialist review.

## 6. Candidate Slow Learning and Evolution Loop

The fast Research Loop is separated from a slower learning and institutional-evolution loop.

```text
Case Outcome / Material Episode
      ↓
Research Process Evaluation
      ↓
Learning Candidate
      ↓
Cross-Case Validation
      ↓
Validated Operational Learning
      │
      ├── Agent Improvement Path
      │      ↓
      │   Memory / Retrieval
      │      ↓
      │   Prompt / Harness
      │      ↓
      │   Training Candidate
      │      ↓
      │   Protected Held-Out Evaluation
      │      ↓
      │   Controlled Model Adaptation
      │
      └── Structural Change Path
             ↓
          Authority Review
             ↓
          Existing Design / Implementation / Capability issue?
             ↓
          Genuine Reconsideration Candidate when warranted
             ↓
          Consequential Governance when materially required
```

The two paths must remain distinct.

A useful training example does not automatically justify a Research Lab rule. A governance rule does not automatically belong in model weights.

### 6.1 Learning Promotion Principle

The current working invariant is:

```text
Observed behavior
≠ validated lesson
≠ training example
≠ deployed behavior
≠ Research Lab rule
```

Promotion between these states requires additional warrant appropriate to the consequence.

### 6.2 Learning Artifact Candidate Semantics

Where useful for experimentation, a Learning Artifact may summarize:

- learning target;
- source episode;
- initial behavior or state;
- material Evaluation / Critique;
- repair or alternative;
- outcome delta or justified retention;
- reusable lesson and scope; and
- current promotion state.

Learning Artifacts are currently non-normative learning-plane views. This document does **not** establish a new canonical Operational Record category.

## 7. Evolving Critic and Question Learning

Current operational learning suggests that Question formation and criticism should themselves be evaluated and improved across Cases.

Candidate Question evaluation concerns include:

- Problem fidelity;
- why resolving the Question matters for the unresolved Problem;
- hidden preferred-answer leakage;
- discriminative value;
- researchability;
- downstream search-space effects; and
- whether alternative framing would materially improve Understanding.

Current experimental Critic Checkpoint examples include:

- mediator decomposition;
- counterfactual challenge;
- premature epistemic sufficiency;
- alternative identification;
- legitimate Unknown / closure;
- causal independence / false-dichotomy checks.

These are **evolving operational memories**, not an approved universal checklist. They may be narrowed, merged, retired, or replaced as additional Cases expose their usefulness and failure boundaries.

## 8. Agent Scaling and Expansion Candidate

The candidate distinguishes three different concepts:

```text
Core Function Topology
≠ Runtime Agent Instance Count
≠ Model Topology
```

A Case may run many parallel Researcher or Critic instances while retaining the same core functions.

### 8.1 Scale-Out

Replication of an existing function is the lowest-burden form of expansion. It is appropriate when work can be partitioned and parallel execution provides net benefit after coordination cost.

### 8.2 Specialist-on-Demand

Domain or methodological specialists may be invoked temporarily when a Case requires material expertise or tools not efficiently provided by the general Researcher / Critic pool. A temporary Specialist does not automatically become a permanent core role.

### 8.3 Experimental and Permanent Role Expansion

A new permanent core role should be considered only when a recurring, material, separable function:

- appears across heterogeneous Cases;
- materially affects research quality or safety;
- cannot be adequately handled through existing roles, better prompts, tools, memory, routing, or on-demand specialization;
- gains material benefit from independent execution;
- improves results in controlled experimental-role pilots; and
- produces durable net system benefit after compute, latency, handoff, coordination, and governance costs are considered.

Permanent role expansion should remain reversible. Merge or retirement should be possible when model capability, usage frequency, or measured system value changes.

A Research Lab-wide permanent core-role change would require appropriate Authority Review and, when consequential, Project Owner / CEO governance. Runtime scale-out and reversible specialist experiments do not by themselves require such governance.

## 9. Local-First / Frontier-on-Exception Candidate Principle

The current runtime direction is **Local-first / Frontier-on-exception**.

The objective is not to minimize Frontier API use as an isolated numerical target. The objective is to use Frontier capability only where it creates proportional epistemic or operational value that the local system cannot reliably provide.

A candidate escalation ladder is:

```text
Local execution
      ↓
Better context / retry
      ↓
Stronger local model or independent local attempt
      ↓
Local Specialist where appropriate
      ↓
Frontier consultation when still materially unresolved
```

Potential Frontier escalation signals include:

- repeated local capability failure;
- material disagreement among local agents;
- high-consequence or high-reuse epistemic work requiring stronger independent challenge;
- novel research topology outside validated local capability;
- repeated Critic failure;
- difficult causal, inferential, or integration problems that remain unresolved after justified local retries.

A Frontier output is **not** higher epistemic authority by origin. It remains subject to the same Research and Evaluation authorities as other model outputs.

Future Frontier interactions may become valuable failure → repair learning data for local model improvement, but only after appropriate evaluation and curation.

## 10. Recording and Telemetry Boundary

The approved Operational Record Specification remains authoritative for canonical research records.

Future runtime implementation may require a richer non-normative telemetry / learning plane containing material information such as:

- candidate Questions and selection history;
- model / agent version;
- learning-memory retrieval events;
- Critic interventions;
- repair trajectories;
- handoffs;
- tool paths;
- process-evaluation outcomes; and
- training eligibility decisions.

This telemetry must not silently become Research Knowledge, semantic authority, or a competing canonical Research Case / Evaluation / Evidence record system.

The implementation should preserve reconstructability without assuming that every token, hidden reasoning trace, or ephemeral intermediate output must be retained.

## 11. Current Non-Decisions

Candidate v0.1 does not decide:

- that exactly four physical agents must always be used;
- exact reviewer counts, voting rules, or consensus algorithms;
- exact Critic invocation frequency;
- exact lifecycle labels beyond approved Methodology;
- a permanent Question Agent, Discussion Agent, Learning Agent, or other additional core role;
- a canonical Learning Artifact record category;
- a complete Critic Checkpoint taxonomy;
- exact telemetry schema or retention policy;
- exact local model families or parameter sizes;
- exact Frontier providers, models, quotas, or API-use targets;
- exact hardware topology beyond ongoing implementation research;
- fine-tuning methods or training schedules;
- exact thresholds for permanent role expansion; or
- adoption of this candidate as the Research Lab-wide normative operating architecture.

## 12. Validation Agenda

Before normative adoption is considered, operational work should test at least the following questions proportionally:

1. Does independent multi-agent runtime reproduce the Critic benefit observed in conversational pilots?
2. What is the minimum functional separation that preserves research quality without creating agent bureaucracy?
3. When does Critic / Evaluator independence materially improve outcomes, and when is function consolidation sufficient?
4. Does fresh-first / memory-second Question formation reduce institutional anchoring without sacrificing useful transfer?
5. Which Learning Artifacts materially improve fresh Case performance versus memory-blind baselines?
6. What negative-transfer cases show when accumulated learning should not be retrieved or applied?
7. What telemetry is necessary for later evaluation and fine-tuning without creating a data swamp?
8. How should protected held-out Cases be isolated from retrieval and future training?
9. What local capability thresholds are sufficient for Case Lead, Researcher, Critic, and Evaluator functions?
10. Which conditions justify Frontier escalation, and what are escalation precision, recall, and value-add?
11. When does runtime scale-out cease to be sufficient and a new experimental role become justified?
12. Does the Agent Expansion Gate prevent both premature proliferation and harmful under-specialization?
13. How should architecture changes be evaluated after deployment, including rollback or retirement when expected benefit does not materialize?

## 13. Related Approved Authorities

- [Stock_vis Research Lab Terminology Governance](terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](research_methodology.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [Stock_vis Research Lab Operational Record Specification](operational_record_specification.md)
- [DR-0006: Separate Epistemic Authority from Consequential Governance](../04_decision_records/DR-0006-separate-epistemic-authority-consequential-governance.md)
- [DR-0008: Require Authority-Backed Review for Material Research Lab Change Candidates](../04_decision_records/DR-0008-require-authority-backed-review-for-material-research-lab-change-candidates.md)
