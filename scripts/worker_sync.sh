#!/bin/bash
# worker_sync.sh — 런타임 트리 공통 동기화 (D-B-WORKER / D-W-WEB / D-DAPHNE-RUNTIME)
#
# 런타임 트리(worker·web·api)를 최신 origin/main으로 정렬한다. 공유 편집 트리
# 브랜치 표류(#45)와 무관하게 워커 bake·web 서빙·API 응답이 항상 정렬된 코드로 동작.
#   - worker 트리: re-detach + celery-worker/beat 재기동(#41).
#   - web 트리: re-detach만(next dev는 핫리로드). package 변경 시 경고(자동 재시작 금지).
#   - api 트리(daphne): re-detach + daphne 재기동. ⚠ WS 연결 끊김 유발
#     (graceful reload는 휴면 후보 DAPHNE-GRACEFUL).
#
# 사용: bash scripts/worker_sync.sh

set -euo pipefail

WORKER_TREE="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
WEB_TREE="/Users/byeongjinjeong/worktrees/sv-web-runtime"
API_TREE="/Users/byeongjinjeong/worktrees/sv-api-runtime"
SHARED_SIGNALS="/Users/byeongjinjeong/Desktop/stock_vis/frontend/public/static/signals"
WEB_SIGNALS="$WEB_TREE/frontend/public/static/signals"
UID_NUM="$(id -u)"

# ── 가드: signals 심링크 ∧ 타겟 실존 (worker 판 + web 판) ─────────────
# 심링크가 깨졌거나 실디렉토리로 되돌아가면 서빙이 조용히 단절되므로 사전 차단.
guard_symlink() {
    local path="$1" label="$2"
    if [ ! -L "$path" ]; then
        echo "[sync] ERROR: $label signals가 심링크가 아님($path) — 심링크 유실. 서빙 단절 위험, 중단." >&2
        exit 1
    fi
    if [ ! -d "$path/" ]; then
        echo "[sync] ERROR: $label signals 심링크 타겟 부재 — worker 트리 signals 확인 필요. 중단." >&2
        exit 1
    fi
}
guard_symlink "$SHARED_SIGNALS" "공유(worker bake)"
[ -d "$WEB_TREE" ] && guard_symlink "$WEB_SIGNALS" "web(next dev)"

# ── worker 트리 re-detach + 재기동 ───────────────────────────────────
cd "$WORKER_TREE"
git fetch origin
git checkout --detach origin/main
echo "[sync] worker 트리 re-detach: $(git rev-parse --short HEAD)"
launchctl kickstart -k "gui/${UID_NUM}/com.stockvis.celery-worker"
launchctl kickstart -k "gui/${UID_NUM}/com.stockvis.celery-beat"
echo "[sync] celery-worker·celery-beat 재기동 완료"

# ── web 트리 re-detach (next dev 핫리로드 — 프로세스 재기동 안 함) ────
if [ -d "$WEB_TREE" ]; then
    cd "$WEB_TREE"
    PREV="$(git rev-parse HEAD)"
    git fetch origin
    git checkout --detach origin/main
    echo "[sync] web 트리 re-detach: $(git rev-parse --short HEAD) (next dev 핫리로드 반영)"
    # package.json/lock 변경 시 = 의존 재설치 + next dev 재시작 필요(수동, 자동 금지)
    if ! git diff --quiet "$PREV" "$(git rev-parse HEAD)" -- frontend/package.json frontend/package-lock.json; then
        echo "[sync] ⚠ WARNING: frontend/package(.json|-lock) 변경 감지 — 'npm install' + next dev 수동 재시작 필요(핫리로드로 미반영)." >&2
    fi
fi

# ── api 트리(daphne) re-detach + 재기동 (D-DAPHNE-RUNTIME) ────────────
# daphne는 코드를 프로세스 기동 시점에 import → 핫리로드 없음, 재기동 필수.
# ⚠ 재기동은 WebSocket 연결을 끊는다(graceful reload는 휴면 후보 DAPHNE-GRACEFUL).
if [ -d "$API_TREE" ]; then
    cd "$API_TREE"
    git fetch origin
    git checkout --detach origin/main
    echo "[sync] api 트리 re-detach: $(git rev-parse --short HEAD)"
    launchctl kickstart -k "gui/${UID_NUM}/com.stockvis.web"
    echo "[sync] daphne(com.stockvis.web) 재기동 완료 (⚠ WS 재연결 필요)"
fi
