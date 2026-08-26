# Workstream 001 — Exploration Batch 03

## Judgment Structure Granularity & Human–AI Authorship Boundary

**Status:** Working  
**Date:** 2026-08-26  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Mixed — granularity is Tier 2 working architecture; human/AI authorship boundary contains a Tier 1 / CEO-critical question.

## 1. Purpose

This batch examines two related questions:

1. **Judgment Structure Granularity** — how much of the maintained judgment structure should be represented explicitly, and how much should be visible by default versus progressively disclosed?
2. **Human–AI Authorship Boundary** — which parts of a maintained judgment may be generated, proposed, edited, adopted, or owned by the system and by the user?

The goal is not to finalize screens or interaction details. The goal is to establish a working boundary that preserves user agency without forcing users to manually maintain a research ontology.

This batch builds on Batch 01 and Batch 02, especially the working model that investment judgment is a maintained and revisable state with internal structure, updated through an evidence-driven process under decision context.

## 2. Authority Boundary

The Research Lab remains authoritative for Research Knowledge, Understanding, Evidence, credibility, applicability, and related Research concepts.

This batch does not redefine the Research-side meaning of Judgment. It studies the downstream user experience and authorship boundary around a user-maintained investment judgment.

The Design Lab working philosophy remains relevant:

> Strengthen user judgment without replacing it.

Any product mechanism that silently turns system synthesis into the user's attributed judgment would therefore require especially strong scrutiny.

## 3. External Evidence — What Does Human Control Actually Achieve?

### 3.1 Editability and control can increase acceptance without guaranteeing better judgment

Multiple human–AI studies show that giving users control over AI recommendations can increase perceived autonomy, trust, understanding, or willingness to use the system. However, control does not automatically improve decision accuracy.

Relevant evidence reviewed:

- Fink, Newman & Haran (2024), *Let me decide: Increasing user autonomy increases recommendation acceptance* — greater choice/control autonomy increased recommendation acceptance.  
  https://www.sciencedirect.com/science/article/pii/S0747563224001122
- Sele & Chugunova (2024), *Putting a human in the loop: Increasing uptake, but decreasing accuracy of automated decision-making* — allowing users to monitor and adjust algorithmic advice increased uptake, but participants were less likely to correct the largest errors and final accuracy decreased in the experiment.  
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298037
- Westphal et al. (2023), *Decision control and explanations in human-AI collaboration* — decision control improved user perceptions and compliance, while explanations increased task complexity and could impair outcomes depending on the user.  
  https://www.sciencedirect.com/science/article/abs/pii/S0747563223000651

**Working implication:** an edit button is not a sufficient definition of agency. Agency requires that user actions actually change the maintained user state and that the distinction between system proposal and user-owned judgment remains legible.

### 3.2 Editable AI reasoning can create an illusion of control

A 2026 CHI study of editable displayed AI reasoning found higher perceived power, control, and satisfaction, but no accuracy improvement; read-only reasoning increased inappropriate reliance, while editability itself could create an illusion of control when edits did not causally affect the recommendation.

Reference:

- *Understanding the Affordances of Control in AI Reasoning for Human-AI Decision-Making* (CHI EA 2026).  
  https://doi.org/10.1145/3772363.3798555

**Working implication:** Stock_vis should distinguish **perceived control** from **causal control**. If a user edits, accepts, rejects, or qualifies a judgment component, that action should have a real, traceable effect on the user-owned judgment state rather than functioning as cosmetic interaction.

### 3.3 Explanations alone do not reliably preserve independent judgment

Prior work on automation bias and AI advice repeatedly shows that explanations may increase trust or advice-taking without reliably improving appropriate reliance.

Relevant evidence:

- Buçinca, Malaya & Gajos (2021), *To Trust or to Think* — cognitive forcing reduced AI overreliance more than simple explainable-AI approaches, but at a usability / subjective-preference cost.  
  https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca2021trust.shtml
- Vered et al. (2023), *The effects of explanations on automation bias* — explanations do not reliably eliminate automation bias.  
  https://www.sciencedirect.com/science/article/pii/S000437022300098X
