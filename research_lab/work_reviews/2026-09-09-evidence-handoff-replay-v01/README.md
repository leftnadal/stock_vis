# Research Evidence Handoff Replay v0.1 — Work → Chat Handoff

## Executive Summary

CEO가 승인한 hard-003 × A/B/C, hard-006 × A/B/C의 여섯 입력과 전용 실행 도구를 준비했다. 기존 review commit을 읽고 동일한 case·candidate identity·수동 작성 short summary·평가 프롬프트·generation config를 동결했다. 실제 모델 호출 직전 환경 점검에서 기존 DeepInfra 인증 정보가 없어 중단했다. 현재 상태는 **blocked_before_model_invocation**이며 실제 비교 결과는 0/6이다. mock 테스트 4개 통과는 harness 검증이며 epistemic quality의 증거가 아니다. 입력과 중단 기록을 별도 브랜치에 보존하며 기존 인증 환경에서 승인된 범위의 실행을 이어갈 수 있다.

## Experiment Setup / A/B/C Conditions

- 기준: `b42eab30331726c4f1db4bd68fcb0a5f0ff2798b`, `research_lab/work_reviews/2026-09-09-critic-evidence/`.
- A: frozen summary만 전달. source 목록·원문 없음.
- B: A와 byte-identical summary + 모든 관련 근거와 candidate output의 opaque source ID·title·fragment reference·version/hash 목록. 모델이 JSON retrieve 요청을 하면 허용된 문서만 반환한다. 근거 본문은 요청 이전에 전달하지 않는다.
- C: 같은 summary + 전체 evidence + 선택된 기존 primary/critique 출력.
- 모든 arm의 평가 목적과 시스템 프롬프트는 같다. API에는 case title, hard-* ID, A/B/C label, 보호된 expectation을 전송하지 않는다. UUID run ID는 관리용이며 모델 입력에 포함하지 않는다.
- `visible/`: 실제 최초 model-visible messages. 후속 B 요청은 실행 시 request-N.json으로 기록한다.
- `frozen/`: 원 case, summary, documents, identity. 이 파일 전체를 모델에게 전달하지 않는다.
- `protected_expectations.json`: 사후 평가용. harness의 API request 생성 경로가 읽지 않는다. 파일 분리는 이 한정 replay의 입력 통제이며 Lab 공통 권한 시스템이 아니다.

## Frozen Variables

기존 provider의 `Qwen/Qwen3.5-122B-A10B`를 하나의 고정된 requested identity로 사용하도록 준비했다. 이는 모델 추천이나 현재 사용 가능성 확인이 아니다. 모든 arm에서 temperature=0.6, top_p=0.95, seed=20260909, reasoning.enabled=true, 총 completion token allowance=8192/run, timeout=420초/call, 최대 3 calls/run, retries=0을 사용한다. B의 조회 후속 호출은 같은 총 output allowance에서 사용량을 차감한다. B가 조회할 경우 호출 수와 input token 양이 늘어나는 것은 access condition의 매개 효과이며 실제 값을 보고해야 한다. 총 최대 18 calls이고 신규 광범위 sweep은 없다. 별도 모델로 자동 전환하지 않는다.

요약은 이전 audit을 본 Work가 새 replay용으로 한 번 작성했다. 원 모델이 당시 생성한 summary가 아니며, 작성자의 사전 노출·사례 선택 편향을 명시한다. 두 case는 development/calibration 전용이다. 모델 backend revision과 seed/reasoning 설정의 실제 준수는 미검증이며 returned model identity도 실행 전에는 알 수 없다. alias가 맞아도 정확한 weights/serving revision의 동일성을 입증하지 못한다.

## hard-003 Results / hard-006 Results

| Case | A | B | C |
|---|---|---|---|
| hard-003 | not_run | not_run | not_run |
| hard-006 | not_run | not_run | not_run |

