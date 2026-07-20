#!/usr/bin/env bash
# session_marker.sh — OPS-WORKTREE-ISOLATION Phase 1 라이브러리 (source 전용).
#
# 세션 마커(.session-marker)로 "이 트리를 세션이 점유 중"을 자동화에 알린다.
# 자동화(리셋·rehome)는 marker_respect()로 판정:
#   - 신선 마커(created_at < TTL) → skip(트리 보존)
#   - stale 마커(>= TTL)          → heal(경고 + 마커 제거 + 리셋 진행) — 고아 마커 영구봉쇄 방지
#   - 마커 부재                    → proceed(현행 동작)
#
# 워커/웹/api 런타임 트리는 마커 대상이 아니다(R1 자동화 단독 소유) —
# marker_write()가 런타임 트리 경로 거부. 설계: docs/harness/design_ops_worktree_isolation_v1.md
#
# 사용: source "$(dirname "$0")/lib/session_marker.sh"

set -o pipefail

MARKER_NAME=".session-marker"
MARKER_TTL_HOURS="${MARKER_TTL_HOURS:-24}"   # 고아 마커 자기치유 임계(시간)

# R1: 런타임 트리(자동화 단독 소유) — 마커 금지 대상.
_RUNTIME_TREES=(
    "/Users/byeongjinjeong/worktrees/sv-worker-runtime"
    "/Users/byeongjinjeong/worktrees/sv-web-runtime"
    "/Users/byeongjinjeong/worktrees/sv-api-runtime"
)

marker_path() { printf '%s/%s' "${1%/}" "$MARKER_NAME"; }

# 절대경로 정규화(심링크/상대 무관 비교용)
_abs() { cd "$1" 2>/dev/null && pwd -P || printf '%s' "$1"; }

is_runtime_tree() {
    local target; target="$(_abs "$1")"
    local t
    for t in "${_RUNTIME_TREES[@]}"; do
        [ "$target" = "$(_abs "$t")" ] && return 0
    done
    return 1
}

# 마커 존재 + 신선 여부. 0=신선, 1=stale, 2=부재
marker_state() {
    local mp; mp="$(marker_path "$1")"
    [ -f "$mp" ] || return 2
    local created epoch now age_h
    created="$(grep -oE '"created_at"[[:space:]]*:[[:space:]]*"[^"]*"' "$mp" 2>/dev/null | sed -E 's/.*"([^"]*)"$/\1/')"
    [ -n "$created" ] || return 1   # created_at 없으면 stale 취급(불량 마커)
    # created_at = epoch 초(헬퍼가 date +%s로 기록 — TZ 무관 안정)
    epoch="$created"
    case "$epoch" in (''|*[!0-9]*) return 1;; esac
    now="$(date +%s)"
    age_h=$(( (now - epoch) / 3600 ))
    [ "$age_h" -lt "$MARKER_TTL_HOURS" ] && return 0 || return 1
}

# 자동화 리셋 판정. echo: skip|heal|proceed / 로그는 stderr
# 사용: verdict="$(marker_respect "$tree" "$caller")"; case $verdict in skip) ...;; esac
marker_respect() {
    local tree="$1" caller="${2:-automation}"
    if is_runtime_tree "$tree"; then
        # 런타임 트리에 마커가 있으면 이상(세션이 있어선 안 될 곳) — 경고만, 리셋 진행
        [ -f "$(marker_path "$tree")" ] && \
            echo "[marker] ⚠ anomaly: 런타임 트리에 세션 마커 존재($tree) — R1 위반, 리셋 진행 ($caller)" >&2
        echo "proceed"; return 0
    fi
    marker_state "$tree"
    case $? in
        0) echo "[marker] respected: $tree ($(marker_track "$tree")) — $caller skip" >&2; echo "skip" ;;
        1) echo "[marker] stale marker(>${MARKER_TTL_HOURS}h) 치유: $tree — 경고 후 리셋 진행 + 마커 제거 ($caller)" >&2
           marker_remove "$tree"; echo "heal" ;;
        2) echo "proceed" ;;
    esac
}

marker_track() {
    local mp; mp="$(marker_path "$1")"
    [ -f "$mp" ] && grep -oE '"track"[[:space:]]*:[[:space:]]*"[^"]*"' "$mp" 2>/dev/null | sed -E 's/.*"([^"]*)"$/\1/' || true
}

# 마커 생성. 워커/런타임 트리 거부(§1-3). 인자: tree track purpose
marker_write() {
    local tree="$1" track="${2:-unknown}" purpose="${3:-}"
    if is_runtime_tree "$tree"; then
        echo "[marker] ✗ 거부: 런타임 트리에 세션 마커 금지($tree) — R1 자동화 단독 소유" >&2
        return 1
    fi
    local sid; sid="${SESSION_ID:-$(id -un)-$$}"
    cat > "$(marker_path "$tree")" <<EOF
{
  "session_id": "$sid",
  "track": "$track",
  "created_at": "$(date +%s)",
  "created_at_h": "$(date '+%Y-%m-%d %H:%M:%S %Z')",
  "purpose": "$purpose"
}
EOF
    echo "[marker] 생성: $(marker_path "$tree") (track=$track)" >&2
}

marker_remove() {
    local mp; mp="$(marker_path "$1")"
    [ -f "$mp" ] && rm -f "$mp" && echo "[marker] 제거: $mp" >&2 || true
}
