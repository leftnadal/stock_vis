#!/bin/bash
# cn_repair_nightly — C-N-REPAIR 뉴스 재수집 무인 배치 (launchd @ 22:10 KST).
#
# 역할: repair_batch_plan.md의 10 배치를 사람 트리거 없이 하루 1배치씩 순차 실행.
#   - 순번: 체크포인트(status.json next_batch). 성공 시에만 전진 → batch1 누락 방지.
#     (지시서 STEP 2-1 "경과일+1"은 day2 시작 시 batch1을 스킵 → 캘린더 산술 기각)
#   - 레이트리밋(AV 20 req/실행): 실행당 정확히 1배치(보존). 압축은 디렉터 승인 후.
#   - 멱등: backfill_broad_news = url upsert + --skip-covered → 재실행 무해.
#   - 이상 시에만 알림(정상=무알림). 10/10 완료 시 스스로 launchd unload.
#
# 실행 트리: REPO_DIR = 이 스크립트가 있는 트리(BASH_SOURCE self-locate).
#   운영 배치는 origin/main 추적 트리(sv-worker-runtime)에서 돌린다 — --dates·계획서 착지분.
# 로그/상태: ~/Library/Logs/stockvis/cn_repair (Desktop TCC 회피 = pg-backup 관례).
#
# 사용:
#   ./cn_repair_nightly.sh            # 실행(다음 배치 1개, --commit)
#   ./cn_repair_nightly.sh --dry-run  # 순번·대상일 매핑만(무쓰기, 카운터 불변)
#
# ⚠️ prod 쓰기 + AV 소비. launchd 등록·kickstart는 디렉터 명시 승인 후.
set -euo pipefail

# ── self-locate: REPO_DIR = 이 스크립트의 상위(트리 루트) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# ── 설정 ──
VENV="${CN_REPAIR_VENV:-$HOME/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python}"
PLAN_FILE="$REPO_DIR/docs/features/cn_repair/repair_batch_plan.md"
STATUS_PY="$SCRIPT_DIR/cn_repair_status.py"
LOG_DIR="$HOME/Library/Logs/stockvis/cn_repair"
STATUS_FILE="$LOG_DIR/status.json"
LABEL="com.stockvis.cn_repair.nightly"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
TOTAL_BATCHES=10
MAX_REQUESTS=20   # 계획서 예산(AV 25/day − broad beat 2 − 여유 3)

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$LOG_DIR"
TODAY="$(date +%F)"
TS="$(date -Iseconds)"
LOGFILE="$LOG_DIR/nightly_${TODAY}.log"
ALERT="$LOG_DIR/ALERT_${TODAY}.txt"
DONE_MARKER="$LOG_DIR/DONE.txt"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOGFILE"; }

alert() {  # $1=제목 $2=본문
  {
    echo "=== C-N-REPAIR ALERT $(date '+%F %T') ==="
    echo "$1"
    echo "$2"
  } | tee -a "$ALERT" >> "$LOGFILE"
  log "ALERT: $1"
  # 선호 채널: macOS 알림 센터(가용 시). 실패해도 스크립트 계속.
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$1\" with title \"C-N-REPAIR\" subtitle \"$2\"" >/dev/null 2>&1 || true
  fi
}

log "─── cn_repair_nightly 시작 (dry-run=$DRY_RUN, REPO_DIR=$REPO_DIR) ───"

# ── 전제 검증 ──
[ -f "$PLAN_FILE" ] || { alert "계획서 없음" "$PLAN_FILE 부재 — 트리 동기화 확인"; exit 1; }
[ -x "$VENV" ] || [ -f "$VENV" ] || { alert "venv 없음" "$VENV 부재"; exit 1; }
grep -q '"--dates"' "$REPO_DIR/services/news/management/commands/backfill_broad_news.py" \
  || { alert "--dates 미착지" "$REPO_DIR 트리에 backfill_broad_news --dates 없음 (worker_sync 필요)"; exit 1; }

# ── 순번 판정(체크포인트) ──
BATCH_NO="$("$VENV" "$STATUS_PY" next --status-file "$STATUS_FILE")"
log "다음 배치: $BATCH_NO / $TOTAL_BATCHES"

