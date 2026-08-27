# Workstream 001 — Synthesis

> **한국어 Companion 문서**  
> 원문: [`synthesis.md`](synthesis.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립 authority를 만들지 않는다. 의미 차이가 생기면 CEO-approved semantic intent와 관련 Design / Research authority를 기준으로 두 문서를 정합시킨다.

**Status:** Working Design Foundation / Research-aligned  
**Source Synced:** 2026-08-27  
**Synthesized:** 2026-08-27  
**Semantic Alignment:** DL-DR-0002 effective 2026-08-27  
**Owner:** Stock_vis Design Lab

## 1. Executive Synthesis

Workstream 001은 Stock_vis가 사용자의 판단을 대신하지 않으면서 투자대상에 대한 view를 형성하고, 유지하고, 수정하고, 비교하고, 실제 decision에 사용하도록 어떻게 도울지를 탐색했다.

6개의 exploration batch, adversarial scenario, Research Lab consistency check, low-fidelity prototype을 거친 뒤 현재 leading direction은 다음과 같다.

> **Stock_vis는 각 투자대상에 대해 추적 가능하고 수정 가능한 Investment View Workspace를 유지하고, 사용자가 의미 있는 변화에 attention을 쓰도록 돕고, 최초 Formation과 지속적인 Maintenance를 adaptive depth로 지원하며, Human–AI authorship boundary를 보존하고, 실제 Judgment와 Decision은 관련 Understanding / maintained view가 Decision Context와 결합될 때 downstream에서 형성되도록 해야 한다.**

Forward comparison은 하나의 forecast나 score를 정답처럼 쓰기보다 plausible future, growth-path condition, valuation, uncertainty, relative opportunity를 구조적으로 비교하는 방향이 현재 가장 강하다.

이 문서는 **Working Design Foundation**이다. 최종 Product IA, navigation, screen naming, ontology, database schema, investment-decision rule을 승인한 것이 아니다.

**Overall Recommendation Strength: Strong**

## 2. Research-aligned Semantic Boundary

Workstream 001 초기에는 `Judgment State`, `Judgment Workspace`, `User Judgment`라는 표현을 persistent company-level state에 사용했다.

하지만 최신 Approved Research Lab 구조와 대조하면 cross-Lab `Judgment`는 다음 관계를 가진다.

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

따라서 **DL-DR-0002**에 따라 Design Lab은 Decision Context 이전부터 존재하는 persistent company state를 cross-Lab `Judgment`라고 정의하지 않는다.

교정된 구조는:

```text
Research Knowledge / Understanding
        ↓
System Synthesis
        ↕
Maintained User Investment View
        +
Decision Context
        ↓
Judgment
        ↓
Decision
        ↓
Action
```

이다.

`Investment View`는 현재 Working Design label이며 아직 최종 governed term이 아니다.

과거 Workstream 문서에는 exploration history를 보존하기 위해 이전 terminology가 남을 수 있다. 하지만 이후 reusable / authoritative Design Knowledge는 정렬된 의미를 사용한다.

## 3. Recommended Problem Framing

핵심 문제는 단순한 정보 부족이나 `어떤 주식이 오를까?`가 아니다.

더 강한 framing은:

> **투자자는 제한된 attention을 배분하고, 변화하는 현실을 기존 Understanding과 expectation에 대입해 해석하고, uncertainty 아래에서 수정 가능한 company view를 유지하며, 왜 그 view가 바뀌었는지를 보존하고, 실제 선택이 필요할 때 그 view를 구체적인 Decision Context와 결합해야 한다.**

따라서 Stock_vis가 지원해야 할 것은:

- attention allocation
- Research / Understanding에서 user-facing synthesis까지의 traceability
- persistent but revisable Investment View memory
- uncertainty와 unresolved state
- Human–AI authorship clarity
- meaningful change에 대한 adaptive review
- downstream Decision Context
- forward-looking comparative opportunity
- company growth와 shareholder / investment value의 구분

이다.

## 4. Maintained Investment View Model

Persistent Design-side state에는 필요할 때 다음이 포함될 수 있다.

- 중요한 driver / proposition
- risk / invalidation condition
- dependency / enabling condition
- unresolved question / alternative
- local conviction / uncertainty
- System–User divergence
- relevant scenario condition
- revision history / provenance

User는 다음 상태도 가질 수 있다.

- 아직 explicit view 없음
- partial view만 있음
- 일부 unresolved
- 일부는 System Synthesis와 agreement
- 일부는 disagreement

사용자가 가치를 얻기 위해 완전한 thesis를 먼저 작성하도록 강제하지 않는다.

## 5. System Synthesis와 User-Owned View

DL-DR-0001의 Human–AI authority boundary는 DL-DR-0002의 의미 정렬 아래 그대로 유효하다.

AI는 자율적으로 research, structure, summary, monitoring, challenge를 수행하고 **System Synthesis**를 유지할 수 있다.

그러나 그것을 사용자의 maintained Investment View로 조용히 귀속하거나 덮어써서는 안 된다.

Material한 user-owned change에는 실제 user control 또는 scope가 보이고 reversible하며 traceable한 명시적 delegation이 필요하다.

System–User disagreement는 남아 있을 수 있다.

또한 향후에는 System Synthesis가 단순히 Research Understanding을 presentation / translation하는 경우와, 새로운 inferential Claim을 생성하는 경우를 구분해야 한다. 후자는 Research epistemic treatment가 필요할 수 있다.

## 6. Recommended Information / Relationship Model

서로 다른 기능을 peer information layer로 납작하게 만들지 않는다.

### 6.1 Maintained Investment View
현재 user-owned company view.

### 6.2 System Synthesis
사용자의 view를 지원하거나 challenge할 수 있는 Stock_vis-generated synthesis.

### 6.3 Update Trigger / Signal
재검토 가치가 있을 수 있음을 알리는 signal. Evidence, event, price move, time decay, regime change, 새로운 competing opportunity, portfolio-context change, user question 등이 포함될 수 있다.

Trigger 자체가 company view를 반박하는 evidence는 아니다.

### 6.4 Reference / Interpretive Context
정보를 해석할 때 사용한 baseline. Prior state, expectation, guidance, consensus, historical range, peer, regime 등이 될 수 있다.

### 6.5 Epistemic Input
Research Knowledge / Understanding과 Research-side credibility, applicability, conflict, uncertainty, scope, limitation.

Design은 이를 소비하고 표현하지 별도의 epistemic authority를 만들지 않는다.

### 6.6 View-Bearing Relation
이전 `Judgment-Bearing Relation`의 persistent-view layer 표현을 교정한 Working concept.

> **이 정보가 현재 Investment View의 어느 부분에 실제로 영향을 주는가?**

support / challenge / qualify / narrow / broaden / uncertainty 증가 / component 추가 / no meaningful bearing 등을 가질 수 있다.

### 6.7 View Impact
이전 `Judgment Impact`를 persistent-view layer에서 교정한 Working wording.

Impact는 정보 자체의 fixed score가 아니라 현재 View에 대한 relational assessment다.

### 6.8 Conviction / Uncertainty
Research credibility와도, 실제 Decision confidence와도 구분한다. 기본적으로 affected component에 local하게 연결하는 방향이 강하다.

### 6.9 Update Trace / Lineage
무엇이, 왜, 어떤 근거 / reference로, 누구의 action 또는 authority를 통해 바뀌었는지 material한 경우 추적 가능해야 한다.

### 6.10 Decision Context
Portfolio exposure, horizon, alternatives, valuation, constraints, opportunity cost, switching cost 등의 decision-specific condition은 relevant Understanding / maintained view와 downstream에서 결합해 Judgment를 지원한다.

## 7. Maintained-View Update Logic

현재 가장 강한 analytical maintenance loop는:

```text
Current Investment View
+ Trigger / Signal
+ relevant Research Knowledge / Understanding
        ↓
Orient
        ↓
Contextualize
        ↓
Affected View component에 연결
        ↓
View Impact 평가
        ↓
Revise / Retain / Mark Unresolved
        ↓
Local conviction / uncertainty 재조정
        ↓
Update trace 보존
        ↓
Updated Investment View
```

이다.

이는 mandatory UI sequence가 아니다.

Valid outcome은 strengthen, weaken, retain after review, qualify, narrow, broaden, conditional split, add/remove component, uncertainty 증가/감소, unresolved, suspend view, not assessed 등이 될 수 있다.

`검토 후 유지`와 `아직 검토하지 않음`은 구분한다.

## 8. Logical Experience Architecture

현재 leading architecture는:

> **Persistent Investment View Workspace + Attention-Oriented Orientation + Formation / Maintenance + Adaptive Review + downstream Decision Context**

다.

```text
                       ORIENTATION
                "어디를 봐야 하지?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company    Decision need
         │                │                │
         ▼                ▼                ▼
     FORMATION        MAINTENANCE      DECISION CONTEXT
         │                │           comparison / portfolio
         │       simple change → inline      │
         │       complex/material → review   │
         │                │                   │
         └───────────────┬┘                   │
                         ▼                    │
              INVESTMENT VIEW WORKSPACE      │
                         │                    │
          evidence / provenance / history    │
                         │                    │
                         └──────────────┬─────┘
                                        ▼
                                     JUDGMENT
                                        ↓
                                     DECISION
```

### Orientation guardrail

Orientation은 `이게 중요하다는 사실이 증명되었다`는 뜻이 아니라 **review value / likely bearing에 따라 attention을 배분하는 것**이다.

`Low priority ≠ proven irrelevant`이며 Quiet item도 펼쳐볼 수 있어야 한다.

### Adaptive Review

- user-facing review 가치 거의 없음 → silent system maintenance
- simple / low-consequence bearing → inline
- multi-component / conflicting / consequential / material divergence → focused review
- allocation / rotate / add / reduce 질문 → explicit Decision Context + downstream Judgment

으로 깊이를 바꾼다.

## 9. Formation과 Maintenance

### Formation

처음 보는 기업에서 System Synthesis는 먼저 중요한 구조를 보여줄 수 있지만 user view를 자동 생성하지 않는다.

Useful guided question:

- 무엇이 가장 중요한가?
- 무엇 때문에 이 case가 깨질 수 있는가?
- 아직 무엇을 모르는가?
- 성장하려면 어떤 조건이 성립해야 하는가?

User는 일부만 채택하거나 unresolved로 남길 수 있다.

### Maintenance

기존 종목에서는 chronological feed를 다시 조립하게 하지 않고 새로운 정보를 maintained view의 affected component와 연결한다.

Simple change는 inline, complex change는 focused review가 현재 leading direction이다.

## 10. Forward-Looking Comparison과 Decision Context

Comparison은 현재 어느 회사가 더 좋아 보이는지만 묻지 않는다.

더 강한 downstream question은:

> **가능한 미래에서 어느 투자가 더 강한 forward opportunity를 가지며, 무엇이 그 경로를 가능하게 하거나 막고, 그 상대적 차이가 실제 allocation / rotation에 의미가 있을 만큼 충분히 크고 신뢰할 수 있는가?**

Working representation:

```text
Company A Understanding / Investment View
        ↓
Plausible Future Scenarios
        ↓
Opportunity
→ Enablers
→ Accelerators
→ Bottlenecks / Delays
→ Invalidation Conditions
→ Value-Capture Conditions
        ↓
Possible Growth / Value Outcomes
        ┐
        │
        ├── Relative Future Opportunity
        │
        ┘
Company B ... 동일 구조

            +
Current Valuation
Uncertainty / credibility
Time Horizon
Portfolio Context
Opportunity Cost
Constraints / switching costs
            ↓
Comparative Judgment
            ↓
Decision
```

### Growth만 보면 안 된다

Business growth와 investment value는 동일하지 않다.

필요할 때 다음을 보존한다.

- growth durability / condition
- timing
- capital needs / dilution
- downside / failure condition
- current valuation
- uncertainty
- business growth가 durable shareholder / per-share value로 실제 전환되는가

### Deterministic winner를 기본으로 만들지 않는다

하나의 precise forecast나 total score보다 conditional future와 traceable condition을 우선한다.

`Relative Opportunity Gap`은 Working interaction concept이지 decision threshold / Research term이 아니다.

## 11. Retained / Revised / Rejected

### Retained

- more information보다 better judgment support
- persistent company-level state
- progressive disclosure
- adaptive review
- authorship provenance
- unresolved / disagreement 허용
- revision history
- Comparison의 중요성
- forward scenario / growth-path condition

### Revised

- `Persistent Judgment State` → **Maintained Investment View / equivalent Design concept**
- `Judgment Workspace` → **Investment View Workspace** Working label
- `Judgment Impact` at persistent layer → **View Impact** Working wording
- `Decision Context downstream from company Judgment` → **Understanding / maintained view + Decision Context 이후 cross-Lab Judgment**
- fixed six-step journey → non-linear maintenance loop
- Change Review foundation → broader workspace 안의 Adaptive Review
- current-state comparison → future scenario / relative opportunity comparison
- generic risk → explicit growth-path conditions

### Rejected as defaults

- chronological news feed를 primary experience로 사용
- universal bullish / bearish label
- 하나의 scalar attractiveness / conviction score
- 모든 change마다 review / approval
- 항상 System / User dual column 노출
- 완전한 thesis 작성 강제
- raw business growth = investment opportunity
- deterministic future forecast
- Design-local `Judgment` 재정의

## 12. Design Knowledge Candidates

아직 자동으로 Approved Knowledge가 되는 것은 아니다.

1. Persistent & revisable company-level Investment View는 judgment support에 유용하다. — **Strong**
2. Semantic object와 update process를 분리한다. — **Strong**
3. Relevance / impact는 intrinsic score보다 relation이다. — **Strong**
4. Orientation은 raw activity보다 likely bearing / review value로 attention을 배분한다. — **Strong**
5. Review depth는 consequence-adaptive해야 한다. — **Strong**
6. User-owned view는 absent / partial / unresolved / System과 disagreement 상태가 가능하다. — **Strong**, authorship boundary는 DL-DR-0001 Approved
7. Decision Context는 구분되어야 하며 downstream Judgment보다 앞선다. — **Very Strong**, DL-DR-0002 Approved
8. Comparison은 shared + asymmetric structure를 모두 보존한다. — **Strong**
9. Forward comparison은 outcome만이 아니라 scenario condition / blocker를 보여줘야 한다. — **Strong**
10. Scalar ranking은 traceable trade-off / uncertainty보다 subordinate해야 한다. — **Moderate–Strong**

## 13. Research Trigger Candidates

### Trigger 1 — Future Scenario / Relative Opportunity Methodology

Future scenario, growth-path condition, predictive growth/value outcome, relative opportunity comparison을 downstream에서 사용할 만큼 충분히 강하게 생성·평가하려면 어떤 Research methodology가 필요한가?

Scenario construction, predictive probability, forecast calibration, expected growth / return estimation, valuation-outcome mapping, growth-path condition의 causal / predictive status, comparative Claim evaluation 등이 포함될 수 있다.

### Trigger 2 — Decision-Support Evaluation

Stock_vis가 maintained-view support에서 comparative / portfolio decision support로 확장될수록 downstream reasoning을 어떻게 warrant / evaluate할지 Research에서 추가 정의가 필요할 수 있다.

### Trigger 3 — System Synthesis Epistemic Boundary

User-facing System Synthesis가 단순히 기존 Research Understanding을 정리 / 표현하는 경우와 새로운 inferential Claim / structure를 만드는 경우를 어떻게 구분할 것인가?

## 14. Failure / Reversal Conditions

다음이 확인되면 Foundation을 수정한다.

- persistent Investment View가 continuity보다 harmful anchoring / maintenance burden을 크게 만듦
- System Synthesis와 user-owned view를 사용자가 구분하지 못함
- adaptive depth가 중요한 정보를 숨기거나 unpredictability를 만듦
- focused review가 inbox workload가 됨
- view-bearing relation / update lineage 유지 비용이 너무 큼
- Formation / Maintenance / Decision Context가 지나치게 fragmented함
- scenario structure가 calibration보다 false confidence를 증가시킴
- growth-path condition이 너무 복잡함
- relative-opportunity framing이 과도한 churn을 유도함
- Research Lab이 관련 semantic / predictive architecture를 공식 변경함

## 15. Design Lab Evolution Findings

현재 운영 방식은 잘 작동했다.

- Batch exploration은 CEO micro-consensus를 줄였다.
- Batch별 문서 분리는 reviewability를 개선했다.
- 한글 companion은 CEO review speed를 크게 높였다.
- Prototype은 text discussion에서 안 보이던 interaction failure를 빠르게 발견했다.
- Research-adjacent terminology를 재사용하는 Design mental model은 promotion 전에 cross-Lab semantic review가 필요하다.

현재 추가 permanent governance layer는 필요하지 않다.

## 16. Decision Package

### Recommended Working Foundation

다음 구조를 Product Surface / IA exploration의 upstream working foundation으로 사용한다.

> **Persistent & revisable Investment View Workspace**  
> + **attention-oriented Orientation**  
> + **Formation / Maintenance + adaptive review depth**  
> + **traceable Research / evidence / authorship / revision lineage**  
> + **System Synthesis와 user-owned view 분리**  
> + **Understanding / maintained view + Decision Context → Judgment → Decision**  
> + **scenario, growth-path condition, valuation, uncertainty, relative opportunity를 이용한 forward Comparison**

**Recommendation Strength: Strong**

### Main Alternative

Persistent Investment View 없이 search / alert / ad-hoc AI Q&A 중심으로 동작하는 더 단순한 episodic research assistant.

Interaction / maintenance cost는 낮지만 현재까지 continuity, revision traceability, longitudinal learning, changing opportunity comparison에서는 약했다.

### CEO Critical Decision

**Workstream 001에 남아 있는 CEO Critical Decision 없음.**

Consequential한 Human–AI authority decision과 cross-Lab Judgment semantic decision은 각각 DL-DR-0001, DL-DR-0002로 이미 승인되었다.

### Deferred / AI-Owned

- persistent Design-side state의 최종 이름
- component taxonomy / count
- View Impact 최종 wording / taxonomy
- screen / navigation structure
- inline / drawer / dedicated review 표현
- exact authorship controls
- visual system
- comparison layout
- scalar summary 사용 여부
- prototype implementation detail

## 17. Next Step

이 corrected Working Foundation을 upstream constraint로 사용하되 최종 Product Architecture로 고정하지 않고 계속 challenge하면서 **Workstream 002 — Product Surface / Information Architecture Exploration**을 연다.
