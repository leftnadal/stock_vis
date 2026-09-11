#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AGENT-SHOT-1 — 온디맨드 화면 캡처 진입점
#
# 야간 도그푸딩(run_dogfood.sh)의 렌더 경로(collect_rendered → render_screens.mjs)를
# 재사용해 임의 경로/기존 목록 부분의 스크린샷(PNG)만 뜬다. 채점·메일 없음(LLM 비용 0).
# 인증은 야간과 동일(.env 명시 로드 = S2.1). 야간 05:20 경로·산출물 파일명·plist 무접촉.
#
# 사용:
#   scripts/shot.sh --path /monitor/<id> [--full|--no-full]
#   scripts/shot.sh --screens key1,key2
# 출력: stock-vis-nightly/adhoc/<YYYYMMDD_HHMM>/ (PNG + 텍스트 + meta.json)
#
# env -i 재현(인증이 셸이 아니라 .env에서 오는지 입증):
#   env -i HOME="$HOME" PATH=/usr/bin:/bin bash scripts/shot.sh --path /... --full
# ============================================================

# launchd/env -i 환경 대비(HOME이 비면 산출물 경로가 깨진다).
export HOME="${HOME:-/Users/byeongjinjeong}"

# 실행 트리 = 런타임 트리(origin/main 정합). 개발 검증은 DOGFOOD_PROJECT_DIR로 override.
PROJECT_DIR="${DOGFOOD_PROJECT_DIR:-$HOME/worktrees/sv-worker-runtime}"
VENV_PY="${DOGFOOD_PYTHON:-$HOME/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python}"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

if [ ! -x "$VENV_PY" ]; then
  echo "❌ python 실행 파일 없음: $VENV_PY" >&2
  exit 1
fi

cd "$PROJECT_DIR"
exec "$VENV_PY" -m auto_agent_system.dogfood.shot "$@"
