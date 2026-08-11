# DR-0002: Adopt the Stock_vis Research Lab Terminology Governance v1

**Record ID:** DR-0002  
**Status:** Approved  
**Decision Type:** Research Governance / Terminology Governance  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-12  
**Approval:** Approved by Project Owner on 2026-08-12  
**Effective Date:** 2026-08-12  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Document:** [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)

## 1. Context

The Stock_vis Research Lab uses concepts across Foundation, Methodology, Evaluation, Model Documents, Decision Records, and future research systems. As those documents evolve, semantic consistency cannot be preserved by standardizing words alone.

Several structural risks were identified:

- the same word may refer to different concepts in different domains;
- the same concept may be expressed through different labels, translations, or files;
- copied definitions, summaries, translations, and AI-generated restatements may drift from their authoritative source;
- multiple documents may appear to define the same concept without a clear resolution rule;
- file location, historical origin, or usage frequency may be mistaken for semantic authority;
- concept identity may be lost during renaming, relocation, split, merge, deprecation, or revision;
- semantic relationships may be changed without clear authority or provenance;
- external vocabularies may introduce mapping assumptions that silently alter Stock_vis meaning;
- historical research may become irreproducible if current definitions overwrite the meanings that were effective when the research was conducted;
- terminology changes may propagate inconsistently into methodology, evaluation, models, automation, code, or product artifacts; and
- premature adoption of an ontology or graph schema may cause implementation structure to determine research meaning rather than represent it.

DR-0001 had already identified shared terminology as a future requirement for preventing concept drift across Research Lab documents. The subsequent terminology-governance discussion therefore focused on a broader question than glossary construction:

> **How should the Research Lab preserve concept identity and authoritative meaning across domains, documents, time, and future machine-readable systems without centralizing all meaning or constraining legitimate research evolution?**

## 2. Decision

The Stock_vis Research Lab adopts **Terminology Governance v1.0** as the normative governance framework for Research Lab concepts.

The decision adopts a federated concept-governance architecture with the following commitments.

### 2.1 Concept-First Governance

Terminology governance applies to concepts rather than words alone.

Lexical identity does not determine conceptual identity. The same concept may have multiple designations, and the same designation may refer to different concepts where their meanings differ.

### 2.2 Stable and Traceable Concept Identity

Concept identity must remain stable across representational change when semantic identity remains materially continuous.

Material changes in meaning must not be hidden through unchanged labels, identifiers, or file locations. Split, merge, supersession, deprecation, reactivation, and other lifecycle events must preserve semantic history where materially necessary.

### 2.3 Federated Meaning Authority

Meaning authority is federated across the Research Lab rather than centralized in one universal glossary.

A governed concept is assigned to the knowledge domain with legitimate semantic responsibility for that concept, subject to higher-level constraints.

### 2.4 One Resolvable Primary Authority per Governed Concept

Every governed concept must have one designated Primary Authority for its authoritative meaning.

Primary Authority is a governance assignment, not a person or file. It is expressed through designated Authority Sources and maintained through stewardship.

The requirement for one Primary Authority does not require false precision. An authority may explicitly preserve ambiguity, competing operationalizations, or unresolved semantic boundaries when current research does not justify a more precise meaning.

### 2.5 Selective Shared Governance

Cross-domain use does not automatically create Research Lab-wide governance.

A concept should remain under the narrowest legitimate authority unless shared governance is justified because no single domain can govern the concept without improperly constraining peer domains or because a shared semantic contract is otherwise necessary.

### 2.6 Ontology-Ready, Implementation-Neutral Evolution

The terminology system should preserve stable identity, explicit relationships, provenance, history, and resolvable authority so that future machine-readable representations remain possible.

No ontology language, graph architecture, identifier schema, inference system, or validation technology is adopted by this decision.

### 2.7 Governance Rules

Terminology Governance v1 establishes operational governance requirements in six areas:

1. governance admission and boundary;
2. normative source, restatement, and effective state;
3. semantic change and lifecycle;
4. terminological relationship and mapping governance;
5. change impact and dependency propagation; and
6. temporal reproducibility and authority continuity.

These rules are maintained in the Related Living Document rather than duplicated here as a second normative source.

## 3. Alternatives Considered

### 3.1 Centralized Global Glossary

A single central glossary could define all shared terms for the Research Lab.

This approach would simplify discovery and apparent standardization, but it was not selected because it would concentrate semantic authority outside the domains that legitimately understand and maintain many concepts. It would also encourage the glossary to become a competing semantic source that silently redefines Foundation, Methodology, Evaluation, or Model concepts.

### 3.2 Fully Local Terminology

Each document or model could define its own terms independently.

This approach would maximize local autonomy and reduce governance overhead, but it was not selected because it would permit uncontrolled semantic drift, make cross-domain reasoning unreliable, and leave humans and automated systems without a principled way to resolve competing meanings.

