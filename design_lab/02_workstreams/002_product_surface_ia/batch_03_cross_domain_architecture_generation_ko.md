# Workstream 002 — Batch 03: Cross-Domain Architecture Generation & Stress Test

> **한국어 Companion 문서**  
> 원문: [`batch_03_cross_domain_architecture_generation.md`](batch_03_cross_domain_architecture_generation.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이며 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-28  
**Status:** Working  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; Approved Product IA / Design Knowledge 아님

## 1. 이번 Batch 질문

> **현재 금융서비스의 메뉴 관습이 아니라, Stock_vis와 구조적으로 비슷한 판단 시스템에서 IA를 생성하면 어떤 전혀 다른 product architecture가 가능하며, 실제 투자 시나리오에서 무엇이 살아남는가?**

Batch 02에서 투자 research / trading, 임상진단, forecasting, intelligence / object system, incident response, quant research 등에서 Idea Pool을 만들었다.

이번 Batch는 그 pattern을 단순 benchmark가 아니라 **IA 생성 재료**로 사용한다.

## 2. 공통 Stress-test 시나리오

모든 후보를 같은 상황에 넣었다.

1. **3분 Morning Review** — 15~30개 보유 / 관심종목 중 어디를 봐야 하는가
2. **처음 보는 회사** — prior Investment View 없이 처음 판단을 형성
3. **Mixed Earnings** — Demand 강화, Execution 약화, Margin uncertainty 증가
4. **Theme Exploration** — `AI power infrastructure`에서 관계를 따라 여러 산업 / 기업 탐색
5. **Forward Comparison / Rotation** — IREN과 NBIS 중 미래 opportunity 차이가 갈아탈 만큼 큰가
6. **Human–AI Disagreement / Learning** — System Synthesis와 My Investment View가 다르고 이후 Reality로 과거 reasoning을 돌아봄

## 3. 후보 A — Portfolio Control Tower

### 출발 분야
Trader / watchlist / alert / incident triage.

### 중심
**Coverage set + attention priority**

```text
Portfolio / Watch Universe
        ↓
Attention Board
  ├─ 지금 검토
  ├─ Monitor
  └─ Quiet
        ↓
Company / Event
        ↓
Focused Review
        ↓
필요하면 Decision Context
```

### 강점
- Morning Review에 매우 강함
- 여러 종목 중 attention 배분이 자연스러움
- 사용자 정의 monitoring rule과 잘 맞음
- Mixed event를 하나의 Focused Review로 묶기 쉬움

### 약점
- 처음 보는 회사와 theme exploration에는 약함
- urgency / alert 중심 product로 변질될 위험
- `Review priority 낮음`이 `중요하지 않음이 증명됨`처럼 보일 수 있음

### 현재 판단
**강한 component지만 전체 IA로는 부족.**

---

## 4. 후보 B — Investment Object Workspace

### 출발 분야
Palantir Object View, AlphaSense Company Profile, analyst company workspace.

### 중심
**회사 / 투자 object**

```text
IREN Investment Workspace
  ├─ System Synthesis
  ├─ My Investment View
  ├─ Changes
  ├─ Evidence / Research
  ├─ Relationships
  ├─ Financials
  ├─ Future Scenarios
  └─ History / Lineage
```

### 강점
- 처음 보는 회사에서 매우 강함
- 한 기업에 대한 continuity 보존
- Mixed Earnings가 기존 Investment View의 어느 부분을 바꾸는지 연결 가능
- AI가 별도 generic AI 페이지가 아니라 현재 company context를 상속 가능

### 약점
- Morning Review는 별도 Orientation이 필요
- Theme-first exploration이 어색할 수 있음
- Rotation / Portfolio reasoning을 한 회사 안에 넣으면 안 됨

### 현재 판단
**가장 강한 persistent anchor 중 하나지만 단독 IA는 아님.**

---

## 5. 후보 C — Differential Reasoning Workspace

### 출발 분야
임상 differential diagnosis, VisualDx / Isabel, Research Lab의 alternative / uncertainty 보존.

### 중심
**해결되지 않은 투자 문제 + competing explanation / future**

```text
Problem Representation
        ↓
A / B / C 가능한 설명·미래
        ↓
Discriminating Evidence
        ↓
Support / Challenge / Unresolved
        ↓
Updated Investment View
```

### 강점
- Mixed Earnings에 매우 강함
- Human–AI disagreement를 억지 consensus 없이 유지 가능
- 처음 보는 투자대상에서 하나의 thesis에 너무 빨리 고정되는 것을 방지
- `무엇이 preferred view를 지지하나?`보다 `무엇이 competing views를 실제로 구분하나?`를 묻게 함

### 약점
- 매일 모든 종목에 쓰기에는 너무 무거움
- 진단학처럼 하나의 정답을 찾는다는 잘못된 analogy 위험
- Research가 warrant하지 않은 probability ranking으로 변질될 수 있음

### 현재 판단
**매우 강한 reasoning lens. Top-level IA 자체로는 부적합 가능성이 높음.**

---

## 6. 후보 D — Forecast & Scenario Board

### 출발 분야
Metaculus, probabilistic forecasting, scenario planning, quant expectation-vs-reality.

### 중심
**미래 scenario + revision history**

```text
Current State
   ↓
Possible Futures
   ↓
Enablers / Accelerators
Bottlenecks / Invalidation
   ↓
Growth / Value Outcomes
   ↓
Forecast Revision Timeline
   ↓
Reality / Learning
```

### 강점
- IREN vs NBIS forward comparison에 매우 강함
- 과거 예상이 왜 바뀌었는지 추적 가능
- `검토 후 유지`와 `오래돼서 안 본 forecast`를 분리 가능
- 성장 방해 조건 / value capture condition과 자연스럽게 연결

### 약점
- 현재 기업 이해 없이 미래부터 보면 과도한 speculation 가능
- false precision 위험이 큼
- 투자 문제는 binary resolution이 없는 경우가 많음
- Forecast probability ≠ Research credibility ≠ Investment attractiveness

### 현재 판단
**필수적인 future-facing lens지만 product 전체 중심으로 쓰기엔 위험.**

---

## 7. 후보 E — Investigation / Question Workspace

### 출발 분야
Intelligence analysis, Research lifecycle, thematic research notebook / case.

### 중심
**질문 / 조사 case**

예:

- `AI 데이터센터 성장에서 power가 계속 binding constraint인가?`
- `IREN이 demand가 좋은데도 왜 underperform하는가?`
- `Transformer shortage가 지속되면 어떤 상장기업이 이익을 얻는가?`

```text
Question / Problem
      ↓
Evidence / Sources
      ↓
Claims / Alternatives
      ↓
Objects / Relationships
      ↓
Synthesis
      ↓
여러 Investment View에 영향
```

### 강점
- Theme exploration에 가장 강함
- ChainSight식 relationship exploration이 별도 메뉴가 아니라 조사 capability가 될 수 있음
- 한 research 결과가 여러 기업에 연결될 수 있음
- 사용자의 시작점이 `회사 X`가 아니라 `이 현상을 이해하고 싶다`일 때 자연스러움

### 약점
- Morning Review에 약함
- project / notebook가 계속 쌓이는 문제
- Product investigation이 Research Knowledge처럼 오해되지 않도록 authority 경계 필요

### 현재 판단
**Explore / Investigation space 후보로 매우 강함.**

---

## 8. 후보 F — Opportunity Allocation Workspace

### 출발 분야
Portfolio manager, buy-side comparison, FactSet portfolio analytics, quant research→deployment discipline.

### 중심
**Decision Context에서의 Relative Opportunity**

```text
Portfolio / Opportunity Set
      +
Investment Views
      +
Future Scenarios
      +
Valuation / Horizon / Constraints
          ↓
Relative Opportunity
          ↓
Judgment
          ↓
HOLD / ADD / REDUCE / ROTATE / WAIT
          ↓
Outcome Review
```

### 강점
- Rotation 문제에 가장 직접적
- `좋은 회사`와 `지금 내 상황에서 더 좋은 투자`를 구분
- Opportunity cost를 제품 구조 안에 명시 가능
- 향후 performance attribution / post-decision review 연결 가능

### 약점
- 이해가 충분히 형성되기 전에 action으로 밀 수 있음
- ranking / total score 압력이 커짐
- Product가 너무 빨리 recommendation / execution tool로 변질될 위험
- Decision-support methodology의 일부는 Research Trigger 영역

### 현재 판단
**강력한 downstream Decision Context architecture이지만 universal starting IA로는 위험.**

## 9. Scenario 결과 요약

| Architecture | Morning | New Co. | Mixed Earnings | Theme Explore | Rotation | Disagreement / Learning |
|---|---|---|---|---|---|---|
| A Control Tower | Strong | Weak | Strong | Weak | Mixed | Mixed |
| B Investment Object | Mixed | Strong | Strong | Mixed | Mixed | Strong |
| C Differential | Weak | Strong | Strong | Mixed | Strong | Strong |
| D Forecast / Scenario | Mixed | Mixed | Strong | Strong | Strong | Strong |
| E Investigation / Question | Weak | Mixed | Strong | Strong | Strong | Strong |
| F Opportunity Allocation | Strong | Mixed | Mixed | Mixed | Strong | Strong |

**한 분야의 architecture가 모든 문제를 해결하지 못했다.** 이게 이번 Batch의 중요한 결과다.

## 10. 가장 중요한 발견 — IA를 메뉴가 아니라 3개 Axis로 볼 수 있다

서로 다른 분야를 붙여보면 Stock_vis의 문제는 `Dashboard / News / Portfolio / ChainSight를 몇 개로 나눌까?`보다 아래 세 축으로 더 잘 설명된다.

### Axis 1 — 지금 다루는 Scope

```text
Portfolio / Coverage Universe
↔ Theme / Question
↔ Single Investment
↔ Comparison / Decision Set
```

### Axis 2 — 지금 하는 사고 작업

```text
Orient
Explore
Understand / Form View
Monitor / Maintain
Compare
Decide
Review / Learn
```

### Axis 3 — 시간

```text
Past / Lineage
Current View
Change
Future Scenario
Outcome / Learning
```

즉 `News`, `Forecast`, `History`, `ChainSight`, `AI`를 각각 영구적인 top-level 메뉴로 둘 필요가 없을 수 있다.

이들은 **같은 scope를 다른 reasoning / time lens로 보는 capability**일 가능성이 있다.

## 11. 이 Pool에서 새로 생성된 조합 IA

### H1 — Minimal 3-Space

```text
Orientation
   ↓
Investment Workspace
   ↓ 필요할 때
Decision Context
```

Differential / Scenario / Evidence / Relationship / History / AI는 contextual lens.

**장점:** 단순함, continuity.  
**위험:** Theme-first exploration이 불편할 수 있음.

### H2 — Explicit Explore Space

```text
          Orientation
        /      |      \
Investment   Explore   Decision Context
 Workspace  / Inquiry
```

**장점:** company-first와 theme-first를 모두 자연스럽게 지원.  
**위험:** Explore가 또 하나의 거대한 research universe가 될 수 있음.

### H3 — Universal Lens Switcher

현재 context는 유지하고 사고 lens를 바꿈.

```text
Context: IREN
[View] [Changes] [Differential] [Scenario] [Evidence] [Relations] [History]
```

**장점:** 기능을 top-level menu로 계속 늘릴 필요가 없음.  
**위험:** 결국 복잡한 toolbar가 될 수 있음.

### H4 — Question-First Adaptive Workspace

사용자의 질문이 어떤 scope와 lens가 필요한지 결정.

```text
"IREN 왜 떨어졌지?"
→ Company + Change + Differential + Evidence

"Transformer shortage 수혜주는?"
→ Investigation + Relation + Comparison

"IREN을 NBIS로 바꿀까?"
→ Comparison + Scenario + Decision Context
```

**장점:** 실제 사용자의 문제와 가장 직접적으로 연결.  
**위험:** AI가 보이지 않는 router가 되면서 제품이 예측 불가능하게 느껴질 수 있음.

## 12. 현재 Recommendation

### 추천

**아직 D1 vs D2나 최종 navigation을 고르지 않는다.**

다음 prototype에서 최소 세 가지를 실제로 만들어 비교한다.

1. **H1 — Minimal Three-Space**
2. **H2 — Explicit Explore Space**
3. **H4 — Question-First Adaptive Workspace**

H3는 별도 IA라기보다 각 prototype 안의 capability pattern으로 먼저 시험한다.

### Recommendation Strength

**Strong**

### 이유

- 어느 한 분야의 architecture도 모든 scenario를 통과하지 못했다.
- 반복해서 살아남은 것은 Orientation, Investment Object continuity, competing alternatives, future scenario, investigation, Decision Context였다.
- 가장 가치 있는 cross-domain insight는 특정 메뉴 이름이 아니라 **Scope × Reasoning Mode × Time**의 분리다.

### Strongest Counterargument

이 구조가 너무 지적으로 우아하지만 사용자에게는 추상적일 수 있다.

평범한:

```text
Dashboard / Company / Discover / Portfolio
```

구조가 실제로는 훨씬 배우기 쉽고 빨리 만들 수 있을 가능성도 충분하다.

따라서 다음 prototype에서는 conceptual elegance가 아니라:

- 어디 있는지 빨리 이해하는가
- 클릭 전에 목적지를 예상할 수 있는가
- navigation decision 수가 적은가
- mobile에서 부담이 적은가
- 길을 잃었을 때 복귀하기 쉬운가

를 같이 봐야 한다.

## 13. 아직 결정하지 않은 것

- 최종 top navigation
- Explore의 독립 surface 여부
- Question Workspace를 persistent object로 저장할지
- Differential / Scenario가 tab인지 overlay인지 AI view인지
- Portfolio가 top-level인지 Decision Context의 한 형태인지
- AI를 menu / panel / background capability 중 어떻게 표현할지
- 최종 terminology
- ontology / DB schema
- prediction probability / rotation methodology

## 14. 다음 Batch

같은 시나리오로 세 개의 **비교 가능한 low-fidelity IA prototype**을 만든다.

- **Prototype A — H1 Minimal Three-Space**
- **Prototype B — H2 Explicit Explore Space**
- **Prototype C — H4 Question-First Adaptive Workspace**

반드시 포함할 시나리오:

1. 3분 Morning Review
2. 처음 보는 회사
3. Theme relationship exploration
4. Mixed Earnings
5. IREN → NBIS forward comparison / rotation
6. 모바일에서 나갔다 돌아왔을 때 re-orientation

특히 사용자가 항상 다음을 이해할 수 있는지 확인한다.

> **나는 지금 어디에 있는가?**  
> **무엇을 보고 있는가 — company / question / portfolio / comparison?**  
> **지금 이해하려는 단계인가, 실제 decision을 생각하는 단계인가?**

## 15. CEO Critical Decision

**이번 Batch에는 없음.**

현재는 아이디어 공간을 넓히고 조합하는 단계다. 지금 큰 IA를 잠그면 cross-domain exploration을 한 목적 자체를 무력화한다.
