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

**세션 끝 DoD (back-annotation 필수)**: 결정/항목 해소 시 **새 블록 append로 끝내지 말고, 원 'pending/대기' 블록에 해소 델타(→ RESOLVED/LANDED/SUPERSEDED @커밋)를 반드시 부기**한다. (미부기 시 stale pending이 인계로 무검증 전파 — 2026-07 D2 phantom. `health_check.py`의 "stale pending 백-어노테이션" 규칙이 WARN으로 감시.)

## F. 미래 확장 (사람 늘면)

PR(원격) + CI(GitHub Actions: pytest·경계테스트) + CODEOWNERS 3개만 추가.
현 1인 셋업이 그대로 디딤돌.

## G. 승격 트리거

차선 이탈이 실제 반복되면 → 그 종류 세션에만 per-worktree pre-commit 가드 국소 도입. 전면 금지.

## H. 배포 대행 (D-DEPLOY-DELEGATE)

**CC 대행 기본(사용자 승인 불필요)**: 자기 세션 브랜치의 **main 머지 · origin push · `sv sync` · worker/beat/daphne 재시작**. 아래 전 조건 충족 시에만.

1. **표준 배포 절차 전 단계 수행 + 각 단계 실측 결과를 리포트에 기재**:
   main worktree clean 확인 → MERGE_HEAD 부재 확인 → 로컬 main ff to origin/main → 세션 브랜치 no-ff 머지 → 충돌 마커 grep 0 → 대표 변경 코드 반영 grep → push(사전 `fetch`/`rev-list`) → 런타임 3트리 HEAD 정렬 확인 → 신규 라우트/코드 실존 확인 → 라이브 응답 확인(401=존재 등).
   (마이그레이션·env·번들 gotcha는 `sub_claude_md/common-bugs.md` "배포 체크리스트"(단일 출처) 준수 — 여기서 절차를 복제하지 않는다.)
2. **자기 세션 브랜치만.** 다른 세션의 미머지 브랜치·worktree는 조회 외 무접근. 머지 대상에 타 브랜치가 섞여야 하는 상황 = **HALT**.
3. 절차 중 어느 단계든 예상 외 결과(충돌, 발산, 미확인 staged 등) = **강행 금지, HALT·보고**.

**병진 수동 유지(승격 제외 — 변경 없음)**: prod DB migrate · 영구/강제 삭제 · 원격 브랜치 삭제 · LaunchAgent plist 변경 · **celery beat DB 엔트리의 등록·삭제·enabled 변경(#28 이력)**.

## I. H1 저위험 갭 자가 해소 (D-H1-SELFRESOLVE)

지시서 실행 중 실측이 지시서 전제와 불일치(스키마 갭 등)할 때, 아래 **3조건 전부** 충족 시 CC 자가 해소 허용:

1. **additive 변경만**으로 해소 가능(기존 필드·행위 보존)
2. 수정 파일이 **지시서 IN 범위 내**
3. **마이그레이션 무발생**

허용 시에도 보고서 "주요 결정 포인트"에 **갭 내용·해소 방식 필수 기재**. 3조건 중 하나라도 미충족 = 기존대로 **HALT**.
(선례: ⑳-1 `name` 필드 갭 자가 해소 — 사후 승인됨.)
