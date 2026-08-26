# DR-0006: Separate Epistemic Authority from Consequential Governance

**Record ID:** DR-0006  
**Status:** Approved  
**Decision Type:** Research Governance / Epistemic Authority  
**Decision Owner:** Stock_vis Research Lab  
**Decision Date:** 2026-08-27  
**Approval:** Approved by Project Owner on 2026-08-27  
**Effective Date:** 2026-08-27  
**Supersedes:** None  
**Superseded By:** None  
**Related Living Documents:** [Research Methodology](../01_methodology/research_methodology.md), [Evaluation Methodology](../02_evaluation/evaluation_methodology.md)

## 1. Context

Research Methodology v1.0 and Evaluation Methodology v1.0 deliberately left exact actor-level Knowledge admission and escalation authority unresolved until actual Research Lab operation provided evidence about what governance was needed.

Operational Pilot 001 exposed the first concrete gap. The Research/Evaluation system could evaluate a Claim, determine that it was sufficiently warranted for admission, and distinguish strong facts from weaker causal interpretations. However, the framework had not yet specified whether the Project Owner / CEO should personally approve epistemic admission.

The Pilot also clarified that the Project Owner / CEO is not intended to function as a domain expert who independently verifies whether specialized factual or causal research conclusions are true. Requiring CEO truth approval would create a research bottleneck, misallocate CEO attention, and risk replacing scientific evaluation with authority-based judgment.

At the same time, sufficiently evaluated Knowledge and Understanding may have major consequences for Stock_vis strategy, research priorities, architecture, product direction, resource allocation, risk tolerance, or cross-lab dependencies. Those consequences do require accountable governance.

The Research Lab therefore needed an explicit separation between:

- **Epistemic Authority** — responsibility for determining what is currently sufficiently warranted; and
- **Consequential Governance Authority** — responsibility for deciding what Stock_vis should do about materially consequential research results.

## 2. Decision

The Stock_vis Research Lab adopts the following authority boundary.

### 2.1 Epistemic Authority Resides in the Research and Evaluation System

The Research/Evaluation system is responsible for determining whether a candidate Claim, Research Knowledge item, Understanding, Model-related result, or other epistemic object is sufficiently warranted for its stated scope and purpose.

The Project Owner / CEO is not the default epistemic truth reviewer and is not required to personally approve whether a specialized factual, causal, predictive, comparative, or other research conclusion is correct.

Epistemic consequence, expected reuse, uncertainty, novelty, disagreement, or downstream dependency may require stronger Evaluation, specialized review, additional challenge, replication, or other epistemic controls. These factors increase epistemic rigor; they do not automatically transfer truth adjudication to the CEO.

Exact agent-level admission mechanics, reviewer counts, voting rules, consensus algorithms, and escalation thresholds remain unresolved and will be specified only when operational evidence justifies greater precision.

### 2.2 The Project Owner / CEO Holds Consequential Governance Authority

The Project Owner / CEO decides what Stock_vis should do about sufficiently evaluated research results when they create material consequential choices.

Consequential governance includes, where material:

- strategic research direction and priority;
- substantial resource commitment;
- system-wide or cross-lab dependency;
- methodology or architecture change;
- product or decision-support direction;
- downstream use boundaries and risk tolerance;
- hard-to-reverse commitments; and
- value choices among multiple legitimate alternatives.

CEO escalation is therefore driven by the consequences of using or acting on research, not by a requirement that the CEO personally verify research truth.

### 2.3 Important Epistemic Results May Require Stronger Review Without CEO Admission

A foundational or highly reused Knowledge item may be epistemically important enough to require stronger internal challenge, independent review, or higher evaluation rigor.

Its importance does not by itself make it a CEO admission decision.

The distinction is:

```text
Epistemic importance
→ stronger Research / Evaluation rigor

Consequential importance
→ possible CEO governance decision
```

### 2.4 CEO Concern Creates Review Obligation, Not Epistemic Override

The Project Owner / CEO may identify a material concern and require Re-evaluation or Reconsideration of a Knowledge item, Understanding, Model, methodology, architecture, assumption, or consequential decision.

Such a request does not predetermine the epistemic result.

The Research/Evaluation system must reconsider the relevant object under the applicable methodology and may retain, strengthen, revise, restrict, supersede, reject, or otherwise update the prior state according to evidence and legitimate epistemic authority.

The Project Owner / CEO does not directly overwrite Research Knowledge or Understanding by decree.

### 2.5 The Same Boundary Applies to Understanding

Research/Evaluation determines which Understanding structures are currently sufficiently warranted and how uncertainty, alternatives, scope, and limitations should be represented.

The CEO decides whether and how a sufficiently evaluated Understanding should affect Stock_vis strategy, research priorities, architecture, product direction, resource allocation, or downstream use.

