# DR-0003: Adopt the Stock_vis Research Lab Knowledge and Understanding Framework v1

**Record ID:** DR-0003  
**Status:** Approved  
**Decision Type:** Research Methodology / Epistemic Architecture  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-20  
**Approval:** Approved by Project Owner on 2026-08-20  
**Effective Date:** 2026-08-20  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Document:** [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)

## 1. Context

The Stock_vis Research Lab Scientific Philosophy defines better understanding of Reality as the Research Lab's direct purpose and treats Models and Evidence as means by which understanding can advance. Terminology Governance v1.0 subsequently established concept-first governance, federated semantic authority, historical reproducibility, and implementation-neutral ontology readiness while explicitly leaving the substantive definition of Research Knowledge, the Knowledge–Understanding relationship, and evidence or confidence metrics for later decisions.

The next methodological problem was therefore not primarily terminological. The Research Lab needed a coherent epistemic architecture that could answer questions such as:

- What distinguishes Evidence from Research Knowledge?
- Does a Hypothesis become Knowledge, or should semantic content and research role remain distinct?
- What is the smallest legitimate unit of Research Knowledge?
- When does composition of existing Knowledge produce new Knowledge rather than a mere collection?
- How is Understanding different from simply having more Knowledge?
- How should the credibility of an Understanding be represented without destroying the structure of its uncertainty?
- Can competing Understandings coexist?
- How should revision, split, merge, regime change, and historical reproducibility be handled?
- How should Model Outputs and AI-generated assertions enter the epistemic system without being silently promoted into Knowledge?
- How can future ontology and sub-agent systems remain evolvable without allowing implementation structure to redefine research meaning?

The discussion proceeded through boundary analysis, comparison with academic and industry approaches, integration of Knowledge- and Understanding-level credibility, cross-boundary tests among Evidence, Hypothesis, Knowledge, Understanding, Model, and Decision, and adversarial evolvability tests covering revision, split/merge, competing Understandings, regime shifts, agent disagreement, ontology expansion, and circular epistemic support.

## 2. Decision

The Stock_vis Research Lab adopts **Knowledge and Understanding Framework v1.0** as the normative Methodology-level framework for Research Knowledge, the operational Knowledge–Understanding relationship, and associated epistemic architecture invariants.

The decision adopts the following commitments.

### 2.1 Distinguish Workflow from Epistemic Object Architecture

The Research Protocol may proceed through stages such as Hypothesis, Research, Evaluation, and Knowledge, but workflow order must not be interpreted as literal transformation of one persistent object into another.

Semantic content, research role, evaluation activities, and admitted epistemic outputs must remain distinguishable.

### 2.2 Use Research Claim as the Methodological Semantic Hinge

A Research Claim is treated conceptually as an assertion about Reality that can be supported, challenged, qualified, revised, restricted, or rejected.

A Research Claim may take the role of a Hypothesis during research and may later be represented in admitted Research Knowledge after evaluation. The framework does not require Research Claim to become a specific first-class ontology or database object.

### 2.3 Evidence Does Not Automatically Constitute Knowledge

Evidence bears on Research Claims. Evidence may support, challenge, qualify, or leave a Claim unresolved, but its presence, quantity, recency, or model origin does not automatically establish Research Knowledge.

### 2.4 Define Atomic Knowledge by Epistemic Contestability

Atomic Research Knowledge is the smallest admitted epistemic unit that can be meaningfully evaluated, challenged, and revised as an independent epistemic boundary.

Atomicity is not defined by binary graph arity. Binary relationships may be common and useful, but conditional, interaction-dependent, or multi-relational claims must not be forced into binary decomposition when doing so changes their meaning.

### 2.5 Require Separate Warrant for Composite Knowledge

Composite Research Knowledge is a bounded epistemic result produced through composition, inference, or integration and separately admitted as Knowledge.

A collection of admitted Atomic Knowledge does not automatically become Composite Knowledge, and credibility does not automatically transfer from inputs to a newly composed result.

### 2.6 Define Understanding by Epistemic Function, Not Size

Understanding is not merely larger Knowledge.

Knowledge preserves bounded epistemic results for evaluation, revision, and reuse. Understanding organizes warranted Knowledge together with relevant relationships, conditions, boundaries, dependencies, alternatives, and uncertainty so that bounded warranted reasoning about Reality becomes possible.

An Understanding may reference explicitly typed non-Knowledge elements such as unresolved Hypotheses, competing explanations, gaps, Models, or scenarios without promoting them into Knowledge.

### 2.7 Permit Competing Understandings

Multiple competing, partially compatible, scope-dependent, condition-dependent, or temporally differentiated Understandings may coexist when current evidence does not justify a single consolidated structure.

