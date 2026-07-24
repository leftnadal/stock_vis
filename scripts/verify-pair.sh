#!/bin/bash
# verify_pair_aggregation.py 실행 wrapper (launchd daily, 02:30 KST).
# .env 로드 후 #28 자율 틱 검증을 돌리고 결과를 로그에 남긴다.
# exit code: python 스크립트 그대로 반환(0=PASS/1=WARN/2=FAIL). launchd는 로그만 본다.

set -uo pipefail

# PROJECT_DIR = 이 스크립트가 속한 트리(scripts/의 부모)를 self-locate로 도출.
# 하드코딩 시 launchd가 어느 트리로 plist를 지향하든 래퍼가 공유트리로 cd해 drift 발생 →
# BASH_SOURCE 기준 자기위치 도출로 "래퍼가 있는 트리"의 코드를 돌린다(OPS-VERIFY-EXEC-TREE, 개정문1).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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
