# Research Evidence Handoff Replay v0.2A

상태: approved limited calibration candidate. Summary-target full-context contamination isolation이다.

두 arm은 동일 frozen summary를 evaluation target으로 사용한다. 두 arm 모두 hard-006 evidence document 17개를 같은 순서와 내용으로 제공한다. Original arm은 historical primary/critic output 두 문서를 함께 제공하고, sanitized arm은 그 두 문서를 제거한다. Evidence를 선택·삭제·강조하거나 expected evidence ID를 알려주지 않는다.

이 lineage는 v0.1 hard-006/C의 선택적 재실행이 아니다. v0.1 failure는 historical comparator로 유지한다. 두 새 arm은 같은 model, prompt, generation config, output budget, timeout과 retry policy를 사용한다.

결과는 protocol completion, token/latency, reasoning-like visible content, introduced error, unsupported strengthening, material condition preservation, conclusion scope calibration로 검토한다. 단일 점수나 permanent architecture 결론을 만들지 않는다.

실행 전 `SHA256SUMS`와 테스트를 검증한다. 실행 결과는 `executions/<batch>/`에 append-only로 생성한다. 같은 checkout에서 기존 executions가 있으면 launcher가 중복 실행을 거부한다.
