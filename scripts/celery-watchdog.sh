#!/bin/bash
# Celery Watchdog — 프로세스 상태 + 중복 인스턴스 감지 + 자동 재시작 + 메일 알림
# LaunchAgent에서 5분(300초) 간격으로 실행
#
# 감지 대상:
#   1. Worker (default)  — `celery -A config worker -l info --concurrency=4`
#   2. Worker (neo4j)    — `celery -A config worker -Q neo4j`
#   3. Beat              — `celery -A config beat`
#
# 동작:
#   - 다운 감지 → launchctl kickstart로 1차 재시작 시도
#   - 다음 5분 후에도 여전히 다운이면 → 메일 발송 (Gmail SMTP via Django)
#   - 중복(count > 1) 감지 → 메일 발송 (PID 포함)
#   - 정상 복구 → 복구 메일
#   - macOS notification은 보조 알림 (즉시 데스크탑 알림)
#
# flag 파일: /tmp/stockvis-{name}-{down|duplicate|kicked}

set +e  # 개별 실패가 전체 워치독을 죽이지 않도록

PROJECT_DIR="/Users/byeongjinjeong/Desktop/stock_vis"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"
DJANGO_SETTINGS="${DJANGO_SETTINGS_MODULE:-config.settings}"
ALERT_RECIPIENT="${EMAIL_HOST_USER:-jinie545@gmail.com}"

notify_desktop() {
    local title="$1"
    local message="$2"
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Crystal\"" 2>/dev/null || true
}

# Django send_mail로 알림 메일 발송 (Gmail SMTP 이미 설정됨)
notify_mail() {
    local subject="$1"
    local body="$2"

    cd "$PROJECT_DIR" || return 1

    if [ -f .env ]; then
        set -a
        # shellcheck disable=SC1091
        . ./.env
        set +a
    fi
    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS"

    "$VENV_DIR/bin/python" - "$subject" "$body" "$ALERT_RECIPIENT" <<'PY' 2>&1 | tail -3
import sys
import django
django.setup()
from django.core.mail import send_mail
from django.conf import settings

subject, body, recipient = sys.argv[1], sys.argv[2], sys.argv[3]
send_mail(
    subject=f'[Stock-Vis Watchdog] {subject}',
    message=body,
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[recipient],
    fail_silently=False,
)
print(f'mail sent ok → {recipient}')
PY
}

count_processes() {
    local pattern="$1"
    ps -eo pid,command 2>/dev/null | grep -F -- "$pattern" | grep -v grep | wc -l | tr -d ' '
}

list_pids() {
    local pattern="$1"
    ps -eo pid,command 2>/dev/null | grep -F -- "$pattern" | grep -v grep | awk '{print $1}' | tr '\n' ',' | sed 's/,$//'
}

# 서비스 점검 + 자동 재시작 + 메일
# args: name pattern launchd_label
check_service() {
    local name="$1"
    local pattern="$2"
    local label="$3"

    local down_flag="/tmp/stockvis-${label}-down"
    local dup_flag="/tmp/stockvis-${label}-duplicate"
    local kicked_flag="/tmp/stockvis-${label}-kicked"

    local cnt
    cnt=$(count_processes "$pattern")

    if [ "$cnt" -eq 0 ]; then
        # DOWN
        rm -f "$dup_flag"
        if [ ! -f "$down_flag" ]; then
            # 첫 감지: launchctl로 재시작 시도, 메일은 다음 사이클까지 대기
            touch "$down_flag"
            touch "$kicked_flag"
            notify_desktop "Stock-Vis ${name} DOWN" "재시작 시도 중 (${label})"
            echo "[$(date)] ${name} DOWN — launchctl kickstart: ${label}"
            launchctl kickstart -k "gui/$UID/${label}" 2>&1 | head -3
        elif [ -f "$kicked_flag" ]; then
            # 재시작 시도했지만 여전히 다운 → 메일
            rm -f "$kicked_flag"
            local body="Celery ${name}(${label})가 자동 재시작 후에도 가동되지 않습니다.

확인 명령:
  launchctl print gui/\$UID/${label}
  tail -50 ~/Library/Logs/stockvis/${label#com.stockvis.}-error.log

시각: $(date)"
            echo "[$(date)] ${name} 재시작 실패 — 메일 발송"
            notify_mail "${name} 재시작 실패" "$body"
            notify_desktop "Stock-Vis ${name} 재시작 실패" "메일 발송됨"
        else
            # 한번 더 재시작 시도
            touch "$kicked_flag"
            echo "[$(date)] ${name} still down — kickstart 재시도"
            launchctl kickstart -k "gui/$UID/${label}" 2>&1 | head -3
        fi
    elif [ "$cnt" -eq 1 ]; then
        # 정상
        if [ -f "$down_flag" ] || [ -f "$kicked_flag" ]; then
            rm -f "$down_flag" "$kicked_flag"
            notify_desktop "Stock-Vis ${name} 복구" "정상 가동"
            echo "[$(date)] ${name} RECOVERED"
            notify_mail "${name} 복구" "Celery ${name}(${label})가 정상 가동되었습니다.

시각: $(date)"
        fi
        if [ -f "$dup_flag" ]; then
            rm -f "$dup_flag"
            notify_desktop "Stock-Vis ${name} 정상화" "중복 해소"
            echo "[$(date)] ${name} duplicate resolved"
        fi
    else
        # 중복 (count >= 2) — 즉시 메일
        local pids
        pids=$(list_pids "$pattern")
        if [ ! -f "$dup_flag" ]; then
            touch "$dup_flag"
            local body="Celery ${name}(${label}) 인스턴스 ${cnt}개 가동 중. 큐 중복 처리 위험.

PIDs: ${pids}
조치: 비-launchd 인스턴스 종료 (kill <PID>)

시각: $(date)"
            notify_desktop "Stock-Vis ${name} 중복" "인스턴스 ${cnt}개 (PIDs: ${pids})"
            notify_mail "${name} 중복 가동" "$body"
            echo "[$(date)] ${name} DUPLICATE: count=${cnt} pids=${pids}"
        else
            echo "[$(date)] ${name} still duplicated: count=${cnt} pids=${pids}"
        fi
    fi
}

echo "[$(date)] Watchdog check started"

# default 워커: --concurrency=4 로 neo4j 워커와 구별
check_service "Worker (default)" "celery -A config worker -l info --concurrency=4" "com.stockvis.celery-worker"

# neo4j 워커: -Q neo4j
check_service "Worker (neo4j)" "celery -A config worker -Q neo4j" "com.stockvis.celery-worker-neo4j"

# Beat
check_service "Beat" "celery -A config beat" "com.stockvis.celery-beat"

echo "[$(date)] Watchdog check completed"
