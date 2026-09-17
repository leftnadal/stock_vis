# docs/instructions/inbox — 디렉터 → 실행자 메일박스 (D-OPS-BRIDGE, 2026-09-16)

- `inbox/<트랙>.md` = 디렉터(Cowork)가 놓는 지시서. **파일이 곧 디스패치**다 — 채팅 복붙 없음.
- `outbox/<트랙>_보고.md` = 실행자(Claude Code)가 남기는 보고. 디렉터는 outbox ↔ git 실측을 대조해 판정한다.
- `approvals/<트랙>.ok` = 병진 승인 증표(`sha=` 필수). 랜딩·push·sync는 이 파일이 있을 때만(OPS-GATE-1 이후 훅이 강제).
- 실행자 첫 동작 = inbox 파일을 자기 브랜치에 **커밋**(0번 게이트 — 지시서 커밋 없이 실행 금지). 완료 시 inbox 파일 상단에 `status: done @<커밋>` 1줄 추기(삭제 금지 — 이력).
- 지시서는 짧다. 없는 것은 repo 하네스(CLAUDE.md → SESSION_CONTRACT → DEPLOY.md → common-bugs)가 단일 출처다 — 여기 복제하지 않는다.
