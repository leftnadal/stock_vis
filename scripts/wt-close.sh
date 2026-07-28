#!/usr/bin/env bash
# wt-close — 격리 worktree 정리 (dirty→wip 커밋 프롬프트 → 마커 제거 → worktree 제거).
# 사용: bash scripts/wt-close.sh <tree_path> [--force-wip]
#   3차 사고(미커밋 WIP가 통합 차단)의 직접 대책 — 이탈 전 wip를 전용 브랜치로 봉인.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/session_marker.sh"

TREE="${1:?사용: wt-close <tree_path> [--force-wip]}"
FORCE_WIP="${2:-}"
TREE="$(_abs "$TREE")"
[ -d "$TREE" ] || { echo "✗ 없음: $TREE" >&2; exit 1; }

BRANCH="$(git -C "$TREE" branch --show-current 2>/dev/null || echo '')"
DIRTY="$(git -C "$TREE" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

if [ "$DIRTY" != "0" ]; then
    echo "⚠ dirty $DIRTY개 — 이탈 전 wip 커밋 필요(3차 사고 대책)." >&2
    if [ "$FORCE_WIP" = "--force-wip" ]; then ans="y"; else
        printf "   전용 브랜치(%s)에 wip 커밋할까요? [y/N] " "${BRANCH:-<detached>}"; read -r ans || ans="n"
    fi
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
        [ -n "$BRANCH" ] || { echo "✗ detached HEAD — 먼저 브랜치 지정 후 재실행." >&2; exit 1; }
        git -C "$TREE" add -A
        git -C "$TREE" commit -q -m "wip($BRANCH): wt-close 이탈 봉인 [$(date '+%Y-%m-%d %H:%M')]"
        echo "   wip 커밋 완료 → 원격 백업 권장: git -C $TREE push origin $BRANCH"
    else
        echo "✗ 중단: dirty 미해소로 worktree 제거 안 함(데이터 보호)." >&2; exit 1
    fi
fi

marker_remove "$TREE"
git -C "$SCRIPT_DIR" worktree remove "$TREE" 2>/dev/null || git worktree remove --force "$TREE"
echo "✅ wt-close: $TREE 제거${BRANCH:+ (브랜치 $BRANCH 보존 — 필요시 push/삭제)}"