# ── 완료 감지 → 자동 마무리(STEP 4) ──
if [ "$BATCH_NO" -gt "$TOTAL_BATCHES" ]; then
  log "10/10 완료 감지."
  {
    echo "C-N-REPAIR 10/10 배치 완료 ($(date '+%F %T'))"
    echo "다음 단계(실행 아님, 안내): ① 일 단위 존재 검증(null 192일 각 >0) → ② C-L3-SELECT-V2 / REGEN-V2 진입."
    echo "Cowork 예약 리마인더는 이 시점에 삭제 가능(수동 유보 — 후보로만)."
  } | tee "$DONE_MARKER"
  if [ "$DRY_RUN" -eq 0 ] && [ -f "$PLIST" ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null \
      || launchctl unload "$PLIST" 2>/dev/null || true
    log "launchd 잡 unload(비활성) 시도 완료."
  fi
  exit 0
fi

# ── 배치 원라이너에서 대상 날짜 추출(계획서 순서 = 배치 순번) ──
DATES="$(sed -n 's/.*--dates "\([^"]*\)".*/\1/p' "$PLAN_FILE" | sed -n "${BATCH_NO}p")"
[ -n "$DATES" ] || { alert "배치$BATCH_NO 원라이너 없음" "계획서에서 $BATCH_NO번째 --dates 추출 실패"; exit 1; }
NDATES="$(awk -F, '{print NF}' <<< "$DATES")"
log "배치$BATCH_NO 대상: ${NDATES}일 (${DATES:0:60}...)"

# ── dry-run: --commit 없이 커맨드 자체 산정 실행, 카운터 불변 ──
if [ "$DRY_RUN" -eq 1 ]; then
  log "DRY-RUN: 커맨드 산정만(무쓰기). 카운터 불변."
  ( cd "$REPO_DIR" && "$VENV" manage.py backfill_broad_news \
      --max-requests "$MAX_REQUESTS" --dates "$DATES" ) 2>&1 | tee -a "$LOGFILE"
  log "─── dry-run 종료(배치$BATCH_NO 매핑 확인) ───"
  exit 0
fi

# ── 실행(--commit): 출력 캡처, exit code 보존 ──
TMPOUT="$(mktemp)"
set +e
( cd "$REPO_DIR" && "$VENV" manage.py backfill_broad_news --commit \
    --max-requests "$MAX_REQUESTS" --dates "$DATES" ) > "$TMPOUT" 2>&1
EXIT=$?
set -e
cat "$TMPOUT" >> "$LOGFILE"

# ── 결과 파싱(ANSI 제거) ──
CLEAN="$(sed 's/\x1b\[[0-9;]*m//g' "$TMPOUT")"
TARGET="$(grep -oE '백필 대상: [0-9]+창' <<< "$CLEAN" | grep -oE '[0-9]+' | head -1)"; TARGET="${TARGET:-0}"
SAVED="$(grep '\[완료\]' <<< "$CLEAN" | grep -oE 'saved [0-9]+' | grep -oE '[0-9]+' | head -1)"; SAVED="${SAVED:-0}"
UPDATED="$(grep '\[완료\]' <<< "$CLEAN" | grep -oE 'updated [0-9]+' | grep -oE '[0-9]+' | head -1)"; UPDATED="${UPDATED:-0}"
NET=$((SAVED + UPDATED))
rm -f "$TMPOUT"
log "결과: exit=$EXIT · 대상 ${TARGET}창 · saved=$SAVED · updated=$UPDATED · net=$NET"

# ── 이상치 판정(퀀트 밴드) ──
read -r MED LOW HIGH NSAMP <<< "$("$VENV" "$STATUS_PY" band --status-file "$STATUS_FILE")"
STATUS="ok"; ADVANCE=1; REASON=""
if [ "$EXIT" -ne 0 ]; then
  STATUS="fail"; ADVANCE=0
  REASON="exit code $EXIT (커맨드 실패) — 전진 보류, 다음 밤 재시도"
elif [ "$NET" -eq 0 ]; then
  STATUS="zero"; ADVANCE=0
  REASON="net 0건 (대상일=null인데 무수집 → fetch 실패/전량 skip 의심) — 전진 보류"
elif [ "$NSAMP" -ge 3 ]; then
  # 밴드 활성: 정수 비교(bash) 위해 소수 제거
  LOW_I="${LOW%.*}"; HIGH_I="${HIGH%.*}"
  if [ "$NET" -lt "$LOW_I" ] || [ "$NET" -gt "$HIGH_I" ]; then
    STATUS="ok_review"; ADVANCE=1
    REASON="net $NET 이 밴드[$LOW,$HIGH](중앙값 $MED, n=$NSAMP) 밖 — 데이터는 수집됨(전진), 검토 권장"
  fi
fi

# ── 상태 기록(성공 시에만 전진) ──
"$VENV" "$STATUS_PY" record --status-file "$STATUS_FILE" \
  --batch "$BATCH_NO" --target "$TARGET" --saved "$SAVED" --updated "$UPDATED" \
  --exit "$EXIT" --status "$STATUS" --advance "$ADVANCE" --ts "$TS" | tee -a "$LOGFILE"

# ── 알림(이상 시에만) ──
case "$STATUS" in
  ok)        log "정상 — 무알림. 다음 배치 대기." ;;
  ok_review) alert "배치$BATCH_NO 볼륨 이상(검토)" "$REASON" ;;
  zero|fail) alert "배치$BATCH_NO $STATUS" "$REASON" ;;
esac

log "─── cn_repair_nightly 종료 (status=$STATUS) ───"
exit 0