- *Cognitive Forcing for Better Decision-Making: Reducing Overreliance on AI Systems Through Partial Explanations* (2025) — partial/full explanation designs can reduce overreliance, but effects depend on task and user characteristics.  
  https://doi.org/10.1145/3710946

**Working implication:** preserving user authorship requires more than showing why the AI thinks something. The system must preserve opportunities for the user to form, retain, reject, or revise judgment independently.

## 4. Granularity Evidence

### 4.1 Full structural exposure creates cognitive and information-load risks

Complex disclosure can increase error and overconfidence in users' ability to process information. Financial-decision research also shows that cognitive load created by task and interface design harms memory and decision quality.

References:

- Jin, Luca & Martin (2021/2022), *Complex Disclosure*.  
  https://pubsonline.informs.org/doi/10.1287/mnsc.2021.4037
- *Affective responses to financial data and multimedia: the effects of information load and cognitive load*.  
  https://www.sciencedirect.com/science/article/abs/pii/S1467089504000053

### 4.2 Meaningful disaggregation can improve understanding

Financial-reporting experiments with nonprofessional investors show that disaggregating a complex item into meaningful components can improve acquisition and understanding of how the components relate to economic events and judgments.

Reference:

- *The effects of the method used to present a complex item on the face of a financial statement on nonprofessional investors' judgments*.  
  https://www.sciencedirect.com/science/article/pii/S0882611016300116

**Working implication:** the answer is not maximal compression or maximal decomposition. Structure should be decomposed enough to preserve judgment-relevant distinctions, then layered so that users are not forced to inspect every component at once.

### 4.3 Progressive disclosure is the strongest current presentation direction

Recent HCI work suggests that progressive, on-demand disclosure can improve understanding while managing information load, and that desired transparency depth varies materially across expert and non-expert users.

References:

- Muralidhar, Belloum & Ashok (2025), *Operationalizing selective transparency using progressive disclosure in artificial intelligence clinical diagnosis systems*.  
  https://www.sciencedirect.com/science/article/pii/S107158192500148X
- *Exploratory search with generative AI: An empirical study on the impact of interaction design strategies on information exploration and cognitive load* (2026).  
  https://www.sciencedirect.com/science/article/pii/S1071581926000467

**Working implication:** Stock_vis can preserve one underlying judgment model while varying disclosure depth, rather than immediately creating separate novice and expert mental models.

## 5. Competing Authorship Models

### 5.1 AI-Owned Judgment

The system generates and continuously updates the canonical investment judgment; users mainly inspect or optionally correct it.

**Strengths**
- lowest user effort;
- excellent continuity and monitoring;
- easy to operationalize alerts and automatic updates.

**Failure modes**
- system synthesis becomes de facto user belief;
- strong anchoring and automation-bias risk;
- unclear accountability when the system is wrong;
- conflicts with the Design Lab direction of strengthening rather than replacing user judgment.

**Current judgment:** reject as the primary user-judgment model.

### 5.2 User-Authored Judgment Only

The user manually creates and maintains the judgment; AI supplies evidence, suggestions, and critique but cannot structure the judgment unless requested.

**Strengths**
- strongest authorship clarity;
- high user agency and accountability;
- minimizes silent AI attribution.

**Failure modes**
- high interaction burden;
- weak for time-constrained or less-experienced users;
- risks recreating spreadsheet / note-taking work;
- poor continuity if users do not maintain the state.

**Current judgment:** too burdensome as the default.

### 5.3 AI Drafts Directly Into the User Judgment, User Can Edit

AI maintains the judgment by default and users may edit or override individual components.

**Strengths**
- low maintenance burden;
- strong continuity;
- apparent collaboration.

**Failure modes**
- default effect means AI-authored content can silently become attributed to the user;
- editability may produce perceived control without independent judgment;
- unclear which beliefs were actually adopted by the user.

**Current judgment:** better than AI-owned judgment, but authorship provenance remains too weak.

### 5.4 Separated Co-authorship / Dual-State Model

The system maintains an explicit **System Synthesis / Judgment Proposal** while the user may maintain a distinct **User Judgment State**. AI can propose additions, updates, challenges, or confidence changes, but it cannot silently attribute them to the user or overwrite the user-owned state.

