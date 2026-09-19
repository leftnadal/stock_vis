# Working Record — Record Reconstruction Evaluation Target / Checkpoint 01

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** record reconstruction, gold audit, valid provenance route, selected_route_validity, route_set_completeness, compound, ambiguous, AND OR, annotation, retrospective rescoring, 근거 역할, 정답 기준, 경로 충분성, 재채점  
**Prior Record:** None for this topic. Related: [Judgment–Outcome–Learning / Checkpoint 03](2026-09-18_judgment-outcome-learning-feedback-loop_03.md).  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Related Official Documents:** [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), [Research Methodology](../../research_lab/01_methodology/research_methodology.md), [Operational Record Specification](../../research_lab/01_methodology/operational_record_specification.md), [Knowledge and Understanding Framework](../../research_lab/01_methodology/knowledge_and_understanding_framework.md).  
**Record Basis:** 사용자가 이번 대화에 붙여 넣은 Work 인계서, 현재 GitHub에서 읽은 공식 문서, 아래 외부 원문, AI의 검토 제안. 원 gold·43개 claim·실행 출력에 대한 독립 감사 결과가 아니다.

## Context

사용자는 Record Reconstruction Development Calibration v0.1.1 후속 gold audit 인계서를 확인해 달라고 요청했다.

- Source batch, as reported: `8737355cc59549c6bee5424cde069d43`
- Previous source batch, as reported: `6f739c4557c84627993657509a9983d0`

Work는 한 claim에 여러 basis가 함께 필요한 경우와, 여러 기록이 각각 충분한 지지 경로가 되는 경우를 일부 gold가 모두 compound로 처리했다고 보고했다. Work는 추가 모델 호출을 멈추고 평가 목표 선택을 요청했다.

AI가 이전에 gold annotation을 먼저 고정하도록 요구한 것은 유지하되, 여러 유효 경로와 선택 경로 내 필수 결합의 경계를 충분히 규정하지 않은 이전 인계의 한계를 인정한다. 이 한계가 실제 오류의 유일한 원인이라고 확정하지 않는다.

## Reported State and Verification Boundary

다음은 Work 보고값이며 이번 Chat에서 원본을 재채점하여 확인한 값이 아니다.

- v0.1.1 protocol complete: 3/3; evaluated claims: 43/43.
- 기존 gold/validator: 35 correct / 8 incorrect.
- 단일 basis gold: 26/26; compound/ambiguous gold: 9/17.
- 17건 audit: 5건 유지 가능, 11건 각각 충분한 경로의 중복 가능성, 1건 검증 기록 불충분.
- JSON Pointer 및 출력 완결성 문제 해결, 원 gold·출력 보존, audit 중 모델 호출 0으로 보고됨.

숫자 간 합계는 일치하지만 개별 판정의 정확성을 의미하지 않는다. Files의 batch 검색 및 관련 제목 검색, GitHub의 source batch 검색에서 원 gold와 세 실행 출력을 확보하지 못했다. 검색 미발견은 원본이 없다는 결론이 아니다.

공식 문서 확인 시작 시 main은 `5c804cca9d5393ffd141096dd681f2222e61880f`였다. 이 commit에서 Evaluation Methodology v1.1 §§1–10, Research Methodology v1.2 §§8–18 관련 범위, ORS v1.0 §§7–9, Scientific Philosophy v1.0 도입부, Knowledge and Understanding Framework v1.0 §§1–5, Working README와 INDEX를 읽었다.

## Review Conclusion — Recommendation, Not Approval

Option B를 development-only 주 평가 목표로 채택하고, 추가 모델 호출 없이 별도 gold v0.2 candidate와 validator로 기존 출력만 재채점하는 방향을 권고한다. 단, 아래 경계를 먼저 명확히 해야 한다.

주 평가 목표의 제안 문구:

> 현재 출력에 명시된 근거 경로가, 해당 claim의 내용·강도·범위를 충분히 지지하며 그 경로의 근거 역할을 정확히 표현하는가?

이는 과거 생성의 실제 인과 경로를 복원했다는 주장이 아니다. 모든 가능한 경로의 발견이나 최소 citation 수 최적화도 주 목표로 삼지 않는다.

## Required Clarifications

### 1. 선택 경로 내부의 결합과 경로 사이의 대안을 분리

`A AND B가 함께 필요함`과 `A만으로도 충분하고 B만으로도 충분함`은 구분한다. 여러 허용 경로가 있다는 사실만으로 claim을 compound 또는 ambiguous로 만들지 않는다.

Compound 여부는 해당 작업 계약에서 선택 경로 안에 실제로 필요한 basis 결합에 대해 판단한다. 문서 수, 원자료 값 수, basis 종류 수, 새 계산·추론 유무는 동일한 정보가 아니다. 불확실성은 경로가 여러 개라는 사실이 아니라 충분성·역할·선택 경로 식별 등에 무엇을 확정하지 못하는지로 표시한다. 최종 schema/label 구현은 Work가 이 의미를 보존하는 최소 범위에서 정교화한다.