### 3.3 Document-Centric Authority

A concept’s authority could be identified with the document in which it is defined.

This approach was not selected because documents may be renamed, moved, split, merged, or reorganized without changing the semantic authority of a concept. Treating a physical document as the authority would confuse semantic continuity with document structure.

The adopted model therefore distinguishes Primary Authority from Authority Source.

### 3.4 Role-Centric Authority

A concept’s authority could be assigned directly to an individual steward, owner, researcher, or agent.

This approach was not selected because personnel or agent assignments can change without changing the semantic identity or authority structure of a concept.

The adopted model therefore distinguishes stewardship from semantic authority.

### 3.5 Usage-Based Authority

The domain that uses a concept most frequently could be considered its authority.

This approach was not selected because frequency of use does not establish legitimate semantic responsibility. A widely reused concept may still have a clear authority elsewhere.

### 3.6 Hierarchy-Based Authority

The highest-level document that mentions a concept could automatically govern it.

This approach was not selected because it would cause Foundation or Scientific Philosophy to absorb lower-level operational concepts merely because they are referenced at a higher level. Higher-level documents provide constraints, but they do not automatically own every downstream concept.

### 3.7 Ontology-First Governance

The Research Lab could immediately adopt SKOS, RDF, OWL, SHACL, a property graph, or another formal representation and use that implementation as the organizing structure for terminology.

This approach was not selected because current concept boundaries, relationships, and governance responsibilities are still evolving. Premature formalization could cause technical representation to determine research meaning rather than represent approved meaning.

The Research Lab instead adopts an ontology-ready but implementation-neutral governance architecture.

### 3.8 One Global Definition for Every Shared Word

The Research Lab could require every repeated word to have one universal definition.

This approach was not selected because lexical sameness does not guarantee conceptual sameness. Different domains may legitimately use the same word for different concepts, and one concept may legitimately have different labels.

## 4. Rationale

The adopted structure balances two requirements that would otherwise conflict.

The Research Lab requires enough semantic coherence for research actors, documents, evaluation, models, and future automation to refer to concepts reliably. At the same time, individual domains require legitimate semantic autonomy to define concepts within their own responsibility without every local change becoming a central governance event.

A fully centralized model would protect consistency at the cost of semantic overreach. A fully local model would protect autonomy at the cost of coherence.

Federated concept governance resolves this tension by combining:

```text
stable concept identity
+
legitimate local semantic responsibility
+
one resolvable Primary Authority
+
upstream consistency
+
selective shared governance
+
explicit semantic history
```

The decision also separates several dimensions that must not be conflated:

```text
concept meaning
≠ label
≠ file location
≠ steward
≠ operationalization
≠ implementation
≠ empirical Research Claim
```

This separation allows terminology governance to remain a semantic-governance layer rather than expanding into control over every entity, research claim, model output, knowledge record, or software artifact.

The architecture is intentionally implementation-neutral. Stable identity, explicit authority, provenance, history, and governed relationships provide a foundation on which later registries, vocabularies, ontologies, validation, or automation may be built without requiring those future technologies to be chosen now.

## 5. Consequences

### 5.1 Binding Implications

Adoption of Terminology Governance v1 establishes the following requirements:

- terminology governance must begin with concept identity rather than lexical identity;
- governed concepts must have one resolvable Primary Authority;
- Primary Authority must be distinguished from Authority Source and stewardship;
- authority assignment must follow semantic jurisdiction rather than origin, file location, hierarchy alone, or frequency of use;
- use or classification of a concept within a framework does not automatically confer authority over the concept’s entire meaning;
- definition must be distinguished from operationalization, measurement, and implementation;
- material semantic dependencies must trigger governance review, while governance burden remains proportional to semantic consequence;
- copied definitions, translations, summaries, generated text, and other restatements are non-normative by default unless explicitly approved as authoritative;
- Draft, Approved, and Effective semantic states must not be treated as identical merely because content exists in the repository;
- material semantic changes must preserve relevant history and may not silently repurpose an identifier for a different meaning;
- terminological relationships and external mappings that affect meaning require appropriate governance and provenance;
- terminological relationships must remain distinguishable from empirical or causal Research Claims;
- material terminology changes require downstream impact review proportional to consequence;
- historical artifacts must remain interpretable against the semantic states they materially depended on; and
- future ontology or automation implementations must represent approved semantics rather than become an unapproved semantic authority.

### 5.2 Expected Benefits

The decision is expected to provide:

- clearer resolution of cross-document and cross-domain semantic conflicts;
- reduced concept drift from copying, translation, summarization, or AI-mediated reuse;
- stable concept identity across document reorganization and terminology changes;
- preserved historical reproducibility for research and model interpretation;
- clearer separation between semantic authority, stewardship, and physical source location;
- stronger foundations for human and non-human research systems to share concepts consistently;
- controlled local autonomy without unnecessary global governance;
- safer future integration with external vocabularies and formal knowledge representations; and
- a foundation for future terminology registries, validation, and automation.

