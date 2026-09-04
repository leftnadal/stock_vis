# Stock_vis Math Lab — Working Constitution v0.1

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab  
**Branch:** `math-lab/bootstrap-v0.2`  
**Normative Status:** 아직 Approved Methodology가 아님

## 0. 한눈에 보는 요약

Math Lab은 Stock_vis의 독립적인 정량 연구실이다. 목적은 개별 종목, 종목군, 데이터 기반 군집, 관계 네트워크, 시장 전체 시스템의 금융 수치 데이터에서 **재현 가능한 예측 구조**를 발견하고 그 성립 범위와 실패 조건을 밝히는 것이다.

Math Lab은 좋은 backtest나 높은 모델 점수를 곧바로 지식으로 인정하지 않는다. 데이터가 당시 실제로 이용 가능했는지, 얼마나 많은 시도를 했는지, 미래정보나 생존편향이 섞이지 않았는지, 단순 기준모델을 이기는지, 독립적인 재현·반복에서도 유지되는지를 확인한 뒤에만 bounded quantitative knowledge 후보로 다룬다.

운영은 sub-agent 위임을 최대화하되, 다음을 보호한다.

- exploration과 confirmation의 분리
- point-in-time data integrity
- hidden multiple testing을 포함한 attempt history
- Critic / Replicator / Evaluator의 기능적 독립성
- canonical Knowledge의 직접 write 제한
- Cross-Lab source ancestry와 authority boundary
- 실패·null·invalid 결과의 보존

CEO / Project Owner는 수학적 사실 판정의 기본 reviewer가 아니라 Purpose, Scope, 자원, 장기 구조, Cross-Lab 경계, production 사용처럼 consequential한 결정을 맡는다.

## 1. Working Constitution 문서

현재 Working Constitution은 다음 문서들로 구성된다.

1. [`00_foundation/foundation_ko.md`](00_foundation/foundation_ko.md)  
   Purpose, Scope, Scientific Principles, Cross-Lab authority boundary.
2. [`01_operating_system/operating_model_ko.md`](01_operating_system/operating_model_ko.md)  
   CEO / Lead / Agent 기능, delegation, protected confirmation, escalation, Lab evolution.
3. [`02_methodology/research_methodology_ko.md`](02_methodology/research_methodology_ko.md)  
   Research Case, Search Family, Experiment, point-in-time data, replication, Data Gap / Opportunity.
4. [`02_methodology/evaluation_methodology_ko.md`](02_methodology/evaluation_methodology_ko.md)  
   Claim-level evaluation, statistical/economic/deployment separation, challenge, admission.
5. [`02_methodology/operational_record_specification_ko.md`](02_methodology/operational_record_specification_ko.md)  
   canonical record responsibilities, status axes, provenance, telemetry boundary.
6. [`02_methodology/cross_lab_interface_ko.md`](02_methodology/cross_lab_interface_ko.md)  
   Research ↔ Math ↔ Design trigger, operationalization, source ancestry, dependency review.
7. [`05_validation/bootstrap_consolidation_stress_test_ko.md`](05_validation/bootstrap_consolidation_stress_test_ko.md)  
   통합 과정의 conflict / redundancy / failure stress test와 남은 validation agenda.

같은 규칙을 여러 문서에 독립적으로 재정의하지 않는다. 각 문서는 자신의 authority domain만 소유하며, 다른 문서의 개념을 사용할 때는 참조한다.

## 2. Lab 전체 흐름

```text
Reality / Market Data / Cross-Lab Trigger
        ↓
Research Program / Case
        ↓
Fresh Question + Prior Attempt Registry Review
        ↓
Data Eligibility Gate
        ↓
Exploratory Research
        ↕
Critic
        ↓
Candidate Quantitative Claim
        ↓
Frozen Confirmatory Protocol
        ↓
Protected Confirmation
        ↓
Reproduction / Replication
        ↓
Structured Evaluation
        ↓
Lifecycle Action
        ├─ continue / revise / restrict / stop
        ├─ preserve null / negative / invalid
        └─ Quantitative Knowledge candidate
```

## 3. 핵심 구분

```text
Program ≠ Case ≠ Search Family ≠ Experiment ≠ Run
Data Source ≠ Point-in-Time Data View ≠ Feature Materialization
Model ≠ Model Use ≠ Model Run / Output
Run Metric ≠ Candidate Quantitative Claim
Critique ≠ Reproduction ≠ Replication ≠ Evaluation
Statistical Validity ≠ Economic Utility ≠ Deployability
Forecast Probability ≠ Epistemic Credibility
Cross-Lab Trigger ≠ Authority Transfer
Completion ≠ Validation
Null ≠ Inconclusive ≠ Invalid ≠ Contradicted
```

## 4. 현재 상태

이 Constitution은 실제 heterogeneous pilot과 software enforcement를 거치기 위한 **Active Working Baseline Candidate**다. Reversible exploration과 첫 vertical slice 구현을 안내할 수 있지만, 아직 irreversible production architecture나 큰 비용 결정을 정당화하는 final authority는 아니다.

다음 구현 단계의 첫 vertical slice는 `Data Eligibility Gate`다. 그 전까지 production schema의 큰 변경은 하지 않는다.