### 2. 각각 충분함은 출처 독립성의 증거가 아님

두 문서가 같은 claim을 각각 지지하더라도 동일 raw evidence, 평가, 가정을 공유할 수 있다. route multiplicity를 독립 실험 수나 독립 지지 수로 해석하지 않는다. 공식 Evaluation Methodology §6.3의 source ancestry/dependency 구분을 유지한다.

### 3. 문구가 같다는 이유로 route 충분성을 인정하지 않음

원 claim의 내용·대상·시점·강도를 먼저 고정한다. Plan의 설계 의도만으로 실제 실행 동일성을 확인했다고 판단하거나, 과거 평가의 진술을 raw verification으로 바꾸어서는 안 된다. 다만 특정 문서에 실제 실행 근거가 포함되어 있는지는 원문을 확인해야 하며 파일명만으로 판정하지 않는다.

'유지 가능'으로 보고된 5건도 새 계약에서 재확인한다. 특히 계산으로 도출하는 경로와 prior assessment를 인용하는 경로가 함께 나열된 예시는 각각 충분한 대안인지, 실제 결합이 필요한지 구분한다. 이번 Chat에서는 해당 5건을 확정 승인하지 않는다.

검증 기록 불충분 1건은 단순 label 변경 문제가 아니다. manifest가 파일 존재·식별만 보이는 경우 그것만으로 검증 PASS를 인정하지 않는다. 모델에 제공된 자료에 충분한 verification evidence가 없으면 그 용도의 support gap을 보존한다. Chat/Work 검토자가 자료를 확보하지 못한 경우의 unassessed와, 입력이 충분히 확인되었는데 모델이 과장한 경우의 incorrect를 구분한다. 사후에 추가 확보한 자료를 당시 모델이 보았던 자료로 취급하지 않는다.

### 4. 두 metric의 책임을 바로잡음

`selected_route_validity`에는 선택 경로 내부의 필수 근거·추론 단계 충족과 role fidelity가 포함되어야 한다. 필수 결합 근거 누락을 부가 완전성 문제로 내려서 주 평가를 통과시키지 않는다.

`route_set_completeness`는 다른 충분한 대안 경로를 얼마나 찾아냈는지에 대한 별도 관찰이다. 이번 재채점에서는 성공 gate로 삼지 않고, 원 프롬프트의 요구와 출력 표현이 허용하는 범위에서만 보고한다. 모든 경로 열거를 요구하지 않았던 기존 출력에 새 의무를 소급하지 않는다. 전체 route set을 완전히 열거했다고 정당화할 수 없으면 '검토된 허용 route set 내 coverage'로 한정하거나 미평가로 남긴다.

Gold에 없는 출력 경로는 자동 오답도 자동 정답도 아니다. 추가 충분성 검토 대상으로 두고, gold 확장 시 이유와 버전을 남긴다. 중복 citation은 그 자체로 오답이 아니지만 무관하거나 잘못된 역할로 제시된 추가 citation을 하나의 맞는 경로 뒤에 숨겨서는 안 된다.

### 5. 외현적 근거 제시와 실제 historical generation 구분

모델이 실제로 어떤 근거 때문에 답을 생성했는지와 출력에 어떤 근거 경로를 제시했는지는 다르다. 선택 경로가 기존 출력에서 명확히 식별되지 않으면 임의로 가장 유리한 route를 선택해 모델의 선택으로 기록하지 않는다. 기록된 refs 집합이 claim을 지지하는지 평가할 수 있더라도 선택 행위 복원을 입증하지는 않는다.

원 citation inventory인 `record_refs_as_originally_reported`는 변경 없이 보존한다. Option A의 inventory 보존 기능은 Option B와 병행할 수 있으나 inventory를 compound 판정으로 치환하지 않는다. Option C는 현재 복원 가능한 실행 이력만 기술하고, 관측되지 않은 생성 인과는 미평가로 남긴다. 추가 reasoning trace 수집을 이번 작업의 전제나 승인 범위로 만들지 않는다.

### 6. 결정론적 validator의 한계와 회귀 비교

Validator는 사전 annotation의 논리와 매칭을 일관되게 검사할 수 있지만 annotation의 의미적 충분성 자체를 독립적으로 입증하지 않는다. 원문 기반 근거와 반례 검토를 annotation에 남긴다. 같은 AI의 재검토를 독립 검증이라고 부르지 않는다.

기존 35/43은 당시 gold/validator 결과로 그대로 남기되 안정된 evidence-role 성능으로 해석하지 않는다. 동일 출력의 새 점수 변화는 평가 계약·annotation 변화에 따른 재채점이며 모델 능력 개선이 아니다. 전후 출력의 능력을 비교하려면 호환되는 동일 목표와 동일 evaluator version을 적용해야 한다.

