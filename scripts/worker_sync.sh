#!/bin/bash
# worker_sync.sh — B′ worker 전용 트리 동기화 (D-B-WORKER)
#
# 워커 코드베이스(~/worktrees/sv-worker-runtime)를 최신 origin/main으로 정렬하고
# 워커를 재기동한다. 공유 편집 트리 브랜치 표류(#45)와 무관하게 워커가 항상
# 정렬된 코드로 bake하도록 보장하는 원커맨드.
#
# 사용: bash scripts/worker_sync.sh

set -euo pipefail

WORKER_TREE="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
SHARED_SIGNALS="/Users/byeongjinjeong/Desktop/stock_vis/frontend/public/static/signals"
UID_NUM="$(id -u)"

# ── 가드: 공유 signals가 심링크 ∧ 타겟 디렉토리 실존 ──────────────────
# 심링크가 깨졌거나 실디렉토리로 되돌아가면 서빙이 조용히 단절되므로 사전 차단.
if [ ! -L "$SHARED_SIGNALS" ]; then
    echo "[worker_sync] ERROR: 공유 signals가 심링크가 아님($SHARED_SIGNALS) — B′ 심링크 유실. 서빙 단절 위험, 중단." >&2
    exit 1
fi
if [ ! -d "$SHARED_SIGNALS/" ]; then
    echo "[worker_sync] ERROR: 공유 signals 심링크 타겟 부재 — worker 트리 signals 확인 필요. 중단." >&2
    exit 1
fi

# ── worker 트리 re-detach origin/main ────────────────────────────────
cd "$WORKER_TREE"
git fetch origin
git checkout --detach origin/main
echo "[worker_sync] worker 트리 re-detach: $(git rev-parse --short HEAD) (origin/main)"

# ── 워커·beat 재기동 (#41: 코드 변경 후 재기동 필수) ─────────────────
launchctl kickstart -k "gui/${UID_NUM}/com.stockvis.celery-worker"
launchctl kickstart -k "gui/${UID_NUM}/com.stockvis.celery-beat"
echo "[worker_sync] celery-worker·celery-beat 재기동 완료"
