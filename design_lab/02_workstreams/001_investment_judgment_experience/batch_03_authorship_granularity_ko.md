# Workstream 001 — Exploration Batch 03

> **한국어 Companion 문서**  
> 원문: [`batch_03_authorship_granularity.md`](batch_03_authorship_granularity.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-26  
**Status:** Working  
**Date:** 2026-08-26  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Mixed — granularity는 Tier 2 working architecture, human/AI authorship boundary에는 Tier 1 / CEO Critical question 포함

## Judgment Structure Granularity & Human–AI Authorship Boundary

## 1. Purpose

이번 Batch는 서로 연결된 두 질문을 검토한다.

1. **Judgment Structure Granularity** — maintained judgment structure를 어느 정도까지 명시적으로 표현할 것인가? 그리고 기본 화면에서 어디까지 보여주고 어디부터 progressive disclosure로 내릴 것인가?
2. **Human–AI Authorship Boundary** — maintained judgment의 어떤 부분을 system과 user가 생성, 제안, 수정, 채택, 소유할 수 있는가?

목표는 screen이나 interaction detail을 확정하는 것이 아니다. 사용자가 research ontology를 직접 유지해야 하는 부담 없이도 user agency를 보존할 수 있는 working boundary를 만드는 것이다.

이번 Batch는 Batch 01과 Batch 02의 다음 working model을 전제로 한다.

> Investment judgment는 내부 구조를 가진 maintained and revisable state이며, evidence-driven process를 통해 decision context 아래에서 업데이트된다.

## 2. Authority Boundary

Research Knowledge, Understanding, Evidence, credibility, applicability 및 관련 Research Concept의 authority는 계속 Research Lab에 있다.

이번 Batch는 Research 측 Judgment의 의미를 재정의하지 않는다. Downstream에서 사용자가 investment judgment를 유지하는 경험과 authorship boundary를 연구한다.

현재 Design Lab working philosophy 중 다음이 직접 관련된다.

> **사용자의 판단 능력을 강화하되 판단을 대신하지 않는다.**

따라서 system synthesis가 사용자의 judgment로 조용히 바뀌거나 귀속되는 mechanism은 특히 강하게 검토해야 한다.

## 3. External Evidence — Human Control은 실제로 무엇을 하는가?

### 3.1 Editability와 control은 수용을 높일 수 있지만 더 좋은 judgment를 보장하지 않는다

여러 human–AI 연구에서 사용자가 AI recommendation을 조정하거나 선택할 수 있게 하면 perceived autonomy, trust, understanding, system adoption이 증가할 수 있다. 그러나 control이 decision accuracy를 자동으로 높이지는 않는다.

검토한 주요 evidence:

- Fink, Newman & Haran (2024), *Let me decide: Increasing user autonomy increases recommendation acceptance* — choice / control autonomy가 recommendation acceptance를 증가시킴.  
  https://www.sciencedirect.com/science/article/pii/S0747563224001122
- Sele & Chugunova (2024), *Putting a human in the loop: Increasing uptake, but decreasing accuracy of automated decision-making* — algorithm recommendation을 monitor하고 수정할 수 있게 하면 이용 의향은 높아졌지만, 큰 오류를 적절히 수정하는 비율이 낮았고 실험에서 최종 정확도는 오히려 감소.  
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298037
- Westphal et al. (2023), *Decision control and explanations in human-AI collaboration* — decision control은 trust / understanding / compliance를 개선했지만 explanation은 task complexity를 높였고 user 특성에 따라 부정적 영향도 가능.  
  https://www.sciencedirect.com/science/article/abs/pii/S0747563223000651

**Working implication:** edit button 자체는 agency의 충분한 정의가 아니다. 사용자의 accept / edit / reject가 실제 user-owned state에 causal effect를 가져야 하고, system proposal과 user judgment의 차이가 읽혀야 한다.

### 3.2 Editable AI reasoning은 illusion of control을 만들 수 있다

2026 CHI 연구에서는 표시된 AI reasoning을 수정할 수 있게 했을 때 perceived power, control, satisfaction은 증가했지만 accuracy improvement는 없었다. Read-only reasoning은 잘못된 AI에 대한 inappropriate reliance를 증가시켰고, editability도 실제 recommendation에 causal effect가 없을 경우 illusion of control을 만들 수 있었다.

Reference:

- *Understanding the Affordances of Control in AI Reasoning for Human-AI Decision-Making* (CHI EA 2026).  
  https://doi.org/10.1145/3772363.3798555

**Working implication:** Stock_vis는 **perceived control과 causal control을 구분**해야 한다. 사용자가 judgment component를 수정·채택·거절·qualify하면 실제 user-owned judgment state가 traceable하게 바뀌어야 한다.

### 3.3 Explanation만으로 independent judgment가 보존되지는 않는다

Automation bias / AI advice 연구에서는 explanation이 trust나 advice-taking을 높일 수 있지만 appropriate reliance를 안정적으로 개선하지 못한다는 결과가 반복된다.

Relevant evidence:

- Buçinca, Malaya & Gajos (2021), *To Trust or to Think* — cognitive forcing이 simple explainable-AI 방식보다 overreliance를 줄였지만 usability / subjective preference 비용이 있었음.  
  https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca2021trust.shtml
- Vered et al. (2023), *The effects of explanations on automation bias* — explanation이 automation bias를 안정적으로 제거하지 못함.  
  https://www.sciencedirect.com/science/article/pii/S000437022300098X
- *Cognitive Forcing for Better Decision-Making: Reducing Overreliance on AI Systems Through Partial Explanations* (2025) — partial/full explanation이 잘못된 AI에 대한 overreliance를 줄일 수 있지만 task 및 user 특성에 따라 효과가 달라짐.  
  https://doi.org/10.1145/3710946

**Working implication:** user authorship 보존은 AI reasoning을 보여주는 것만으로 부족하다. 사용자가 독립적으로 judgment를 형성, 유지, 거부, 수정할 수 있는 구조가 필요하다.

## 4. Granularity Evidence

### 4.1 모든 구조를 한 번에 노출하면 cognitive / information-load 위험이 있다

Complex disclosure는 user error 및 자기 processing ability에 대한 overconfidence를 증가시킬 수 있고, financial decision research에서도 task와 interface가 만드는 cognitive load가 memory와 decision quality를 떨어뜨린다는 결과가 있다.

References:

- Jin, Luca & Martin (2021/2022), *Complex Disclosure*.  
  https://pubsonline.informs.org/doi/10.1287/mnsc.2021.4037
- *Affective responses to financial data and multimedia: the effects of information load and cognitive load*.  
  https://www.sciencedirect.com/science/article/abs/pii/S1467089504000053

### 4.2 의미 있는 disaggregation은 이해를 개선할 수 있다

Nonprofessional investor 대상 financial-reporting experiment에서는 complex item을 meaningful component로 disaggregate할 경우 component가 economic event와 judgment에 어떻게 연결되는지 더 잘 이해하는 결과가 있었다.

Reference:

- *The effects of the method used to present a complex item on the face of a financial statement on nonprofessional investors' judgments*.  
  https://www.sciencedirect.com/science/article/pii/S0882611016300116

**Working implication:** maximal compression도 maximal decomposition도 답이 아니다. Judgment-relevant distinction은 보존할 만큼 분해하되, 모든 component를 동시에 읽도록 강제하지 않아야 한다.

### 4.3 Progressive disclosure가 현재 가장 강한 presentation direction이다

최근 HCI 연구는 progressive / on-demand disclosure가 information load를 관리하면서 understanding을 개선할 수 있음을 보여주며, 필요한 transparency depth는 expert와 non-expert에서 의미 있게 달랐다.

References:

- Muralidhar, Belloum & Ashok (2025), *Operationalizing selective transparency using progressive disclosure in artificial intelligence clinical diagnosis systems*.  
  https://www.sciencedirect.com/science/article/pii/S107158192500148X
- *Exploratory search with generative AI: An empirical study on the impact of interaction design strategies on information exploration and cognitive load* (2026).  
  https://www.sciencedirect.com/science/article/pii/S1071581926000467

**Working implication:** expert / novice에게 처음부터 별도 mental model을 만들기보다 하나의 underlying judgment model을 유지하고 disclosure depth를 달리하는 접근이 더 강하다.

## 5. Competing Authorship Models

### 5.1 AI-Owned Judgment

System이 canonical investment judgment를 만들고 계속 업데이트하며, user는 주로 inspect하거나 선택적으로 수정한다.

**Strengths**
- user effort 최소
- continuity / monitoring 우수
- automatic alert / update 구현이 쉬움

**Failure modes**
- system synthesis가 사실상 user belief가 됨
- anchoring / automation bias 위험 큼
- system이 틀렸을 때 accountability 불명확
- “사용자 판단을 강화하되 대신하지 않는다”는 Design direction과 충돌

**Current judgment:** primary user-judgment model로는 기각.

### 5.2 User-Authored Judgment Only

User가 judgment를 직접 만들고 유지하며 AI는 evidence, suggestion, critique만 제공한다.

**Strengths**
- authorship 명확
- user agency / accountability 강함
- silent AI attribution 최소화

**Failure modes**
- interaction burden 큼
- time-constrained / less-experienced user에게 약함
- spreadsheet / note-taking 작업을 다시 만들 위험
- user가 유지하지 않으면 continuity 실패

**Current judgment:** default로는 부담이 너무 큼.

### 5.3 AI가 User Judgment에 직접 Draft하고 User가 수정 가능

AI가 기본적으로 judgment를 유지하며 user가 component를 edit / override할 수 있다.

**Strengths**
- maintenance burden 낮음
- continuity 강함
- collaboration처럼 보임

**Failure modes**
- default effect로 AI-authored content가 조용히 user belief로 귀속될 수 있음
- editability가 independent judgment 없는 perceived control만 만들 수 있음
- 실제 user가 무엇을 채택한 것인지 불명확

**Current judgment:** AI-owned보다 낫지만 provenance가 아직 약함.

### 5.4 Separated Co-authorship / Dual-State Model

System은 명시적인 **System Synthesis / Judgment Proposal**을 유지하고, user는 구분되는 **User Judgment State**를 가질 수 있다. AI는 addition, update, challenge, conviction change를 제안할 수 있지만 이를 user에게 조용히 귀속하거나 user state를 덮어쓰지 않는다.

User는 명시적으로:

- proposed component를 채택
- 수정
- 거절
- unresolved로 남김
- system challenge에도 기존 view 유지
- user-only component 생성

을 할 수 있다.

System synthesis는 user와 disagreement가 있어도 독립적으로 계속 업데이트될 수 있다.

**Strengths**
- authorship provenance 명확
- AI가 대부분의 structural labor를 수행하면서도 user judgment를 소유한 척하지 않음
- disagreement 및 user vs system comparison 가능
- update lineage 보존
- expert / time-constrained user 모두 다양한 authorship depth 지원 가능

**Failure modes**
- 두 state가 cognitive confusion을 만들 수 있음
- confirmation prompt가 많아지면 product-level micro-consensus가 됨
- passive user는 여전히 rubber-stamp 가능
- system synthesis가 truth처럼 보이지 않도록 naming / framing 주의 필요

**Current judgment:** 가장 강한 model.

**Recommendation Strength:** Strong.

## 6. Recommended Working Authorship Boundary

현재 추천은 다음과 같다.

> **AI는 investment judgment를 생성하고, 구조화하고, challenge하고, update를 제안할 수 있다. 그러나 AI proposal을 사용자의 judgment로 조용히 귀속하거나 덮어써서는 안 된다. System synthesis와 user-owned judgment는 구분되어야 하며, material adoption / revision에는 authorship provenance와 lineage가 남아야 한다.**

이것은 user가 모든 evidence item이나 minor update를 하나씩 승인해야 한다는 뜻이 아니다.

Working distinction:

```text
Research Knowledge / Understanding
        ↓
System Synthesis / Judgment Proposal
        ↓ can propose
User Judgment State
        ↓ contributes to
Decision Context and later Decision
```

System은 자신의 synthesis를 자동으로 업데이트할 수 있다. User state는 meaningful user action 또는 scope가 명시되고 reversible한 delegated rule을 통해서만 바뀌는 방향이 현재 가장 안전하다.

## 7. Consequence-Proportional Human Engagement

모든 AI contribution 전에 user가 독립 judgment를 먼저 만들도록 강제하면 friction이 너무 크다. 반대로 모든 consequential moment에서 AI conclusion을 즉시 먼저 보여주면 anchoring과 overreliance가 증가할 수 있다.

따라서 현재 가장 강한 방향은 universal precommitment가 아니라 **selective cognitive friction**이다.

더 강한 user engagement가 정당화될 수 있는 high-consequence moment 예시:

- AI가 제안한 material judgment change를 user-owned state에 채택
- user view와 strong contrary evidence 사이의 major conflict 해결
- core driver / risk를 active ↔ invalid 등으로 크게 변경
- conflicting / uncertain evidence 아래에서 conviction을 material하게 변경
- judgment review에서 consequential portfolio decision으로 넘어가는 순간

Routine monitoring, orientation, evidence browsing은 가볍게 유지한다.

Cognitive forcing 연구에서는 overreliance를 줄이는 효과와 함께 subjective preference 감소 및 user 차이가 확인되어, universal rule보다 consequence-proportional rule을 지지한다.  
https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca2021trust.shtml

## 8. Recommended Granularity Model

Semantic structure는 **default visible surface보다 더 풍부하게 유지**한다.

### Layer A — Judgment Snapshot

현재 view를 이해하는 데 필요한 작은 material judgment component set만 먼저 보여준다.

Important driver / claim, risk, unresolved uncertainty, meaningful recent change 등이 후보가 될 수 있다. Design Lab은 아직 universal count를 3개, 5개, 7개처럼 고정하지 않는다.

### Layer B — Component Detail

필요할 때 각 component에서 다음을 확장한다.

- current direction / state
- local conviction / uncertainty
- 중요한 supporting / challenging input
- 최근 update가 왜 영향을 줬는지
- dependency / condition
- material한 경우 system vs user authorship / adoption status

### Layer C — Evidence / Provenance / Update Trace

더 깊게 내려가면 Research Knowledge, conflicting evidence, historical revision, material change의 actor / reason까지 trace한다.

이 layered model은 ontology-like full graph를 항상 노출하지 않으면서 semantic structure를 보존한다.

## 9. Expertise and Personalization

현재 evidence만으로 expert와 less-experienced user가 서로 다른 foundational judgment model을 가져야 한다고 볼 근거는 부족하다.

더 강한 starting hypothesis는:

> **same underlying semantic model, different disclosure depth and control density.**

가능한 차이는:

- expert에게 evidence / provenance direct access 강화
- less-experienced user에게 guided question / summary 강화
- default depth user configuration
- advanced comparison / assumption / dependency expansion

정도다. Real-user validation이 필요하다.

## 10. Scenario Stress Test

### Time-constrained holder

AI가 system synthesis를 유지하고 material change만 surface한다. User가 모든 component를 수동 유지할 필요가 없다.

**Result:** dual-state + progressive disclosure survives.

### Strong independent thesis를 가진 expert investor

Evidence를 직접 확인하고, system synthesis와 disagreement를 유지하고, custom component를 만들고, AI update가 기존 thesis를 자동 overwrite하지 않게 할 수 있다.

**Result:** AI-owned / simplified single-state보다 잘 버팀.

### Less-experienced user

AI structure가 judgment formation을 scaffold할 수 있지만 system view를 user conclusion처럼 표현해서는 안 된다. Guided adoption + progressive detail이 burden을 줄일 수 있다.

**Result:** survives. 다만 authorship distinction 이해 가능성은 user test 필요.

### 큰 drawdown 뒤 confirmation을 찾는 user

System은 contrary evidence와 disagreement를 보존할 수 있고, user state를 자동 rewrite하지도 user position을 그대로 mirror하지도 않는다.

**Result:** confirmation-bias 방어에 유리.

### AI synthesis가 material하게 틀림

User는 proposal을 reject할 수 있고 user-owned judgment는 오염되지 않는다. System이 무엇을 왜 제안했는지는 provenance로 남긴다.

**Result:** single auto-maintained state보다 안전.

### Passive / buck-passing user

모든 proposal을 그냥 accept할 수 있다. Editability만으로 해결되지 않는다. Consequence-proportional friction / challenge 필요.

**Result:** partial survival. 주요 validation risk로 유지.

## 11. Failure / Reversal Conditions

다음이 real-user validation에서 확인되면 추천을 수정해야 한다.

- user가 system synthesis와 user judgment를 이해하거나 의미 있게 구분하지 못함
- 두 state 유지가 agency보다 confusion을 더 크게 만듦
- explicit adoption mechanism이 심각한 abandonment / maintenance failure를 만듦
- user가 사실상 하나의 shared state를 강하게 선호하고 provenance metadata만으로 authorship 보존이 충분함
- state를 분리해도 system-generated structure가 anchoring을 크게 증가시킴
- judgment structure가 routine monitoring에 너무 복잡함
- progressive disclosure가 아니라 expert / novice에게 다른 semantic model 자체가 필요함

## 12. Batch Consensus

### Recommended Working Architecture

1. Rich underlying judgment structure를 보존하되 progressively expose한다.
2. Default visible judgment component 수를 지금 고정하지 않는다.
3. Expert / novice용 별도 foundational model을 만들기 전에 하나의 semantic model + variable disclosure depth를 우선한다.
4. Editability를 agency의 충분조건으로 보지 않고 real causal control과 authorship provenance를 요구한다.
5. 모든 interaction에 independent judgment를 강제하지 않고 selective / consequence-proportional cognitive friction을 사용한다.
6. System–user disagreement를 하나의 consensus state로 강제하지 않고 보존한다.

**Recommendation Strength:** Strong.

## 13. CEO Critical Decision — Human / AI Judgment Authority Boundary

### Decision

Stock_vis가 다음 boundary를 working product-authority direction으로 채택할지 CEO가 직접 판단할 필요가 있다.

> **AI는 System Synthesis / Judgment Proposal을 생성·구조화·challenge하고 지속적으로 업데이트할 수 있다. 그러나 이를 user의 investment judgment로 조용히 덮어쓰거나 귀속해서는 안 된다. User Judgment State는 구분되어야 하며, material change에는 meaningful user adoption / editing / rejection 또는 scope가 명시된 reversible delegated rule이 필요하다.**

### 왜 CEO Critical Decision인가

이건 interaction detail이 아니라 다음을 장기적으로 결정한다.

- core investment judgment의 owner가 누구인가
- AI authority가 어디까지인가
- 향후 `내 판단`과 `Stock_vis의 view`를 product surface에서 어떻게 구분하는가
- automation이 조용히 decision authority로 변할 수 있는지
- judgment history, personalization, comparison, alert, future agent behavior가 어떤 구조에 의존하는가

### Design Lab Lead Recommendation

**위 boundary를 Working human–AI authority direction으로 채택한다.**

**Recommendation Strength: Strong**

### Strongest Counterargument

Dual-state는 불필요하게 복잡할 수 있다. Clear provenance와 easy override가 있는 하나의 AI-maintained shared judgment만으로도 더 단순하고 engagement가 높은 product를 만들 수 있으며, user는 별도의 judgment state를 공식적으로 유지하고 싶어 하지 않을 수 있다.

### 왜 Very Strong은 아닌가

User가 분리된 User Judgment State를 실제로 이해하고 가치 있게 느끼는지 real-user evidence가 아직 없다. Single shared state에 strong provenance, editable components, reversible system updates를 결합해도 agency를 충분히 보존하면서 interaction cost를 크게 줄일 가능성이 있다.

### Failure / Reversal Condition

Prototype에서 user가 single shared state 안에서도 authorship을 일관되게 이해하고 agency를 유지하며, dual-state가 usability / continuity를 material하게 해친다는 것이 확인되면 architecture를 단순화한다.

## 14. Deferred / AI-Owned

현재 CEO 결정이 필요하지 않은 항목:

- `System Synthesis`, `Judgment Proposal`, `My View` 등 실제 naming
- authorship provenance의 visual marker
- default visible component 정확한 수
- adoption이 button, inline editing, diff review 등 어떤 interaction으로 이루어지는지
- advanced expert control
- selective cognitive friction의 정확한 trigger threshold
- detailed judgment component taxonomy

이들은 authority boundary가 결정된 뒤 prototype에서 탐색한다.
