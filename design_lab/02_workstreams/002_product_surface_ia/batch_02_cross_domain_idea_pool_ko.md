# Workstream 002 — Batch 02: Cross-Domain Analogical Benchmark & Idea Pool

> **한국어 Companion 문서**  
> 원문: [`batch_02_cross_domain_idea_pool.md`](batch_02_cross_domain_idea_pool.md)  
> 이 문서는 영어 canonical document를 빠르게 검토하기 위한 한국어 companion이며 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; Approved Product IA / Design Knowledge 아님

## 1. 왜 이 Batch를 추가하는가

Workstream 002는 Workstream 001의 Research-aligned foundation을 바탕으로 Product Surface / IA 후보를 좁히기 시작했다. 그런데 CEO feedback을 통해 중요한 위험이 확인됐다.

> Design Lab이 현재 Stock_vis 개념과 기존 금융서비스 관습 안에서 너무 빨리 수렴할 수 있다.

따라서 IA를 더 잠그기 전에 exploration을 다시 넓힌다.

목표는 유명 서비스의 예쁜 화면을 모으는 것이 아니다. **Stock_vis와 구조적으로 비슷한 판단 문제를 푸는 다른 분야의 사고법·정보구조·interaction pattern을 추출하고, 무엇이 전이 가능하고 무엇은 전이하면 안 되는지 구분한 뒤, 조합 가능한 Idea Pool을 만드는 것**이다.

이 접근은 Research Lab과도 정합적이다. Research Lab은 object와 process를 분리하고, uncertainty와 competing alternatives를 보존하며, comparative / predictive / design-oriented question과 adversarial analysis를 허용한다.

## 2. Analogical Search Principle

다음과 같은 구조를 공유하는 분야를 우선적으로 본다.

- evidence가 불완전하고 계속 변함
- 여러 explanation / future가 경쟁함
- uncertainty 아래에서 판단해야 함
- 시간과 attention이 제한됨
- context / provenance가 중요함
- 한 번의 답보다 반복 update가 중요함
- false certainty의 비용이 큼
- analysis와 action을 구분해야 함
- Human–AI collaboration이 중요함
- 과거 decision / outcome에서 학습할 필요가 있음

화면이 비슷하다는 것만으로는 transfer evidence가 약하다.

## 3. Idea Pool Card

각 pattern은 최소한 다음을 기록한다.

- **Source domain / service**
- **원래 해결하는 cognitive problem**
- **Observed pattern**
- **왜 Stock_vis로 transfer 가능할 수 있는가**
- **무엇은 transfer하면 안 되는가**
- **Stock_vis translation candidate**
- **Main risk / anti-pattern**
- **Test scenario**
- **현재 strength** — Tentative / Moderate / Strong

Idea Pool은 아이디어 생성 도구이지 Governance가 아니다. 여기에 들어갔다고 Design Principle이나 IA가 되지 않는다.

## 4. 초기 Source Family

### 4.1 투자 research / trading / portfolio tools

대표 서비스:

- AlphaSense
- Koyfin
- TradingView
- FinChat 등 AI-first investment research tool

볼 가치가 있는 구조:

- 여러 종목 monitoring과 한 기업 deep work의 분리
- company-centric research hub
- watchlist / portfolio라는 persistent coverage set
- configurable alert
- screener를 통한 opportunity discovery
- 현재 research context 안에서 작동하는 AI
- customizable dashboard / saved view

현재 benchmark signal:

- AlphaSense는 Company Profile을 single-company research hub로 두고, Dashboard / alert는 broader monitoring을 담당한다. Generative Search도 현재 company, dashboard widget, 선택 document를 context로 그대로 가져간다.
- Koyfin은 watchlist, portfolio, dashboard, alert, screener의 사용자 customization을 강하게 지원한다.
- TradingView는 watchlist-wide alert, screener, custom condition을 강하게 제공하며 AI로 screening 조건을 만들 수도 있다.

Stock_vis transfer 후보:

- Orientation과 single-investment workspace는 다른 책임을 가져야 할 가능성이 높다.
- AI는 별도 generic AI 페이지보다 현재 investment / evidence scope를 상속하는 것이 유리하다.
- saved monitoring logic은 사용자 attention layer가 될 수 있다.
- Screener / Discovery가 반드시 top-level destination일 필요는 없다.

피해야 할 것:

- feature / tool sprawl
- metric abundance 자체가 IA가 되는 구조
- judgment relevance보다 activity를 최적화한 alert
- 사용자가 무엇이 중요한지 알기도 전에 customization을 요구하는 구조

