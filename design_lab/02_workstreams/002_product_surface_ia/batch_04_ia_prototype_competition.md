# Workstream 002 — Batch 04: IA Prototype Competition

**Status:** Working  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; not Approved Product IA

## 1. Batch Question

> **When the leading IA families are represented as actual low-fidelity user flows rather than conceptual diagrams, which architecture best preserves orientation, reasoning continuity, predictable navigation, and cross-scenario scalability?**

Batch 03 generated multiple architectures from cross-domain patterns. Batch 04 prototypes the three most consequential combination candidates:

- **H1 — Minimal Three-Space**
- **H2 — Explicit Explore**
- **H4 — Question-First Adaptive**

The purpose is not to select final navigation labels. It is to expose where each semantic structure creates or removes cognitive friction.

## 2. Prototype Evaluation Frame

Each prototype must answer four questions at all times:

1. **Where am I?** — current semantic scope must remain visible.
2. **What am I doing?** — Orient / Explore / View / Monitor / Compare / Decide / Review should not blur silently.
3. **What object or question is carrying context?** — company, theme, comparison set, portfolio, or investigation.
4. **How do I return?** — especially after interruption or on mobile.

Additional stress dimensions:

- orientation speed;
- discoverability;
- continuity of Investment View;
- context switching;
- duplication;
- mobile returnability;
- Human–AI authority clarity;
- progressive disclosure;
- extensibility.

## 3. Prototype H1 — Minimal Three-Space

### Stable structure

```text
ORIENTATION
    ↓
INVESTMENT WORKSPACE
    ↓ when decision needed
DECISION CONTEXT
```

Research / relationship exploration / evidence / scenario analysis are contextual capabilities opened from the current Investment Workspace or Decision Context.

### Scenario walkthroughs

#### S1 — Three-minute Morning Review

`Orientation → attention-ranked companies → IREN → inline change / focused review if material`

Very low navigation cost. The user's coverage universe and attention priority have a clear home.

#### S2 — New Company

`Search / discovery entry → Investment Workspace → System Synthesis → evidence / risks / scenarios → optional My Investment View`

Simple and coherent once a company is selected.

#### S3 — Mixed Earnings

`Orientation trigger → IREN Workspace → Focused Review → affected components / evidence / unresolved items`

Strong because the event maps back to one maintained object.

#### S4 — AI Power Infrastructure Exploration

This exposes H1's core weakness. If exploration must always begin inside a company workspace, the user is forced to pick a company before the real question is mature.

Possible workaround: a contextual `Explore` overlay launched from Search or relationships. But as that overlay becomes richer, H1 starts hiding an implicit fourth space.

#### S5 — IREN vs NBIS Rotation

`IREN / NBIS views → Decision Context → future scenarios / valuation / portfolio / relative opportunity`

Semantically clean.

#### S6 — Mobile Return

Very strong. The small number of stable spaces makes interruption recovery easy.

### H1 judgment

**Strength:** learnability and stable orientation.  
**Failure:** open-ended investigation becomes artificially subordinate to a selected investment object.

**Current strength: Strong, but structurally incomplete if theme/question exploration is a first-class user need.**

---

## 4. Prototype H2 — Explicit Explore

### Stable structure

```text
ORIENTATION
      ├──────────────┐
      ↓              ↓
INVESTMENT        EXPLORE
WORKSPACE         question / theme / relationship
      \              /
       \            /
        ↓          ↓
       DECISION CONTEXT
```

Explore is a real semantic space rather than a hidden tool.

### Scenario walkthroughs

#### S1 — Three-minute Morning Review

Still strong. Orientation remains the default coverage entry.

#### S2 — New Company

A new company may be entered either from Search / Explore or directly into an Investment Workspace. This improves discovery continuity.

#### S3 — Mixed Earnings

Strong, but a boundary question appears: should deep evidence investigation occur inside Investment Workspace or transition to Explore? Without a rule, evidence and reasoning can duplicate.

#### S4 — AI Power Infrastructure Exploration

Very strong. `Explore: AI power infrastructure` can preserve a thematic question before any one company becomes primary.

Relationships, claims, evidence, companies and candidate opportunities can coexist without forcing early object commitment.

#### S5 — IREN vs NBIS Rotation

