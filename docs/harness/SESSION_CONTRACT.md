# 세션 계약 (Session Contract)

목적: 여러 Claude Code 세션이 동시에 돌아도 git 충돌·브랜치 섞임이 안 나게.
강제 수준: 소프트 — worktree(물리 격리) + 아래 규칙 선언. 훅 없음.
1차 소스 체인: CLAUDE.md "Session Lifecycle" → SESSION_STARTUP_CHECKLIST → 이 문서(§C 헤더).

## A. 불변 규칙 (안 바뀜)

1. 한 세션은 자기 소유 영역만 commit한다.
2. 작업은 자기 worktree(`monorepo/sess-*` 또는 지정 브랜치)에서만. 원본 리포 main 직접 commit 금지.
   → 명명 변경 사유 (2026-06-02): 기존 `sess/*`는 `.git/hooks/pre-commit` 화이트리스트(`monorepo/*`만 통과) 거부 → b 옵션(이름 우회)로 hook 무수정 해소. hook hardening(c)은 트리거 보류(TASKQUEUE CONTRACT-IMPROVE).
3. 공유 존(packages/shared, config/\*, packages/web)은 한 번에 한 세션만.
   건드리기 전 → STOP → 사용자에게 "공유 편집 필요" 보고 → 단독 확인 후.
4. 메타 레이어(PROGRESS·DECISIONS·TASKQUEUE·common-bugs·docs·scripts·
   tests/architecture·health_check)는 관리 세션 단독 소유.
   메인/외부API 세션은 메타 안 건드림 — 보고는 관리 세션이 받아 기록.
5. 세션 끝 = 자기 브랜치 push + main 머지 (미루면 merge hell).
6. 머지 전 = pytest(+경계 테스트·health) 통과 게이트 (CI 1인 대체).

## B. 소유권 매핑

| 세션 종류         | 소유(commit 가능)                                                                     | worktree · 브랜치                                        |
| ----------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 메인              | apps/{하나} (dashboard·market_pulse·chain_sight·portfolio)                            | ../stock*vis*{앱} · `monorepo/sess-{앱}`                |
| 관리              | PROGRESS·DECISIONS·TASKQUEUE·common-bugs·docs·scripts·tests/architecture·health_check | ../stock_vis_mgmt · `monorepo/sess-mgmt`                |
| 외부 API          | integrations/iron_trading                                                             | ../stock_vis_api · iron-trading-api (기존 브랜치 재사용) |
| 공유(단독 소유 X) | packages/shared · config/\* · packages/web                                            | 규칙으로 직렬화(한 번에 하나)                            |

## C. 세션 시작 헤더 (가변 — 시작 시 빈칸 채워 Claude Code에 붙임)

\`\`\`
[세션 계약 — 시작]
세션 종류: \_**\_ (메인 / 관리 / 외부API)
메인이면 소유 앱: \_\_** (apps/\_**\_)
worktree: ../stock_vis\_\_\_** · 브랜치: \_**\_
소유 영역: \_\_** (commit 허용 경로)
금지: 다른 apps/**, packages/shared/**, config/\*, packages/web/\*\*(공유), 메타(관리 외)
공유 편집 필요 시: STOP → 사용자 보고 → 확인 후
종료: pytest 게이트 → 브랜치 push → main 머지
\`\`\`

## D. worktree 셋업 (동적)

원본 리포 = main 전용 머지 지점. 작업은 전부 worktree에서.
\`\`\`bash
git worktree add ../stock_vis_mgmt -b monorepo/sess-mgmt # 관리(상시)
git worktree add ../stock_vis_market_pulse -b monorepo/sess-market_pulse # 메인 예시
git worktree add ../stock_vis_api iron-trading-api # 외부 API(기존 브랜치)
git worktree list
\`\`\`
세션 추가 = worktree add 한 줄. 메인 앱 변경 = 그 앱용 worktree 새로 add.

## E. 세션 끝 — 머지 흐름

\`\`\`bash

# 자기 worktree에서 게이트

pytest && python scripts/health_check.py
git add -A && git commit -m "..."
git push origin <브랜치>

# 원본 리포(main)에서 머지

git checkout main && git pull
git merge <브랜치>
pytest
git push origin main

# 정리(앱 세션 종료 시)

git worktree remove ../stock*vis*<앱>
\`\`\`
공유 파일 만진 세션이 둘이면 머지 순서대로, 두 번째가 충돌 해결(머지 1회).

## F. 미래 확장 (사람 늘면)

PR(원격) + CI(GitHub Actions: pytest·경계테스트) + CODEOWNERS 3개만 추가.
현 1인 셋업이 그대로 디딤돌.

## G. 승격 트리거

차선 이탈이 실제 반복되면 → 그 종류 세션에만 per-worktree pre-commit 가드 국소 도입. 전면 금지.
