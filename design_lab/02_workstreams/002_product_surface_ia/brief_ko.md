# Workstream 002 — Product Surface / Information Architecture Exploration

> **한국어 Companion 문서**  
> 원문: [`brief.md`](brief.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-27  
**Status:** Active / Working  
**Opened:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Tier:** 기본 Tier 2. 주요 mental model / IA commitment가 consequential하면 escalation

## 1. Purpose

Research-aligned Workstream 001 Design Foundation을 **Product Surface / Information Architecture**로 번역한다.

다만 화면 이름, navigation, implementation을 너무 일찍 고정하지 않는다.

핵심 질문은:

> **Stock_vis가 Orientation, maintained Investment View, Research exploration, Comparison, downstream Judgment / Decision을 지원하려면 어떤 user purpose / object / transition을 별도 surface가 책임져야 하고, 어떤 것은 하나의 surface 안에 통합해야 cognitive fragmentation이 최소가 되는가?**

이다.

## 2. Upstream Constraints

이번 Workstream은 다음을 따라야 한다.

- Stock_vis Ultimate Purpose — `Better Investment Decisions`
- Design Lab working direct purpose — `Better Investment Judgment`
- Workstream 001 Research-aligned Working Design Foundation
- `DL-DR-0001 — Human–AI Judgment Authority Boundary`
- `DL-DR-0002 — Cross-Lab Judgment Semantic Boundary`
- Research Lab semantic authority, 특히:

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

Decision Context 이전의 persistent Design-side state는 현재 Working label로 **Investment View**라고 부른다.

## 3. 해결할 문제

### 3.1 Orientation

사용자가 어디에서 다음 질문에 답하는가?

- 지금 무엇을 봐야 하나?
- 무엇이 material하게 변했나?
- 무엇은 quiet한가?
- 어떤 unresolved issue가 consequential해지고 있나?

### 3.2 Company / Investment Workspace

사용자는 어디에서:

- 회사를 이해하고
- System Synthesis를 확인하고
- Investment View를 처음 형성 / 유지하고
- driver, risk, uncertainty, condition, provenance, history를 보고
- material change를 review하는가?

### 3.3 Research Exploration

더 깊은 evidence, relationship, scenario, industry / chain exploration은:

- Company Workspace 안에 들어가야 하나?
- contextual layer로 열려야 하나?
- 별도 exploratory surface가 필요한가?

`ChainSight` 같은 과거 이름은 아직 hypothesis다.

### 3.4 Portfolio / Decision Context

Portfolio exposure, horizon, alternative, constraint, opportunity cost, switching cost, valuation 등의 decision-specific context는 어디에서 경험에 들어오는가?

이 IA는 portfolio context를 intrinsic company truth처럼 만들면 안 된다.

### 3.5 Comparison / Opportunity

사용자는 어디에서:

- current company view
- future scenario
- growth-path condition
- valuation / uncertainty
- asymmetric risk
- relative opportunity
- 실제 rotation을 더 깊이 검토할 만큼 gap이 큰가

를 비교해야 하는가?

### 3.6 Discovery

Discovery가 별도 surface가 필요한가?

아니면 search, relationship, comparison, watchlist, opportunity-oriented orientation을 통해 나타나는 cross-cutting capability인가?

## 4. Starting Surface Hypotheses — IA 결정 아님

과거 Stock_vis 논의에는 다음이 있었다.

- Dashboard
- Company / Thesis-like surface
- Portfolio
- Comparison / Discovery
- ChainSight / relationship exploration
- News / Evidence Context

하지만 이것들이 각각 독립 top-level navigation이 되어야 한다고 가정하지 않는다.

각각이 실제로:

- primary surface인지
- 다른 surface 안의 mode인지
- cross-cutting capability인지
- contextual overlay인지
- 불필요한 duplication인지

검증한다.

## 5. 비교할 IA Family

최소한 다음 네 family를 경쟁시킨다.

### A. Surface-per-Task

Dashboard / Company / Research / Portfolio / Compare / Discover를 각각 독립 destination으로 둔다.

### B. Company-Centered Workspace

Company Workspace가 중심 object가 되고 research, view maintenance, evidence, comparison의 대부분이 여기에서 시작된다.

### C. Portfolio / Decision-Centered

Portfolio와 active decision question이 중심 organizing layer가 되고 company research는 subordinate하게 들어간다.

### D. Object + Context Hybrid

Orientation, Investment / Company, Portfolio / Decision Context처럼 소수의 persistent object / workspace만 두고 Research, Comparison, Evidence, Change Review는 기본적으로 contextual capability로 작동한다.

아직 어떤 family도 우선하지 않는다.

## 6. Stress-Test Scenario

최소 다음 상황에 대입한다.

1. 3분 Morning Portfolio Review
2. 처음 보는 기업
3. Mixed earnings 이후 오래 보유한 기업 view 유지
4. material change의 원인 깊게 조사
5. 현재 holding vs 새로운 alternative 비교
6. 여러 기업을 가로지르는 industry / relationship chain 탐색
7. 아직 portfolio가 없는 사용자
8. 50개 이상 watch하지만 실제 보유는 몇 개뿐인 사용자
9. Mobile / constrained attention
10. System Synthesis와 user-owned view가 크게 다름

## 7. Evaluation Dimensions

IA 대안을 다음 기준으로 비교한다.

- orientation speed
- Investment View continuity
- context switching / navigation cost
- information duplication
- object ownership clarity
- Research ↔ Design semantic consistency
- progressive disclosure
- novice / expert scalability
- comparison / rotation support
- portfolio-context separation
- mobile adaptability
- AI authority confusion risk
- long-term extensibility

## 8. Research / Evidence Boundary

현재 금융 research / investment product와 IA pattern을 benchmark할 수 있다.

하지만 경쟁 제품이 많이 사용한다는 사실을 correctness evidence로 취급하지 않는다.

IA exploration 중 Research concept / methodology gap이 발견되면 Research 의미를 임의로 바꾸지 않고 Research Trigger Candidate로 남긴다.

## 9. Expected Outputs

- competing IA architecture
- surface responsibility map
- entry / transition model
- scenario stress-test
- 필요한 경우 low-fidelity IA / navigation prototype
- recommended working architecture
- 주요 alternative와 reversal condition
- 정말 consequential한 major product mental model / IA boundary가 있을 때만 CEO Critical Decision

## 10. Non-Decisions

이번 Workstream을 연다고 다음이 승인되는 것은 아니다.

- 최종 Dashboard
- top navigation label
- 최종 Company page architecture
- permanent Thesis surface
- ChainSight top-level surface
- Portfolio universal home
- final Comparison screen
- final mobile navigation
- visual design / design-system architecture

## 11. Working Principle

> **별도 surface는 의미 있게 다른 user purpose, persistent object, 또는 interaction mode를 실제로 소유하고 기존 surface 안에 넣었을 때보다 fragmentation을 줄일 수 있을 때만 만든다.**

이것은 아직 Working IA heuristic이며 Approved Design Knowledge가 아니다.
