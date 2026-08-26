# DL-DR-0001 — Human–AI Judgment Authority Boundary

> **한국어 Companion 문서**  
> 원문: [`DL-DR-0001_human_ai_judgment_authority.md`](DL-DR-0001_human_ai_judgment_authority.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 CEO-approved semantic intent와 관련 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Approved  
**Decision ID:** DL-DR-0001  
**Approved:** 2026-08-27  
**Effective Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Authority:** CEO / Project Owner

## 1. Decision

Stock_vis는 다음 Human–AI judgment authority boundary를 채택한다.

> **AI는 System Synthesis / Judgment Proposal을 생성하고, 구조화하고, challenge하고, 지속적으로 업데이트할 수 있다. 그러나 이를 사용자의 investment judgment로 조용히 덮어쓰거나, 귀속하거나, 사용자의 판단인 것처럼 표현해서는 안 된다. User-owned judgment는 의미상 구분되어야 한다. User-owned judgment의 material한 변경에는 의미 있는 user action 또는 scope가 보이고 되돌릴 수 있으며 추적 가능한 명시적 delegated rule이 필요하다.**

Material한 채택이나 수정에는 충분한 **authorship provenance와 update lineage**가 남아야 한다. 즉 system이 무엇을 제안했고, 사용자가 무엇을 채택하거나 직접 만들었으며, 무엇이 material하게 바뀌었는지 추적할 수 있어야 한다.

System과 user의 disagreement는 명시적으로 남을 수 있다. Interface 단순화를 이유로 하나의 consensus state를 인위적으로 만들어서는 안 된다.

## 2. 왜 이 결정이 Consequential한가

이 boundary는 다음을 결정한다.

- 사용자의 investment judgment를 누가 소유하는가
- AI authority가 어디까지 확장될 수 있는가
- 향후 surface에서 `Stock_vis view`와 `my view`를 어떻게 구분하는가
- automation이 조용히 judgment 또는 decision authority가 될 수 있는가
- judgment history, personalization, comparison, alert, future agent가 authorship을 어떻게 다루는가
- Design Lab의 working direction인 “사용자의 judgment를 강화하되 대신하지 않는다”를 product에서 어떻게 운영하는가

따라서 이 결정은 장기적인 semantic / product architecture 영향이 크며 CEO authority가 필요하다.

## 3. Required Invariants

향후 Design work는 이 Decision Record가 명시적으로 수정되거나 supersede되기 전까지 다음 invariant를 보존해야 한다.

### 3.1 No Silent Attribution

System-generated synthesis는 단지 표시되거나 prefill되거나 자동 유지된다는 이유만으로 사용자의 판단으로 귀속되어서는 안 된다.

### 3.2 No Silent Overwrite

Material한 user-owned judgment는 system update에 의해 조용히 변경되어서는 안 된다.

### 3.3 Real User Control

User의 채택, 수정, 거절, qualification, delegation은 cosmetic interaction이 아니라 실제 user-owned judgment state에 causal effect를 가져야 한다.

### 3.4 Authorship Provenance

Material한 경우 system-authored, user-authored, adopted, modified, rejected, unresolved, delegated change를 experience가 해석 가능한 수준으로 구분할 수 있어야 한다.

이 record는 final authorship taxonomy까지 정하지 않는다.

### 3.5 Revision Lineage

Material한 judgment change는 무엇이, 왜, 누구의 action 또는 delegated authority를 통해 바뀌었는지 이해할 수 있는 history를 충분히 보존해야 한다.

### 3.6 Disagreement May Persist

System은 user judgment와 다른 synthesis를 유지할 수 있다. 하나의 clean state를 만들기 위해 agreement를 강제해서는 안 된다.

## 4. Delegation Boundary

이 결정은 사용자가 모든 evidence item, system observation, minor update, routine monitoring result를 하나씩 승인해야 한다는 뜻이 아니다.

System은 자신의 synthesis를 자동으로 유지하고 routine research, monitoring, prioritization, challenge를 자율적으로 수행할 수 있다.

User-owned judgment도 명시적으로 delegated rule을 통해 바뀔 수 있다. 단 그 delegation은:

- scope를 이해할 수 있고
- 되돌릴 수 있으며
- 추적 가능하고
- 일반적인 judgment authority를 system에 숨겨서 넘기는 방식이 아니어야 한다.

어떤 변경을 material judgment change로 볼지에 대한 정확한 threshold는 향후 Design / validation 문제로 남긴다.

## 5. Non-Decisions

이 결정은 다음 implementation / interaction choice를 의도적으로 고정하지 않는다.

- System Synthesis와 User Judgment를 실제 DB의 두 객체로 저장할지
- 두 화면, 한 화면, overlay, diff 또는 다른 표현으로 보여줄지
- `System Synthesis`, `Judgment Proposal`, `My View` 등의 최종 naming
- 정확한 component taxonomy 또는 기본 visible component 수
- 정확한 adopt / edit / reject interaction
- authorship provenance의 visual treatment
- selective cognitive friction의 precise threshold
- expert / novice disclosure 전략의 최종 형태

이들은 추후 consequential해지지 않는 한 delegated / reversible Design exploration으로 남는다.

## 6. Rationale and Alternatives

### Adopted Direction — Semantically Separated Co-authorship

AI가 대부분의 synthesis와 maintenance 노동을 수행하면서도 사용자의 judgment를 조용히 소유하지 않도록 할 수 있다.

Disagreement, provenance, revision history를 보존하면서 progressive하고 low-friction한 interaction design도 가능하다.

### Main Alternative — Single Shared AI-Maintained State with Provenance

하나의 shared state는 훨씬 단순하고 interaction cost도 낮을 수 있다. 강한 provenance와 쉬운 override만으로도 user agency를 충분히 보존할 가능성이 있다.

이 대안은 **Approved semantic authority boundary를 보존하는 한** prototype 비교 대상으로 계속 유효하다. 즉 시각적·물리적으로 하나의 state를 사용하더라도 system synthesis와 user-owned judgment가 의미상 구분되고 silent attribution / overwrite가 없어야 한다.

### Rejected Default — AI-Owned Judgment

System이 유지하는 judgment가 자동으로 사용자의 view가 되는 model은 이 approved authority boundary와 충돌한다.

## 7. Evidence and Origin

이 결정은 Workstream 001, Exploration Batch 03 — Judgment Structure Granularity & Human–AI Authorship Boundary에서 나왔다.

해당 exploration에서는 editability와 explanation이 perceived control / acceptance를 높일 수 있지만 independent judgment를 안정적으로 개선하지 않으며 automation bias나 illusion of control을 만들 수도 있다는 human–AI decision-support evidence를 검토했다. 따라서 Design Lab은 perceived control과 causal control을 구분하고 authorship provenance를 핵심 requirement로 본다.

참조:

- `design_lab/02_workstreams/001_investment_judgment_experience/batch_03_authorship_granularity.md`
- `research_lab/01_methodology/knowledge_and_understanding_framework.md` — Understanding, Decision Context, Judgment, Decision, Action의 upstream Research boundary

## 8. Failure / Reversal Conditions

다음과 같은 강한 real-user evidence가 나오면 이 결정을 명시적으로 재검토해야 한다.

- 사용자가 system synthesis와 user-owned judgment를 의미 있게 구분하지 못함
- semantic separation이 agency보다 confusion을 훨씬 크게 만듦
- 하나의 shared representation + strong provenance가 independent judgment를 실제로 보존하면서 usability를 크게 개선함
- authorship separation이 명확해도 system-generated structure가 harmful anchoring을 유발함
- 이 boundary가 useful automation을 크게 제한하지만 judgment quality / agency 개선은 거의 없음

수정은 Design Lab의 상위 Purpose와 Research–Design authority boundary를 보존해야 하며 consequential CEO-level decision으로 다뤄야 한다.

## 9. Downstream Constraint

향후 Judgment Experience, Thesis-like surface, monitoring, comparison, alert, personalization, portfolio decision support, AI agent behavior 작업은 이 Decision Record가 수정되거나 supersede되기 전까지 이를 Approved constraint로 취급한다.