The Research Lab must not manufacture premature consensus merely to maintain one preferred explanation.

### 2.8 Adopt an Understanding Epistemic Profile

Understanding credibility is represented conceptually as an epistemic profile rather than as one intrinsic scalar or an average of component Knowledge credibility.

The profile has four conceptual dimensions:

1. **Support Sufficiency** — whether the Knowledge and inferential warrants sufficiently support the claimed structure;
2. **Structural Integrity** — whether the organization of Knowledge and relationships is logically and semantically sound;
3. **Scope Adequacy** — whether the Understanding adequately represents what it claims within its declared scope; and
4. **Robustness** — whether the core structure remains warranted under plausible changes in assumptions, evidence, conditions, regimes, or competing explanations.

Material weaknesses, alternatives, dependencies, unassessed areas, boundary conditions, and temporal or contextual limitations may be preserved as explicit annotations.

### 2.9 Separate Credibility, Applicability, and Decision Relevance

Credibility concerns epistemic warrant. Applicability concerns whether an epistemic structure applies to a particular current scope, condition, regime, or time. Decision relevance or confidence arises downstream when Understanding is combined with Decision Context and Judgment.

These dimensions must not be silently conflated.

### 2.10 Keep Models Orthogonal to Epistemic Admission

Models are tools and representations that may generate, analyze, test, express, support, or challenge Evidence, Claims, Knowledge, and Understanding.

A Model is not automatically Knowledge or Understanding, and a Model Output is not automatically Research Knowledge.

### 2.11 Preserve Epistemic Lineage

Material revision must preserve enough lineage to interpret earlier Knowledge, Understanding, Models, evaluations, and Decisions against the epistemic states on which they materially depended.

Split, merge, restriction, supersession, replacement, and related lifecycle changes must not silently overwrite material history.

### 2.12 Adopt Seven Architecture Invariants

The framework establishes seven constraints for future Methodology, Evaluation, ontology, automation, and software work:

1. **No Silent Epistemic Promotion**
2. **No Automatic Credibility Inheritance**
3. **Content–Role–Status Separation**
4. **Process–Object Separation**
5. **Intrinsic–Decision Context Separation**
6. **Revision Must Preserve Lineage**
7. **No Circular Epistemic Support**

These invariants protect epistemic traceability and prevent future implementation convenience from silently changing the meaning of Research Knowledge or Understanding.

## 3. Alternatives Considered

### 3.1 Treat Hypothesis as an Object That Becomes Knowledge

The Research Lab could model the workflow as direct object transformation: Hypothesis → Knowledge.

This was not selected because it collapses semantic content, research role, and admission status and makes historical provenance more difficult to reproduce when a Claim is later revised, restricted, or rejected.

### 3.2 Treat Every Relationship Edge as Atomic Knowledge

Atomic Knowledge could be defined as exactly one binary relationship between two objects.

This was not selected because many legitimate claims are conditional, interaction-dependent, multi-relational, or regime-dependent. Forced binary decomposition may alter the epistemic meaning of the claim. Atomicity is therefore based on independent epistemic contestability rather than graph arity.

### 3.3 Let Existing Knowledge Automatically Produce Composite Knowledge

A composition of admitted Knowledge could be treated as admitted whenever its inputs are admitted.

This was not selected because composition introduces new inferential assumptions, dependencies, scope changes, and possible failure points. Automatic promotion would permit epistemic laundering.

### 3.4 Represent Understanding Credibility with One Score

Understanding credibility could be stored as one probability, numeric score, or categorical rating.

This was not selected as the intrinsic conceptual representation because an Understanding may be strong in support and structure but weak in robustness or scope adequacy. A single scalar would conceal where the structure is strong, weak, unknown, or context-sensitive.

Later Evaluation or Decision systems may create summaries for specific operational purposes, but those summaries must not replace the underlying epistemic profile by definition.

### 3.5 Require One Canonical Understanding per Problem

The Research Lab could require one currently preferred Understanding and treat alternatives as rejected or secondary.

This was not selected because reality may support multiple plausible, partially compatible, or condition-dependent explanations. Premature consolidation would create pressure to protect a preferred structure rather than preserve material uncertainty.

### 3.6 Treat Historical Non-Applicability as Loss of Credibility

An Understanding that no longer applies under a new market regime could be downgraded as epistemically weak.

This was not selected because historical credibility and current applicability are distinct. A well-supported Understanding may remain valid within its original scope even when external conditions change.

### 3.7 Ontology-First Formalization

The Research Lab could immediately formalize Research Claims, Knowledge, and Understanding in a particular graph or ontology technology.

