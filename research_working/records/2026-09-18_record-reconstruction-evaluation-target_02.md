# Working Record — Record Reconstruction Evaluation Target / Checkpoint 02

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** record reconstruction, gold v0.2 candidate, valid provenance route, selected_route_validity, route coverage, bounded execution approval, retrospective rescoring, 승인 범위, 근거 역할, 평가 계약, 재채점  
**Prior Record:** [Checkpoint 01](2026-09-18_record-reconstruction-evaluation-target_01.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Record Basis:** 직전 Chat 추천에 대한 사용자의 명시적 응답 “좋아 추천대로 하자”. 승인 범위와 Research Work 전달 내용을 보존하는 후속 기록이다. 새 실험 결과나 개별 gold 판정의 검증 기록이 아니다.

## Context and Current State

Work는 v0.1.1 출력의 기존 gold 평가에서 35/43 일치, 8/43 불일치를 보고했다. 후속 감사에서 함께 필요한 basis 결합과 각각 충분한 대안 경로를 일부 gold가 혼동한다고 보고했다. 원 gold·출력 보존, 감사 중 추가 모델 호출 0도 Work 보고 상태다.

Checkpoint 01은 Option B를 주 평가 목표로 하되, 선택 경로 내부의 필수 근거와 대안 경로 발견 범위를 분리하고 모델 재호출 없이 재채점할 것을 추천했다. 사용자는 이번 메시지에서 그 추천대로 진행하도록 승인했다.

이 승인으로 달라진 것은 한정된 Work 작업의 실행 허용 상태다. 개별 claim 정답, gold 충분성, 모델 성능, 영구 규칙을 CEO가 승인한 것은 아니다. 기록이 GitHub에 존재한다는 이유로 새로운 공식 Methodology나 추가 권한이 생기지 않는다.

## Approved Work Scope

담당은 Research Work다. 기존 작업과 artifact 계보를 이어간다. 이 인계는 Crosslab 이관이나 새로운 별도 Job 생성 지시가 아니다.

- Source batch, as reported: `8737355cc59549c6bee5424cde069d43`
- Previous source batch, as reported: `6f739c4557c84627993657509a9983d0`

주 평가 목표:

> 현재 출력에 명시된 근거 경로가 해당 claim의 내용·강도·범위를 충분히 지지하며, 그 경로의 근거 역할을 정확히 표현하는가?

승인된 실행은 development-only local gold v0.2 candidate 및 validator 보완과 기존 v0.1.1 출력 3개의 재채점이다. 추가 모델 호출과 prompt 튜닝은 이번 범위에 없다.

### Evaluation Boundaries

1. `selected_route_validity`는 선택 경로의 충분성, 경로 내부에 필요한 근거·계산·추론 단계의 충족, basis 역할 표시의 적합성을 포함한다. 필요한 결합 요소의 누락은 이 주 평가에서 처리하며 보조 완전성 문제로 낮추지 않는다.
2. `A와 B가 함께 필요함`과 `A 또는 B가 각각 충분함`을 구분한다. 문서 수, 데이터 값 수, basis 종류 수를 동일시하지 않는다. 복수의 충분한 경로만으로 compound/ambiguous를 강제하지 않고, 각각 충분함을 출처 독립성으로 해석하지 않는다.
3. 대안 경로 발견 범위는 보조 관찰이다. 기존 prompt가 모든 경로 열거를 요구하지 않았다면 새 의무를 소급하지 않는다. 전체 가능 경로를 포괄했는지 모르면 검토된 허용 route set 내 coverage로 한정하거나 미평가로 둔다.
4. Plan의 의도와 실행 사실, prior evaluation의 진술과 직접 검증, manifest의 존재와 검증 PASS를 구분한다. 각 조건에서 실제 모델에게 제공된 입력 안에서 충분성을 평가한다. 사후 확보 자료로 당시 근거 사용을 정당화하지 않는다.
5. 출력에서 선택 route를 식별하지 못하면 가장 유리한 route를 사후 선택해 모델의 선택으로 기록하지 않는다. gold에 없는 경로는 추가 검토 대상으로 두며 자동 오답/정답으로 만들지 않는다. 하나의 유효 경로를 이유로 무관하거나 역할이 잘못된 추가 reference를 숨기지 않는다.
6. 원 citation inventory인 `record_refs_as_originally_reported`를 보존한다. 실제 historical generation의 인과 경로는 이번 평가 대상이 아니며, 누락된 생성 과정을 임의로 복원하지 않는다.

## Execution Sequence

1. 기존 baseline의 입력, 43개 claim ID·내용, gold, validator, 세 출력, 당시 prompt, 원 reference inventory와 계보를 확인하고 보존한다. Work의 실제 경로·버전·해시는 현장에서 확인한다. 이 기록에 미확인 로컬 앵커를 만들지 않는다.
2. 점수와 별개로 주 평가 목표와 허용 route의 의미를 먼저 명시한 별도 gold v0.2 candidate를 만든다. 기존 불일치 8건뿐 아니라 43건 전체를 같은 기준으로 재검토한다. '유지 가능' 5건 및 자료 불충분 1건도 확정 정답으로 넘겨받지 않는다.
3. route별 근거 위치, 역할, 필요한 결합·계산, 충분성 판단, 불확실성과 해당 입력에서의 접근 가능성을 남긴다. Work는 승인된 의미를 바꾸지 않는 범위에서 annotation·fixture·validator 형식을 자율적으로 정한다.
4. 결합/대안 경로 구분, 필수 근거 누락, 잘못된 role, 충분한 중복 인용, 무관 인용, 자료 부족, 경로 식별 불가, gold 밖 경로를 synthetic fixture로 검사한다. 결정론적 검사는 annotation의 의미적 정확성에 대한 독립 검증이 아니다.
5. 기존 세 출력을 변경하지 않은 채 새 gold/validator로 재채점한다. claim별 원래 판정, 새 판정, 변경 이유를 연결한다. 미평가·근거 부족·불일치를 구분하고 분모와 판정 보류 건수를 밝힌다.
6. 구조 유효성, 근거 경로·역할 적합성, 사실 복원·original request 결손 인식·unsupported causal conclusion 문제를 분리해 보고한다. 실제로 역할 구분을 시험한 claim의 범위와 오분류를 표시한다. 모델 재실행 없이 새 모델 회귀 실험이나 능력 개선을 주장하지 않는다.

원본 결손이나 식별 불가 항목은 임의 재구성·제외하지 않고 범위를 밝힌다. 나머지 가능한 작업은 진행하되 전체 재채점이 차단되거나 평가 목표 변경·권한 확대가 필요하면 그 사유와 선택지를 Chat에 보고한다. 단순 경계 annotation마다 CEO에게 정답 결정을 요청하지 않는다.

## Expected Return to Chat

결과는 evaluator 교정 보고로 반환한다. 구판 35/43을 이력으로 보존하고 새 결과와 claim별 변경 이유, 판정 보류·근거 부족 항목, 역할별 실제 평가 범위, validator fixture 결과, 남은 실패·불확실성을 제시한다. 점수 상승 자체는 모델 성능 향상이 아니다.

다음 Chat 판단은 평가 목표·gold가 충분히 명료해졌는지, 현재 출력의 역할 판별 문제가 무엇으로 남는지, 이후 추가 calibration 또는 held-out 검토를 제안할 근거가 있는지다. 후속 모델 호출이나 held-out 실행은 이번 승인으로 자동 허용되지 않는다.

## Explicit Exclusions

추가 모델 호출, prompt 튜닝, held-out 실행, 공식 Methodology/Terminology 변경, permanent architecture, Research Knowledge/memory admission, Work 산출물 push/merge/deploy/promotion은 승인하지 않는다. 기존 원본과 과거 판정은 덮어쓰지 않는다.

## Authority Check and Actual Actions

이번 작업 시작 시 main은 `c93e89a7c30f27f24cd3c5e19b812ef7b6c54a2b`였다. 직전 authority 검토 기준인 `5c804cca9d5393ffd141096dd681f2222e61880f`와 비교한 결과 변경은 Checkpoint 01 추가와 INDEX 갱신의 두 파일뿐이었다. 따라서 직전에 읽은 Research/Evaluation Methodology, ORS, Scientific Philosophy, Knowledge and Understanding Framework 및 Working README의 상태는 그 검토 이후 변경되지 않았음을 확인했다. 이번에는 최신 INDEX와 Checkpoint 01의 실행·범위 부분을 다시 읽었다.

이 기록 작성 시 Chat이 실제 수행하는 변경은 이 후속 Working Record와 INDEX 갱신뿐이다. Research Work에 대한 전달문을 마련하지만 다른 채팅 세션에 자동 전송하거나 재채점을 실행했다고 주장하지 않는다. Work의 원 gold·validator·출력은 Chat에서 수정하지 않았으며, 승인 후 실행 여부와 결과는 후속 Work 보고로 확인해야 한다.

## Disposition

Checkpoint 01의 '승인 대기'는 당시 상태 그대로 유지한다. 이 후속 기록은 한정된 Work 실행이 사용자에게 승인됐다는 변화를 보존한다. 추가 CEO 결정은 이 범위의 실행을 시작하기 위해 필요하지 않다. 현재는 승인·인계 준비 상태이며 재채점 완료 상태가 아니다.
