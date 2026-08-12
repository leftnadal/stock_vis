#!/usr/bin/env bash
# =============================================================================
# cleanup_worktrees_20260812.sh
# 생성일   : 2026-08-12
# 생성세션 : MGMT-MICRO (monorepo/sess-mgmt-cleanup-script)
# 대상건수 : 45 (origin/main 완전 소진 + worktree 딸린 로컬 브랜치)
# 좌표     : STEP 0 재실측(2026-08-12, origin/main=2aba9dac→6bf3acfd) 기준
#            리프레시 2026-08-12: sess-mgmt-b28 신규 소진 +1 반영(44→45)
#
# 제외 1건(소진이나 라이브 인프라 보호): monorepo/nightly-20260811 @
#   /Users/byeongjinjeong/stock-vis-nightly/repo — nightly cron 자동화의
#   작업 디렉토리(라이브 자동화 트리, cf. common-bugs #67). worktree 제거 시
#   야간 자동화가 깨질 수 있어 배열에서 제외. 삭제 필요 시 nightly cron
#   재지정 확인 후 병진이 개별 판단.
#
# ⚠ 병진 수동 실행 전용 — CC(에이전트)는 이 스크립트를 실행하지 않는다.
#   근거 = DECISIONS.md D-BRANCH-DELETE-MANUAL (2026-08-10, [governance]):
#   "브랜치 삭제(-d/-D)·worktree 제거·원격 브랜치 삭제는 위임 불가 —
#    병진 수동 집행 고정. 세션 내 예외 승인으로도 CC 집행 불가."
#   → 이 파일은 '삭제 후보 + 안전 재검증'을 코드화한 산출물이며,
#     집행 주체는 사람(병진)이다.
#
# 안전선(사양):
#   - 기본 = dry-run(계획만 출력). 실제 집행은 --apply 인자 필요.
#   - 건별 origin/main 소진 재검증(merge-base --is-ancestor) 후에만 집행.
#   - worktree remove는 --force 없음(dirty면 git이 자체 거부 → skip).
#   - branch -d만 사용(-D 금지). "not fully merged" 거부 시 그 건 skip.
#   - 제외: main 체크아웃 트리 · 런타임 트리(sv-worker/api/web-runtime,
#     가동 celery/daphne cwd) · 현 세션 트리 · sess-signal-fwd-recon.
#     (제외분은 애초에 아래 배열에 없음)
#   - 미포함: 원격 삭제 · -D · --force · 미머지 브랜치 · git gc.
# =============================================================================
set -u  # set -e 금지: 개별 실패가 전체를 중단시키지 않도록

# 대상 = "branch|worktree_path" (STEP 0 재실측 주입, 2026-08-12)
TARGETS=(
  "monorepo/sess-20g-honest-cards|/Users/byeongjinjeong/Desktop/stock_vis/.claude/worktrees/monorepo+sess-news-av-broad"
  "monorepo/sess-cs-m2|/Users/byeongjinjeong/Desktop/stock_vis_cs_m2"
  "monorepo/sess-cs-rd3|/Users/byeongjinjeong/Desktop/stock_vis_cs_rd3"
  "monorepo/sess-graph-cleanup|/Users/byeongjinjeong/Desktop/stock_vis_graph_cleanup"
  "monorepo/sess-hcheck-redesign|/Users/byeongjinjeong/Desktop/stock_vis_hcheck"
  "monorepo/sess-sfi-i2-close|/Users/byeongjinjeong/Desktop/stock_vis_mgmt_v2"
  # (제외) monorepo/nightly-20260811 = 라이브 nightly 자동화 트리 — 헤더 주석 참조
  "monorepo/sess-boundary-llm-mgmt|/Users/byeongjinjeong/worktrees/sv-boundary-llm"
  "monorepo/sess-CN-repair|/Users/byeongjinjeong/worktrees/sv-cn-repair"
  "monorepo/sess-docs-hooks|/Users/byeongjinjeong/worktrees/sv-docs-hooks"
  "monorepo/sess-dotsym|/Users/byeongjinjeong/worktrees/sv-dotsym"
  "monorepo/sess-eod-fresh-fix1-addendum|/Users/byeongjinjeong/worktrees/sv-eod-addendum"
  "monorepo/sess-eod-fresh-fix1|/Users/byeongjinjeong/worktrees/sv-eod-fix1"
  "monorepo/sess-eod-fresh|/Users/byeongjinjeong/worktrees/sv-eod-fresh"
  "monorepo/sess-hold-p1-integrate|/Users/byeongjinjeong/worktrees/sv-hold-p1-integrate"
  "monorepo/sess-measure-c2s2|/Users/byeongjinjeong/worktrees/sv-measure-c2s2"
  "monorepo/sess-mgmt-b22|/Users/byeongjinjeong/worktrees/sv-mgmt-b22"
  "monorepo/sess-mgmt-b23|/Users/byeongjinjeong/worktrees/sv-mgmt-b23"
  "monorepo/sess-mgmt-b24|/Users/byeongjinjeong/worktrees/sv-mgmt-b24"
  "monorepo/sess-mgmt-b25|/Users/byeongjinjeong/worktrees/sv-mgmt-b25"
  "monorepo/sess-mgmt-b26|/Users/byeongjinjeong/worktrees/sv-mgmt-b26"
  "monorepo/sess-mgmt-b27|/Users/byeongjinjeong/worktrees/sv-mgmt-b27"
  "monorepo/sess-mgmt-b28|/Users/byeongjinjeong/worktrees/sv-mgmt-b28"
  "monorepo/sess-mgmt-batch-a|/Users/byeongjinjeong/worktrees/sv-mgmt-batch-a"
  "monorepo/sess-mgmt-ledger3|/Users/byeongjinjeong/worktrees/sv-mgmt-ledger3"
  "monorepo/sess-mgmt-taskq|/Users/byeongjinjeong/worktrees/sv-mgmt-taskq"
  "monorepo/sess-mon-reset|/Users/byeongjinjeong/worktrees/sv-mon-reset"
  "monorepo/sess-p1a-relanding|/Users/byeongjinjeong/worktrees/sv-p1a-relanding"
  "monorepo/sess-regen-v2-mgmt|/Users/byeongjinjeong/worktrees/sv-regen-v2"
  "monorepo/sess-review-p2|/Users/byeongjinjeong/worktrees/sv-review-p2"
  "monorepo/sess-s1b1|/Users/byeongjinjeong/worktrees/sv-s1b1"
  "monorepo/sess-s1b2|/Users/byeongjinjeong/worktrees/sv-s1b2"
  "monorepo/sess-s1b2-shared|/Users/byeongjinjeong/worktrees/sv-s1b2-shared"
  "monorepo/sess-s3-mindmap|/Users/byeongjinjeong/worktrees/sv-s3-mindmap"
  "monorepo/sess-secb-v2-recon|/Users/byeongjinjeong/worktrees/sv-secb-v2-recon"
  "monorepo/sess-sfi-i1|/Users/byeongjinjeong/worktrees/sv-sfi-i1"
  "monorepo/sess-sfi-i1b|/Users/byeongjinjeong/worktrees/sv-sfi-i1b"
  "monorepo/sess-sfi-i2|/Users/byeongjinjeong/worktrees/sv-sfi-i2"
  "monorepo/sess-sfi-i3|/Users/byeongjinjeong/worktrees/sv-sfi-i3"
  "monorepo/sess-spot-conv|/Users/byeongjinjeong/worktrees/sv-spot-conv"
  "monorepo/sess-sunmon-recon|/Users/byeongjinjeong/worktrees/sv-sunmon-recon"
  "monorepo/sess-th-s1|/Users/byeongjinjeong/worktrees/sv-th-s1"
  "monorepo/sess-cs-theme-heat|/Users/byeongjinjeong/worktrees/sv-theme-heat"
  "monorepo/sess-treatb-hooks|/Users/byeongjinjeong/worktrees/sv-treatb-hooks"
  "monorepo/sess-truth-v2|/Users/byeongjinjeong/worktrees/sv-truth-v2"
  "monorepo/sess-v1-residual-cleanup|/Users/byeongjinjeong/worktrees/sv-v1-cleanup"
)

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

