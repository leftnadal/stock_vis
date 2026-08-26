# Workstream 001 — Exploration Batch 04

## Judgment Experience Interaction Architecture

**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — Working interaction architecture under approved DL-DR-0001

## 1. Purpose

This batch translates the current judgment semantics into an interaction architecture without prematurely fixing product navigation, screen names, or a final Design System.

The core question is:

> **How should a user move between attention, understanding, system synthesis, user-owned judgment, revision, and decision context while preserving low interaction cost and the approved Human–AI authority boundary?**

This batch builds on:

- Batch 01 — maintained and revisable judgment as a structured state under decision context;
- Batch 02 — separation of judgment semantic model from judgment update process;
- Batch 03 — progressive disclosure and semantically separated human–AI co-authorship; and
- `DL-DR-0001 — Human–AI Judgment Authority Boundary`.

This is not yet a final product IA.

## 2. Approved Constraint

DL-DR-0001 requires that:

- system synthesis must not silently become the user's judgment;
- material user-owned judgment changes require meaningful user action or an explicit, reversible, traceable delegated rule;
- system–user disagreement may persist;
- authorship provenance and material update lineage must remain interpretable; and
- the physical interface does not need to expose two permanent side-by-side states if the semantic distinction is preserved.

This batch therefore optimizes interaction within that boundary rather than reopening it.

## 3. External Pattern Review

### 3.1 The competitive bar for monitoring and AI research is already high

Current financial research products increasingly connect monitoring directly to AI-supported research.

AlphaSense's 2026 product updates include automated monitoring, Workflow Agents for thesis checking / validation / refresh / postmortem, cited AI synthesis, always-current project reports, and agent-driven research workflows. Koyfin supports watchlist and portfolio alerts for price, valuation, technical, news, filings, transcripts, and related research navigation.

References:

- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/53942181071123-AlphaSense-Product-Updates-July-2026
- https://www.koyfin.com/features/alerts/

**Working implication:** `alert → research → AI summary` alone is not a sufficient distinctive interaction architecture for Stock_vis. A stronger opportunity is to connect changes to a maintained, traceable judgment state.

### 3.2 Mixed-initiative interaction is a better fit than fixed turn-taking

Recent human–AI work describes mixed-initiative collaboration as a model where human and AI can each take initiative when better positioned to advance the task. This supports a Stock_vis experience where the system autonomously monitors and proposes, while the user can interrogate, redirect, retain disagreement, or take control at consequential moments.

References:

- Natarajan (2025), *Adaptive Agents for Mixed-Initiative Human-AI Collaborations*: https://doi.org/10.1609/aaai.v39i28.35220
- Hu et al. (2025), *Human at the Center: A Framework for Human-Driven AI Development*: https://onlinelibrary.wiley.com/doi/10.1002/aaai.70043
- Holter, Moruzzi & El-Assady (2026), *Toward Agency in Human-AI Collaboration*: https://doi.org/10.1109/MCG.2025.3623892

**Working implication:** the interaction model should not force either `AI always leads` or `user always leads`. Initiative should depend on task and consequence.

### 3.3 Too many interruptive alerts can destroy attention value

Alert-fatigue research in clinical decision support is not direct financial-product evidence, but it provides a useful interaction warning: high-frequency or low-value interruptions can reduce response quality and user engagement even when individual alerts are technically relevant.

References:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC12310297/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13385993/

**Working implication:** Stock_vis should not treat every detected change as an interruptive judgment-review request. System initiative should be filtered by judgment impact, uncertainty, novelty, and consequence.

### 3.4 Structured deliberation can preserve open questions and disagreement

Recent deliberation interfaces use structured summaries, open questions, argument maps, or explicitly managed context rather than relying only on chronological chat. This supports the prior Design Lab direction that the maintained judgment structure should be a persistent object while conversation remains an access / manipulation mechanism.

References:

- Turkstra et al. (2026), *ARGSBASE: A Multi-Agent Interface for Structured Human–AI Deliberation*: https://aclanthology.org/2026.eacl-demo.39/
- Li et al. (2026), *Mixed-Initiative Context*: https://arxiv.org/abs/2604.07121

## 4. Competing Interaction Architectures

## 4.1 Feed-First / Event-First

The primary experience is a stream of news, alerts, earnings, price moves, and AI summaries. Users move from an event into deeper research and optionally update judgment.

**Strengths**
- excellent orientation and immediacy;
- low learning cost;
- naturally fits mobile / daily monitoring;
- familiar market-product pattern.

**Failure modes**
- episodic events remain the organizing object instead of judgment;
- salience can dominate materiality;
- difficult to preserve long-term judgment memory;
- users repeatedly reconstruct `what do I currently believe?`;
- differentiation from existing alert / research products is weak.