Where multiple warranted or partially compatible Understandings coexist, the Research Lab preserves their epistemic status. CEO governance may decide how Stock_vis prepares for or acts under those possibilities without redefining which Understanding is scientifically warranted.

### 2.6 Research Methodology v1.1 and Evaluation Methodology v1.1 Form a Coordinated Revision Set

This decision is operationalized through Research Methodology v1.1 and Evaluation Methodology v1.1.

The two revisions become effective together because the authority boundary spans both the research lifecycle and the evaluation/review interface.

Later revisions may evolve independently when dependency review confirms continued consistency with each other and with upstream authorities.

## 3. Alternatives Considered

### 3.1 CEO Approves Important Research Knowledge

Under this alternative, high-impact Knowledge or Understanding would require direct CEO epistemic approval.

This was not selected because importance of a research conclusion does not make the CEO the most qualified truth reviewer. It would also recreate micro-approval bottlenecks and blur scientific judgment with organizational authority.

### 3.2 Research/AI System Owns Both Epistemic and Consequential Decisions

Under this alternative, the Research/AI system would both determine what is warranted and decide strategic direction, resource allocation, product consequences, and other major organizational actions.

This was not selected because it would hide value-dependent and hard-to-reverse decisions inside the research system and remove accountable CEO governance from consequential choices.

### 3.3 No Explicit Separation

The Research Lab could leave authority implicit and resolve cases ad hoc.

This was not selected because the Pilot already demonstrated ambiguity around admission authority, and implicit governance would make future agent automation and escalation inconsistent.

## 4. Rationale

The adopted separation aligns authority with competence and responsibility.

Research and Evaluation are designed to test evidence, logic, scope, uncertainty, alternatives, and epistemic warrant. They should therefore determine what the Research Lab is currently justified in treating as Knowledge or Understanding.

The Project Owner / CEO is responsible for Stock_vis direction, resource allocation, major architecture, risk boundaries, and other consequential commitments. CEO attention should therefore concentrate on what materially changes because of research, rather than on personally re-performing specialist factual verification.

Allowing the CEO to initiate Re-evaluation or Reconsideration preserves meaningful challenge and organizational accountability without allowing authority to replace evidence.

## 5. Consequences

### 5.1 Binding Implications

This decision establishes that:

- the CEO is not the default epistemic admission authority;
- high epistemic consequence increases evaluation rigor rather than requiring CEO truth approval;
- Research/Evaluation owns warranted epistemic status under approved methodology;
- CEO escalation is based on consequential governance needs;
- CEO concerns may require Re-evaluation or Reconsideration;
- governance-initiated review does not predetermine epistemic outcome;
- Research Knowledge and Understanding cannot be directly overwritten by CEO decree; and
- exact agent-level admission and routing mechanics remain open for later operational design.

### 5.2 Expected Benefits

The decision is expected to:

- keep scientific evaluation grounded in evidence rather than organizational authority;
- reduce CEO bottlenecks as Research Lab output scales;
- focus CEO attention on strategic and hard-to-reverse consequences;
- preserve independent challenge of important research results;
- provide a clearer foundation for future sub-agent admission and escalation workflows; and
- keep consequential governance accountable without collapsing it into epistemic evaluation.

### 5.3 Required Follow-on Work

Later operational work should determine, based on additional Pilot evidence:

- the minimum internal admission workflow;
- when specialized or independent challenge is required;
- how disagreements among evaluators are resolved;
- exact CEO escalation drivers and routing;
- the format of CEO Decision Packets;
- record and provenance requirements for admission decisions; and
- how these rules are implemented in future agent orchestration and software permissions.

## 6. Non-Decisions

This decision does not establish:

- numerical admission thresholds;
- fixed epistemic consequence tiers;
- exact reviewer counts;
- mandatory independent review for every Knowledge item;
- agent voting or consensus rules;
- exact disagreement-resolution procedures;
- exact CEO escalation thresholds;
- software permission models;
- product decision rules; or
- investment decision rules.

## 7. Related Documents

- [Stock_vis Research Lab Scientific Philosophy](../00_foundation/scientific_philosophy.md)
- [Stock_vis Research Lab Terminology Governance](../01_methodology/terminology_governance.md)
- [Stock_vis Research Lab Knowledge and Understanding Framework](../01_methodology/knowledge_and_understanding_framework.md)
- [Stock_vis Research Lab Research Methodology](../01_methodology/research_methodology.md)
- [Stock_vis Research Lab Evaluation Methodology](../02_evaluation/evaluation_methodology.md)
- [DR-0004: Adopt the Stock_vis Research Lab Research Methodology v1](DR-0004-adopt-research-methodology-v1.md)
- [DR-0005: Adopt the Stock_vis Research Lab Evaluation Methodology v1](DR-0005-adopt-evaluation-methodology-v1.md)
