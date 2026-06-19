#!/bin/bash
# Daphne ASGI 웹 서버 wrapper script for LaunchAgent (TRASH-9)
# .env를 안전하게 로드한 후 daphne를 exec으로 실행.
# 프론트엔드 NEXT_PUBLIC_API_URL=http://localhost:18765/api/v1 의 단일 백엔드.
#
# 배경: daphne만 launchd 미관리로 수동 기동돼, 2026-06-15 기동분이
#       옛 URLConf(events 라우트 없음)로 며칠 상주 → /chainsight 보드 404.
#       launchd KeepAlive로 일원화하여 staleness/고아 프로세스 재발 차단.

set -e

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"
PORT=18765

cd "$PROJECT_DIR"

# .env 로드 — celery-worker.sh와 동일 패턴(set -a + source, raw 값 형식 전제)
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    echo "[$(date)] .env loaded successfully (source mode)"
else
    echo "[$(date)] WARNING: .env file not found at $PROJECT_DIR/.env"
fi

echo "[$(date)] === Web (daphne) Environment Check ==="
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings}"
echo "  DB_HOST=${DB_HOST:-(default)}"
echo "  DB_NAME=${DB_NAME:-(default)}"
echo "  PORT=$PORT"
echo "======================================"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
# macOS Postgres GSS 행 방지(공통 버그 #25) — fork 없는 ASGI라도 DB 연결 안정화.
export PGGSSENCMODE="${PGGSSENCMODE:-disable}"

# exec으로 daphne 실행 (PID 유지 → launchd KeepAlive 정상 동작)
exec "$VENV_DIR/bin/daphne" -p "$PORT" -v 1 config.asgi:application
