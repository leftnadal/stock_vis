# Workstream 001 — Investment Judgment Experience Foundation

> **한국어 Companion 문서**  
> 원문: [`brief.md`](brief.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않으며, 의미 차이가 있을 경우 영어 원문을 기준으로 해소한다.

**Status:** Working  
**Version:** 0.1  
**Started:** 2026-08-21  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 Workstream. 작업 중 Tier 1 issue가 발견되면 escalation

## 1. Purpose

이 Workstream은 Stock_vis가 사용자의 investment judgment 형성, 수정, 비교, calibration을 어떻게 지원해야 하는지를 연구한다.

목표는 screen을 너무 일찍 정의하는 것이 아니다. 사용자의 judgment problem과 이를 지원하는 데 필요한 information / experience structure에 대한 검증된 working model을 만드는 것이다.

이 Workstream은 현재 Design Lab의 working purpose인:

> **Better Investment Judgment**

및 Stock_vis의 더 넓은 purpose인:

> **Better Investment Decisions**

아래에서 수행된다.

## 2. Authority와 Boundary

- Research concept와 Research Knowledge는 계속 `research_lab/`에서 governance한다.
- 이 Workstream은 Research Knowledge를 user experience 관점에서 interpret할 수 있지만 공식 Research concept를 재정의해서는 안 된다.
- Research Lab에서 승인된 Understanding, Judgment, Decision, Action의 구분을 보존해야 한다.
- Synthetic persona와 agent agreement는 exploratory tool이며 user evidence가 아니다.
- Workstream output은 기본적으로 Working이며 자동으로 Design Knowledge, Principle, approved product architecture가 되지 않는다.

## 3. Core Design Problem

현재 working framing:

> 투자자는 복잡하고 변화하며 불확실한 현실 속에서 investment judgment를 형성하고 지속적으로 업데이트하기 어렵다.

특히 중요하게 반복되는 질문은:

> 무엇이 변했는가, 왜 중요한가, 그리고 내 판단을 바꿔야 하는가?

이 framing은 검증할 hypothesis이며 승인된 final problem definition이 아니다.

## 4. Scope

이 Workstream은 하나의 coherent batch로 다음을 검토한다.

1. **User Judgment Problems**
   - 최초 judgment formation
   - 새로운 evidence / event 이후 judgment updating
   - alternatives 사이의 comparative judgment
   - uncertainty와 conflicting evidence 아래의 judgment

2. **Judgment Mental Model**
   - investment judgment를 단일 score나 bullish/bearish label보다 claims, drivers, risks, uncertainties의 structured set으로 표현하는 것이 더 적절한지
   - false precision으로 축소하지 않으면서 conviction이 judgment와 어떤 관계를 가져야 하는지

3. **Judgment Journey**
   - 사용자가 어떻게 변화나 기회를 알아차리고, contextualize하고, evaluate하고, connect하고, revise하고, calibrate하는지
   - 하나의 common loop가 신규 opportunity와 existing holding 모두를 지원할 수 있는지

4. **Information Model**
   - judgment를 지원하는 데 필요한 information structure는 무엇인지
   - state/change, context/relationships, evidence/uncertainty, significance/materiality, judgment structure 사이의 관계

5. **Logical Experience Architecture**
   - `Orient → Understand → Judge` 같은 model이 유용한지
   - comparison이 context mechanism인지, judgment mode인지, 별도 experience space인지

## 5. Primary Scenarios

Working model은 최소한 다음 scenario에서 stress-test를 통과해야 한다.

- 보유 종목의 sharp price decline
- mixed signal을 포함한 earnings release
- 이전에 몰랐던 신규 종목 발견
- 기존 보유 종목과 신규 opportunity 비교
- conflicting 또는 incomplete evidence
- 시간 또는 attention 제약이 있는 사용자

실질적으로 다른 judgment problem을 드러내는 경우 추가 scenario를 넣을 수 있다.

## 6. Challenge할 Working Hypotheses

다음은 이전 exploratory discussion에서 가져온 hypothesis이며, 기본적으로 유지해야 하는 결론이 아니다.

- investment judgment는 하나의 score보다 structured form일 가능성이 높다.
- 크게 보이는 변화와 judgment materiality는 다를 수 있다.
- Fact / Interpretation / Expectation을 experience에서 구분할 필요가 있을 수 있다.
- 하나의 common judgment loop가 judgment formation과 updating을 모두 지원할 수 있다.
- comparison은 cross-cutting capability이며 동시에 comparative judgment mode가 될 수 있다.
- `Orient → Understand → Judge`는 useful logical experience model일 수 있다.
- conviction은 최대화가 아니라 evidence와 uncertainty에 맞춰 calibrate되어야 한다.

Workstream은 이 hypothesis들을 retain, revise, narrow, replace, reject할 수 있다.

## 7. Exploration Perspectives

Design Lab Lead는 다음 중 최소한의 유용한 관점을 task에 맞게 구성한다.

### Explore
- investor / user problem perspective
- behavioral / cognitive perspective
- financial product / information-design benchmarking
- 관련 academic / industry evidence

### Design
- information architecture
- interaction / sensemaking
- information representation / progressive disclosure

### Challenge
- design critique
- adversarial / synthetic persona stress-test
- 필요한 경우 accessibility / cognitive-load review
- Research consistency review

Workstream 진행에 따라 perspective를 추가하거나 제거할 수 있다.

## 8. Expected Outputs

Workstream은 다음을 만들어야 한다.

- 더 명확한 problem framing
- 주요 alternatives와 rejected framing
- recommended working judgment model
- 정당화된다면 recommended judgment journey / loop
- recommended information model
- evidence가 지지할 때만 logical experience architecture
- unresolved questions / validation needs
- Research Trigger Candidate
- reusable Design Knowledge candidate
- 작업 중 발견된 Design Lab operating friction

## 9. Escalation

일반적인 exploration이나 reversible modeling choice는 escalation하지 않는다.

다음 내용을 material하게 변경하는 문제가 발견되면 escalation한다.

- Design Lab Purpose / Philosophy
- core Design Principle
- Research–Design authority boundary
- 여러 future product surface를 지배할 가능성이 높은 major user mental model
- durable downstream dependency가 큰 major information architecture
- human / AI judgment authority
- 기타 high-consequence cross-cutting commitment

## 10. Completion Condition

Leading model이 materially different scenario와 alternative를 충분히 challenge받고, key Research boundary가 확인되고, 주요 failure condition이 명시되며, 남은 uncertainty가 prototype 또는 further validation으로 넘길 수 있을 정도로 분명해지면 synthesis 준비가 된 것으로 본다.
