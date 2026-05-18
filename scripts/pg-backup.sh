#!/bin/bash
# PostgreSQL 일일 백업 — launchd로 매일 02:00 KST 실행
#
# 출력: ~/Library/Application Support/stockvis-backups/{date}.dump (custom format, -Z 9)
# Rotation: 7일치 유지, 그 이상은 자동 삭제
#
# 복구: pg_restore -d stock_vis_restore <backup.dump>

set -euo pipefail

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
BACKUP_DIR="$HOME/Library/Application Support/stockvis-backups"
PG_BIN="/opt/homebrew/opt/postgresql@16/bin"

mkdir -p "$BACKUP_DIR"

# .env 로드 (DB credentials 옵션 — 기본값으로도 동작)
cd "$PROJECT_DIR"
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

DB_NAME="${DB_NAME:-stock_vis}"
DB_USER="${DB_USER:-byeongjinjeong}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

DATE=$(date +%Y-%m-%d)
DUMP_FILE="$BACKUP_DIR/$DATE.dump"

echo "[$(date)] pg-backup start → $DUMP_FILE"
echo "  DB: $DB_NAME @ $DB_HOST:$DB_PORT (user=$DB_USER)"

# pg_dump custom format + 압축 9 — pg_restore로 부분 복원 가능
"$PG_BIN/pg_dump" \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F c -Z 9 -f "$DUMP_FILE"
RC=$?

if [ $RC -eq 0 ] && [ -f "$DUMP_FILE" ]; then
    SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    echo "[$(date)] backup OK: $DUMP_FILE ($SIZE)"
else
    echo "[$(date)] backup FAILED: rc=$RC"
    osascript -e "display notification \"PostgreSQL 백업 실패 (rc=$RC)\" with title \"Stock-Vis 장애\" sound name \"Crystal\"" 2>/dev/null || true
    exit $RC
fi

# Rotation: 7일 이상된 .dump 파일 삭제
echo "[$(date)] rotation: 7일 초과 백업 정리"
DELETED=$(find "$BACKUP_DIR" -name "*.dump" -mtime +7 -print -delete 2>&1 | wc -l | tr -d ' ')
echo "  deleted $DELETED files"

# 현재 백업 목록
echo "[$(date)] current backups:"
ls -la "$BACKUP_DIR"/*.dump 2>/dev/null | tail -10

exit 0
