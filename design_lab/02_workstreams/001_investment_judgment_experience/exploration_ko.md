# Workstream 001 — Exploration Log

> **한국어 Companion 문서**  
> 원문: [`exploration.md`](exploration.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않으며, 의미 차이가 있을 경우 영어 원문을 기준으로 해소한다.

**Status:** Working  
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

## Open Questions

- Investment judgment는 state, structure, process 중 무엇으로 보는 것이 가장 적절한가? 혹은 복합적인가?
- Conviction은 전체 judgment의 property인가, individual claim의 property인가, 둘 다인가?
- Judgment materiality를 책임 있게 평가하려면 얼마나 많은 user context가 필요한가?
- 하나의 common architecture가 discovery와 monitoring을 모두 지원할 수 있는가, 아니면 하나의 mental model을 억지로 강요하게 되는가?
- Sequential journey는 실제 user에게 유용한가, 아니면 Design Lab 분석용 model에 더 가까운가?
- Model의 어떤 부분을 user-visible하게 해야 하고 어떤 부분은 system-side reasoning으로 남겨야 하는가?
- Synthesized interpretation과 user-authored judgment 사이의 boundary는 어디에 있어야 하는가?

## Design Lab Evolution Observations

이 section은 Workstream을 수행하면서 발견되는 recurring operating friction을 기록한다. One-off inconvenience는 local하게 처리하고 자동으로 Lab governance로 바꾸지 않는다.

_현재까지 recurring operating issue 없음._
