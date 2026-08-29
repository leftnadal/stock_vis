# DL-DR-0002 — Cross-Lab Judgment Semantic Boundary

> **한국어 Companion 문서**  
> 원문: [`DL-DR-0002_cross_lab_judgment_semantic_boundary.md`](DL-DR-0002_cross_lab_judgment_semantic_boundary.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이다. 독립 authority를 만들지 않는다. 의미 충돌이 생기면 CEO-approved semantic intent와 관련 Design / Research authority를 기준으로 정합시킨다.

**Source Synced:** 2026-08-27  
**Status:** Approved  
**Decision ID:** DL-DR-0002  
**Approved:** 2026-08-27  
**Effective Date:** 2026-08-27  
**Owner:** Stock_vis Design Lab  
**Decision Authority:** CEO / Project Owner

## 1. Decision

Stock_vis는 Approved Research Lab Knowledge and Understanding Framework와 정합되는 하나의 cross-Lab `Judgment` semantic boundary를 채택한다.

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

Design Lab은 Decision Context가 적용되기 전부터 존재하는 persistent company-level state의 authoritative 이름으로 `Judgment`를 사용하지 않는다.

Workstream 001에서 발견한 persistent Design-side object 자체는 여전히 필요하고 유효하다. 다만 이것은 **별개의 Design concept candidate**로 취급한다. 최종 명칭은 delegated exploration 대상으로 남기며 `Investment View`, `Company View`, `Thesis State` 또는 다른 label을 검토할 수 있다.

## 2. 왜 이 결정이 Consequential한가

`Judgment`는 Research ↔ Design ↔ Product 경계에 직접 걸쳐 있다. Research와 Design이 같은 label을 서로 다른 의미로 쓰면 future agent, 문서, ontology/schema, API, interface, downstream decision support에서 semantic drift가 생길 위험이 크다.

따라서 Design에서 경쟁 정의를 만드는 대신 현재 Research authority의 mental-model boundary에 맞춘다.

## 3. Required Invariants

### 3.1 Research Semantic Authority 보존

Cross-Lab concept인 `Judgment`에 대해서는 Understanding, Decision Context, Judgment, Decision, Action 사이의 관계를 Research Lab의 semantic authority가 규정한다.

### 3.2 Persistent Company-Level State는 별개

구체적인 Decision Context 이전에도 user-owned 또는 system-maintained company view는 존재할 수 있다. 하지만 이것이 이후 Judgment를 지원한다고 해서 자동으로 cross-Lab Judgment object가 되는 것은 아니다.

### 3.3 Decision Context는 Judgment보다 앞선다

Portfolio exposure, time horizon, alternatives, valuation, opportunity cost, constraints, switching cost 등의 decision-specific condition은 relevant Understanding 및 maintained view와 결합되어 Judgment를 지원할 수 있다.

이것들은 이미 형성된 Judgment 뒤에 붙는 단순 annotation이 아니다.

### 3.4 화면 결합이 semantic 통합을 의미하지 않는다

제품에서 maintained Investment View, System Synthesis, Decision Context, Judgment를 하나의 surface 안에 함께 보여줄 수 있다. 하지만 하나의 화면이나 component를 쓴다고 의미 구분이 사라지는 것은 아니다.

### 3.5 과거 Design language는 역사적으로 해석 가능해야 한다

Workstream 001의 초기 문서에는 alignment 이전 Working language로 `Judgment State`, `Judgment Workspace`, `User Judgment`가 남아 있을 수 있다. 이는 Research `Judgment`를 재정의하는 authority가 아니라 historical exploration language다.

Material한 downstream 문서는 정렬된 semantics를 사용해야 한다. 과거 exploration artifact는 의미가 충분히 명확하다면 모두 기계적으로 고칠 필요는 없지만, authoritative 또는 reusable Design Knowledge에는 ambiguity를 남기지 않는다.

## 4. DL-DR-0001과의 관계

DL-DR-0001 — Human–AI Judgment Authority Boundary의 실질적인 결정은 그대로 유효하다.

그 결정의 핵심은 **authorship / authority**였다. 즉 System Synthesis가 조용히 사용자의 maintained view가 되어서는 안 되며, material한 user-owned state 변경에는 실제 causal user control 또는 명시적 bounded delegation이 필요하다는 것이다.

DL-DR-0001에서 Decision Context 이전의 persistent state를 가리키며 사용한 `user-owned judgment` 표현은 이제 persistent **user-owned Investment View / equivalent Design concept**를 의미하는 것으로 정렬해서 해석한다. Research-governed Judgment를 재정의하는 뜻이 아니다.

Human–AI authorship boundary 자체는 바뀌지 않는다.

## 5. Workstream 001에 미치는 영향

Workstream 001 Foundation은 개념적으로 다음과 같이 교정한다.

기존 Working 표현:

```text
Persistent Judgment Workspace
→ Decision Context
→ Decision
```

Research-aligned 방향:

```text
Research Knowledge / Understanding
        ↓
System Synthesis
        ↕
Maintained User Investment View
        +
Decision Context
        ↓
Judgment
        ↓
Decision
        ↓
Action
```

Persistent Design-side state의 최종 label과 정확한 representation은 아직 Working이다.

## 6. Non-Decisions

이 결정은 다음을 확정하지 않는다.

- `Investment View`라는 최종 naming
- database schema 또는 ontology class
- System Synthesis와 user-owned view를 실제로 두 객체로 저장할지
- 최종 Product IA / screen 구조
- investment decision rule
- Judgment의 numerical / qualitative representation
- predictive / comparative Judgment input을 만드는 Research methodology

## 7. Rationale and Main Alternative

### 채택 방향 — Shared Cross-Lab Meaning

Research-approved semantic boundary를 사용하고 persistent Design-side state는 별도 identity로 발전시킨다.

이 방식은 사용자에게 지속적으로 수정 가능한 company view가 필요하다는 Design discovery를 유지하면서 장기 semantic ambiguity를 최소화한다.

### 주요 대안 — Design-local Judgment Definition

Design이 Decision Context 이전에도 존재하는 별도의 `Investment Judgment` product concept를 정의할 수도 있다.

Terminology Governance는 legitimate local concept를 허용하지만, `Judgment`의 semantic reach와 반복적인 cross-Lab use를 고려하면 이 ambiguity는 불필요하게 비용이 크다고 판단해 채택하지 않았다.

## 8. Failure / Reversal Conditions

다음 상황에서는 재검토한다.

- Research Lab이 upstream Judgment boundary를 공식적으로 변경함
- 이후 cross-Lab terminology governance에서 materially 더 좋은 shared semantic architecture가 승인됨
- 실제 운영 evidence에서 이 분리가 예방하는 문제보다 더 큰 semantic failure를 만든다고 확인됨

Material한 수정에는 explicit cross-Lab impact review와 CEO-level consequential approval이 필요하다.

## 9. Related Authority

- `research_lab/01_methodology/knowledge_and_understanding_framework.md`
- `research_lab/01_methodology/terminology_governance.md`
- `research_lab/04_decision_records/DR-0006-separate-epistemic-authority-consequential-governance.md`
- `design_lab/04_decision_records/DL-DR-0001_human_ai_judgment_authority.md`