A user may explicitly:

- adopt a proposed component;
- modify it;
- reject it;
- mark it unresolved;
- preserve an existing view despite a system challenge; or
- create a user-only component.

The system may continue to update its own synthesis independently, preserving disagreement when appropriate.

**Strengths**
- clear authorship provenance;
- allows AI to do most structural labor without pretending to own the user's judgment;
- supports disagreement and later comparison between user and system state;
- preserves update lineage;
- supports experts and time-constrained users with different levels of active authorship.

**Failure modes**
- two states can become cognitively confusing;
- excessive confirmation prompts could recreate micro-consensus at the product level;
- users may still rubber-stamp system proposals;
- requires careful nomenclature so "system synthesis" is not mistaken for truth.

**Current judgment:** strongest model.

**Recommendation Strength:** Strong.

## 6. Recommended Working Authorship Boundary

The current recommendation is:

> **AI may generate, organize, challenge, and propose updates to investment judgment, but it should not silently attribute or overwrite a user's judgment. System synthesis and user-owned judgment should remain distinguishable, with material adoption / revision preserving authorship provenance and lineage.**

This does **not** mean the user must manually approve every evidence item or minor update.

A useful working distinction is:

```text
Research Knowledge / Understanding
        ↓
System Synthesis / Judgment Proposal
        ↓ can propose
User Judgment State
        ↓ contributes to
Decision Context and later Decision
```

The system may automatically update its synthesis. The user's maintained state should change through meaningful user action or a clearly delegated rule whose scope remains visible and reversible.

## 7. Consequence-Proportional Human Engagement

Requiring an independent user judgment before every AI contribution would create excessive friction. But immediate AI-first presentation at every consequential moment may increase anchoring and overreliance.

The strongest current direction is **selective cognitive friction** rather than universal precommitment.

Potential high-consequence moments where stronger user engagement may be justified include:

- adopting a material AI-proposed change to a user-owned judgment;
- resolving a major conflict between the user's view and strong contrary evidence;
- changing a core driver / risk from active to invalid or vice versa;
- materially changing conviction under uncertain or conflicting evidence; or
- moving from judgment review toward a consequential portfolio decision.

Low-consequence monitoring, orientation, and evidence browsing should remain lightweight.

Evidence for cognitive forcing suggests it can reduce overreliance but also reduces subjective preference and may affect users differently, supporting a consequence-proportional rather than universal rule.  
https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca2021trust.shtml

## 8. Recommended Granularity Model

The semantic structure should be **richer than the default visible surface**.

### Layer A — Judgment Snapshot

Show only the small set of currently material judgment components needed to understand the current view.

Likely categories may include important drivers / claims, risks, unresolved uncertainties, and meaningful recent changes. The Design Lab should **not** yet fix a universal count such as 3, 5, or 7.

### Layer B — Component Detail

On demand, expose for each component:

- current direction / state;
- local conviction or uncertainty where useful;
- important supporting / challenging inputs;
- why a recent update affected the component;
- dependencies / conditions; and
- system vs user authorship / adoption status where material.

### Layer C — Evidence / Provenance / Update Trace

Provide deeper traceability to Research Knowledge, conflicting evidence, historical revisions, and the actor / reason behind material changes.

This layered model preserves semantic structure without requiring the user to inspect an ontology-like graph at all times.

## 9. Expertise and Personalization

Current evidence does not justify separate foundational judgment models for experts and less-experienced users.

A stronger starting hypothesis is:

> **same underlying semantic model, different disclosure depth and control density.**

Possible differences may include:

- more direct evidence / provenance access for experts;
- stronger guided questions or summaries for less-experienced users;
- user-configurable default depth;
- expandable advanced comparison / assumptions / dependencies.

This remains a working direction and should be validated with real users.

## 10. Scenario Stress Test

### Time-constrained holder

AI can maintain system synthesis and surface only material changes. The user does not manually maintain every component.

**Result:** dual-state + progressive disclosure survives.

### Expert investor with a strong independent thesis

The expert can inspect evidence, preserve a disagreement with system synthesis, author custom components, and avoid having AI updates silently overwrite the thesis.

