# Working Record — Record Reconstruction Evaluation Target / Checkpoint 03

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** gold v0.2 candidate, retrospective rescoring, 41 valid, 59 routes, semantic audit, prior evaluation citation, claim strength, derivation, checksum, review independence, 재채점, 의미 감사, 주장 강도, 원문 대조, 독립 검토  
**Prior Record:** [Checkpoint 02](2026-09-18_record-reconstruction-evaluation-target_02.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Related Official Documents:** [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), particularly §§6–7 and §§13–14; [Research Methodology](../../research_lab/01_methodology/research_methodology.md); [Operational Record Specification](../../research_lab/01_methodology/operational_record_specification.md).  
**Record Basis:** 현재 사용자가 붙여 넣은 Work 결과 보고와 Chat의 후속 검토. 원 실행 파일·gold·59개 경로에 대한 직접 감사 결과가 아니다.

## Context and Reported State

사용자는 앞선 추천에 대한 동의와 함께 Option B Gold v0.2 candidate 작성·기존 출력 재채점 완료 보고를 전달했다. Checkpoint 02에서 승인한 작업은 추가 모델 호출 없이 local gold/validator를 보완하고 기존 출력을 재채점하는 것이었다.

Work 보고값:

- 구판 gold 기준: 35/43, 이력 보존.
- Gold v0.2 재채점: 41 valid / 2 invalid / 0 review-required.
- 개선된 판정 6건은 구판 gold가 각각 충분한 대안 경로들을 compound로 강제한 문제의 교정으로 설명됨.
- 모델 호출 0, 기존 prompt·출력·gold 변경 없음, Work push/merge/deploy 없음.
- 신규 validator/unit/integration tests 12 passed, 기존 gold/static tests 11 passed, runner tests 10 passed, source batch checksum 16/16 passed.
- Gold v0.2에 충분하다고 annotation된 경로 59개를 추가 의미 검토할 것을 Work가 권고함.

43은 frozen claim 판정 단위이고 59는 허용 경로 후보의 단위다. 59개가 독립 사례나 독립 증거라는 뜻은 아니다. 이번 재채점은 새로운 factual reconstruction 또는 unsupported-causality regression 실행으로 보고되지 않았다.

## Verification Boundary

이번 Chat은 current main `f086fb94246754b6cb79975c601f2072c9a1dc5e`와 Checkpoint 02, Working README/INDEX를 확인하고 Evaluation Methodology의 근거 충분성·강도·추론·평가 재사용 관련 부분을 다시 읽었다. 읽은 Evaluation Methodology blob은 `a731f70218bfea57f5c33ddfe9b462bc1233bda0`이다.

Files에서 Gold v0.2 및 재채점 관련 내용·제목을 검색했지만 해당 원본을 확보하지 못했다. 현재 conversation 파일 목록은 0개였으며 사용자가 나열한 네 자료명에는 이 턴에서 사용할 수 있는 실제 파일 참조가 없었다. Library 검색 미발견은 자료 자체가 없다는 결론이 아니다.

따라서 수치, 테스트 통과, checksum, 두 오류와 6건 교정 이유는 Work 보고 상태다. 이 Chat이 재실행·재채점하여 확인한 사실로 승격하지 않는다. 특히 구판/신판 claim별 전이표와 원문을 읽지 않고 6건의 정확성을 별도로 인증하지 않는다.

## Review Conclusion — AI Recommendation

보고된 작업은 앞선 한정 승인과 정합적이다. Gold v0.2는 development candidate로 유지하고, prompt 수정과 held-out 실행보다 59개 허용 경로 후보의 원문 기반 의미 감사를 우선할 것을 권고한다.

41/43은 해당 candidate gold/validator의 판정 결과이지 일반화 성능, 모든 claim의 사실성, gold 자체의 검증 완료를 뜻하지 않는다. `review-required=0`도 해당 규칙이 보류로 분류한 출력이 없었다는 뜻이지 외부 검토할 문제가 없다는 뜻은 아니다. 같은 출력의 재채점이므로 성적 변화는 모델 능력 변화가 아니다.

## Residual Errors and Priority Questions

### 1. `2f9...-q2-c4` — prior evaluation을 source_direct로 표시

Work 보고대로라면 이는 원래 시험하려던 근거 역할 판별의 잔여 오류다. 과거 평가를 인용한 것과 원자료에서 직접 확인한 것을 구분해야 한다. 현재 Chat에서는 정확한 frozen claim·선택 refs를 읽지 못했으므로 단축 ID를 임의 확장하거나 최종 판정을 재확정하지 않는다.

### 2. `a4d...-q4-c4` — protocol failure에서 재구성 불가를 도출

new_inference 및 derivation 누락을 검사하는 것 외에 전제에서 결론이 실제로 정당하게 도출되는지도 봐야 한다. protocol failure만으로 final artifact가 존재하지 않거나 재구성 불가능하다고 일반적으로 결론 내릴 수는 없다. 실제 제공 자료의 결손, 대안 경로 유무, 시간·자료 범위가 frozen claim의 강도를 뒷받침하는지 확인한다.

이 검토는 새 오류가 추가로 확정됐다는 뜻이 아니다. 단순 역할 누락인지 내용상 추론 과장도 있는지 확인해야 한다는 감사 질문이다. 근거 기록에는 재현 가능한 계산·변환 또는 짧은 전제–결론 설명이 필요할 수 있으나 비공개 사고과정 복원을 요구하지 않는다.

### 3. `a4d...-q2-c2` — SHA 검증 claim의 충분성

Work는 manifest만으로 충분하지 않지만 prior semantic assessment도 인용되었으므로 valid로 판정했다고 보고했다. 이번 Chat은 이 claim을 임의로 invalid로 바꾸지 않지만, prior evaluation 인용이 있다는 사실만으로 frozen claim의 충분성을 확정하지 않는다.

- '과거 평가가 SHA 통과라고 기록했다'는 귀속된 기록 사실과 '해당 artifact가 실제 SHA 검증을 통과했다'는 실행 사실, '현재 직접 재검증했다'는 주장은 구분된다.
- 과거 평가를 실행 사실의 근거로 재사용하는 것이 언제나 금지되는 것은 아니다. 대상 artifact/run/version, 당시 실제 평가 내용, 중요한 근거·제약, 현재 claim의 강도와 목적이 충분히 호환되는지 확인해야 한다. 모든 재사용에 원자료 재실행을 일률적으로 요구하지 않는다.
- manifest가 관련 있지만 충분성에 필수적이지 않은 참조라는 표시는 가능하다. 그러나 그 표시가 충분한 인용처럼 잘못 제시된 사실이나 잘못된 basis role을 면제하지는 않는다.
- 현재 source batch checksum 16/16 보고를 이용해 당시 frozen claim의 근거 결손을 사후 보충하지 않는다. 두 검증의 대상과 시점은 별도로 확인해야 한다.

## Proposed Next Work — Scope and Review Independence

다음 작업은 기존 Research Work 계보를 유지하는 development gold 의미 감사로 제안한다. 새로운 schema, 모델 구조, 공식 평가 family를 만들 필요는 없다.

1. 59개 candidate route 각각을 frozen claim·당시 접근 가능 입력·정확한 근거 위치에 연결하고, 기존 평가 목표 아래 역할 표시, 주장 강도, 필수 결합/계산, 대안 경로와 자료 부족을 검토한다. 동일 source에 대한 검토는 참조로 재사용할 수 있지만 claim별 충분성 검토를 생략하지 않는다.
2. 두 invalid만 검토하지 않는다. 기존 41 valid에서 선택된 경로와 아직 선택되지 않았지만 gold에 허용된 경로를 함께 본다. 원출력에서 선택하지 않은 다른 경로로 틀린 선택을 대신 정당화하지 않는다.
3. 우선순위는 prior-evaluation-only 경로, SHA claim, 재구성 불가 같은 결손 기반 추론, 6건 교정 경로다. 이후 나머지에도 같은 기준을 적용한다. 59개 전부를 sufficient로 유지하거나 43/43으로 만드는 것이 목표가 아니다.
4. 각 경로의 유지·수정·제외·판정 보류 이유와 최소 근거를 남기고, 43개 판정에 미치는 영향을 후속 평가 버전으로 연결한다. 원문을 약화해 통과시키지 않으며 약한 재진술이 필요하면 별도 제안으로 둔다. 자료가 없어 판정할 수 없을 때는 그 범위를 보존한다.
5. 판단을 원점에서 분리하여 대조할 수 있는 별도 검토자를 확보한다면, 첫 판정에는 기존 점수·gold verdict·작성자의 정당화·모델의 예상 label을 가능한 한 가리고 필요한 claim·출처·계약·안전 정보는 제공한다. prior assessment가 검토할 Evidence라면 그 본문을 숨겨서는 안 된다. 최종 비교 전에 1차 판정을 보존한다.

'독립' 여부는 검토자, gold 작성 참여 여부, 입력·기존 결론 노출, 검토 절차를 확인하고 제한적으로 설명한다. 같은 AI의 재독은 자가검토이고, 새 세션 또는 다른 모델이라는 사실만으로 독립성이나 오류 제거가 보장되지는 않는다. 이 Chat은 이미 41/43과 Work 설명을 보았으며 원본도 확보하지 못했으므로, 결과 비노출 독립 감사가 아니다.

새 LLM reviewer/API 호출은 대상 모델 재실행이 아니더라도 새로운 호출·자원 사용이다. 기존 모델 호출 0 경계를 자동으로 확대하지 않는다. 현재 승인 범위에서 가능한 자료 정리·원문 대조와, 추가 reviewer·비용 승인이 필요한 작업을 구분한다. 별도 검토자가 확인되지 않으면 independent review complete라고 보고하지 않는다.

## Interpretation and Completion

기준 안정화는 모든 출력의 정답화를 뜻하지 않는다. 감사 후 2개 오류가 그대로 남더라도 판정 근거가 명료해질 수 있다. 반대로 다수 valid가 보류나 invalid로 바뀔 수도 있다. 어느 경우든 근거와 변경 이유를 보존한다.

held-out 보류를 권고하는 이유는 단순히 두 오류가 남아서가 아니라 gold의 충분성 경계가 아직 의미 감사 전이기 때문이다. 감사 이후 평가 기준의 일관성과 남은 한계를 확인한 뒤 prompt calibration 또는 held-out 검토를 별도로 판단한다. 43/43을 후속 평가의 필수 조건으로 새로 만들지 않는다.

최소 반환 내용은 59개 경로별 감사 결과, 43개 판정과의 연결·변경 이유, SHA claim과 prior evaluation 재사용 범위, 미확인 사항, 역할별 실제 평가 기회, 검토자·노출·독립성 한계다. 긴 새 방법론 문서를 요구하지 않는다.

## Alternatives / Trade-offs

두 잔여 오류를 먼저 prompt로 고치는 안은 빠르지만 candidate gold의 약점을 기준으로 모델을 맞출 수 있어 지금은 후순위다. 일부 경로만 표본 검토하는 안은 부담을 줄이지만, 이번에는 이미 정해진 59개 허용 경로와 여러 공유 근거의 충분성을 확인해야 하므로 전수 의미 감사를 추천한다. 모든 원자료를 재실행하는 안은 현재 역사적 입력 기준과 비용·권한 경계를 넘으므로 일률적으로 요구하지 않는다.

## External Comparison

ALCE는 답변 correctness와 cited-passage support를 다른 측정 대상으로 두고, citation precision에서도 불필요한 인용과 최소 집합 요구를 구분한다. 이번에는 그 구분을 참고할 뿐 ALCE 지표를 이 gold의 새 규칙으로 채택하지 않는다. https://arxiv.org/html/2305.14627v2 (§§3.2–3.3)

## Approval and Actual Change Boundary

이번 메시지는 이전 추천 동의와 Work 결과 공유다. 59개 경로의 새 독립 의미 감사, 신규 reviewer/model 호출, 예산 사용이 이미 승인되거나 실행됐다고 기록하지 않는다. CEO에게 요청할 것은 후속 검토의 우선순위·자원·범위이지 개별 경로의 정답 판정이 아니다.

이번 Chat의 실제 GitHub 변경은 이 Working Record 추가와 INDEX의 발견용 참조 갱신뿐이다. 공식 research_lab 문서, 이전 checkpoint 본문, Work gold·validator·prompt·출력은 변경하지 않는다. Gold promotion, 추가 모델 실행, held-out, Methodology/Terminology 변경, permanent architecture, Research Knowledge/memory admission 또는 Work push/merge/deploy/promotion은 수행하지 않는다.
