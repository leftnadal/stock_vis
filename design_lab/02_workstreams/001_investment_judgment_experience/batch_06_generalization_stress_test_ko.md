# Workstream 001 — Exploration Batch 06

> **한국어 Companion 문서**  
> 원문: [`batch_06_generalization_stress_test.md`](batch_06_generalization_stress_test.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 CEO-approved semantic intent와 관련 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** Tier 2 — 승인된 DL-DR-0001 아래의 reversible interaction architecture refinement

## Generalization Stress Test — Formation, Morning Review, Comparison

## 1. 목적

이번 Batch는 Batch 05의 현재 leading architecture가 단순히 “보유종목의 기존 판단을 업데이트하는 상황”을 넘어 더 일반적인 투자 판단 경험에도 적용되는지 검증한다.

세 가지 scenario로 공격적으로 stress-test했다.

1. **처음 보는 기업 / 최초 판단 형성** — prior user judgment가 없음
2. **3분 Morning Portfolio Review** — 여러 보유종목 중 어디에 attention을 써야 하는지 빠르게 판단
3. **두 투자기회 비교 / ROTATE 가능성** — 서로 다른 두 investment judgment를 decision context 안에서 비교

목표는 navigation이나 screen 이름을 확정하는 것이 아니다. Formation, maintenance, update, monitoring, comparison을 하나의 coherent architecture로 지원할 수 있는지 확인하는 것이다.

`DL-DR-0001 — Human–AI Judgment Authority Boundary`는 계속 Approved constraint다.

## 2. 외부 패턴에서 얻은 시사점

### 2.1 Portfolio monitoring과 alert는 이미 경쟁 제품이 잘한다

현재 investment platform은 이미 portfolio / watchlist alert, customizable dashboard, side-by-side comparison 등을 제공한다. Koyfin은 portfolio·watchlist 단위 alert와 비교 기능을 제공하고, AlphaSense도 automated monitoring, 대형 watchlist search, investment-thesis workflow agent를 확장하고 있다.

References:

- https://www.koyfin.com/features/alerts/
- https://www.koyfin.com/features/watchlists/
- https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026

**Working implication:** Stock_vis의 핵심을 alert aggregation이나 단순 side-by-side metric comparison으로 잡아서는 차별성이 약하다. 현재 더 강한 가설은 **judgment-bearing change를 우선순위화하고, 시간이 지나도 traceable한 investment judgment state를 유지하는 것**이다.

### 2.2 Comparison은 task complexity와 맞는 수준의 지원이 필요하다

Decision-support 연구에서는 comparison aid가 흩어진 정보를 정리하고 중요한 dimension을 비교 가능하게 만들 때 도움이 되지만, 지나치게 강한 support나 task와 맞지 않는 구조는 오히려 사용자가 단순 heuristic에 의존하거나 충분히 생각하지 않게 만들 수 있다.

References:

- Tan, Teo & Benbasat, *Assessing Screening and Evaluation Decision Support Systems: A Resource-Matching Approach*, Information Systems Research (2010)
- Frontiers in Psychology (2025), computer-based decision aids and cognitive load: https://doi.org/10.3389/fpsyg.2025.1576319

**Working implication:** Stock_vis comparison은 비교 effort를 줄여야 하지만, 최종 trade-off를 하나의 자동 ranking으로 대신해서는 안 된다.

## 3. Scenario A — 처음 보는 기업 / Judgment Formation

### 문제

사용자가 처음 보는 기업에는 prior personal judgment가 없다. 따라서 change-centric architecture만으로는 시작점이 없다.

### Literal Adaptive Change Review의 failure

제품이 `무엇이 변했나?`부터 시작하면 존재하지 않는 prior state를 전제로 하게 된다. 이를 억지로 `initial change`처럼 다루는 것은 mental model을 왜곡한다.

### 더 강한 Formation flow

```text
Discovery / Search
      ↓
Initial System Synthesis
      ↓
Judgment Formation Workspace
      ├─ 중요한 driver / claim
      ├─ risk / invalidation condition
      ├─ unresolved uncertainty
      ├─ 중요한 evidence / provenance
      └─ 더 확인할 가치가 있는 question
      ↓
User explores / challenges / asks questions
      ↓
필요한 부분만 User Judgment 형성
      ↓
Maintained Judgment State
```

### 핵심 발견

**User Judgment가 아직 없다는 상태도 정상적인 상태여야 한다.**

System이 이미 synthesis를 만들었다고 해서 사용자가 억지로 thesis를 만들어야 하는 것은 아니다.

User state는 다음처럼 존재할 수 있다.

- 아직 explicit view 없음
- 일부 component에 대해서만 view 형성
- 일부는 unresolved
- system과 특정 부분에서 disagreement

이 구조가 DL-DR-0001을 보존하면서도 사용자에게 manual thesis maintenance를 강요하지 않는다.

### Progressive Formation

처음부터 전체 semantic structure를 보여주기보다 다음과 같은 질문으로 진입하는 것이 더 강하다.

```text
무엇이 가장 중요한가?
이 투자 아이디어는 무엇 때문에 깨질 수 있는가?
아직 무엇을 모르는가?
최근 무엇이 중요하게 변했는가?
```

이 질문들은 underlying structure 자체가 아니라 structure에 접근하는 방법이다.

### 결과

**현재 architecture는 `Change Review`가 전체 foundation이 아니라 broader Judgment Workspace 내부의 하나의 adaptive mode일 때 살아남는다.**

## 4. Scenario B — 3분 Morning Portfolio Review

### 문제

보유종목이 많으면 매일 각 기업의 Judgment Home을 하나씩 열 수 없다.

이때 핵심 task는 deep research가 아니라 **attention allocation**이다.

### Leading orientation model

```text
MORNING REVIEW

지금 판단 검토 필요
NVDA   Mixed earnings — 핵심 component 3개 영향
CEG    규제 변화 — core risk 변화 가능

알아둘 가치 있음 / judgment action은 아님
IREN   -14% — thesis unchanged / valuation improved
MSFT   Filing — material bearing 없음

Quiet
12 holdings — meaningful judgment-bearing change 없음
```

### Alert inbox와의 차이

우선순위는 단순 recency나 price magnitude가 아니다.

- current judgment에 대한 bearing
- unresolved conflict / uncertainty가 더 consequential해졌는가
- material system–user divergence 발생
- user-defined monitoring condition
- 필요할 경우 decision-context 변화

를 기준으로 한다.

### 핵심 Contract

**Attention item ≠ task ≠ approval request.**

Morning Review의 대부분은 사용자가 이해하는 것만으로 끝날 수 있어야 한다. Focused Review는 복잡하거나 user-owned judgment에 material한 영향을 줄 가능성이 있을 때만 연다.

### 결과

**Orientation을 개별 기업 Judgment Workspace 위의 first-class cross-company layer로 두면 architecture가 잘 일반화된다.**

## 5. Scenario C — 두 투자기회 비교 / ROTATE 가능성

### 문제

사용자가 묻는 것은 단순히 “A가 좋은 회사인가?”가 아니다.

예:

> 현재 portfolio, 투자기간, constraints, opportunity cost를 고려했을 때 A가 B보다 충분히 나아서 자본이나 attention을 옮길 가치가 있는가?

이것은 두 회사 각각의 maintained judgment와는 다른 object다.

### 단순 side-by-side Judgment card의 failure

두 회사의 핵심 causal structure가 다를 수 있다.

```text
IREN                         NBIS
Power advantage              Customer concentration
Build execution              AI cloud demand
Capital intensity            GPU supply access
Valuation                    Valuation
```

모든 항목을 억지로 동일한 row에 넣으면 오히려 실제로 중요한 차이를 지울 수 있다.

### Leading Comparison Architecture

Comparison은 두 maintained judgment를 input으로 사용하는 **Decision Context / Comparison Lens**가 되어야 한다.

```text
Judgment A ─────┐
                ├── Comparison / Decision Context
Judgment B ─────┘        │
                         ├─ 실제 비교 가능한 공통 dimension
Portfolio / horizon ─────┤
Constraints ─────────────┤
Opportunity cost ────────┘
                         ↓
              Relative trade-off structure
```

### Comparison이 먼저 답해야 할 질문

단일 score보다 다음을 먼저 명확하게 하는 것이 더 강하다.

- A가 B보다 의미 있게 우세한 부분은 어디인가?
- B가 A보다 우세한 부분은 어디인가?
- 그 차이 중 현재 decision context에서 실제 중요한 것은 무엇인가?
- 어떤 uncertainty 때문에 비교를 강하게 결론 내릴 수 없는가?
- A가 B보다 더 나으려면 무엇이 true여야 하는가?
- 차이가 실제 rotate할 만큼 큰가, 아니면 실질적으로 비슷한 범위인가?

### 공통 Dimension + 비대칭 Dimension

진짜 비교 가능한 dimension은 표준화해서 보여주되, 각 기업에서만 material한 component는 따로 보존한다.

```text
공통 비교
Demand durability        A > B
Execution confidence     B > A
Valuation                A > B
Uncertainty              mixed

A-specific concern
Power / build dependency

B-specific concern
Customer concentration
```

### False Scalar Certainty를 피한다

`A = 82 / B = 76`과 같은 single score는 heterogeneous trade-off와 uncertainty를 마치 객관적 한 숫자인 것처럼 압축할 위험이 있다.

현재 Design direction은 **aggregate ranking보다 relative trade-off structure를 먼저 보여주는 것**이다.

향후 aggregate recommendation을 실험할 수는 있지만, underlying component reasoning과 uncertainty로 traceable해야 한다.

### 결과

**Comparison을 Judgment Home 안에 억지로 넣지 않고 downstream cross-cutting Decision Context capability로 둘 때 architecture가 잘 일반화된다.**

## 6. Architecture Revision

`Adaptive Change Review`라는 이름은 이제 foundation 전체를 설명하기에는 너무 좁다.

현재 더 강한 generalized architecture는:

> **Persistent Judgment Workspace + Attention-Oriented Orientation + Adaptive Review + Decision Context**

이다.

Working logical architecture:

```text
                       ORIENTATION
              "어디를 봐야 하지?"
                          │
         ┌────────────────┼────────────────┐
         │                │                │
   New company      Existing company   Cross-company need
         │                │                │
         ▼                ▼                ▼
   FORMATION MODE    MAINTENANCE MODE   DECISION CONTEXT
         │                │            comparison / portfolio
         │       ┌────────┴────────┐
         │       │                 │
         │   simple change    complex/material
         │       │                 │
         │    inline           focused review
         │       │                 │
         └───────┴────────┬────────┘
                          ▼
                  JUDGMENT WORKSPACE
                   maintained state
                          │
                 evidence / provenance
                          │
                  update trace / history
```

### 모든 mode에서 유지되는 것

동일한 underlying semantic model이 다음을 모두 지원할 수 있다.

- initial formation
- ongoing maintenance
- evidence-driven revision
- system–user disagreement
- monitoring
- downstream comparison

달라지는 것은 foundational semantics가 아니라 **entry point, disclosure depth, interaction objective**다.

## 7. Strong Working Findings

### 7.1 User Judgment는 없거나 부분적이어도 된다

사용자가 완성된 explicit view를 가지고 있어야만 Stock_vis가 유용한 것은 아니다.

**Recommendation Strength: Strong**

### 7.2 Orientation은 news feed가 아니라 attention allocation이다

Morning review는 raw activity보다 judgment-bearing change를 우선순위화하고 quiet holding은 적극적으로 collapse해야 한다.

**Recommendation Strength: Strong**

### 7.3 Comparison은 downstream Decision Context에 속한다

Comparison은 underlying company judgment를 바꾸는 것이 아니라, 유지된 judgment와 portfolio / horizon / opportunity-cost context를 입력으로 사용해야 한다.

**Recommendation Strength: Strong**

### 7.4 Comparison은 asymmetric structure를 보존해야 한다

공통 dimension은 유용하지만 각 기업의 고유한 material driver / risk가 필요한 경우 반드시 남아야 한다.

**Recommendation Strength: Strong**

### 7.5 Default total score는 피하는 쪽이 우세하다

Aggregate rank보다 relative trade-off, uncertainty, decision relevance가 먼저 이해되어야 한다.

**Recommendation Strength: Moderate–Strong**

향후 prototype에서 carefully designed aggregate layer가 orientation에 도움을 주는지 검증할 수 있지만 underlying structure를 지워서는 안 된다.

## 8. Failure / Reversal Conditions

다음이 실제 prototype / user testing에서 나타나면 generalized architecture를 수정해야 한다.

- 사용자가 Formation / Maintenance / Decision Context의 차이를 이해하기 어려움
- mode 사이 이동 때문에 product가 지나치게 fragmented하게 느껴짐
- 하나의 universal company page + contextual module만으로도 충분히 orientation이 가능하고 더 단순함
- morning triage가 너무 많은 material change를 숨김
- 대부분의 실제 비교에서 judgment-based comparison이 conventional metric comparison보다 느리고 덜 유용함
- asymmetric comparison이 오히려 비교를 어렵게 만듦
- practical decision을 위해 더 명시적인 recommendation / ranking layer가 반드시 필요함

## 9. Batch Consensus

현재 leading hypothesis를 `Adaptive Change Review`에서 다음으로 확장하는 것을 추천한다.

> **Formation과 Maintenance를 지원하는 persistent Judgment Workspace를 중심에 두고, 그 위에는 attention-oriented Orientation, change에는 adaptive review depth, Comparison / Portfolio reasoning은 downstream Decision Context로 둔다.**

**Recommendation Strength: Strong**

아직 Approved Product IA가 아니라 Working architecture다.

## 10. CEO Critical Decision

**이번 Batch에는 없음.**

이미 승인된 Human–AI authority boundary 아래에서 reversible Tier 2 interaction architecture를 넓게 검증하고 refinement한 단계다. 새로운 장기 authority나 major Product IA를 잠그지 않는다.

## 11. Deferred / AI-Owned

- Judgment Workspace / Formation / Maintenance의 최종 naming
- Formation과 Maintenance가 실제 별도 mode인지 하나의 surface 안 contextual state인지
- Morning Review grouping과 threshold
- Comparison visual layout
- exact shared comparison dimension
- aggregate comparison summary의 필요 여부
- mobile interaction
- component / button naming