### 4.2 임상 진단학 / Clinical Decision Support

대표 서비스 / 접근:

- VisualDx
- Isabel DDx
- UpToDate / UpToDate Pathways / Expert AI

이 analogy가 강한 이유:

임상진단은 흔히 다음과 같이 생각한다.

```text
현재 증상 / 상태
→ problem representation
→ differential hypothesis
→ 구별에 도움이 되는 evidence / test
→ 가능성 update
→ 위험한 대안 보존
→ 환자 context에서 다음 행동 결정
```

투자 reasoning과 구조적으로 유사하다.

```text
기업 / 시장 상태
→ 현재 Investment View
→ competing explanation / future
→ 구별에 도움이 되는 evidence
→ view / uncertainty 수정
→ invalidation alternative 보존
→ Decision Context에서 Judgment
```

관찰된 pattern:

- VisualDx는 finding을 추가/삭제하면 differential이 계속 변하고 finding과 diagnostic possibility의 관계를 보이게 한다.
- Isabel은 patient context / clinical feature에서 넓은 differential을 만들어 premature closure를 막는 safety net 역할을 한다.
- UpToDate는 evidence-grounded answer, interactive pathway, abnormal lab interpretation, AI clinical reasoning을 point-of-care workflow 안에서 제공한다.

Stock_vis transfer 후보:

- **Differential View:** 하나의 thesis만이 아니라 competing investment explanation / scenario를 유지
- **Discriminating Evidence:** preferred view를 지지하는 정보보다 alternative를 실제로 구분하는 evidence 강조
- **Must-not-miss analogue:** 가능성은 낮아도 손실이 큰 failure path를 명시적으로 보존
- **Problem Representation:** 세부정보 전에 현재 investment situation을 짧게 표현
- **Guided Pathway:** uncertainty / consequence가 큰 경우 structured decision support를 제공하되 user Judgment를 대체하지 않음

직접 transfer하면 안 되는 점:

- disease와 investment는 다르다.
- 진단은 하나의 causal diagnosis를 찾는 경우가 많지만 투자에서는 여러 explanation이 동시에 true일 수 있다.
- 임상에는 validated care pathway가 존재하지만 Stock_vis가 투자 decision rule을 임의로 만들면 안 된다.

Main risk:

Research methodology가 warrant하지 않았는데 differential을 probability ranking처럼 보여주는 것.

### 4.3 확률적 Forecasting / Prediction

대표 서비스:

- Metaculus
- Good Judgment Open / Superforecasting

관찰된 pattern:

- vague language가 아니라 explicit probability / distribution을 사용
- evidence가 바뀌면 prediction을 계속 수정
- 이전 forecast가 reality와 비교 가능하게 history로 남음
- resolution criterion이 명확함
- central forecast와 disagreement / uncertainty를 분리 가능
- calibration / proper scoring을 통해 장기 prediction quality를 평가

Stock_vis transfer 후보:

- **Scenario Timeline:** 현재 예상뿐 아니라 미래 예상이 어떻게 변했는지 보임
- **Explicit uncertainty:** Research가 warrant할 때 range / distribution 표현
- **Reaffirmation:** `검토했고 그대로`와 `오래돼서 안 봄`을 구분
- **Disagreement View:** system / user / alternative model 차이를 보존
- **Resolution / Learning Loop:** reality가 나온 뒤 과거 scenario assumption을 다시 평가

직접 transfer하면 안 되는 점:

- 투자질문은 clean binary resolution date가 없는 경우가 많다.
- 주가 outcome은 business growth + valuation + path dependence가 섞인다.
- forecast probability ≠ Research credibility ≠ investment attractiveness.

Main risk:

false precision / probability fetishism.

### 4.4 Intelligence Analysis / Operational Decision System

대표 platform:

- Palantir Foundry / Ontology-aware applications
- object / link investigation 계열 도구

관찰된 pattern:

- page가 아니라 real-world object / relationship이 semantic center
- Object View가 information, linked object, metric, analysis, workflow의 hub
- exploratory application과 workflow-specific application을 분리
- data / logic / action / decision lineage를 연결하되 같은 object로 collapse하지 않음
- Human / AI action을 traceable하게 관리

Stock_vis transfer 후보:

