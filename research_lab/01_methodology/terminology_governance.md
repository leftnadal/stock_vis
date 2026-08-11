# Stock_vis Research Lab Terminology Governance

**Status:** Approved  
**Version:** 1.0  
**Last Updated:** 2026-08-12  
**Owner:** Stock_vis Research Lab  
**Approval:** Approved by Project Owner on 2026-08-12  
**Effective Date:** 2026-08-12

## 1. Purpose

The purpose of Terminology Governance is to preserve semantic consistency, traceability, and accountable meaning across the Stock_vis Research Lab while preserving legitimate autonomy within individual research domains.

Terminology Governance does not exist to force every document to use the same word. The same concept may have different labels, and the same label may refer to different concepts in different contexts. The object of governance is therefore the concept and its authoritative meaning, not the surface form of a word alone.

As the Research Lab grows, concepts may be reused across Foundation, Methodology, Evaluation, Model Documents, Decision Records, automation, and future machine-readable representations. Without explicit governance, definitions may drift, copied wording may become mistaken for authority, semantic changes may overwrite history, and different domains may claim incompatible meanings for the same concept.

Terminology Governance establishes how concept identity, authority, semantic scope, change, relationships, and historical continuity are managed so that the Research Lab can evolve without losing the meaning of its own knowledge.

## 2. Scope

Terminology Governance is a cross-document governance layer. It governs the integrity and authority of meaning across the Research Lab; it does not replace the documents that legitimately define that meaning.

For example, if the Scientific Philosophy is the Primary Authority for a concept, Terminology Governance does not redefine that concept. It records and preserves where its authoritative meaning resides, how that meaning may be referenced elsewhere, and how semantic changes must be handled.

Terminology Governance applies to:

- concept identity;
- designations and labels;
- authoritative meaning and semantic scope;
- Primary Authority and Authority Sources;
- governance scope and stewardship;
- terminological relationships and external mappings;
- semantic change, lifecycle, and provenance;
- cross-document semantic consistency;
- historical reproducibility; and
- future machine-readable terminology representations.

Terminology Governance does not, by itself, govern every real-world entity, instance, event, observation, research claim, research result, or model output expressed using governed concepts.

Terminology Governance also does not define specific research procedures, evaluation criteria, model implementations, product behavior, ontology languages, knowledge-graph architectures, or software schemas unless a later approved document explicitly assigns such responsibilities to terminology governance.

## 3. Governance Principles

The principles are ordered logically rather than procedurally.

### Principle 1 — Terminology governs concepts, not words.

#### Meaning

A concept is the semantic object of governance. A word, phrase, acronym, translation, or display label is a designation used to refer to a concept.

The same concept may legitimately have multiple designations. The same designation may also refer to different concepts when their meanings differ.

#### Governance Implication

Terminology decisions must begin by determining what concept is meant rather than by assuming that lexical similarity or difference determines conceptual identity.

---

### Principle 2 — Concept identity must remain stable across representational change, while material changes in meaning must remain explicit and traceable.

#### Meaning

A concept must not lose its identity merely because its preferred label, wording, file location, section location, translation, or other representation changes.

Identity stability does not mean semantic immutability. When the meaning of a concept materially changes, that change must be made explicit and must not be hidden behind unchanged wording, identifiers, or file locations.

#### Governance Implication

Representational change may preserve concept identity. Material semantic change requires explicit review, history, and lifecycle handling. An inactive identifier must not be repurposed for a different semantic identity.

---

### Principle 3 — Meaning authority is federated across the Research Lab.

#### Meaning

Semantic authority does not reside in one universal glossary or one central document. Different concepts may legitimately be governed by different domains according to their semantic responsibilities.

Federation does not mean uncontrolled local redefinition. Federated authority must remain resolvable, accountable, and consistent with higher-level authorities.

#### Governance Implication

A concept may be governed by Foundation, Methodology, Evaluation, a Model domain, or another legitimate authority according to semantic jurisdiction rather than file location, historical origin, or frequency of use.

---

### Principle 4 — Every governed concept must have one designated Primary Authority for its authoritative meaning.

#### Meaning

The Primary Authority is the single designated governance assignment that determines where final normative authority over a governed concept’s meaning resides when competing definitions or interpretations arise.

The Primary Authority is not identical to a person, a file, or a steward. It is expressed through one or more authoritative sources and maintained through stewardship.

One Primary Authority does not require one artificially precise interpretation. A Primary Authority may explicitly preserve ambiguity, competing operationalizations, or unresolved boundaries when the evidence or current research state does not justify greater precision.

