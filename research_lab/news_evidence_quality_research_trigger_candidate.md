# Stock_vis News Evidence Quality — Cross-Lab Research Trigger Candidate

**Status:** Working / Research Trigger Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Origin:** Stock_vis Design Lab  
**Intended Recipient:** Stock_vis Research Lab  
**Normative Status:** None — this document is not Research Knowledge, an approved Research Case, a methodology change, or a product decision  
**Korean Companion:** [`news_evidence_quality_research_trigger_candidate_ko.md`](news_evidence_quality_research_trigger_candidate_ko.md)

## 1. Plain-Language Summary

While using real Stock_vis data to design the Company Workspace, the Design Lab found a material mismatch between **news volume**, **processed news-intelligence volume**, and the apparent **company relevance of the resulting items**.

Two opposite failure patterns appeared:

- **NVDA:** very large raw and processed-news counts, but the latest processed sample contains several items whose apparent primary subject is another company or topic.
- **VRT:** substantial raw-news coverage and several apparently direct, potentially material company events, but only one processed-intelligence record.

This does not yet prove a single pipeline defect. It does show that the current counts cannot safely be interpreted as evidence quality, relevance, materiality, or decision usefulness.

The Design Lab therefore submits a Research Trigger Candidate:

> Stock_vis needs a research-grounded semantic and evaluative contract for transforming raw news into company-relevant, event-structured, claim-relative evidence before news intelligence can safely drive Investment View formation or revision.

The Research Lab should decide whether to accept, reframe, merge, defer, or close this candidate under the approved Research Methodology.

---

## 2. Why This Trigger Emerged

The Design Lab is currently translating the H5 reasoning architecture into a real-data Company Workspace. The intended product experience distinguishes:

```text
What changed?
    ↓
What may matter?
    ↓
Which part of the current View may be affected?
    ↓
What evidence supports, challenges, or qualifies that interpretation?
```

News is expected to contribute to `What changed?`, challenge, uncertainty, and evidence exploration. During a read-only data reality pass, the Design Lab found that the current news data could not yet be treated as a reliable input to that flow without additional semantic evaluation.

This is not merely a UI ranking issue. Before Design can decide how to present news, Research must help determine what the news output *means* and what warrant it carries.

---

## 3. Source Snapshot and Reproducibility

The observations below come from the private working-evidence repository:

- Repository: `leftnadal/stock_vis_design_handoff`
- Handoff run: `2026-09-03T163602+0900`
- Inspector version: `0.1`
- Inspector implementation commit: `1826fb88580253f9affadbdc152a3b9c746b8155`
- Schema authority ref used by the Inspector: `origin/main@eb3cdd85ce5cba4d65137758a2f507ebb70fde8b`
- Read-only DB role: `stockvis_design_reader`
- Privacy validation: pass
- Raw integrity validation: pass

Primary references:

- [Latest manifest](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/manifest.json)
- [NVDA data quality](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/NVDA/data_quality.json)
- [NVDA news](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/NVDA/news.json)
- [VRT data quality](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/VRT/data_quality.json)
- [VRT news](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/VRT/news.json)

The handoff repository is private working evidence. It is not Research Lab authority or official Design Knowledge.

---

## 4. Observed Evidence

### 4.1 Coverage counts

| Symbol | Raw news | Processed intelligence | Initial observation |
| --- | ---: | ---: | --- |
| NVDA | 15,653 | 795 | High volume at both stages |
| VRT | 197 | 1 | Raw coverage exists, but processed coverage is extremely sparse |

Both records emit the Inspector warning:

```text
NEWS_INTELLIGENCE_COVERAGE_GAP
Processed intelligence is a subset of raw stored news;
sparse intelligence does not mean no news.
```

### 4.2 NVDA: high processed volume, uncertain direct relevance

The latest bounded NVDA intelligence sample includes multiple items whose titles appear primarily about other companies or topics, including examples centered on:

- a Hasbro insider sale;
- F5 cybersecurity product announcements;
- several AMD institutional-holding changes;
- Amazon institutional-holding changes.

Some records contain co-mentioned symbols, but the title-level primary subject does not appear to be NVDA. These items may be legitimate indirect-context records, false-positive company associations, graph-propagated context, or serving/ranking contamination. The current observation does not determine which explanation is correct.

### 4.3 VRT: low processed volume despite apparently direct raw events

The latest VRT raw-news sample includes several items that appear directly related to Vertiv and potentially material to its business context, including:

