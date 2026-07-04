#!/bin/bash
# Celery Worker wrapper script for LaunchAgent
# .env를 안전하게 로드한 후 celery worker를 exec으로 실행

set -e

# B′ worker 전용 트리 (D-B-WORKER): 워커 코드베이스를 공유 편집 트리에서 분리.
# 공유 트리 브랜치 표류와 무관하게 항상 origin/main 코드로 실행(#45 종료).
# .env는 worker 트리의 심링크(→ 공유 트리 .env)로 재사용.
PROJECT_DIR="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"

cd "$PROJECT_DIR"

# .env 로드 — bash source 사용 (따옴표/공백 처리 정확)
# 사유: 기존 `export "$line"` 패턴은 KEY="value" 형식에서 따옴표를 값에 포함시켜
#       FRED/Gemini API key가 invalid 처리되는 버그가 있었음.
#       set -a + source는 bash가 = 우측 따옴표를 syntax로 해석하여 정확하게 분리.
#       단, .env는 따옴표 없는 raw 값 형식이어야 함 (현재 정리 완료).
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
echo "  ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY:+SET}"
echo "  FMP_API_KEY=${FMP_API_KEY:+SET}"
echo "  GEMINI_API_KEY=${GEMINI_API_KEY:+SET}"
echo "  CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}"
echo "==========================="

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

# exec으로 celery worker 실행 (PID 유지)
exec "$VENV_DIR/bin/celery" -A config worker -l info --concurrency=4
