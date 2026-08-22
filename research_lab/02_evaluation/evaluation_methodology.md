# Stock_vis Research Lab Evaluation Methodology

**Status:** Draft  
**Version:** 1.0-draft  
**Last Updated:** 2026-08-22  
**Owner:** Stock_vis Research Lab  
**Approval:** Pending Project Owner review  
**Effective Date:** Not yet effective

## 1. Purpose

The purpose of the Evaluation Methodology is to define how the Stock_vis Research Lab critically characterizes the epistemic quality, limitations, uncertainty, and fitness of research objects in relation to Reality, declared scope, and intended use.

Evaluation is not primarily a certification or scoring system. Its central function is to make support, weakness, conflict, uncertainty, unassessed areas, and conditions of failure explicit enough that research and later decisions can use them responsibly.

The Evaluation Methodology operationalizes the Scientific Philosophy and the Knowledge and Understanding Framework. It does not redefine the philosophical meaning of Reality, Evidence, Understanding, or Models, and it does not replace Research Methodology's authority over the research lifecycle.

## 2. Scope and Authority

The Evaluation Methodology domain holds normative authority over general epistemic evaluation within the Stock_vis Research Lab. This document is the canonical Authority Source and resolution point through which that authority is expressed for v1.

It governs:

- common principles for evaluation;
- the semantic contract of an evaluation;
- object-relative evaluation families;
- Evidence Item, Evidence–Claim, and Evidence Body evaluation;
- Claim and Research Knowledge credibility evaluation;
- Composition Evaluation for Composite Knowledge;
- operationalization of the approved Understanding Epistemic Profile;
- evaluation of research process quality;
- general Model, Model Use, and Model Run/Output evaluation;
- consequence-proportional rigor and effective challenge;
- versioned Evaluation Records;
- material warrant and dependency traceability;
- re-evaluation and reconsideration triggers as evaluation mechanisms; and
- meta-evaluation of the Evaluation Methodology itself.

This document does not define:

- the research lifecycle or next-action rules;
- the philosophical meaning of Understanding or Models;
- exact numerical scores or admission thresholds;
- model-specific validation metrics or benchmarks;
- agent voting or orchestration algorithms;
- ontology, database, or graph implementation; or
- investment decision rules.

## 3. Evaluation Philosophy

### 3.1 Reality Takes Precedence Over Metrics

Evaluation metrics, benchmarks, scores, and checklists are instruments for examining Reality. They are not substitutes for Reality and must not become authoritative merely because they are easy to measure.

A high benchmark score does not by itself establish a strong Model, Knowledge item, or Understanding. An apparently strong evaluation must remain open to challenge when Reality, new Evidence, or changed conditions reveal material failure.

### 3.2 Evaluation Is Critical Characterization

Evaluation should answer questions such as:

- What is supported?
- What is weak?
- What conflicts with the current result?
- What has not been assessed?
- What remains uncertain?
- What assumptions and dependencies matter?
- Under what conditions might the result fail or cease to apply?

A binary PASS/FAIL result may be useful for a particular operational gate, but it must not replace the underlying structured assessment.

### 3.3 Evaluation Structures Uncertainty Rather Than Eliminating It

Evaluation does not transform uncertainty into certainty by declaration. It seeks to convert unstructured uncertainty into explicit, interpretable uncertainty.

Not Material, Unassessed, Unknown, Unsupported, Contradicted, Out of Scope, and No Longer Applicable must remain distinguishable when materially relevant.

### 3.4 Evaluation Is Object-Relative and Context-Bound

Different epistemic objects require different evaluation questions. The same object may also require different rigor or criteria depending on Evaluation Purpose, scope, and epistemic consequence.

Evaluation without an explicit target and purpose is incomplete.

### 3.5 Evaluation Must Provide Effective Challenge

Evaluation must do more than confirm what supports a preferred result. Material evaluation should actively examine competing explanations, contrary evidence, missing evidence, dependency, hidden assumptions, and plausible failure conditions.

The degree of independent or adversarial challenge should be proportional to epistemic consequence rather than required uniformly for all work.

### 3.6 Evaluation Is Falsifiable and Revisable

