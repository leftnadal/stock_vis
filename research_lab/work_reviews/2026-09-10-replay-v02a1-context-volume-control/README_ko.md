# Research Evidence Handoff Replay v0.2A.1

상태: CEO-approved limited context-volume control preparation. Working review evidence이며 Approved/Effective 또는 architecture adoption이 아니다.

S-short와 S-long-control 모두 동일 frozen summary와 동일 evidence 17개를 사용하고 historical candidate/critique를 포함하지 않는다. 공통 system prompt는 `context_volume_control`이 비근거 부피 제어 값이며 판단이나 인용에 사용되면 안 된다고 동일하게 명시한다.

S-long-control은 SHA-256에서 생성한 deterministic lowercase hexadecimal identifier만 포함한다. 자연어, case/evidence prose, expected conclusion 또는 source ID guidance를 넣지 않는다.

실행 전 exact requested model ID를 `local_files_only=True`, `trust_remote_code=False`로 불러온 fast tokenizer가 historical v0.2A provider count 4,903과 14,387을 모두 정확히 재현해야 한다. 이후 새 long input도 local count 14,387과 정확히 일치해야 한다. 하나라도 실패하면 model invocation 0회로 중단한다. Tokenizer나 dependency를 network에서 설치·다운로드하지 않는다.
