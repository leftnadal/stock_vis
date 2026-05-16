# pre-commit hook 정책

## 정책

- 브랜치 화이트리스트: `main` / `portfolio` / `slice<N>`
- 작업 경로: `/Users/byeongjinjeong/Desktop/stock_vis` (경고만, 강제 차단 아님)
- 부채 ID: #39

## 화이트리스트 갱신 시점

새 슬라이스 진입 시 `.git/hooks/pre-commit`의 `ALLOWED_BRANCHES` 배열에 추가:

```bash
ALLOWED_BRANCHES=("main" "portfolio" "slice8" "slice9" "slice10" ...)
```

## hook 비활성화 (긴급 시만)

```bash
git commit --no-verify -m "..."
```

- 사용 시 commit message에 사유 명시
- Slice 종결 보고서에 비활성화 회수 기록

## 사고 학습 케이스

- 2026-05-16: Slice 8 Part 1에서 `fix/*-20260516`, `test/*-20260516` 자동 전환 발생 (도구 미상, #40 추적 중)
- Part 1 진행 중 Step 1, Step 2, Q-1 commit 시 매번 다른 일자 패치 브랜치로 전환됨
- 대응 패턴: `git checkout slice8 && git cherry-pick <commit>`

## 주의 사항

- `.git/hooks/`는 git tracked가 아니므로, 다른 환경(iCloud 등)에서는 hook 부재 가능
- → Desktop 단독 작업 정책으로 보완 (Q-1 WORKSPACE_ROOT.md 표지)
- 향후 `husky` 같은 도구로 tracked hook 도입 검토 가능 (Slice 9 후보)

## 테스트 결과 (Q-2 검증)

- 정상 케이스: `slice8` 브랜치에서 commit → 통과 (Q-3 이후 commit 시 자연 검증)
- 차단 케이스: 비화이트리스트 브랜치에서 commit 시도 → `exit 1` 반환 (수동 검증)
