#!/bin/bash
# Celery Worker wrapper script for LaunchAgent
# .env를 안전하게 로드한 후 celery worker를 exec으로 실행

set -e

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"

cd "$PROJECT_DIR"

# .env 안전 로드 (주석, 공백 줄 무시)
if [ -f .env ]; then
    while IFS= read -r line; do
        # 빈 줄, 주석, 공백만 있는 줄 무시
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" =~ ^[[:space:]]*$ ]] && continue
        export "$line"
    done < .env
    echo "[$(date)] .env loaded successfully"
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
