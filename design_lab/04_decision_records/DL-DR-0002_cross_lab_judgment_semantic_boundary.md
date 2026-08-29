# DL-DR-0002 — Cross-Lab Judgment Semantic Boundary

**Status:** Approved  
**Decision ID:** DL-DR-0002  
**Approved:** 2026-08-27  
**Effective Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Authority:** CEO / Project Owner

## 1. Decision

Stock_vis adopts one cross-Lab semantic boundary for **Judgment** consistent with the Approved Research Lab Knowledge and Understanding Framework:

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

Design Lab must not use `Judgment` as the authoritative name for a persistent company-level state that exists before Decision Context is applied.

The persistent Design-side object discovered in Workstream 001 remains legitimate and useful, but it is a **distinct Design concept candidate**. Its final designation is delegated; `Investment View`, `Company View`, `Thesis State`, or another label may be explored without changing this decision.

## 2. Why This Decision Is Consequential

`Judgment` sits directly on the Research ↔ Design ↔ Product boundary. Allowing Research and Design to use the same label for materially different concepts would create semantic drift across agents, documents, future ontology/schema work, APIs, interfaces, and downstream decision support.

This decision therefore aligns the product mental model with the current Research authority rather than creating a competing Design definition.

## 3. Required Invariants

### 3.1 Research Semantic Authority Is Preserved

For the cross-Lab concept `Judgment`, Research Lab remains the semantic authority for the relationship among Understanding, Decision Context, Judgment, Decision, and Action.

### 3.2 Persistent Company-Level State Is Distinct

A persistent user-owned or system-maintained view of a company may exist before a concrete Decision Context. It must not silently be treated as the cross-Lab Judgment object merely because it supports later Judgment.

### 3.3 Decision Context Precedes Judgment

Portfolio exposure, time horizon, alternatives, valuation, opportunity cost, constraints, switching costs, or other decision-specific conditions may combine with relevant Understanding and maintained views to support a Judgment.

They are not merely optional annotations added after Judgment has already been formed.

### 3.4 Representation Does Not Determine Semantics

The product may visually combine a maintained Investment View, System Synthesis, Decision Context, and Judgment in one surface if useful. A single screen or shared component does not collapse their semantic distinctions.

### 3.5 Historical Design Language Must Be Interpretable

Earlier Workstream 001 documents may contain `Judgment State`, `Judgment Workspace`, or `User Judgment` as Working language created before this alignment. These terms are historical exploration language, not authority to redefine Research `Judgment`.

Material downstream documents should use the aligned semantics. Older exploration artifacts need not be mechanically rewritten when their historical meaning remains clear, but authoritative or reusable Design knowledge must not preserve the ambiguity.

## 4. Relationship to DL-DR-0001

DL-DR-0001 — Human–AI Judgment Authority Boundary remains substantively in force.

Its approved invariant was about **authorship and authority**: system-generated synthesis must not silently become the user's own maintained view, and material user-owned changes require meaningful causal user control or explicit bounded delegation.

Where DL-DR-0001 uses `user-owned judgment` for a persistent state that exists before Decision Context, that phrase is now interpreted as the persistent **user-owned Investment View / equivalent Design concept**, not as a redefinition of the Research-governed Judgment object.

The Human–AI authorship boundary is unchanged.

## 5. Implications for Workstream 001

The Workstream 001 foundation should be semantically corrected from:

```text
Persistent Judgment Workspace
→ Decision Context
→ Decision
```

toward:

```text
Research Knowledge / Understanding
        ↓
System Synthesis
        ↕
Maintained User Investment View
        +
Decision Context
        ↓
Judgment
        ↓
Decision
        ↓
Action
```

The final label and exact representation of the persistent Design-side state remain Working.

## 6. Non-Decisions

This decision does not establish:

- the final name `Investment View`;
- a database schema or ontology class;
- whether System Synthesis and user-owned view are separate physical objects;
- the final Product IA or screen structure;
- investment-decision rules;
- how Judgment is numerically or qualitatively represented; or
- the authoritative Research methodology for predictive / comparative Judgment inputs.

## 7. Rationale and Main Alternative

### Adopted Direction — Shared Cross-Lab Meaning

Use the Research-approved semantic boundary and give the persistent Design-side state a distinct identity.

This minimizes long-term ambiguity while preserving the Design discovery that users benefit from a persistent, revisable company-level view.

### Main Alternative — Local Design Definition of Judgment

Design could define a local product concept called `Investment Judgment` that exists before Decision Context while Research keeps a different meaning.

Terminology Governance permits local concepts where legitimate, but this alternative was not selected because the semantic reach and repeated cross-Lab use of `Judgment` make the ambiguity unnecessarily costly.

## 8. Failure / Reversal Conditions

Reconsider this decision if:

- Research Lab formally revises the upstream Judgment boundary;
- later cross-Lab terminology governance establishes a materially better shared semantic architecture; or
- strong operational evidence shows that the separation creates more semantic failure than it prevents.

Any material revision requires explicit cross-Lab impact review and CEO-level consequential approval.

## 9. Related Authority

- `research_lab/01_methodology/knowledge_and_understanding_framework.md`
- `research_lab/01_methodology/terminology_governance.md`
- `research_lab/04_decision_records/DR-0006-separate-epistemic-authority-consequential-governance.md`
- `design_lab/04_decision_records/DL-DR-0001_human_ai_judgment_authority.md`