Evaluation criteria, profiles, benchmarks, and prior assessments may themselves be wrong, incomplete, outdated, or poorly calibrated.

Evaluation therefore remains subject to re-evaluation and meta-evaluation. No evaluation method is exempt from the Scientific Philosophy's requirement to remain open to challenge from Reality and Evidence.

## 4. Common Evaluation Contract

Every material evaluation should be semantically resolvable through a common contract.

Conceptually, an evaluation includes:

```text
Evaluation Target
+ Target State / Version
+ Evaluation Purpose
+ Declared Scope / Context
+ Epistemic Consequence
+ Applicable Evaluation Profile
+ Material Evidence / Provenance
+ Effective Challenge
→ Structured Evaluation Result
```

A Structured Evaluation Result should preserve, where material:

- what object and version were evaluated;
- why the evaluation was performed;
- which scope, context, and intended use were assumed;
- which evaluation profile or criteria version was used;
- material supporting findings;
- material weaknesses and limitations;
- conflicts and alternatives;
- unassessed or unknown areas;
- material assumptions and dependencies;
- the degree or form of evaluation rigor used;
- evaluation time; and
- conditions that should trigger re-evaluation.

This is a semantic contract, not a mandatory database schema.

### 4.1 Materiality and Assessment State

Evaluation dimensions apply according to materiality for the target, purpose, scope, and consequence being evaluated. A dimension that is not material for a particular evaluation need not be forced into a favorable or unfavorable rating.

The following distinctions must be preserved when relevant:

```text
Not Material ≠ Favorable
Unassessed ≠ Unfavorable
Unknown ≠ Contradicted
```

An evaluation must not manufacture apparent completeness merely to fill every profile dimension.

## 5. Evaluation Object Map

Evaluation Methodology v1 recognizes the following general evaluation families:

1. **Evidence Evaluation** — evaluates Evidence Items, their relation to Claims, and Claim-relative Evidence Bodies.
2. **Claim / Knowledge Evaluation** — evaluates whether a bounded assertion is sufficiently warranted for its stated scope and purpose.
3. **Composition Evaluation** — evaluates new epistemic structure introduced when existing epistemic units are composed, inferred, compared, transformed, or integrated.
4. **Understanding Evaluation** — operationalizes the approved Understanding Epistemic Profile.
5. **Research Process Evaluation** — evaluates whether the process that produced a result provided adequate epistemic warrant.
6. **Model Evaluation** — evaluates Models, Model Uses, and Model Runs/Outputs in relation to purpose, scope, context, and Reality.
7. **Decision-Support Evaluation** — reserved for later downstream methodology; v1 recognizes the family but does not define its complete profile.

These families share common principles but do not collapse into one universal quality score.

## 6. Evidence Evaluation

Evidence evaluation has three conceptually distinct layers.

### 6.1 Evidence Item Profile

An Evidence Item Profile asks how trustworthy and faithful the individual evidential item is as information about Reality.

The current v1 conceptual functions are:

#### Provenance Integrity

Can the Evidence's origin, derivation, source ancestry, and material transformations be determined and trusted sufficiently for the intended use?

#### Generation Reliability

Was the Evidence generated, measured, collected, reported, computed, modeled, or otherwise produced through a process reliable enough for the intended inference?

Generation Reliability may include measurement quality, sampling, methodology, reporting process, data processing, model generation, or other modality-specific concerns.

#### Information Fidelity

Does the Evidence preserve the relevant content with sufficient accuracy, resolution, and completeness, or has material information been lost, distorted, summarized, or transformed?

Source reputation may inform these judgments but must not substitute for them.

### 6.2 Evidence–Claim Relation

Evidence is not inherently supporting or challenging without reference to a Claim.

An Evidence–Claim relation may evaluate, where material:

- **Relevance / Directness** — how directly the Evidence bears on the Claim;
- **Scope / Context Fit** — whether entity, time, geography, population, regime, state, or other context matches the Claim;
- **Direction** — whether the Evidence supports, challenges, qualifies, is mixed, is neutral, or is inconclusive with respect to the Claim; and
- **Discriminative Value** — where material, whether the Evidence distinguishes the Claim from plausible competing explanations rather than merely being compatible with all of them.

