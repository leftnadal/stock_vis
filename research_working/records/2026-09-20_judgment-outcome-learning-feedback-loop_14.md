# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 14

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-20  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** prior-record utility, development pilot, paired conditions, action fit, decision linkage, proportionality, harmful transfer, 다음 연구 행동, 파일럿 설계, 조건 비교, 잘못된 전이  
**Prior Record:** [Checkpoint 13](2026-09-19_judgment-outcome-learning-feedback-loop_13.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Related Official Documents:** [Research Methodology](../../research_lab/01_methodology/research_methodology.md), §§8–9; [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), §§3.4–4.1, §10.  
**Record Basis:** 사용자의 “좋아 다음작업하자” 요청, Checkpoint 13의 개발 설계, 최신 공식 문서 확인, AI의 파일럿 설계 제안. 실행·모델 호출·독립 평가 결과가 아니다.

## Current Position

합의된 연구 방향은 동일한 현재 사실·제약 아래 선정된 과거 경험 기록의 추가 제공 여부가 다음 연구 행동 제안의 질에 어떤 차이를 만드는지 비교하는 것이다. Checkpoint 13은 입력 동일성이 미확인·확인됨·현재 확인 불가인 세 합성 상황과 두 조건의 기본 구조를 제안했다.

이번 단계는 실제 파일럿을 시작하지 않고, 개발용 파일럿의 최소 구조와 평가 경계를 제안한다. Research Work의 reviewer 준비 보완과는 분리한다. 사용자의 수동 인계 부담을 줄이기 위해 이 본류 설계는 Chat 안에서 계속하고, Work 인계는 실행·새 권한·material blocker가 생길 때만 별도로 만든다.

## Proposed Development Pilot Structure — Not Yet Approved

세 상황 각각에 대해 baseline 조건과 prior-record 조건을 둔다. 현재 문제·사실·공식 제약·기본 지시·검토 기회는 동일하게 유지하고, 차이는 사전에 고정된 과거 경험 기록의 추가 제공 여부로 한정한다.

첫 실행 후보는 각 상황·조건을 독립 세션으로 반복하는 paired design이다. 한 대화에서 baseline 답변 후 기록을 보여주고 다시 답하게 하는 방식은 재검토 기회와 순서 효과가 섞이므로 피한다.

초기 반복 수 후보는 각 조건당 3회다. 세 상황 × 두 조건 × 세 반복이면 18개 응답이다. 이 수는 통계적 효능을 보장하는 표본 크기가 아니라 모델 변동과 명백한 방향성·부정적 전이를 관찰하기 위한 작은 development pilot 후보다. 모델·temperature/seed 지원 여부·비용·호출 승인은 미정이며 실제 실행 전에 따로 확인한다.

## Evaluation Candidate

단일 가중합 점수를 먼저 만들지 않고 각 응답을 다음 의미 질문으로 검토한다.

1. **Current-state fidelity** — 현재 확인된 사실·미확인·적용 조건을 정확히 구분하고 과장·창작하지 않는가.
2. **Action fit** — 제안한 다음 행동이 현재 연구 문제의 material한 공백을 실제로 다루는가.
3. **Decision linkage** — 그 행동의 가능한 결과가 이후 판단·범위 제한·종료·다음 질문에 어떻게 연결되는지 설명하는가.
4. **Proportionality** — 이미 해결된 검사를 불필요하게 반복하지 않고, 자료 접근·부담·실행 가능성·승인 경계를 반영하는가.

이는 새 공식 evaluation family나 영구 score rubric이 아니다. 항목은 서로 일부 관련될 수 있으며 기계적 합산을 전제로 하지 않는다.

별도 material failure flag 후보:
- unsupported causal conclusion / fabricated evidence;
- harmful transfer: 과거 경험의 적용 조건이 현재와 맞지 않거나 이미 해소됐는데도 그 경험 때문에 material하게 잘못된 행동·불필요한 보류·과장을 유발함;
- unauthorized execution: 추가 승인이 필요한 행동을 이미 허용된 실행처럼 취급함.

Failure flag는 문장 스타일의 작은 결함이 아니라 현재 연구 판단을 왜곡하는 경우에만 사용한다. 조건부로 승인 요청을 제안하는 것은 unauthorized execution이 아니다.

## Comparison Interpretation

각 응답을 현재 자료에 대해 먼저 평가한 뒤 같은 상황의 baseline/prior-record 조건을 비교한다. 조건 간 결과는 material improvement / no material difference / material worsening / indeterminate 정도의 기술적 비교로 시작할 수 있으나 이를 새로운 공식 등급으로 고정하지 않는다.

과거 기록 조건이 더 길거나 교훈을 직접 언급했다는 이유로 개선으로 세지 않는다. baseline도 이미 적절하면 no material difference가 정당한 결과다. prior-record 조건에서 harmful transfer가 나타나면 평균적인 다른 장점과 조용히 상쇄하지 않고 별도 보고한다.

첫 파일럿은 과거 기록의 선정·활용 가능성을 보는 development evidence다. 자동 retrieval 전체, memory architecture, 실제 연구 행동의 결과, 장기 생산성, 투자 성과를 입증하지 않는다.

## Evaluator Boundary

평가자에게 조건명, 설계자의 예상 승패, 과거 기록 제공 여부를 가능한 범위에서 첫 판정 전에 숨기는 방향을 유지한다. 답변 내용 자체로 조건을 추정할 수 있으므로 완전 비노출을 주장하지 않는다.

평가자는 하나의 모범 행동명과 문장 일치를 정답으로 삼지 않는다. 현재 자료가 허용하는 다른 유효 행동·조건부 계획·정당한 유지·종료를 인정한다. 새로운 좋은 답이 기준에 없으면 원자료와 연구 목적에 비추어 기준을 수정하고 두 조건 모두에 대칭 적용한다.

동일 evaluator가 두 조건을 비교하는 경우 위치·장황함·조건 추정 편향 가능성을 기록하고, 가능하면 개별 평가를 먼저 보존한 뒤 paired comparison을 한다. 실제 evaluator 구성과 reviewer 모델은 후속 실행안에서 결정한다.

## Role Separation / Handoff Boundary

Chat은 연구 질문, 비교 설계, 평가 의미, CEO 결정 범위를 책임진다. Work는 승인된 실행 범위 안에서 패키지 구성·로컬 검증·실행·결과 집계와 기술적 결함 보완을 자율적으로 수행한다.

중간 기술 수정마다 Chat↔Work 인계를 요구하지 않는다. Work가 Chat으로 상신할 기본 조건은 다음과 같은 material escalation이다.

- 평가 목표·Gold 의미·공식 Methodology 또는 승인 경계를 바꿔야 함;
- 추가 모델/API/비용/private payload 전송 등 새로운 권한·자원이 필요함;
- 결과가 기존 연구 방향이나 핵심 가정을 material하게 흔듦;
- Work가 근거로 해결할 수 없는 여러 정당한 연구 선택지 사이의 우선순위 결정이 필요함;
- 실행을 계속하면 historical fidelity나 비교 유효성을 훼손할 위험이 있음.

그 외 로컬 구현·fixture·validator·패키징·재현성 결함은 기존 승인 범위 안에서 Work가 수정·검증하고, material checkpoint 또는 완료 시 한 번에 보고하는 것을 기본으로 제안한다. 이 운영 경계는 아직 공식 Methodology 변경이 아니라 Chat/Work 협업 가안이다.

## Decision Scope / Next

추천은 3상황 × 2조건의 개발 묶음을 유지하고, 각 조건 3회 반복 후보와 위 네 의미 질문 + material failure flags를 실행 설계 후보로 삼는 것이다. 다음 단계에서는 실제 사용할 과거 기록/합성 기록, 모델·설정, 반복·순서, evaluator, 비용·데이터 전송 범위를 한 번에 묶어 실행 승인안을 작성할 수 있다.

이번 기록은 실제 모델 실행·reviewer 호출·held-out·memory admission·공식 Methodology/Terminology 변경·새 Job 생성·Research Work 범위 확장을 승인하지 않는다.

## Actual Actions

이번 GitHub 변경은 이 non-authoritative Working Record와 INDEX 발견용 참조 추가뿐이다. 공식 `research_lab/`, 기존 Work 산출물·Gold·prompt·실행 권한은 변경하지 않는다.
