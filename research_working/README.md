# Stock_vis Research Working Records

**Status:** Non-Authoritative Working Area  
**Official Authority:** [`../research_lab/`](../research_lab/) on `main`

## Purpose

`research_working/` preserves material research thinking that is important enough to reconstruct later but is not yet an approved Research Lab document, Research Knowledge, Methodology, Decision, or other authoritative artifact.

This area exists to prevent important ideas, provisional positions, alternatives, objections, failure risks, unresolved questions, and later revisions from being trapped only in transient chat or agent context.

## Authority Boundary

- The Single Source of Truth for official Stock_vis Research Lab content remains `main/research_lab/`.
- Nothing in `research_working/` becomes official merely because it is stored here.
- A Working Record may contain ideas that are incomplete, later rejected, superseded, or inconsistent with official documents.
- If a Working Record conflicts with an official Research Lab document, the official document always prevails.
- Official changes still require the Project Owner's explicit execution approval and the normal Research Lab change process.

## Recording Principle

Working Records follow **reconstructability over exhaustiveness**.

Do not preserve every conversation, intermediate thought, or minor edit. Preserve material checkpoints when doing so helps a future researcher or agent reconstruct why an important research, methodology, evaluation, architecture, or operating judgment developed or changed.

Typical record-worthy events include:

- a material new idea or structure;
- a provisional agreement among meaningful alternatives;
- a serious objection or failure condition;
- a material unresolved question;
- a change, restriction, or withdrawal of an earlier position;
- an observed result that causes an important judgment to be reconsidered; or
- a candidate idea that may later affect official Methodology, Evaluation, Architecture, Terminology, Ontology, or operations.

## Historical Fidelity

Working Records should preserve the intellectual state at the time of the checkpoint.

Do not rewrite a prior record after later outcomes become known in order to make the earlier judgment appear more accurate or coherent. Material reinterpretation, correction, restriction, or withdrawal should be represented by a later record or an explicit disposition update that preserves the earlier state.

## Retrieval

Use [`INDEX.md`](INDEX.md) as a lightweight discovery layer.

Each record should normally include:

- `Status`
- `Date`
- `Topic`
- `Keywords`
- `Prior Record`, when applicable
- `Related Official Documents`, when applicable
- Context
- Current State
- Alternatives / Objections
- Provisional Position
- Open Questions
- Next

`INDEX.md` is a locator, not a second source of truth. Detailed working history belongs in the records; current official state belongs in `research_lab/`.

## Initial Structure

```text
research_working/
├── README.md
├── INDEX.md
└── records/
```

The physical structure should remain minimal until repeated use demonstrates a need for additional organization.
