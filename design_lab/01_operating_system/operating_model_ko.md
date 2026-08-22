# Stock_vis Design Lab Operating Model

> **한국어 Companion 문서**  
> 원문: [`operating_model.md`](operating_model.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않으며, 의미 차이가 있을 경우 영어 원문을 기준으로 해소한다.

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-20  
**Owner:** Stock_vis Design Lab  
**Operational Use:** 2026-08-20 Project Owner가 working bootstrap baseline으로 운영 사용 승인

## 1. Core Operating Principle

> **The Design Lab should maximize delegated exploration while concentrating CEO attention on consequential decisions.**

Design Lab은 작은 디자인 선택에 대해 CEO의 지속적인 승인을 받는 구조로 운영하지 않는다. 탐색, 비교, 비판, 통합, 되돌릴 수 있는 실행은 기본적으로 위임하고, consequential decision에만 Project Owner의 집중된 attention을 사용한다.

## 2. Roles

### CEO / Project Owner

CEO / Project Owner는 Design Lab의 consequential decision에 대한 최종 authority를 가진다. 특히 장기 Purpose, Principles, user mental model, major information architecture, authority boundary, cross-Lab 의미, 장기 dependency를 실질적으로 규정하는 결정이 이에 해당한다.

CEO에게는 정리되지 않은 중간 탐색 결과가 아니라 준비된 Decision Package를 제공한다.

### Design Lab Lead / AI Co-researcher

Design Lab Lead는 문제를 framing하고, 작업을 분해하고, specialist perspective를 선택하고, exploration을 위임하고, alternative를 비교하고, counterargument를 검토하고, Research consistency를 확인하고, finding을 통합하고, decision consequence를 판단하고, 필요한 경우 escalation하며, 승인된 boundary 안에서 자율적으로 실행한다.

Lead는 자신의 최초 제안을 방어할 의무가 없다. Evidence나 critique가 더 나은 대안을 지지하면 기존 제안을 수정하거나 교체한다.

### Specialist Agents

Specialist Agent는 Lead가 정의한 brief 안에서 bounded research, design, critique, simulation, validation, documentation을 수행한다.

Agent output은 synthesis를 위한 input이다. Agent가 만들었다는 이유만으로 authoritative decision이나 Design Knowledge가 되지 않는다.

## 3. Batch Consensus by Default

기본 협업 단위는 isolated micro-decision이 아니라 하나의 coherent design question 또는 architecture boundary다.

기본 흐름은 다음과 같다.

```text
Coherent Design Problem
→ delegated exploration
→ alternatives and counterarguments
→ failure / edge-case review
→ Research and Design consistency review
→ Lead synthesis
→ recommendation with recommendation strength
→ CEO decision when required
→ autonomous execution within the approved boundary
```

하나의 semantic choice 자체가 consequential한 경우에는 Micro-consensus가 유용할 수 있지만, 기본 운영 방식은 아니다.

### 3.1 Batch Size

Batch는 하나의 coherent question을 함께 최적화할 만큼 충분히 커야 하지만, CEO가 trade-off를 이해하고 의미 있는 결정을 할 수 있을 정도로는 작아야 한다.

따라서 Batch 크기는 consequence와 uncertainty에 비례해 조정한다.

다음 두 극단을 피한다.

- 하나의 architecture question을 반복적인 저가치 approval로 잘게 쪼개는 것
- 서로 관련이 약한 결정을 하나의 과도하게 큰 package로 묶는 것

## 4. Decision Tiers

Decision Tier는 사전에 정해둔 이름이나 카테고리보다 **consequence**를 우선 기준으로 판단한다. 아래 예시는 heuristic이다.

### Tier 1 — CEO Direct Decision

장기 Design Lab 또는 Stock_vis experience를 실질적으로 규정하고 Project Owner의 직접적인 judgment가 필요한 결정에 사용한다.

대표적인 signal은 다음과 같다.

- Purpose 또는 Philosophy 변경
- core Design Principle
- major user mental model
- major information architecture
- human / AI authority boundary
- Research Knowledge에 대한 material interpretation
- cross-Lab semantic impact
- 높은 irreversibility 또는 long-term dependency
- 기존의 중요한 approved direction을 뒤집는 결정

Process:

```text
Explore
→ compare alternatives
→ critique and stress-test
→ synthesize
→ direct CEO discussion
→ explicit decision
```

### Tier 2 — Batch Decision

넓은 탐색이 필요하지만 CEO가 모든 하위 결정을 각각 승인할 필요는 없는 중요한 구조적 선택에 사용한다.

Lead가 관련된 결정을 하나의 coherent Decision Package로 통합한다. CEO가 큰 방향을 승인하면 그 boundary 아래의 reversible detail은 위임된다.

### Tier 3 — Delegated Decision

승인된 Purpose, Principles, architecture, guardrail에서 자연스럽게 파생되는 reversible choice에 사용한다.

Lead가 반복적으로 승인을 요청하지 않고 결정하고 진행한다.

Tier 3 작업 중 더 높은 consequence의 문제가 발견되면 다시 분류하고 escalation한다.

## 5. Consequence-Based Escalation

Escalation 판단에는 다음 요소를 고려한다.

- **Consequence** — 얼마나 많은 downstream work 또는 user experience가 해당 결정에 의존하는가
- **Uncertainty** — 현재 근거가 얼마나 약하거나 논쟁적인가
- **Irreversibility** — 되돌리기가 얼마나 어렵거나 비용이 큰가
- **Semantic Reach** — Design Knowledge 또는 product behavior 전반의 의미를 얼마나 넓게 바꾸는가
- **Long-term Dependency** — 얼마나 많은 후속 결정이 이를 상속하게 되는가
- **Cross-Lab Impact** — Research, Product, Engineering 또는 다른 authority boundary에 영향을 주는가

특히 다음 경우에는 escalation이 필요하다.

1. 기존 approved meaning을 실질적으로 변경해야 하는 경우
2. 새로운 core Design Concept 또는 Principle이 필요해 보이는 경우
3. Approved Research Knowledge를 위반하거나 잘못 표현할 가능성이 있는 경우
4. major mental model, IA boundary, authority boundary를 변경해야 하는 경우
5. durable schema, ontology, Design System 또는 기타 장기 dependency를 도입하는 경우
6. 주요 대안 사이에 중요한 value judgment가 필요한 경우
7. recommendation strength가 낮은데 decision consequence가 높은 경우
8. 새로운 evidence가 CEO-approved direction을 실질적으로 흔드는 경우

## 6. Recommendation Strength

중요한 recommendation에는 CEO가 추천의 강도를 해석하는 데 도움이 될 때 명시적인 Recommendation Strength를 표시한다.

- **Very Strong** — 현재 evidence와 상위 constraint 아래에서 명확히 우세하며 중요한 새로운 evidence 없이는 뒤집힐 가능성이 낮음
- **Strong** — 현재 우세하지만 후속 design 또는 test를 통해 의미 있는 수정이나 reversal 가능성이 남아 있음
- **Moderate** — 선호 방향은 있으나 credible alternative가 남아 있고 validation 결과에 따라 바뀔 수 있음
- **Weak / Tentative** — evidence가 제한적이거나 구조가 아직 unresolved인 exploratory working proposal

중요한 recommendation에는 보통 다음을 포함한다.

- Recommendation
- Recommendation Strength
- Why
- Main Alternative(s)
- Key Trade-offs
- Failure / Reversal Conditions

Strength는 새로운 evidence에 따라 변경될 수 있다.

## 7. Decision Package

Tier 1과 중요한 Tier 2 decision에서는 이전 작업을 CEO가 집중해서 판단할 수 있는 package로 압축한다.

필요에 따라 다음을 포함한다.

- 결정해야 할 내용
- 왜 지금 중요한지
- 현재 evidence와 constraint
- 현실적인 alternatives
- 주요 trade-offs
- strongest counterargument
- Lead recommendation
- Recommendation Strength
- failure / reversal conditions
- CEO가 실제로 판단해야 하는 정확한 질문

Agent output이나 모든 exploratory branch를 그대로 재현하지 않는다.

### 7.1 CEO와 Lead의 의견이 다를 때

Lead는 결론이 내려지기 전에 중요한 의견 차이를 조용히 숨기지 않는다. 자신이 보는 위험, CEO의 안이 더 나을 수 있는 조건, Lead recommendation이 실패할 조건을 설명한다.

CEO가 consequential decision을 내리면 해당 결정은 downstream work의 approved constraint가 된다.

Lead는 그 boundary 안에서 실행하되, 중요한 새로운 evidence, Research conflict, materially changed condition이 발생하면 재검토를 위해 다시 escalation할 수 있다.

## 8. Execution Depth

Process depth는 consequence와 uncertainty에 비례해야 한다.

Local하고 reversible한 선택은 Lead가 직접 처리하거나 작은 agent set으로 충분할 수 있다. High-consequence semantic 또는 architectural decision은 더 넓은 exploration, independent critique, 필요한 경우 Research consistency review, explicit escalation을 거쳐야 한다.

Design Lab은 다음 두 극단을 모두 피한다.

- consequential decision을 충분히 검토하지 않는 것
- routine reversible work에 heavyweight governance를 적용하는 것

## 9. Default Work Cycle

```text
Design Problem
→ frame the problem and success condition
→ classify consequence and uncertainty
→ compose the minimum useful agent team
→ explore / design / challenge
→ synthesize
→ decide autonomously or escalate by tier
→ build / prototype / document as appropriate
→ test or observe
→ capture reusable learning when justified
→ inspect the Lab process for recurring friction
```

마지막 단계는 일반 Design work를 Design Lab Evolution process와 연결한다.
