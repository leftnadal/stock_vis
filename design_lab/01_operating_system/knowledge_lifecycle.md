# Stock_vis Design Lab Knowledge Lifecycle

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-22  
**Owner:** Stock_vis Design Lab  
**Use Status:** Active Working Baseline (authorized for operational use by Project Owner)

## 1. Purpose

The Design Lab should learn from its work without turning every exploration, preference, or temporary solution into official Design Knowledge.

This lifecycle defines how working exploration can become reusable knowledge, stronger Design guidance, or an explicit Decision Record while preserving revision and avoiding premature formalization.

## 2. Authority Boundary

Research Knowledge remains governed by `research_lab/`.

Design Lab documents may reference Research Knowledge and study its design implications, but they must not duplicate a Research definition and silently claim independent authority over the same concept.

The Design Lab knowledge lifecycle governs Design-side learning: user experience, information representation, interaction, design interpretation, design methods, patterns, failure modes, and other reusable Design knowledge.

## 3. Minimal Document Status

During bootstrap, the Design Lab uses a deliberately small document-status vocabulary unless stronger lifecycle states become necessary.

- **Working** — usable as the current operating or design baseline, but intentionally open to revision through further work and evidence.
- **Approved** — explicitly accepted by the Project Owner as a durable authoritative Design Lab commitment within its stated scope.

A Working document may be **active for operational use** without its underlying concepts becoming final Approved Design Knowledge. Operational permission and epistemic or governance maturity are different questions. To reduce ambiguity, operational-use metadata should avoid using `Approved` as a status label unless the document itself has Approved status.

Additional states such as Superseded, Deprecated, or Retired should be introduced only when real lifecycle needs justify them.

## 4. Default Knowledge States

A useful minimal lifecycle is:

```text
Exploration
→ Working Finding
→ Reusable Design Knowledge
→ Principle / Standard when justified
```

These are maturity states, not mandatory workflow stages. A finding does not have to reach a stronger state.

### Exploration

Ideas, hypotheses, alternatives, benchmarks, persona simulations, prototype results, critiques, and unresolved questions generated during work.

Exploration is not assumed to be true or reusable.

### Working Finding

A finding that is useful enough to guide the current workstream but remains provisional.

Working Findings may be revised freely as the work develops.

### Reusable Design Knowledge

A finding that has demonstrated value beyond a single local decision and is worth making discoverable to future Design work.

Promotion should normally be supported by one or more of the following:

- repeated usefulness across workstreams or scenarios;
- user or usability evidence;
- credible external research or established design evidence;
- repeated prototype or stress-test support;
- explanatory value across multiple design problems; or
- strong consistency with higher-level approved Design and Research constraints.

### Principle / Standard

A Principle or Standard should be created only when a finding requires durable consistency across a meaningful scope and the cost of treating it as merely local or optional has become significant.

Principles and Standards should not be created simply because a statement sounds broadly reasonable.

## 5. Workstreams as the Default Exploration Container

New Design problems should normally begin as workstreams rather than as Foundation, Principles, or Standards.

Workstreams may contain:

- problem framing;
- hypotheses;
- desk research and benchmarking;
- user or persona perspectives;
- alternatives;
- prototypes;
- critique;
- experiments;
- findings; and
- unresolved questions.

Workstream content is Working by default unless a stronger status is explicitly established elsewhere.

The repository does not need a workstream directory before the first real workstream creates demand for one.

## 6. Knowledge Promotion

Promotion is a deliberate judgment, not an automatic result of repetition or agent consensus.

Before promoting a Working Finding, the Lead should ask:

- Is this useful beyond the current local implementation?
- What evidence supports it?
- What is its valid scope?
- What would falsify, narrow, or reverse it?
- Does an existing Research or Design authority already govern the concept?
- Would formalization improve future work enough to justify maintenance cost?

When those questions cannot yet be answered well, the finding should remain Working.

## 7. Knowledge and Decisions Are Different

Design Knowledge describes what the Design Lab has learned.

A Design Decision records an important choice among possibilities under a particular context and authority.

For example, a reusable finding about how users interpret uncertainty may become Design Knowledge, while adopting a specific major navigation architecture is a Design Decision.

Consequential decisions with durable downstream dependency should be captured in a Decision Record when the need arises. Minor reversible decisions normally should not be recorded as formal Decision Records.

## 8. Revision and Retirement

Design Knowledge must remain revisable.

New evidence or repeated failure may justify one of the following:

- **Retain** — current knowledge remains adequate;
- **Revise** — meaning or guidance changes while the knowledge remains substantially continuous;
- **Narrow** — the valid scope is reduced;
- **Replace** — a stronger model or pattern supersedes the prior knowledge;
- **Retire** — the knowledge is no longer appropriate for current use.

Material semantic change should remain explicit and traceable rather than silently overwriting the historical meaning of important knowledge.

If a Design concept becomes cross-Lab or begins to overlap with governed Research terminology, the authority boundary should be reviewed rather than resolved through local renaming alone.

## 9. Documentation Economy

> **Save what future agents need to know; do not archive every thought.**

Use the lightest appropriate level of documentation:

- temporary exploration with little future value may remain unsaved;
- current-workstream material belongs with that workstream;
- reusable findings belong in Design Knowledge when such a structure becomes necessary;
- Lab-wide long-term commitments belong in Foundation, Principles, Standards, or Decision Records only when justified.

Documentation should reduce future reasoning and coordination cost. If documentation creates more maintenance cost than learning value, the structure should be reconsidered.

## 10. Connection to Lab Evolution

The knowledge lifecycle applies to Design work, while `evolution.md` governs learning about the Design Lab's own operating system.

The two may interact. For example, a recurring design-process failure may generate both reusable Design Ops knowledge and a change to the Agent Protocol or Operating Model.
