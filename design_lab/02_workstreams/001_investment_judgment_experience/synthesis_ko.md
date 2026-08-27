# Workstream 001 — Synthesis

> **한국어 Companion 문서**  
> 원문: [`synthesis.md`](synthesis.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Status:** Working Synthesis / Foundation promotion에 대한 CEO 결정 대기  
**Source Synced:** 2026-08-27  
**Synthesized:** 2026-08-27  
**Owner:** Stock_vis Design Lab

## 1. Executive Synthesis

Workstream 001은 다음 질문에서 시작했다.

> Stock_vis는 사용자의 investment judgment를 대신하지 않으면서 어떻게 처음 형성하고, 유지하고, 수정하고, 비교하고, 실제 판단에 사용하도록 도울 것인가?

6개의 exploration batch, adversarial scenario, Research Lab boundary check, 2개의 low-fidelity prototype을 거친 뒤 현재 가장 강하게 살아남은 방향은 다음이다.

> **Stock_vis는 각 투자대상에 대해 traceable하고 수정 가능한 Judgment Workspace를 유지하고, 사용자가 judgment-bearing change에 attention을 배분하도록 돕고, 최초 Formation과 ongoing revision을 상황에 맞는 깊이로 지원하며, Human–AI authorship boundary를 보존하고, Comparison / Portfolio reasoning은 forward scenario와 relative opportunity를 포함할 수 있는 downstream Decision Context에서 처리한다.**

이것은 **Design mental model + logical experience architecture**다. 최종 Product IA, navigation, 화면 이름, DB schema를 의미하지 않는다.

**Overall Recommendation Strength: Strong**

Very Strong이 아닌 이유는 real-user validation이 아직 부족하고, user-visible granularity가 미확정이며, future scenario / relative opportunity methodology는 Design Lab이 임의로 만들 수 없는 Research Lab 영역이 남아 있기 때문이다.

## 2. Recommended Problem Framing

### 추천 framing

핵심 문제는 단순한 정보 부족이나 `어떤 주식이 오를까?`가 아니다.

더 강한 formulation은:

> **투자자는 제한된 attention을 배분하고, 새로운 정보를 기존 expectation과 context에 대입해 해석하고, uncertainty 아래에서 belief를 수정하며, 왜 판단이 바뀌었는지를 보존하고, salience나 AI synthesis가 자신의 판단으로 조용히 바뀌지 않도록 하면서 현재 보유종목과 미래 대안을 비교해야 한다.**

따라서 Stock_vis가 지원해야 할 것은:

- attention allocation
- evidence-to-judgment traceability
- belief / judgment revision
- uncertainty와 unresolved state의 명시
- persistent judgment memory
- Human–AI authorship clarity
- Decision Context 아래의 forward-looking comparison
- company growth와 investment value의 구분

이다.

### 좁히거나 기각한 framing

#### More information이 핵심 해결책

불충분하다. 더 많은 정보는 overload, salience bias, reactive decision을 오히려 키울 수 있다.

#### News / event feed가 primary organizing object

Orientation / Trigger 역할로 축소했다. Event는 최근 발생했기 때문이 아니라 **현재 Judgment에 어떤 bearing이 있는가** 때문에 중요하다.

#### Judgment = 하나의 score 또는 bullish / bearish

기본값으로 기각했다. 중요한 component는 서로 다른 방향으로 움직일 수 있고 uncertainty / conviction도 다를 수 있다.

#### 고정된 linear user journey

축소했다. `Orient → Understand → Judge`는 shorthand로는 유용하지만 mandatory screen flow로는 살아남지 못했다.

## 3. Recommended Judgment Model

### 3.1 Investment Judgment는 maintained & revisable state

`state / structure / process 중 하나`를 고르는 문제로 보는 framing 자체를 기각했다.

더 강한 모델은:

> **Investment Judgment = internal structure를 가진 maintained state + 그것을 수정하는 update process + Decision Context에 따라 달라지는 downstream relevance**

이다.

필요한 경우 Maintained Judgment에는:

- 중요한 driver / claim
- risk / invalidation condition
- dependency / condition
- unresolved question / alternative
- local conviction / uncertainty
- System–User divergence
- material revision history

등을 포함할 수 있다.

### 3.2 Semantic Model과 Update Process는 분리한다

초기 모델은 object, relation, evaluation, process를 한 구조에 섞고 있었다.

현재 추천은:

1. **Judgment Semantic Model** — 무엇이 존재하고 어떻게 연결되는가
2. **Judgment Update Logic** — trigger가 maintained state를 어떻게 revise / retain / qualify / unresolved하게 만드는가

를 구분하는 것이다.

이는 Research Lab의 process–object separation과도 정합적이다.

### 3.3 System Synthesis와 User Judgment는 의미상 구분된다

이 부분은 이미 `DL-DR-0001 — Human–AI Judgment Authority Boundary`로 Approved 상태다.

AI는 자율적으로 research, synthesis, challenge, monitoring을 하고 **System Synthesis**를 업데이트할 수 있다. 그러나 material한 **User-owned Judgment**를 조용히 귀속하거나 덮어써서는 안 된다.

User의 명시적 판단이 아직 없는 것도 정상적인 상태다.

- 아직 view 없음
- partial view
- 일부 unresolved
- 일부는 system과 agreement
- 일부는 disagreement

가 모두 가능해야 한다.

## 4. Recommended Information Model

필요한 것은 peer information layer 목록이 아니라 서로 다른 의미를 가진 object와 relation이다.

### Maintained Judgment State

현재 구조화된 투자 판단.

### Update Trigger / Signal

재검토가 가치 있을 수 있음을 알리는 signal. Price move, news, time decay, competitor, portfolio context change, user question 등이 trigger가 될 수 있다.

Trigger 자체는 thesis 반증 evidence가 아니다.

### Reference / Interpretive Context

정보를 무엇과 비교해 해석하는지 나타내는 baseline. Prior judgment, prior expectation, guidance, consensus, peer, historical range, regime 등이 될 수 있다.

### Epistemic Input

Research Knowledge / Understanding과 관련 credibility, applicability, conflict, uncertainty, limitation.

Design은 이를 소비하고 표현하지 별도의 product-side epistemic authority를 만들어서는 안 된다.

### Judgment-Bearing Relation

다음 질문에 답하는 명시적 관계다.

> **이 정보가 현재 Judgment의 어느 부분에 실제로 영향을 주는가?**

Input은 support / challenge / qualify / narrow / broaden / uncertainty 증가 / 새로운 component 추가 / no meaningful bearing 등의 관계를 가질 수 있다.

### Judgment Impact

기존 `Significance / Materiality`를 더 정확하게 표현하는 Working Design concept다.

Judgment Impact는 정보 자체에 붙어 있는 fixed score가 아니라 **현재 Judgment에 대한 relational assessment**다.

매우 credible한 evidence도 peripheral component에 관한 것이면 impact가 작을 수 있다. 반대로 central driver에 관한 약한 conflicting evidence는 방향을 즉시 바꾸기보다 uncertainty를 높일 수 있다.

### Conviction / Uncertainty

Judgment direction과 분리하며, 가능하면 global scalar보다 affected component에 local하게 연결한다.

### Update Trace / Lineage

Material change가 생기면 무엇이, 왜, 무엇을 근거로, 어떤 reference 아래에서, 누구의 action / authority로 바뀌었는지 추적 가능해야 한다.

### Decision Context

Portfolio, horizon, alternatives, constraints, opportunity cost, switching cost 등의 decision-specific 조건은 company judgment와 구분된 downstream layer로 둔다.

## 5. Recommended Judgment Update Logic

현재 가장 강한 analytical loop는:

```text
Current Judgment State
+ Trigger / Signal
+ relevant Research Knowledge / Understanding
+ 필요할 경우 Decision Context
        ↓
Orient
        ↓
Contextualize
        ↓
Link to Judgment
        ↓
Assess Judgment Impact
        ↓
Revise / Retain / Mark Unresolved
        ↓
Recalibrate Conviction & Uncertainty
        ↓
Preserve Update Trace
        ↓
Updated Judgment State
```

이다.

이것은 mandatory UI sequence가 아니다.

Valid outcome은:

- strengthen
- weaken
- retain after review
- add / remove / qualify
- narrow / broaden
- conditional case로 split
- uncertainty 증가 / 감소
- unresolved
- suspend judgment
- not assessed

등이 될 수 있다.

`검토 후 유지`와 `아직 검토하지 않음`은 반드시 구분한다.

## 6. Recommended Logical Experience Architecture

`Adaptive Change Review`는 살아남았지만 전체 foundation이 아니라 broader architecture 안의 한 mode로 자리 잡았다.

현재 leading architecture는:

> **Persistent Judgment Workspace + Attention-Oriented Orientation + Formation / Maintenance + Adaptive Review + downstream Decision Context**

다.

```text
                       ORIENTATION
                "어디를 봐야 하지?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company   Cross-company need
         │                │                │
         ▼                ▼                ▼
     FORMATION        MAINTENANCE      DECISION CONTEXT
         │                │          comparison / portfolio
         │       simple change → inline
         │       complex/material → focused review
         │                │
         └───────────────┬┘
                         ▼
                JUDGMENT WORKSPACE
                  maintained state
                         │
              evidence / provenance
                         │
               update trace / history
```

### Orientation = News Feed가 아니라 Attention Allocation

여러 종목을 볼 때 raw activity가 아니라:

- current judgment에 material bearing
- consequential해진 unresolved uncertainty
- material System–User divergence
- user-defined monitoring condition

등을 우선한다.

**Attention item ≠ task ≠ approval request**다.

### Adaptive review depth

- user attention 가치 없음 → silent system maintenance
- simple / low-consequence bearing → inline annotation
- multi-component / conflict / consequential / material divergence → focused review
- allocation / comparison / rotation reasoning → user-initiated Decision Context

으로 깊이를 바꾼다.

## 7. Formation, Maintenance, Comparison

### 7.1 Formation

처음 보는 기업에는 prior User Judgment가 없다. 따라서 artificial `change`를 만들지 않고 System Synthesis + guided exploration에서 시작한다.

좋은 access question 후보는:

- 무엇이 가장 중요한가?
- 무엇 때문에 이 investment case가 깨질 수 있는가?
- 아직 무엇을 모르는가?
- 최근 무엇이 중요하게 변했는가?

이다.

User는 일부 component에 대해서만 view를 만들고 나머지는 unresolved로 둘 수 있다.

### 7.2 Maintenance

기존 보유종목은 change-driven orientation + adaptive review depth가 유리하다. 핵심은 current state의 continuity를 시간에 따라 보존하는 것이다.

### 7.3 Comparison은 Decision Context에 속한다

Comparison은 두 maintained judgment를 input으로 사용하고 underlying company judgment를 덮어쓰지 않는다.

비교에서는:

- 실제 comparable한 shared dimension
- company-specific asymmetric driver / risk

를 모두 보존한다.

Default comparison을 total score 하나로 압축하지 않는다.

## 8. Forward-Looking Comparison과 Rotation

실제 투자 비교는 inherently forward-looking하다는 결론이 강해졌다.

핵심 질문은 단순히 `오늘 어느 회사가 더 좋아 보이는가?`가 아니라:

> **가능한 미래에서 어느 투자가 더 강한 forward opportunity를 가지며, 무엇이 잘되어야 하고 무엇이 그 기회를 방해할 수 있으며, 그 상대적 차이가 capital allocation을 바꿀 만큼 충분히 크고 신뢰할 수 있는가?**

이다.

### 8.1 Future Scenario Structure

가능하면 하나의 deterministic future보다 conditional scenario를 우선한다.

```text
Possible Future
→ Growth Opportunity
→ Growth-Path Conditions
→ Company-specific response
→ Growth / Value Outcome
→ Relative Future Opportunity
```

### 8.2 Growth-Path Conditions

시장 opportunity가 자동으로 company growth가 된다고 가정하지 않는다.

Working Design structure는 다음을 구분한다.

- **Opportunity** — 외부 / 구조적 성장 가능성
- **Enablers** — opportunity를 실제로 가져가기 위해 필요한 조건
- **Accelerators** — growth speed / scale / economics를 높이는 조건
- **Bottlenecks / Delays** — thesis를 깨지는 않지만 성장 크기 / 시점을 제한하는 조건
- **Invalidation Conditions** — scenario 또는 핵심 growth mechanism을 materially 깨는 조건
- **Value-Capture Conditions** — business growth가 durable shareholder / per-share value로 전환되는 조건
- **Monitoring Signals** — 위 조건들이 실제로 강화 / 약화되는지 보여주는 evidence

이 구조는 Future Comparison과 기존 Judgment maintenance를 연결한다. New evidence는 Enabler를 강화하거나, Bottleneck을 악화하거나, Invalidation에 가까워지거나, Value Capture를 바꾸는 signal로 읽을 수 있다.

### 8.3 Growth 자체가 optimization target은 아니다

개념적으로:

```text
Business growth
+ growth-path durability / conditions
+ current valuation
+ capital requirement / dilution
+ downside / failure conditions
+ timing
+ uncertainty
→ Forward Investment Opportunity
```

`Forward Investment Opportunity`는 Working Design phrase이며 Approved Research term이 아니다.

### 8.4 Relative Opportunity Gap

Comparison은 alternative가 단순히 조금 더 좋은지, 아니면 실제 rotation을 deeper review할 만큼 충분히 좋은지를 구분해야 한다.

작은 apparent advantage가 자동 portfolio churn으로 이어져서는 안 된다.

이번 Workstream은 rotation threshold나 investment decision rule을 정의하지 않는다.

## 9. Starting Hypothesis에서 무엇이 바뀌었는가

### 유지

- More information보다 Better Judgment가 목표
- persistent judgment structure
- change / context / evidence / uncertainty / conviction의 중요성
- progressive disclosure
- comparison의 중요성
- Design은 judgment를 지원하되 대신하지 않음

### 수정

- `Judgment = Structure` → **maintained state + internal structure + update process under Decision Context**
- `Materiality` information layer → **relational Judgment Impact**
- linear 6-step journey → **analytical update loop, UI에서는 non-linear**
- `Adaptive Change Review` foundation → **broader Judgment Workspace 안의 adaptive review**
- current-state comparison → **forward scenario / relative opportunity comparison**
- generic growth risk → **explicit Growth-Path Conditions**

### 기본값으로 기각

- chronological news feed가 primary experience
- universal bullish / bearish label
- 하나의 global conviction / attractiveness score
- 항상 두 칼럼으로 System vs User 표시
- 모든 change가 review / approval 필요
- User가 full thesis를 작성해야만 가치 제공
- raw growth rate = investment opportunity
- deterministic future forecast가 default comparison

## 10. Design Knowledge Candidates

아래 finding은 여러 scenario에서 반복적으로 살아남아 reusable Design Knowledge 후보가 됐다. 하지만 자동 승격하지 않는다.

1. **Investment judgment는 episodic answer보다 maintained / revisable state로 다루는 것이 우세하다.** — Strong
2. **Semantic object와 update process를 분리한다.** — Strong
3. **Judgment relevance / impact는 intrinsic information score가 아니라 relation이다.** — Strong
4. **Orientation은 raw activity보다 judgment bearing을 기준으로 attention을 배분한다.** — Strong
5. **Review depth는 consequence에 따라 adaptive해야 한다.** — Strong
6. **User Judgment는 absent / partial / unresolved / disagreement 상태를 가질 수 있다.** — Strong. Human–AI authorship boundary는 DL-DR-0001로 이미 Approved.
7. **Decision Context는 underlying company judgment와 분리한다.** — Strong
8. **Comparison은 shared + asymmetric structure를 동시에 보존한다.** — Strong
9. **Forward Comparison은 forecast 결과뿐 아니라 scenario condition과 growth blocker를 보여준다.** — Strong
10. **Default scalar rank는 traceable relative trade-off와 uncertainty보다 하위에 둔다.** — Moderate–Strong

다음 promotion 단계에서 무엇을 `03_design_knowledge/`로 옮길지, 어떤 항목이 CEO approval을 필요로 하는지 결정한다.

## 11. Research Trigger Candidates

### Trigger 1 — Future Scenario / Relative Opportunity Methodology

> **Future scenario, Growth-Path Condition, predictive growth/value outcome, Relative Opportunity Comparison을 downstream Design과 Portfolio Decision Support에서 사용할 만큼 충분히 강하게 생성·평가하려면 Research Lab에 어떤 methodology가 필요한가?**

여기에는 필요에 따라:

- scenario construction
- predictive probability
- forecast calibration
- expected growth / return estimation
- valuation-outcome mapping
- probability weighting
- uncertainty aggregation
- Growth-Path Condition의 causal / predictive status
- predictive / comparative Claim의 epistemic evaluation

이 포함될 수 있다.

Design Lab은 이를 어떻게 보여주고 비교할지는 연구할 수 있지만 epistemic authority를 정의해서는 안 된다.

### Trigger 2 — Downstream Decision-Support Methodology

Research Lab Evaluation Methodology는 Decision-Support Evaluation을 향후 downstream family로 이미 인식하고 있다. Stock_vis가 Judgment Support에서 Comparative / Portfolio Decision Support로 확장될 경우, Research truth와 product recommendation rule을 섞지 않으면서 downstream reasoning을 어떻게 warrant / evaluate할지 Research methodology가 필요할 수 있다.

## 12. Failure / Reversal Conditions

다음 evidence가 나오면 architecture를 수정한다.

- persistent judgment structure가 continuity보다 harmful anchoring을 더 크게 만듦
- authorship treatment가 있어도 User가 System Synthesis와 자신의 view를 구분하지 못함
- adaptive depth가 unpredictable하거나 중요한 정보를 과도하게 숨김
- focused review가 새로운 inbox burden이 됨
- Judgment-Bearing Relation이 너무 artificial / costly함
- revision lineage가 complexity를 정당화할 만큼 유용하지 않음
- Formation / Maintenance / Decision Context가 하나의 contextual universal page보다 fragmented하게 느껴짐
- Future Scenario가 calibrated understanding보다 false confidence를 만듦
- Growth-Path taxonomy가 cognitive load만 증가시킴
- Relative Opportunity framing이 불필요한 portfolio churn을 유도
- Research Lab이 predictive / comparative reasoning에 materially 다른 architecture를 제시

## 13. Design Lab Evolution Findings

현재 Design Lab Operating Model은 이번 Workstream에서 큰 문제 없이 작동했다.

주요 운영 learning:

- Batch exploration이 CEO micro-consensus를 줄이면서 consequential escalation은 보존했다.
- Workstream이 커지면서 Batch별 파일 분리가 필요해졌고, 하나의 monolithic exploration file보다 review가 쉬웠다.
- 한국어 companion은 CEO review 속도를 실제로 높였으므로 consequential Design 문서의 기본 운영으로 유지하는 것이 좋다.
- Prototype은 conceptual discussion에서 보이지 않던 failure를 발견하는 데 큰 가치가 있었다. 특히 literal Change Review foundation의 한계를 Prototype에서 확인했다.
- 새로운 permanent governance나 agent taxonomy를 추가할 이유는 현재 없다.

따라서 현재 Design Lab 구조 자체의 structural change는 필요 없다.

## 14. Decision Package

### Recommended Structure

다음 구조를 downstream Product Surface / IA exploration을 위한 **leading Investment Judgment Experience Foundation**으로 가져가는 것을 추천한다.

> **Persistent & revisable Judgment Workspace**  
> + **Attention-oriented Orientation**  
> + **동일 semantic model을 공유하는 Formation / Maintenance**  
> + **Consequence-adaptive review depth**  
> + **Research / Evidence / authorship / revision lineage traceability**  
> + **Company Judgment와 구분된 downstream Decision Context**  
> + **Scenario, Growth-Path Conditions, Valuation, Uncertainty, Relative Opportunity를 사용하는 forward-looking Comparison**

### Recommendation Strength

**Strong**

### Why

현재까지 다음 scenario를 가장 넓게 통과했다.

- prior user judgment 없음
- thesis change 없는 급락
- mixed earnings
- material Human–AI disagreement
- 여러 보유종목 Morning Review
- cross-company comparison
- possible portfolio rotation

또한 Approved Research–Design boundary와 DL-DR-0001 Human–AI authority boundary를 보존한다.

### Main Alternatives

1. **Event / Feed-centered product** — orientation은 단순하지만 judgment continuity와 differentiation이 약함
2. **One integrated universal Judgment Home** — navigation cost는 낮지만 complex multi-component change / comparison에서 overload 위험
3. **AI-maintained single shared thesis** — user effort는 낮지만 semantic authorship를 매우 조심스럽게 보존해야 함
4. **Score / Ranking-centered Comparison** — 빠르지만 false symmetry / false precision / hidden trade-off 위험

### Key Trade-offs

- continuity vs anchoring
- traceability vs complexity
- adaptive disclosure vs predictability
- user agency vs interaction burden
- structured comparison vs cognitive load
- forward usefulness vs false precision
- opportunity optimization vs portfolio churn

## 15. Batch Consensus

CEO decision, real-user evidence, Research authority가 반박하지 않는 한 다음을 **Working Consensus**로 유지하는 것을 추천한다.

- maintained / revisable judgment core mental model
- Semantic Model과 Update Process 분리
- Judgment-Bearing Relation + relational Judgment Impact
- default global scalar보다 local conviction / uncertainty
- traceable update lineage
- attention-oriented Orientation
- adaptive review depth
- DL-DR-0001에 따른 System Synthesis ≠ User Judgment
- Decision Context와 company judgment 분리
- explicit Growth-Path Conditions를 포함한 forward-looking Comparison
- default total score / automatic rotation rule 없음

## 16. CEO Critical Decision — Foundation Promotion

### 결정할 것

위에서 synthesis한 core mental model을 **다음 Product Surface / IA Workstream의 Working Design Foundation으로 받아들일 것인가?**

단, 모든 component를 Approved Design Knowledge로 승격하거나 최종 Product IA로 고정하는 것은 아니다.

### Design Lab Lead Recommendation

**Working Foundation으로 승인하고, 계속 falsifiable하게 유지하는 것을 추천한다.**

### Recommendation Strength

**Strong**

### 왜 CEO 판단인가

이제는 local interaction detail이 아니라 향후 Dashboard / Company Surface / Comparison / Portfolio / Monitoring IA가 어떤 mental model에서 파생될지를 결정하는 수준이기 때문이다.

하지만 이번 승인은 **Working Foundation**이므로 permanent Product IA를 잠그거나 모든 용어를 durable knowledge로 승인하는 것보다 훨씬 reversible하다.

### Strongest Counterargument

Real user가 persistent judgment model을 실제로 원하거나 잘 사용할 수 있다는 evidence가 충분하지 않은 상태에서 Stock_vis가 투자 판단을 과도하게 구조화할 위험이 있다. 더 단순한 AI research + alert + comparison experience가 훨씬 낮은 learning cost로 대부분의 가치를 제공할 수도 있다.

### Failure / Reversal Conditions

다음이 prototype / user test에서 확인되면 Working Foundation 승인을 재검토한다.

- persistent structured judgment가 harmful anchoring을 만듦
- 사용자에게 maintenance work처럼 느껴짐
- AI opinion과 User Judgment의 차이가 이해되지 않음
- comparison / revision quality를 실제로 개선하지 못함
- simpler episodic experience보다 materially 덜 유용함

## 17. Deferred / AI-Owned

다음은 consequential해지지 않는 한 계속 delegated / reversible detail로 둔다.

- Judgment Workspace / Formation / Maintenance / Change Review / Judgment Impact / Relative Opportunity Gap의 최종 naming
- exact component taxonomy / visible component count
- conviction / uncertainty / provenance / divergence visual treatment
- adaptive-review precise threshold
- explicit mode navigation인지 one surface의 contextual state인지
- Morning Review grouping / ranking detail
- Comparison visual layout
- exact Growth-Path Condition label
- aggregate comparison summary의 유용성
- mobile interaction
- implementation / storage schema
