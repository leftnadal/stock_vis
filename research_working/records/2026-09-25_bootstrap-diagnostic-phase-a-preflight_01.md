# Working Record — Bootstrap Diagnostic Phase A / Checkpoint 01

**Status:** Working Record — Non-Authoritative; source inventory verified, execution-contract corrections proposed  
**Date:** 2026-09-25  
**Topic:** Bootstrap Diagnostic Review — Phase A Source Inventory and Blinding Boundary  
**Keywords:** bootstrap diagnostic, Phase A, frozen claims, selected route validity, Gold v0.2.2, blind-first, source provenance, shared miss, no duplicate execution, inventory correction, 사전 점검, 배치 혼동, 근거 경로, 역할 분리  
**Prior Record:** [Chat / Work role boundary](2026-09-20_research-chat-work-role-boundary_01.md); [record evaluation checkpoint 09](2026-09-19_record-reconstruction-evaluation-target_09.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Official snapshot read:** `36e385a189ef6014a899ff2b8dd994a1a3d28dd2`  
**Related Official Documents:** [Research Methodology v1.2](../../research_lab/01_methodology/research_methodology.md), [Evaluation Methodology v1.1](../../research_lab/02_evaluation/evaluation_methodology.md), [Operational Record Specification v1.0](../../research_lab/01_methodology/operational_record_specification.md).  
**Recording basis:** The established Working Record system permits material checkpoints without separate per-record approval. This record does not amend official Methodology or authorize a new experiment.

## Context and Prior Position

The current Chat proposed a Bootstrap Diagnostic Pilot with a development-only Phase A and a later discovery phase. The user agreed to continue the design. The latest Phase A proposal reused historical Primary outputs, hid Gold v0.2.2 and prior verdicts, and described three full packages as 14 / 14 / 15 claims. It also associated the baseline package with the original all-source_direct collapse.

This checkpoint records actual archive inspection and corrections. It does not retroactively rewrite the earlier proposal, and the newly proposed design corrections below are not represented as already agreed official decisions.

## Directly Checked Source State

The current materialized development source batch is `8737355cc59549c6bee5424cde069d43`, with predecessor `6f739c4557c84627993657509a9983d0`.

| Bundle | Frozen input claims | Primary annotations | Gold v0.2.2 entries | Stored v0.2.2 judgments |
|---|---:|---:|---:|---|
| `2f9c8a41e6d54703` | 14 | 14 | 14 | 13 valid / 1 invalid |
| `7b6e1a9c4d2f43b8` | 13 | 13 | 13 | 13 valid / 0 invalid |
| `a4d71e0b93c6425f` | 16 | 16 | 16 | 14 valid / 2 invalid |
| Total | 43 | 43 | 43 | 40 valid / 3 invalid / 0 review-required |

The input claim text matches the Gold claim text for all 43 IDs. Gold v0.2.2 contains 51 sufficient routes and 9 known-insufficient routes. These route counts are not counts of independent cases, nor are they the complete 62-item reviewer population.

The three Primary files contain development basis annotations, not the original free-form reconstruction outputs. In the current baseline output, only 4 of 13 annotations have the sole basis set `source_direct`; other basis sets are present. The original 43/43 collapse remains historical evidence about an earlier run, not an observed property of this later batch.

### Mechanical Verification Performed Here

A new read-only local checker inspected four original archives without executing their bundled code:

- archive CRC checks: 4/4;
- declared artifact SHA-256/byte entries: 78/78 match;
- source-batch SHA256SUMS entries: 16/16 match;
- structural and cross-file consistency checks: 23/23;
- exact claim-ID coverage and input-to-Gold claim text agreement: 43/43;
- all four archive hashes unchanged after inspection.

These checks establish byte/record consistency within the retrieved packages. They are not independent semantic validation, proof of upstream authenticity, a reviewer-performance experiment, or a re-adjudication of the stored 40/3/0 result. The Gold claim_sha256 derivation convention was not separately revalidated; the checker compared actual claim strings and package-byte hashes.

## Source Identity

Library archives, verified by their actual bytes:

| Archive | SHA-256 |
|---|---|
| `StockVis_Gold_v021_Route_Sufficiency_Audit_8737355c.zip` | `507b23a8e389cb90a83a7cc557dafdaab596fa7364b70ead695de5b84863820c` |
| `StockVis_Gold_v022_Reviewer_Adjudication_Candidate.zip` | `18310ba9ea521dafe17295557f94f3bbc9021c147ae1e9fd190f77df5e06ea6b` |
| `StockVis_Gold_v021_Reviewer_SchemaCorrection_v021r2c1.zip` | `3cbb0043009e27310dc36c57cd3b0a6356e4688006e70a64066f31f15a59ed70` |
| `StockVis_Record_Reconstruction_Transfer_Canary_v010r1_Preparation.zip` | `5bab33723fc34d164a273c483f2b9b7452506ecb1a1ad51f32108e57dc2ef6bc` |

Material members:

- `record_reconstruction_development_calibration_v011/inputs/<bundle_id>.json`: frozen claims and source bundles.
- `source_batch_8737355c/8737355cc59549c6bee5424cde069d43/<bundle_id>/parsed_final.json`: historical Primary basis annotations.
- `reviewer_adjudication_v022/protected/gold_v022_candidate.json`: SHA-256 `96b2481140df6444106be94a6fe1f422dd1b12f92c382977a509545ace843547`.
- `reviewer_adjudication_v022/results/rescore_v022_candidate.json`: SHA-256 `c5214227ac84ecb1c3e7b31008bf16a48d9b69b5dcbc3d462c96b64204210b09`.
- `reviewer_adjudication_v022/results/route_adjudication_v022.json`: 62-item historical Work adjudication, not a new audit performed here.

The original reviewer execution ZIP `bce177e5e1934caaad9361de94402f3f` could not be materialized through the current authorized file path. Its reported 3/3 completion and execution checksum checks are therefore inherited Work reports, not independently rerun or rechecked here.

## Design Corrections Proposed

### 1. Freeze identity, not just the number 43

Use the actual 14 / 13 / 16 claim IDs and source batch. Do not substitute earlier reconstruction outputs merely because their total also equals 43. Original collapse examples may be added only as a separately identified historical control, with their own artifact lineage.

### 2. Separate blind-first assessment from selected-route audit

The approved development target in the retrieved Gold is `selected_route_validity`: whether the route actually declared in an output supports the claim's content, strength and scope, with appropriate roles and derivation. It is not an obligation to recover every valid route or the historical causal generation path.

Keep the proposed blind-first assessment as an initial source-grounded view made without seeing the Primary annotations or Gold. Then, in an explicitly post-reveal comparison/audit step, inspect the frozen Primary's actual basis sets, evidence references, locators and derivation. Only this second step can characterize a defect in the selected Primary route. Its findings must not be mislabeled as pre-reveal blind discoveries.

A different valid route selected by the blind reviewer is not by itself a Primary error. A reviewer may not silently repair an unsupported Primary route by citing a better route and then call the original output valid.

This is a proposed operational correction, not permission for extra model calls. Work should map it to a bounded execution plan rather than silently adding calls.

### 3. Preserve evidential prior evaluations

Do not blanket-delete all prior evaluations from the source bundle. A prior assessment being cited is part of the task evidence and must remain readable with its provenance. Hide case-specific Gold verdicts, later rescoring, correction rationales and diagnostic/adjudication answers. Missing original records remain missing; packaging must not fill them with reconstructed content.

### 4. Do not inspect only disagreements

A disagreement-only adjudication path cannot observe shared misses in agreement cases. Phase A should include a predeclared source-grounded check of agreement/positive-control cases as well. For the finite 43-claim development set, full lightweight coverage is a reasonable proposal; deeper adjudication remains materiality-proportional. Agreement is not proof of correctness, and absence of review is not a negative finding.

## Work State and Non-Duplication

The latest retrieved transfer-canary preparation says `prepared_not_executed` / `ready_for_approved_single_execution`, selects historical reserve `hard-002`, and contains 12 frozen claims. It reports an existing one-call, no-retry execution envelope capped at USD 0.04. The package itself is not evidence that the call later ran; no later execution result was verified here.

That canary is historically exposed transfer evidence, not true held-out discovery. Its prior approval does not authorize new three-case Bootstrap calls, a different provider, or extra private-payload transmission. Do not cancel or duplicate that Work task based only on this checkpoint.

## Current State / Next

**Completed here:** official-document and Working Record reads; source retrieval; byte/identity checks; inventory manifest; design-level corrections.

**Not completed or claimed:** new blind payload construction, leakage-test completion for a new payload, new reviewer/model execution, independent adjudication, Phase B readiness, permanent architecture, Knowledge/memory admission, or official Methodology changes.

Research Chat recommends preserving this corrected source inventory and resolving the input-visibility contract before Work freezes a new executable payload. Routine implementation repairs remain Work-owned. New resources or materially changed experimental contrasts require the applicable bounded approval, not repetitive approval for every parser or fixture repair.

The accompanying local `source_inventory_manifest.json` is a source-audit artifact, not a model-visible input or permission token. Its SHA-256 at this checkpoint is `f3c811d66bff609e604340670eaa2d20ce3c97ccbc7cf78add888550688bbd38`.
