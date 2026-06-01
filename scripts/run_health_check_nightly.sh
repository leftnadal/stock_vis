#!/bin/bash
# ============================================================
#  야간 자동화용 health_check.py 실행 wrapper
#
#  매일 nightly_v3.sh 종료 직전 호출되어 docs/nightly_auto_system/
#  YYYYMM/DD/health_check.json에 정합성 점검 결과 저장.
#
#  단계 1 (2026-05-28~): 누적 기록만, 알림 없음.
#  단계 2 (2026-06-중 예정): 1~2주 관찰 후 임계 결정 + 알림 도입.
#
#  관련 결정: DECISIONS.md "문서·git 정합성 관리 원칙" Layer 1
#  관련 버그: sub_claude_md/common-bugs.md #30
#
#  exit code: 항상 0 반환 (cron이 nightly 전체를 실패로 잡지 않게).
#  실제 health_check exit code는 JSON 본문의 status 필드로 보존.
# ============================================================

set -uo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/stock-vis}"
REPORT_BASE="$PROJECT_DIR/docs/nightly_auto_system"
YEAR_MONTH=$(date +%Y%m)
DAY=$(date +%d)
REPORT_DIR="$REPORT_BASE/$YEAR_MONTH/$DAY"
OUTPUT_FILE="$REPORT_DIR/health_check.json"

# PROJECT_DIR / health_check.py 존재 확인
if [ ! -f "$PROJECT_DIR/scripts/health_check.py" ]; then
    echo "[health_check_nightly] scripts/health_check.py 없음 — 건너뜀: $PROJECT_DIR" >&2
    exit 0
fi

mkdir -p "$REPORT_DIR"

cd "$PROJECT_DIR" || exit 0

# JSON 모드 + stderr 통합 저장, exit code는 별도 보존
HC_EXIT=0
python3 scripts/health_check.py --json --ledger > "$OUTPUT_FILE" 2>>"$REPORT_DIR/health_check.stderr.log" || HC_EXIT=$?

# 콘솔에도 1줄 요약 (cron log)
echo "[health_check_nightly] $(date '+%Y-%m-%d %H:%M:%S') exit=$HC_EXIT -> $OUTPUT_FILE"

# nightly 전체가 fail로 잡히지 않도록 항상 0 반환 (단계 1 정책)
exit 0
