# DR-0005: Adopt the Stock_vis Research Lab Evaluation Methodology v1

**Record ID:** DR-0005  
**Status:** Approved  
**Decision Type:** Evaluation Methodology / Epistemic Architecture  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-24  
**Approval:** Approved by Project Owner on 2026-08-24  
**Effective Date:** 2026-08-24  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Document:** [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)

## 1. Context

The Scientific Philosophy establishes Reality as the final standard, Models as tools for understanding, better Evidence as capable of advancing or overturning current Understanding, and all Models as open to falsification.

The Knowledge and Understanding Framework subsequently defined Evidence, Research Claims, Atomic and Composite Research Knowledge, Understanding, Models, credibility, applicability, lineage, and seven epistemic architecture invariants while delegating concrete Evaluation Methodology to later work.

The Research Lab therefore needed an Evaluation Methodology capable of answering questions such as:

- How should Evidence quality be separated from the relevance of Evidence to a particular Claim?
- How should multiple Evidence Items be evaluated when they share common roots or conflict?
- How should Claim credibility differ from source credibility, probability estimates, and admission status?
- How should Composite Knowledge be evaluated without averaging component credibility?
- How should the approved Understanding Epistemic Profile be operationalized?
- How should Models, Model Uses, and Model Outputs be evaluated without treating benchmark performance as the same thing as credibility?
- How should evaluation remain proportional, revisable, and open to challenge rather than becoming a new authority above Reality?
- How should material dependencies and weaknesses be preserved across Evidence, Knowledge, Understanding, and Models without recording every intermediate reasoning step?

The resulting architecture was developed through comparison with scientific evidence assessment, model-risk management, validation practice, and repeated Stock_vis-specific adversarial tests.

## 2. Decision

The Stock_vis Research Lab adopts **Evaluation Methodology v1.0** as the general normative framework for epistemic evaluation.

The decision adopts the following commitments.

### 2.1 Define Evaluation as Reality-Grounded Critical Characterization

Evaluation exists to characterize how well a research object is warranted or fit for its declared scope and purpose, where it is weak, what remains uncertain or unassessed, and under what conditions it may fail.

Metrics and benchmarks remain instruments rather than substitutes for Reality.

### 2.2 Use a Layered Evaluation Architecture

Evaluation Methodology uses:

```text
Common Evaluation Principles
→ Common Evaluation Contract
→ Object-specific Evaluation Profiles
→ Purpose / Scope / Context
→ Consequence-proportional Challenge
→ Structured Assessment
```

Different epistemic objects must not be forced into one universal scalar score.

### 2.3 Distinguish Evidence Item, Evidence–Claim Relation, and Claim-Relative Evidence Body

Evidence quality, Claim-specific fit, and body-level support structure are distinct.

Evidence Item evaluation examines provenance, generation reliability, and information fidelity.

Evidence–Claim evaluation examines relevance/directness, context fit, direction, and where material, discriminative value.

Evidence Body evaluation examines dependency, conflict, coverage, and other body-level limitations relative to a particular Claim and Evaluation Purpose.

### 2.4 Adopt a Claim / Knowledge Core Credibility Profile

Claim and Atomic Research Knowledge evaluation uses four conceptual functions:

1. **Evidential Sufficiency**
2. **Inferential Soundness**
3. **Scope Calibration**
4. **Challenge Resilience**

The exact labels may later be refined without altering the conceptual functions.

Claim modality may route evaluation to conditional extensions without requiring one exhaustive taxonomy in v1.

Evaluation dimensions apply according to materiality. A dimension that is Not Material is not thereby favorable, and an Unassessed dimension is not thereby unfavorable.

### 2.5 Separate Probability, Credibility, and Admission

A probability contained in Claim content is not equivalent to confidence in that Claim.

Source credibility is not Evidence credibility.

Claim or Knowledge credibility is not identical to Knowledge admission.

Admission remains a lifecycle decision informed by Evaluation Purpose and criteria rather than an automatic numerical threshold by definition.

Every Research Knowledge admission requires an admission-purpose structured evaluation, with rigor proportional to epistemic consequence.

### 2.6 Require Composition Warrant for Composite Knowledge

Composite Knowledge requires evaluation of newly introduced epistemic structure, not merely reuse of component credibility.

Composition Evaluation includes material checks of operation validity, interface compatibility, dependency integrity, scope/condition propagation, and emergent interaction or nonlinearity.

No relation is assumed to be transitive by default.

Composite credibility must not be automatically calculated as an average, minimum, product, or other arithmetic aggregation of component credibility.