Strong. Explore may help investigate unresolved comparative questions, while Decision Context owns the actual comparison / allocation judgment.

#### S6 — Mobile Return

Strong if the product preserves a clear `current investigation` identity. Slightly harder than H1 because users must remember whether they were in Explore or Investment.

### H2 judgment

**Strength:** gives genuine conceptual room to investigation and discovery.  
**Failure:** Explore can become a catch-all research bucket and duplicate company evidence / scenarios / relationships.

**Current strength: Strong.**

---

## 5. Prototype H4 — Question-First Adaptive

### Raw version

The user asks a question and the system composes the relevant object(s), reasoning lenses and evidence.

Examples:

```text
"Why did IREN fall?"
→ IREN + Change + competing explanations + relevant evidence

"Should I rotate IREN into NBIS?"
→ IREN + NBIS + future scenarios + valuation + Decision Context

"Who benefits if transformer shortages persist?"
→ theme + relationships + companies + future conditions
```

### Core benefit

The architecture maps closely to how users think: they usually have a question, not a feature name.

### Raw-version failure

Pure adaptive composition creates a serious location problem:

- the same question may produce materially different layouts;
- users may not learn where information lives;
- returning after interruption can feel like reopening an AI answer rather than returning to a durable workspace;
- AI may silently control information hierarchy.

Therefore Batch 04 also tests **H4-S — Stable Semantic Shell + Adaptive Canvas**.

## 6. H4-S — Stable Semantic Shell + Adaptive Canvas

### Fixed coordinates

The system may adapt content, but it must always expose two stable semantic coordinates.

#### Scope

```text
Coverage / Portfolio
Theme / Question
Investment
Comparison / Decision Set
```

#### Reasoning mode

```text
Orient
Explore
View / Understand
Monitor / Update
Compare
Decide
Review / Learn
```

Time orientation is visible context where material:

`Past / Current / Change / Future / Outcome`.

### Example shell

```text
Scope: IREN
Mode: Monitor / Update
Question: What did Q2 earnings change?

[adaptive canvas]
- affected Investment View components
- competing explanation
- evidence
- scenario impact
- system-user divergence

Persistent escape / return:
Orientation | Open Investment | Decision Context
```

The canvas can adapt while the semantic coordinates remain stable.

### Scenario walkthroughs

#### S1 — Three-minute Morning Review

`Scope: Coverage | Mode: Orient`

The canvas ranks attention items. Selecting IREN changes scope while preserving the reason for transition.

Strong.

#### S2 — New Company

`Scope: Investment: NewCo | Mode: View / Understand`

Suggested questions can compose evidence, risks and scenarios without creating a separate AI page.

Strong.

#### S3 — Mixed Earnings

`Scope: IREN | Mode: Monitor / Update | Question: What changed?`

Differential, evidence and scenario impact can appear only when needed.

Very strong.

#### S4 — AI Power Infrastructure Exploration

`Scope: Theme / Question: AI power infrastructure | Mode: Explore`

The user can traverse relationships without prematurely choosing a company. When a company becomes interesting, scope can shift to Investment while preserving provenance from the investigation.

Very strong.

#### S5 — IREN vs NBIS Rotation

`Scope: Comparison Set: IREN + NBIS | Mode: Compare → Decide`

Future scenarios, growth-path conditions, valuation and portfolio context can be composed without implying that comparison is intrinsic company truth.

Very strong.

#### S6 — Mobile Return

The raw H4 version is weak. H4-S improves substantially if the product persists:

- scope;
- mode;
- active question / investigation;
- last meaningful state;
- explicit resume affordance.

Still more demanding than H1.

### H4-S judgment

**Strength:** maximum fit to real user questions while preserving stable coordinates.  
**Failure:** requires excellent state persistence and disciplined adaptive composition. If the canvas feels arbitrary, predictability collapses.

**Current strength: Strong–Very Strong as a generative direction, not yet a final IA.**

---

## 7. Comparative Stress Test

