# Working Record — Record Reconstruction Evaluation Target / Checkpoint 06

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** gold v0.2.1, reviewer package, preparation only, execution plan, bounded approval, conditional evaluation reuse, reviewer isolation, 검토 패키지, 실행안 준비, 호출 미승인, 승인 범위  
**Prior Record:** [Checkpoint 05](2026-09-18_record-reconstruction-evaluation-target_05.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Related Official Documents:** [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), §14; [Research Methodology](../../research_lab/01_methodology/research_methodology.md), §§14.1–14.3.  
**Record Basis:** Checkpoint 05에 해당하는 직전 Chat 추천에 대한 사용자의 응답 “좋아 네 의견대로 가자”. 한정된 준비 작업 승인 이력이며 새 실험·감사 결과가 아니다.

## Context and Current State

사용자는 Gold v0.2.1을 다음 별도 검토의 development candidate로 사용하고, 기존 Option B와 과거 평가의 조건부 재사용을 유지하며, reviewer 패키지 갱신 및 실행안을 준비하자는 추천대로 진행하도록 승인했다. 실제 reviewer 호출은 구체적인 실행 범위를 확인한 뒤 별도 승인한다는 조건을 유지한다.

이전 Work 보고는 v0.2.1 활성 경로 56개, 부모 경로 59개 추적, frozen claim 43개 재채점 40 valid / 3 invalid / 0 review-required이다. 이 수치와 원본의 정확성을 이번 Chat이 재검증하거나 확정한 것은 아니다. Gold 작성자에게 노출된 self-audit라는 한계도 유지한다. 승인으로 바뀐 것은 준비 작업의 진행 허용 상태이며 정답표의 의미적 정확성이나 모델 성능의 지위가 아니다.

## Approved Preparation Scope — Research Work

담당은 기존 Research Work다. 기존 Job·batch·artifact 계보를 유지하며 새 Job이나 Crosslab 이관을 지시하지 않는다.

- Source batch (앞선 Work 보고): `8737355cc59549c6bee5424cde069d43`
- Previous batch (앞선 Work 보고): `6f739c4557c84627993657509a9983d0`
- 검토할 후보: Gold v0.2.1. 보고된 SHA-256은 `ed754d738abd57caf973d3c10a07ad569a142fb4f32018bbaebabf25013a938b`이며 실제 원본·현재 경로·해시는 Work에서 확인한다.

### 1. 기존 준비본을 인수하여 갱신

기존 opaque reviewer package가 있으면 재사용하고 필요한 부분만 v0.2.1에 맞춰 갱신한다. 이미 갱신된 산출물이 있으면 먼저 확인하고 중복 생성하지 않는다. 원 gold v0.2/v0.2.1, 당시 prompt, frozen claim·출력·source 및 과거 감사/재채점 결과는 변경하지 않는다. 새 reviewer 지시문 작성은 준비 범위지만 대상 reconstruction prompt 튜닝이나 모델 실행은 아니다.

활성 56개 경로와 부모 59개 경로의 연결, 제외·단순화·교체된 경로를 대조 가능하게 보존한다. 제외 판단도 검토 대상에 포함하되 이전 정답을 미리 알려주는 형태로 제출하지 않는다. 현재 활성 경로 수와 실제 reviewer 검토 항목 수를 구분한다. 기존 20/20/19 분할이나 호출 수를 고정하지 않고 실제 내용·문맥·입력 한도에 맞춘 묶음과 분모를 제안한다.

### 2. 원 claim 의미와 평가 목적을 유지

평가 목표는 출력에 명시된 경로가 claim의 내용·강도·범위를 충분히 지지하고 근거 역할을 정확히 표현하는가이다. 과거 평가 인용을 일괄 배제하거나 자동으로 충분하다고 인정하지 않는다. 귀속된 보고와 underlying fact, 현재 직접 검증을 구분하고 당시 질문·응답 계약·basis 및 참조 정보를 함께 보존한다. 감사자가 사후에 attribution 한계를 붙여 frozen claim을 약화해 통과시키지 않는다. 모든 underlying fact의 독립 재실행을 새 목표로 추가하지 않는다.

### 3. 결과 비노출 검토가 가능하도록 입력 분리

Reviewer의 첫 판단에 기존 aggregate score, 현재 gold의 판정·정답 label, 작성자의 정당화 및 정정 이유가 섞이지 않도록 별도 보관한다. 판단에 필요한 원 claim, 당시 질문·출력 계약, 근거 원문·정확한 위치, 출처의 성격과 관련 조건·자료 결손은 유지한다. 평가 대상인 prior assessment 본문을 단순히 평가 기록이라는 이유로 숨기지 않는다.

실제 reviewer에게 전달될 최종 직렬화 입력 전체를 대상으로 결론 누출과 문맥 손실을 정적으로 점검한다. Opaque ID만으로 비노출을 보장하거나 정적 검사를 독립 의미 검증으로 표현하지 않는다. Reviewer의 gold 작성 참여·기존 결과 노출 여부를 확인할 방법, 첫 판정 보존 후 gold와 대조하는 절차, 불일치를 원문과 계약으로 검토하는 방법을 실행안에 포함한다. 단순 다수결이나 새 reviewer의 결론을 자동 정답으로 삼지 않는다.

### 4. 호출하지 않고 한정된 실행안을 제시

추천 reviewer 또는 모델·버전·실행 환경, 선택 이유, 입력 묶음·토큰/문맥 추정 근거, 호출 및 재시도 상한, 출력 한도, 비용 추정·근거·상한, 외부 전달 데이터 범위, 중단 조건, 실패·부분 완료 처리와 산출물 위치를 제안한다. 현재 근거 없이 가격·가용성·토큰량을 확정하지 않으며 미확인 값은 표시한다. 이전 모델/예산/권한을 묵시적으로 승계하지 않는다.

패키지 생성·무결성·매핑·누출/문맥 보존을 확인하는 로컬 정적 검사와 기존 승인 범위의 로컬 테스트는 가능하다. Reviewer용을 포함한 모델/API 호출, 유료 작업 또는 데이터 업로드는 시작하지 않는다.

## Required Return and Completion

반환물은 갱신 패키지의 실제 접근 가능한 파일 참조와 확인한 SHA-256, 원본 보존·경로 매핑·검토 범위·정적 검사 결과, 추천 실행안과 미확인 사항, 명시적인 호출 승인 요청이다. 파일 이름만을 접근 가능한 원본 인계로 간주하지 않는다.

준비 완료 시 실제 상태는 '패키지 및 실행안 준비 완료, reviewer 호출 승인 대기'로 보고한다. 별도 reviewer가 실행되지 않았다면 독립 검토 결과·독립 감사 완료·새 모델 성능을 보고하지 않는다. 이번 Chat의 승인 기록을 준비 완료 증거로 삼지 않는다.

## Boundaries and Next CEO Decision

이번 승인에는 실제 reviewer 또는 대상 모델 호출, prompt calibration, 새로운 raw 실험·historical source verification 실행, held-out, 공식 Methodology/Terminology 변경, permanent architecture, Research Knowledge/memory admission, Work artifact push/merge/deploy/promotion이 없다. 기존 Gold의 새 의미 정정이나 추가 재채점을 이번 준비 작업에 조용히 포함하지 않는다. 패키지 결함은 범위 내에서 보완하되 후보 의미의 변경이 필요하면 해당 문제를 별도 보고한다.

이 준비 범위의 시작에 추가 CEO 승인은 필요하지 않다. 다음 CEO 결정은 제안된 reviewer 실행의 모델·호출/재시도·비용·데이터 범위를 승인할지이며 개별 claim의 정답 판정이 아니다. 43/43이나 모든 경로의 통과를 다음 단계 조건으로 새로 만들지 않는다.

## Actual Chat Actions and Authority Check

시작 시 main은 `beb8425ba297b810e0fd43c10a9d4c14c6124e87`이었다. 이 상태에서 Checkpoint 05, Working README와 INDEX, Evaluation Methodology의 평가 재사용 부분, Research Methodology의 admission/governance 경계를 다시 읽었다. 각 공식 문서 blob은 `a731f70218bfea57f5c33ddfe9b462bc1233bda0` 및 `5abcfc43bc6d775805aaf064a7f6dd05b8b1336a`로 직전 확인과 같다. 별도 대화 맥락 검색에서도 v0.2.1 reviewer 패키지 갱신 완료나 실제 호출 승인이 이미 있었다는 근거를 확인하지 못했으며, 이는 원 산출물의 부재를 단정한 것이 아니다.

이번 Chat이 실제 수행하는 변경은 이 후속 non-authoritative 기록 및 INDEX 참조 갱신이다. Work 패키지를 직접 생성·수정·전송하거나 reviewer를 호출하지 않았다. 직전 추천의 승인 대기 이력은 덮어쓰지 않고 이번 사용자 승인을 후속 기록으로 연결한다.