### 2.7 Operationalize the Approved Understanding Epistemic Profile

Evaluation Methodology operationalizes the Knowledge and Understanding Framework's four approved dimensions:

1. Support Sufficiency
2. Structural Integrity
3. Scope Adequacy
4. Robustness

It does not redefine them or replace them with one intrinsic scalar.

### 2.8 Evaluate Research Process Separately From Result Quality

Research process may be evaluated for whether it supplied adequate epistemic warrant, including design alignment, exploration-confirmation separation, evidence-selection bias, alternative analysis, reproducibility, and material methodological deviations.

Process quality and result quality remain distinguishable.

### 2.9 Distinguish Model, Model Use, and Model Run / Output

Model Evaluation treats Model, Context of Use, and particular Run/Output as distinct evaluation targets.

Model validity is always relative to a stated Purpose, Scope, and Context of Use rather than an absolute context-free property.

The Model common core includes conceptual soundness, implementation fidelity/verification, empirical validity, robustness/uncertainty, and applicability/use fitness, with modality-specific extensions when needed.

Performance metrics are not equivalent to Model credibility or Model research contribution.

A Model Output does not automatically inherit the credibility of the Model that produced it.

### 2.10 Adopt Material Warrant Network as a Cross-Layer Conceptual Backbone

Formal epistemic outputs should remain sufficiently connected to material upstream warrant and downstream dependencies, including assumptions, transformations, weaknesses, and versions, so that consequential warrant and impact paths can be reconstructed when needed.

The requirement is **Material Warrant Traceability**, not full preservation of every intermediate reasoning step.

The exact storage and graph implementation remain undecided.

### 2.11 Adopt Cross-Layer Evaluation Principles

The methodology adopts:

- **Local Evaluation, Global Traceability**
- **Referential Propagation, Not Scalar Propagation**
- **Change Propagates Review Obligations, Not Conclusions**
- **Evaluation Is Versioned and Purpose-Bound**

These principles operationalize the Knowledge and Understanding Framework's architecture invariants.

### 2.12 Use Proportional Rigor and Effective Challenge

Evaluation rigor is driven by epistemic consequence, downstream dependency, uncertainty, novelty, complexity, evidence conflict, reversibility, and consequences of being wrong.

Not every evaluation requires the same validation burden or a separate independent evaluator.

Urgency may justify provisional or restricted use and closer monitoring, but it must not silently redefine epistemic quality.

### 2.13 Distinguish Re-evaluation and Reconsideration Triggers

Evaluation Methodology provides the canonical v1 methodological definitions of Re-evaluation Trigger and Reconsideration Trigger.

A Re-evaluation Trigger reopens evaluation of a specific epistemic object or prior assessment.

A Reconsideration Trigger reopens an existing methodology, architecture, assumption, or consequential decision to determine whether it should be retained, modified, restricted, or replaced.

For Material Warrant Network, maintenance burden, low practical use, equivalent simpler alternatives, or repeated failure to detect important dependency or revision impact are valid observable reconsideration signals.

A trigger creates review obligation rather than predetermined change.

### 2.14 Require Meta-Evaluation

Evaluation Methodology itself remains falsifiable and revisable.

The Research Lab may assess evaluator inconsistency, false confidence, recurring missed failures, benchmark drift, disagreement between prior evaluation and later observations, evidence, or outcomes concerning Reality, burden, and trigger effectiveness in order to improve the evaluation system.

### 2.15 Coordinate the Initial v1 Adoption

Evaluation Methodology v1.0 and Research Methodology v1.0 form one coordinated initial adoption set because each defines one side of the research–evaluation handoff.

They become effective together for their initial v1 adoption. After that initial adoption, either methodology may evolve through its own revision lifecycle when dependency review confirms continued consistency with the other and with upstream authorities.

## 3. Alternatives Considered

### 3.1 Universal Score and PASS/FAIL Gate

The Research Lab could evaluate all objects with one score or one pass/fail gate.

This was not selected because it would collapse different epistemic questions, hide uncertainty, encourage metric optimization, and create automatic promotion pressure.

### 3.2 Independent Checklist for Every Object Type

Evidence, Claims, Knowledge, Understanding, Models, and other objects could each have independent evaluation systems with no shared contract.

This was not selected because it would duplicate concepts, create inconsistent evaluation cultures, and make cross-layer traceability more difficult.

### 3.3 Let Upstream Credibility Scores Propagate Downstream

Evidence scores could be averaged into Claim scores, component Knowledge scores could be aggregated into Composite scores, and Knowledge scores could be averaged into Understanding.

