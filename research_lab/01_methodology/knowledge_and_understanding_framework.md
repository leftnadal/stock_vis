# Stock_vis Research Lab Knowledge and Understanding Framework

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-08-20  
**Owner:** Stock_vis Research Lab  
**Approval:** Approved by Project Owner on 2026-08-20  
**Effective Date:** 2026-08-20

## 1. Purpose

The purpose of the Knowledge and Understanding Framework is to define the operational conceptual structure by which the Stock_vis Research Lab represents Research Claims, Research Knowledge, and Understanding while preserving epistemic traceability, uncertainty, revision, and compatibility with future evaluation and machine-readable systems.

The framework supports the Research Lab's direct purpose of developing a better understanding of reality. It does not redefine the philosophical meaning of Understanding established by the Scientific Philosophy. Instead, it specifies how Research Knowledge relates to Understanding at the Methodology level and establishes boundaries that later Research Methodology, Evaluation Methodology, Model Documents, ontology work, and research automation must respect.

The framework is designed to prevent several recurrent failures:

- evidence, hypotheses, model outputs, or collections of existing Knowledge being silently promoted into stronger epistemic states;
- credibility being inherited or averaged across compositions without evaluating new inferential structure;
- a Research Claim's semantic content being confused with its role as a Hypothesis or its admission as Research Knowledge;
- revision overwriting the history required to reproduce earlier research and decisions;
- uncertainty or competing explanations being removed merely to force consensus;
- current applicability being confused with credibility; and
- AI-, model-, or knowledge-derived outputs creating circular support for themselves.

## 2. Scope

This framework governs the operational conceptual boundaries among:

- Evidence and Observation;
- Research Claims;
- Hypotheses as research roles;
- Atomic Research Knowledge;
- Composite Research Knowledge;
- Understanding;
- Models and Model Outputs as they interact with epistemic objects;
- credibility and applicability at the conceptual level;
- epistemic revision and lineage; and
- the relationship between Understanding and downstream Judgment and Decision.

This framework does not prescribe concrete research procedures, evidence weights, admission thresholds, numerical credibility scores, validation tests, agent consensus algorithms, ontology languages, graph schemas, database representations, or product behavior.

Knowledge is treated here as a Research Output, not as a Research Primitive.

## 3. Authority and Upstream Constraints

The Scientific Philosophy remains the higher-level authority for the philosophical role of Reality, Understanding, Models, Research, Evidence, and falsifiability. In particular, Reality remains the final standard; Understanding of Reality remains the Research Lab's direct purpose; Models remain tools for understanding rather than ends in themselves; and better evidence must remain capable of changing current understanding.

Terminology Governance remains the cross-document authority for concept identity, semantic authority, governance scope, semantic lifecycle, provenance, and implementation-neutral ontology readiness.

This framework therefore operates under the following authority boundary:

```text
Scientific Philosophy
    ↓ constrains
Knowledge and Understanding Framework
    ↓ operationalized by
Research Methodology / Evaluation Methodology / Model Documents
    ↓ represented by
future ontology, schemas, automation, and software
```

Lower-level implementations must represent the approved semantics of this framework rather than silently redefine them.

## 4. Conceptual Architecture

The Research Protocol is a workflow architecture. This framework defines a distinct epistemic object architecture. The two must not be conflated.

A workflow may be expressed as:

```text
Research Question
→ Hypothesis
→ Research
→ Engineering
→ Evaluation
→ Knowledge
```

This sequence does not mean that one persistent object literally transforms from a Hypothesis into Knowledge. The epistemic architecture instead distinguishes semantic content, research roles, evaluation activities, and admitted epistemic outputs.

A simplified epistemic architecture is:

```text
Reality
  ↓
Observation / Evidence
  ↓ bears on
Research Claim
  ├─ may take a Hypothesis role in research
  └─ may, after evaluation and admission, become represented in Research Knowledge

Research Knowledge
  ├─ Atomic Research Knowledge
  └─ Composite Research Knowledge
        ↓ organized through synthesis
Understanding
        ↓ supports bounded warranted reasoning
New Research Claims
        ↓ may return to research and evaluation
```

Models are not a stage in this ladder. They form an orthogonal tool and representation layer that may help observe, analyze, generate, test, express, support, or challenge Evidence, Research Claims, Knowledge, and Understanding.

