# Stock_vis Design Lab Evolution Model

> **한국어 Companion 문서**  
> 원문: [`evolution.md`](evolution.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않으며, 의미 차이가 있을 경우 영어 원문을 기준으로 해소한다.

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-20  
**Owner:** Stock_vis Design Lab  
**Operational Use:** 2026-08-20 Project Owner가 working bootstrap baseline으로 운영 사용 승인

## 1. Purpose

Design Lab 자체도 사용하면서 개선되어야 하는 하나의 design system이다.

이 문서는 Design work 중 발견되는 반복적인 friction, failure, structural mismatch가 Lab의 operating model, agent protocol, knowledge structure, documentation 또는 기타 내부 architecture를 어떻게 바꿀 수 있는지를 정의한다. 초기 구조가 영원히 맞아야 한다고 가정하지 않는다.

목표는 rigidity와 governance sprawl을 모두 피하면서 controlled evolution을 가능하게 하는 것이다.

## 2. Core Evolution Loop

```text
Operate
→ Observe
→ Diagnose
→ Adapt
→ Validate
```

### Operate

현재 Design Lab 구조를 사용해 실제 작업을 수행한다.

### Observe

Friction, 반복적인 confusion, missed escalation, synthesis cost, authority ambiguity, documentation failure, agent failure 등 Lab 구조가 Purpose를 제대로 지원하지 못한다는 signal을 관찰한다.

### Diagnose

문제가 다음 중 어디에 해당하는지 판단한다.

- 한 task에만 local한 문제
- 여러 future work에서 반복될 가능성이 높은 문제
- Lab 전체에 structural하고 consequential한 문제

### Adapt

진단된 scope에 맞는 가장 작은 변화를 적용한다.

### Validate

후속 work에서 해당 변화가 문제를 해결했는지, 새로운 failure mode를 만들었는지 관찰한다.

## 3. Three Levels of Change

### Local Fix

현재 workstream 밖에는 영향이 거의 없을 것으로 예상되는 task-specific adjustment.

예: 한 agent output을 짧게 만들기, 한 prototype exercise 순서 변경, temporary role 조정.

Design Lab Lead가 formal governance나 CEO approval 없이 즉시 적용할 수 있다.

### Operating Improvement

여러 future task를 개선할 가능성이 있는 반복적인 working pattern의 변경.

예: Agent Output Contract 변경, 반복 workflow에서 critique를 더 앞당기기, workstream write-back 명확화, 특정 recurring task class의 default agent composition 조정.

Lead는 승인된 authority 안에서 reversible Operating Improvement를 적용할 수 있고, future agent가 알아야 하는 persistent change라면 관련 문서를 갱신한다.

Authority, semantics, long-term dependency를 실질적으로 바꾸면 Structural Change로 재분류한다.

### Structural Change

Design Lab의 Purpose, Philosophy, core operating authority, major knowledge architecture, Research–Design boundary 또는 기타 durable cross-cutting structure에 material하게 영향을 주는 변경.

Structural Change는 Operating Model의 escalation rule에 따라 consequence analysis와 CEO discussion을 거친다.

## 4. Anti-Overreaction Rule

> **Do not promote one-off friction into permanent governance too quickly.**

한 번 불편했던 task가 자동으로 새로운 문서, agent role, principle, process stage, approval requirement를 정당화하지 않는다.

틀려도 비용이 낮다면 Local Fix를 먼저 선호한다.

Repeated friction, cross-workstream recurrence, high-consequence failure가 formal operating change를 더 강하게 정당화한다.

## 5. Lab이 진화해야 할 수 있다는 Signal

다음은 useful signal의 예이며 exhaustive trigger는 아니다.

- agent가 필요한 context 또는 authority를 반복적으로 찾지 못함
- agent output을 synthesis하는 비용이 지속적으로 큼
- independent critique가 너무 늦게 들어와 rework를 막지 못함
- design commitment 후에 Research consistency 문제가 반복 발견됨
- Micro-consensus가 다시 나타나 속도를 늦추지만 decision quality는 개선하지 못함
- Tier 3 decision이 의도하지 않은 semantic commitment를 누적함
- CEO escalation이 지속적으로 너무 많거나 너무 적음
- Decision Package가 너무 커져 coherent review가 어려움
- workstream finding이 과도하게 formalize되거나 반복적으로 유실됨
- Design Knowledge와 Working exploration을 구분하기 어려움
- documentation structure의 maintenance cost가 retrieval value보다 커짐
- Lead가 지속적인 synthesis bottleneck이 됨
- 새로운 Design work가 current Lab structure에 반복적인 exception 없이는 맞지 않음

이 signal들은 자동 structural change가 아니라 **diagnosis를 시작하는 신호**다.

## 6. Delegation Reversal Conditions

현재 Design Lab은 delegated exploration과 approved boundary 아래의 autonomous execution을 선호한다.

다음 failure가 반복되면 delegation 범위를 줄이거나 재구성해야 한다.

- 중요한 semantic / architectural commitment를 routine Tier 3로 처리함
- approved Research / Design authority와 반복적으로 충돌함
- 중요한 CEO-approved constraint가 조용히 약화됨
- batch decision이 너무 넓어 CEO가 의미 있게 review하기 어려움
- autonomous execution이 costly downstream reversal을 반복적으로 만듦

반대로 어떤 class의 decision이 low-risk, reversible하고 기존 authority로 안정적으로 constrain된다는 것이 반복적으로 확인되면 delegation을 확대할 수 있다.

## 7. Documentation and Versioning

Lab은 future consistency와 traceability에 필요한 정도까지만 operating change를 문서화한다.

- Local Fix는 보통 permanent record가 필요하지 않음
- Operating Improvement는 지속될 behavior라면 관련 living document를 갱신
- Structural Change는 explicit review를 거치고 consequential한 경우 해당 structure가 생긴 뒤 적절한 Decision Record를 남김

Material governance 또는 authority change가 일어날 때 historical meaning을 조용히 덮어쓰지 않는다.

## 8. 다른 Bootstrap 문서와의 관계

- `operating_model.md` — Lab이 현재 어떻게 운영되고 결정하는지 정의
- `agent_protocol.md` — specialist agent work를 어떻게 구성하고 통합하는지 정의
- `knowledge_lifecycle.md` — Design work가 reusable Design Knowledge로 발전하는 방법 정의
- 이 문서 — Lab 운영에서 나온 evidence가 위 시스템 자체를 어떻게 변화시킬 수 있는지 정의

Evolution Model은 별도의 approval bureaucracy가 아니다. Bootstrap 구조를 의도적으로 provisional하고, testable하고, 개선 가능하게 유지하는 mechanism이다.
