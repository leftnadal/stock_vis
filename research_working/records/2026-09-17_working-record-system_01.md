# Working Record — Working Record System / Checkpoint 01

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-17  
**Topic:** Working Record System  
**Keywords:** working record, non-authoritative, historical fidelity, reconstructability, material checkpoint, retrieval, index  
**Prior Record:** None  
**Related Official Documents:**
- `research_lab/README.md`
- `research_lab/01_methodology/operational_record_specification.md`

## Context

Important Research Lab ideas, provisional agreements, objections, and incomplete designs were often preserved only in chat until they were formally approved. This created a gap between transient discussion and authoritative `research_lab/` documents.

The goal is to preserve material intellectual history without creating a second official knowledge system or recording every conversation.

## Current State

The preferred initial architecture is a repository sibling of the official Research Lab:

```text
research_lab/       # authoritative
research_working/   # non-authoritative
```

`research_working/` begins with only:

```text
README.md
INDEX.md
records/
```

Working Records are organized around **material checkpoints**, not chat sessions and not permanently mutable topic documents.

Each record uses stable Topic and Keywords metadata so later human or agent retrieval does not depend on remembering a conversation date. `Prior Record` links may connect later checkpoints in the same intellectual lineage.

`INDEX.md` is a lightweight retrieval layer only; it must not become a competing summary authority.

## Alternatives / Objections

### `research_lab/working/`

Rejected as the preferred initial location because placing non-authoritative material under the official Research Lab directory could blur authority boundaries.

### Separate repository

Considered stronger isolation but unnecessarily increases retrieval, linking, and automation complexity at the current scale.

### GitHub Issues / Discussions as primary record

Potentially useful as an interaction surface but less suitable than repository Markdown as the durable primary working record for versioning and machine retrieval.

### Session-based meeting notes

Simple to create but weak for topic-based retrieval and longitudinal reconstruction.

### Continuously edited idea documents

Easy to read in the present but risk hindsight rewriting and loss of historical intellectual states.

## Provisional Position

Use `research_working/` as a clearly non-authoritative sibling of `research_lab/`.

Use material-checkpoint records with stable Topic/Keywords metadata and append-oriented history. Preserve earlier material states rather than rewriting them after later outcomes are known.

After the Working Record system is established, material checkpoints may be recorded without requesting separate approval each time. This does not authorize changes to official Research Lab documents.

## Open Questions

- Whether repeated operational use will justify additional subdirectories or record types.
- Whether a controlled status/disposition vocabulary becomes useful after real usage accumulates.
- How retrieval/routing should work when the number of Working Records becomes large.
- Whether other Labs should use analogous systems or their existing working structures are sufficient.

## Next

Use the minimal structure in real Research Lab work before adding further schema or hierarchy. Evaluate retrieval quality, recording burden, authority confusion, and historical reconstructability from actual use.
