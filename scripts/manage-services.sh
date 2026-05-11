#!/bin/bash
# Stock-Vis 서비스 관리 스크립트
# Usage: ./scripts/manage-services.sh {start|stop|restart|status|logs}

set -e

WORKER_PLIST="$HOME/Library/LaunchAgents/com.stockvis.celery-worker.plist"
BEAT_PLIST="$HOME/Library/LaunchAgents/com.stockvis.celery-beat.plist"
WATCHDOG_PLIST="$HOME/Library/LaunchAgents/com.stockvis.celery-watchdog.plist"
LOG_DIR="$(dirname "$0")/../logs"

case "$1" in
    start)
        echo "Starting Stock-Vis services..."
        launchctl load "$WORKER_PLIST" 2>/dev/null && echo "  Celery worker: started" || echo "  Celery worker: already loaded"
        launchctl load "$BEAT_PLIST" 2>/dev/null && echo "  Celery beat: started" || echo "  Celery beat: already loaded"
        launchctl load "$WATCHDOG_PLIST" 2>/dev/null && echo "  Celery watchdog: started" || echo "  Celery watchdog: already loaded"
        echo "Done."
        ;;
    stop)
        echo "Stopping Stock-Vis services..."
        launchctl unload "$WATCHDOG_PLIST" 2>/dev/null && echo "  Celery watchdog: stopped" || echo "  Celery watchdog: not loaded"
        launchctl unload "$BEAT_PLIST" 2>/dev/null && echo "  Celery beat: stopped" || echo "  Celery beat: not loaded"
        launchctl unload "$WORKER_PLIST" 2>/dev/null && echo "  Celery worker: stopped" || echo "  Celery worker: not loaded"
        echo "Done."
        ;;
    restart)
        echo "Restarting Stock-Vis services..."
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        echo "Stock-Vis service status:"
        echo -n "  Celery worker:   "
        launchctl list | grep -q "com.stockvis.celery-worker" && echo "running" || echo "stopped"
        echo -n "  Celery beat:     "
        launchctl list | grep -q "com.stockvis.celery-beat" && echo "running" || echo "stopped"
        echo -n "  Celery watchdog: "
        launchctl list | grep -q "com.stockvis.celery-watchdog" && echo "running" || echo "stopped"
        echo ""
        echo "Redis:"
        echo -n "  "
        brew services list | grep redis || echo "  redis not found"
        echo ""
        echo "PostgreSQL:"
        echo -n "  "
        brew services list | grep postgresql || echo "  postgresql not found"
        echo ""
        echo "Neo4j:"
        echo -n "  "
        brew services list | grep neo4j || echo "  neo4j not found"
        ;;
    logs)
        LOG_TYPE="${2:-worker}"
        case "$LOG_TYPE" in
            worker)
                tail -f "$LOG_DIR/celery-worker.log"
                ;;
            beat)
                tail -f "$LOG_DIR/celery-beat.log"
                ;;
            watchdog)
                tail -f "$LOG_DIR/celery-watchdog.log"
                ;;
            errors)
                tail -f "$LOG_DIR/celery-worker-error.log" "$LOG_DIR/celery-beat-error.log" "$LOG_DIR/celery-watchdog-error.log"
                ;;
            *)
                echo "Usage: $0 logs {worker|beat|watchdog|errors}"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [worker|beat|watchdog|errors]}"
        exit 1
        ;;
esac
