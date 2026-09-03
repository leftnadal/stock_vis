#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Stock-Vis 야간 도그푸딩 에이전트 — 1단계(정량) + 2단계(루브릭 채점)
#
# 05:20 KST 실행. 미국장 휴장일(주말·NYSE 휴장)은 점검을 건너뛴다 — 장이 안 열린
# 날은 EOD 데이터가 갱신되지 않아 신선도 판정이 무의미하고, 매일 오는 메일에
# 의미 없는 통지가 섞이면 읽히지 않기 때문이다. 강제 실행은 --force.
#
# 2단계(AGENT-S2): 렌더 수집(Playwright) → 루브릭 채점(claude -p 1회) → 메일에 병합.
# 2단계가 실패해도 1단계 점검과 메일은 그대로 나간다(격리).
#
# read-only: DB 쓰기 없음, 코드 수정 없음. GET 네비게이션과 로그인 외 상태 변경 금지.
# tier1~3 스크립트·healthcheck 에이전트와 독립.
# ============================================================

FORCE="${1:-}"

NIGHTLY_DIR="$HOME/stock-vis-nightly"
LOG_DIR="$NIGHTLY_DIR/logs"
OUT_DIR="$NIGHTLY_DIR/dogfood"
LOCK_FILE="$OUT_DIR/.dogfood.lock"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/dogfood_${TIMESTAMP}.log"

# 실행 트리 = 런타임 트리(origin/main 정합). Desktop 사본 금지(#47 stale 사본 방지).
PROJECT_DIR="${DOGFOOD_PROJECT_DIR:-$HOME/worktrees/sv-worker-runtime}"

# launchd 환경에서는 PATH가 최소라 poetry venv python을 직접 가리킨다.
VENV_PY="${DOGFOOD_PYTHON:-$HOME/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python}"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

mkdir -p "$LOG_DIR" "$OUT_DIR"
log() { echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"; }

# ── 중복 실행 방지 (수동 실행과 launchd가 겹치는 경우) ────────────
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

log "▶ 도그푸딩 1단계 시작 (tree=$PROJECT_DIR)"

if [ ! -x "$VENV_PY" ]; then
  log "❌ python 실행 파일 없음: $VENV_PY"
  exit 1
fi
cd "$PROJECT_DIR"

# ── 휴장 판정 ─────────────────────────────────────────────
HOLIDAY="$("$VENV_PY" -c "
from datetime import date
from auto_agent_system.dogfood.market_calendar import holiday_name
print(holiday_name(date.today()) or '')
" 2>>"$LOG_FILE")"

if [ -n "$HOLIDAY" ] && [ "$FORCE" != "--force" ]; then
  log "⏭  미국장 휴장($HOLIDAY) — 점검 스킵. 강제 실행은 --force."
  exit 0
fi
[ -n "$HOLIDAY" ] && log "⚠️  휴장($HOLIDAY)인데 --force로 실행합니다."

# ── ⑴ 정량 체크 ───────────────────────────────────────────
RC_CHECK=0
"$VENV_PY" -m auto_agent_system.dogfood.check_quant --out-dir "$OUT_DIR" >>"$LOG_FILE" 2>&1 || RC_CHECK=$?
log "정량 체크 종료코드 $RC_CHECK"

# ── ⑵ 렌더 수집 (AGENT-S2, 2단계) ─────────────────────────────
# 2·3단계 실패는 경고로 남기고 메일은 반드시 발송한다(1단계와 격리).
RC_RENDER=0
"$VENV_PY" -m auto_agent_system.dogfood.collect_rendered --out-dir "$OUT_DIR" >>"$LOG_FILE" 2>&1 || RC_RENDER=$?
log "렌더 수집 종료코드 $RC_RENDER"
[ "$RC_RENDER" -ne 0 ] && log "⚠️  렌더 수집에 문제 있음 — 루브릭은 '측정 불가'로 보고됩니다."

# ── ⑶ 루브릭 채점 (AGENT-S2) ──────────────────────────────────
RC_SCORE=0
if [ "$RC_RENDER" -eq 0 ]; then
  "$VENV_PY" -m auto_agent_system.dogfood.score_rubric --out-dir "$OUT_DIR" >>"$LOG_FILE" 2>&1 || RC_SCORE=$?
  log "루브릭 채점 종료코드 $RC_SCORE"
  [ "$RC_SCORE" -ne 0 ] && log "⚠️  채점 실패 — 루브릭은 '측정 불가'로 보고됩니다."
else
  log "⏭  렌더 수집 실패로 채점 생략."
  RC_SCORE=1
fi

# ── ⑷ diff + 메일 (체크가 fail이어도 보고는 해야 하므로 계속) ──
RC_MAIL=0
"$VENV_PY" -m auto_agent_system.dogfood.report_mail --out-dir "$OUT_DIR" >>"$LOG_FILE" 2>&1 || RC_MAIL=$?
log "메일 종료코드 $RC_MAIL"

if [ "$RC_MAIL" -ne 0 ]; then
  log "❌ 메일 발송 실패 — 로그: $LOG_FILE"
  exit 2
fi
if [ "$RC_CHECK" -ne 0 ]; then
  log "⚠️  정량 체크에 실패 항목 있음(메일 발송됨) — 로그: $LOG_FILE"
  exit 1
fi
log "✅ 완료"
