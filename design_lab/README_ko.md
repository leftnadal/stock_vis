# Stock_vis Design Lab

> **한국어 Companion 문서**  
> 이 문서는 [`README.md`](README.md)의 한국어 companion이다. 운영 및 의미 기준은 영어 원문과 동일하게 유지하며, 두 문서 사이에 의미 차이가 발견되면 원문을 기준으로 차이를 해소하고 한국어 문서를 갱신한다. 한국어 companion 자체가 별도의 독립 authority를 만들지는 않는다.

이 디렉터리는 Stock_vis Design Lab의 공식 지식 및 운영 라이브러리다.

Design Lab은 Stock_vis의 더 넓은 목적인 **Better Investment Decisions**를 위해, Stock_vis가 사용자의 **Better Investment Judgment**를 어떻게 지원할 수 있는지를 연구하고 개선한다.

## Authority

- Research 개념과 Research Knowledge는 [`research_lab/`](../research_lab/)에서 관리한다.
- Design Lab의 Purpose, 운영 지식, Design Knowledge, Workstream, Design Decision은 각각 승인된 authority에 따라 `design_lab/`에서 관리한다.
- Design Lab 문서는 Research Lab 개념을 암묵적으로 재정의해서는 안 된다.

## Bootstrap 읽기 순서

한글로 빠르게 검토하려면 아래 companion 문서를 읽는다.

1. [`00_foundation/foundation_ko.md`](00_foundation/foundation_ko.md)
2. [`01_operating_system/operating_model_ko.md`](01_operating_system/operating_model_ko.md)
3. [`01_operating_system/agent_protocol_ko.md`](01_operating_system/agent_protocol_ko.md)
4. [`01_operating_system/knowledge_lifecycle_ko.md`](01_operating_system/knowledge_lifecycle_ko.md)
5. [`01_operating_system/evolution_ko.md`](01_operating_system/evolution_ko.md)

영어 원문은 각각 같은 이름의 `_ko`가 없는 파일이다.

## 현재 Active Workstream

- [`Workstream 001 — Investment Judgment Experience Foundation`](02_workstreams/001_investment_judgment_experience/brief_ko.md)
  - [`Exploration Log`](02_workstreams/001_investment_judgment_experience/exploration_ko.md)
  - [`Synthesis`](02_workstreams/001_investment_judgment_experience/synthesis_ko.md)

Workstream 자료는 기본적으로 **Working** 상태이며, 자동으로 Approved Design Knowledge나 제품 architecture가 되지 않는다.

## Growth Model

Design Lab은 실제 운영에 필요한 최소 구조에서 시작한다. 새로운 Workstream, Knowledge, Decision, Evaluation, Terminology, Design System 구조는 실제 작업에서 반복적인 필요가 생길 때만 추가한다.

Design Lab의 구조 자체도 사용, 관찰, consequential한 경우의 명시적 review, versioned update를 통해 계속 발전한다.

## Bilingual Documentation Rule

사용자의 빠른 검토를 위해 핵심 Design Lab 문서는 영어 원문과 한국어 companion을 함께 유지한다.

- 영어 원문은 semantic source로 유지한다.
- 한국어 companion은 가능한 한 구조와 의미를 1:1로 보존한다.
- 영어 원문이 materially 변경되면 한국어 companion도 함께 갱신한다.
- 번역 차이는 새로운 Design 개념이나 별도 결정으로 취급하지 않는다.
