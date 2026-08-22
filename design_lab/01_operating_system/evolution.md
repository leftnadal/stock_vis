# Stock_vis Design Lab Evolution Model

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-22  
**Owner:** Stock_vis Design Lab  
**Use Status:** Active Working Baseline (authorized for operational use by Project Owner)

## 1. Purpose

The Design Lab itself is a design system that should improve through use.

This document defines how recurring friction, failure, or structural mismatch discovered during Design work can change the Lab's own operating model, agent protocol, knowledge structure, documentation, or other internal architecture without requiring the initial structure to be correct forever.

The objective is controlled evolution without either rigidity or governance sprawl.

## 2. Core Evolution Loop

```text
Operate
→ Observe
→ Diagnose
→ Adapt
→ Validate
```

### Operate

Use the current Design Lab structure to perform real work.

### Observe

Notice friction, repeated confusion, missed escalation, synthesis cost, authority ambiguity, documentation failure, agent failure, or other evidence that the Lab structure may not be serving its purpose.

### Diagnose

Determine whether the issue is:

- local to one task;
- likely to recur across work;
- or structural and consequential for the Lab as a whole.

### Adapt

Make the smallest change appropriate to the diagnosed scope.

### Validate

Observe later work to determine whether the change solved the problem or introduced new failure modes.

## 3. Three Levels of Change

### Local Fix

A task-specific adjustment with little expected impact outside the current workstream.

Examples may include shortening one agent output, changing the sequence of one prototype exercise, or adjusting a temporary role.

The Design Lab Lead may make Local Fixes immediately without formal governance or CEO approval.

### Operating Improvement

A change to a repeated working pattern that is likely to improve multiple future tasks.

Examples may include changing the Agent Output Contract, moving critique earlier in a recurring workflow, clarifying workstream write-back, or adjusting the default composition of agents for a recurring task class.

The Lead may implement reversible Operating Improvements within approved or active Working authority, while recording or documenting them when future agents need the changed rule.

If the improvement materially changes authority, semantics, or long-term dependency, it should be reclassified as Structural Change.

### Structural Change

A change that materially affects the Design Lab's Purpose, Philosophy, core operating authority, major knowledge architecture, Research–Design boundary, or other durable cross-cutting structure.

Structural Changes require consequence analysis and CEO discussion under the Operating Model's escalation rules.

## 4. Anti-Overreaction Rule

> **Do not promote one-off friction into permanent governance too quickly.**

A single inconvenient task does not automatically justify a new document, agent role, principle, process stage, or approval requirement.

Prefer a Local Fix first when the cost of being wrong is low.

Repeated friction, cross-workstream recurrence, or high-consequence failure provides stronger justification for formal operating change.

## 5. Signals That the Lab May Need to Evolve

The following are examples of useful signals, not exhaustive triggers:

- agents repeatedly cannot find the context or authority they need;
- agent outputs are consistently difficult or costly to synthesize;
- independent critique arrives too late to prevent rework;
- Research consistency issues are repeatedly discovered after design commitment;
- Micro-consensus begins to reappear and slows work without improving decision quality;
- Tier 3 decisions accumulate unintended semantic commitments;
- CEO escalation is consistently too frequent or too rare;
- Decision Packages become too large to evaluate coherently;
- workstream findings are either over-formalized or repeatedly lost;
- Design Knowledge and Working exploration become difficult to distinguish;
- documentation structures create more maintenance cost than retrieval value;
- the Lead becomes a persistent synthesis bottleneck; or
- new Design work no longer fits the current Lab structure without repeated exceptions.

These signals should prompt diagnosis rather than automatic structural change.

## 6. Delegation Reversal Conditions

The Design Lab currently favors delegated exploration and autonomous execution under approved or active Working boundaries.

Delegation should be narrowed or restructured if evidence shows repeated failures such as:

- important semantic or architectural commitments being treated as routine Tier 3 decisions;
- repeated conflict with approved Research or Design authorities;
- important CEO-approved constraints being silently eroded;
- batch decisions becoming too broad for meaningful CEO review; or
- autonomous execution producing costly downstream reversals.

Conversely, delegation may be expanded when repeated work demonstrates that a class of decisions is low-risk, reversible, and reliably constrained by existing authority.

## 7. Documentation and Versioning

The Lab should document operating changes only to the degree needed for future consistency and traceability.

- Local Fixes normally do not require permanent records.
- Operating Improvements should update the relevant living document when the new behavior is expected to persist.
- Structural Changes should receive explicit review and, when consequential, an appropriate Decision Record once that structure exists.

Historical meaning should not be silently rewritten when a material governance or authority change occurs.

## 8. Relationship to Other Bootstrap Documents

- `operating_model.md` defines how the Lab currently operates and decides.
- `agent_protocol.md` defines how specialist agent work is composed and synthesized.
- `knowledge_lifecycle.md` defines how Design work becomes reusable Design Knowledge.
- this document defines how evidence from operating the Lab can change those systems themselves.

The Evolution Model is not a separate approval bureaucracy. It is the mechanism that keeps the Bootstrap structure intentionally provisional, testable, and capable of improvement.