- an announced acquisition of UtilityInnovation Group;
- reports describing a roughly $1.45 billion transaction;
- stated intent to reduce time-to-power constraints for AI data centers;
- company-specific discussion of AI infrastructure demand and power bottlenecks.

Yet the processed-intelligence section contains only one record. This may reflect a processing-coverage gap, delayed processing, pipeline routing differences, event-extraction failure, filtering thresholds, or another cause not yet established.

### 4.4 What the comparison establishes

The comparison supports the following bounded observations:

1. Raw-news count is not a measure of relevant evidence quality.
2. Processed-intelligence count is not a measure of company relevance or materiality.
3. High processed volume can coexist with apparent low-directness noise.
4. Sparse processed volume can coexist with apparently direct and potentially material raw events.
5. News availability, processing coverage, semantic relevance, and decision usefulness must remain distinguishable.

---

## 5. What This Evidence Does **Not** Establish

The current evidence does not establish:

- that every apparently indirect NVDA item is an erroneous record;
- that the VRT acquisition news is necessarily investment-material under all scopes;
- which exact pipeline stage caused the observed mismatch;
- whether the root problem is retrieval, entity linking, graph propagation, extraction, storage, ranking, or serving;
- whether article titles alone are sufficient to evaluate relevance;
- how any item supports or challenges a particular Research Claim;
- whether the current pipeline has acceptable precision or recall overall;
- whether one universal materiality rule is possible across companies, claims, and user contexts.

These remain research and engineering questions.

---

## 6. Candidate Research Trigger

### Trigger classes

This candidate appears to involve several approved trigger classes:

- **Failure:** processed outputs include apparently low-directness items and miss or under-process apparently direct items.
- **Knowledge Gap:** Stock_vis lacks a validated semantic contract for news relevance, event identity, materiality, and claim bearing.
- **User Need:** Company Workspace design requires trustworthy signals about what changed and why it may matter.
- **External Change / Scale:** the news pipeline now operates at a scale where volume-based proxies can conceal semantic failure.

### Candidate trigger statement

> Real-data inspection suggests that the current Stock_vis news pipeline may not reliably distinguish raw availability, company association, primary subject, event relevance, materiality, and claim-relative evidential role. This limits the Research Lab’s ability to treat news-derived outputs as disciplined Evidence and limits the Design Lab’s ability to present them responsibly.

---

## 7. Candidate Research Problem

> Stock_vis currently lacks a sufficiently evaluated semantic and evidential framework for transforming raw news items into company-relevant, event-structured, materially scoped, claim-relative evidence. As a result, pipeline output counts and existing “intelligence” records may overstate, understate, or ambiguously represent what the system actually knows about a company.

The Problem should remain open to reframing. A later audit may show that the dominant issue is a narrow implementation defect rather than a broad research gap.

---

## 8. Candidate Primary Research Question

> What semantic and evaluative contract should govern the transformation of raw news into company-relevant and claim-relative evidence for Stock_vis?

### Candidate secondary questions

1. **Entity identity:** Is the company correctly linked to the article?
2. **Primary subject:** Is the company the article’s main subject, a secondary subject, a co-mention, or merely graph-adjacent context?
3. **Directness:** What distinguishes direct relevance, indirect relevance, contextual relevance, and unrelated association?
4. **Event identity:** What event, if any, is the article reporting?
5. **Novelty:** Is the item a new event, a duplicate, an update, commentary, or repetition?
6. **Materiality:** Under what declared scope could the event matter to understanding the company?
7. **Claim bearing:** When a specific Claim is supplied, does the item support, challenge, qualify, discriminate among alternatives, or remain irrelevant?
8. **Source and provenance:** What source properties and provenance must remain visible for later evaluation?
9. **Abstention:** When should the system explicitly return `unknown`, `uncertain`, or `not sufficiently assessed`?
10. **Coverage:** How should Stock_vis characterize the difference between raw coverage and processed-intelligence coverage?
11. **Propagation:** When may news about a related company legitimately propagate to another company, and how should that indirectness be represented?
12. **Evaluation:** What precision, recall, calibration, and consequence-sensitive error profile is fit for each intended use?

---

## 9. Candidate Conceptual Decomposition

The following is a **candidate decomposition for investigation**, not an approved taxonomy.

