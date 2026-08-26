# DL-DR-0001 — Human–AI Judgment Authority Boundary

**Status:** Approved  
**Decision ID:** DL-DR-0001  
**Approved:** 2026-08-27  
**Effective Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Authority:** CEO / Project Owner

## 1. Decision

Stock_vis adopts the following Human–AI judgment authority boundary:

> **AI may generate, structure, challenge, and continuously update a System Synthesis / Judgment Proposal, but it must not silently overwrite, attribute, or represent that proposal as the user's own investment judgment. User-owned judgment must remain semantically distinguishable. Material changes to user-owned judgment require meaningful user action or an explicitly delegated rule whose scope is visible, reversible, and traceable.**

Material adoption or revision must preserve sufficient **authorship provenance and update lineage** to determine what was proposed by the system, what was adopted or authored by the user, and what materially changed.

System–user disagreement may remain explicit. The product must not manufacture a single consensus state merely for interface simplicity.

## 2. Why This Decision Is Consequential

This boundary determines:

- who owns the user's investment judgment;
- how far AI authority may extend;
- how future surfaces interpret `Stock_vis view` versus `my view`;
- whether automation may silently become judgment or decision authority;
- how judgment history, personalization, comparison, alerts, and future agents treat authorship; and
- how the Design Lab operationalizes its working direction to strengthen user judgment without replacing it.

The decision therefore has long-term semantic and product-architecture reach and requires CEO authority.

## 3. Required Invariants

Future Design work must preserve the following unless this Decision Record is explicitly revised or superseded.

### 3.1 No Silent Attribution

System-generated synthesis must not become attributed to the user merely because it is displayed, prefilled, or automatically maintained.

### 3.2 No Silent Overwrite

A material user-owned judgment must not be silently changed by a system update.

### 3.3 Real User Control

User adoption, editing, rejection, qualification, or delegation must have a real causal effect on the user-owned judgment state rather than functioning as cosmetic control.

### 3.4 Authorship Provenance

Where material, the system must be able to distinguish system-authored, user-authored, adopted, modified, rejected, unresolved, or delegated changes sufficiently for the experience to remain interpretable.

This record does not prescribe a final authorship taxonomy.

### 3.5 Revision Lineage

Material judgment changes should preserve enough history to understand what changed, why, and through whose action or delegated authority.

### 3.6 Disagreement May Persist

The system may maintain a synthesis that differs from the user's judgment. The interface must not force agreement merely to create one clean state.

## 4. Delegation Boundary

The decision does **not** require the user to approve every evidence item, system observation, minor update, or routine monitoring result.

The system may autonomously maintain its own synthesis and perform routine research, monitoring, prioritization, and challenge.

A user-owned judgment may also change through an explicitly delegated rule when that delegation is:

- understandable in scope;
- reversible;
- traceable; and
- not a hidden transfer of general judgment authority to the system.

The exact threshold for what counts as a material judgment change remains a Design and validation question.

## 5. Non-Decisions

This decision intentionally does **not** lock the following implementation or interaction choices:

- whether System Synthesis and User Judgment are stored as two physical database objects;
- whether they appear as two separate screens, one combined surface, overlays, diffs, or another representation;
- the final names of `System Synthesis`, `Judgment Proposal`, `My View`, or equivalent concepts;
- the exact component taxonomy or visible component count;
- the exact adoption / edit / reject interaction;
- the visual treatment of authorship provenance;
- the precise thresholds for selective cognitive friction; or
- the final expert / novice disclosure strategy.

These remain delegated, reversible Design exploration unless they later become consequential.

## 6. Rationale and Alternatives

### Adopted Direction — Semantically Separated Co-authorship

This direction allows AI to perform most of the expensive synthesis and maintenance work while preventing the system from silently claiming ownership of the user's judgment.

It preserves disagreement, provenance, and revision history while allowing progressive and low-friction interaction design.

### Main Alternative — Single Shared AI-Maintained State with Provenance

A single shared state could be materially simpler and may produce lower interaction cost. Strong provenance and easy override might be sufficient to preserve user agency.

This alternative remains valid for prototype comparison **only if it preserves the approved semantic authority boundary**. A visually or physically single state is acceptable if system synthesis and user-owned judgment remain meaningfully distinguishable and no silent attribution or overwrite occurs.

### Rejected Default — AI-Owned Judgment

A model in which the system's maintained judgment automatically becomes the user's view is inconsistent with this approved authority boundary.

## 7. Evidence and Origin

This decision originates from Workstream 001, Exploration Batch 03 — Judgment Structure Granularity & Human–AI Authorship Boundary.

The exploration reviewed human–AI decision-support evidence indicating that editability and explanation can improve perceived control or acceptance without reliably improving independent judgment, and may create automation bias or an illusion of control. The Design Lab therefore distinguishes perceived control from causal control and treats authorship provenance as a core requirement.

See:

- `design_lab/02_workstreams/001_investment_judgment_experience/batch_03_authorship_granularity.md`
- `research_lab/01_methodology/knowledge_and_understanding_framework.md` for the upstream Research boundary between Understanding, Decision Context, Judgment, Decision, and Action.

## 8. Failure / Reversal Conditions

This decision should be explicitly reconsidered if strong real-user evidence shows that:

- users cannot meaningfully understand the distinction between system synthesis and user-owned judgment;
- maintaining semantic separation creates substantially more confusion than agency;
- a single shared representation with strong provenance demonstrably preserves independent user judgment and materially improves usability;
- system-generated structure causes harmful anchoring despite clear authorship separation; or
- the boundary prevents useful automation without materially improving user judgment quality or agency.

Any revision must preserve the Design Lab's broader purpose and Research–Design authority boundary, and should be treated as a consequential CEO-level decision.

## 9. Downstream Constraint

Future work on Judgment Experience, Thesis-like surfaces, monitoring, comparison, alerts, personalization, portfolio decision support, and AI agent behavior must treat this Decision Record as an approved constraint until revised or superseded.