#### Governance Implication

Competing authoritative meanings for the same governed concept must be resolved through its Primary Authority or through an approved revision of the authority structure. Stewardship may be shared, but final semantic authority must remain resolvable.

---

### Principle 5 — A concept acquires Research Lab-wide semantic governance only when shared governance is justified.

#### Meaning

Use across multiple documents or domains does not by itself make a concept Research Lab-wide. A concept should remain within the narrowest legitimate governance scope unless no single domain can govern it without improperly constraining peer domains or unless a shared semantic contract is otherwise justified.

Governance scope may expand or contract as the concept and Research Lab evolve.

#### Governance Implication

Discoverability in a central registry must not be confused with Research Lab-wide semantic authority. Local, cross-domain, and Research Lab-wide governance are distinct questions.

---

### Principle 6 — The terminology system must remain ontology-ready without prematurely committing to an ontology.

#### Meaning

Terminology Governance should preserve stable identity, explicit relationships, provenance, semantic history, and resolvable authority in ways that can later support machine-readable concept schemes, ontologies, validation, and automation.

Ontology readiness does not justify prematurely fixing formal classes, relation semantics, identifier formats, graph models, inference rules, or implementation technologies before the research concepts are sufficiently mature.

#### Governance Implication

Current governance must be implementation-neutral. Future technical representations must implement the approved semantics rather than become the authority that silently determines them.

## 4. Governance Model

### 4.1 Concept Candidate

A Concept Candidate is a proposed or exploratory concept whose meaning is still under development or does not yet require formal semantic governance.

Candidate status permits research exploration without forcing every temporary term into a formal approval process.

### 4.2 Governed Concept

A Governed Concept is a concept admitted to formal terminology governance because stable and accountable meaning has become materially consequential to Research Lab work.

Governance should be proportional to semantic consequence. A temporary working term may require little or no formal governance, while a cross-domain normative concept may require stronger controls.

### 4.3 Concept Identity

Concept Identity is the continuity by which the Research Lab recognizes a concept as the same semantic object across labels, files, representations, and revision history.

Concept Identity is not determined by a label or file path alone.

### 4.4 Designation / Label

A Designation or Label is a lexical representation of a concept, including preferred names, abbreviations, alternate terms, translations, or presentation labels.

A change in designation does not automatically constitute a change in concept identity.

### 4.5 Primary Authority

The Primary Authority is the designated governance assignment that holds final normative authority over a governed concept’s meaning.

Primary Authority answers the question:

> Where must the Research Lab resolve the authoritative meaning of this concept when competing interpretations arise?

### 4.6 Authority Source and Canonical Resolution Point

An Authority Source is a normative source through which a Primary Authority expresses authoritative meaning.

A Primary Authority may rely on more than one Authority Source when necessary. However, the Research Lab must retain a canonical resolution point that makes the currently effective authoritative meaning resolvable without requiring readers or systems to guess among competing sources.

A document, section, record, or future machine-readable representation may function as an Authority Source only when explicitly designated as such.

### 4.7 Stewardship

Stewardship identifies responsibility for maintaining an authority, reviewing changes, and preserving continuity.

Stewardship does not itself constitute semantic authority. A change in steward does not automatically change a concept’s meaning or Primary Authority.

### 4.8 Governance Scope

Governance Scope identifies the domains for which a concept carries normative semantic authority.

Terms such as local, shared, cross-domain, or Research Lab-wide may be used descriptively, but v1 does not prescribe a fixed enumeration or schema for governance scope.

### 4.9 Effective Semantic State

The Effective Semantic State identifies the meaning of a governed concept that is currently in force for a defined scope and period.

Repository presence, document approval, and effective semantic state are distinct. A draft or partially applied revision must not silently become authoritative merely because it exists in the repository.

### 4.10 Research Lab Terminology Registry

A future Research Lab Terminology Registry may provide discovery and resolution for governed concepts, including identity, labels, Primary Authority, governance scope, semantic state, and history.

Registry inclusion does not imply Research Lab-wide semantic governance, and the registry does not automatically become the Primary Authority for the concepts it records.

### 4.11 Terminological Relationship and Mapping

A Terminological Relationship expresses a semantic relation among concepts, such as broader, narrower, related, equivalent, or another explicitly governed relation.

An external mapping expresses a governed semantic assertion between a Stock_vis concept and a concept from an external vocabulary or scheme.

Terminological relationships are distinct from empirical, causal, factual, or predictive Research Claims about reality.

## 5. Authority Assignment

