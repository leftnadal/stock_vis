# Stock_vis Cross-Lab Research Interface — Math Lab Working Contract

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab  
**Scope:** Math Lab side of the Research ↔ Math ↔ Design federation

## 0. 한눈에 보는 요약

Stock_vis의 Lab들은 하나로 합쳐지는 것이 아니라 **각자의 authority를 유지한 채 서로에게 새로운 연구 Trigger를 제공하는 federation**으로 운영한다.

Research Understanding은 Math 연구를 촉발할 수 있고, Math finding은 Research의 mechanism/meaning 연구를 촉발할 수 있으며, Design/User finding은 Research 또는 Math의 새 질문을 만들 수 있다. 그러나 Lab 간 전달이 source result의 의미나 authority를 자동 이전하지 않는다.

## 1. Core Federation Principle

> **Cross-Lab transfer creates a traceable research dependency or trigger; it does not automatically transfer epistemic authority or confer independent confirmation.**

## 2. 기본 흐름

```text
Research Understanding
        ↓
Quantitative Operationalization
        ↓
Math Research Trigger / Case
        ↓
Quantitative Claim / Knowledge
        ↓
Interpretation / Mechanism Trigger
        ↓
Research Investigation
```

Design은 다음과 같이 연결될 수 있다.

```text
Math forecast / uncertainty
        ↓
Design representation
        ↓
User interpretation / behavior finding
        ↓
Math calibration trigger
or Research explanation trigger
```

## 3. Authority Boundary

### Research Lab

- 기업·산업·시장 개념의 의미
- Research Knowledge / Understanding
- causal / mechanistic / semantic interpretation

### Math Lab

- numerical proxy definition
- target / feature / model use
- statistical and predictive interpretation
- quantitative claim / validation

### Design Lab

- user-facing representation
- interaction / IA
- judgment-support experience

### Cross-Lab Review

- concept → proxy fidelity
- translation loss
- source ancestry / independence
- scope/horizon compatibility
- material dependency

## 4. Cross-Lab Handoff Types

현재 최소 transfer types:

1. **research_trigger**
2. **quantitative_operationalization**
3. **interpretation_or_mechanism_trigger**
4. **composition_input**
5. **dependency_change_notice**

recipient Lab은 accepted / reframed / merged / deferred / declined를 선택할 수 있다.

## 5. Handoff Record

material handoff에는 필요에 따라 다음을 보존한다.

- source_lab
- source_object_id
- source_object_version
- source_authority / source status
- recipient_lab
- transfer_type
- requested_use
- allowed_use
- source_scope / entity / horizon / conditions
- operationalization
- alternative operationalizations
- translation_loss
- source ancestry
- independence profile
- recipient disposition
- created Case refs
- dependency review conditions

source object를 복사해 recipient Lab의 새 authority처럼 만들지 않는다.

## 6. Operationalization Map

Research concept를 Math 변수로 바꿀 때 다음을 분리한다.

```text
Research Concept
→ Operational Definition
→ Observable Variable / Proxy
→ Quantitative Hypothesis
```

각 proxy에는 최소한 다음 질문을 적용한다.

### Construct Fidelity

원 concept의 중요한 의미를 얼마나 포착하는가.

### Source Independence

원 source/derivation과 얼마나 독립적인 evidence인가.

두 축은 독립적이다.

- high fidelity + low independence 가능
- low fidelity + high independence 가능

따라서 높은 predictive performance가 곧 독립적 corroboration을 의미하지 않는다.

## 7. Circularity / Shared Ancestry

다음 loop를 탐지한다.

```text
Research Understanding
→ ChainSight semantic relation
→ Math feature
→ Math result
→ original Understanding의 independent evidence로 재사용
```

shared ancestry가 있다고 결과가 무효인 것은 아니다. 그러나 독립성은 제한된다.

independence status 후보:

- independent
- partially_dependent
- shared_ancestry
- self_derived
- unknown

## 8. Math → Research Trigger

Math Lab이 correlation/prediction을 발견해도 causal mechanism을 자동 선언하지 않는다.

예:

```text
Neighbor return predicts target return
```

Math Lab이 말할 수 있는 범위:

- predictive association
- effect size
- scope / horizon
- robustness / replication
- failure regime

Research Trigger가 질문할 수 있는 것:

- supply-chain mechanism인가
- common factor인가
- ETF / liquidity flow인가
- information diffusion인가
- third-variable explanation인가

## 9. Research → Math Trigger

Research Understanding을 그대로 truth label로 넣지 않는다.

예:

```text
AI data-center capex acceleration
```

가능한 proxy:

- relevant firms' capex growth
- estimate revisions
- ChainSight network breadth
- volume/return response

서로 다른 proxy를 비교하고 translation loss를 기록한다.

## 10. Source Revision Propagation

source object가 바뀌었다고 downstream 결과를 자동 폐기하거나 자동 수정하지 않는다.

```text
Source Revision
→ Dependency Change Notice
→ Review Obligation
→ retain / re-evaluate / rerun / restrict / retire
```

## 11. Cross-Lab Composition

Research + Math + Design output을 합칠 때 component validity를 자동 상속하지 않는다.

특히 확인한다.

- horizon mismatch
- universe mismatch
- duplicate information
- shared source ancestry
- scope / boundary mismatch
- conflicting uncertainty
- new composition assumption

material combined output은 별도 Composition Evaluation을 받는다.

## 12. Product Boundary

Cross-Lab Handoff 또는 Math prediction만으로 자동 product action을 만들지 않는다. user exposure, alert, ranking, recommendation 등은 downstream Design/Product governance를 거친다.

## 13. Future Neutral Interface Location

현재 이 문서는 Math Lab working contract다. Federation-wide interface가 안정되면 `math_lab/` 밖의 neutral canonical location으로 이동할 수 있다. 그 이동 자체는 cross-Lab authority review 대상이다.