### 5.3 Costs and Limitations

The decision creates additional governance costs and does not solve every semantic problem automatically:

- authority assignment may require judgment and discussion;
- distinguishing clarification from material semantic change may be difficult;
- cross-authority relationships may require additional coordination;
- impact analysis creates documentation and review overhead;
- preserving historical semantic states increases record-keeping requirements;
- governance can become bureaucratic if not kept proportional to semantic consequence;
- one Primary Authority does not guarantee that the authoritative concept is scientifically correct;
- terminology governance cannot determine the truth of empirical Research Claims;
- formal validation or ontology consistency cannot substitute for evidence and research judgment; and
- detailed registry, lifecycle, identifier, automation, and escalation procedures remain future work.

Terminology Governance preserves the integrity and accountability of meaning. It does not make the governed meaning immune to revision by better evidence or research.

## 6. Scope and Non-Decisions

### 6.1 In Scope

DR-0002 decides:

- adoption of Terminology Governance v1.0;
- concept-first terminology governance;
- stable and traceable concept identity;
- federated semantic authority;
- one designated Primary Authority per governed concept;
- authority assignment through semantic jurisdiction and the narrowest legitimate authority;
- upstream consistency and selective shared governance;
- governance review for materially consequential concepts;
- distinction among concept, designation, instance, Research Claim, operationalization, and implementation;
- normative-source and effective-state governance;
- semantic lifecycle and historical continuity;
- terminological relationship and mapping governance;
- change-impact and dependency review;
- temporal reproducibility and authority continuity; and
- ontology-ready, implementation-neutral evolution.

### 6.2 Out of Scope

DR-0002 does not decide:

- the final list of Research Primitives;
- the final generic definitions of State, Decision, Knowledge, or other unresolved concepts;
- the investment-decision taxonomy;
- the final definition, admission criteria, or status vocabulary for Research Knowledge;
- the formal semantic relationship between Research Knowledge and Understanding;
- evaluation metrics, evidence-scoring methods, confidence scales, or thresholds;
- a concrete Terminology Registry schema;
- Concept ID syntax or naming conventions;
- adoption of SKOS, RDF, OWL, SHACL, property graphs, or another ontology or graph technology;
- Knowledge Graph architecture;
- automated semantic validation rules;
- detailed stewardship organization, RACI structures, or escalation procedures;
- definition-authoring templates or formal definition logic;
- specific code, data, product, model, or user-interface changes; or
- changes to the Scientific Philosophy or other existing authoritative documents not separately approved within their own scope.

Concepts discussed during governance stress testing, including Research Knowledge, Understanding, State, Decision, and possible future knowledge-graph structures, remain inputs to later research unless separately approved.

## 7. Affected Documents

| Document or Area | Effect |
|---|---|
| `research_lab/01_methodology/terminology_governance.md` | Becomes the Living Document containing the currently effective Terminology Governance v1.0. |
| `research_lab/01_methodology/README.md` | Receives a navigation link to the Terminology Governance Living Document. |
| `research_lab/04_decision_records/DR-0002-adopt-terminology-governance-v1.md` | Preserves the historical decision to adopt Terminology Governance v1, including context, alternatives, rationale, consequences, and non-decisions. |
| `research_lab/04_decision_records/README.md` | Receives the DR-0002 record entry. |
| Scientific Philosophy | Remains an upstream normative authority where it already defines concepts; no semantic change is authorized by DR-0002. |
| Future Research Methodology and Evaluation Methodology | Must apply this governance when concepts within their scope become formally governed. |
| Model Documents | May define and govern model-specific concepts within legitimate jurisdiction while remaining consistent with upstream authorities. |
| Future Research Lab Terminology Registry | Must implement rather than replace the semantic authority structure established by Terminology Governance. |
| Future ontology, knowledge-graph, validation, and automation systems | Must remain subordinate to approved semantic authority unless a later approved decision changes that relationship. |
| Code, product, data, and current implementations | No direct modification is authorized by this decision. |

Being affected does not automatically authorize modification. Any required change to an existing artifact remains subject to that artifact’s own authority, scope, and approval process.

## 8. Approval

**Decision:** Adopt the Stock_vis Research Lab Terminology Governance v1.0  
**Decision Owner:** Stock_vis Research Lab  
**Approver:** Project Owner  
**Approval Status:** Approved  
**Decision Date:** 2026-08-12  
**Effective Date:** 2026-08-12

> **The Project Owner approves the adoption of the Stock_vis Research Lab Terminology Governance v1.0 as defined in the related Living Document.**