This was not selected because dependency, new inference, critical bridges, scope transformation, and emergent interaction make automatic inheritance epistemically invalid.

### 3.4 Treat Model Validation as Absolute

A model could receive one validated/not-validated state independent of Purpose or Context of Use.

This was not selected because validity and risk depend materially on target, horizon, regime, data distribution, purpose, and use.

### 3.5 Preserve Full Reasoning Trace

Every intermediate thought, agent message, discarded path, and reasoning step could be stored for maximum transparency.

This was not selected because the burden would be disproportionate and could turn epistemic traceability into reasoning bureaucracy. V1 requires reconstruction of material warrant rather than total thought history.

### 3.6 Omit Warrant Network and Store Only Final Results

This was not selected because future revision, dependency analysis, re-evaluation, and reuse require more than a final label or score. However, the Material Warrant Network remains subject to Reconsideration Triggers if operational burden materially exceeds value.

## 4. Rationale

The adopted Evaluation Methodology balances rigor, traceability, and evolvability.

It preserves enough structure to distinguish Evidence quality, Claim warrant, Composition warrant, Understanding quality, research-process rigor, and Model validity without constructing a single universal scoring ontology.

The Methodology deliberately emphasizes structured assessment over certification. This prevents evaluation metrics from becoming substitutes for Reality and preserves the possibility that later evidence may strengthen, restrict, revise, or overturn current assessments.

The Material Warrant Network provides a common traceability backbone while the Reconsideration Trigger principle ensures that this architecture itself remains open to simplification or replacement if empirical operation shows that the burden exceeds its value.

## 5. Consequences

### 5.1 Binding Implications

Adoption of Evaluation Methodology v1.0 establishes that:

- evaluation must be purpose-, scope-, and context-aware;
- different epistemic objects require distinct profiles under common principles;
- evaluation dimensions apply according to materiality, and unassessed or non-material dimensions must not be silently converted into favorable or unfavorable scores;
- uncertainty and unassessed areas must not be silently converted into favorable scores;
- upstream evaluation does not automatically determine downstream credibility;
- Evidence Bodies are Claim-relative and dependency-aware;
- Claim and Knowledge credibility preserve inferential and scope information beyond source quality;
- every Research Knowledge admission requires an applicable admission-purpose evaluation;
- Composite Knowledge requires separate composition warrant;
- Understanding uses the four approved epistemic-profile dimensions;
- Model validity is context-bound and Model Outputs require run/use evaluation;
- material upstream warrant and downstream dependency should be reconstructable across layers;
- Evaluation Records are versioned and purpose-bound;
- upstream change creates review obligations rather than automatic downstream conclusions; and
- Evaluation Methodology remains subject to meta-evaluation and reconsideration.

### 5.2 Expected Benefits

The methodology is expected to provide:

- better resistance to epistemic inflation from AI or model outputs;
- more informative uncertainty than scalar confidence alone;
- safer reuse of Research Knowledge;
- stronger dependency and circular-support detection;
- clearer revision impact analysis;
- more credible Model validation and reuse;
- consistent cross-object evaluation without forcing universal scores; and
- an auditable basis for future research agents and machine-readable systems.

### 5.3 Required Follow-on Work

Later work may include:

- operational rubrics and examples;
- empirical calibration of rigor tiers and thresholds;
- model-specific evaluation standards;
- evaluation-record implementation;
- Material Warrant Network implementation;
- agent challenge and escalation workflows;
- meta-evaluation metrics; and
- downstream Decision-Support Evaluation.

## 6. Non-Decisions

This decision does not adopt:

- numerical evidence or credibility weights;
- universal scalar quality scores;
- exact Knowledge admission thresholds;
- exact High / Medium / Low definitions;
- fixed rigor tiers;
- exhaustive Claim, Model, or Composition taxonomies;
- exact evaluation-outcome vocabulary;
- mandatory independent evaluators for all work;
- agent voting or consensus rules;
- exact Re-evaluation or Reconsideration thresholds;
- exact meta-evaluation metrics;
- an evaluation-reuse compatibility algorithm;
- a graph, database, ontology, or physical Material Warrant Network schema;
- model-specific benchmark metrics; or
- investment Decision-Support evaluation criteria.

## 7. Related Documents

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](../01_methodology/research_methodology.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [DR-0003: Adopt the Stock_vis Research Lab Knowledge and Understanding Framework v1](DR-0003-adopt-knowledge-understanding-framework-v1.md)
- [DR-0004: Adopt the Stock_vis Research Lab Research Methodology v1](DR-0004-adopt-research-methodology-v1.md)