- **Investment Object Hub:** 기업 / 투자 object가 data, relationship, Investment View, evidence, scenario, contextual action을 anchor
- **Explore vs Decide Separation:** 관계 탐색이 자동으로 action workflow가 되지 않게 함
- **Contextual Capability:** ChainSight 같은 network exploration을 투자 object / question에서 열 수 있게 함
- **Decision Lineage:** material Judgment / Decision 당시 사용된 data / logic / context를 보존

직접 transfer하면 안 되는 점:

- enterprise ontology는 consumer IA가 아니다.
- ontology complexity를 user complexity로 노출하면 안 된다.
- action model이 있다고 trading execution system으로 바로 가면 안 된다.

Main risk:

experience보다 ontology를 먼저 만드는 과설계.

### 4.5 Incident Response / Observability

대표 서비스:

- PagerDuty
- Datadog Incident Management

이 analogy가 유용한 이유:

운영팀도 많은 signal, 제한된 attention, uncertain cause, 빠르게 변하는 evidence 속에서 routine noise와 deep review가 필요한 incident를 구분해야 한다.

관찰된 pattern:

- alert / signal이 먼저 triage되고 모두 incident가 되지는 않음
- incident는 bounded focused review unit이 됨
- timeline이 언제, 무엇이, 누구에 의해 바뀌었는지 보존
- post-incident review가 history를 learning으로 변환
- AI가 timeline / root cause / follow-up을 draft해도 human이 refine / govern

Stock_vis transfer 후보:

- **Orientation / Triage:** 많은 변화 중 일부만 focused attention으로 승격
- **Focused Review Object:** mixed earnings / major thesis conflict / material divergence를 temporary analytical episode로 처리
- **Timeline / Lineage:** event → interpretation → Investment View revision 보존
- **Post-decision Review:** Decision이 왜 이루어졌고 이후 Reality가 무엇을 보여줬는지 평가

직접 transfer하면 안 되는 점:

- investment는 incident가 아니다.
- urgency 중심 UX는 short-termism과 salience bias를 키울 수 있다.

Main risk:

Stock_vis를 alert / task inbox로 만드는 것.

## 5. 초기 Cross-Domain Pattern Pool

### P1 — Orientation / Triage

**Source:** clinical urgency, incident response, investment monitoring  
**Stock_vis:** 어디에 attention을 쓸 가치가 있는지 우선순위를 정하되 low-priority item도 접근 가능하게 둠.  
**Strength:** Strong

### P2 — Persistent Object Workspace

**Source:** Palantir Object View, AlphaSense Company Profile, clinical patient context  
**Stock_vis:** 하나의 investment object가 current state, relationship, evidence, Investment View, change, relevant workflow를 anchor.  
**Strength:** Strong

### P3 — Differential / Competing Explanations

**Source:** diagnosis, intelligence analysis  
**Stock_vis:** 하나의 clean narrative 대신 competing thesis / explanation / scenario를 유지.  
**Strength:** Strong conceptually; representation open

### P4 — Discriminating Evidence

**Source:** diagnosis, hypothesis testing, Research Lab warrant structure  
**Stock_vis:** preferred view를 지지하는 evidence만이 아니라 중요한 alternative의 상대 가능성을 실제로 바꾸는 evidence를 강조.  
**Strength:** Strong

### P5 — Adaptive Review Depth

**Source:** incident escalation, clinical work-up, Workstream 001  
**Stock_vis:** 단순한 변화는 inline, conflict / consequence가 큰 경우 focused review.  
**Strength:** Strong

### P6 — Explicit Forecast Revision

**Source:** Metaculus / forecasting  
**Stock_vis:** scenario / expectation history를 보존하고 `reviewed unchanged`와 `stale`을 구분.  
**Strength:** Moderate–Strong; Research methodology dependency

### P7 — Uncertainty / Disagreement as First-Class State

**Source:** forecasting, diagnosis, Research Lab Understanding  
**Stock_vis:** unresolved alternative와 system–user divergence를 forced consensus 없이 보존.  
**Strength:** Strong

### P8 — Context-Preserving AI

**Source:** AlphaSense scoped GenSearch, UpToDate workflow  
**Stock_vis:** AI가 별도 generic destination이 아니라 현재 investment / evidence / comparison context에서 작동.  
**Strength:** Strong

### P9 — Decision Lineage / Postmortem

**Source:** Palantir decision data, Datadog timeline, PagerDuty post-incident review, forecasting track record  
**Stock_vis:** material Judgment / Decision 시점에 무엇을 알았고 무엇을 선택했고 이후 무엇이 일어났는지 보존.  
**Strength:** Moderate–Strong