| Layer | Question | Important boundary |
| --- | --- | --- |
| Source identity | What source item is this? | Presence in DB does not confer credibility |
| Entity association | Which entities are mentioned or linked? | Mention is not relevance |
| Primary subject | What is the article mainly about? | Co-mention is not primary subject |
| Relationship context | Is another entity connected through a material relationship? | Graph adjacency is not automatically evidential relevance |
| Event extraction | What happened, to whom, when, and under what conditions? | Article identity is not event identity |
| Novelty / duplication | Is this new information or repetition? | More articles are not more independent evidence |
| Semantic relevance | Is the event relevant to the company under a stated scope? | Relevance is not materiality |
| Materiality | Could it materially affect understanding under the declared research scope? | Materiality is not user priority or investment attractiveness |
| Claim-relative bearing | How does it bear on a specified Claim? | Bearing is a relation, not an intrinsic article property |
| Processing state | How completely and confidently was it processed? | Processing coverage is not evidence quality |
| Product priority | Should it be shown now to a particular user? | This is primarily a downstream Design responsibility |

These distinctions should not be collapsed into one `news quality score`.

---

## 10. Plausible Alternative Explanations for the Current Failure

The present observations may arise from one or more of the following:

1. ticker/entity-linking false positives;
2. use of co-mention as if it were direct company relevance;
3. primary-subject classification failure;
4. relationship-graph propagation without adequate directness labels;
5. event extraction failure or incomplete event materialization;
6. deduplication or clustering failure;
7. stale or delayed processing queues;
8. source-specific ingestion differences;
9. serving logic that ranks by recency rather than relevance;
10. a correct data model paired with an incorrect Company Workspace query;
11. title-only inspection producing misleading impressions about full-text relevance;
12. thresholds optimized for coverage rather than precision;
13. absent abstention behavior, forcing weak associations into positive classifications.

A Research Case should not assume one explanation before the pipeline is mapped and sampled.

---

## 11. Candidate Initial Investigation

The Research Lab should determine the final Research Design. A reasonable starting design may include:

### Phase A — Pipeline and semantic map

Map the current transformation path:

```text
Raw article
→ source normalization
→ entity extraction / symbol association
→ primary-subject determination
→ event extraction
→ duplicate / update clustering
→ relationship propagation
→ relevance classification
→ materiality / claim linkage
→ storage
→ serving / ranking
```

For every stage, identify:

- explicit semantic responsibility;
- actual implementation behavior;
- missing states and forced classifications;
- provenance preserved or lost;
- possible false-positive and false-negative paths.

### Phase B — Stratified error sample

Build a bounded evaluation sample across at least:

- a high-volume case such as NVDA;
- an uneven-coverage case such as VRT;
- one or more additional cases chosen to expose ticker ambiguity, sparse news, or relationship propagation.

The sample should include both:

- records currently classified as intelligence;
- raw records not promoted into intelligence.

The sample size and sampling method should be set by the Research Design rather than by convenience.

### Phase C — Independent annotation

Candidate annotation dimensions may include:

- entity-link correctness;
- primary / secondary / co-mentioned / unrelated subject role;
- direct / indirect / contextual relevance;
- event identity and event type;
- duplicate / update / commentary status;
- materiality under a stated scope;
- claim-relative bearing when a concrete Claim is supplied;
- source/provenance adequacy;
- legitimate abstention state.

Discovery annotations and confirmatory evaluation should remain distinguishable.

### Phase D — Error analysis and contract candidate

Produce a structured error profile rather than one aggregate score. Determine which failures are:

- semantic-definition gaps;
- data limitations;
- model limitations;
- engineering defects;
- serving/ranking defects;
- unavoidable uncertainty.

Then propose a bounded `News Evidence Quality Contract` candidate for evaluation.

---

## 12. Evaluation Considerations

A single accuracy score is unlikely to be sufficient. Candidate dimensions include:

- entity-link precision and recall;
- primary-subject accuracy;
- direct-relevance precision and recall;
- material-event recall;
- duplicate/event-cluster accuracy;
- source and provenance completeness;
- abstention calibration;
- processed-coverage completeness;
- claim-bearing accuracy when a Claim is explicitly specified;
- severity-weighted false positives and false negatives;
- stability across company types and news-volume regimes.

The intended use must be declared. Different thresholds may be appropriate for:

```text
Background exploration
≠ Company alerting
≠ Investment View revision proposal
≠ Research Evidence admission
```

Click-through rate, article count, sentiment volume, and user engagement must not be treated as sufficient evidence of epistemic quality.

---

## 13. Cross-Lab Responsibility Boundary

