# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 12

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-19  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** next research action, development vignette, source-grounded criteria, alternative answers, unknown input identity, evaluation leakage, 다음 연구 행동, 설계용 사례, 판정 근거, 대안 답변, 평가 누수  
**Prior Record:** [Checkpoint 11](2026-09-19_judgment-outcome-learning-feedback-loop_11.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Record Basis:** 사용자의 ‘좋아 다음작업하자’ 요청, 최신 GitHub·Library 조회, 아래 논의용 사례에 대한 AI의 설계 검토. 모델 실행·reader test·독립 의미 검증 결과가 아니다.

## Current Position

조회한 Library의 최신 관련 Work 인계는 준비본 0.2.1r1이며, 후속 수정 완료본은 이번 검색과 최근 파일 목록에서 찾지 못했다. 2026-09-19 05:28 UTC 기준 조회에서 최신 관련 파일은 Chat의 Completed 답신·재현 ZIP이었다. 이는 Work에서 보완을 시작하지 않았거나 후속 산출물이 존재하지 않는다는 단정이 아니다. GitHub의 평가목표 Checkpoint 09도 응답 수용 경계 보완과 실제 호출 미승인을 유지한다.

같은 인계를 재작성하거나 Work 수리를 대신 병행하지 않고, Checkpoints 10–11의 본류 설계로 진행한다. 합의된 것은 선택된 과거 기록의 유무가 제한된 다음 연구 행동 제안에 미치는 차이를 비교하는 방향이다. 이하 과제의 세부 내용은 아직 가안이다.

## Development Vignette — Illustrative Only

목적은 같은 기업 문서를 처리하는 두 분석 절차의 차이를 평가할 다음 행동을 제안하는 것이다. 비교하려는 처리 절차의 차이 자체와, 동일해야 할 문서 입력·평가 조건을 구분한다.

논의용 현재 자료: 한 번의 비교에서 B의 평가 점수가 A보다 높았다는 결과가 있다. 평가 항목과 채점 방식은 제시되어 있다. 각 실행에 실제로 전달된 문서 입력의 사본은 저장되어 있으나 내용 동일성은 아직 대조되지 않았다. 저장 자료의 오프라인 확인은 가능하고, 추가 모델 호출은 별도 승인 사항이다. 이들은 가상 사례의 설정이지 실제 Work에서 측정한 사실이 아니다.

선택적으로 제공하는 과거 경험의 설명용 문구: ‘예전에 두 절차가 서로 다른 문서 입력으로 평가되어 점수 차이의 원인을 절차 자체로만 설명할 수 없었다.’ 이 문구도 실제 과거 record의 인용이 아니다. 실제 파일럿에서는 출처·시점·선정 이유를 확인한 경험 자료로 대체하거나 합성 자료임을 명확히 해야 한다.

현재 자료와 과제·제약은 기록 제공/비제공 두 조건에 동일하게 제공한다. 평가에 필요한 현재 사실이나 공식 규칙을 과거 기록에만 숨기지 않는다.

## Proposed Assessment Boundary

미리 한 문장의 모범답안을 만들기보다, 현재 자료가 허용하는 주장과 필요한 확인·한계를 사례별로 명료하게 한다. 새로운 공식 profile이나 영구 schema가 아니다.

이 사례에서는 관찰된 점수 차이를 보고할 수 있지만, 입력이 다르다고 단정하거나 B의 일반적 우수성이 확정됐다고 말할 수는 없다. 입력 동일성이 미확인이라는 사실은 입력 불일치가 원인이라는 증거가 아니다.

저장된 입력을 먼저 대조하는 것은 유력한 행동이다. 그러나 오류 사례·채점 내용을 함께 확인하는 짧은 계획도 목적과 비용에 맞고 핵심 입력 공백을 해소한다면 허용될 수 있다. 더 나은 대안이 제시되면 행동 이름 불일치만으로 오답 처리하지 않는다. 입력이 같다는 결과만으로 실행 변동·다른 평가 불확실성이 모두 사라지지 않음을 보존한다.

‘입력을 확인한다’는 행동을 골랐어도 이미 입력이 다르다고 확정하거나 어떤 결과에도 같은 결론을 고집한다면 근거와 추론을 별도로 문제 삼는다. 반대로 과거 기록을 인용하지 않았어도 현재 자료에 맞는 제안이면 동등하게 인정한다. 답변이 길거나 경고를 많이 반복했다는 이유로 우위 점수를 주지 않는다.

## Contrast and Counterexamples

현재 실행의 입력 동일성이 정확한 대상·버전의 원문 대조로 이미 확인된 변형을 함께 고려한다. 그때에도 추가 이유 없이 동일 검사를 반복하는 답을 자동으로 좋은 답으로 보지 않는다. 다만 전후 조건이나 검증 범위에 실제 결손이 있다면 재확인이 정당할 수 있다. 절차의 의도된 차이까지 모두 제거해야 한다는 기준은 만들지 않는다.

이 예시와 변형은 설계자와 사용자에게 노출된 development 예시다. 아직 모델에 전달하거나 데이터셋으로 실행하지 않았다. 실제 응답 비교에서 더 나은 대안이 발견되어 평가 기준을 바꾸면 변경 이유·버전을 남기고 두 조건에 대칭적으로 적용한다. 조건별로 유리한 답만 사후 정당화하지 않는다.

채점자의 오류를 줄이기 위해 현재 자료와 평가 목적을 먼저 정의하고, 그에 비추어 과거 경험을 선정한다. 정답을 유도하는 자료를 일부러 고르는 방식은 피한다. 후보 평가를 결과 전에 적어 두는 것만으로 독립성이 보장되는 것은 아니며, 평가 근거 자체도 검토 대상이다.

## Limits and Next

이번에 구체화한 것은 한 사례의 현재 정보, 허용되는 판단 범위, 대안 답변의 인정 조건이다. 인과적인 기억 효과, 자동 검색의 효과, 실제 연구 실행의 이득 또는 투자 성과는 측정하지 않았다. 기준 모델이 이미 같은 판단을 할 가능성, 사례가 쉬워 차이가 없을 가능성, 경험의 잘못된 적용을 열어둔다.

이 기준을 다른 개발 사례에도 적용할 수 있을지 논의를 이어갈 수 있으나 사례 수·모델·비용·반복 횟수·통과 기준·실제 reviewer는 미정이다. 이번 메시지를 새 Job, 모델/계수 API, private payload 전송, held-out, memory admission 또는 공식 문서 변경 승인으로 해석하지 않는다. Work의 r1 후속 수리는 기존 인계를 유지하며 이 사례를 추가하지 않는다.

## Source Check and Actual Changes

시작 시 main: `570ee6224d0da0548560c92934207d635c798970`. 해당 상태의 Checkpoint 11, INDEX, Working README, Research Methodology §§8–9, Evaluation Methodology §10, Scientific Philosophy의 Reality 원칙 관련 부분을 직접 읽었다.

Ribeiro et al., Beyond Accuracy: Behavioral Testing of NLP Models with CheckList (2020), https://arxiv.org/abs/2005.04118 의 초록에서 전체 정확도 외에 능력·행동별 사례를 설계해 평가하는 접근을 참고했다. 해당 성능 수치·분류표를 StockVis에 이전하거나 실제 효과를 입증한 것으로 취급하지 않는다.

이번 GitHub 변경은 이 non-authoritative checkpoint와 INDEX 참조 갱신뿐이다. 기존 기록·공식 문서·Work 산출물은 수정하지 않으며, 로컬 모델·reviewer 또는 별도 평가를 실행하지 않는다.
