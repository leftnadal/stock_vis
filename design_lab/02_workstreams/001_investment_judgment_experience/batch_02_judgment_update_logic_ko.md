# Workstream 001 — Exploration Batch 02: Judgment Update Logic & Information Model

> **한국어 Companion 문서**  
> 원문: [`batch_02_judgment_update_logic.md`](batch_02_judgment_update_logic.md)  
> 이 문서는 영어 원문의 빠른 검토를 위한 한국어 companion이다. 독립 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Status:** Working  
**Source Synced:** 2026-08-25  
**Date:** 2026-08-25  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; Approved Design Knowledge 또는 product architecture가 아님

## 1. 이번 Batch의 질문

이번 Batch는 다음을 묻는다.

> 새로운 evidence, event, 조건 변화, 또는 Decision Context 변화가 나타났을 때 기존 investment judgment가 바뀌어야 하는지, 바뀐다면 어떻게 바뀌어야 하는지를 무엇이 결정해야 하는가?

기존 후보 구조:

```text
State & Change
+ Context & Relationships
+ Evidence & Uncertainty
        ↓
Significance / Materiality
        ↓
Judgment Structure + Conviction
```

및 기존 6-step judgment loop를 공격적으로 검토하는 것이 목적이다.

## 2. Research Lab Boundary Check

현재 Approved Research Lab architecture는 Design 작업에 다음 constraint를 준다.

- Evidence, Claim, Research Knowledge, Understanding, Judgment, Decision, Action은 구분되어야 한다.
- Understanding과 그 credibility는 downstream Judgment보다 upstream이다.
- Credibility와 applicability는 다르다.
- 특정 Decision에 대한 relevance 또는 confidence는 Understanding의 intrinsic property가 아니며 Understanding과 Decision Context가 만날 때 downstream에서 발생한다.
- Evaluation은 `Not Material ≠ Favorable`, `Unassessed ≠ Unfavorable`, `Unknown ≠ Contradicted` 같은 distinction을 보존한다.
- Process와 epistemic object는 구분되어야 한다.
- Material revision은 lineage를 보존해야 한다.

따라서 Design이 evidence quality, Research credibility, current applicability, decision relevance, judgment impact, user conviction을 하나의 product-side scalar로 조용히 합쳐서는 안 된다.

## 3. Update Logic과 관련된 외부 Evidence

### 3.1 Reference frame은 belief updating 자체를 바꾼다

Financial analyst field evidence에서는 expectation이 reference point로 작동할 수 있었다. 거의 동일한 earnings signal을 본 analyst도 자신의 forecast를 아주 조금 상회했는지, 아주 조금 하회했는지에 따라 이후 belief update가 달라졌다.

Reference:
- *Expectational reference points and belief formation: Field evidence from financial analysts* (2025): https://www.sciencedirect.com/science/article/pii/S0167268124004025

**Design implication candidate:** Context는 필요하지만 neutral하지 않다. 하나의 expectation, consensus, prior price, prior judgment를 보이지 않는 truth baseline으로 쓰기보다 어떤 reference frame이 사용되고 있는지를 드러낼 필요가 있다.

### 3.2 Information processing과 즉각적인 action을 분리하면 belief formation이 개선될 수 있다

Investment experiment에서는 involvement를 낮추고 belief formation과 즉각적인 decision opportunity를 분리할 때 belief가 Bayesian benchmark에 더 가까워졌고, information을 하나씩 reactive하게 처리하는 것보다 bundle해서 처리하는 방식도 도움이 됐다.

Reference:
- Holzmeister et al. (2023), *Take your time: How delayed information and restricted decision opportunities improve belief formation in investment decisions*: https://www.sciencedirect.com/science/article/pii/S1544612322006195

**Design implication candidate:** Update process는 반드시 즉각적인 action recommendation으로 끝날 필요가 없다. `judgment revised / retained / unresolved`에서 끝날 수 있어야 한다.

### 3.3 Confidence는 revision에 유용하지만 local과 global confidence는 다르다

Metacognition 연구에서는 explicit local confidence가 이후 change-of-mind에 영향을 주며, global confidence는 local confidence와 feedback을 시간에 따라 통합해서 형성될 수 있음을 보여준다.