Not every dimension is material for every Claim.

### 6.3 Claim-Relative Evidence Body

An Evidence Body is evaluated relative to a particular Claim and Evaluation Purpose. It is not defined merely as a fixed collection of sources.

Material concerns may include:

- **Independence / Dependency** — whether apparent support shares common source, model, assumption, or derivation roots;
- **Consistency / Conflict** — whether material evidence agrees, conflicts, or differs under identifiable conditions;
- **Coverage / Adequacy** — whether the evidence body sufficiently addresses the relevant parts of the Claim; and
- **Precision / Resolution** — where material, whether uncertainty or measurement resolution is sufficient for the intended inference.

Evidence count alone must not be treated as independent support count.

## 7. Claim and Research Knowledge Credibility

Candidate Claims and admitted Atomic Research Knowledge share a common core credibility profile because both concern the warrant of a bounded assertion. Their Evaluation Purpose, epistemic state, and required rigor may differ.

The current v1 core conceptual functions are:

### 7.1 Evidential Sufficiency

Are the material Evidence Items, Evidence–Claim relations, and Claim-relative Evidence Body sufficient to warrant the Claim at its stated strength and scope?

Evidence profiles are inputs to this judgment, not scores that are automatically averaged or inherited.

### 7.2 Inferential Soundness

Is the reasoning from Evidence to Claim justified? Are material logical bridges, causal assumptions, prediction assumptions, comparison logic, or other inferential steps legitimate?

### 7.3 Scope Calibration

Is the Claim's scope, strength, and conditionality calibrated to what its Evidence and inference actually warrant, rather than being materially overgeneralized or overstated?

### 7.4 Challenge Resilience

After material counterevidence, plausible alternatives, assumptions, and failure conditions have been examined, does the Claim remain sufficiently warranted for its intended epistemic use?

The exact names of these dimensions may be refined without changing their conceptual functions. Their applicability in a particular evaluation remains subject to the materiality rule in Section 4.1.

### 7.5 Claim Modality and Conditional Extensions

Claims may require modality-specific evaluation extensions, including for descriptive/reported, causal/explanatory, predictive, comparative, model-derived, or other Claim forms.

V1 does not adopt an exhaustive Claim taxonomy. Claim modality is used as evaluation-routing metadata so that universal profiles do not expand indefinitely.

### 7.6 Probability Is Not Credibility

A probability expressed in Claim content, such as a 60% forecast probability, is not the same as epistemic credibility in the estimate or Claim.

### 7.7 Admission Is Not a Credibility Score

Knowledge admission depends on Evaluation Purpose and applicable admission criteria. It must not be reduced by definition to passing one numerical credibility threshold.

An admitted Knowledge item may retain explicit limitations, unresolved alternatives, or scope restrictions.

Every Knowledge admission requires an admission-purpose structured evaluation. The required rigor may differ with epistemic consequence, but admission must not occur without an applicable evaluation.

## 8. Composition Evaluation

Composite Research Knowledge introduces new epistemic structure that is not evaluated merely by re-evaluating component Knowledge.

Composition Evaluation focuses on:

```text
Input epistemic units
+ Composition operation
+ Newly introduced assumptions / interfaces / transformations
→ Candidate Composite Result
```

### 8.1 No Default Transitivity

No relation type is assumed to be transitive merely because `A → B` and `B → C` are admitted. A resulting `A → C` Claim requires its own warrant.

### 8.2 Composition Mode / Operator

The material operation used to compose epistemic units should be identifiable. Possible examples include chaining, aggregation, comparison, normalization, transformation, and integration.

V1 does not fix a complete operator taxonomy.

### 8.3 Composition Warrant Layer

The current v1 conceptual checks are:

- **Operation Validity** — whether the composition or inference operation is legitimate;
- **Interface Compatibility** — whether the connected concepts, entities, units, scopes, states, or conditions are compatible;
- **Dependency Integrity** — whether shared evidence, model ancestry, assumptions, or circularity distort apparent support;
- **Scope / Condition Propagation** — whether scope and boundary conditions are transformed explicitly and legitimately; and
- **Emergent Interaction / Nonlinearity** — whether interaction, bottleneck, substitution, complementarity, aggregation effects, or other emergent behavior undermine naive composition.

