#!/bin/bash
# runtime-check.sh — runtime_check.py(read-only 감지) 실행 + 알림 래퍼 (RB-1)
#
# LaunchAgent(com.stockvis.runtime-check)에서 1시간(3600초) 간격 실행.
# 이 래퍼는 **감지하지 않는다** — 판정은 전적으로 runtime_check.py(단일 출처). 여기서는
# 종료 코드만 보고 알림을 결정한다(집행 없음: kill·kickstart·checkout 절대 안 함).
#
#   exit 0 = 전부 OK      → 무알림(로그만)
#   exit 1 = WARN 존재    → 데스크탑 알림만(24h 드리프트 등 — health_check가 표면화)
#   exit 2 = ERROR/ORPHAN → 메일 + 데스크탑 알림(관리이탈 고아 등 즉시 개입 필요)
#
# 알림 인프라 = celery-watchdog.sh 패턴 재사용(Gmail SMTP via Django send_mail).
# 신규 외부 의존 도입 없음.

set +e  # 개별 실패가 래퍼를 죽이지 않도록

# 런타임 트리에서 Django 컨텍스트 로드(Desktop 무접촉). .env는 심링크(→ 공유 .env).
PROJECT_DIR="/Users/byeongjinjeong/worktrees/sv-worker-runtime"
API_TREE="/Users/byeongjinjeong/worktrees/sv-api-runtime"
VENV_DIR="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12"
DJANGO_SETTINGS="${DJANGO_SETTINGS_MODULE:-config.settings}"

# .env 로드(EMAIL_HOST_USER 등)
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_DIR/.env"
    set +a
fi
ALERT_RECIPIENT="${EMAIL_HOST_USER:-jinie545@gmail.com}"

notify_desktop() {
    osascript -e "display notification \"$2\" with title \"$1\" sound name \"Crystal\"" 2>/dev/null || true
}

notify_mail() {
    local subject="$1" body="$2"
    cd "$PROJECT_DIR" || return 1
    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS"
    "$VENV_DIR/bin/python" - "$subject" "$body" "$ALERT_RECIPIENT" <<'PY' 2>&1 | tail -3
import sys, django
django.setup()
from django.core.mail import send_mail
from django.conf import settings
subject, body, recipient = sys.argv[1], sys.argv[2], sys.argv[3]
send_mail(
    subject=f'[Stock-Vis Runtime] {subject}',
    message=body,
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[recipient],
    fail_silently=False,
)
print(f'mail sent ok -> {recipient}')
PY
}

# ── 감지 실행 (read-only) — runtime_check.py 사본은 api 런타임 트리(origin/main 정합) ──
# 을 우선 사용(#47 stale 사본 방지). 없으면 worker 트리.
if [ -f "$API_TREE/scripts/runtime_check.py" ]; then
    RC_TREE="$API_TREE"
else
    RC_TREE="$PROJECT_DIR"
fi

OUT="$("$VENV_DIR/bin/python" "$RC_TREE/scripts/runtime_check.py" 2>&1)"
CODE=$?
echo "$OUT"

case "$CODE" in
    0)
        : # 전부 OK — 무알림(runtime_check.log에만 기록)
        ;;
    1)
        notify_desktop "Stock-Vis 런타임 WARN" "runtime_check WARN — health_check 표면화 확인"
        ;;
    *)
        # ERROR/ORPHAN 또는 예외
        SUMMARY="$(echo "$OUT" | grep -E '❌|ORPHAN' | head -5)"
        notify_mail "런타임 ERROR 감지 (code=$CODE)" "runtime_check 이상 감지 — 집행은 사람(런북 docs/runbook/DEPLOY.md 1장 고아 스윕 절차):

$SUMMARY

전문 로그: ~/Library/Logs/stockvis/runtime_check.log"
        notify_desktop "Stock-Vis 런타임 ERROR" "메일 발송됨 — 런북 1장 참조(집행=사람)"
        ;;
esac

exit "$CODE"