References:
- Folke et al. (2017), *Explicit representation of confidence informs future value-based decisions*: https://www.nature.com/articles/s41562-016-0002
- Rouault et al. (2019), *Forming global estimates of self-performance from local confidence*: https://www.nature.com/articles/s41467-019-09075-3

**Design implication candidate:** Conviction은 우선 그것이 가리키는 judgment component 또는 proposition에 붙어야 한다. Global summary를 둘 수는 있지만 heterogeneous local confidence를 지우면 안 된다.

### 3.4 Uncertainty cue를 더 많이 넣는다고 calibration이 자동으로 좋아지지 않는다

최근 LLM decision-support 연구에서는 visual confidence cue가 subjective accuracy discrimination은 높였지만, 틀린 output에 대한 behavioral over-reliance도 증가시킬 수 있었다.

Reference:
- *More is not better: Visual uncertainty cues and the fragility of trust calibration in LLM-assisted decision making* (2026): https://www.sciencedirect.com/science/article/pii/S2949882126000587

**Design implication candidate:** Uncertainty를 단순한 badge layer로 만들거나 confidence indicator를 많이 추가하는 것으로 해결하면 안 된다. 영향을 받는 claim, evidence, judgment impact, unresolved decision relevance와 연결되어야 한다.

## 4. 기존 Information Model의 주요 문제

이전 모델은 서로 다른 semantic function을 하나의 hierarchy 안에 섞고 있었다.

예를 들면:

- **State / Judgment State** — object 또는 maintained condition
- **Evidence** — epistemic input
- **Context / Reference** — 해석에 필요한 relational information
- **Materiality** — impact / relevance에 대한 assessment
- **Judgment revision** — process / operation
- **Conviction** — judgment 또는 component에 대한 meta-level property

이들을 모두 같은 레벨의 “information type”처럼 두면 object, relationship, evaluation, update operation이 뒤섞일 위험이 크다.

**Working conclusion:** **Judgment Semantic Model**과 **Judgment Update Logic**을 분리한다.

## 5. Recommended Working Judgment Semantic Model

현재 leading semantic model은 다음 요소를 구분한다.

### 5.1 Maintained Judgment State

시간에 따라 수정될 수 있는 현재 investment view.

필요에 따라 다음을 포함할 수 있다.
- important claim / driver
- risk / failure condition
- unresolved alternative / question
- relevant condition / dependency
- local conviction / confidence annotation
- material revision의 historical lineage

모든 항목을 UI에 동시에 보여줘야 한다는 의미는 아니다.

### 5.2 Update Trigger / Signal

재검토가 가치 있을 가능성을 만드는 것.

Trigger는 다음에서 발생할 수 있다.
- 새로운 Evidence 또는 Research Knowledge
- material event / observation
- condition / regime 변화
- 시간 경과 / applicability stale
- 새로운 competing opportunity
- portfolio 또는 Decision Context 변화
- user question 또는 명시적인 reconsideration 요청

따라서 price movement는 기본적으로 trigger 또는 observation이지 fundamental claim 변화의 자동 proof가 아니다.

### 5.3 Reference & Interpretive Context

Trigger가 무엇을 의미하는지 해석하기 위해 필요한 정보.

가능한 reference:
- prior state
- prior judgment
- prior expectation
- management guidance
- market consensus
- historical distribution
- peer / industry comparison
- stated boundary condition
- time horizon / regime

Reference point에 따라 belief update가 달라질 수 있으므로 어떤 reference frame을 쓰는지 식별 가능해야 한다.

### 5.4 Epistemic Input / Profile

Judgment에 사용할 수 있는 warranted Research-side content와 그 limitation, conflict, uncertainty, credibility, applicability.

Design은 Research-side epistemic characterization을 소비하고 표현해야 하며, Product에서 새로운 정의로 Research object를 다시 평가하는 독립 authority를 조용히 만들어서는 안 된다.

### 5.5 Judgment-Bearing Relation

기존 모델에서 빠져 있던 핵심 relation:

> **이 input은 현재 maintained judgment의 어떤 부분에 실제로 영향을 주는가?**

Input은 judgment component를:
- support
- challenge
- qualify
- narrow
- broaden
- 새로운 component 도입
- unresolved conflict 생성
- 특정 component에는 meaningful bearing 없음

등으로 다르게 건드릴 수 있다.

같은 input이 여러 judgment component에 서로 다른 방향으로 작용할 수도 있다.

### 5.6 Judgment Impact

기존 `Significance / Materiality`를 대체하는 현재 선호 Working term.

Judgment Impact는 information item의 intrinsic property가 아니다. 새로운 input이 관련 context 아래에서 현재 judgment를 meaningful하게 변경할 만큼 충분한 근거가 되는지를 나타내는 relation / assessment다.

Formula로 축소하지 않되 다음이 material factor가 될 수 있다.
- 어떤 judgment component가 영향을 받는가
- 해당 component가 얼마나 central하거나 dependency-heavy한가
- warranted change의 direction / magnitude
- input의 epistemic strength와 current applicability
- conflict / alternative explanation
- 변화한 condition의 persistence / reversibility
- downstream relevance를 볼 때의 current Decision Context

`materiality`라는 자연어는 계속 쓸 수 있지만, `Judgment Impact`가 information의 고정 속성처럼 오해되는 문제와 Research Evaluation의 materiality semantics와 충돌할 위험을 더 잘 피한다.

### 5.7 Decision Context

Decision Context는 downstream이며 intrinsic Research meaning과 구분한다.

가능한 요소:
- investment horizon
- portfolio exposure / concentration
- available alternatives
- constraints
- opportunity cost
- 필요한 경우 liquidity, tax 등 decision-relevant condition

Decision Context가 바뀌면 underlying company judgment가 그대로여도 action relevance는 달라질 수 있다.

### 5.8 Update Trace / Lineage

Material change는 최소한 다음을 다시 확인할 수 있을 정도의 trace를 보존해야 한다.
- prior judgment가 무엇이었는가
- 어떤 new input이 들어왔는가
- 어떤 reference / context를 사용했는가
- 어떤 judgment component가 영향을 받았는가
- 왜 바뀌었거나, 유지되었거나, 더 uncertain해졌는가
- 무엇이 아직 unresolved인가

User verification과 hindsight reconstruction 감소 모두에 중요하다.

## 6. Recommended Working Judgment Update Logic

현재 leading process는 실제 사용에서는 non-linear할 수 있지만 분석적으로는 다음처럼 표현할 수 있다.

```text
Current Judgment State
+ Update Trigger / Signal
+ relevant Research Knowledge / Understanding
+ 필요할 때 Decision Context
        ↓
1. Select / Orient
        ↓
2. Contextualize
        ↓
3. Establish Judgment Bearing
        ↓
4. Assess Judgment Impact
        ↓
5. Revise / Retain / Mark Unresolved
        ↓
6. Recalibrate Conviction & Uncertainty
        ↓
7. Preserve Update Trace
        ↓
Updated Judgment State
        ↓
optional downstream Decision evaluation
```

### 6.1 Select / Orient

Trigger가 scarce user attention을 받을 가치가 있는지 판단한다.

Salience, price magnitude, headline volume, recency를 judgment relevance와 동일시해서는 안 된다.

### 6.2 Contextualize

적절한 comparison / reference를 찾고 관련 Research understanding이 현재 applicable한지 본다.

Material하게 충돌할 경우 여러 reference frame을 함께 보존할 필요가 있다.

### 6.3 Establish Judgment Bearing

Input이 어떤 claim, driver, risk, condition, unresolved question에 영향을 주는지 연결한다.

이 단계가 있어야 generic `good news / bad news`가 primary update mechanism이 되는 것을 막을 수 있다.

### 6.4 Assess Judgment Impact

그 bearing이 maintained judgment를 바꿀 만큼 중요하고 충분히 warranted한지 본다.

하나의 scalar로 강제하지 않는다.

Working state 후보:
- material positive impact
- material negative impact
- qualifying / scope-changing impact
- uncertainty increase
- uncertainty reduction
- currently no material impact
- unresolved / conflicting
- not assessed

