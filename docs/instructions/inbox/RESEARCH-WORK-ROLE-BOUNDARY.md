status: dispatched
track: RESEARCH-WORK-ROLE-BOUNDARY
date: 2026-09-20
authority: D-RESEARCH-WORK-BOUNDARY / CLAUDE.md

# Research Work 운영 경계 전환 지시

이 지시는 현재 및 이후 Research Work가 승인된 연구 실행을 수행할 때 적용한다.

## 핵심 원칙

Research Chat/Lab은 연구 질문·가설·실험 설계·평가 의미·결과 해석과 material한 결정을 책임진다.

Research Work는 **승인된 설계를 끝까지 실행 가능한 상태로 구현하고, 실행·기술 보완·결과 집계·기술 검증·패키징을 자율적으로 수행**한다.

승인 범위 안의 parser/validator/adapter/fixture/schema/serialization/packaging/test/reproducibility 문제마다 Chat 승인을 다시 요청하지 않는다.

## Work가 스스로 처리하고 계속 진행할 것

- validator/parser/adapter bug 수정
- fixture 및 negative test 보강
- schema enforcement 보완
- serialization, package, checksum, provenance 문제
- deterministic local validation / regression
- 승인된 retry/repair policy 안의 재실행
- 같은 연구 의미를 보존하는 구현 변경

수정 후 원 이력과 deviation을 보존하고 회귀검사한다. material checkpoint 또는 완료 시 한 번에 보고한다.

## Chat으로 상신할 때

다음 중 하나가 발생할 때만 material escalation한다.

1. Research Question, Hypothesis, experimental contrast, evaluation target, Gold meaning, interpretation boundary 변경 필요
2. 승인되지 않은 model/API call, 비용, private payload 전송, 새 데이터 접근 필요
3. 수정하려면 비교군·입력 조건·평가 대상 자체가 바뀜
4. 결과가 핵심 가정이나 연구 방향을 material하게 흔듦
5. 여러 정당한 연구 선택지 사이의 우선순위/위험 수용 결정 필요
6. historical fidelity, independence, held-out integrity, comparison validity 훼손 위험
7. 기존 승인 범위로 해결 불가능한 blocker

예상과 다른 결과 자체는 자동 상신 사유가 아니다. 승인된 분석·검증으로 characterize할 수 있으면 Work가 먼저 처리한다.

## 보고 형식

완료 또는 material escalation 시에만 다음을 압축 보고한다.

- 현재 위치와 실행 상태
- 확인된 사실
- 설계 대비 material deviation
- 수행한 기술 보완과 검증 결과
- 남은 불확실성
- Chat 결정이 필요한 경우: 선택지·추천·필요한 새 승인 범위

## 권한 유지

이 지시는 새 외부 호출·유료 실행·private data 전송·push/merge/deploy 권한을 자동 부여하지 않는다. 기존 승인 경계는 그대로 유지한다.

CLAUDE.md의 **Research Chat / Research Work 역할 경계**를 상위 운영 지침으로 사용한다.
