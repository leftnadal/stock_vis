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
# 사용:
#   bash scripts/worker_sync.sh            # 3트리 동기화 + 재기동
#   bash scripts/worker_sync.sh --dry-run  # 변경 없이 트리별 HEAD↔origin/main 비교만 출력

set -euo pipefail

# ── 인자: --dry-run (사전 실측, 변경·재기동 없음) ──────────────────────
DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
elif [ -n "${1:-}" ]; then
    echo "[sync] 알 수 없는 인자: $1 (사용: [--dry-run])" >&2
    exit 64
fi

WORKER_TREE="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
WEB_TREE="/Users/byeongjinjeong/worktrees/sv-web-runtime"
API_TREE="/Users/byeongjinjeong/worktrees/sv-api-runtime"
SHARED_SIGNALS="/Users/byeongjinjeong/Desktop/stock_vis/frontend/public/static/signals"
WEB_SIGNALS="$WEB_TREE/frontend/public/static/signals"
UID_NUM="$(id -u)"
VENV_BIN="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin"

# ── 단계간 검증 헬퍼 (전부 non-fatal — 부팅 지연이 배포를 중단시키지 않게) ──
# celery worker가 브로커에 응답하는지 (재기동 후 task 재등록 확인 대용).
check_worker_registered() {
    local i
    for i in 1 2 3 4 5 6; do
        if "$VENV_BIN/celery" -A config inspect ping --timeout 6 >/dev/null 2>&1; then
            echo "[sync] ✓ celery worker 응답 (inspect ping)"
            return 0
        fi
        sleep 4
    done
    echo "[sync] ⚠ celery worker 무응답(부팅 지연/실패 가능) — celery-worker 로그 확인 권장." >&2
    return 0
}
# daphne(:18765)가 응답하는지 (401/403/200 = 정상, 인증 관문 살아있음).
check_daphne_health() {
    local i code
    for i in 1 2 3 4 5 6; do
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:18765/api/v1/chainsight/ 2>/dev/null || echo 000)"
        case "$code" in
            200|401|403) echo "[sync] ✓ daphne 응답 (HTTP $code)"; return 0 ;;
        esac
        sleep 4
    done
    echo "[sync] ⚠ daphne 응답 이상 (마지막 HTTP $code) — com.stockvis.web 로그 확인 권장." >&2
    return 0
}
# dry-run: 트리별 현재 HEAD ↔ origin/main 비교 (변경 없음).
plan_tree() {
    local tree="$1" label="$2" restart="$3"
    if [ ! -d "$tree" ]; then echo "[dry-run] $label: 트리 없음 ($tree) — 건너뜀"; return 0; fi
    git -C "$tree" fetch origin --quiet 2>/dev/null || true
    local head origin
    head="$(git -C "$tree" rev-parse --short HEAD 2>/dev/null || echo '?')"
    origin="$(git -C "$tree" rev-parse --short origin/main 2>/dev/null || echo '?')"
    if [ "$head" = "$origin" ]; then
        echo "[dry-run] $label: 이미 정합 (HEAD=$head) — 재기동 대상: $restart"
    else
        echo "[dry-run] $label: HEAD=$head → origin/main=$origin (re-detach 예정) — 재기동: $restart"
    fi
}

# ── 자기가드: 이 스크립트 사본이 origin/main 정합인지 (#47 / D-SYNC-ENTRYPOINT) ──
# stale 사본(공유 편집 트리·뒤처진 런타임 트리)에서 실행하면 구버전 로직 = 부분
# 동기화(실패 모드) → 거부가 맞다. 최신화는 래퍼 `sv sync`(exec 전 re-detach)가 담당.
# 본문의 트리 re-detach는 자기가드 통과 후이므로 자기 파일이 이미 origin/main = no-op
# (bash 실행 중 파일 무변경 = 버퍼링 위험 없음).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
guard_self_tree() {
    if ! git -C "$SCRIPT_DIR" fetch origin --quiet 2>/dev/null; then
        echo "[sync] ⚠ 네트워크 불가 — origin/main 대조 생략, 진행(graceful)." >&2
        return 0
    fi
    local head origin
    head="$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null)"
    origin="$(git -C "$SCRIPT_DIR" rev-parse origin/main 2>/dev/null)"
    if [ "$head" != "$origin" ]; then
        echo "[sync] ERROR: 이 스크립트 사본이 stale — 부분 동기화 방지 위해 중단(#47/D-SYNC-ENTRYPOINT)." >&2
        echo "[sync]   위치: $SCRIPT_DIR" >&2
        echo "[sync]   HEAD=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null) ≠ origin/main=$(git -C "$SCRIPT_DIR" rev-parse --short origin/main 2>/dev/null)" >&2
        echo "[sync]   → 해결: 'sv sync'(권장, 최신화 후 실행) 또는 런타임 트리 사본 직접 실행:" >&2
        echo "[sync]     bash $WORKER_TREE/scripts/worker_sync.sh" >&2
        exit 2
    fi
}
guard_self_tree

# ── dry-run: 계획만 출력하고 종료 (변경·재기동 없음) ──────────────────
if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] worker_sync 계획 (실제 변경 없음, 3트리):"
    plan_tree "$WORKER_TREE" "worker(sv-worker-runtime)"   "celery-worker+beat"
    plan_tree "$WEB_TREE"    "web(sv-web-runtime)"          "없음(next dev 핫리로드)"
    plan_tree "$API_TREE"    "api(sv-api-runtime, daphne)"  "com.stockvis.web(daphne)"
    echo "[dry-run] 끝 — 아무것도 변경하지 않음."
    exit 0
fi

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
check_worker_registered  # non-fatal: worker 응답 확인 (daphne 재기동 전 단계 검증)

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
    check_daphne_health  # non-fatal: daphne 응답 확인
fi