These checks explain composition-specific warrant. They do not replace the Claim / Knowledge Core Profile.

### 8.4 Critical Warrant Paths

Composite credibility must not be calculated automatically as an average, minimum, product, or other arithmetic aggregation of component credibility.

Where material, evaluation should identify which upstream Knowledge, assumptions, interfaces, or inferential bridges are critical to the Composite result and which are redundant or non-critical.

### 8.5 Composite Knowledge or Understanding

A composition that produces a bounded reusable assertion may become a Composite Knowledge candidate. A composition that primarily creates an organized reasoning structure across multiple epistemic units is more appropriately evaluated as Understanding synthesis.

## 9. Understanding Evaluation

The authoritative conceptual profile for Understanding is defined by the Knowledge and Understanding Framework. Evaluation Methodology operationalizes, but does not redefine, its four dimensions:

1. **Support Sufficiency**
2. **Structural Integrity**
3. **Scope Adequacy**
4. **Robustness**

Understanding evaluation may also preserve material annotations such as:

- Critical Weaknesses
- Unresolved Alternatives
- Unassessed Areas
- Important Dependencies
- Boundary Conditions
- Temporal or contextual limitations

Understanding credibility is not a scalar inherited from component Knowledge.

Credibility, current applicability, and downstream Decision relevance remain distinct.

## 10. Research Process Evaluation

Research Methodology defines how research should proceed. Evaluation Methodology may assess whether the process actually provided adequate epistemic warrant for the result being claimed.

Material process evaluation may examine:

- alignment between Question and Research Design;
- whether exploration and confirmation were improperly conflated;
- source or evidence selection bias;
- whether material alternatives were sought;
- adherence to pre-specified methods when confirmation required them;
- reproducibility of material transformations or analyses;
- whether deviations were material and transparently handled; and
- whether methodological weaknesses affect the resulting Claim.

Process quality and result quality remain distinguishable. A rigorous process may produce an unresolved result, and a weak process may occasionally produce a correct result without adequate warrant.

## 11. Model Evaluation

### 11.1 Distinguish Model, Model Use, and Model Run / Output

Model Evaluation must distinguish:

- **Model** — the representation, algorithmic, statistical, simulation, or other model itself;
- **Model Use** — the application of that model for a stated purpose, scope, horizon, regime, or context; and
- **Model Run / Output** — a particular execution or result produced under specific inputs and configuration.

A strong evaluation at one level does not automatically transfer to the others.

### 11.2 Model Validity Is Context-Bound

Model validity is not treated as an absolute context-free property.

A Model is evaluated as sufficiently valid or credible **for a stated Purpose, Scope, and Context of Use**. Reuse outside that context may require additional evaluation.

### 11.3 Model Common Core

The current v1 conceptual functions are:

#### Conceptual Soundness

Does the Model represent relevant aspects of Reality in a way appropriate to its stated purpose, including material assumptions, simplifications, and structural choices?

#### Implementation Fidelity / Verification

Has the intended Model been implemented, computed, or executed correctly enough that implementation defects do not materially distort the intended representation?

#### Empirical Validity

Does Model behavior agree sufficiently with relevant Reality, referent data, outcomes, or other empirical tests for the intended use?

#### Robustness and Uncertainty

How sensitive is the Model to inputs, assumptions, data, conditions, regimes, or perturbations, and is material uncertainty adequately characterized?

#### Applicability / Use Fitness

Is the Model appropriate for the declared target, purpose, scope, population, horizon, regime, and current context?

### 11.4 Model Modality Extensions

Different Model modalities may require additional evaluation, such as calibration and out-of-sample stability for predictive models, identification assumptions for causal models, sensitivity and referent validation for simulations, or grounding and hallucination risk for generative models.

V1 does not adopt a fixed Model taxonomy or modality-specific metric catalog.

### 11.5 Performance Is Not Model Credibility

