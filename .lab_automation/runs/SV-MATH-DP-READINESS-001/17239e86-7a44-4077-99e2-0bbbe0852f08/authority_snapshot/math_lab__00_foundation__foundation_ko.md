# Stock_vis Math Lab Foundation

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab은 금융시장 숫자에서 재현 가능한 예측 구조를 발견하고, 그 구조가 언제 성립하고 언제 무너지는지 밝히기 위해 존재한다. 모델 자체는 목적이 아니라 도구다.

## 1. Purpose

> **Discover reproducible predictive structure in financial market numbers.**

한국어 의미:

> **금융시장 숫자에서 재현 가능한 예측 구조를 발견한다.**

Stock_vis의 상위 목적 `Better Investment Decisions`를 지원하되, Math Lab은 매수/매도 명령을 직접 생성하는 조직이 아니라 투자 관련 불확실성을 줄일 수 있는 quantitative knowledge를 만든다.

## 2. Scope

### 2.1 Information Source Axis

Math Lab은 모든 숫자를 같은 종류로 취급하지 않는다. 최소 provenance class는 다음과 같다.

- **market_native** — 가격, 수익률, 거래량, volatility, order-flow 등 시장에서 직접 관측되는 수치
- **fundamental_native** — 매출, 이익, 현금흐름, balance-sheet, valuation 등 기업 재무 수치
- **cross_market_native** — 금리, FX, commodity, index, option-derived 수치 등
- **stockvis_numerical_derived** — Stock_vis가 numerical-native input에서 계산한 feature
- **stockvis_semantic_derived** — Research / news / LLM / semantic relation 등 비수치 원천에서 수치화된 feature

`stockvis_semantic_derived`는 사용 가능하지만 numerical-native와 분리해 기록하며, 독립적 수치 검증으로 자동 간주하지 않는다.

### 2.2 Unit-of-Analysis Axis

Math Lab은 개별 종목에 제한되지 않는다.

1. **Single Asset** — 한 자산의 시계열 구조
2. **Cross-Sectional Universe** — 여러 종목의 상대적 구조와 순위
3. **Cluster / Group** — 데이터 기반 군집, factor, latent group
4. **Relational Network** — ChainSight 등을 포함한 node-edge 구조와 정보 전파
5. **Market / System** — 전체 시장의 breadth, dispersion, correlation, regime, systemic structure

### 2.3 Stock_vis / ChainSight

Stock_vis와 ChainSight는 Math Lab의 주요 upstream data platform이다. 그러나 현재 product-serving value가 과거에도 알 수 있었던 값이라는 가정은 하지 않는다. material research에서는 point-in-time provenance와 reconstructability를 확인한다.

ChainSight 관계는 truth assumption이 아니라 연구 가능한 structural input 또는 hypothesis generator다.

## 3. Scientific Principles

### Principle 1 — Predictability must be demonstrated, not presumed

시장에 usable predictive structure가 있다고 가정하지 않는다. null result와 실패도 정상적인 결과다.

### Principle 2 — Apparent predictability is fragile until challenged

좋은 결과는 leakage, overfitting, selection bias, data snooping, multiple testing, regime coincidence, data artifact 가능성을 먼저 공격한다.

### Principle 3 — Reproducibility precedes knowledge

다른 연구자가 material data, code, transformation, parameter, environment를 이용해 결과를 다시 만들 수 없다면 Math Knowledge로 승격하지 않는다.

### Principle 4 — Simplicity earns priority; complexity earns burden of proof

복잡한 모델은 parameter risk, tuning degrees of freedom, instability, compute, interpretability loss를 추가한다. 단순 기준모델 대비 추가 가치가 명확해야 한다.

### Principle 5 — Statistical validity, economic utility, and deployability are distinct

통계적으로 반복되는 구조, out-of-sample 예측력, 거래비용 후 투자 가치, production 운영 가능성은 서로 다른 claim이다.

### Principle 6 — Failure is durable output when well tested

잘 설계된 null, negative, contradicted result는 future search space를 줄이는 재사용 가능한 연구 자산이 될 수 있다.

## 4. Epistemic Boundary

```text
Numerical Observation
        ↓
Observed Pattern
        ↓
Candidate Quantitative Claim
        ↓
Experimental Result
        ↓
Replicated Result
        ↓
Validated Quantitative Knowledge candidate
```

그 이후 application layer는 별도다.

```text
Validated Quantitative Knowledge
        ↓
Candidate Signal
        ↓
Tradable Signal
        ↓
Production Model
```

특히:

> **Validated Quantitative Knowledge ≠ Tradable Signal ≠ Production Model**

## 5. Cross-Lab Authority Boundary

| 영역 | Primary Authority |
|---|---|
| 기업·산업·시장 의미, Research Knowledge / Understanding | Research Lab |
| 수치 데이터의 predictive structure와 quantitative evidence | Math Lab |
| 사용자 표현, 판단지원 experience, information architecture | Design Lab |
| product implementation | Product / Engineering |
| consequential cross-Lab decision | CEO / legitimate downstream authority |

한 Lab의 결과는 다른 Lab의 연구 Trigger가 될 수 있지만 authority를 자동 이전하지 않는다.

```text
Research Understanding → Math Research Trigger
Math Finding → Research Mechanism / Meaning Trigger
Design/User Finding → Research or Math Trigger
```

Math correlation은 causal Research Knowledge가 아니며, Research Understanding이 Math hypothesis를 자동으로 참으로 만들지도 않는다.

## 6. Investment Decision Boundary

Math Lab은 사용자의 최종 투자 judgment를 대체하지 않는다. forecast와 uncertainty를 생성하더라도 이를 실제 user experience와 decision support에 어떻게 배치할지는 Design / downstream methodology가 별도로 평가한다.

## 7. Foundation Evolution

Foundation은 빈번히 수정하지 않는다. 반복되는 pilot friction이나 material new evidence가 Purpose, Scope, Principles, authority boundary를 흔들 때만 reconsideration candidate를 만든다.