**Current judgment:** useful entry mechanism, rejected as the foundational architecture.

## 4.2 Judgment-Home / State-First

The primary experience is the maintained judgment snapshot. Users begin with current drivers, risks, uncertainty, conviction, and disagreement, then open evidence or changes.

**Strengths**
- excellent continuity and memory;
- makes judgment structure first-class;
- strong evidence-to-judgment traceability;
- works well for deliberate review.

**Failure modes**
- can make the system synthesis feel too authoritative or static;
- weak for quick daily orientation across many holdings;
- important new events may be buried inside state;
- a novice may not know where to start;
- users may anchor on the existing structure.

**Current judgment:** necessary persistent state, but too heavy as the only entry pattern.

## 4.3 Change-Review Queue / Diff-First

The system creates a queue of material changes. Each review shows what changed, which judgment components are affected, the system's proposed revision, evidence, and an accept / modify / reject / defer path.

**Strengths**
- directly operationalizes judgment updating;
- strong provenance and lineage;
- excellent for monitoring existing holdings;
- makes system proposal vs user adoption legible.

**Failure modes**
- inbox / review fatigue;
- weak for first-time company formation;
- can make every meaningful change feel like a required task;
- user may rubber-stamp repeated proposals;
- the maintained state becomes secondary to a queue.

**Current judgment:** strongest update mechanism, insufficient as the entire experience.

## 4.4 Permanent Side-by-Side Dual State

System Synthesis and User Judgment are always shown side-by-side or as parallel columns.

**Strengths**
- maximal authorship clarity;
- disagreement is obvious;
- comparison and diff are easy to understand.

**Failure modes**
- doubles visual and cognitive complexity;
- implies that two complete states are always required;
- overemphasizes human–AI conflict when most components may agree or the user may have no explicit view;
- weak for time-constrained monitoring;
- risks turning the semantic authority boundary into a UI burden.

**Current judgment:** useful as a local diff / disagreement interaction, rejected as the always-on primary architecture.

## 4.5 State-Centered, Change-Driven, Mixed-Initiative Hybrid

The system maintains a persistent judgment structure, but users commonly enter through material changes, recurring questions, or direct company exploration. System and user initiative can alternate. Human–AI divergence is surfaced when material rather than forcing two complete parallel views at all times.

**Current judgment:** strongest architecture.

**Recommendation Strength:** Strong.

## 5. Leading Working Architecture

The current recommendation can be summarized as:

> **Maintain state continuously, enter through meaningful change or user questions, review material implications in context, and surface human–AI authorship / disagreement only where it matters.**

A conceptual interaction architecture is:

```text
                    ┌─────────────────────┐
                    │  Orientation Layer  │
                    │ meaningful changes  │
                    │ questions / search  │
                    └─────────┬───────────┘
                              │
                 user or system initiative
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Judgment Snapshot   │
                    │ current maintained  │
                    │ state + recent diff │
                    └──────┬───────┬──────┘
                           │       │
                 inspect   │       │ review change
                           │       │
                           ▼       ▼
                ┌─────────────┐  ┌──────────────────┐
                │ Component   │  │ Change Review    │
                │ Detail      │  │ impact + proposal│
                └──────┬──────┘  └────────┬─────────┘
                       │                  │
                       ▼                  ▼
                ┌─────────────┐   adopt / modify /
                │ Evidence /  │   reject / retain /
                │ Provenance  │   defer / unresolved
                └──────┬──────┘          │
                       │                  ▼
                       └─────────► Updated User State
                                      + lineage

Decision Context is invoked as a separate overlay / mode when comparison,
portfolio constraints, horizon, opportunity cost, or action relevance matters.
```

The diagram expresses logical interaction roles, not final screens.

## 6. Interaction Roles

### 6.1 Orientation Layer — `What deserves attention?`

The system may take initiative here.

It should prioritize:

- judgment-bearing changes;
- important unresolved evidence conflicts;
- applicability / regime changes;
- material changes in uncertainty;
- user-requested monitoring targets; and
- decision-context changes when relevant.

Raw event volume is not the objective.

A price move, filing, or headline may be a trigger without being a judgment change.

**Interaction principle candidate:** `surface reasons to inspect, not conclusions to obey.`

### 6.2 Judgment Snapshot — `Where do things stand now?`

This is the persistent memory of the current investment view.

Default exposure should remain compact and progressive. It may show:

- the most material current judgment components;
- unresolved or weak areas;
- material recent changes;
- local conviction / uncertainty only where useful;
- whether a material component contains a system–user divergence; and
- whether the user has not formed an explicit view.

It should not imply that every system component has been adopted by the user.

