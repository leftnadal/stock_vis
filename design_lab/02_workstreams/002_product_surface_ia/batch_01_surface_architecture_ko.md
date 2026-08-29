# Workstream 002 — Batch 01: Surface Responsibility & IA Families

> **한국어 Companion 문서**  
> 원문: [`batch_01_surface_architecture.md`](batch_01_surface_architecture.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-27  
**Status:** Working  
**Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; Approved Product IA 아님

## 1. Batch Question

> **사용자가 서로 끊어진 tool들을 돌아다니지 않고 Orientation, 기업 이해, Investment View 유지, Research 탐색, downstream Decision Context까지 이어갈 수 있으려면 무엇을 persistent product space로 두고 무엇을 contextual capability로 두어야 하는가?**

## 2. 현재 Stock_vis 구현 — Evidence이지 Authority는 아님

현재 frontend는 기능 중심 navigation이 축적되어 있다.

Desktop global navigation:

- Dashboard
- Market Pulse
- Chain Sight
- News
- Screener
- Guide
- My

`My` 안에는 다시:

- Watchlist
- Monitor
- Coach
- Wallet
- Portfolio

가 있다.

Mobile도 Home, Market Pulse, Chain Sight, News, Guide, My를 별도 destination으로 둔다.

이 구조는 실제 제품 개발 역사와 기능을 반영하는 중요한 evidence다. 다만 현재 Design Foundation 관점에서는 다음 failure가 가능하다.

> **제품이 투자 질문을 도와주기 전에 사용자가 먼저 ‘어느 기능에 답이 있는지’를 알아야 한다.**

따라서 기존 route는 migration constraint와 prototype material로 존중하지만 미래 IA의 authority로 보지는 않는다.

## 3. 최신 외부 Benchmark에서 보이는 신호

### AlphaSense

현재 AlphaSense 문서에서는:

- **Dashboard**가 coverage universe를 지속 monitoring하는 customizable interface이고
- **Company Profile**이 한 기업의 financial data, document, summary, commentary, peer, Generative Search를 모은 central research hub

로 설명된다.

즉 **cross-object orientation / monitoring**과 **single-company deep work**를 분리하는 패턴은 유효한 benchmark다.

다만 AlphaSense는 professional research workflow를 주로 최적화하므로 Stock_vis의 Better Investment Judgment 목적에 그대로 복사할 이유는 없다.

### Koyfin

Koyfin은 dashboard, watchlist, portfolio, financial analysis, screener, news, alert, chart를 별도 tool로 제공하면서 서로 조합 가능하게 만든다.

이는 composable tool과 customization의 장점을 보여준다. 반면 기본적으로는 **tool / data-workbench model**에 가깝다. Stock_vis는 maintained Investment View와 downstream Judgment라는 더 강한 semantic center가 필요할 수 있다.

### FinChat

FinChat의 현재 공개 자료는 company data, financial datasets, company-specific AI prompt, generative AI / Copilot, card-based rendering을 강하게 보여준다.

이는 AI / company context가 cross-cutting access mechanism이 될 수 있다는 evidence다. 하지만 persistent user-view continuity나 Portfolio Decision Context 자체를 해결해주지는 않는다.

## 4. 후보 A — Surface-per-Task / Feature

```text
Dashboard
Market
News
Research / Chain
Screener / Discover
Company
Portfolio
Compare
AI
```

### 장점

- 기능별 책임이 명확하고 독립 개발이 쉽다.
- financial terminal / tool power user에게 익숙하다.
- 현재 Stock_vis 구현과 비교적 가깝다.

### 문제

- 동일 context가 여러 surface에 반복된다.
- 사용자가 문제보다 tool을 먼저 선택해야 한다.
- Investment View continuity가 약해진다.
- Change / Evidence / Research / Comparison이 각각 분리된다.
- Mobile navigation이 쉽게 포화된다.
- 기능이 늘수록 top-level navigation도 계속 늘어나는 경향이 있다.

### 현재 판단

**Foundational IA로는 비선호.**

다만 advanced utility나 secondary tool에는 적합할 수 있다.

## 5. 후보 B — Company-Centered Workspace

```text
Orientation
   ↓
Company / Investment Workspace
   ├─ View
   ├─ Changes
   ├─ Evidence
   ├─ Financials
   ├─ Relationships
   ├─ Scenarios
   └─ Compare launch
```

### 장점

- Investment View continuity가 매우 강하다.
- Object ownership이 명확하다.
- Research / Evidence / Change / History를 company context 안에 유지하기 쉽다.
- Progressive disclosure와 잘 맞는다.

### 문제

- Morning cross-company orientation에는 약하다.
- Industry / macro / relationship exploration이 company 안에 갇힐 수 있다.
- Portfolio allocation / rotation은 company-local problem이 아니다.
- Comparison이 어색한 object jump가 될 수 있다.
- 50개 이상 종목을 follow하는 사용자에게 cross-object layer가 필요하다.

### 현재 판단

**Company-level architecture로는 Strong하지만 전체 Product IA로는 부족.**

## 6. 후보 C — Portfolio / Decision-Centered

```text
Portfolio / Active Decisions
   ↓
Holdings / Opportunities
   ↓
Company Research
```

### 장점

- Capital allocation과 직접 연결된다.
- Comparison / Rotation이 자연스럽다.
- 실제 portfolio가 있는 active investor에게 강하다.
- Decision Context가 숨겨지지 않는다.

### 문제

- 아직 portfolio가 없거나 exploration만 하는 사용자의 home이 약하다.
- Understanding에서 너무 빨리 Decision으로 밀어갈 위험이 있다.
- Company information이 current holding을 기준으로 왜곡될 수 있다.
- New idea / industry exploration이 portfolio에 종속된다.
- 과도한 action / turnover를 자극할 수 있다.

### 현재 판단

**중요한 downstream mode이지만 universal organizing center로는 비선호.**

## 7. 후보 D — Object + Context Hybrid

현재 leading family다.

```text
                    ORIENTATION
             지금 무엇을 봐야 하나?
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
 INVESTMENT         RESEARCH /       DECISION
 WORKSPACE           EXPLORE          CONTEXT
 company object      contextual       portfolio / compare
       │              capability            │
       │                   ┌─────────────────┘
       └───────────────────┤
                           ▼
                        JUDGMENT
                           ↓
                        DECISION
```

위 label은 conceptual role이지 final navigation label이 아니다.

### Persistent space / object

#### 1. Orientation

책임:

- 지금 무엇을 볼 가치가 있는가
- cross-company meaningful change
- unresolved / divergence escalation
- quiet state compression
- relevant company / research / decision context로 진입

Generic market-news dashboard가 기본이 되어서는 안 된다.

#### 2. Investment / Company Workspace

책임:

- System Synthesis
- user-owned Investment View
- Formation / Maintenance
- Change Review
- driver / condition / risk / uncertainty
- evidence / provenance access
- revision history
- company-local scenario / relationship

현재 가장 강한 persistent semantic object다.

#### 3. Portfolio / Decision Context

Intrinsic company truth가 아니라 decision-specific context를 책임진다.

- holding / exposure
- horizon
- constraint
- alternative
- opportunity cost
- current decision에서의 valuation
- allocation / rotate / add / reduce question
- comparative Judgment 준비

### Contextual capability — top-level일 필요는 아직 없음

#### Research / Explore

어떤 object / question에서도 열 수 있고 다음을 포함할 수 있다.

- Evidence
- Documents
- Relationship / Chain exploration
- Industry context
- Scenario
- AI question
- Deep search

다만 cross-object exploration의 중요성이 충분히 크면 별도 global Explore space가 필요할 수도 있어 다음 Batch에서 계속 검증한다.

#### Comparison

현재 hypothesis는 **Decision Context 주변에서 만들어지는 mode / workspace**이며 permanent top-level destination은 아니다.

Company, Portfolio, Opportunity, Research result에서 launch할 수 있다.

#### Change Review

Universal inbox가 아니라 Orientation / Investment Workspace 안에서 adaptive interaction으로 작동한다.

#### Discovery / Screener

현재는 자동으로 top-level IA로 보기보다 opportunity-generation capability로 보는 쪽이 우세하다.

하지만 이 부분은 아직 검증이 약해 distinct Explore / Discover space가 살아남을 가능성이 있다.

## 8. Scenario Stress Test

| Scenario | A Feature | B Company | C Portfolio | D Hybrid |
|---|---|---|---|---|
| 3분 Morning Review | 보통 | 약함 | Holding에는 강함 | **강함** |
| 처음 보는 기업 | 보통 | **강함** | 약함 | **강함** |
| Mixed earnings 유지 | Fragmented | **강함** | 보통 | **강함** |
| Evidence / Chain 깊은 조사 | 기능은 강하나 분리 | 중~강 | 약함 | **Contextual Explore가 잘되면 강함** |
| Holding vs Alternative | 보통 | 약~보통 | **강함** | **강함** |
| Portfolio 없음 | 강함 | 강함 | 약함 | **강함** |
| 50+ Watch names | 보통 | 약함 | 보통 | **Orientation layer 강함** |
| Mobile | 기능 증가 시 약함 | 보통 | 보통 | **가장 유망** |
| System–User divergence | Fragmented | 강함 | 보통 | **강함** |

이 표는 user-test evidence가 아니라 Design Lab synthesis다.

## 9. Hybrid에 대한 가장 강한 반론

Hybrid가 개념적으로는 우아하지만 실제 제품에서는 애매할 수 있다.

`Research / Explore`, `Comparison`, `Change Review`, `Discovery`를 모두 contextual capability로 만들면 사용자가 어디에서 기능을 찾아야 하는지 예측하기 어렵고, 소수 surface 안에 너무 많은 hidden mode가 생길 수 있다.

반대로 feature-oriented IA는 각 tool에 stable destination이 있어서 findability가 오히려 좋아질 수도 있다.

따라서 Hybrid는 다음 prototype에서 반드시:

- predictable entry point
- stable object identity
- hidden-mode confusion 최소화
- efficient cross-object exploration
- mobile viability

를 보여줘야 살아남는다.

## 10. Current Working Recommendation

### Recommendation

**Object + Context Hybrid**를 leading IA family로 올리고 두 challenger를 유지한다.

1. **Company-Centered + dedicated Explore**
2. **Hybrid + Explore / Discover를 네 번째 persistent global space로 추가**

### Recommendation Strength

**Strong**

### Why

Workstream 001의 semantic architecture를 가장 잘 보존하면서 기능이 늘 때마다 top navigation이 계속 늘어나는 문제를 막을 가능성이 높다.

특히 반복해서 살아남은 세 목적에 명확한 ownership을 줄 수 있다.

- cross-object **Orientation**
- persistent **Investment / Company View**
- downstream **Decision Context**

Research, Evidence, Change Review, AI, Comparison, Discovery는 그 주변 capability로 검증한다.

## 11. Failure / Reversal Conditions

다음이면 수정한다.

- contextual capability를 찾기 어려움
- Investment Workspace가 모든 것을 넣은 monolithic page가 됨
- cross-object Research / Chain exploration의 stable home이 부족함
- 사용자가 반복적으로 dedicated Discovery workflow를 원함
- Comparison이 persistent destination 없이는 이해되지 않음
- Mobile이 responsive adaptation이 아니라 materially 다른 IA를 요구함
- 현재 구현 migration cost가 expected judgment benefit보다 materially 큼

## 12. CEO Critical Decision

**Batch 01에는 없음.**

아직 reversible IA family hypothesis다. Persistent product space / top-level navigation을 실제로 잠그는 단계가 오면 CEO Critical Decision이 될 수 있다.

## 13. Next Exploration

다음 low-fidelity IA / navigation prototype에서는:

- **D1 — dedicated Explore 없는 Hybrid**
- **D2 — Explore / Discover를 4번째 persistent space로 가진 Hybrid**

를 비교한다.

다음 상황에 대입한다.

- Morning Review
- New-company research
- Cross-company relationship exploration
- Holding vs alternative comparison
- Mobile navigation
