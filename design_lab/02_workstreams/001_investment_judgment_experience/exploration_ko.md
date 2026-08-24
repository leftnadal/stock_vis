# Workstream 001 — Exploration Log

> **한국어 Companion 문서**  
> 원문: [`exploration.md`](exploration.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Status:** Working  
**Source Synced:** 2026-08-24  
**Started:** 2026-08-21  
**Owner:** Stock_vis Design Lab

## Purpose

이 문서는 Investment Judgment Experience Foundation Workstream을 challenge하고 refine하는 데 필요한 exploration을 기록한다.

의도적으로 working space로 사용하며, 여기의 내용은 Design Lab Knowledge Lifecycle을 통해 승격되지 않는 한 Approved Design Knowledge가 아니다.

## 이전 논의에서 가져온 Starting Inputs

다음 내용은 오직 working hypothesis로만 가져온다.

### User problem

투자자는 단순히 정보가 없어서가 아니라 변화하는 현실 속에서 다음을 판단하기 어렵기 때문에 어려움을 겪을 수 있다.

- 실제로 무엇이 변했는가
- 단순히 눈에 띄는 것과 실제로 중요한 것을 어떻게 구분하는가
- 새로운 정보가 기존 또는 형성 중인 investment view와 어떻게 연결되는가
- 어느 정도 confidence가 정당한가
- 다른 opportunity와의 비교가 현재 judgment를 바꾸는가

### Candidate judgment loop

이전 exploratory model에서는 대략 다음 sequence가 제안되었다.

1. 변화 또는 기회를 감지한다.
2. 적절한 reference와 비교하며 의미를 이해한다.
3. material change와 non-material change를 구분한다.
4. evidence와 uncertainty를 평가한다.
5. judgment structure를 형성하거나 업데이트한다.
6. conviction을 recalibrate한다.

이 sequence는 기본적으로 보존하는 것이 아니라 test해야 한다.

### Candidate information model

이전 exploratory model에서는 정보를 다음처럼 묶었다.

- **State & Change**
- **Context & Relationships**
- **Evidence & Uncertainty**
- **Significance / Materiality**
- **Judgment Structure + Conviction**

가능한 layered interpretation은 다음과 같았다.

```text
State & Change
+ Context & Relationships
+ Evidence & Uncertainty
        ↓
Significance / Materiality
        ↓
Judgment Structure + Conviction
```

여전히 provisional하다.

### Candidate logical experience model

이전 hypothesis에서는 experience를 다음과 같이 압축했다.

```text
Orient
→ Understand
→ Judge
```

이것은 navigation 또는 screen architecture가 아니라 logical model이다. Alternative structure와 realistic user task를 통해 검증해야 한다.

### Comparison hypothesis

Comparison은 두 역할을 가질 수 있다.

- number, event, state를 이해하기 위한 context mechanism
- 두 개 이상의 investment alternative를 평가하는 comparative judgment mode

Dedicated comparison surface는 가정하지 않는다.

## Known Important Insight Candidates

다음 prior finding은 반드시 explicit challenge가 필요하다.

### Visible magnitude는 judgment materiality와 다르다

큰 price move, accounting miss, headline, numerical change가 core investment judgment에는 거의 영향을 주지 않을 수 있다. 반대로 작아 보이는 변화가 core driver를 material하게 강화하거나 약화시킬 수 있다.

이 distinction이 reusable Design Knowledge가 될 정도로 robust한지, user-specific context가 materiality를 어떻게 바꾸는지 검증해야 한다.

### Judgment는 structured할 수 있다

새로운 evidence는 investment view의 일부를 강화하면서 다른 일부를 약화시킬 수 있다. 따라서 single bullish/bearish label이나 overall score는 중요한 judgment structure를 지울 위험이 있다.

Thesis graph나 component model이 필요하다고 가정하지 말고 competing representation을 test한다.

### Uncertainty는 simplification 이후에도 살아남아야 한다

Useful compression 때문에 unverified claim, management narrative, forecast, model inference, observed fact가 epistemically identical하게 보여서는 안 된다.

Fact / Interpretation / Expectation 같은 구분이 올바른 Design abstraction인지, 다른 representation이 더 나은지 검토한다.

## Planned Challenge Matrix

각 candidate model은 최소 다음 dimension에서 challenge한다.

| Dimension | Questions |
|---|---|
| New vs existing judgment | Prior thesis가 전혀 없는 경우와 mature holding 모두에 작동하는가? |
| Event type | Earnings, price movement, industry change, regulatory event, new opportunity에 모두 작동하는가? |
| Evidence conflict | Disagreement와 uncertainty를 보존하면서도 unusable해지지 않는가? |
| Time horizon | Long-term investor와 short-horizon investor의 materiality model이 달라야 하는가? |
| Comparison | 전체 architecture를 복제하지 않고 opportunity cost와 rotation을 지원할 수 있는가? |
| Attention | Time-constrained user가 필요한 depth를 잃지 않으면서 빠르게 orient할 수 있는가? |
| Expertise | Experienced user에게 지나치게 단순하지 않고 less-experienced user를 압도하지 않는가? |
| Behavioral risk | Salience, loss aversion, anchoring, confirmation bias, recency가 journey를 왜곡하는가? |
| Research boundary | Design abstraction이 공식 Research concept를 조용히 재정의하고 있지 않은가? |
| Action boundary | Judgment support와 decision prescription이 구분되어 있는가? |

## 탐색할 Alternative Framings

현재 model을 유일한 candidate로 취급하지 않는다. 최소한 다음 alternative를 검토한다.

1. **Question-driven model** — sequential journey보다 반복되는 핵심 investor question을 중심으로 experience를 조직
2. **Claim-centered model** — claim과 이를 support/challenge하는 evidence를 중심으로 조직
3. **Change-centered model** — driver와 risk의 material change를 중심으로 조직
4. **Decision-context model** — user portfolio context, alternative, horizon, constraint를 중심으로 조직
5. **Hybrid model** — orientation, deep understanding, judgment state, decision context를 분리하면서 non-linear movement 허용

Final synthesis는 이들을 결합하거나 모두 일부 수정할 수 있다.

## Evidence and Benchmarking Needs

추가 exploration에서는 다음과 관련된 evidence 또는 strong prior art를 찾아야 한다.

- investor information overload / selective attention
- belief updating / confirmation bias
- uncertainty / confidence calibration
- comparison / choice architecture
- complex information의 progressive disclosure
- user agency를 보존하는 decision-support system
- raw information, interpretation, user judgment를 구분하는 financial product
- professional / retail investor가 thesis change를 시간에 따라 monitoring하는 방식

External example은 pattern과 trade-off에 대한 evidence로 사용하며 product architecture를 그대로 복사하지 않는다.

## Initial Research Consistency Check

Approved Research Lab Knowledge and Understanding Framework는 Understanding을 downstream Judgment, Decision, Action과 구분한다. 따라서 이 Workstream은 Research Knowledge와 Understanding을 upstream input으로 취급하고, decision context 아래에서 user judgment를 형성하는 experience에 집중한다.

Understanding, Evidence, Research Knowledge 또는 기타 Research concept를 재정의할 필요가 생기면 local하게 해결하지 않고 Research Trigger Candidate로 surface한다.

# Exploration Batch 01 — User Problem and Competing Judgment Models

**Batch Status:** Working synthesis candidate이며 Approved Design Knowledge가 아님.  
**Exploration Focus:** behavioral evidence, decision-support evidence, 현재 financial-product pattern, competing mental model, scenario stress test.

## 1. External Evidence — 실제로 어떤 문제가 Design Support를 필요로 하는가?

### 1.1 Scarce attention은 1차적 constraint다

Behavioral-finance evidence는 투자자가 이용 가능한 모든 정보를 처리할 수 없고 attention을 선택적으로 배분한다는 점을 반복적으로 보여준다. 눈에 띄거나 attention을 끄는 정보는 가장 fundamental한 정보가 아니어도 trading에 영향을 줄 수 있다. 따라서 단순히 더 많은 정보를 제공하면 충분하다고 가정하기보다 **attention allocation 자체를 judgment problem의 일부**로 봐야 한다.

검토한 주요 evidence:

- Choi & Choi (2019), *Effects of limited attention on investors' trading behavior* — attention-grabbing stock은 abnormal trading을 유발하고 less-sophisticated individual investor가 더 지속적으로 매수하는 경향; https://www.sciencedirect.com/science/article/abs/pii/S0927538X18303196
- Andrei et al. (2020), *Limited attention, salience of information and stock market activity* — 제한된 processing capacity 아래에서 salient cue가 investor attention에 영향을 줌; https://www.sciencedirect.com/science/article/pii/S0264999318311519
- Hirshleifer & Teoh (2003), *Limited attention, information disclosure, and financial reporting* — investor attention이 제한될 때 information presentation과 aggregation 방식이 중요; https://www.sciencedirect.com/science/article/pii/S0165410103000648

**Design implication candidate:** 문제는 단순한 정보 availability가 아니다. Stock_vis는 scarce attention을 judgment-relevant change로 배분하도록 돕되 deeper context에 접근할 수 있어야 할 가능성이 높다.

### 1.2 Belief updating은 중립적이지 않다

실험 evidence는 investment belief가 involvement, 현재 position, 정보의 주관적 favorability 등에 의해 왜곡될 수 있음을 시사한다. Information processing / belief formation을 즉각적인 decision opportunity와 분리하고 정보를 bundle하는 방식은 Bayesian benchmark에 더 가까운 belief formation을 만들 수 있다.

검토한 주요 evidence:

- Holzmeister et al. (2023), *Take your time: How delayed information and restricted decision opportunities improve belief formation in investment decisions*; https://www.sciencedirect.com/science/article/pii/S1544612322006195
- Giglio et al. (2021), *Five Facts about Beliefs and Portfolios* — investor belief는 persistent하고 heterogeneous하며, belief가 portfolio에 미치는 민감도는 attention과 confidence 등에 따라 달라짐; https://pubs.aeaweb.org/doi/10.1257/aer.20200243
- *Do you have a choice?: Implications for belief updating and the disposition effect* (2024) — loss-related investment behavior에서 belief updating의 역할을 추가로 지지; https://www.sciencedirect.com/science/article/pii/S0167487024000266

**Design implication candidate:** Stock_vis는 understanding, judgment, action을 하나의 즉각적인 recommendation flow로 압축하지 않는 편이 좋다. Evidence를 검토하고 judgment를 수정하는 별도의 cognitive/process space가 가치 있을 가능성이 높다.

### 1.3 Confidence는 이후 revision에 영향을 주지만 false precision은 위험하다

Finance 외 decision research에서는 explicit confidence representation이 이후 change-of-mind에 영향을 줄 수 있음이 나타난다. Confidence가 낮을수록 같은 선택을 다시 만났을 때 판단을 바꿀 가능성이 커진다. 따라서 conviction/confidence는 judgment state의 의미 있는 일부일 수 있지만, 이것이 precise한 하나의 overall score를 정당화하지는 않는다.

검토한 주요 evidence:

- Folke et al. (2017), *Explicit representation of confidence informs future value-based decisions*; https://www.nature.com/articles/s41562-016-0002

**Design implication candidate:** conviction은 revisability를 위한 calibration signal로 유용할 수 있다. 다만 무엇에 대한 confidence인지 연결되어야 하고 uncertainty를 지우는 숫자 정밀도를 만들어서는 안 된다.

### 1.4 Decision support는 도움을 주면서 automation bias도 만들 수 있다

최근 및 고전적 decision-support research는 decision aid가 time과 performance를 개선할 수 있지만, user가 이를 과도하게 사용하거나 덜 사용하거나 과신할 수 있음을 보여준다. Explanation을 제공한다고 automation bias가 안정적으로 사라지는 것도 아니며 때로는 reliance를 증가시킬 수 있다.

검토한 주요 evidence:

- *Information shapes decisions: The access and use of decision support* (2026); https://www.sciencedirect.com/science/article/pii/S2451958826000230
- Vered et al. (2023), *The effects of explanations on automation bias*; https://www.sciencedirect.com/science/article/pii/S000437022300098X
- Skitka, Mosier & Burdick (1999), *Does automation bias decision-making?*; https://www.sciencedirect.com/science/article/pii/S1071581999902525

**Design implication candidate:** “AI reasoning을 설명해준다”만으로 user agency가 보존된다고 볼 수 없다. User가 evidence, disagreement, uncertainty를 inspect하고 system-supported judgment를 수정할 수 있는 구조적 기회가 필요할 가능성이 높다.

## 2. Current Financial-Product Pattern Review

현재 시장에는 data access, monitoring, research acceleration, comparison, AI synthesis를 강하게 지원하는 제품이 이미 많다. 그러나 이번에 검토한 제품의 public positioning에서는 **persistent하고 user-verifiable한 investment judgment state 자체를 primary organizing object로 명확히 두는 패턴은 뚜렷하지 않았다.**

### Koyfin

Koyfin은 customizable watchlist, dashboard, alert, chart, financial analysis, company snapshot, screener, portfolio monitoring에 강하다. 핵심 강점은 flexible data orientation과 monitoring이다.

Reference: https://www.koyfin.com/features/

**이 Workstream과 관련된 observed gap:** 강력한 information configuration만으로 evidence가 maintained investment view를 어떻게 바꾸는지는 해결되지 않는다.

### FinChat

FinChat은 financial data, company-specific KPI, dashboard, comparison, notification, AI research를 결합한다. 반복적인 research task는 AI가 자동화하고 thinking은 human에게 남긴다는 positioning도 명시적이다.

Reference: https://finchat.io/

**Observed gap:** understanding과 research acceleration은 강하지만, 이번에 확인한 public positioning만으로는 persistent structured judgment / revision state가 central user object로 보이지 않는다.

### AlphaSense

AlphaSense는 exploration, deep research, financial data, monitoring, alert, cited AI output, company profile, workflow agent를 통합한다. 2026 platform에는 investment-thesis research agent와 continuous portfolio / watchlist monitoring도 명시돼 있다.

References:

- https://www.alpha-sense.com/platform/
- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/42623871994131-Company-Profiles

**Observed implication:** research synthesis와 monitoring의 competitive bar는 이미 높다. 따라서 Stock_vis의 differentiation을 단순히 “AI가 research를 요약해준다”에서 찾으면 약할 가능성이 높다. 더 강한 기회는 **시간, evidence 변화, alternative 비교를 가로질러 traceable judgment structure를 유지하는 것**일 수 있다.

이 competitive interpretation은 아직 provisional하며 final product-strategy conclusion으로 취급하지 않는다.

## 3. Competing Mental Model Stress Test

### 3.1 Question-driven model

**Strengths**
- user에게 자연스러운 entry point
- time / attention constraint에서 강함
- “무엇이 변했나?”, “이게 중요한가?” 같은 recurring question과 바로 연결되어 cognitive load를 줄일 수 있음

**Failure modes**
- investment view의 durable memory가 약함
- 반복 질문이 disconnected answer로 남을 수 있음
- evidence가 시간에 따라 어떻게 누적·충돌하는지 표현하기 어려움

**Current judgment:** interaction / access layer로는 유용하지만 foundational judgment model로는 약함.

### 3.2 Claim-centered model

**Strengths**
- evidence → belief traceability가 강함
- conflicting evidence 및 부분적 strengthening / weakening 지원
- mixed earnings와 thesis revision에 적합

**Failure modes**
- 너무 많은 claim으로 experience가 atomize될 수 있음
- attention priority, decision context, portfolio opportunity cost를 단독으로 표현하기 어려움
- user에게 research ontology를 수동 유지하도록 요구할 위험

**Current judgment:** 가장 강한 structural backbone candidate지만 단독으로는 부족함.

### 3.3 Change-centered model

**Strengths**
- existing holding monitoring에 매우 강함
- alert 및 “what changed?” orientation과 자연스럽게 연결
- materiality로 filter하면 information overload 감소에 유리

**Failure modes**
- prior baseline이 없는 신규 종목에서는 약함
- 최근 변하지 않았지만 중요한 structural fact가 묻힐 수 있음
- “change”가 magnitude와 동일시되면 salience bias가 다시 들어옴

**Current judgment:** 강한 update / monitoring mechanism이지만 완전한 모델은 아님.

### 3.4 Decision-context model

**Strengths**
- comparison, opportunity cost, horizon, portfolio constraint, rotation question에 필수
- 같은 evidence도 user마다 judgment materiality가 달라지는 이유를 설명할 수 있음

**Failure modes**
- research가 너무 일찍 action choice를 중심으로 조직될 위험
- judgment support가 decision prescription으로 넘어갈 수 있음
- user portfolio context를 너무 일찍 섞으면 underlying company reality 표현을 왜곡할 수 있음

**Current judgment:** 필요한 contextual layer지만 underlying judgment structure를 대체해서는 안 됨.

### 3.5 Hybrid model

현재 가장 강한 모델은 하나의 abstraction이 모든 역할을 하게 만들기보다 서로 다른 역할을 결합하는 구조다.

Working formulation:

> **Investment judgment는 내부 구조를 가진 maintained and revisable state이며, decision context 아래에서 evidence-driven process를 통해 업데이트된다.**

이는 세 가지 구별되는 측면을 가진다.

1. **Judgment State / Structure** — 현재 investment view. 중요한 claim 또는 driver, risk, unresolved uncertainty, calibrated confidence 등을 포함.
2. **Judgment Update Process** — 새로운 evidence/change를 contextualize하고 significance를 평가하며 affected judgment component에 연결한 뒤 confidence 또는 structure를 수정.
3. **Decision Context** — horizon, portfolio state, alternatives, constraints, opportunity cost가 relevance와 comparison을 바꾸지만 underlying Research reality 자체를 재정의하지는 않음.

Question-driven layer는 이 deeper structure의 underlying semantic model이 아니라 lightweight user entry 역할을 할 수 있다.

**Current Recommendation Strength:** Strong. 아직 Very Strong은 아니다. Real-user validation이 없고 structured model 중 어느 깊이를 실제 user-visible하게 해야 하는지가 unresolved이기 때문이다.

## 4. Leading Hybrid Scenario Stress Test

### Held stock with sharp price decline

Salient price move와 judgment materiality를 분리하고 어떤 structural claim / risk가 실제로 영향을 받는지 볼 수 있다. Decision context는 urgency를 바꿀 수 있지만 price 자체를 thesis failure evidence로 자동 취급하지 않는다.

**Result:** survives.

### Mixed earnings release

Revenue, guidance, margin, execution, demand evidence가 서로 다른 judgment component를 동시에 강화·약화시킬 수 있다.

**Result:** single-score 또는 change-only model보다 잘 버팀.

### Previously unfamiliar company

Change-only model은 baseline이 없어 약하다. Hybrid는 current state, context, evidence, unresolved question에서 initial structured judgment를 만들 수 있고 question-driven orientation으로 빠른 ramp-up도 지원한다.

**Result:** survives. Formation과 update는 구분되지만 underlying structure는 공유할 수 있다는 가설을 지지.

### Existing holding vs new opportunity

별도의 comparison ontology를 만들기보다 동일한 maintained judgment structure들을 decision context 아래에서 비교할 수 있다. Opportunity cost와 constraint는 intrinsic company representation보다 comparative judgment에 속한다.

**Result:** conceptually survives. 실제 comparison dimension은 추가 exploration 필요.

### Conflicting or incomplete evidence

하나의 답으로 강제하지 않고 unresolved disagreement를 structure 안에 보존할 수 있다.

**Result:** survives. 단, interface가 conflict를 overall score로 다시 collapse하면 실패.

### Time-constrained user

매번 full structure를 읽는 것은 비용이 너무 크다. 따라서 deeper model 위에 question-driven entry, prioritization, progressive disclosure가 필요하다.

**Result:** full structure always-visible 방식은 실패. Layered / progressive experience로는 survives.

## 5. Refined Core User-Problem Framing

초기 framing인 “복잡하고 변화하며 불확실한 현실 속에서 investor가 judgment를 형성하고 업데이트하기 어렵다”는 방향은 맞지만 너무 넓다.

현재 더 강한 working framing은 다음과 같다.

> **투자자는 scarce attention을 배분하고, evidence를 context 속에서 해석하며, uncertainty 아래 heterogeneous belief를 수정해야 한다. 이 과정에서 salience, 기존 position, automated synthesis가 judgment를 너무 일찍 action으로 collapse시키지 않도록 해야 한다.**

따라서 Stock_vis Design Problem은 정보 전달량을 최대화하는 것보다 다음을 지원하는 문제에 더 가까울 수 있다.

- attention allocation
- evidence-to-judgment traceability
- structured belief revision
- uncertainty / conviction calibration
- explicit decision context 아래의 comparison
- user agency preservation

이것은 Working Finding이며 Approved Design Principle 또는 product architecture가 아니다.

## 6. Starting Hypotheses에서 무엇이 달라졌는가

### Strengthened

- judgment는 하나의 score보다 meaningful한 structure를 가진다는 가설
- visible magnitude와 judgment materiality는 구분되어야 한다는 가설
- evidence / uncertainty가 synthesis 이후에도 살아남아야 한다는 가설
- comparison은 완전히 별도의 information ontology보다 judgment mode / context overlay로 보는 것이 적합하다는 가설
- user agency 보존에는 단순 AI explanation 이상의 구조가 필요하다는 점

### Revised

- “Judgment = structure”만으로는 너무 좁다. 현재 evidence는 **state + structure + update process + decision context**를 지지한다.
- candidate sequential journey를 아직 core user mental model로 볼 이유는 약해졌다. Internal update logic에 더 적합할 가능성이 있다.
- `Orient → Understand → Judge`는 high-level shorthand로는 아직 plausible하지만 strict sequence보다는 non-linear access가 더 적합해 보인다.

### Standalone foundation으로 약화 / 기각

- question-driven model 단독
- change-centered model 단독
- single scalar conviction / attractiveness score를 primary judgment representation으로 사용하는 방식
- transparency/explanation만으로 over-reliance가 해결된다고 보는 AI-explanation-first model

## 7. Reversal / Validation Conditions

Real-user work에서 다음이 확인되면 leading model을 수정해야 한다.

- investor가 persistent structured view보다 episodic question-answer support에서 더 큰 benefit을 얻음
- structured judgment 유지 비용이 줄이는 cognitive / interaction cost보다 더 큼
- system-generated structure가 belief revision을 돕기보다 anchoring을 더 강하게 만듦
- decision context가 judgment relevance를 너무 강하게 지배해 company-centered maintained state가 오히려 misleading함
- expert와 less-experienced user가 disclosure depth 차이가 아니라 fundamentally different model을 필요로 함
- comparison에서 동일 judgment structure를 reuse하려 하면 artificial common dimension을 강제하게 됨

## 8. Current Batch Position

**Leading Recommendation:** Workstream 001을 `maintained judgment state/structure + evidence-driven update process + explicit decision context`, 그리고 likely experience layer로서 `question-driven access`를 사용하는 hybrid formulation으로 계속 진행한다.

**Recommendation Strength:** Strong.

**CEO Critical Decision:** 현재 없음. 이 model은 아직 Working이며 durable user mental model 또는 major product architecture로 승격하기 전에 추가 검증이 필요하다.

## Open Questions

- Maintained judgment structure 중 어떤 부분을 user-authored, system-synthesized, jointly editable로 둘 것인가?
- Conviction은 전체 judgment의 property인가, individual claim의 property인가, 둘 다인가?
- Judgment materiality를 책임 있게 평가하려면 얼마나 많은 user context가 필요한가?
- 하나의 common architecture가 discovery와 monitoring을 모두 지원할 수 있는가, 아니면 하나의 mental model을 억지로 강요하게 되는가?
- Hybrid revision 이후에도 6-step candidate journey가 internal update logic으로 유용한가?
- Model의 어떤 부분을 user-visible하게 해야 하고 어떤 부분은 system-side reasoning으로 남겨야 하는가?
- Synthesized interpretation과 user-authored judgment 사이의 boundary는 어디에 있어야 하는가?

## Design Lab Evolution Observations

이 section은 Workstream을 수행하면서 발견되는 recurring operating friction을 기록한다. One-off inconvenience는 local하게 처리하고 자동으로 Lab governance로 바꾸지 않는다.

_현재까지 recurring operating issue 없음._
