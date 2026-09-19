# Working Record — Record Reconstruction Evaluation Target / Checkpoint 05

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** gold v0.2.1, 40 valid, attribution limit, frozen claim semantics, review readiness, independent reviewer, opaque package, source verification, 근거 충분성, 귀속 범위, 원 주장 보존, 별도 검토, 승인 경계  
**Prior Record:** [Checkpoint 04](2026-09-18_record-reconstruction-evaluation-target_04.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Record Basis:** 사용자가 제공한 Work 인계서와 Library의 `Gold_v021_Route_Sufficiency_Audit_Work_Chat_Handoff_ko.md` 원문, 최신 GitHub 공식 문서 대조, 아래 Chat 검토 제안. Gold JSON·raw evidence·frozen output을 직접 대조하거나 테스트/해시를 재실행한 기록은 아니다.

## Context and Reported State

Work는 Checkpoint 04의 범위에서 59개 부모 경로의 근거 충분성 자가 감사를 보완했다고 보고했다.

- 부모 경로: 충분 22, attribution 범위에서 충분 31, 충분하지만 불필요하게 복합적인 경로 2, 불충분 4. 합계 59.
- 원 Gold v0.2 보존. 별도 v0.2.1에서 부모 경로 4개 제외, 교정 경로 1개 추가, 복합 경로 2개 단순화. 활성 경로 56개.
- 동일 frozen output 3개/43개 claim 재채점: v0.1 35/43 → v0.2 41/2/0 → v0.2.1 40/3/0.
- 새 invalid: `a4d71e0b93c6425f-q1-c1`. Manifest-only 인용에 JSONDecodeError의 근거가 없다는 이유.
- 유지된 invalid: prior evaluation을 source_direct로 표기한 `2f9...-q2-c4`; 추론 표시·derivation이 없는 `a4d...-q4-c4`.
- Source checksum 16/16, tests 22/22, 모델/API 호출 0, 원본·prompt·출력 변경 및 Work push/merge/deploy/promotion 없음으로 보고됨.
- 검토자는 gold·점수·rationale를 본 동일 Work AI다. 독립 감사가 아니다.

이 숫자들의 산술적 정합성과 보고의 의미는 확인했지만 개별 판정, 실행 결과, 해시 일치를 Chat이 재검증한 것은 아니다. 59→56은 59-4+1과 일치한다. 두 단순화는 경로 교체로 설명되며 원본 매핑은 추가 산출물 확인이 필요하다.

## Sources and Verification Boundary

확인한 Library 인계서: `Gold_v021_Route_Sufficiency_Audit_Work_Chat_Handoff_ko.md`, file ID `file_000000006b7c821196ac9accb742563f`, version 1. 사용자의 인계와 주요 수치·결론·제약이 일치한다. 인계서가 인용한 raw/gold/audit JSON 및 reviewer archive는 이번 검색에서 확보하지 못했다. 문서 원문 열람은 그 안의 모든 검증 주장에 대한 독립 검증이 아니다.

보고된 해시(직접 계산하지 않음):
- Gold v0.2.1: `ed754d738abd57caf973d3c10a07ad569a142fb4f32018bbaebabf25013a938b`
- v0.2.1 rescore: `1c149717b64d202d75cce9e88dd1f335cbe1492311eddd6b73fa77ffd3437c9c`
- enhanced audit: `cd92c3ff696132d5143a93c486c2b1a14d8e6bec0367d68848e8a1e00593e0a5`

공식 확인 기준 main은 `b3a6da6baa3199e7aa0796e10a497910ddc96a82`다. 이전 확인 기준 `a11eebe282ce5b0c64b98f2d9bc58479572ebd81`와 비교하여 변경이 Checkpoint 04 및 INDEX에 한정됨을 확인했다. 이전에 확인한 Research Methodology/ORS/상위 문서/Working README는 그 이후 변경되지 않았다. 이번에 Evaluation Methodology §§6.2–7.5, §§13.2–15 및 최신 INDEX를 다시 읽었다. Evaluation Methodology blob은 `a731f70218bfea57f5c33ddfe9b462bc1233bda0`이다.

## Review Conclusion — Recommendation, Not New Approval

Gold v0.2.1을 다음 별도 검토의 development correction candidate로 삼는 것을 추천한다. 이는 정답표의 의미적 정확성이나 40/3/0을 확정하는 승인과 다르다.

더 많은 동일 작성자의 무한 자가 감사보다, 기존 결론과 분리된 검토자를 통한 대조를 다음 방향으로 추천한다. 다만 실제 reviewer 호출은 아직 승인되지 않았다. 기존 no-call 준비 범위에서 패키지를 갱신하고, 실제 호출은 reviewer/모델·입력 범위·호출/재시도 한도·비용·데이터 전달 경계를 정한 실행안에 대해 별도로 승인받는다.

## Main Unresolved Boundary — Attributed Support and Frozen Claim

31개의 `sufficient_with_attribution_limit` 경로가 곧 오답이라는 결론도, 모두 원 claim에 충분하다는 결론도 내리지 않는다.

다음은 구분해야 한다.

- 근거가 실제로 해당 평가/참여자의 보고를 담고 있는가.
- 그 보고를 현재 frozen claim의 의미·강도·시점·범위에 맞게 사용했는가.
- 원 사실을 이번에 독립 재현했는가.

첫 번째가 충족된다는 이유만으로 두 번째와 세 번째가 자동 충족되지 않는다. 그러나 세 번째가 수행되지 않았다는 이유만으로 모든 과거 평가 재사용을 금지하지도 않는다. 공식 Evaluation Methodology §14는 대상 상태·목적·조건·기준·중요한 근거가 충분히 호환될 때 과거 평가 재사용을 허용한다.

따라서 Work의 결정 질문 3은 'prior evaluation을 전면 허용할 것인가 / 모든 원자료 독립 검증을 요구할 것인가'의 양자택일로 처리하지 않는다. 기존 Option B를 유지한다. 각 경로가 실제로 지지하는 범위와 frozen claim의 요구 범위가 맞는지 확인한다.

특히 SHA claim은 '이전 평가가 checked 8, failed 0이라고 보고했다', '해당 artifact가 당시 검증을 통과했다', '이번에 직접 재검증했다'가 같은 주장이 아님을 보존해야 한다. 원 평가가 정당한 이차 근거로 재사용될 수 있는지는 범위·근거·의존성에 따라 판단하며, 존재하지 않는 raw log를 가정하거나 현재 checksum으로 사후 보완하지 않는다.

귀속 범위는 본문 한 문장만이 아니라 당시 질문, claim, 기존 응답 계약 및 그 claim에 연결된 basis/참조 metadata를 포함하여 해석한다. 모든 문장에 같은 귀속 문구의 반복을 강제하는 새 문체 규칙은 만들지 않는다. 반대로 감사자가 나중에 attribution-limited라는 label을 붙였다는 이유로 원래 무조건적 주장이나 직접 검증 주장을 조용히 약화해 통과시키지 않는다. 기존 출력의 의미가 불명확하면 억지로 valid/invalid를 확정하지 않고 그 불확실성을 보존한다.

31개 부모 경로의 감사 결과와 현재 56개 활성 경로, 실제 43개 출력 판정 사이의 연결은 reviewer package에서 추적 가능해야 한다. 새 전수 자가 감사가 아니라 다음 별도 검토에서 우선 확인할 질문으로 둔다.

## Interpretation of Specific Corrections

Manifest에 protocol 상태만 있고 JSONDecodeError가 없다면 manifest-only로 그 claim 전체를 지지할 수 없다는 Work의 정정 논리는 적절하다. 다른 유효 raw route가 존재해도 출력이 선택하지 않았다면 자동 구제하지 않는다. 실제 claim/source 비교는 별도 검토에서 확인한다.

자료 결손에 대한 '재구성 불가'는 제공된 기록으로 원래 final의 내용을 충실하게 복원할 수 있는지에 한정한다. 실패한 프로토콜에서 어떤 syntactically valid JSON도 만들 수 없다는 보편 명제로 바꾸지 않는다. 필요한 전제–결론 설명은 재현 가능한 짧은 derivation이며 비공개 사고과정 복원이 아니다.

감사표의 충분성, attribution 한계, 불필요한 복합성은 같은 종류의 단일 등급이 아니다. 현재 표는 감사 요약으로 유지할 수 있지만 공식 신뢰도 등급이나 완결적 taxonomy로 승격하지 않는다. Reviewer에게는 필요한 사실과 사용 범위를 보존하고 자동 점수 상속을 만들지 않는다.

## Reviewer Package Recommendation

1. 검토 기준 후보는 v0.2.1의 활성 56개 경로다. 부모 59개 경로와의 연결, 제외된 4개 및 단순화/대체된 경로는 별도 대조 자료로 보존한다. 유지 경로만 보여주어 무조건 수용하는 reviewer도 성공처럼 보이지 않게, 제거·수정 판단도 대조 대상에 포함한다.
2. 기존 20/20/19는 59개 부모 경로의 분할이다. 숫자를 억지로 유지하거나 활성 경로 수와 감사 대상 수를 혼동하지 않는다. 실제 묶음 크기는 필요한 문맥과 입력 한도에 맞추고 각 단위·전체 분모·parent mapping을 명시한다. 묶음 수를 독립 reviewer 수나 독립 실험 수로 세지 않는다.
3. 별도 검토자의 첫 판정에서는 기존 35/43·41/2/0·40/3/0, gold 정답/등급, 수정 이유 및 작성자의 정당화 등을 분리한다. 원 claim, 당시 질문/출력 계약, 후보 근거의 원문·정확한 위치·대상 상태, 필요한 참조 관계와 결손 정보는 제공한다. prior assessment가 평가 대상 근거이면 본문을 숨기지 않는다. Opaque ID만으로 결과 비노출을 보장한다고 말하지 않는다.
4. 검토자 첫 판정을 보존한 후 gold와 대조한다. 불일치는 단순 투표나 새 reviewer 권위로 덮지 않고 원문/계약의 어느 부분에서 갈렸는지 해소한다. 독립성은 gold 작성 참여 여부와 실제 노출 범위를 명시하고 제한적으로 설명한다.
5. 독립 reviewer의 의미 검토, historical underlying fact의 독립 재실행, held-out generalization 평가는 다르다. 앞의 검토가 완료되어도 뒤의 두 가지가 완료된 것은 아니다.

## CEO Decision Scope and Limits

추천할 선택은 다음 세 가지다.

- v0.2.1을 개발 검토 대상 후보로 사용하되 정답표/성능 확정으로 승격하지 않는다.
- 기존 Option B와 과거 평가의 조건부 재사용을 유지하며, 귀속된 보고 범위와 frozen claim 범위의 일치를 reviewer의 핵심 질문으로 삼는다. 모든 underlying fact의 원자료 독립 재검증을 새 목표로 추가하지 않는다.
- Reviewer package 갱신과 실행 계획 준비를 다음 작업으로 삼고, 실제 reviewer/model 호출은 구체적인 실행·비용·입력 경계가 확인된 뒤 별도 승인한다.

사용자의 이번 발언은 인계서 확인 요청이다. 새로운 reviewer 실행, 프롬프트 수정, 재채점 추가 수행이 이미 승인됐다고 기록하지 않는다. 개별 claim의 정답을 CEO에게 결정하도록 넘기지 않는다.

## External Comparison

ALCE는 답변 correctness와 cited support를 별개로 평가하며, citation 평가에서도 claim 전체에 대한 지지 여부를 묻는다. 구분의 참고일 뿐 Stock_vis의 role taxonomy나 attribution 기준을 대신하지 않는다. 원문 HTML §§3.2–3.3 및 Appendix F를 확인했다: https://arxiv.org/html/2305.14627v2

## Actual Change Scope

이번 Chat의 GitHub 변경은 이 비공식 후속 기록과 INDEX 갱신뿐이다. 원 Working checkpoint, 공식 research_lab 문서, Work의 gold·validator·frozen output·reviewer package는 변경하지 않는다. 별도 reviewer/API 호출, 대상 모델 호출, held-out, memory/Knowledge admission, permanent architecture, Work artifact promotion은 수행하지 않는다. 이후 별도 reviewer 검토가 없더라도 현재 self-audit 이력은 보존하고, 43/43을 다음 단계의 필수 조건으로 만들지 않는다.
