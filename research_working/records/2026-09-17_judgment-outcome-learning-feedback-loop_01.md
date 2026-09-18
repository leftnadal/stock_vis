# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 01

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-17  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** judgment quality, outcome bias, signal, review target, execution, evidence, assumption, system, learning quality, candidate learning, transfer test, operational learning  
**Prior Record:** None  
**Related Official Documents:**
- `research_lab/01_methodology/research_methodology.md`
- `research_lab/02_evaluation/evaluation_methodology.md`
- `research_lab/01_methodology/operational_record_specification.md`

## Context

The Research Lab needs to improve how it makes research judgments by comparing the reasons for a decision with what later occurred, without equating a good outcome with a good judgment.

The discussion began from the need to preserve what was known, unknown, expected, and considered at decision time; compare that state with later Reality; and use the difference to improve future research judgments without hindsight rewriting or reactive overfitting to recent outcomes.

## Current State

A useful working distinction has emerged among three layers:

1. **Judgment Quality** — how well the decision was made given information and uncertainty available at the time.
2. **Outcome / Reality** — what actually occurred afterward.
3. **Post-outcome Learning** — whether the Lab interpreted the difference appropriately and improved future judgment without overclaiming what the result establishes.

Unexpected or important results should not move directly from `Outcome → Change`.

The current working flow is:

```text
Judgment
↓
Outcome / Reality
↓
Signal
↓
Candidate Review Targets
↓
Investigation
↓
Diagnosis
↓
Candidate Learning
↓
Discriminating / Transfer Test
↓
Bounded Operational Learning
↓
Future Judgment
↓
Reality comparison again
```

Candidate Review Targets may include:

- Execution
- Evidence / Information
- Reasoning / Assumption
- Method / System

These are candidate targets rather than an immediate root-cause declaration because one observed failure may plausibly involve more than one layer.

Review Target and Change Target should remain distinct. Investigation may show that the initially reviewed component does not need modification, and `Maintain` or `Observe` must remain legitimate outcomes.

## Signal Strength Working Principles

A reconsideration obligation should not depend only on a mechanical count of failures.

Two broad patterns can justify review:

- a single sufficiently direct and material contradiction of a core assumption; or
- an accumulating pattern across sufficiently independent observations.

Relevant characteristics may include directness, materiality, recurrence, independence, and degree of conflict with the prior expectation. These are not currently proposed as a numerical score.

A review obligation does not imply a change obligation.

## Judgment Quality Working View

The current candidate dimensions for examining a research judgment include:

- framing;
- information adequacy;
- alternative adequacy;
- assumption and uncertainty awareness;
- reasoning and effective challenge; and
- epistemic value / proportionality.

The dimensions are intended as structured questions rather than a universal numerical score.

A research action may be valuable even when it does not produce the desired outcome if it was a disciplined choice that discriminated among important alternatives or reduced material uncertainty.

## Learning Quality Working View

`Learning Quality` is currently treated as a useful working concept, not a new official Evaluation family.

The preferred current direction is to examine it as a post-outcome aspect of Research Process Evaluation unless later operational evidence supports a separate formal category.

Candidate properties include:

- historical fidelity;
- diagnostic discipline;
- update proportionality;
- preservation of uncertainty; and
- transfer testability.

A result-derived lesson should normally remain **Candidate Learning** until it is tested sufficiently to support broader use.

## Candidate Learning and Generalization

One strong counterexample may be enough to defeat an overly universal prior claim, but it does not automatically establish a new universal rule.

Generalization should consider more than case count. Relevant questions include:

- replication;
- independence;
- discrimination among competing explanations;
- boundary conditions; and
- transfer beyond the development case.

The preferred direction is toward bounded learning such as "under conditions X, mechanism Y creates risk Z" rather than broad statements such as "Critics do not work."

Candidate learning should, when material, support a discriminating prediction that could separate it from plausible alternative explanations.

## Alternatives / Objections

### Change the method after every unexpected result

Rejected because this risks recency-driven overfitting and confuses execution failure, missing evidence, incorrect assumptions, and system-level failure.

### Require repeated failures before any reconsideration

Rejected as too rigid because a single decisive observation may directly contradict a core premise.

### Immediately create a new Learning Quality Evaluation family

Deferred because the existing Research Process Evaluation and meta-evaluation structures may already cover the needed function. Operational evidence should precede additional ontology or methodology layers.

### Promote every useful lesson directly into methodology

Rejected because development-case fit is not equivalent to transfer or generalization.

## Provisional Position

Preserve decision-time rationale separately from later outcomes.

Use results as evidence for review rather than as direct verdicts on judgment quality. Diagnose candidate review targets before choosing what to change. Keep learning bounded to what the evidence supports, and test important candidate lessons in other conditions before treating them as operationally general.

Do not revise historical decision records to make them fit later outcomes.

## Open Questions

- How should bounded Operational Learning be retrieved and routed into future Research Cases without overwhelming agents with historical context?
- When does a Candidate Learning have enough transfer evidence to influence a routine operating rule?
- How should cross-case independence be characterized operationally without creating rigid numerical thresholds?
- Which parts of this working structure are already adequately represented by current official Evaluation and Operational Record semantics, and which—if any—eventually warrant an official extension?

## Next

Continue with the operational question of how relevant prior learning should be retrieved and introduced into future research judgments. Use actual Research Work outcomes to stress-test the working model before proposing Methodology changes.
