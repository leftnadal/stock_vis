# Stock_vis Math Lab Operational Record Specification

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab 기록체계의 목적은 모든 생각을 저장하는 것이 아니라, **결과를 재구성하고 과적합·누수·source dependency를 평가하는 데 필요한 material information을 canonical home 하나에 보존하는 것**이다.

## 1. Logical Record Responsibilities

현재 최소 logical responsibilities는 다음과 같다.

1. Research Program
2. Research Case
3. Search / Experiment Family
4. Cross-Lab Handoff
5. Candidate Quantitative Claim
6. Experiment Protocol
7. Experiment Run
8. Data / Artifact Reference
9. Assessment
10. Quantitative Knowledge
11. Decision Record

물리적 파일/DB table 수와 동일할 필요는 없다.

## 2. Specialized Conditional Views

필요할 때만 사용한다.

- Universe View
- Entity Resolution View
- Data View
- Graph Data View
- Feature Definition
- Model Specification
- Benchmark Definition
- Holdout Exposure Record

반복 필요성이 입증되기 전에는 permanent top-level object로 무조건 승격하지 않는다.

## 3. Canonical Home Principle

같은 material information을 여러 문서에서 독립적으로 유지하지 않는다.

예:

- Protocol의 primary metric은 Protocol이 canonical home이다.
- Run의 실제 metric은 Run이 canonical home이다.
- Claim의 stated scope는 Claim record가 canonical home이다.
- Evaluation conclusion은 Assessment/Evaluation record가 canonical home이다.

README나 registry는 이를 참조하거나 자동 생성된 view로 보여줄 수 있다.

## 4. Status Axes

하나의 `status`로 모든 의미를 표현하지 않는다.

### Document Status

- Working
- Approved
- Superseded

### Case Status

- Proposed
- Active
- Paused
- Closed

### Protocol State

- Draft
- Registered
- Frozen
- Superseded

### Run State

- Queued
- Running
- Completed
- Failed
- Aborted
- Invalidated

### Contamination

- Clean
- Partially Exposed
- Contaminated
- Unknown

### Research Maturity

- Exploration
- Candidate Pattern
- Experimental
- Replicated
- Validated

### Evaluation Conclusion

- Supported
- Restricted
- Mixed
- Unresolved
- Contradicted
- Invalid

### Applicability

- Current
- Review Required
- No Longer Applicable

### Deployment

- None
- Candidate
- Shadow
- Production
- Retired

문서 승인, 연구 maturity, deployment를 서로 상속하지 않는다.

## 5. Program / Case / Family / Experiment / Run

```text
Program
  └─ Case
      └─ Search Family
          ├─ Experiment Protocol v1
          │    ├─ Run A
          │    ├─ Run B
          │    └─ Run C
          └─ Experiment Protocol v2
```

Family는 hidden search burden을 집계한다. Protocol은 design이고 Run은 execution이다.

## 6. Candidate Quantitative Claim

Claim은 metric을 복사한 summary가 아니라 평가 가능한 bounded assertion이다.

최소한 다음이 resolvable해야 한다.

- content
- modality
- market / universe
- unit of analysis
- frequency / horizon / period
- regime / condition
- supporting Experiment/Run refs
- assessment refs
- maturity
- applicability
- lineage

## 7. Data / Artifact Reference

material artifact에는 가능하면 다음을 보존한다.

- stable locator
- content hash
- source system / object / version
- extraction code commit
- effective time
- available_at
- recorded_at
- transformation chain
- entity/universe version
- known limitation
- point-in-time eligibility

binary file 자체를 GitHub에 둘 필요는 없다.

## 8. Protocol Mutation

결과 확인 후 protocol을 silently overwrite하지 않는다.

mutation class 후보:

- pre-result clarification
- non-material implementation repair
- material design change
- post-holdout redesign

마지막 두 유형은 새 version과 confirmation status review를 요구한다.

## 9. Attempt Registry

Registry는 manually maintained competing authority가 아니다. source manifests에서 생성되는 view가 기본이다.

Family-level registry에는 최소한 다음 terminal attempts를 포함한다.

- completed
- failed
- aborted
- invalidated
- retries

그리고 target/horizon/feature/model/seed/search budget/holdout exposure를 추적한다.

## 10. Assessment Record

공통 envelope 아래 subtype을 구분한다.

- critique
- reproduction
- replication
- evaluation
- process evaluation

material Assessment는 target version, purpose, scope, evidence/artifact refs, challenge, findings, limitations, unknowns, conclusion, re-evaluation condition을 보존한다.

## 11. Knowledge Record

Quantitative Knowledge record는 모든 실험 세부사항을 복사하지 않는다. 재사용 가능한 bounded finding과 그 warrant를 연결한다.

필수 의미 후보:

- canonical content
- scope / conditions
- effect / uncertainty
- replication profile
- source ancestry
- limitation
- current applicability
- re-evaluation condition
- evaluation refs
- lineage

## 12. Decision Record

Decision Record는 quantitative truth verdict가 아니라 consequential governance를 기록한다.

예:

- Purpose / Scope 변경
- large data purchase
- major infrastructure
- permanent core-role change
- cross-Lab authority decision
- production deployment

## 13. Runtime / Telemetry Plane

Telemetry는 canonical epistemic object와 분리한다.

가능한 telemetry:

- agent/model/prompt/tool version
- routing
- context retrieval
- retries / failures
- critic interventions
- latency / compute / cost
- handoff
- permission denial
- process-evaluation signal

Telemetry가 자동으로 Knowledge나 Lab Rule이 되지 않는다.

## 14. Write Authority

### Specialist / Research Agent

- assigned workspace write 가능
- experiment artifact 생성 가능
- candidate claim 제안 가능
- Foundation / Methodology / canonical Knowledge 직접 수정 불가

### Lead

- Case / synthesis / routing 관리
- candidate document 작성
- lifecycle action 제안
- consequential escalation

### Admission / Evaluation path

- claim-level warrant를 기록
- Knowledge promotion proposal 제공

### CEO

- consequential governance
- material review request
- epistemic conclusion 직접 overwrite하지 않음

## 15. Documentation Economy

다음은 canonical record로 무조건 저장하지 않는다.

- 모든 agent token
- every discarded idea
- redundant summary
- low-value intermediate reasoning

미래 연구자가 결과를 재구성·검증·재사용하는 데 material한 정보만 durable record로 승격한다.