모든 claim에 raw route가 허용되어 높은 점수가 나와도 participant explanation, prior evaluation, new inference 구분 능력이 시험됐는지 별도로 확인한다. 해당 역할이 필요한 claim의 수·범위와 오분류를 함께 보고하고, 없는 테스트 기회를 통과로 취급하지 않는다.

## Proposed Work Sequence — Pending User Execution Approval

1. 원 입력·43개 claim ID/내용·gold·validator·세 출력·당시 prompt와 original reference inventory를 보존하고 새 산출물과 연결한다.
2. 위 target 의미를 먼저 명시한 별도 gold v0.2 candidate를 만든다. 기존 정답으로 분류된 26건과 유지 후보 5건도 포함해 43건 모두 같은 기준으로 검토한다.
3. route별 source locator, basis role, 필요한 결합/계산, claim support 근거, 불확실성 및 해당 실행 입력에서의 접근 가능성을 annotation한다. 모든 필드를 영구 schema로 고정하지 않는다.
4. AND/OR 구분, role 오표기, 필수 근거 누락, 충분한 중복 citation, 무관 citation 추가, 자료 부족, 선택 경로 식별 불가, gold 밖 후보 경로를 synthetic fixture로 검사한다.
5. 기존 v0.1.1 출력만 byte-preserving하게 재채점하고 구판/신판 점수와 claim별 변경 이유를 함께 보고한다. 모델 재호출이나 이번 단계의 prompt 튜닝은 하지 않는다.
6. 구조 유효성, 근거 경로/역할 적합성, factual reconstruction·original request 결손·인과 과장 문제를 구분하여 검토한다. 재채점만으로 새로운 모델 regression 실험을 했다고 표현하지 않는다.

## Alternatives and Trade-offs

- A 중심: 원 인용 목록을 복원하는 목적에는 적합하나 근거의 충분성과 역할 정합성을 대신하지 않는다. 여러 citation을 보존한다고 compound로 묶어야 하는 것은 아니다.
- B 중심: 현재의 근거 역할 판별 목표에 가장 적합하다는 추천. route별 annotation 부담과 유리한 경로만 골라 통과시키는 위험이 있다.
- C 중심: historical causal provenance라는 다른 질문에 충실하지만 현재 보고된 자료로 상당 부분 식별되지 않는다. B 결과로 C를 성취했다고 말하지 않는다.
- 모든 route 완전성까지 주 성공 조건으로 추가: 원래 task보다 넓어지고 기존 출력에 없던 의무를 소급할 수 있어 이번에는 권고하지 않는다.

## External Context

- W3C PROV-DM, §2.1.2: 활동이 입력을 사용하고 출력을 생성했다는 사실만으로 그 입력에서 출력이 실제 derivation되었다고 보장하지 않는다는 구분을 참고했다. https://www.w3.org/TR/prov-dm/
- Gao et al., Enabling Large Language Models to Generate Text with Citations (ALCE), §3.3: 인용 근거의 support와 irrelevant citation을 구분하고 최소 citation 집합을 강제하지 않는 접근을 참고했다. ALCE의 citation recall은 여기서 제안된 '모든 대안 route 발견'과 같은 metric이 아니며, 그 benchmark 성과를 Stock_vis에 이전하지 않는다. https://arxiv.org/html/2305.14627v2

외부 원문은 관련 개념의 비교 자료이며 이 gold/validator의 정확성에 대한 검증 결과가 아니다.

## CEO Decision Scope / Open Questions

추천 결정은 development 평가 목적을 외현적 valid-route와 역할 적합성으로 명확히 하고, 모델 재호출 없는 local gold/validator 개정·재채점에 한정하여 다음 작업을 승인하는 것이다. 개별 claim의 정답과 validator 정확성을 CEO가 판정하는 안이 아니다.

사용자의 이번 메시지는 인계서 검토 요청이다. 이 기록은 평가 계약 변경이나 Work 재채점 실행이 승인·수행됐다고 기록하지 않는다.

원본을 읽어 확인해야 할 것은 43개 annotation의 충분성, '유지 가능' 5건, 자료 부족 1건, 기존 prompt의 route 열거 요구, 선택 route의 식별 가능성, 역할별 실질적인 테스트 범위다.

## Change Scope

이번 GitHub 변경은 이 non-authoritative Chat 검토 checkpoint와 INDEX의 발견용 참조에 한정한다. 공식 `research_lab/`, Work의 gold·validator·prompt·출력·Job, 과거 checkpoint는 변경하지 않는다. 추가 모델 실험, held-out 실행, Methodology/Terminology 변경, permanent architecture, Research Knowledge/memory admission, Work 산출물 push/merge/deploy/promotion은 수행하거나 승인하지 않는다.