**Result:** survives better than AI-owned or simplified single-state models.

### Less-experienced user

AI structure can scaffold judgment formation, but the product must avoid presenting the system view as the user's own conclusion. Guided adoption and progressive detail may reduce burden.

**Result:** survives, but user testing is necessary to ensure authorship distinction is understandable.

### User seeking confirmation after a large drawdown

The system can maintain contrary evidence and explicitly show disagreement rather than rewriting the user judgment automatically or simply mirroring the user's position.

**Result:** survives and supports anti-confirmation-bias design.

### AI synthesis is materially wrong

The user can reject the proposal without corrupting the user-owned judgment, while provenance preserves what the system proposed and why.

**Result:** substantially safer than a single auto-maintained judgment state.

### Passive / buck-passing user

The user may simply accept every proposal. Editability alone does not solve this. Consequence-proportional friction and challenge remain necessary.

**Result:** partial survival; this remains a key validation risk.

## 11. Failure / Reversal Conditions

The recommendation should be revised if real-user validation shows that:

- users cannot understand or meaningfully distinguish system synthesis from user judgment;
- maintaining two states creates more confusion than agency;
- explicit adoption mechanics cause severe abandonment or maintenance failure;
- users overwhelmingly prefer one shared state and provenance metadata is sufficient to preserve authorship;
- system-generated structure produces stronger anchoring even when separated visually;
- the judgment structure is too complex to support routine monitoring; or
- separate expert / novice semantic models prove necessary rather than progressive disclosure.

## 12. Batch Consensus

### Recommended Working Architecture

1. Preserve a rich underlying judgment structure but expose it progressively.
2. Do not fix a universal number of visible judgment components yet.
3. Prefer one semantic model with variable disclosure depth before creating separate expert / novice models.
4. Treat editability as insufficient evidence of agency; require real causal control and authorship provenance.
5. Use selective / consequence-proportional cognitive friction rather than forcing independent judgment at every interaction.
6. Preserve system–user disagreement rather than forcing one consensus state.

**Recommendation Strength:** Strong.

## 13. CEO Critical Decision — Human / AI Judgment Authority Boundary

### Decision

Should Stock_vis adopt the following boundary as the working product-authority direction?

> **AI may generate, structure, challenge, and continuously update a System Synthesis / Judgment Proposal, but it may not silently overwrite or attribute that proposal as the user's own investment judgment. A User Judgment State remains distinguishable and material changes to it require meaningful user adoption, editing, rejection, or an explicitly delegated reversible rule.**

### Why this is CEO-critical

This is not merely an interaction detail. It defines:

- who owns the core investment judgment;
- how far AI authority extends;
- how later product surfaces interpret "my view" versus "Stock_vis view";
- whether system automation can silently become decision authority; and
- a long-term dependency for judgment history, personalization, comparison, alerts, and future agent behavior.

### Lead Recommendation

**Adopt the boundary above as the Working human–AI authority direction.**

**Recommendation Strength:** Strong.

### Strongest Counterargument

A dual-state model may be unnecessarily complex. A single AI-maintained judgment with clear provenance and easy override could provide a much simpler product and materially higher engagement, while users may not want to formally maintain a separate judgment state.

### Why the recommendation is not Very Strong

We do not yet have real-user evidence that users understand or value a separate User Judgment State. It is possible that strong provenance, editable components, and reversible system updates within a single state could preserve enough agency with much lower interaction cost.

### Failure / Reversal Condition

If prototypes show that users consistently understand authorship and maintain agency in a single shared state with explicit provenance — and the dual-state model materially harms usability or continuity — the architecture should be simplified.

## 14. Deferred / AI-Owned

The following details do not currently require CEO decision:

- naming of `System Synthesis`, `Judgment Proposal`, `My View`, or equivalent surfaces;
- exact visual markers for authorship provenance;
- exact number of default visible components;
- whether adoption occurs via buttons, inline editing, diff review, or another interaction;
- advanced expert controls;
- precise trigger thresholds for selective cognitive friction; and
- detailed component taxonomy.

These should be explored through prototypes after the authority boundary is resolved.