Authority assignment is a semantic judgment rather than a file-placement rule.

### 5.1 Confirm Concept Identity and Necessary Semantic Scope

Before assigning authority, determine whether the proposed item is actually one concept and whether its semantic scope is broader than necessary.

A need for a narrow concept must not be used to create an unnecessarily broad generic concept merely so that an authority can be assigned.

### 5.2 Identify Semantic Jurisdiction

Semantic Jurisdiction asks which knowledge domain has legitimate responsibility for defining the concept’s meaning.

Historical origin, current file location, and frequency of use do not by themselves determine jurisdiction.

### 5.3 Choose the Narrowest Legitimate Authority

A concept’s Primary Authority should reside in the narrowest knowledge domain that can legitimately define and maintain its authoritative meaning without exceeding that domain’s semantic jurisdiction.

“Narrowest” does not mean the lowest document in the hierarchy. It means the least unnecessarily broad authority that can legitimately govern the concept as a whole.

### 5.4 Preserve Upstream Consistency

A lower-level authority may define concepts within its jurisdiction but must remain consistent with constraints established by higher-level authorities.

An upstream document does not automatically own every downstream concept, but a downstream authority may not silently redefine an upstream meaning.

### 5.5 Elevate Governance Only When Necessary

When no single domain can govern a concept without improperly constraining peer domains, governance may be elevated to an appropriate shared level.

Shared use alone is insufficient justification for shared governance.

### 5.6 Classification and Use Do Not Confer Full Meaning Authority

Authority over the use, classification, measurement, or operationalization of a concept within one framework does not automatically confer authority over the concept’s entire meaning.

For example, a methodology may classify a concept within its framework without thereby acquiring authority over every meaning of that concept across the Research Lab.

### 5.7 Definition, Operationalization, Measurement, and Implementation Are Distinct

A concept’s authoritative meaning must be distinguished from how a particular model, method, evaluation, or system operationalizes, measures, detects, computes, or implements that concept.

Different operationalizations do not automatically imply different concepts. Conversely, an operationalization that materially changes semantic scope may require a distinct concept or explicit semantic review.

## 6. Governance Rules

### 6.1 Governance Admission and Boundary

A concept should trigger formal governance review when its meaning becomes materially consequential to one or more of the following:

- an authoritative or normative Research Lab document;
- repeated cross-domain communication or reuse;
- evaluation or validation criteria;
- persistent model, automation, or software dependencies;
- repeated ambiguity, semantic conflict, or duplicate creation; or
- durable references that must remain interpretable over time.

These conditions require governance review; they do not automatically require admission. Review may conclude that a concept should remain a candidate, be merged with an existing concept, be split, remain local, or enter formal governance.

Before admission, the Research Lab should consider whether an existing governed concept already covers the intended meaning.

Terminology Governance governs concepts and their designations. It does not automatically govern every real-world instance, entity record, observation, event, research result, Research Claim, model output, or knowledge record that uses those concepts.

### 6.2 Normative Source, Restatement, and Effective State

Authoritative meaning must be resolvable through the Primary Authority and its designated Authority Source or Sources.

Copies, explanatory restatements, translations, summaries, AI-generated paraphrases, product labels, generated websites, or cached representations are non-normative by default unless explicitly designated as authoritative through approved governance.

A non-normative restatement must not silently expand, narrow, or redefine the authoritative concept.

If multiple language representations or multiple sources are designated as authoritative, conflict-resolution rules must also be explicit.

Repository presence does not by itself establish approval or effect. Draft, Approved, and Effective are distinct states.

Material semantic revisions that require coordinated changes across multiple artifacts must become effective as an internally coherent revision set. Partial updates must not silently create a new authoritative semantic state.

### 6.3 Semantic Change and Lifecycle

Semantic lifecycle decisions must distinguish representational change from material change in meaning.

Changes such as label replacement, file relocation, formatting, translation improvement, or clarification may preserve identity when semantic scope remains materially unchanged.

Material changes may require explicit revision, a new concept identity, split, merge, supersession, deprecation, or another lifecycle action depending on the nature of the change.

The Research Lab must preserve semantic history when concepts are split, merged, deprecated, superseded, or reactivated.

An inactive identifier must not be repurposed for a different semantic identity. Reactivation may be permitted when the same semantic identity was inactivated in error or when an approved review establishes genuine continuity.

Governance scope may expand or contract without automatically changing concept identity, provided the concept’s meaning remains materially continuous.

Rollback must be recorded as a new revision event rather than by erasing the historical period during which the reverted semantic state was effective.