hard-003의 분모 수정, 산술 정확성, 상한 해석, 결론 강화는 모두 **unassessed**다. hard-006의 자료 가용→실제 조회→조건 인식→최종 결론 제약도 모델 출력이 없으므로 **unassessed**다. available 문서 세트만 준비돼 있다.

## Repair / Preserve / Introduce Profile

12개 승인된 profile 항목을 `replay.py`의 PROFILE에 유지하며 각 실제 run 결과의 초기 상태는 unassessed다. 모델이 final JSON을 반환해도 `completed_pending_semantic_review`일 뿐 semantic pass가 아니다. output hash를 평가 target identity로 연결한다. repaired/preserved/introduced 항목은 최종 출력·원문을 대조한 사후 평가에서 warrant와 함께 채워야 한다. 모델의 used_source_ids 자기보고만으로 올바른 근거 사용을 판정하지 않는다. scalar score 없음.

## Evidence Retrieval Behavior / Condition Preservation

B는 available/requested/successfully retrieved IDs, 실패 이유, 조회 순서, latency, 반환 fragment와 hash/version을 보존한다. material source not requested와 retrieved but unused material source는 보호된 기준과 실제 출력을 대조할 때 채울 항목이다. 현재는 조회가 한 번도 없으므로 누락·미사용으로 집계하지 않고 unassessed다. 원문 내용이 답변에 등장한 것과 최종 결론을 제한한 것은 별도로 평가한다. 잘못된 ID는 source_not_available로 기록하고 다른 문서를 대신 반환하지 않는다.

## Unsupported Strengthening / Abstention / Unassessed

실제 결과 없음. not_run을 적절한 abstention으로 계산하지 않는다. 현재 요약에 남긴 기존 오류는 실험 대상 내용이며 새 모델의 오류가 아니다. 기존 5개/6개 근거 제한 등 원문 속 과거 지시는 현재 replay의 지시로 다시 실행하지 않도록 공통 prompt에 명시했다.

## Execution / Truncation Failures

`preflight/`에 실제 환경 점검을 기록했다: credential_present=false, planned_runs=6, model_invocations=0, network_reachability=unverified. 연결 요청을 시도한 것이 아니므로 provider outage나 인증 거부로 해석하지 않는다. Work 환경에는 codex executable도 없다. 관련 환경변수의 존재 여부만 확인했으며 credential 값을 출력하거나 원 로그에서 추출하지 않았다.

실제 실행 도구는 첫 오류·잘림·모델 identity mismatch·protocol 실패·usage 부재·호출 한도 초과에서 결과를 보존하고 batch를 중단한다. 자동 재시도 없음. 서버 timeout 이후에는 처리·청구 여부를 별도 확인해야 한다. provider exception의 전문은 저장하지 않고 예외 종류만 기록한다.

## Cost / Latency Observations

실제 유료 호출 없음. model latency와 actual cost는 미측정이다. mock 테스트 latency를 모델 성능으로 사용하지 않는다. 기존 provider_adapter의 과거 요율표는 이 replay의 현재 가격 근거로 사용하지 않는다. 구체적인 현재 비용 견적과 provider의 결제 한도는 실제 실행 환경에서 확인해야 하며, 비용이 material하면 승인된 stop condition에 따라 인계한다.

## Unexpected Findings

별도 업로드 `shared-primary(2).json`에서 label=hard-006/shared-primary인 원 출력이 추가로 발견됐다. `supplemental_inputs/`에 원 byte 그대로 보존하고 새 replay에 명시적으로 연결했다. 기존 감사 snapshot은 변경하지 않았다. 원 run의 parent hash로 연결됐다는 증거는 여전히 미확인이다. 따라서 historical causal pair를 증명했다고 하지 않는다. C는 이 자료와 기존 critique를 제공하는 명시적 replay 구성이다.

초기 준비본에는 이 primary가 없었다. 이를 실행하지 않고 `preparation_history/initial/`에 보존한 뒤 현재 plan을 다시 동결했다. 초기 준비본은 run 결과가 아니며 실행 대상도 아니다.

## Integrity / Leakage Checks

실행한 테스트 4개:

