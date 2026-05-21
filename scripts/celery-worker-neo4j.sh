#!/bin/bash
# Celery Worker (neo4j 큐 전용) wrapper script for LaunchAgent
# common-bugs #25: macOS fork + Neo4j Bolt 드라이버 SIGSEGV 회피 위해 --pool=solo 필수
# Beat에서 queue: neo4j로 라우팅된 태스크 (chainsight sync, news sync 등) 전담 처리

set -e

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"

cd "$PROJECT_DIR"

# .env 로드 — celery-worker.sh와 동일 패턴 (set -a + source)
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    echo "[$(date)] .env loaded (neo4j worker)"
else
    echo "[$(date)] WARNING: .env not found"
fi

echo "[$(date)] === neo4j worker env ==="
echo "  NEO4J_URI=${NEO4J_URI:-(default)}"
echo "  CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}"
echo "========================="

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

# --pool=solo: fork 없이 단일 프로세스 (common-bugs #25)
# --concurrency=1: solo pool은 1만 의미 있음
# -Q neo4j: neo4j 큐만 listen (default 워커와 책임 분리)
# -n: 워커 이름에 neo4j 식별자 포함 (watchdog 매치용)
exec "$VENV_DIR/bin/celery" -A config worker \
    -Q neo4j \
    --pool=solo \
    --concurrency=1 \
    -n neo4j@%h \
    -l info