정확한 label은 아직 Working이다.

### 6.5 Revise / Retain / Mark Unresolved

Valid outcome은 항상 `thesis change`가 아니다.

가능한 operation:
- retain
- strengthen
- weaken
- add
- remove
- reframe
- conditional case로 split
- scope narrow / broaden
- unresolved 표시
- warrant가 부족하면 judgment suspend

`평가 후 retain`과 `아예 평가하지 않음`은 구분해야 한다.

### 6.6 Recalibrate Conviction & Uncertainty

Conviction은 우선 affected component에 local하게 붙는 것이 좋다.

새 evidence는:
- direction은 바꾸지만 confidence는 거의 안 바꿀 수 있고
- confidence만 바꾸고 directional judgment는 유지할 수 있으며
- central judgment는 유지하지만 unresolved uncertainty는 증가시킬 수 있다.

따라서 direction, confidence, uncertainty는 서로 분리되어야 한다.

### 6.7 Preserve Update Trace

Material revision을 현재 state로 조용히 덮어쓰지 말고 inspect 가능하게 유지해야 한다.

이것은 learning, accountability, time comparison, future challenge를 지원한다.

## 7. Stress Test

### 7.1 Fundamental new information 없이 sharp price decline

**Naive model:** 큰 변화 → high materiality → thesis 약화.

**Recommended model:** Price decline은 trigger다. Valuation, market sentiment, liquidity, risk 관련 component에는 영향을 줄 수 있지만 operating / demand claim을 자동으로 challenge하지 않는다.

**Result:** process-object separation이 salience를 evidence로 승격시키는 오류를 막는다.

### 7.2 Earnings beat지만 guidance 악화

서로 다른 input이 서로 다른 component에 작용한다. Historical execution은 강화되면서 forward demand / margin expectation은 약화될 수 있다.

**Result:** 하나의 event 안에서 multi-directional update가 가능하며 overall bullish/bearish answer를 강제하지 않는다.

### 7.3 같은 earnings result, 다른 expectation reference

Company guidance 대비 강하지만 market consensus 대비 약할 수 있고 반대도 가능하다.

**Result:** Explicit reference frame이 필요하다. 하나의 보이지 않는 baseline은 false objectivity를 만든다.

### 7.4 매우 강한 evidence가 peripheral component에만 영향

Epistemically strong한 evidence라도 현재 view의 주변적이고 dependency가 낮은 component에만 작용하면 Judgment Impact는 낮을 수 있다.

**Result:** epistemic strength와 judgment impact를 구분할 수 있다.

### 7.5 Central thesis driver에 영향을 주지만 evidence가 weak / conflicting

Centrality는 높지만 warrant가 약하다.

**Recommended update:** 즉시 thesis를 약화시키기보다 uncertainty 증가 또는 unresolved challenge로 남길 수 있다.

**Result:** potential importance가 높다는 이유만으로 premature revision을 만들지 않는다.

### 7.6 Company judgment는 그대로인데 Decision Context만 변화

다른 holding 하락으로 concentration이 커지거나 더 좋은 alternative가 나타날 수 있다.

**Result:** maintained company judgment는 그대로인데 decision relevance는 달라질 수 있으므로 Decision Context separation이 필요하다.

### 7.7 처음 보는 신규 종목

업데이트할 prior maintained judgment가 없다.

**Result:** 동일 semantic model로 최초 Judgment State를 형성할 수 있지만 모든 workflow가 prior thesis에서 시작한다고 가정하면 안 된다.

## 8. 기존 6-Step Journey는 어떻게 되는가?

기존 sequence:
1. 변화 / opportunity detect
2. reference와 비교하며 이해
3. material / non-material 구분
4. evidence / uncertainty 평가
5. judgment structure 형성 / 업데이트
6. conviction recalibration

현재 critique:
- evidence evaluation은 주로 upstream Research authority에 속하며 Design이 새 epistemic authority처럼 복제하면 안 됨
- materiality는 intrinsic information classification이 아니라 relational함
- `Judgment Bearing` relation이 빠져 있음
- revision outcome은 strengthen / weaken보다 다양함
- lineage / update trace가 빠져 있음
- formation과 updating은 semantic model은 공유하지만 process는 동일하지 않음