Understanding is also not a Decision. Decision requires downstream context and judgment.

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action / Outcome
→ Reality
→ possible new Research Trigger
```

## 5. Evidence and Research Claims

### 5.1 Evidence

Evidence consists of observations, measurements, data, records, documents, experimental results, comparisons, model-derived results, and other grounds that bear on claims about Reality.

Evidence is not automatically Research Knowledge. Its existence, quantity, recency, or agreement with a preferred explanation does not by itself establish an admitted epistemic result.

Evidence may support, challenge, qualify, or leave unresolved a Research Claim.

### 5.2 Research Claim

A Research Claim is an assertion about Reality that can be supported, challenged, qualified, revised, restricted, or rejected through research and evidence.

Research Claim is used in this framework as a methodological concept. This framework does not decide whether every Research Claim must later become a first-class ontology node, database record, or graph object.

The distinction between a Research Claim and its epistemic role is fundamental. The semantic content of an assertion may remain identifiable while the Research Lab changes how that assertion is being treated.

### 5.3 Hypothesis as a Research Role

A Hypothesis is a research role in which a Research Claim is made explicitly investigable and open to evidential challenge.

A Hypothesis does not silently become Knowledge merely because research has been completed. The relevant Research Claim may be admitted into Research Knowledge after appropriate evaluation, while the historical Hypothesis and its provenance remain traceable.

This preserves the distinction among:

```text
semantic content
≠ research role
≠ epistemic admission state
```

## 6. Research Knowledge

### 6.1 Research Knowledge

Research Knowledge is a current admitted epistemic output of the Stock_vis Research Lab. Admission means that the Research Lab currently accepts a bounded epistemic result for legitimate reuse under its stated scope, conditions, provenance, and epistemic limitations.

Admission is not a declaration of timeless or infallible truth. Research Knowledge remains revisable, restrictable, supersedable, splittable, mergeable, challengeable, and, where justified, rejectable in response to better evidence or improved understanding.

### 6.2 Atomic Research Knowledge

Atomic Research Knowledge is the smallest admitted epistemic unit that can be meaningfully evaluated, challenged, and revised as an independent epistemic boundary.

Atomicity is determined by epistemic contestability, not by a fixed graph arity or data representation.

A binary relationship between two objects may often be a useful Atomic Knowledge form, but the framework does not require every Atomic Knowledge item to be reducible to one binary edge. Some claims may be irreducibly conditional, interaction-dependent, multi-relational, or otherwise lose meaning if mechanically decomposed.

An Atomic Knowledge item may therefore include, where materially necessary:

- a core assertion;
- relevant scope;
- boundary or enabling conditions;
- temporal or contextual conditions;
- provenance and evidential basis;
- material assumptions;
- epistemic limitations; and
- its current epistemic state.

The precise storage requirements and minimum admission fields are delegated to later methodology and evaluation work.

### 6.3 Composite Research Knowledge

Composite Research Knowledge is a bounded epistemic result produced through composition, inference, or integration of existing epistemic units and separately admitted as Research Knowledge.

A collection of Atomic Knowledge is not automatically Composite Knowledge.

For example, if admitted Knowledge supports `A → B` and `B → C`, the new assertion `A → C` does not become admitted merely because its inputs are admitted. The composition introduces new inferential work that may create assumptions, dependency, scope changes, or failure points. The resulting bounded claim therefore requires its own warrant and, when treated as reusable Research Knowledge, its own admission.

Composite Knowledge must not inherit credibility automatically from its components.

## 7. Knowledge and Understanding

### 7.1 Distinct Epistemic Functions

Understanding is not merely larger Knowledge.

Research Knowledge preserves bounded epistemic claims or results so that they may be evaluated, revised, and reused.

Understanding organizes warranted Knowledge together with relevant relationships, conditions, boundaries, dependencies, alternatives, and uncertainty so that bounded warranted reasoning about Reality becomes possible.

The relationship is therefore a change in epistemic function rather than a simple size hierarchy.

```text
Atomic Knowledge
→ may contribute to Composite Knowledge
→ may contribute to Understanding
```

The arrows represent organization and epistemic contribution, not automatic promotion or increasing truth status.

### 7.2 Warrant Base and Non-Knowledge References

The warrant base of an Understanding is admitted Research Knowledge. However, an Understanding may also explicitly reference non-Knowledge elements when reasoning requires them, including:

- unresolved Hypotheses;
- competing explanations;
- identified Knowledge Gaps;
- uncertainty;
- Models; and
- scenarios or boundary conditions.

Their epistemic typing must remain explicit. Inclusion in an Understanding does not promote a Hypothesis, alternative, gap, scenario, Model Output, or other non-Knowledge item into Research Knowledge.

### 7.3 Competing and Partially Compatible Understandings

The Research Lab may maintain multiple Understandings of the same or overlapping aspects of Reality when evidence does not justify a single consolidated structure.

Such Understandings may be competing, partially compatible, condition-dependent, scope-dependent, or temporally differentiated.

The existence of multiple Understandings is not itself a governance failure. Prematurely forcing one preferred explanation into exclusive authority may suppress uncertainty and conflict that are epistemically material.

Later evidence may strengthen one Understanding, weaken another, reveal that they apply under different conditions, or support a substantially different structure.

## 8. Understanding Epistemic Profile

Understanding credibility is not defined as a single intrinsic scalar and is not calculated by averaging the credibility of component Knowledge.

An Understanding has a conceptual Epistemic Profile with four dimensions.

### 8.1 Support Sufficiency

Support Sufficiency asks whether the Knowledge and inferential warrants underlying the Understanding are sufficient for the structure it claims.

Material considerations may include weak critical links, dependence on shared evidence roots, concentrated support, insufficiently warranted bridges, and other support limitations.

### 8.2 Structural Integrity

Structural Integrity asks whether the organization of Knowledge and relationships is logically and semantically sound.

Material concerns may include contradiction, unsupported inferential jumps, circular reasoning, incompatible scopes, semantic mismatch, hidden assumptions, and structural single points of failure.

### 8.3 Scope Adequacy

Scope Adequacy asks whether an Understanding adequately represents what it claims to explain within its declared scope.

It does not require completeness with respect to Reality as a whole. Models and Understandings may legitimately select and simplify. The relevant question is whether material factors, relationships, or conditions required by the declared scope have been omitted or inadequately represented.

### 8.4 Robustness

Robustness asks whether the core structure remains warranted under plausible changes in assumptions, evidence, conditions, regimes, or competing explanations.

Robustness does not require invariance under every possible condition. Boundary-sensitive Understanding may be legitimate when those boundaries are explicit.

### 8.5 Epistemic Annotations

The four dimensions do not exhaust all useful information. Material annotations may include:

- Critical Weaknesses;
- Unresolved Alternatives;
- Unassessed Areas;
- Important Dependencies;
- Boundary Conditions;
- temporal or contextual limitations; and
- other epistemically material uncertainty.

The framework does not prescribe a fixed annotation schema.

### 8.6 Credibility and Applicability

Credibility and applicability are distinct.

Credibility concerns how well an epistemic structure is warranted. Applicability concerns whether that structure is appropriate to a particular current scope, condition, regime, time, or use context.

An Understanding may remain historically credible while no longer being applicable under current conditions. Conversely, apparent current relevance does not establish epistemic strength.

Decision-specific relevance or confidence is also not an intrinsic Understanding property. It arises downstream when Understanding is considered together with Decision Context.

## 9. Models and Model Outputs

A Model is not Research Knowledge and is not Understanding itself.

A Model may select, simplify, represent, analyze, simulate, predict, classify, generate, test, or challenge aspects of Reality and may thereby contribute to research and Understanding.

A Model Output is not automatically Research Knowledge. It may function as Evidence, generate a candidate Research Claim, or contribute to another research process, but admission requires appropriate evaluation of its assumptions, inputs, validation, scope, limitations, and relationship to other evidence.

The fact that an AI or Model generated an assertion does not confer epistemic status on that assertion.

## 10. Epistemic Evolution and Lineage

### 10.1 Revision

Research Knowledge and Understanding are expected to evolve with better evidence and improved understanding.

Material revision must preserve enough lineage to determine what changed, why it changed, and which prior research, models, evaluations, or decisions materially depended on an earlier epistemic state.

Current state must not silently overwrite material historical state.

### 10.2 Split, Merge, Restriction, and Supersession

A Knowledge item or Understanding may later prove too broad, too narrow, duplicative, condition-specific, or structurally inadequate.

Revision may therefore require split, merge, scope restriction, supersession, replacement, or another lifecycle action. The exact lifecycle vocabulary is not decided by v1.

Where the action is materially consequential, lineage must preserve the relationship between earlier and later epistemic states.

### 10.3 Disagreement

Disagreement among researchers or research agents may itself be epistemically material. It must not be erased merely to manufacture consensus.

Knowledge admission represents the Research Lab's current epistemic acceptance under an approved evaluation process, not an infallible truth declaration.

The specific agent workflow, voting logic, escalation rules, and admission thresholds are delegated to later methodology and evaluation work.

## 11. Architecture Invariants

The following invariants constrain future operationalization and implementation.

### 11.1 No Silent Epistemic Promotion

No Evidence, Hypothesis, Model Output, Knowledge collection, or other object acquires a stronger epistemic status merely through inclusion, composition, generation, or workflow completion.

### 11.2 No Automatic Credibility Inheritance

Credibility of lower-level Knowledge does not automatically transfer, average, or aggregate into Composite Knowledge or Understanding. New composition and organization create new epistemic structure that must remain open to evaluation.

### 11.3 Content–Role–Status Separation

The semantic content of a Research Claim, the role in which it is investigated, and its current epistemic admission state must remain distinguishable.

### 11.4 Process–Object Separation

Activities such as Evaluation, Admission, Synthesis, and Reasoning must remain conceptually distinguishable from the epistemic objects they use or produce.

A future system may persist records of those activities without collapsing the distinction.

### 11.5 Intrinsic–Decision Context Separation

The intrinsic epistemic qualities of an Understanding must remain distinguishable from its relevance, usefulness, or confidence for a particular Decision Context.

### 11.6 Revision Must Preserve Lineage

Material revision, split, merge, restriction, supersession, or replacement must preserve sufficient lineage for historical interpretation and reproducibility.

### 11.7 No Circular Epistemic Support

A Research Claim, Knowledge item, Understanding, Model, or Model Output must not gain independent support by recursively relying on its own derivation chain.

Shared evidence ancestry, model ancestry, and material derivation dependency must be distinguishable when necessary so that circular or duplicated support is not mistaken for independent corroboration.

## 12. Boundaries and Non-Decisions

Knowledge and Understanding Framework v1 establishes conceptual boundaries and invariants. It intentionally does not decide:

- concrete Research Knowledge admission procedures;
- minimum evidence requirements;
- evidence weights or independence formulas;
- numerical credibility scores;
- High / Medium / Low or other rating scales;
- validation thresholds;
- formulas for the Understanding Epistemic Profile;
- aggregation rules for credibility;
- agent consensus, dispute-resolution, or escalation algorithms;
- a final lifecycle vocabulary for Research Knowledge or Understanding;
- whether Research Claim is a first-class ontology entity;
- database tables, persistent object schemas, or identifier formats;
- graph arity or relation encoding;
- RDF, OWL, SKOS, SHACL, property-graph, or other ontology technologies;
- the formal class relationship between Synthesis and Reasoning activities;
- the physical storage model of Understanding;
- product UI representations; or
- investment decision rules.

These matters require later Methodology, Evaluation, Model, ontology, engineering, or product decisions as appropriate.

## 13. Dependencies and Future Work

Future Research Methodology should operationalize how Research Claims arise from Research Problems and Questions, how Hypotheses are investigated, and how research proceeds toward evaluable outputs and Knowledge admission.

Future Evaluation Methodology should define evidence evaluation, Research Knowledge credibility, admission criteria, Understanding Epistemic Profile assessment, disagreement handling, validation, and related procedures without contradicting the conceptual boundaries of this framework.

Model Documents should record model-specific assumptions, data, outputs, scope, limitations, validation, and the role of model-derived results in Evidence, Claims, Knowledge, and Understanding.

Future ontology and automation work should preserve concept identity, provenance, epistemic typing, lineage, and the architecture invariants established here while remaining subordinate to approved semantic authorities.

## 14. Change Log

### v1.0 — 2026-08-20

- Established the operational conceptual boundaries among Evidence, Research Claims, Hypotheses, Research Knowledge, Understanding, Models, and Decisions.
- Defined Atomic and Composite Research Knowledge by epistemic boundary rather than representation size or graph arity.
- Defined Understanding as an organized epistemic structure supporting bounded warranted reasoning rather than as a larger Knowledge unit.
- Established the four-dimensional Understanding Epistemic Profile: Support Sufficiency, Structural Integrity, Scope Adequacy, and Robustness.
- Distinguished credibility from applicability and intrinsic epistemic quality from decision-specific relevance.
- Allowed competing and partially compatible Understandings to coexist when evidence does not justify premature consolidation.
- Established lineage-preserving epistemic evolution and seven architecture invariants.
- Preserved implementation neutrality by deferring metrics, thresholds, schemas, ontology technologies, and agent workflow details to later work.
