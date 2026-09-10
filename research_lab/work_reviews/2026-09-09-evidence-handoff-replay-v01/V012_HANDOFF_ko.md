# StockVis Work → Chat: Replay 0.1.2 수정 후보

## Executive Summary
원 A의 코드 블록 JSON은 0.1.1에서 복구됐다. 실제 B는 E1/E2/E4 조회와 최종 응답까지 완료했으나 changes의 객체 목록을 검증기가 거부했다. 모델 프롬프트는 changes/limitations 내부 타입을 제한하지 않았으므로 문자열 전용 검사는 Work가 도입한 implementation defect였다. 이번 후보는 그 제약을 제거하고 A/B를 동일 파서로 오프라인 검증하며 미실행 4조건만 이어간다. 기존 실패·복구 기록은 수정하지 않는다. 실제 Mac 실행 결과는 아직 확보되지 않았다.

## Contract before / after
Before: changes/limitations는 문자열 목록만 허용.
After: 두 필드는 배열인지 검증하고 내부 JSON 값을 원형 보존한다. used_source_ids는 식별자 문자열 목록 유지. action, answer, 엄격한 JSON 문법, 단일 전체 fence, 중복 키/비정상 숫자 거부는 유지한다. 내부 값의 연구적 적절성은 별도 semantic review 대상이다. 프롬프트/요약/모델/config/실행 예산은 변경하지 않는다. 새 공식 schema나 methodology 채택이 아니다.

## Verification
12 tests passed, synthetic mocks only. A 저장 응답 및 B의 retrieve→final 2응답 복구; 문자열/객체 변경 기록 보존; B request-1을 원 조회 문서·원 event latency까지 포함하여 재구성 비교; 변조 요청 거부; 4건만 새 호출; 중복 실행 거부; 원 기록 byte 보존. 실제 provider 호출은 개발 검증에 포함하지 않았다.

## History / provenance
Original batch: 0b5220e04007446695d092f763b72020
Original A run: e1522095a29d41c9877be27c1a07003c
B run: 945be0e4f2bd447783e5521cd961c871
Original preparation: c5f1c67f8c38ad29f6ea69a53ff616abf2cb5908
Parent recovery candidate: 1412337d756fc27d310828b73e4c904e6e7c7977
Mac runtime: /Users/byeongjinjeong/Developer/stockvis_research_runtime/evidence-handoff-replay-v01
새 결과 위치: continuations_v012/동일 batch ID. 저장된 A/B는 원 inference latency/usage 유지. 복구 타임스탬프는 별도 기록. B 저장 요청/응답 원본은 Mac에 있으며 이번 GitHub 후보에는 포함되지 않았다. 아래 연구적 관찰은 사용자 제공 출력과 frozen source 대조에 따른 잠정 검토다.

## Findings / limits
A는 본문에서 확률 판단을 유보하지만 changes에는 낮은 달성 가능성 유지라고 기록한다. B는 산업 성장률과 회사 성장률의 연결 가정을 지적하고 낮은 가능성 결론을 반복하지 않았다. B는 E5 등 필요한 추가 자료를 조회하지 않았고 분모 수정은 검증하지 못했다. 이는 retrieval 실패가 아닌 미시도다. 조건부 19.7% 산술과 현실 적용 근거도 구분이 불충분하다. 여전히 네 조건 미실행이며 A/B/C 우열이나 일반화를 판단할 수 없다.

## Work recommendation
Strong: 저장 A/B를 재생성하지 않고 동일 파서 검증 후 기존 승인 범위 네 조건만 완료한다. 원 파일 불일치/새 실패 시 그대로 중단하고 원인을 조사한다. 새 methodology, 역할, runtime 구조나 평가 의미 변경이 필요해지면 Chat 인계한다. 모든 12개 평가 항목의 의미 검토는 실험 후 별도 수행한다. 이번 단순 구현 결함 수정에 새 연구 방향 승인은 필요하지 않다.

## Safety state
별도 feature branch 저장만 수행. main/merge/deploy/Approved 승격/장기 memory admission 없음. 원 Job 또는 Math Lab 파일 변경 없음. 실행 스크립트는 push하지 않는다. GitHub에 실제 실행 증거 저장은 Mac 결과 확보 이후 진행한다.
