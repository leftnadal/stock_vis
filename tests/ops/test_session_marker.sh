#!/usr/bin/env bash
# test_session_marker.sh — OPS-WORKTREE-ISOLATION Phase 1 마커 라이브러리 테스트.
# 실행: bash tests/ops/test_session_marker.sh  (exit 0=PASS)
set -uo pipefail

DIR="$(cd "$(dirname "$0")/../../scripts/lib" && pwd)"
source "$DIR/session_marker.sh"

PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
check(){ [ "$2" = "$3" ] && ok "$1 ($2)" || bad "$1: 기대=$3 실제=$2"; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# 1) 마커 부재 → proceed
check "부재→proceed" "$(marker_respect "$TMP" test 2>/dev/null)" "proceed"

# 2) 신선 마커 → skip (marker_write로 생성, created_at=now)
marker_write "$TMP" mytrack "테스트" >/dev/null 2>&1
check "신선→skip" "$(marker_respect "$TMP" test 2>/dev/null)" "skip"
check "track 판독" "$(marker_track "$TMP")" "mytrack"

# 3) stale 마커(>TTL) → heal + 마커 제거
cat > "$(marker_path "$TMP")" <<EOF
{ "session_id":"x", "track":"old", "created_at":"$(( $(date +%s) - 25*3600 ))", "purpose":"" }
EOF
check "stale→heal" "$(marker_respect "$TMP" test 2>/dev/null)" "heal"
[ ! -f "$(marker_path "$TMP")" ] && ok "heal 후 마커 제거됨" || bad "heal 후 마커 잔존"

# 4) 워커(런타임) 트리 → marker_write 거부 + respect=proceed(예외)
RT="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
if marker_write "$RT" x 2>/dev/null; then bad "런타임 트리 마커 생성이 거부 안 됨"; marker_remove "$RT" 2>/dev/null; else ok "런타임 트리 마커 생성 거부"; fi
check "런타임→proceed(예외)" "$(marker_respect "$RT" test 2>/dev/null)" "proceed"

# 5) 불량 마커(created_at 없음) → stale 취급(heal)
echo '{ "track":"broken" }' > "$(marker_path "$TMP")"
check "불량마커→heal" "$(marker_respect "$TMP" test 2>/dev/null)" "heal"

echo "─────────────────────────────"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ] && { echo "✅ ALL GREEN"; exit 0; } || { echo "❌ FAIL"; exit 1; }
