# Workstream 001 — Exploration Batch 04

> **한국어 Companion 문서**  
> 원문: [`batch_04_interaction_architecture.md`](batch_04_interaction_architecture.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 CEO-approved semantic intent와 관련 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — 승인된 DL-DR-0001 아래의 Working interaction architecture

## Judgment Experience Interaction Architecture

## 1. Purpose

이번 Batch는 현재까지 만든 judgment semantics를 실제 interaction architecture로 번역한다. 아직 product navigation, screen 이름, 최종 Design System을 고정하지 않는다.

핵심 질문은 다음이다.

> **사용자가 attention, understanding, system synthesis, user-owned judgment, revision, decision context 사이를 어떻게 오가야 낮은 interaction cost와 승인된 Human–AI authority boundary를 동시에 보존할 수 있는가?**

이번 Batch는 다음을 전제로 한다.

- Batch 01 — investment judgment는 decision context 아래에서 유지·수정되는 structured state
- Batch 02 — judgment semantic model과 judgment update process 분리
- Batch 03 — progressive disclosure와 의미상 분리된 human–AI co-authorship
- `DL-DR-0001 — Human–AI Judgment Authority Boundary`

아직 최종 product IA가 아니다.

## 2. Approved Constraint

DL-DR-0001은 다음을 요구한다.

- system synthesis가 조용히 user judgment가 되어서는 안 됨
- material한 user-owned judgment 변경에는 meaningful user action 또는 명시적이고 reversible하며 traceable한 delegated rule 필요
- system–user disagreement는 남을 수 있음
- authorship provenance와 material update lineage는 해석 가능해야 함
- semantic distinction만 보존된다면 물리적으로 항상 두 state를 side-by-side로 보여줄 필요는 없음

따라서 이번 Batch는 이 boundary를 다시 논의하지 않고 그 안에서 interaction을 최적화한다.

## 3. External Pattern Review

### 3.1 Monitoring + AI research의 경쟁 기준은 이미 높다

현재 금융 research product는 monitoring을 AI-assisted research에 직접 연결하는 방향으로 발전하고 있다.

AlphaSense의 2026년 업데이트에는 automated monitoring, thesis checking / validation / refresh / postmortem Workflow Agents, cited AI synthesis, always-current report, agent-driven research workflow가 포함된다. Koyfin도 watchlist / portfolio 단위에서 price, valuation, technical, news, filing, transcript alert와 관련 research navigation을 제공한다.

References:

- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/53942181071123-AlphaSense-Product-Updates-July-2026
- https://www.koyfin.com/features/alerts/

**Working implication:** `alert → research → AI summary`만으로는 Stock_vis의 distinctive interaction architecture가 되기 어렵다. 더 강한 기회는 변화를 maintained, traceable judgment state와 연결하는 것이다.

### 3.2 Fixed turn-taking보다 Mixed-initiative interaction이 더 적합하다

최근 human–AI research는 human과 AI가 각자 더 잘할 수 있는 순간에 initiative를 가져가는 mixed-initiative collaboration을 중요하게 다룬다.

이는 Stock_vis에서도 system이 monitoring과 proposal을 자율적으로 수행하고, user는 consequential한 순간에 질문·redirect·disagreement 유지·control을 가져가는 구조를 지지한다.

References:

- Natarajan (2025), *Adaptive Agents for Mixed-Initiative Human-AI Collaborations*: https://doi.org/10.1609/aaai.v39i28.35220
- Hu et al. (2025), *Human at the Center: A Framework for Human-Driven AI Development*: https://onlinelibrary.wiley.com/doi/10.1002/aaai.70043
- Holter, Moruzzi & El-Assady (2026), *Toward Agency in Human-AI Collaboration*: https://doi.org/10.1109/MCG.2025.3623892

**Working implication:** `AI가 항상 먼저` 또는 `user가 항상 먼저`를 강제하지 않는다. Initiative는 task와 consequence에 따라 달라져야 한다.

### 3.3 Interruptive alert가 너무 많으면 attention value를 파괴할 수 있다

Clinical decision support의 alert fatigue research는 금융 제품의 직접 evidence는 아니지만 interaction warning으로 유용하다. Individual alert가 technically relevant하더라도 너무 잦거나 low-value한 interruption은 response quality와 engagement를 낮출 수 있다.

References:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC12310297/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13385993/

**Working implication:** Stock_vis는 모든 detected change를 interruptive judgment-review request로 만들면 안 된다. System initiative는 judgment impact, uncertainty, novelty, consequence에 따라 filtering되어야 한다.

### 3.4 Structured deliberation은 open question과 disagreement 보존에 유리하다

최근 deliberation interface들은 chronological chat만 쓰는 대신 structured summary, open question, argument map, explicitly managed context를 사용한다.

이는 maintained judgment structure가 persistent object가 되고 conversation은 접근·조작 mechanism이 되는 방향을 지지한다.

References:

- Turkstra et al. (2026), *ARGSBASE*: https://aclanthology.org/2026.eacl-demo.39/
- Li et al. (2026), *Mixed-Initiative Context*: https://arxiv.org/abs/2604.07121

## 4. Competing Interaction Architectures

### 4.1 Feed-First / Event-First

Primary experience가 news, alert, earnings, price move, AI summary stream이다. 사용자는 event에서 deeper research로 들어가고 필요하면 judgment를 수정한다.

**Strengths**
- orientation과 immediacy가 강함
- learning cost 낮음
- mobile / daily monitoring에 자연스러움
- 익숙한 market-product pattern

**Failure modes**
- judgment가 아니라 episodic event가 organizing object가 됨
- salience가 materiality를 지배할 수 있음
- long-term judgment memory 보존 약함
- 사용자가 반복해서 `나는 지금 이 회사를 어떻게 보고 있지?`를 재구성해야 함
- 기존 alert / research product와 차별화 약함

**Current judgment:** entry mechanism으로는 유용하지만 foundational architecture로는 기각.

### 4.2 Judgment-Home / State-First

Primary experience가 maintained judgment snapshot이다. 사용자는 current drivers, risks, uncertainty, conviction, disagreement를 먼저 보고 evidence나 change를 연다.

**Strengths**
- continuity / memory 강함
- judgment structure를 first-class로 만듦
- evidence-to-judgment traceability 우수
- deliberate review에 강함

**Failure modes**
- system synthesis가 너무 authoritative하거나 static하게 느껴질 수 있음
- 여러 holding을 빠르게 morning review하기 약함
- 중요한 신규 event가 state 안에 묻힐 수 있음
- novice는 어디서 시작할지 어려울 수 있음
- existing structure에 anchoring될 위험

**Current judgment:** persistent state로는 필요하지만 유일한 entry pattern으로는 무거움.

### 4.3 Change-Review Queue / Diff-First

System이 material change queue를 만든다. 각 review에서 무엇이 변했고, 어떤 judgment component가 영향받고, system이 어떤 revision을 제안하는지와 evidence를 보여주며 accept / modify / reject / defer를 제공한다.

**Strengths**
- judgment updating을 직접 operationalize
- provenance / lineage 강함
- existing holding monitoring에 매우 적합
- system proposal과 user adoption 구분 명확

**Failure modes**
- inbox / review fatigue
- 신규 기업 initial formation에 약함
- 모든 meaningful change가 task처럼 느껴질 수 있음
- repeated proposal rubber-stamp 위험
- maintained state가 queue보다 secondary가 됨

**Current judgment:** 가장 강한 update mechanism이지만 전체 experience로는 부족.

### 4.4 Permanent Side-by-Side Dual State

System Synthesis와 User Judgment를 항상 side-by-side column이나 parallel view로 보여준다.

**Strengths**
- authorship clarity 최대
- disagreement가 명확
- diff / comparison 이해 쉬움

**Failure modes**
- visual / cognitive complexity 두 배
- 두 complete state가 항상 있어야 한다는 잘못된 전제 유발
- 대부분 agreement하거나 user view가 비어 있어도 human–AI conflict를 과도하게 강조
- time-constrained monitoring에 약함
- semantic authority boundary가 UI burden으로 변함

**Current judgment:** local diff / disagreement interaction으로는 유용하지만 always-on primary architecture로는 기각.

### 4.5 State-Centered, Change-Driven, Mixed-Initiative Hybrid

System은 persistent judgment structure를 유지하지만, 사용자는 주로 material change, recurring question, direct company exploration을 통해 진입한다. Human과 system의 initiative는 바뀔 수 있고, human–AI divergence는 material할 때만 surface한다.

**Current judgment:** 가장 강한 architecture.

**Recommendation Strength:** Strong.

## 5. Leading Working Architecture

현재 추천을 한 문장으로 요약하면:

> **State는 지속적으로 유지하고, meaningful change 또는 user question을 통해 진입하며, material implication을 context 안에서 review하고, human–AI authorship / disagreement는 필요한 곳에만 드러낸다.**

Conceptual interaction architecture:

```text
                    ┌─────────────────────┐
                    │  Orientation Layer  │
                    │ meaningful changes  │
                    │ questions / search  │
                    └─────────┬───────────┘
                              │
                 user or system initiative
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Judgment Snapshot   │
                    │ current maintained  │
                    │ state + recent diff │
                    └──────┬───────┬──────┘
                           │       │
                 inspect   │       │ review change
                           │       │
                           ▼       ▼
                ┌─────────────┐  ┌──────────────────┐
                │ Component   │  │ Change Review    │
                │ Detail      │  │ impact + proposal│
                └──────┬──────┘  └────────┬─────────┘
                       │                  │
                       ▼                  ▼
                ┌─────────────┐   adopt / modify /
                │ Evidence /  │   reject / retain /
                │ Provenance  │   defer / unresolved
                └──────┬──────┘          │
                       │                  ▼
                       └─────────► Updated User State
                                      + lineage

Decision Context는 comparison, portfolio constraint, horizon,
opportunity cost, action relevance가 필요할 때 별도 overlay / mode로 들어온다.
```

이 diagram은 logical interaction role이지 최종 screen이 아니다.

## 6. Interaction Roles

### 6.1 Orientation Layer — `무엇에 attention을 써야 하는가?`

이 layer에서는 system initiative가 가능하다.

우선순위 후보:

- judgment-bearing change
- 중요한 unresolved evidence conflict
- applicability / regime change
- material uncertainty 변화
- user-requested monitoring target
- 필요할 경우 decision-context 변화

Raw event volume 자체가 목적이 아니다.

Price move, filing, headline은 judgment change가 아니라 trigger일 수 있다.

**Interaction principle candidate:** `결론을 따르라고 보여주기보다, 왜 확인해야 하는지를 보여준다.`

### 6.2 Judgment Snapshot — `현재 어디에 서 있는가?`

현재 investment view의 persistent memory다.

Default exposure는 compact하고 progressive해야 한다. 예를 들어:

- 현재 가장 material한 judgment component
- unresolved / weak area
- material recent change
- 유용한 경우 local conviction / uncertainty
- material component에서 system–user divergence 존재 여부
- user가 아직 explicit view를 만들지 않았는지 여부

System component가 모두 user에게 채택된 것처럼 보여서는 안 된다.

### 6.3 Change Review — `무엇이 변했고, 무엇에 영향을 주며, 내 판단이 바뀌어야 하는가?`

핵심 judgment-update interaction이다.

하나의 review unit은 다음을 표현할 수 있어야 한다.

1. **Trigger** — 무엇이 review를 시작했는가
2. **Reference / Context** — 무엇과 비교했는가
3. **Research Input** — material Knowledge / Understanding / evidence state
4. **Judgment Bearing** — 어떤 component가 영향받는가
5. **System Assessment** — strengthen / weaken / qualify / unresolved / no material change 등
6. **System Proposal** — system synthesis update와 별도의 user proposal
7. **User Response** — material한 경우 adopt / modify / reject / retain / defer / unresolved
8. **Lineage** — 무엇이 왜 material하게 바뀌었는가

User-owned change가 없다면 user가 review를 승인할 필요가 없어야 한다.

### 6.4 Component Detail — `왜 현재 이렇게 보고 있는가?`

전체 semantic model을 항상 보여주지 않고 judgment-bearing structure를 자세히 확인하는 layer다.

다음이 들어갈 수 있다.

- supporting / challenging input
- unresolved alternative
- condition / dependency
- local conviction / uncertainty
- relevant update history
- material한 authorship / adoption status
- direct questioning / exploration entry

### 6.5 Evidence / Provenance / Update Trace — `검증하고 재구성할 수 있는가?`

Authoritative Research output과 material history까지 추적하는 deeper layer다.

Conversation은 follow-up question에 사용할 수 있지만, judgment가 왜 존재하는지에 대한 memory가 chat에만 남아서는 안 된다.

### 6.6 Decision Context — `현재 선택에서 이 judgment는 어떤 의미인가?`

Portfolio, horizon, alternatives, concentration, opportunity cost, constraints는 comparison이나 action에 필요할 때 들어온다.

Decision Context가 intrinsic company judgment를 조용히 rewrite하면 안 된다.

향후 comparison / rotation / portfolio workflow로 확장할 수 있다.

## 7. Mixed-Initiative Rules

Leading architecture는 consequence-proportional initiative를 사용한다.

### System initiative가 적합한 경우

- monitoring / candidate change detection
- evidence organize / prioritize
- judgment-bearing link proposal
- unresolved conflict / uncertainty surface
- System Synthesis update
- material change review 제안

### User initiative가 우선인 경우

- user-only judgment component 생성 / 유지
- material judgment change를 user-owned state로 채택
- system proposal reject / modify
- decision context / personal constraint 표현
- disagreement 유지
- 실제 investment decision으로 넘어갈지 결정

### Shared initiative가 적합한 경우

- clarification
- alternative explanation exploration
- conviction recalibration
- comparison
- 어떤 추가 evidence가 judgment를 바꿀지 탐색

## 8. Formation vs Update

두 경우를 지원하되 foundation model을 두 개 만들지 않는다.

### New / unfamiliar company — Formation path

```text
Question / Discovery
→ System Synthesis of current structure
→ material drivers / risks / uncertainties
→ evidence exploration
→ user may adopt, modify, reject, or leave components unowned
→ partial User Judgment State emerges over time
```

Prior thesis가 없어도 사용할 수 있다.

### Existing holding — Update path

```text
Monitoring trigger
→ Judgment-bearing change detected
→ Change Review
→ current component + evidence + proposed impact
→ user involvement only when material to user-owned judgment
→ updated state + lineage
```

Formation과 update는 같은 semantic model을 공유하고 entry path만 다르다.

## 9. Scenario Stress Test

### 9.1 여러 holding의 Morning Review

Feed-first는 수십 개 alert를 보여줄 수 있다. Hybrid는 meaningful judgment impact 또는 unresolved risk가 있는 candidate change만 우선 surface하고 raw event stream은 별도 접근 가능하게 둔다.

**Result:** survives. Alert prioritization은 중요한 향후 evaluation 문제.

### 9.2 큰 주가 하락, 새 fundamental evidence 없음

Price move는 orientation trigger가 될 수 있다. 하지만 system은 큰 market move가 있었지만 material Research update는 아직 확인되지 않았다고 표현할 수 있다.

User는 thesis 약화라는 결론을 강요받지 않고 조사할 수 있다.

**Result:** magnitude ≠ judgment impact를 보존.

### 9.3 Mixed Earnings

여러 judgment component가 서로 다른 방향으로 움직일 수 있다. Change Review에서 affected component와 local revision을 보여주고 하나의 earnings verdict로 collapse하지 않는다.

**Result:** feed-first / scalar summary보다 잘 버팀.

### 9.4 System과 User가 material하게 disagreement

Judgment Snapshot은 affected component에만 divergence를 표시하고 필요할 때 local diff / compare를 연다. 두 complete state를 permanent column으로 보여줄 필요가 없다.

**Result:** DL-DR-0001을 lower cognitive cost로 보존.

### 9.5 User가 explicit judgment를 아직 만들지 않음

System Synthesis는 존재할 수 있지만 User Judgment는 absent / partial일 수 있다. Structure를 채우기 위해 user view를 만들어내면 안 된다.

**Result:** false attribution 방지.

### 9.6 User가 review proposal을 반복해서 무시

System은 pending review를 더 많은 notification으로 escalation하지 않는다. System Synthesis는 계속 업데이트할 수 있고, 적절한 review moment에 deferred / unreviewed material divergence를 summary할 수 있다.

**Result:** conceptually survives. Notification / review burden calibration은 validation 필요.

### 9.7 신규 opportunity와 기존 holding 비교

각 asset은 maintained judgment structure를 그대로 reuse한다. Decision Context가 portfolio / opportunity-cost comparison을 추가하고 underlying company judgment는 변형하지 않는다.

**Result:** survives. Comparison interaction은 후속 Batch / Workstream.

## 10. Key Design Risks

### 10.1 Review Inbox가 또 다른 일이 됨

AI change마다 user adoption을 요구하면 Stock_vis가 product-level micro-consensus를 재현한다.

Mitigation direction: user-owned judgment를 material하게 바꾸는 경우만 user action 요구. 낮은 consequence update는 summary.

### 10.2 System Synthesis가 User를 Anchoring

Semantic separation이 있어도 system view가 attention을 지배할 수 있다.

Mitigation direction: selective cognitive friction, explicit uncertainty / disagreement, user-authored component, consequential moment에서 ordering / reveal timing 실험.

### 10.3 Persistent State가 stale / overgrown

Maintained judgment가 obsolete component를 축적할 수 있다.

Mitigation direction: applicability check, component lifecycle, periodic compression / retirement, stale / unresolved를 silent delete 대신 표현.

### 10.4 Materiality Filter가 Novelty를 숨김

System은 현재 이해한 structure를 기준으로 prioritization하기 때문에 novel / weakly linked evidence가 잘못 suppress될 수 있다.

Mitigation direction: unexplained / unusual change용 secondary discovery path 유지, prioritization 이유 노출.

### 10.5 Conversation이 Structure를 대체

Chat은 유연하지만 memory와 provenance를 fragment할 수 있다.

Mitigation direction: conversation은 persistent structured object를 inspect / manipulate하는 수단이고 sole state store가 되면 안 됨.

## 11. Batch Consensus

### Recommended Working Interaction Architecture

Prototype exploration의 leading Working direction으로 다음을 채택하는 것을 추천한다.

> **State-centered, change-driven, mixed-initiative judgment experience with progressive disclosure.**

이 architecture는:

1. persistent judgment state 유지
2. meaningful change와 user question을 common entry point로 사용
3. raw alert나 mandatory approval queue가 아니라 Change Review를 core update interaction으로 사용
4. compact Judgment Snapshot을 항상 접근 가능하게 유지
5. deeper evidence / provenance / history는 on-demand
6. human–AI divergence는 permanent duplicated state가 아니라 material한 부분에 local하게 표시
7. Decision Context는 distinct comparison / action layer로 호출
8. Formation과 Update는 같은 semantic model 위의 다른 entry path로 지원

**Recommendation Strength:** Strong.

## 12. Main Alternative

### Judgment-Home with Integrated Change Diff

더 단순한 대안은 Judgment Snapshot을 company experience의 중심으로 두고 최근 변화도 별도 Change Review mode 없이 state 안에서 integrated diff로 처리하는 방식이다.

**Why it remains credible**
- interaction concept 수가 적음
- product navigation이 더 단순할 수 있음
- review-queue 느낌을 피함
- provenance / local diff 보존 가능

**현재 2순위인 이유**
- 여러 holding의 attention handling이 약함
- `새 signal requiring review`와 `existing state` 구분이 약함
- important update가 묻히거나 state가 noisy해질 위험

Prototype에서는 계속 비교 대상으로 유지한다.

## 13. Failure / Reversal Conditions

다음이 prototype / user testing에서 확인되면 leading architecture를 수정한다.

- user가 Judgment Snapshot과 Change Review 차이를 이해하지 못함
- change-driven entry가 task / inbox fatigue를 유발
- explicit review보다 direct state editing을 압도적으로 선호
- system-first change presentation이 approved authority boundary에도 불구하고 harmful anchoring을 만듦
- persistent structured judgment 유지 비용이 decision value보다 큼
- Decision Context와 company judgment를 의미 있게 분리하기 어려움
- simpler Judgment-Home architecture가 훨씬 낮은 interaction cost로 동등하거나 더 좋은 judgment quality를 만듦

## 14. Deferred / AI-Owned

다음은 reversible exploration detail로 남긴다.

- Orientation, Judgment Snapshot, Change Review, Component Detail, System Synthesis 최종 naming
- screen 수 / navigation 위치
- mobile vs desktop arrangement
- divergence, uncertainty, authorship, material change visual language
- exact review action / microcopy
- notification cadence / bundling
- component count / hierarchy
- Change Review가 page, drawer, card, timeline item, inline diff 중 무엇인지
- conversation placement

## 15. CEO Critical Decision

**이번 Batch에는 없음.**

이미 승인된 Human–AI judgment authority boundary 아래에서 reversible한 Tier 2 working architecture다. Major product IA를 잠그기 전에 prototype과 test를 거치는 것이 맞다.

## 16. Next Recommended Step

추상 architecture에서 **low-fidelity interaction prototype / wireflow** 단계로 이동한다.

Stress scenario 후보:

1. 큰 주가 하락이 있었지만 confirmed thesis change는 없는 held stock
2. 서로 다른 judgment component를 강화·약화하는 mixed earnings
3. material system–user disagreement
4. first-time company exploration / judgment formation
5. portfolio / watchlist morning monitoring

최소 두 architecture를 비교한다.

- leading state-centered + change-driven hybrid
- simpler Judgment-Home + integrated diff alternative

목표는 visual polish가 아니다. **comprehension, attention cost, authorship clarity, review burden, 사용자가 왜 judgment가 바뀌었는지 재구성할 수 있는가**를 검증하는 것이다.