### 6.3 Change Review — `What changed, what does it bear on, and should my judgment change?`

This is the core judgment-update interaction.

A review unit should be capable of expressing:

1. **Trigger** — what prompted review;
2. **Reference / Context** — compared with what;
3. **Research Input** — material Knowledge / Understanding / evidence state;
4. **Judgment Bearing** — which components are affected;
5. **System Assessment** — strengthen / weaken / qualify / unresolved / no material change, where applicable;
6. **System Proposal** — any proposed revision to system synthesis and, separately, a proposal to the user;
7. **User Response** — adopt / modify / reject / retain / defer / unresolved, when material;
8. **Lineage** — what materially changed and why.

The user should not need to approve a review when there is no material user-owned change.

### 6.4 Component Detail — `Why do we currently believe this?`

This exposes the judgment-bearing structure without requiring the user to inspect the entire semantic model.

It can provide:

- supporting / challenging inputs;
- unresolved alternatives;
- conditions / dependencies;
- local conviction / uncertainty;
- relevant recent update history;
- authorship / adoption status where material; and
- direct questioning or exploration entry points.

### 6.5 Evidence / Provenance / Update Trace — `Can I verify and reconstruct this?`

This deeper layer preserves traceability to authoritative Research outputs and material history.

Conversation can be used to ask follow-up questions, but chat should not become the only memory of why a judgment exists.

### 6.6 Decision Context — `What does this judgment mean for my current choice?`

Portfolio state, horizon, alternatives, concentration, opportunity cost, and constraints should enter when relevant to comparison or action.

Decision Context should not silently rewrite intrinsic company judgment.

This may later support comparison / rotation / portfolio workflows without requiring a separate company-reality ontology.

## 7. Mixed-Initiative Rules

The leading architecture uses consequence-proportional initiative.

### System initiative is appropriate for:

- monitoring and detecting candidate changes;
- organizing and prioritizing evidence;
- proposing judgment-bearing links;
- surfacing unresolved conflict or uncertainty;
- updating System Synthesis;
- suggesting that the user review a material change.

### User initiative is primary for:

- creating or preserving a user-only judgment component;
- accepting ownership of a material judgment change;
- rejecting / modifying a system proposal;
- expressing decision context or personal constraints;
- preserving disagreement; and
- determining whether to proceed toward an actual investment decision.

### Initiative should be shared for:

- clarification;
- exploration of alternative explanations;
- conviction recalibration;
- comparison;
- identifying what additional evidence would change the judgment.

## 8. Formation vs Update

The architecture should support both without creating two foundational models.

### New / unfamiliar company — Formation path

```text
Question / Discovery
→ System Synthesis of current structure
→ material drivers / risks / uncertainties
→ evidence exploration
→ user may adopt, modify, reject, or leave components unowned
→ partial User Judgment State emerges over time
```

The user does not need a prior thesis to use the system.

### Existing holding — Update path

```text
Monitoring trigger
→ Judgment-bearing change detected
→ Change Review
→ current component + evidence + proposed impact
→ user involvement only when material to user-owned judgment
→ updated state + lineage
```

Formation and update share the same semantic model but different entry paths.

## 9. Scenario Stress Test

### 9.1 Morning review across many holdings

A feed-first system may surface dozens of alerts. The hybrid instead prioritizes only candidate changes with meaningful judgment impact or unresolved risk, while preserving access to the raw event stream.

**Result:** hybrid survives; alert prioritization becomes a critical later evaluation problem.

### 9.2 Sharp price decline with no new fundamental evidence

The price move can trigger orientation. The system can explicitly state that a large market move occurred while no corresponding material Research update has yet been identified.

The user may investigate without being told that the thesis weakened.

**Result:** survives and preserves magnitude ≠ judgment impact.

### 9.3 Mixed earnings

Several judgment components may move in different directions. The Change Review can show affected components and proposed local revisions rather than forcing one earnings verdict.

**Result:** survives better than feed-first or scalar-summary models.

### 9.4 System and user materially disagree

The Judgment Snapshot can mark divergence only on affected components. A local diff / compare interaction can expand when needed. There is no requirement to display two complete permanent columns.

**Result:** preserves DL-DR-0001 with lower cognitive cost than permanent dual-state UI.

### 9.5 User has no explicit judgment

System Synthesis can exist while User Judgment remains absent or partial. The interface should not manufacture a user view merely to fill the structure.

**Result:** survives and avoids false attribution.

### 9.6 User repeatedly ignores review proposals

The system should not escalate every pending review into more notifications. It may keep System Synthesis current and summarize deferred / unreviewed material divergence at appropriate review moments.

**Result:** survives conceptually; notification / review-burden calibration requires validation.

### 9.7 New opportunity compared with a current holding

