# Workstream 001 — Exploration Batch 05

> **한국어 Companion 문서**  
> 원문: [`batch_05_wireflow_prototype.md`](batch_05_wireflow_prototype.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 CEO-approved semantic intent와 관련 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — 승인된 DL-DR-0001 아래의 reversible prototype architecture

## Low-Fidelity Wireflow / Prototype Exploration

## 1. Purpose

이번 Batch는 Batch 04의 interaction architecture를 실제 low-fidelity user flow로 내려본다. Visual styling을 정하는 작업이 아니라, 빠른 orientation, maintained judgment, evidence traceability, Human–AI authority를 유지하면서도 review fatigue를 만들지 않는 interaction 구조를 찾는 것이 목적이다.

두 prototype family를 비교한다.

- **Prototype A — State-centered + explicit Change Review**
- **Prototype B — Judgment Home + integrated change diff**

그리고 5개의 현실적인 scenario에서 둘을 stress-test한 뒤 더 좋은 hybrid가 있는지 확인한다.

`DL-DR-0001 — Human–AI Judgment Authority Boundary`는 그대로 hard constraint다.

## 2. Prototype A — State-Centered + Explicit Change Review

### Core wireflow

```text
Portfolio / Orientation
    ↓ material change 또는 company 선택
Judgment Snapshot
    ├─ component 확인 → Component Detail → Evidence / Trace
    └─ material change 검토 → Focused Change Review
                                ↓
                      adopt / modify / reject /
                      retain / defer / unresolved
                                ↓
                       Updated User Judgment
                                ↓
                             History
```

### Low-fidelity screen contract

#### A1. Orientation

```text
TODAY — 3 ITEMS MAY DESERVE ATTENTION

IREN        -14% price move
             System: material thesis change 없음
             Why look: volatility / valuation 변화

NVDA        Earnings
             Judgment component 2개 영향
             Demand ↑ / Margin uncertainty ↑

CEG         Regulatory filing
             Core risk 1개가 약화됐을 가능성
```

Entry point는 단순 event magnitude보다 **왜 attention을 써야 하는가**를 보여준다.

#### A2. Judgment Snapshot

```text
IREN — CURRENT JUDGMENT

AI demand                     Strong / stable
Power advantage               Moderate / stable
Execution                     Moderate / watch
Valuation                     Price decline 이후 improved

Recent material judgment change: 없음
Open uncertainty: build timing
System ↔ My View divergence: Execution

[Review latest change]   [Explore judgment]
```

#### A3. Focused Change Review

```text
WHAT CHANGED?
Q2 earnings + guidance

WHAT DOES IT BEAR ON?
Demand             strengthened
Execution          weakened
Margins            unresolved

WHY?
[3 supporting inputs] [2 challenging inputs]

SYSTEM SYNTHESIS UPDATE
Demand: stronger
Execution: weaker

MY CURRENT VIEW
Demand: moderate
Execution: unchanged

Material user-state change가 있을 때만:
[Adopt] [Modify] [Keep my view] [Leave unresolved]
```

### Strengths

- event와 judgment impact를 강하게 분리
- multi-component change에 강함
- provenance와 update lineage 우수
- material human action이 필요한 지점이 명확
- disagreement 처리에 강함

### Weaknesses

- 단순 변화에도 별도 transition이 생길 수 있음
- 잘못 쓰면 inbox / approval workflow가 됨
- routine monitoring을 과도하게 formalize할 위험
- 신규 기업에서는 change review로 시작하는 것이 부자연스러움

## 3. Prototype B — Judgment Home + Integrated Diff

### Core wireflow

```text
Portfolio / Search
    ↓
Judgment Home
    ├─ current components
    ├─ recent change badge / inline diff
    ├─ system ↔ user divergence marker
    └─ component expand → evidence / history / edit
```

기본적으로 별도 Change Review는 없다.

### Low-fidelity screen contract

```text
NVDA — JUDGMENT

Demand       ↑ strengthened
             New: hyperscaler capex evidence
             My view: adopted
             [Why?]

Margins      ? more uncertain
             New: mix / cost evidence conflicts
             My view: unresolved
             [Review evidence]

Execution    stable

Recent event: Q2 earnings
[See full event impact]
```

### Strengths

- transition이 적음
- judgment가 항상 organizing object로 유지됨
- 단순 변화에 빠름
- learning model이 단순
- review inbox fatigue 위험이 낮음

### Weaknesses

- 복잡한 event가 여러 card에 흩어질 수 있음
- 하나의 event가 여러 component에 미치는 causal story를 user가 직접 재구성해야 할 수 있음
- material system proposal이 current judgment와 섞여 보일 수 있음
- history / provenance가 분산될 수 있음
- high-consequence disagreement에서는 결국 더 강한 focused interaction이 필요

## 4. Five-Scenario Stress Test

### Scenario 1 — 급락했지만 thesis-changing evidence는 없음

**User need:** drawdown이 investment judgment를 바꾸는지, 아니면 price / valuation / urgency만 바꾸는지 빨리 파악.

**Prototype A**

```text
Orientation: IREN -14%
→ Snapshot: material thesis change 없음
→ evidence가 궁금할 때만 focused review
```

이 경우 full Change Review는 과도한 friction이다.

**Prototype B**

```text
IREN Judgment Home
Price trigger badge: -14%
Thesis components: unchanged
Valuation: improved
[Why no thesis change?]
```

**Result:** low-complexity case에서는 B 우세.

**Design implication:** 모든 trigger가 dedicated review를 열 필요는 없다.

---

### Scenario 2 — Mixed earnings: 일부 driver는 좋아지고 일부는 악화

**User need:** 하나의 event가 여러 judgment component에 서로 다른 방향으로 미친 영향을 이해.

**Prototype A**

Focused Change Review가 event를 하나의 causal unit으로 보존하고 affected component를 한 번에 요약한 뒤 drill-down 가능.

**Prototype B**

Inline diff는 빠르지만 user가 여러 card에서 cross-component story를 재구성해야 함.

**Result:** A가 명확히 우세.

**Design implication:** multi-component 또는 conflicting event는 focused review mode가 유리.

---

### Scenario 3 — System과 user가 material하게 disagree

예:

```text
System: Execution thesis weakened
User: Execution thesis unchanged
```

**Prototype A**

Focused review에서 disagreement, contrary evidence, user response를 명확히 보여줄 수 있고 full dual-state를 항상 보여줄 필요는 없음.

**Prototype B**

Divergence marker는 passive visibility에는 충분하지만, disagreement를 검토하거나 유지하는 순간 deeper local interaction이 필요.

**Result:** consequential moment에서는 A 우세, 평소 visibility에는 B로 충분.

**Design implication:** disagreement는 평소에는 가볍게, 실제 review할 때만 깊게 보여준다.

---

### Scenario 4 — 처음 보는 기업

**User need:** prior judgment를 update하는 것이 아니라 initial judgment를 형성.

**Prototype A**

Change-centric path는 어색하다. System-generated initial Judgment Snapshot으로 Change Review를 건너뛰어야 자연스럽다.

**Prototype B**

Judgment Home이 initial formation에 자연스럽다. System synthesis가 driver, risk, uncertainty, question을 제안하고 user가 필요한 부분만 자신의 view로 형성할 수 있다.

**Result:** formation에서는 B 우세.

**Design implication:** 처음 보는 기업을 `nothing → change`처럼 다루지 말고 Judgment Snapshot / guided exploration으로 시작.

---

### Scenario 5 — 여러 보유 종목 Morning Review

**User need:** 실제로 judgment-relevant change가 있는 곳에만 attention을 사용.

A나 B 단독보다 다음 hybrid가 가장 강했다.

```text
PORTFOLIO ORIENTATION

Needs review now
NVDA   Mixed earnings — 3 components affected
CEG    Regulatory change — core risk affected

Worth noting, no judgment action
IREN   -14% — thesis unchanged / valuation improved
MSFT   Filing — no material bearing detected

No meaningful change
12 holdings collapsed
```

첫 번째 category만 focused Change Review를 연다. Low-impact change는 inline / informational로 유지한다.

**Result:** hybrid 우세.

## 5. Refined Leading Prototype — Adaptive Change Review

두 prototype을 binary choice로 볼 필요는 없다.

현재 가장 강한 architecture는:

> **Persistent Judgment Home + change-driven orientation + adaptive review depth**

이다.

변화는 judgment 의미를 보존하는 가장 가벼운 depth에서 표현한다.

### Level 0 — Silent system maintenance

User-facing attention이 정당화되지 않으면 System Synthesis만 내부적으로 업데이트. interruption도 user approval도 없음.

### Level 1 — Inline change annotation

Impact가 단순하거나 low-consequence이거나 user-owned judgment를 material하게 바꾸지 않을 때 사용.

```text
Valuation     improved
              price -14% 때문
              thesis components unchanged
```

### Level 2 — Focused Change Review

하나의 event가 다음에 해당할 때 사용한다.

- 여러 judgment component에 영향
- meaningful evidence conflict 생성
- material system–user divergence 생성
- user-owned judgment를 material하게 바꿀 가능성
- uncertainty / conviction을 material하게 변경
- card-level diff만으로 안전하게 이해하기 어려움

### Level 3 — Decision Context transition

User가 allocation, comparison, rotation, constraint, action implication을 직접 보고 싶을 때만 이동.

```text
Judgment Review
      ↓ user chooses
Decision Context
      ↓
compare / portfolio implications / possible decision
```

Judgment review가 자동으로 buy/sell recommendation으로 이어져서는 안 된다.

## 6. Refined Wireflow

```text
                         PORTFOLIO / ORIENTATION
                       "Where should I look?"
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
       no material change    simple bearing     complex/material bearing
              │                   │                   │
              ▼                   ▼                   ▼
       collapsed / quiet     Inline Change       Focused Change
                              Annotation             Review
                                  │                   │
                                  └────────┬──────────┘
                                           ▼
                                  JUDGMENT SNAPSHOT
                               "Where do I stand now?"
                                 │      │       │
                     inspect ────┘      │       └── divergence
                                        │
                                        ▼
                                COMPONENT DETAIL
                                        │
                                        ▼
                              EVIDENCE / PROVENANCE
                                        │
                         optional, user-initiated only
                                        ▼
                                 DECISION CONTEXT
```

모든 change가 별도 page나 confirmation step을 필요로 한다는 가정을 제거한다.

## 7. Material Interaction Contract

### 7.1 Attention ≠ Approval

Surface된 item은 `확인할 가치가 있다`는 뜻이지 `AI 결론을 승인해달라`는 뜻이 아니다.

### 7.2 System update ≠ User judgment update

System은 user에게 묻지 않고 System Synthesis를 업데이트할 수 있다. Material한 user-owned state change는 DL-DR-0001을 따른다.

### 7.3 No response ≠ agreement

User가 system proposal을 review하지 않았다고 해서 adopted로 처리해서는 안 된다.

### 7.4 Retain도 의미 있는 상태

`evidence를 검토했고 내 view를 유지했다`와 `아직 검토하지 않았다`는 구분돼야 한다.

### 7.5 Unresolved는 정상적인 상태

Evidence가 부족하거나 conflicting하면 strengthen / weaken를 강제하지 않고 unresolved가 더 정확한 outcome이 될 수 있다.

## 8. Prototype Information Priority

### Portfolio / Orientation

기본 우선순위:

1. current judgment에 material bearing이 있는 change
2. 더 consequential해진 unresolved conflict / uncertainty
3. 새롭게 material해진 system–user divergence
4. user-requested monitoring condition
5. raw price / news / filing activity는 context 또는 trigger로 필요할 때만

Chronological news feed와 의도적으로 다르다.

### Judgment Snapshot

기본 우선순위:

1. current material components
2. last meaningful review 이후 materially 달라진 것
3. unresolved / weak areas
4. material system–user divergence
5. deeper evidence와 history는 on demand

## 9. Competitive Implication

현재 research product는 alert, automated monitoring, thesis checking, cited synthesis, agentic research workflow까지 빠르게 발전하고 있다. AlphaSense는 thesis validation / refresh / postmortem agent와 automatically updated output을 제공하고, Koyfin은 watchlist / portfolio alert를 research workflow에 연결한다.

References:

- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026
- https://help.alpha-sense.com/hc/en-us/articles/53942181071123-AlphaSense-Product-Updates-July-2026
- https://www.koyfin.com/features/alerts/

따라서 Stock_vis의 differentiation을 alert 또는 AI synthesis 그 자체라고 가정하면 안 된다. 더 distinctive한 interaction hypothesis는 **traceable judgment state를 유지하고, 새 정보를 시간에 따른 explicit judgment impact로 변환하는 것**이다.

아직 Approved product-strategy claim은 아니다.

## 10. Failure / Reversal Conditions

다음이 prototype test에서 확인되면 adaptive architecture를 수정해야 한다.

- user가 inline annotation과 focused review의 차이를 이해하지 못함
- adaptive depth 때문에 interface가 예측 불가능하게 느껴짐
- system이 너무 많이 숨겨 important change를 놓침
- focused review가 너무 많아져 결국 inbox가 됨
- 하나의 integrated Judgment Home이 복잡한 change도 훨씬 낮은 interaction cost로 충분히 전달함
- user가 system proposal이 자신의 view에 adopted되었는지 구분하지 못함
- initial formation과 monitoring이 하나의 Judgment model을 공유하기 어렵고 실제로 별도 surface가 필요함

## 11. Batch Consensus

### Recommended Working Prototype

**Persistent Judgment Home + Change-Driven Orientation + Adaptive Change Review**를 leading low-fidelity prototype direction으로 사용한다.

**Recommendation Strength:** Strong

### Why

두 architecture의 장점을 모두 살린다.

- simple / non-material change에서는 friction이 낮음
- complex / consequential change에서는 causal understanding을 집중적으로 제공
- maintained judgment가 durable organizing object로 남음
- DL-DR-0001과 강하게 정합
- product-level approval inbox를 만들 필요 없음
- initial formation과 ongoing monitoring 모두 자연스럽게 지원

### Main Alternative

모든 change를 하나의 Judgment Home에서 inline으로만 표현하는 단순화안은 가장 강한 comparator로 계속 유지한다.

### Deferred / AI-Owned

- Level 1 vs Level 2 exact threshold
- card / page / drawer 등 실제 representation
- default visible component 수
- `Review`, `Impact`, `My View`, `System View` 같은 naming
- mobile vs desktop transition
- animation / iconography / color / visual system
- adopt / retain / unresolved exact microcopy

## 12. CEO Critical Decision

**이번 Batch에는 없음.**

이미 승인된 Human–AI judgment authority boundary 안의 reversible prototype direction이다.

## 13. Next Prototype Step

다음은 abstract wireflow가 아니라 **하나의 concrete end-to-end low-fidelity prototype scenario**로 내려간다.

첫 prototype scenario 추천:

> **보유 종목이 급락한 뒤 mixed earnings evidence가 들어오는 상황**

이 한 시나리오에서 다음을 모두 검증할 수 있다.

- low-impact trigger handling
- inline annotation → focused review transition
- multi-component judgment change
- uncertainty
- system–user disagreement
- evidence drill-down
- user-owned revision
- update lineage

동일 scenario를 simplified all-inline Judgment Home으로도 만들어 comparator로 둔다.