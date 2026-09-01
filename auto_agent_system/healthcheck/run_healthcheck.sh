#!/usr/bin/env bash
set -uo pipefail

# ============================================================
# Stock-Vis 야간 하네스 건강 점검 (OPS-HEALTHCHECK-NIGHTLY-WIRE)
#
# 05:40 KST 실행. dogfood(05:20)와 분리된 독립 잡 — 한쪽이 죽어도 다른 쪽 보고가
# 멈추지 않는다(D-HC-NIGHTLY-WIRE, 옵션 A).
#
# 휴장일과 무관하게 매일 실행한다 — 하네스 정합성(문서·git·launchd 트리·.env)은
# 장이 열리는지와 무관하게 어긋날 수 있다.
#
# read-only: DB 쓰기 없음, 코드 수정 없음. 산출물은 전부 트리 밖(~/stock-vis-nightly)에
# 둔다 — 런타임 트리에 파일을 만들면 sv sync가 충돌한다(구 wrapper의 결함).
# ============================================================

NIGHTLY_DIR="$HOME/stock-vis-nightly"
LOG_DIR="$NIGHTLY_DIR/logs"
OUT_DIR="$NIGHTLY_DIR/health"
LOCK_FILE="$OUT_DIR/.healthcheck.lock"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/healthcheck_${TIMESTAMP}.log"
TODAY=$(date +%Y%m%d)
JSON_FILE="$OUT_DIR/health_${TODAY}.json"

# 실행 트리 = 이 스크립트가 속한 트리(self-locate). 공유 편집 트리 금지(#47).
PROJECT_DIR="${HEALTHCHECK_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# launchd 환경은 PATH가 최소라 poetry venv python을 직접 가리킨다.
VENV_PY="${HEALTHCHECK_PYTHON:-$HOME/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python}"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

mkdir -p "$LOG_DIR" "$OUT_DIR"
log() { echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"; }

# ── 중복 실행 방지 ────────────────────────────────────────
if [ -e "$LOCK_FILE" ]; then
  if kill -0 "$(cat "$LOCK_FILE" 2>/dev/null)" 2>/dev/null; then
    log "⏭  이미 실행 중(pid $(cat "$LOCK_FILE")) — 종료."
    exit 0
  fi
  log "⚠️  죽은 lock 발견 — 제거하고 진행."
  rm -f "$LOCK_FILE"
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

log "▶ 하네스 건강 점검 시작 (tree=$PROJECT_DIR)"

if [ ! -x "$VENV_PY" ]; then
  log "❌ python 실행 파일 없음: $VENV_PY"
  exit 1
fi
cd "$PROJECT_DIR" || { log "❌ 트리 진입 실패: $PROJECT_DIR"; exit 1; }

# ── ⑴ 점검 실행 → JSON (트리 밖) ──────────────────────────
# --ledger는 쓰지 않는다: 트리 내부 docs/harness/boundary_ledger.jsonl에 append 하므로
# 런타임 트리를 dirty로 만들어 sv sync와 충돌한다.
HC_EXIT=0
"$VENV_PY" scripts/health_check.py --json > "$JSON_FILE" 2>>"$LOG_FILE" || HC_EXIT=$?
log "점검 종료코드 $HC_EXIT → $JSON_FILE"

if [ ! -s "$JSON_FILE" ]; then
  log "❌ JSON이 비었음 — 점검 실행 실패. 로그: $LOG_FILE"
  exit 1
fi

# ── ⑵ diff + 메일 (조용한 날은 report 쪽에서 스스로 생략) ──
RC_MAIL=0
"$VENV_PY" -m auto_agent_system.healthcheck.report_health_mail --out-dir "$OUT_DIR" >>"$LOG_FILE" 2>&1 || RC_MAIL=$?
log "보고 종료코드 $RC_MAIL"

if [ "$RC_MAIL" -ne 0 ]; then
  log "❌ 보고 실패 — 로그: $LOG_FILE"
  exit 2
fi
if [ "$HC_EXIT" -ge 2 ]; then
  log "⚠️  점검에 ERROR 항목 있음(보고 발송됨) — 로그: $LOG_FILE"
  exit 1
fi
log "✅ 완료"
