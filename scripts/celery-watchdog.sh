#!/bin/bash
# Celery Watchdog — 프로세스 상태 확인 + macOS 알림 센터
# LaunchAgent에서 5분(300초) 간격으로 실행
# 다운 감지 시 소리 포함 알림, 연속 알림 방지를 위한 플래그 파일 사용

WORKER_FLAG="/tmp/stockvis-worker-down"
BEAT_FLAG="/tmp/stockvis-beat-down"

notify() {
    local title="$1"
    local message="$2"
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Crystal\""
}

check_process() {
    local name="$1"
    local pattern="$2"
    local flag="$3"

    if pgrep -f "$pattern" > /dev/null 2>&1; then
        # 프로세스 실행 중
        if [ -f "$flag" ]; then
            # 복구됨 — 플래그 삭제 + 복구 알림
            rm -f "$flag"
            notify "Stock-Vis 복구" "Celery $name 복구됨"
            echo "[$(date)] Celery $name RECOVERED"
        fi
    else
        # 프로세스 다운
        if [ ! -f "$flag" ]; then
            # 첫 감지 — 알림 발송 + 플래그 생성
            touch "$flag"
            notify "Stock-Vis 장애" "Celery $name 중단됨!"
            echo "[$(date)] Celery $name DOWN — notification sent"
        else
            echo "[$(date)] Celery $name still down (notification already sent)"
        fi
    fi
}

echo "[$(date)] Watchdog check started"
check_process "Worker" "celery.*worker" "$WORKER_FLAG"
check_process "Beat" "celery.*beat" "$BEAT_FLAG"
echo "[$(date)] Watchdog check completed"