### 6.4 Terminological Relationship and Mapping Governance

Terminological relationships that materially affect concept meaning must be treated as governed semantic assertions rather than decorative metadata.

Such relationships require appropriate provenance and authority. Cross-authority relationships must be governed in a manner appropriate to every authority whose concept meaning may be affected.

Terminological relationships must remain distinct from empirical or causal Research Claims about reality.

External mappings must not automatically transfer semantic authority from an external vocabulary to Stock_vis. Material mappings should preserve the identity and, where relevant, the semantic version or effective state of the external concept, together with mapping provenance.

Future technical implementations must distinguish, where relevant, between relationships explicitly asserted by an authority and relationships inferred by a formal system.

Formal validity or successful automated inference does not by itself establish that a semantic choice is scientifically correct or that a Research Claim is true.

### 6.5 Change Impact and Dependency Propagation

Before a material terminology change becomes effective, its likely downstream impact must be considered in proportion to semantic consequence.

Potential dependencies include:

- related concepts and terminological relationships;
- upstream and downstream documents;
- Research Methodology and Evaluation Methodology;
- Model Documents and model-specific operationalizations;
- research records and historical references;
- automation, code, schemas, identifiers, and caches;
- product or interface terminology; and
- future registries, ontologies, or knowledge representations.

Being affected does not automatically authorize modification. Each affected artifact remains subject to its own authority, scope, and approval rules.

### 6.6 Temporal Reproducibility and Authority Continuity

The Research Lab must be able to determine, when materially necessary, which semantic state of a governed concept was effective when a historical research artifact, evaluation, model, or decision used it.

Concept Identity, document version, and effective semantic state are distinct. A document version change does not imply that every concept in the document has changed meaning, and concept semantic change must not be hidden merely because a document version remains unchanged.

Historical semantic states and provenance must not be silently overwritten when a concept is revised or invalidated.

Primary Authority transfer, stewardship change, authority-source relocation, vacancy, or organizational change must preserve semantic continuity. If authority becomes unresolved, the ambiguity must be made explicit and resolved through governance rather than filled by an undocumented default.

## 7. Boundaries and Non-Decisions

Terminology Governance v1 establishes how semantic governance operates. It does not decide the substantive meaning or implementation of every concept that may later be governed.

The following are explicitly outside the decisions of v1 unless separately approved:

- the final list of Research Primitives;
- the generic definitions of State, Decision, Knowledge, or other unresolved concepts;
- the taxonomy of investment decisions;
- the final definition, admission criteria, or lifecycle vocabulary for Research Knowledge;
- the formal semantic relationship between Research Knowledge and Understanding;
- evaluation metrics, evidence scores, confidence scales, or validation thresholds;
- the concrete Research Lab Terminology Registry schema;
- Concept ID syntax or naming conventions;
- adoption of SKOS, RDF, OWL, SHACL, property graphs, or another ontology or graph technology;
- Knowledge Graph architecture;
- automated semantic validation rules;
- detailed stewardship organization, RACI structures, or escalation procedures;
- software architecture, data models, or product behavior; and
- any change to Scientific Philosophy, Evaluation Methodology, Model Documents, code, product behavior, or existing data not separately approved within its own scope.

Terminology Governance may govern these concepts or artifacts when they are later formalized, but v1 does not predetermine their substantive solutions.

## 8. Evolution

Terminology Governance is a Living Document.

Its purpose is to provide enough structure to preserve semantic integrity without creating unnecessary bureaucracy or prematurely fixing implementation details.

Governance should remain proportional to semantic consequence. Reversible local terminology should not receive the same governance burden as Research Lab-wide concepts on which methodology, evaluation, models, or automation materially depend.

This document should be split into separate authority, registry, lifecycle, or implementation documents only when operational complexity creates a meaningful independent governance responsibility. Document structure must follow demonstrated governance needs rather than anticipate them prematurely.

Future versions may refine procedures, lifecycle vocabularies, registry structures, machine-readable representations, validation, and automation while remaining accountable to the principles established here.

## Change Log

### Version 1.0 — 2026-08-12

- Established concept-first terminology governance.
- Established stable concept identity with explicit semantic change history.
- Established federated meaning authority and one Primary Authority per governed concept.
- Established authority assignment by semantic jurisdiction and the narrowest legitimate authority.
- Established selective Research Lab-wide governance.
- Established governance admission and boundary rules.
- Established normative-source, lifecycle, relationship, impact, reproducibility, and authority-continuity rules.
- Established ontology-ready, implementation-neutral evolution.
