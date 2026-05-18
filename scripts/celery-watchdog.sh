#!/bin/bash
# Celery Watchdog — 프로세스 상태 + 중복 인스턴스 감지 + macOS 알림
# LaunchAgent에서 5분(300초) 간격으로 실행
#
# 감지 조건:
#   1. Worker DOWN (count = 0)
#   2. Beat DOWN (count = 0)
#   3. Worker 중복 (count > 1) — Celery 큐 중복 처리 위험
#   4. Beat 중복 (count > 1) — 모든 스케줄 태스크가 2번 트리거 위험
#
# 플래그 파일로 알림 중복 방지. 복구 시 해제 알림.

WORKER_FLAG="/tmp/stockvis-worker-down"
BEAT_FLAG="/tmp/stockvis-beat-down"
WORKER_DUP_FLAG="/tmp/stockvis-worker-duplicate"
BEAT_DUP_FLAG="/tmp/stockvis-beat-duplicate"

notify() {
    local title="$1"
    local message="$2"
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Crystal\""
}

# count: ps + grep 매치 개수 (pgrep은 공백 패턴 처리가 BSD에서 불안정)
count_processes() {
    local pattern="$1"
    ps -eo pid,command 2>/dev/null | grep -F -- "$pattern" | grep -v grep | wc -l | tr -d ' '
}

# pids: ps + grep으로 PID 목록 추출
list_pids() {
    local pattern="$1"
    ps -eo pid,command 2>/dev/null | grep -F -- "$pattern" | grep -v grep | awk '{print $1}'
}

# 워커/Beat 단일 인스턴스 확인 — 중복 시 PID 리스트도 알림에 포함
check_singleton() {
    local name="$1"
    local pattern="$2"
    local down_flag="$3"
    local dup_flag="$4"

    local cnt
    cnt=$(count_processes "$pattern")

    if [ "$cnt" -eq 0 ]; then
        # DOWN
        if [ -f "$dup_flag" ]; then rm -f "$dup_flag"; fi  # dup도 같이 해제
        if [ ! -f "$down_flag" ]; then
            touch "$down_flag"
            notify "Stock-Vis 장애" "Celery $name 중단됨!"
            echo "[$(date)] Celery $name DOWN — notification sent"
        else
            echo "[$(date)] Celery $name still down (notification already sent)"
        fi
    elif [ "$cnt" -eq 1 ]; then
        # 정상
        if [ -f "$down_flag" ]; then
            rm -f "$down_flag"
            notify "Stock-Vis 복구" "Celery $name 복구됨"
            echo "[$(date)] Celery $name RECOVERED"
        fi
        if [ -f "$dup_flag" ]; then
            rm -f "$dup_flag"
            notify "Stock-Vis 정상화" "Celery $name 중복 해소"
            echo "[$(date)] Celery $name duplicate resolved"
        fi
    else
        # 중복 (count >= 2)
        local pids
        pids=$(list_pids "$pattern" | tr '\n' ',' | sed 's/,$//')
        if [ ! -f "$dup_flag" ]; then
            touch "$dup_flag"
            notify "Stock-Vis 중복 워커" "Celery $name 인스턴스 ${cnt}개 (PIDs: ${pids})"
            echo "[$(date)] Celery $name DUPLICATE detected: count=$cnt pids=$pids"
        else
            echo "[$(date)] Celery $name still duplicated: count=$cnt pids=$pids"
        fi
    fi
}

echo "[$(date)] Watchdog check started"

# Worker: 정확히 "celery -A config worker" 만 매치 (다른 celery 명령 제외)
check_singleton "Worker" "celery -A config worker" "$WORKER_FLAG" "$WORKER_DUP_FLAG"

# Beat: "celery -A config beat" 만 매치
check_singleton "Beat" "celery -A config beat" "$BEAT_FLAG" "$BEAT_DUP_FLAG"

echo "[$(date)] Watchdog check completed"