This was not selected because representation choices should implement approved epistemic semantics, not determine them. The adopted architecture remains ontology-ready but implementation-neutral.

## 4. Rationale

The adopted framework resolves a tension between epistemic rigor and evolvability.

A minimal linear pipeline would be simple to implement but would hide the difference between evidence, claims, roles, admission, composition, and understanding. A fully formalized ontology-first design could preserve more structure but would risk freezing immature semantics and making sub-agent workflows unnecessarily complex.

The adopted model instead protects a small number of consequential boundaries:

```text
Evidence
≠ Research Knowledge

Research Claim content
≠ Hypothesis role
≠ Knowledge admission state

Atomic Knowledge collection
≠ automatically Composite Knowledge

Knowledge
≠ Understanding

Model / Model Output
≠ Knowledge by origin

Understanding epistemic quality
≠ Decision relevance

Historical credibility
≠ current applicability
```

The architecture is intentionally asymmetric. Knowledge admission establishes a reusable bounded epistemic result, while Understanding is evaluated for the quality of the structure that organizes Knowledge for reasoning. This prevents the credibility of component Knowledge from being mistaken for the credibility of the larger synthesis.

The framework also treats revision and disagreement as normal properties of scientific work. Competing Understandings can coexist, admission can later be revised, and historical state is preserved rather than overwritten. This supports the Scientific Philosophy's requirement that better evidence remain capable of strengthening, restricting, restructuring, replacing, or overturning current understanding.

Finally, the seven architecture invariants create constraints that future agent systems and machine-readable implementations can follow without requiring v1 to prescribe their exact technologies or algorithms.

## 5. Consequences

### 5.1 Binding Implications

Adoption of Knowledge and Understanding Framework v1.0 establishes that:

- future Research Methodology and Evaluation Methodology must distinguish Evidence, Research Claims, research roles, and Knowledge admission;
- Atomic Research Knowledge must be defined by independent epistemic contestability rather than a mandatory binary graph representation;
- new Composite Knowledge requires warrant for the composition itself and may not inherit epistemic status automatically from its components;
- Understanding must not be reduced to the quantity or size of Knowledge;
- non-Knowledge elements may contribute to reasoning only when their epistemic typing remains explicit;
- competing Understandings may be maintained when epistemically justified;
- Understanding evaluation must preserve the conceptual distinctions among Support Sufficiency, Structural Integrity, Scope Adequacy, and Robustness;
- future operational summaries must not silently redefine Understanding credibility as a single intrinsic scalar;
- credibility, applicability, and decision-specific relevance must remain distinguishable;
- Model and AI outputs require appropriate evaluation before they can support admitted Knowledge;
- material revision must preserve lineage; and
- circular or duplicated derivation must not be counted as independent epistemic support.

### 5.2 Expected Benefits

The framework is expected to provide:

- clearer boundaries for Research Knowledge admission;
- stronger provenance and historical reproducibility;
- reduced epistemic inflation from automated inference or AI-generated content;
- a stable conceptual basis for later Evaluation Methodology;
- an ontology-ready structure without premature formalization;
- better handling of uncertainty, competing explanations, and changing market regimes;
- clearer separation between research understanding and downstream investment decisions; and
- safer delegation to future sub-agent research systems.

### 5.3 Required Follow-on Work

The framework creates dependencies for later work, including:

- Research Methodology for Research Claim, Hypothesis, research, and admission workflows;
- Evaluation Methodology for evidence assessment, Knowledge credibility, admission criteria, Understanding Epistemic Profile assessment, disagreement handling, and validation;
- Model Documents for model-specific epistemic interfaces and limitations;
- future terminology/ontology work for machine-readable representation; and
- future agent architecture for provenance-aware research execution and escalation.

## 6. Non-Decisions

This decision does not adopt:

- evidence weights;
- Knowledge admission thresholds;
- numerical credibility scales;
- profile scoring formulas;
- automatic aggregation rules;
- exact Knowledge or Understanding lifecycle vocabularies;
- a Claim database table or ontology node;
- a specific graph schema or relation arity encoding;
- RDF, OWL, SKOS, SHACL, property graphs, or another ontology technology;
- an exact Synthesis or Reasoning class hierarchy;
- a physical Understanding storage representation;
- agent voting or escalation rules;
- product UI behavior; or
- investment decision rules.

These matters remain subject to their legitimate downstream authorities and future approval.

## 7. Related Documents

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [DR-0001: Adopt the Stock_vis Research Lab Scientific Philosophy v1](DR-0001-adopt-scientific-philosophy-v1.md)
- [DR-0002: Adopt the Stock_vis Research Lab Terminology Governance v1](DR-0002-adopt-terminology-governance-v1.md)