### Research Lab — semantic and epistemic authority

The Research Lab should own or govern:

- the meaning of company relevance;
- direct versus indirect relevance;
- event and evidence identity;
- materiality under research scope;
- claim-relative Evidence bearing;
- source/provenance requirements;
- evaluation design and fitness criteria;
- legitimate unknown and abstention states.

### Engineering / Codex — implementation and instrumentation

Engineering should own:

- pipeline mapping and code audit;
- entity resolution;
- primary-subject classification;
- event extraction and clustering;
- deduplication;
- processing instrumentation;
- confidence propagation;
- ranking and serving implementation;
- regression tests and monitoring.

Engineering metrics must implement, not silently redefine, Research semantics.

### Design Lab — downstream representation and user effect

The Design Lab should own:

- which valid information receives attention priority;
- how directness, confidence, coverage, and provenance are shown;
- how uncertainty and processing limits are communicated;
- how users move from event to evidence to View review;
- whether the interface improves investment judgment without creating over-reliance.

### Math Lab — optional downstream contribution

The Math Lab may later study numerical relationships between news-derived signals and market outcomes. It is not the primary authority for the semantic meaning of news relevance or Evidence.

---

## 14. Design Lab Dependency and Interim Guardrails

Until this issue is better understood, the Design Lab will treat news intelligence as **provisional, coverage-limited input**.

Interim guardrails:

1. Do not equate processed-intelligence count with relevance quality.
2. Keep raw-news coverage and processed-intelligence coverage separate.
3. Do not say `no news` when processed coverage is sparse but raw news exists.
4. Do not allow news records alone to silently revise a user-owned Investment View.
5. Keep source and publication-time provenance accessible.
6. Surface `relevance quality under evaluation` where material.
7. Treat direct and indirect company relevance as distinguishable when the system can support it.
8. Prefer abstention to confident but weak relevance claims.
9. Do not use current pipeline outputs as admitted Research Knowledge by origin.

The Design Lab can continue prototype work using these limitations. Product work does not need to stop while Research proceeds.

---

## 15. Candidate Outputs From a Research Undertaking

Possible legitimate outputs include:

- a mapped current-state news transformation pipeline;
- a bounded error taxonomy;
- an annotated evaluation set with provenance;
- a `News Evidence Quality Contract` candidate;
- structured evaluation results by intended use;
- engineering remediation requirements;
- unresolved alternatives or known limits;
- a decision to narrow, split, or close the Research Problem;
- a later candidate Research Claim or Knowledge item, if warranted through the approved methodology.

No output is automatically Research Knowledge.

---

## 16. Requested Research Lab Action

The Design Lab requests that the Research Lab:

1. review this handoff against current Research authorities;
2. decide whether the Trigger is legitimate and material;
3. accept, reframe, merge, defer, or reject it;
4. if accepted, create or designate the appropriate Research Case and Research Design;
5. determine what additional evidence is necessary before any semantic contract is proposed;
6. route narrowly technical defects directly to Engineering when research is not required;
7. return any material Research findings or unresolved constraints that should change Design assumptions.

The Design Lab does **not** request that the Research Lab approve the current Company Workspace design or adopt the candidate decomposition as official terminology.

---

## 17. Reversal / Closure Conditions for This Candidate

This broad Research Trigger Candidate may be narrowed or closed if:

- a reproducible audit shows the observed NVDA/VRT mismatch is caused by one localized implementation bug;
- the Company Workspace query, rather than the underlying news model, is the sole cause;
- the private handoff sample is found to be corrupted or non-representative;
- the intended news use is materially narrower than assumed;
- existing approved Research Knowledge already provides the necessary semantic contract;
- expected epistemic value is low relative to the cost of a broader undertaking.

Conversely, the case should expand only if evidence shows that the problem materially affects multiple symbols, pipeline stages, research uses, or downstream judgments.

---

## 18. Current Recommendation From Design Lab

**Recommendation:** Treat this as a legitimate Research Trigger Candidate and begin with a bounded pipeline/error audit before defining a universal news-quality framework.  
**Recommendation Strength:** Strong  
**Why not Very Strong:** The observed mismatch is material, but the sample is limited and the root cause is not yet identified.  
**Main Alternative:** Route directly to Engineering as a narrow entity-linking or serving bug.  
**Decision Rule:** If the first audit reveals only a localized defect, fix and close. If it reveals unresolved semantic disagreement about relevance, materiality, event identity, or claim bearing, continue as a Research Case.
