#!/bin/bash
# Celery Beat wrapper script for LaunchAgent
# .env를 안전하게 로드한 후 celery beat를 exec으로 실행
#
# ★ PROJECT_DIR = worker 런타임 트리(B′, celery-worker.sh와 동일). 사유(2026-07-10 사고):
#   DatabaseScheduler는 기동 시 app.conf.beat_schedule dict를 DB로 sync(create/update)하므로,
#   메인 편집 repo(브랜치 표류)에서 beat를 띄우면 stale config가 DB를 매 재기동마다 덮어써
#   수동 교정(예: collect-av tz=UTC)이 무효화된다(#28 정정). 런타임 트리(origin/main 정렬)에서
#   띄워야 startup sync가 최신 config를 반영한다. 갱신 = worker_sync.sh.

set -e

PROJECT_DIR="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"

cd "$PROJECT_DIR"

# .env 로드 — bash source 사용 (따옴표/공백 처리 정확)
# 사유: 기존 `export "$line"` 패턴은 KEY="value" 형식에서 따옴표를 값에 포함시키는 버그.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    echo "[$(date)] .env loaded successfully (source mode)"
else
    echo "[$(date)] WARNING: .env file not found at $PROJECT_DIR/.env"
fi

# 주요 환경변수 로드 확인
echo "[$(date)] === Environment Check ==="
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings}"
echo "  DB_HOST=${DB_HOST:-(default)}"
echo "  DB_NAME=${DB_NAME:-(default)}"
echo "  CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}"
echo "==========================="

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

# exec으로 celery beat 실행 (PID 유지)
exec "$VENV_DIR/bin/celery" -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