No single performance metric, benchmark, complexity measure, or accuracy score is equivalent by definition to Model credibility or contribution to Understanding.

### 11.6 Model Research Contribution Is Distinct

A Model's research value concerns how its use advances Research Claims, Knowledge, Understanding, or future research. This is distinct from Model credibility itself.

### 11.7 Model Output Does Not Inherit Model Credibility

A Model-derived output must be evaluated in relation to the Model version, Model Evaluation, inputs, run configuration, output uncertainty, and Context of Use before it serves as material Evidence or support for a Claim.

## 12. Proportional Evaluation Rigor

Evaluation rigor should be driven by epistemic consequence rather than a single burden for all work.

Material rigor drivers may include:

- epistemic consequence;
- downstream dependency and reuse;
- uncertainty;
- novelty and complexity;
- evidence conflict or dependence;
- difficulty of reversal; and
- consequences of being wrong.

V1 does not adopt fixed rigor tiers or numeric thresholds.

### 12.1 Urgency Does Not Redefine Epistemic Quality

Urgent use may justify provisional or restricted use, explicit limitations, increased monitoring, or later follow-up evaluation. Urgency must not silently convert incomplete evaluation into stronger epistemic quality.

## 13. Material Warrant Network

The Research Lab adopts **Material Warrant Network** as a conceptual cross-layer backbone for epistemic traceability.

The requirement is not to store every intermediate reasoning step. It is that formal epistemic outputs remain sufficiently connected to material upstream warrant and downstream dependency, including material assumptions, transformations, weaknesses, and versions, so that consequential warrant and impact paths can be reconstructed when needed.

The network may conceptually link:

```text
Evidence
  ↓ bears on
Claims / Atomic Knowledge
  ↓ composed through
Composite Knowledge
  ↓ organized into
Understanding

Models / Model Uses / Outputs
  ↕ may support or challenge multiple layers

Evaluation Records
  ↕ characterize specific object states and purposes
```

The exact graph, relational, document, or hybrid implementation is a Non-Decision of v1.

### 13.1 Local Evaluation, Global Traceability

Each Evaluation layer evaluates the epistemic structure newly introduced at that layer. Material lineage and dependency remain traceable across layers.

### 13.2 Referential Propagation, Not Scalar Propagation

Upstream evaluation scores or labels must not automatically propagate into downstream credibility.

What propagates is material epistemic information: support, weakness, dependency, assumptions, scope conditions, uncertainty, and relevant Evaluation Records.

### 13.3 Change Propagates Review Obligations, Not Conclusions

When an upstream object changes materially, dependent downstream objects are not automatically invalidated or downgraded. Instead, material dependencies should generate impact review and, when warranted, Re-evaluation Triggers.

## 14. Versioned Evaluation Records and Reuse

A formal Evaluation Result is a versioned, purpose-bound assessment rather than a permanent certificate.

A material Evaluation Record should remain associated with:

- target identity and version/state;
- Evaluation Purpose;
- declared scope and context;
- applicable profile or criteria version;
- material findings and warrant links;
- unassessed areas;
- evaluation time; and
- re-evaluation conditions.

Prior evaluation may be reused when the previous target state, purpose, context, criteria, and material evidence remain sufficiently compatible. Mere existence of a previous evaluation does not automatically authorize reuse.

The exact compatibility algorithm is not fixed by v1.

## 15. Re-evaluation and Reconsideration Triggers

This section is the canonical methodological definition source for Re-evaluation Trigger and Reconsideration Trigger in v1.

### 15.1 Re-evaluation Trigger

A Re-evaluation Trigger indicates that an existing evaluation of an Evidence item, Claim, Knowledge item, Understanding, Model, Model Use, Model Output, or other evaluable object may no longer be adequate for the current object state or use.

Signals may include:

- material new Evidence;
- material object revision;
- scope, regime, or Context of Use change;
- new conflicting evidence;
- unexpected real-world outcome;
- material dependency change;
- evaluation-method revision; or
- discovery of a previous evaluation error.

A trigger creates a review obligation. It does not predetermine the new conclusion.

### 15.2 Reconsideration Trigger