| Scenario / criterion | H1 Minimal | H2 Explicit Explore | H4-S Stable Adaptive |
|---|---|---|---|
| Morning orientation | Very Strong | Very Strong | Strong–Very Strong |
| New company | Strong | Strong | Strong |
| Mixed earnings | Strong | Strong | Very Strong |
| Theme / relationship exploration | Weak–Mixed | Very Strong | Very Strong |
| Rotation / comparison | Strong | Strong | Very Strong |
| Human–AI disagreement | Strong | Strong | Very Strong |
| Learnability | Very Strong | Strong | Moderate–Strong |
| Location awareness | Very Strong | Strong | Strong if shell is explicit |
| Mobile return | Very Strong | Strong | Moderate–Strong |
| Context continuity | Strong | Strong | Very Strong |
| Risk of feature duplication | Low initially; hidden Explore risk | Moderate | Low–Moderate if semantic lenses are disciplined |
| Risk of AI authority / unpredictability | Low | Low | Highest unless shell constraints are strong |

## 8. Main Prototype Finding

The competition does **not** support choosing one literal architecture unchanged.

Instead, three different strengths should be combined:

- from **H1**: a small number of durable semantic anchors and easy return paths;
- from **H2**: explicit recognition that open-ended investigation / theme exploration is sometimes a genuinely different scope;
- from **H4**: question-first composition and contextual reasoning lenses.

This generates a new candidate:

## 9. H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas

### Working model

```text
                ORIENTATION
                    │
        ┌───────────┼───────────┐
        │           │           │
 INVESTMENT      EXPLORE     DECISION CONTEXT
        │           │           │
        └─────── contextual ─────┘
             reasoning canvas
```

This diagram is intentionally logical, not final navigation.

Inside any space, the product can adapt the visible lenses according to the active question while preserving stable scope / mode / provenance.

Examples:

- IREN earnings → Investment + Monitor / Update lens;
- AI power infrastructure → Explore + Theme / Relationship lens;
- IREN vs NBIS → Decision Context + Compare / Future lens;
- morning review → Orientation + Triage lens.

### Why H5 is promising

It treats **space** and **reasoning lens** as different things.

This prevents every capability from becoming a permanent menu item while also preventing AI from making the entire interface structurally unpredictable.

### Important constraint

Adaptive composition must not silently change semantic authority or make Research / System Synthesis appear as the user's own Investment View or Judgment.

## 10. What This Batch Rejects

### Pure feature menu as the primary IA

Still rejected as the leading model. Features such as News, AI, Relationships, Scenarios, History and Compare appear increasingly like contextual lenses / capabilities rather than equal semantic destinations.

### Pure H1 minimalism

Rejected as too restrictive if genuine theme / investigation workflows matter.

### Unconstrained question-first UI

Rejected. A chat-like answer generator is not sufficient IA. Durable semantic coordinates and return paths are necessary.

### Universal Explore bucket

Rejected as a default. Explore should own question / theme / relationship investigation, not become the place where every deep feature is moved.

## 11. Remaining Uncertainties

- Are four logical spaces already too many for a retail user, or can navigation expose fewer labels while preserving four semantic responsibilities?
- Can Explore remain coherent without duplicating Investment evidence and scenarios?
- Can question-first adaptation remain predictable after repeated use?
- What should persist as resumable work on mobile?
- Should Portfolio be a persistent object inside Orientation / Decision Context or deserve a visible space of its own?
- How should Watchlist / coverage sets relate to Orientation?
- What level of user customization is helpful before it becomes configuration burden?

## 12. Recommendation

Advance **H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas** as the leading prototype hypothesis, while retaining H1 as the simplicity challenger and H2 as the explicit-space challenger.

**Recommendation Strength: Strong.**

Do not approve final IA yet. The next prototype should test actual screen-level navigation and return behavior, especially on mobile, before any top-level architecture commitment.

## 13. Failure / Reversal Conditions

Reverse or simplify H5 if:

- users cannot predict where a task belongs;
- Explore and Investment repeatedly duplicate content;
- adaptive lenses create disorientation;
- mobile state restoration is poor;
- users prefer a simpler H1-like structure without losing meaningful exploration ability;
- portfolio / comparison tasks require a different persistent structure; or
- real usage shows that question-first entry is much less important than expected.

## 14. CEO Critical Decision

**None in this Batch.**

H5 remains a Working IA hypothesis. No top-level navigation, screen naming or product architecture is being locked.