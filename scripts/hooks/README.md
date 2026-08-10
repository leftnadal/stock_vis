# scripts/hooks — 버전관리 git 훅

이 디렉터리의 훅은 **버전관리 대상**이라 클론·전 worktree에 따라온다(비버전관리 `.git/hooks`와 달리). 활성화는 `core.hooksPath` 설정 1회로 이뤄진다.

## 신규 클론 부트스트랩 (필수 1회)

```bash
git config core.hooksPath scripts/hooks
```

- 로컬 config(클론 시 미설정)라 **새 클론/새 기계마다 1회 실행**해야 훅이 발화한다.
- `core.hooksPath`는 전 worktree 공유 config이며, 상대경로는 각 worktree 루트 기준으로 해석된다.

## 훅 목록

### `pre-commit`

- **브랜치 화이트리스트**: `main`·`slice*`·`security/*`·`monorepo/*` 등 허용 브랜치만 커밋 통과(자동 브랜치 전환 오염 방지). 그 외 = 거부.
- **작업 경로 경고**: 표준 경로 밖이면 경고(비차단).
- **KB 큐 미드레인 경고**: `shared_kb` 큐 미드레인 시 stderr 경고(비차단).
- **채번 가드**: staged `sub_claude_md/common-bugs.md`에 신규 `#NN` 헤딩을 추가하는데 현재 브랜치가 `sess-mgmt` 계열이 아니면 **커밋 거부**. 채번은 mgmt 세션 전용이라는 규약의 집행.
  - 규약 근거·판정 절차는 `DECISIONS.md`의 **D-NUMBERING-MGMT-ONLY**(단일 출처) 참조.
