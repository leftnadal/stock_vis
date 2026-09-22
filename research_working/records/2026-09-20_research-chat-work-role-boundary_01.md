# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 15

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-20  
**Topic:** Research Chat / Work Role Boundary  
**Keywords:** chat work boundary, research design, investigation, execution autonomy, escalation, handoff minimization, 역할 분리, 실행 자율성, 인계 최소화, Research Work  
**Prior Record:** [Checkpoint 14](2026-09-20_judgment-outcome-learning-feedback-loop_14.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Related Official Documents:** [Research Methodology](../../research_lab/01_methodology/research_methodology.md), especially §§8, 11–12; [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md).  
**Record Basis:** 사용자의 제안 “Research Lab은 완성도 있게 구성되고 실험을 제대로 짜는 데 집중하고, 실험 실행·보완·결과 처리는 Work의 일” 및 직전 Chat 제안에 대한 동의. 운영 방향 합의 기록이며 공식 Methodology 변경이 아니다.

## Agreed Direction

Chat/Research Lab과 Research Work의 기본 역할을 다음처럼 분리한다.

### Chat / Research Lab

주 책임은 연구의 의미와 설계다.

- unresolved reality / Research Problem / Question을 정교화한다.
- 필요한 학계·산업 접근과 기존 Stock_vis 원칙을 검토한다.
- Hypothesis가 필요한 경우 가설과 경쟁 설명을 설계한다.
- 연구 범위, 비교 조건, 통제해야 할 차이, evidence strategy, failure condition, 평가 목적을 정한다.
- 실험이 무엇을 구분할 수 있고 무엇을 구분할 수 없는지 명확히 한다.
- 실행 전 material한 설계 선택과 자원·위험·권한 범위를 정한다.
- Work 결과를 해석하고, 연구 결론·다음 연구 방향·공식 변경 여부를 판단한다.
- 기술적 사실 확인이나 개별 판정 책임을 CEO에게 넘기지 않는다.

### Research Work

주 책임은 승인된 연구 설계의 실행과 실행 품질이다.

- 승인된 설계를 실제 입력·fixture·코드·패키지·실행 절차로 구현한다.
- 사전 조건, 무결성, instrumentation, provenance, checksum, validation을 준비한다.
- 실험·모델·reviewer 실행을 승인 범위 안에서 수행한다.
- 실행 중 발견되는 구현·validator·fixture·serialization·packaging·reproducibility 문제를 설계 의미를 바꾸지 않는 범위에서 자율적으로 수정·검증한다.
- 실패·중단·부분 완료를 숨기지 않고 원 실행 이력을 보존한다.
- 정해진 평가 계약에 따라 결과를 집계하고 기술적 검증을 수행한다.
- 결과, deviation, unresolved issue, 실행 비용·상태를 Chat이 판단할 수 있게 압축 보고한다.

## No Routine Ping-Pong

중간 기술 수정마다 Chat↔Work 인계서를 왕복하지 않는 것을 기본으로 한다.

승인된 설계·권한 안에서 해결 가능한 다음 항목은 Work가 스스로 처리하고 material checkpoint 또는 완료 시 한 번에 보고한다.

- validator / parser / adapter bug;
- fixture 보강;
- schema enforcement;
- local package / serialization / checksum issue;
- test or reproducibility failure;
- safe retry/repair when retry policy is already approved;
- deterministic validation and evidence packaging;
- 같은 의미를 보존하는 구현상 형식 변경.

이러한 수정은 historical fidelity를 보존하고 변경 이력을 남겨야 하며, 실험 의미를 조용히 바꾸면 안 된다.

## Escalation to Chat

다음과 같이 연구 의미·권한·비교 유효성에 material한 영향이 있을 때 Work가 Chat에 상신한다.

- Research Question, Hypothesis, evaluation target, Gold meaning, experimental contrast 또는 interpretation boundary를 바꿔야 할 때.
- 새로운 모델/API 호출, 유료 비용, private payload 전송, 새로운 데이터 접근 등 승인되지 않은 자원·권한이 필요할 때.
- 결손이나 구현 문제를 고치려면 실험 조건·비교군·평가 대상 자체를 바꿔야 할 때.
- 예상 밖 결과가 기존 핵심 가정이나 연구 방향을 material하게 흔들 때.
- 여러 정당한 연구 선택지가 남아 우선순위·위험 수용 결정을 내려야 할 때.
- 계속 진행하면 historical fidelity, independence, held-out integrity, comparison validity를 훼손할 위험이 있을 때.
- 승인 범위 안에서 기술적으로 해결할 수 없는 blocker가 생길 때.

단순히 예상과 다른 결과가 나왔다는 이유만으로 자동 상신하지 않는다. 승인된 분석·검증으로 결과를 충분히 characterize할 수 있으면 Work가 먼저 수행한다.

## Handoff Form

인계가 정말 필요할 때도 장문의 반복 문서보다 다음을 중심으로 한다.

- 현재 전체 위치;
- 확인된 실행 사실;
- 기존 설계와 다른 material deviation;
- 왜 Chat 결정이 필요한지;
- 가능한 선택과 Work 추천;
- 새 승인에 포함/제외될 범위.

Chat은 이 인계를 바탕으로 의미·방향을 결정하고, 다시 세부 구현을 micro-manage하지 않는다.

## Relation to Official Methodology

이 역할 분리는 Research Methodology의 책임 경계와 정합적이다.

- Research Design은 Question을 Investigation에 연결하며 scope, evidence strategy, alternatives, assumptions, threats to inference, evaluation purpose를 명시한다.
- Investigation은 설계를 실행하며 evidence acquisition, analysis, comparison, modeling, engineering, experiment 등을 수행한다.
- Evaluation Methodology는 대상·목적에 맞춰 결과와 과정의 warrant, 한계, uncertainty를 평가한다.

이번 합의는 공식 문서의 새 정의나 agent orchestration 알고리즘이 아니다. 실제 반복 사용에서 역할 경계가 잘 작동하는지 관찰한 뒤 필요하면 공식 운영 규칙 후보를 별도로 논의한다.

## Scope / Next

직전 prior-record utility development pilot 방향에 대한 사용자 동의도 보존한다. 앞으로 Chat은 파일럿의 연구 설계와 실행 승인안이 충분히 성숙할 때까지 설계를 다듬고, 승인 후 Work가 구현·실행·기술 보완·결과 패키징을 맡는 방향을 기본으로 한다.

이번 기록은 새 실험 실행·reviewer 호출·공식 Methodology 변경·memory admission을 승인하지 않는다.