### P10 — Exploration vs Workflow-Specific Mode

**Source:** Palantir exploratory vs workflow app, clinical search vs pathway, investment discovery vs Decision Context  
**Stock_vis:** open Explore와 constrained Decision Context가 underlying object는 공유하더라도 다른 interaction mode일 수 있음.  
**Strength:** Strong; Workstream 002에 직접 중요

## 6. 조합 실험 후보

### C1 — Clinical Differential × Investment View

```text
Current Investment View
+ Competing Explanation / Scenario
+ Discriminating Evidence
+ Invalidation / Must-not-miss condition
```

가치: premature narrative closure를 줄일 수 있음.

### C2 — Incident Triage × Morning Investment Orientation

```text
많은 signal
→ low-priority collapse
→ attention-worthy item
→ 필요할 때만 focused review
```

가치: news / alert overload 감소.

### C3 — Forecast Timeline × Future Opportunity Comparison

```text
Scenario / expectation
→ probability 또는 qualitative confidence (warrant될 때)
→ 시간에 따른 update
→ disagreement
→ 실제 outcome / learning
```

가치: 미래 reasoning을 revisable하고 accountable하게 만듦.

### C4 — Palantir Object View × ChainSight × Company Workspace

```text
Investment Object
├ current view
├ linked entity / relationship
├ evidence
├ changes
├ scenarios
└ contextual Explore
```

가치: relationship exploration이 disconnected tool이 아니라 context-aware capability가 됨.

### C5 — UpToDate Pathway × Stock_vis Decision Context

```text
Decision question
→ relevant context
→ key alternative
→ evidence / uncertainty
→ consequence / unresolved point
→ User Judgment
```

가치: silent recommendation authority 없이 structured decision support 가능.

### C6 — Incident / Forecast Postmortem × Investment Decision Journal

```text
당시 무엇을 알았는가?
나는 / system은 무엇을 믿었는가?
어떤 alternative를 버렸는가?
어떤 Decision을 했는가?
실제로 무엇이 일어났는가?
무엇을 배워야 하는가?
```

가치: hindsight reconstruction을 줄이고 repeated judgment quality를 개선할 가능성.

## 7. Workstream 002에 주는 의미

이제 즉시 IA를:

> D1 `Orientation / Investment / Decision Context`
> vs
> D2 `Orientation / Investment / Explore / Decision Context`

만으로 좁혀서는 안 된다.

먼저 다음 **cognitive responsibility**가 persistent product space인지, contextual capability인지, temporary review mode인지 테스트해야 한다.

1. Orientation / triage
2. Persistent investment-object work
3. Open exploration / relationship discovery
4. Differential / scenario reasoning
5. Material change의 focused review
6. Comparison / Decision Context
7. Historical learning / postmortem
8. Contextual AI

이렇게 해야 기존 금융서비스 메뉴를 그대로 따라가지 않는 IA가 나올 수 있다.

## 8. Operating Recommendation

Workstream 002 동안 임시 **Cross-Domain Pattern Pool**을 exploration tool로 사용한다.

지금 별도 영구 Governance나 formal pattern library를 만들지는 않는다.

```text
Stock_vis Design / Research constraint
        +
Analogous domain reasoning
        +
Benchmark service pattern
        ↓
transferable primitive 추출
        ↓
아이디어 조합
        ↓
경쟁 IA / interaction prototype 생성
        ↓
adversarial stress-test
        ↓
keep / modify / reject
```

여러 Workstream에서 반복적으로 재사용 가치가 확인될 때만 formal Design Pattern / Analogical Knowledge 구조를 만든다.

**Recommendation Strength: Very Strong**

## 9. Failure / Reversal Conditions

다음 문제가 나타나면 이 접근을 축소하거나 수정한다.

- analogy research가 prototype 지연 핑계가 됨
- screenshot catalog만 쌓이고 cognitive pattern을 추출하지 못함
- domain 차이를 무시한 false equivalence
- idea가 너무 많아 synthesis가 어려워짐
- 외부 product convention이 Stock_vis / Research constraint를 덮어씀
- 여러 batch에서 cross-domain combination이 prototype 품질을 개선하지 못함

## 10. CEO Critical Decision

**없음.**

Workstream 002 내부의 reversible exploration method이며, consequential convergence 전에 broad delegated exploration을 수행한다는 Design Lab 운영 원칙과 직접 정합된다.