현재 replacement candidate:

```text
Orient
→ Contextualize
→ Link to Judgment
→ Assess Impact
→ Revise / Retain / Resolve Uncertainty
→ Recalibrate
→ Trace
```

이것은 analytical update logic이며 mandatory screen flow가 아니다.

## 9. 기존 Information Model에 대한 판정

### 유지하되 reinterpret

- **State & Change** → maintained state와 update trigger / signal로 분리
- **Context & Relationships** → explicit reference / interpretive context + judgment-bearing relation으로 유지·확장
- **Evidence & Uncertainty** → upstream epistemic input으로 유지하되 Research authority 보존, downstream conviction과 uncertainty를 구분
- **Judgment Structure + Conviction** → 유지하되 conviction을 단순한 final stage가 아니라 local meta-property로 봄

### 교체

- **Significance / Materiality as an information layer** → **Judgment Impact as a relational assessment**로 교체

### 추가

- **Judgment-Bearing Relation** — new information과 affected judgment component 사이의 explicit mapping
- **Update Trace / Lineage** — material judgment revision의 역사 보존
- **Decision Context separation** — intrinsic company truth가 아니라 downstream overlay

## 10. Current Working Recommendation

### Recommendation

두 개의 model을 분리한 architecture로 진행한다.

1. **Judgment Semantic Model** — maintained judgment state, epistemic input, reference/context, judgment-bearing relation, Decision Context, conviction/uncertainty annotation, update trace.
2. **Judgment Update Logic** — `Orient → Contextualize → Link → Assess Impact → Revise/Retain/Unresolved → Recalibrate → Trace`.

`Judgment Impact`는 fixed information property 또는 scalar materiality score가 아니라 relational하고 context-bound한 assessment로 본다.

### Recommendation Strength

**Strong**

### 왜 Very Strong이 아닌가

- real investor validation이 아직 없음
- maintained judgment component의 적절한 granularity가 unresolved
- user-visible vs system-side depth가 아직 미결정
- user-authored vs AI-synthesized judgment boundary가 열려 있음

### Main Alternatives

- 기존 linear information hierarchy 유지
- pure claim/evidence graph를 semantic + interaction model 양쪽으로 사용
- persistent judgment state 없이 event triage + episodic Q&A 중심으로 축소

각각 더 단순한 장점은 있지만 현재는 traceable revision에 필요한 distinction을 지우거나 주요 scenario에서 더 많이 깨진다.

### Failure / Reversal Conditions

다음이 확인되면 model을 수정한다.
- explicit judgment-bearing link 유지가 너무 비싸거나 artificial함
- user가 revision lineage를 의미 있게 사용하지 못함
- `Judgment Impact`가 opaque scoring model 없이 설명 가능하지 않음
- system-side structuring이 useful revision보다 anchoring을 더 강하게 만듦
- user Decision Context와 maintained investment judgment를 실제 product에서 분리하기 어려움

## 11. Batch Consensus / CEO Critical / AI-Owned

### Batch Consensus Candidate

- Process와 semantic object model을 분리한다.
- Materiality를 intrinsic information property가 아니라 judgment-relative impact relation으로 본다.
- Judgment-bearing linkage를 필수적으로 추가한다.
- Conviction과 uncertainty는 local하게 유지하고 directional judgment와 분리한다.
- Material revision에는 update lineage를 보존한다.
- Decision Context는 intrinsic company/research view와 구분한다.

### CEO Critical Decision

**현재 없음.**

아직 모두 Working architecture finding이다. 이를 Stock_vis 전체의 durable user mental model, cross-surface information architecture, human/AI judgment-authority boundary로 공식 채택하려는 시점에 CEO-critical이 된다.

### Deferred / AI-Owned

- `Judgment Impact`와 대안 명칭 중 최종 naming
- exact update-state label
- local conviction의 categorical / verbal / visual / numeric representation
- update history representation detail
- interaction order와 progressive-disclosure detail
