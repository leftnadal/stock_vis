# Stock_vis Design Lab

> **한국어 Companion 문서**  
> 이 문서는 [`README.md`](README.md)의 한국어 companion이다. 영어 파일은 canonical repository document로 유지하지만, 영어 문구 자체가 승인된 의미보다 우선하지는 않는다. 영어와 한국어 사이에 의미 차이가 발견되면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다. 한국어 companion 자체가 별도의 독립 authority를 만들지는 않는다.

**Source Synced:** 2026-08-27

이 디렉터리는 Stock_vis Design Lab의 공식 지식 및 운영 라이브러리다.

Design Lab은 Stock_vis의 더 넓은 목적인 **Better Investment Decisions**를 위해, Stock_vis가 사용자의 **Better Investment Judgment**를 어떻게 지원할 수 있는지를 연구하고 개선한다.

## Authority

- Research 개념과 Research Knowledge는 [`research_lab/`](../research_lab/)에서 관리한다.
- Design Lab의 Purpose, 운영 지식, Design Knowledge, Workstream, Design Decision은 각각 승인된 authority에 따라 `design_lab/`에서 관리한다.
- Design Lab 문서는 Research Lab 개념을 암묵적으로 재정의해서는 안 된다.
- 영어 파일은 repository의 canonical document이며, 한국어 companion은 빠른 검토를 위한 번역본이다.
- 번역 불일치가 생기면 영어 문구가 자동으로 승리하는 것이 아니라, 관련 CEO-approved intent와 authoritative decision을 기준으로 두 버전을 수정한다.

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
  - [`Exploration Log / Batch 01`](02_workstreams/001_investment_judgment_experience/exploration_ko.md)
  - [`Exploration Batch 02 — Judgment Update Logic & Information Model`](02_workstreams/001_investment_judgment_experience/batch_02_judgment_update_logic_ko.md)
  - [`Exploration Batch 03 — Judgment Structure Granularity & Human–AI Authorship Boundary`](02_workstreams/001_investment_judgment_experience/batch_03_authorship_granularity_ko.md)
  - [`Exploration Batch 04 — Judgment Experience Interaction Architecture`](02_workstreams/001_investment_judgment_experience/batch_04_interaction_architecture_ko.md)
  - [`Exploration Batch 05 — Low-Fidelity Wireflow / Prototype Exploration`](02_workstreams/001_investment_judgment_experience/batch_05_wireflow_prototype_ko.md)
  - [`Prototype 01 — Interactive Judgment Experience`](02_workstreams/001_investment_judgment_experience/prototype_01_judgment_experience.html) — Working prototype artifact
  - [`Synthesis`](02_workstreams/001_investment_judgment_experience/synthesis_ko.md)

Workstream 자료와 prototype artifact는 기본적으로 **Working** 상태이며, 자동으로 Approved Design Knowledge나 제품 architecture가 되지 않는다.

## Approved Decision Records

- [`DL-DR-0001 — Human–AI Judgment Authority Boundary`](04_decision_records/DL-DR-0001_human_ai_judgment_authority_ko.md)

Approved Decision Record는 명시된 scope 안에서 수정되거나 supersede되기 전까지 downstream Design work의 durable constraint로 취급한다.

## Growth Model

Design Lab은 실제 운영에 필요한 최소 구조에서 시작한다. 새로운 Workstream, Knowledge, Decision, Evaluation, Terminology, Design System 구조는 실제 작업에서 반복적인 필요가 생길 때만 추가한다.

Design Lab의 구조 자체도 사용, 관찰, consequential한 경우의 명시적 review, versioned update를 통해 계속 발전한다.

## Bilingual Documentation Rule

사용자의 빠른 검토를 위해 핵심 Design Lab 문서는 영어 원문과 한국어 companion을 함께 유지한다.

- 영어 원문은 canonical repository document로 유지한다.
- 한국어 companion은 가능한 한 구조와 의미를 1:1로 보존한다.
- 영어 원문이 materially 변경되면 한국어 companion도 함께 갱신한다.
- 한국어 companion에는 가능하면 source version / sync date를 표시한다.
- 번역 차이는 새로운 Design 개념이나 별도 결정으로 취급하지 않으며, 관련 승인된 semantic intent를 기준으로 해소한다.
