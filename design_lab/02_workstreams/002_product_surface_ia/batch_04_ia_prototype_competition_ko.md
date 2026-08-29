# Workstream 002 — Batch 04: IA Prototype Competition

> **한국어 Companion 문서**  
> 원문: [`batch_04_ia_prototype_competition.md`](batch_04_ia_prototype_competition.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이며 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-28  
**Status:** Working  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; Approved Product IA 아님

## 1. Batch Question

> **개념도가 아니라 실제 low-fidelity user flow로 내려갔을 때, 어떤 IA가 위치 인식, reasoning continuity, 예측 가능한 navigation, 다양한 투자 scenario 확장성을 가장 잘 보존하는가?**

Batch 03에서 cross-domain pattern을 조합해 여러 IA 후보를 만들었다. 이번 Batch에서는 그중 가장 중요한 세 후보를 실제 사용자 흐름 수준으로 비교한다.

- **H1 — Minimal Three-Space**
- **H2 — Explicit Explore**
- **H4 — Question-First Adaptive**

목표는 최종 메뉴 이름을 고르는 것이 아니라 각 semantic structure가 어디에서 cognitive friction을 만들거나 줄이는지를 찾는 것이다.

## 2. Prototype 평가 기준

어떤 prototype이든 사용자는 항상 다음 네 질문에 답할 수 있어야 한다.

1. **나는 지금 어디에 있는가?** — 현재 semantic scope가 보여야 한다.
2. **지금 무엇을 하고 있는가?** — Orient / Explore / View / Monitor / Compare / Decide / Review가 조용히 섞이면 안 된다.
3. **어떤 object 또는 question이 context를 들고 있는가?** — company, theme, comparison set, portfolio, investigation.
4. **어떻게 돌아오는가?** — 특히 mobile이나 중간 interruption 이후.

추가 평가 기준:

- orientation speed
- discoverability
- Investment View continuity
- context switching
- duplication
- mobile returnability
- Human–AI authority clarity
- progressive disclosure
- extensibility

## 3. H1 — Minimal Three-Space

### Stable structure

```text
ORIENTATION
    ↓
INVESTMENT WORKSPACE
    ↓ 실제 판단 필요 시
DECISION CONTEXT
```

Research / relationship / evidence / scenario는 현재 Investment Workspace 또는 Decision Context에서 contextual capability로 열린다.

### Scenario 결과

**Morning Review:** 매우 강함. 어디서 coverage를 보고 무엇을 우선할지가 명확하다.

**처음 보는 기업:** 기업을 선택한 이후에는 매우 단순하고 자연스럽다.

**Mixed Earnings:** Orientation → IREN → Focused Review로 연결되어 강하다.

**AI Power Infrastructure 탐색:** 핵심 약점. 사용자의 진짜 출발점은 산업/질문인데 회사부터 선택해야 한다. 이를 해결하려면 결국 숨겨진 Explore layer가 필요해져 H1의 3-space 단순성이 깨진다.

**IREN → NBIS Rotation:** 두 View를 Decision Context로 가져가면 의미적으로 깔끔하다.

**Mobile 복귀:** 매우 강함. 안정된 공간 수가 적어 복귀가 쉽다.

### 현재 판단

**장점:** 학습하기 쉽고 위치가 안정적.  
**약점:** open-ended investigation을 회사 아래에 억지로 넣게 됨.

**Current Strength: Strong. 단, theme/question exploration이 중요하면 구조적으로 불완전.**

---

## 4. H2 — Explicit Explore

### Stable structure

```text
ORIENTATION
      ├──────────────┐
      ↓              ↓
INVESTMENT        EXPLORE
WORKSPACE         question / theme / relationship
      \              /
       \            /
        ↓          ↓
       DECISION CONTEXT
```

Explore를 숨은 도구가 아니라 실제 semantic space로 인정한다.

### Scenario 결과

**Morning Review:** Orientation이 그대로 있어 강하다.

**처음 보는 기업:** Search/Explore에서 시작해 자연스럽게 Investment Workspace로 전환 가능하다.

**Mixed Earnings:** 강하지만 deep evidence investigation을 Investment에 둘지 Explore로 보낼지 boundary가 애매해질 수 있다.

**AI Power Infrastructure 탐색:** 매우 강함. 특정 회사를 고르기 전에 theme/question 자체를 유지할 수 있다.

**IREN → NBIS Rotation:** Explore에서 unresolved comparative question을 조사하고 실제 판단은 Decision Context가 소유할 수 있다.

**Mobile 복귀:** H1보다 약간 어렵지만 active investigation identity를 보존하면 충분히 가능하다.

### 현재 판단

**장점:** discovery / investigation에 제대로 된 공간을 줌.  
**약점:** Explore가 모든 deep research를 빨아들이는 catch-all bucket이 될 위험.

**Current Strength: Strong.**

---

## 5. H4 — Question-First Adaptive

### Raw version

사용자가 질문하면 system이 필요한 object, lens, evidence를 조합한다.

```text
"IREN 왜 떨어졌어?"
→ IREN + Change + competing explanations + evidence

"IREN에서 NBIS로 갈아탈까?"
→ IREN + NBIS + future scenarios + valuation + Decision Context

"변압기 부족이 계속되면 누가 수혜를 보나?"
→ theme + relationship + companies + future conditions
```

### 장점

사용자는 feature 이름보다 질문을 가지고 오기 때문에 실제 mental model과 매우 잘 맞는다.

### Raw version의 문제

완전히 adaptive하면:

- 같은 질문에서도 layout이 크게 바뀔 수 있고
- 사용자는 정보가 어디에 있는지 학습하기 어렵고
- mobile이나 interruption 이후 돌아왔을 때 AI 답변을 다시 여는 느낌이 나며
- AI가 information hierarchy를 과도하게 통제할 수 있다.

그래서 **H4-S — Stable Semantic Shell + Adaptive Canvas**를 같이 테스트했다.

## 6. H4-S — Stable Semantic Shell + Adaptive Canvas

### 고정 좌표 1 — Scope

```text
Coverage / Portfolio
Theme / Question
Investment
Comparison / Decision Set
```

### 고정 좌표 2 — Reasoning Mode

```text
Orient
Explore
View / Understand
Monitor / Update
Compare
Decide
Review / Learn
```

필요할 때 Time도 보여준다.

`Past / Current / Change / Future / Outcome`

### 예시

```text
Scope: IREN
Mode: Monitor / Update
Question: Q2 earnings가 무엇을 바꿨나?

[adaptive canvas]
- affected Investment View components
- competing explanation
- evidence
- scenario impact
- System–User divergence

항상 보이는 escape / return
Orientation | Open Investment | Decision Context
```

Content는 adapt해도 semantic coordinate는 고정한다.

### Scenario 결과

**Morning Review:** `Coverage + Orient`로 강함.

**처음 보는 기업:** `Investment + View/Understand`에서 suggested question을 이용해 자연스럽게 시작 가능.

**Mixed Earnings:** `IREN + Monitor/Update`에 differential, evidence, scenario impact를 필요한 만큼만 붙일 수 있어 매우 강함.

**AI Power Infrastructure 탐색:** `Theme/Question + Explore`로 회사 선택 전 관계 탐색이 가능하고, 이후 관심 회사가 생기면 provenance를 보존한 채 Investment scope로 전환할 수 있다.

**IREN vs NBIS Rotation:** `Comparison Set + Compare → Decide`로 future scenario, growth-path condition, valuation, portfolio context를 조합할 수 있다.

**Mobile 복귀:** Raw H4는 약하지만 H4-S는 scope / mode / active question / last state / resume affordance를 저장하면 크게 개선된다. 그래도 H1보다는 어렵다.

### 현재 판단

**장점:** 실제 user question에 가장 잘 맞으면서 stable coordinate를 보존할 수 있음.  
**약점:** state persistence와 adaptive composition 규칙이 나쁘면 즉시 예측 불가능한 UI가 됨.

**Current Strength: Strong–Very Strong as a generative direction. 아직 final IA는 아님.**

---

## 7. 비교 Stress Test

| Scenario / criterion | H1 Minimal | H2 Explicit Explore | H4-S Stable Adaptive |
|---|---|---|---|
| Morning orientation | Very Strong | Very Strong | Strong–Very Strong |
| New company | Strong | Strong | Strong |
| Mixed earnings | Strong | Strong | Very Strong |
| Theme / relationship exploration | Weak–Mixed | Very Strong | Very Strong |
| Rotation / comparison | Strong | Strong | Very Strong |
| Human–AI disagreement | Strong | Strong | Very Strong |
| Learnability | Very Strong | Strong | Moderate–Strong |
| Location awareness | Very Strong | Strong | Strong if shell explicit |
| Mobile return | Very Strong | Strong | Moderate–Strong |
| Context continuity | Strong | Strong | Very Strong |
| Feature duplication risk | 초기 낮음, hidden Explore 위험 | Moderate | semantic lens discipline가 있으면 Low–Moderate |
| AI unpredictability risk | Low | Low | shell constraint가 없으면 가장 높음 |

## 8. 가장 중요한 Prototype Finding

한 후보를 그대로 선택하기보다 세 후보의 강점을 조합하는 것이 더 좋다.

- **H1에서:** 적은 수의 durable semantic anchor + 쉬운 return path
- **H2에서:** question/theme investigation이 실제로 다른 scope일 수 있다는 인정
- **H4에서:** question-first composition + contextual reasoning lens

그래서 새로운 후보를 만든다.

## 9. H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas

```text
                ORIENTATION
                    │
        ┌───────────┼───────────┐
        │           │           │
 INVESTMENT      EXPLORE     DECISION CONTEXT
        │           │           │
        └────── contextual ─────┘
             reasoning canvas
```

이 그림은 논리 구조이며 최종 navigation label이 아니다.

각 공간 안에서 active question에 따라 lens를 바꾸되 scope / mode / provenance는 안정적으로 유지한다.

예:

- IREN 실적 → Investment + Monitor/Update
- AI power infrastructure → Explore + Theme/Relationship
- IREN vs NBIS → Decision Context + Compare/Future
- Morning review → Orientation + Triage

### 왜 H5가 유망한가

**space와 reasoning lens를 서로 다른 것으로 취급**하기 때문이다.

그러면 News, AI, Relationships, Scenario, History, Compare 같은 기능을 모두 top-level menu로 만들 필요가 없고, 동시에 AI가 매번 UI 전체를 마음대로 바꾸는 것도 막을 수 있다.

### 중요한 constraint

Adaptive composition이 Research / System Synthesis를 User Investment View나 Judgment로 조용히 보이게 해서는 안 된다.

## 10. 이번 Batch에서 기각한 것

- **Pure feature-menu IA** — 여전히 leading model로는 비추천.
- **Pure H1 minimalism** — theme/investigation workflow가 중요하면 너무 좁음.
- **Unconstrained question-first UI** — chat answer generator는 IA가 아니다. Durable coordinate와 return path가 필요.
- **Universal Explore bucket** — Explore는 question/theme/relationship investigation을 소유해야지 모든 deep feature의 저장소가 되어서는 안 됨.

## 11. 남은 불확실성

- 논리 공간 4개가 retail user에게 이미 많은가? 아니면 navigation label은 더 적게 보이면서 내부 책임은 4개로 유지할 수 있는가?
- Explore와 Investment가 evidence / scenario를 중복하지 않게 할 수 있는가?
- question-first adaptation이 반복 사용 후에도 예측 가능하게 느껴지는가?
- mobile에서 무엇을 resumable state로 저장해야 하는가?
- Portfolio는 Orientation / Decision Context 안의 object인가, visible space가 필요한가?
- Watchlist / coverage set은 Orientation과 어떻게 연결되는가?
- customization은 언제 도움이 되고 언제 설정 부담이 되는가?

## 12. Recommendation

**H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas**를 다음 leading prototype hypothesis로 가져가되, H1은 simplicity challenger, H2는 explicit-space challenger로 남긴다.

**Recommendation Strength: Strong**

아직 final IA를 승인하지 않는다. 다음에는 실제 screen-level navigation과 mobile return behavior를 prototype으로 확인한 후에야 top-level architecture commitment를 검토한다.

## 13. Failure / Reversal Conditions

다음이 반복되면 H5를 단순화하거나 뒤집는다.

- 사용자가 task가 어디에 속하는지 예상하지 못함
- Explore와 Investment가 계속 같은 내용을 중복함
- adaptive lens가 orientation을 깨뜨림
- mobile state restoration이 나쁨
- H1 같은 단순 구조가 exploration ability를 거의 잃지 않으면서 훨씬 편함
- portfolio/comparison task에 별도 persistent structure가 필요함
- 실제 사용에서 question-first entry가 예상보다 중요하지 않음

## 14. CEO Critical Decision

**이번 Batch에는 없음.**

H5는 Working IA hypothesis이며 top-level navigation, screen name, Product IA를 잠근 것이 아니다.