# Research Evidence Handoff Replay v0.1 Closure

상태: closed calibration working evidence. Approved/Effective 또는 methodology adoption이 아니다.

최종 결과는 hard-003 A/B/C와 hard-006 A/B의 semantic output 5건, hard-006/C execution failure 1건이다. 선택적 재실행은 하지 않는다. 원 batch `0b5220e04007446695d092f763b72020`과 원 failure를 역사적 결과로 유지한다.

실제 lineage 전체에서 provider 호출은 8회, prompt 35,709 tokens, completion 17,880 tokens, 기록된 latency 합계 약 124.208초다. 실제 비용은 확인되지 않았다. A/B 저장 응답 복구 과정에서 모델을 다시 호출하지 않았고 v0.1 historical file hash 검증은 `historical_files_unchanged=true`였다.

확인된 failure surface는 다음과 같다. Summary-only는 근거 부족에 유보할 수 있지만 본문과 structured change record가 충돌했다. Retrievable Evidence는 transport와 retrieval이 작동해도 material evidence를 요청하지 않았다. Full Context는 evidence 존재에도 hard-003 해석 오류를 유지했고 hard-006에서 protocol final artifact를 만들지 못했다. 따라서 Evidence availability, retrieval, recognition, use, conclusion constraint는 서로 다른 상태다.

hard-006/C는 provider `finish_reason=stop`, completion 8,192 tokens였지만 final JSON이 없었다. user-visible answer에는 반복적인 internal-review-like content가 있었다. 이는 semantic output으로 평가하지 않으며 execution/protocol failure로 남긴다. 원 raw response와 요청은 Mac local execution directory에 있고 이 closure 문서는 사용자가 제공한 ledger/result 출력에 근거한다.

GitHub 기준 candidate는 `52fe0279a25aa78da8e3b12a9c8c99a3d52ab94d`, branch는 `feature/research-replay-schema-recovery-v012`다. Mac 결과 경로는 `research_lab/work_reviews/2026-09-09-evidence-handoff-replay-v01/continuations_v012/0b5220e04007446695d092f763b72020`이다.

