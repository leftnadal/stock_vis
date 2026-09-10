# Mac 실행 및 저장

이 task는 준비 commit에서 정확히 한 번 실행한다. Launcher는 다음 안전 경계를 강제한다.

- 지정된 review branch와 clean worktree 확인
- tracked input/code checksum 확인
- 9개 regression test 실행
- 기존 `executions/`가 있으면 중복 호출 거부
- C-original과 C-sanitized를 각 1회만 호출
- 실제 token 및 Authorization header가 artifact에 남지 않았는지 검사
- task의 새 execution directory만 stage
- `[skip ci]` review commit 생성 후 같은 feature branch에 push

모델 응답이 protocol-incomplete여도 provider 호출 자체가 정상 반환됐다면 두 arm 실행을 마치고 그 상태를 보존한다. Network/provider exception은 추가 호출과 publish를 중단하며 생성된 로컬 evidence는 삭제하지 않는다.

Review branch 저장은 adoption, merge, main 반영 또는 deployment가 아니다. 실행 후 semantic assessment는 저장된 두 output을 독립적으로 검토해 별도 addendum으로 기록한다.