if [ "$APPLY" -eq 1 ]; then
  echo "=== MODE: --apply (실제 집행) ==="
else
  echo "=== MODE: dry-run (계획만; 집행하려면 --apply) ==="
fi

# 재검증 기준 최신화
echo "-- git fetch origin (재검증 기준 최신화) --"
git fetch origin 2>&1 | tail -1
OM_REF="origin/main"

removed=0
skip_absent=0
skip_notmerged=0
skip_wt=0
skip_branch=0

for entry in "${TARGETS[@]}"; do
  br="${entry%%|*}"
  path="${entry#*|}"

  # a. tip 조회 (브랜치 부재 시 skip)
  tip=$(git rev-parse --verify --quiet "${br}^{commit}" 2>/dev/null)
  if [ -z "$tip" ]; then
    echo "SKIP(브랜치부재): $br"
    skip_absent=$((skip_absent + 1))
    continue
  fi

  # b. origin/main 소진 재검증
  if ! git merge-base --is-ancestor "$tip" "$OM_REF" 2>/dev/null; then
    echo "SKIP(미소진): $br (tip=$tip 이 $OM_REF 조상 아님)"
    skip_notmerged=$((skip_notmerged + 1))
    continue
  fi

  if [ "$APPLY" -eq 0 ]; then
    echo "PLAN: worktree remove '$path' + branch -d '$br'  (tip=${tip:0:8} 소진확인)"
    removed=$((removed + 1))
    continue
  fi

  # c. worktree 제거 (--force 없음: dirty면 거부)
  if [ -n "$path" ] && [ -e "$path" ]; then
    if git worktree remove "$path" 2>/tmp/wt_err; then
      echo "WT-REMOVED: $path"
    else
      echo "SKIP(worktree제거실패): $path — $(cat /tmp/wt_err)"
      skip_wt=$((skip_wt + 1))
      continue
    fi
  fi

  # d. 로컬 브랜치 삭제 (-d만; 거부 시 skip, -D 금지)
  if git branch -d "$br" 2>/tmp/br_err; then
    echo "BRANCH-DELETED: $br"
    removed=$((removed + 1))
  else
    echo "SKIP(branch -d 거부): $br — $(cat /tmp/br_err) [HALT 관례: -D 자가전환 금지]"
    skip_branch=$((skip_branch + 1))
  fi
done

echo ""
echo "================ 요약 ================"
if [ "$APPLY" -eq 1 ]; then
  echo "삭제 완료(worktree+branch): $removed"
else
  echo "삭제 계획(dry-run 대상): $removed"
fi
echo "스킵 — 브랜치부재      : $skip_absent"
echo "스킵 — 미소진(재검증탈락): $skip_notmerged"
echo "스킵 — worktree제거실패 : $skip_wt"
echo "스킵 — branch -d 거부   : $skip_branch"
echo "잔여 worktree 수        : $(git worktree list | wc -l | tr -d ' ')"
echo "====================================="