A Reconsideration Trigger indicates that an existing methodology, evaluation architecture, assumption, or consequential decision should be reopened to determine whether it should be retained, modified, restricted, or replaced.

For the Material Warrant Network, observable signals may include:

- maintenance burden materially exceeding practical epistemic value;
- low use of stored warrant information in revision, impact analysis, or research reuse;
- a substantially simpler provenance approach providing equivalent practical protection; or
- repeated failure of the network to detect material dependency or revision impact.

The trigger does not require change. It requires reconsideration.

Exact thresholds remain a Non-Decision of v1.

## 16. Meta-Evaluation

The Evaluation Methodology itself must be evaluated over time.

Meta-evaluation may examine, where data permit:

- repeated false confidence;
- repeated over-rejection of useful research;
- evaluator or agent inconsistency;
- recurring missed failure patterns;
- criteria or benchmark drift;
- disagreement between prior evaluation and later observations, evidence, or outcomes concerning Reality;
- burden relative to practical value; and
- whether Re-evaluation and Reconsideration Triggers are functioning as intended.

V1 does not adopt exact calibration metrics or thresholds for meta-evaluation.

## 17. Evaluation Handoff and Downstream Action

Evaluation produces a structured assessment. It does not automatically own the downstream lifecycle or governance action.

When Evaluation is performed within a research lifecycle or for Research Knowledge admission, Evaluation Methodology owns the applicable epistemic criteria and assessment, while Research Methodology owns the workflow process and lifecycle action taken in response.

```text
Candidate Research Object
  ↓
Evaluation Methodology
  ↓
Structured Assessment
  ↓
Research Methodology
  ↓
Lifecycle / Admission Action
```

In other contexts, including Model governance, ongoing monitoring, meta-evaluation, or future downstream decision-support systems, the legitimate downstream authority owns the response to the structured assessment.

This separation prevents Evaluation from silently becoming an automatic epistemic promotion or governance mechanism.

## 18. Boundaries and Non-Decisions

Evaluation Methodology v1 does not adopt:

- a universal scalar quality score;
- evidence weights;
- numerical credibility scales;
- exact Knowledge admission thresholds;
- exact High / Medium / Low definitions;
- fixed rigor tiers or escalation thresholds;
- a complete Claim Modality taxonomy;
- a complete Composition Operator taxonomy;
- a complete Model Modality taxonomy;
- exact lifecycle or evaluation-outcome vocabulary;
- agent voting or consensus rules;
- mandatory independent evaluators for every evaluation;
- an evaluation reuse compatibility algorithm;
- exact Re-evaluation or Reconsideration thresholds;
- meta-evaluation calibration metrics;
- a graph, ontology, database, or storage implementation for Material Warrant Network;
- model-specific benchmark or validation metrics; or
- investment Decision-Support evaluation criteria.

These matters may be specified later by legitimate authorities when empirical operation justifies greater precision.

## 19. Dependencies and Related Documents

This document depends on and must remain consistent with:

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](../01_methodology/research_methodology.md)

Research Methodology is a peer operational authority. Evaluation Methodology does not own the research lifecycle.

## 20. Change Log

### 1.0-draft — 2026-08-22

- Initial draft based on the approved Knowledge and Understanding Framework and the Evaluation Methodology working consensus.
- Established reality-grounded critical characterization as the Evaluation philosophy.
- Defined the Common Evaluation Contract and object-relative Evaluation Map.
- Defined Evidence Item, Evidence–Claim, and Claim-relative Evidence Body evaluation.
- Defined the Claim / Knowledge Core Credibility Profile and conditional extensions.
- Added Composition Warrant evaluation and critical warrant-path analysis.
- Operationalized the approved Understanding Epistemic Profile.
- Established general Model / Model Use / Model Run-Output evaluation with context-bound validity.
- Adopted the Material Warrant Network conceptual backbone.
- Established versioned Evaluation Records, proportional rigor, Re-evaluation and Reconsideration Triggers, and Meta-Evaluation.
- Clarified Authority Source wording, dimension materiality, warrant/dependency directionality, meta-evaluation language, and downstream handoff boundaries after adversarial document review.