1. 정확히 두 case×A/B/C, 동일 case별 summary hash·candidate refs.
2. 최초 prompt 동일성, input hash, A 원문 차단/B 목록만/C 원문, 관리 case ID 및 expectation 파일명 미포함.
3. 허용되지 않은 source ID 요청에서 내용 반환 차단.
4. mock B 조회→final 왕복·실패 telemetry·공유 output allowance 차감·semantic profile unassessed 유지.

통과 결과는 tests.txt에 보존한다. 이 검사는 모든 형태의 의미적 leakage를 증명하는 완전한 검사가 아니다. 역사적 candidate 문장 자체의 편향, 학습 데이터 노출, provider 내부 동작은 통제하지 못한다. 모델 호출이 없는 현재 실제 retrieval 또는 semantic 결과를 꾸며 기록하지 않았다.

## Artifacts / Reproduction

`plan.json`, `frozen/`, `visible/`, `replay.py`, `provider_adapter.py`, `test_replay.py`, `protected_expectations.json`, `preflight/`, `supplemental_inputs/`, `tests.txt`, `SHA256SUMS`.

현재 디렉터리에서:

```bash
python3 -m unittest -v test_replay
python3 replay.py
```

이미 사용하던 provider의 인증이 안전하게 설정된 실행 환경에서 승인된 실험을 이어갈 때만:

```bash
python3 replay.py --execute
```

인증은 DEEPINFRA_TOKEN 또는 DEEP_INFRA_API_KEY 환경변수를 사용한다. 값을 Chat·GitHub·명령행 인자로 보내지 않는다. 위 명령은 Mac 로컬 모델 benchmark가 아니라 hosted API replay다. 원 Lab Automation worktree·runner의 변경이 필요 없다. `build.py`는 이 Work의 준비 출처용이며 기존 동결 plan을 재생성하지 않는다. 여섯 run을 다시 시작하면 새로운 execution directory를 만들므로, 일부 결과가 이미 있으면 무작정 재실행하지 말고 원 실행 상태부터 검토한다.

## What This Supports / Does Not Support

지원: 동결 입력과 B 프로토콜의 제한적 offline 검증, 기존 자료 보존, 실행 차단 원인 확인.
지원하지 않음: A/B/C 우열, net epistemic value 개선, generalization, held-out 검증, model/agent topology, Mac 성능, memory admission.

## Work Recommendation

기존 provider 인증을 사용할 수 있는 실행 환경으로 이 동일 snapshot을 넘겨 승인된 여섯 run을 수행하고, 실제 결과가 나온 뒤 profile을 근거별로 평가한다. 새 provider 구매나 프론티어 모델 교체로 우회하지 않는다.

추천 강도: Strong (동일 승인 범위를 재현하기 위한 운영 권고); A/B/C 우열 추천은 없음.
추천이 부적절한 조건: 기존 모델이 더 이상 제공되지 않음, 원 provider 접근이 불가능함, 비용이 material함, 새 공통 orchestration이 필요함. 이 경우 사용자 stop condition F/H/I 등에 따라 Chat으로 인계한다.

## Decision Needed From Chat

실험 방향의 재승인은 필요 없다. 필요한 것은 기존 provider 인증과 접근을 제공할 실행 환경의 연결 또는 로컬 Work 인계다. 새 provider·모델 구매·공통 구조 변경이 필요할 때만 추가 결정을 요청한다. 보호된 expectation을 모델 입력에 포함하거나 mock 결과를 실제 결과로 취급해서는 안 된다.

## Current Safety State

- actual_model_runs: 0 / 6
- current_state: blocked_before_model_invocation
- evidence_saved_to_separate_github_branch: true (저장 완료 후 commit 참조로 확인)
- main_modified / merge / deploy / production_db_execution: false
- original_review_or_math_candidate_modified: false
- memory_admission / methodology_adoption / topology_adoption: false
- additional_design_approval_needed: false for the already approved replay
- blocker: existing provider credentials unavailable in current Work runtime
