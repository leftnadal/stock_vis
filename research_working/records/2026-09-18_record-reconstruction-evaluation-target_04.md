# Working Record — Record Reconstruction Evaluation Target / Checkpoint 04

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** gold v0.2 candidate, 59 routes, semantic sufficiency audit, existing audit reconciliation, claim strength, prior evaluation citation, review independence, bounded approval, 의미 감사, 중복 작업 방지, 충분성, 주장 강도, 승인 범위  
**Prior Record:** [Checkpoint 03](2026-09-18_record-reconstruction-evaluation-target_03.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Related Official Documents:** [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), [Research Methodology](../../research_lab/01_methodology/research_methodology.md), [Operational Record Specification](../../research_lab/01_methodology/operational_record_specification.md).  
**Record Basis:** 직전 59개 허용 경로 의미 감사 추천에 대한 사용자의 응답 “좋아 다음작업하자”, 최신 공식 문서 및 Working Record 확인, 별도 Work 대화에 대한 맥락 검색. 원 패키지의 직접 감사나 독립 실험 결과가 아니다.

## Context and Approval Scope

사용자는 Gold v0.2를 development candidate로 유지하면서 prompt 교정보다 59개 허용 경로의 원문 기반 의미 감사를 우선하자는 직전 추천에 대해 다음 작업 진행을 요청했다.

이번 진행 범위는 기존 Research Work의 local 의미 감사, 기존 감사가 있다면 그 결과의 인수와 범위 대조, 빠진 항목 보완이다. 별도 Job 또는 Crosslab 이관을 지시하지 않는다. 개별 claim의 정답을 사용자가 승인한 것이 아니며, reviewer용을 포함한 추가 모델/LLM API 호출·비용 승인을 뜻하지 않는다.

기존 Option B 목표는 유지한다.

> 출력에 명시된 근거 경로가 해당 claim의 내용·강도·범위를 충분히 지지하며, 그 경로의 근거 역할을 정확히 표현하는가?

사용자에게 전달된 기준 결과는 Work 보고값인 41 valid / 2 invalid / 0 review-required이며 원 gold 기준 35/43은 이력으로 보존한다. 이 기록에서 두 결과의 정확성을 재인증하지 않는다.

## Additional Context — Existing Audit May Already Be Available

다른 Work 대화의 과거 AI 답변을 검색한 결과, 59개 경로 감사를 완료했고 access/role mismatch 0, gold 변경 없음, 재채점 41/2/0 유지, 추가 모델/API 호출 0이라고 보고한 내용이 확인되었다. 이는 원 감사 산출물에 대한 직접 확인이 아니라 다른 대화의 완료 보고다.

검색에서 얻은 탐색용 파일명은 다음과 같다.

- `StockVis_OptionB_Gold_v02_Rescore_8737355c.zip`
- `results/route_semantic_audit.json`
- `Route_Semantic_Audit_Handoff_ko.md`
- `protected/gold_v02_candidate.json`
- `rescore_v02.json`

Files에서 정확한 파일명과 단순화한 이름으로 검색했으나 해당 원본은 확보하지 못했다. 검색에서 언급된 이전 세션의 작업 경로도 현재 컨테이너에는 없었다. 이 사실은 Work 쪽 산출물 부재를 뜻하지 않는다. 위 이름은 확인할 후보이지 검증된 현재 경로·버전·해시가 아니다.

따라서 다음 지시는 '전수 감사를 무조건 새로 수행'이 아니라 '기존 산출물이 있으면 먼저 인수하고 이번 검토 범위와 대조한 뒤 부족한 부분만 보완'으로 한다. 이미 충분히 확인된 항목은 참조로 재사용한다. 과거 완료 보고를 이번 Chat 승인 이후 수행된 결과로 다시 쓰지 않는다.

## Work Execution Handoff

### 1. 기존 계보와 감사부터 확인

기존 batch `8737355cc59549c6bee5424cde069d43` 및 선행 batch `6f739c4557c84627993657509a9983d0`의 실제 연결을 확인한다. 현재 사용 중인 gold, 43개 frozen claim, 3개 출력, 원래 prompt, 원 reference inventory, validator, 감사 결과의 실제 경로·버전·해시와 입력 범위를 확인한다. 이 ID들은 앞선 Work 보고에서 전달받은 값이며 새로운 Job ID가 아니다.

기존 59-route 감사가 있으면 먼저 그 범위와 결과를 읽는다. 단순히 source access와 role 일치만 확인했는지, 주장 강도와 필수 추론의 충분성까지 확인했는지 대조한다. 후자까지 이미 근거가 있으면 재작성하지 않고 연결한다. 누락된 점검만 추가한다.

### 2. 59개 경로의 충분성을 같은 기준으로 확인

범위는 선택된 경로와 선택되지 않은 허용 경로 후보 모두다. 각 route가 어떤 frozen claim을, 당시 해당 조건에서 모델에게 실제 제공된 어떤 근거로, 어떤 역할·필수 결합·계산·추론을 통해 뒷받침하는지 확인한다.

근거에 적힌 문구의 존재와 그 문구가 claim의 전체 강도를 뒷받침한다는 판단을 분리한다. A와 B가 함께 필요한 경로와 A 또는 B가 각각 충분한 대안 경로를 혼동하지 않는다. 대안 경로가 있다는 이유로 원 출력의 잘못된 선택이나 무관한 추가 인용을 대신 정당화하지 않는다.

공유 source의 확인 결과는 재사용할 수 있지만 claim별 의미·시점·범위 차이를 생략하지 않는다. 필요한 derivation은 재현 가능한 계산·변환 또는 짧은 전제–결론 설명이며, 관측되지 않은 비공개 생성 사고과정을 복원하거나 수집하라는 요구가 아니다.

### 3. 우선 확인할 쟁점

- Prior-evaluation-only 경로: 과거 평가가 무엇을 실제로 확인했는지와 그 한계를 확인한다. 귀속된 기록 사실, 과거 실행 사실, 현재 직접 검증을 구분한다. 과거 평가를 무조건 금지하거나 자동으로 충분하다고 인정하지 않는다.
- `a4d...-q2-c2`: manifest와 prior semantic assessment가 각각 무엇을 뒷받침하는지, frozen SHA 검증 claim의 강도와 맞는지 확인한다. 현재 source batch checksum으로 과거 입력의 근거 결손을 메우지 않는다.
- `a4d...-q4-c4`: protocol failure만으로 재구성 불가가 도출되는지, 실제 입력 결손과 대체 경로 및 자료 범위가 결론을 뒷받침하는지 확인한다. new_inference 표시 누락과 추론 자체의 정당성을 구분한다.
- `2f9...-q2-c4`: 선택한 semantic assessment route와 source_direct 표기의 불일치를 원문·원출력에서 확인한다.
- 구판에서 새 기준으로 달라진 6건: 각각 충분한 대안 경로라는 이유가 실제로 성립하는지 확인한다.

이후 나머지 경로도 같은 원칙으로 포함한다. 단축 claim ID는 임의 확장하지 않고 원 산출물에서 대응시킨다.

### 4. 변경과 판정 보류 처리

원 gold v0.2, 기존 평가와 출력은 덮어쓰지 않는다. 충분성 감사로 정정이 필요한 경우 같은 Option B 의미 안에서 별도 후속 candidate와 변경 이유를 보존하고 frozen 출력에 미친 영향만 재채점한다. 정정할 필요가 없으면 점수 유지 이유와 실제 확인 범위를 보고한다.

현재 근거로 판정할 수 없는 항목은 그 이유와 분모를 보존한다. 근거가 실제로 부족한 경우와 감사자가 접근하지 못한 경우를 구분한다. 원 claim을 약화해 통과시키거나 모든 경로를 sufficient로 유지하는 것을 목표로 하지 않는다. 평가 목표 자체의 변경이 필요하면 임의 변경하지 않고 Chat에 상신한다.

## Review Independence and Additional Calls

검토자, gold 작성 참여 여부, 기존 점수·정답·작성 근거 노출 여부를 보고한다. 동일 Work/AI의 재독은 자가 재검토이며, 다른 세션이나 다른 모델이라는 이름만으로 독립 검증을 주장하지 않는다.

이미 허용된 검토자가 실제로 있는 경우 그 기존 권한 안에서 대조할 수 있다. 그렇지 않으면 자료 정리와 가능한 자체 감사를 진행하고 independent review는 미실시로 남긴다. 이번 요청만으로 새 reviewer 호출, 유료 검토, 외부 전송을 시작하지 않는다.

별도 결과 비노출 검토가 필요하면 입력 패키지만 준비할 수 있다. 최초 판정에는 기존 점수·gold verdict·작성자의 정당화를 구분해 두되, 평가에 필요한 claim·근거·계약·안전 정보는 제공한다. prior assessment가 해당 route의 실제 근거라면 그 본문을 감추지 않는다. 이미 노출된 정보를 비노출 상태였다고 소급하지 않는다.

## Expected Return and Completion Boundary

최소 반환물은 기존 감사의 재사용 범위와 추가 점검 범위, 59개 route별 근거 위치·짧은 충분성 설명·결론, 43개 claim 판정에 미친 영향과 변경 이유, 우선 쟁점의 결론, 검토자·노출·독립성 한계, 남은 미확인 항목이다. 실제 원문과 연결할 수 있는 패키지 또는 파일 참조와 확인된 해시를 함께 제공한다. 현재 Chat에서 확보하지 못한 파일을 이름만으로 인수 완료 처리하지 않는다.

완료는 모든 route에 대해 수행/재사용한 검토 또는 판정 불가 범위가 추적되는 상태다. 59/59 sufficient나 43/43 valid를 요구하지 않는다. 추가 모델 실행이 없으므로 점수 변화는 모델 성능 개선이나 새 factual reconstruction regression이 아니다.

그 결과를 본 뒤 평가 기준이 다음 개발 단계에 사용할 만큼 명료한지와 남은 모델 오류를 분리하여 판단한다. Prompt calibration이나 held-out은 자동 개시하지 않는다.

## Explicit Exclusions

추가 모델/LLM API 호출(독립 reviewer 포함), prompt 튜닝, held-out 실행, 과거 raw 실험 재실행, 공식 Methodology/Terminology 변경, permanent architecture, Research Knowledge/memory admission, Work 산출물 push/merge/deploy/promotion은 이번 범위에 없다. 별도 검토자 확보가 필요한 경우 자원·호출 결정은 분리한다.

## Authority Check and Actual Actions

이번 시작 시 `main`은 `a11eebe282ce5b0c64b98f2d9bc58479572ebd81`였다. 이 상태의 Working README, INDEX, Checkpoint 03, Evaluation Methodology §§6.2–7.5, Research Methodology §§14.1–15, ORS §7.3 관련 범위를 확인했다. 해당 공식 파일 blob은 각각 `a731f70218bfea57f5c33ddfe9b462bc1233bda0`, `5abcfc43bc6d775805aaf064a7f6dd05b8b1336a`, `e10fddb99d0f44eb17d9d343930001cc71426719`로 앞선 확인 내용과 같다.

Chat이 이번에 실제 수행한 것은 최신 상태·자료 접근 확인, 승인 범위의 인계문 정리, 이 후속 Working Record 및 INDEX 갱신이다. Work의 원 gold·감사 JSON·실행 결과를 직접 읽거나 수정하지 않았고, 59개 의미 감사 또는 독립 검토를 수행했다고 주장하지 않는다. 다른 채팅 세션에 자동 전달하지 않는다. 기존 결과의 인수·보완을 시작하는 데 추가 CEO 승인은 요구하지 않는다.