Each asset can reuse its maintained judgment structure. Decision Context introduces portfolio / opportunity-cost comparison without mutating the underlying company judgment.

**Result:** survives; comparison interaction remains a later workstream / batch.

## 10. Key Design Risks

### 10.1 Review Inbox Becomes Work

If too many system changes ask for user adoption, Stock_vis may recreate product-level micro-consensus.

Mitigation direction: require user action only for material user-owned judgment changes; summarize lower-consequence updates.

### 10.2 System Synthesis Anchors the User

Even with semantic separation, the system view may dominate attention.

Mitigation direction: selective cognitive friction, explicit uncertainty / disagreement, user-authored components, and experiments with ordering / reveal timing at consequential moments.

### 10.3 Persistent State Becomes Stale or Overgrown

A maintained judgment may accumulate obsolete components.

Mitigation direction: applicability checks, component lifecycle, periodic compression / retirement, and visible unresolved / stale state rather than silent deletion.

### 10.4 Materiality Filter Hides Important Novelty

A system can only prioritize against what it currently understands. Novel or weakly linked evidence may be wrongly suppressed.

Mitigation direction: preserve a secondary discovery path for unusual / unexplained changes and expose why prioritization occurred.

### 10.5 Conversation Replaces Structure

Chat is flexible but can fragment memory and provenance.

Mitigation direction: conversation should manipulate / inspect persistent structured objects rather than become the sole state store.

## 11. Batch Consensus

### Recommended Working Interaction Architecture

Adopt the following as the leading Working direction for prototype exploration:

> **State-centered, change-driven, mixed-initiative judgment experience with progressive disclosure.**

The architecture should:

1. maintain a persistent judgment state;
2. use meaningful change and user questions as common entry points;
3. treat Change Review as the core update interaction rather than a raw alert or mandatory approval queue;
4. preserve compact Judgment Snapshot access at all times;
5. expose deeper evidence / provenance / update history on demand;
6. surface human–AI divergence locally when material rather than through permanent duplicated states;
7. invoke Decision Context as a distinct comparison / action layer; and
8. support formation and update through different entry paths over the same semantic model.

**Recommendation Strength:** Strong.

## 12. Main Alternative

### Judgment-Home with Integrated Change Diff

A simpler alternative is to make the Judgment Snapshot the dominant company experience and integrate all recent changes directly into that state without a separate Change Review mode.

**Why it remains credible**
- fewer interaction concepts;
- potentially easier product navigation;
- avoids review-queue framing;
- could still preserve provenance and local diffs.

**Why it is currently second-best**
- weaker attention handling across many holdings;
- harder to distinguish `new signal requiring review` from `existing state`;
- may bury important updates or make the state visually noisy.

Prototype comparison should keep this alternative alive.

## 13. Failure / Reversal Conditions

The leading architecture should be revised if prototype / user testing shows that:

- users cannot understand the difference between Judgment Snapshot and Change Review;
- change-driven entry causes task / inbox fatigue;
- users overwhelmingly prefer direct state editing without an explicit review interaction;
- system-first change presentation produces harmful anchoring despite the approved authority boundary;
- maintaining persistent structured judgment creates more work than decision value;
- Decision Context cannot remain meaningfully separate from company judgment; or
- a simpler Judgment-Home architecture produces equal or better judgment quality with materially lower interaction cost.

## 14. Deferred / AI-Owned

The following remain reversible exploration details:

- final naming of Orientation, Judgment Snapshot, Change Review, Component Detail, and System Synthesis;
- screen count or navigation placement;
- mobile vs desktop arrangement;
- exact visual language for divergence, uncertainty, authorship, and material change;
- exact review actions and microcopy;
- notification cadence / bundling;
- component count and hierarchy;
- whether Change Review is a page, drawer, card, timeline item, or inline diff; and
- conversation placement.

## 15. CEO Critical Decision

**None in this batch.**

The interaction architecture is a reversible Tier 2 working direction under the already approved Human–AI judgment authority boundary. It should be prototyped and tested before any major product IA is locked.

## 16. Next Recommended Step

Move from abstract architecture to **low-fidelity interaction prototypes / wireflows** for a small set of stress scenarios:

1. held stock after a sharp price decline with no confirmed thesis change;
2. mixed earnings that strengthens and weakens different judgment components;
3. material system–user disagreement;
4. first-time company exploration / judgment formation; and
5. morning monitoring across a portfolio / watchlist.

The prototypes should compare at least:

- the leading state-centered + change-driven hybrid; and
- the simpler Judgment-Home + integrated diff alternative.

The goal is not visual polish. The goal is to test comprehension, attention cost, authorship clarity, review burden, and whether users can reconstruct why their judgment changed.
