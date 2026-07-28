#!/usr/bin/env bash
# wt-open — 격리 worktree 생성 + 세션 마커 (OPS-WORKTREE-ISOLATION Phase 1 헬퍼, Opt-1 흡수).
# 사용: bash scripts/wt-open.sh <track> [purpose]
#   → ~/worktrees/sv-<track> 에 origin/main 기준 브랜치 monorepo/sess-<track> 생성 + 마커.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/session_marker.sh"

TRACK="${1:?사용: wt-open <track> [purpose]}"
PURPOSE="${2:-}"
REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
WT_DIR="$HOME/worktrees/sv-${TRACK}"
BRANCH="monorepo/sess-${TRACK}"

if is_runtime_tree "$WT_DIR"; then
    echo "✗ 거부: '$TRACK'는 런타임 트리 경로와 충돌 — 다른 track명을 쓰세요." >&2; exit 1
fi
[ -e "$WT_DIR" ] && { echo "✗ 이미 존재: $WT_DIR" >&2; exit 1; }

git -C "$REPO" fetch origin --quiet
git -C "$REPO" worktree add -b "$BRANCH" "$WT_DIR" origin/main
marker_write "$WT_DIR" "$TRACK" "$PURPOSE"
echo "✅ wt-open: $WT_DIR (branch $BRANCH, base origin/main $(git -C "$WT_DIR" rev-parse --short HEAD))"
echo "   작업 후 정리: bash $SCRIPT_DIR/wt-close.sh $WT_DIR"
