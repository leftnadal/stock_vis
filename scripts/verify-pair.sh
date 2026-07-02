#!/bin/bash
# verify_pair_aggregation.py 실행 wrapper (launchd daily, 02:30 KST).
# .env 로드 후 #28 자율 틱 검증을 돌리고 결과를 로그에 남긴다.
# exit code: python 스크립트 그대로 반환(0=PASS/1=WARN/2=FAIL). launchd는 로그만 본다.

set -uo pipefail

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"

cd "$PROJECT_DIR"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

echo "===== [$(date '+%Y-%m-%d %H:%M:%S %Z')] verify_pair_aggregation ====="
"$VENV_DIR/bin/python" scripts/verify_pair_aggregation.py
