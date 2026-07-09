"""
유니버스 갱신 + 감시 태스크 (TH-6) — TH-UNIVERSE-REFRESH-ALERT.

- refresh_sp500_universe_task: Wikipedia 소스(결정9 B) → 검증 가드 → 비파괴 sync.
  가드 위반·예외 → 알림.
- monitor_universe_staleness_task: 주간 신선도 감시(>7일 경고, >30일 stale=결정8).

알림 정본(STEP 0-5): chainsight 전용 채널 없음 → **ERROR 로그 + 상태 기록 + send_mail
best-effort**(serverless 관례 재사용, 실패해도 태스크 진행). 새 알림 인프라 발명 금지.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _alert(subject: str, body: str) -> None:
    """ERROR 로그(정본) + send_mail best-effort. 메일 실패는 격리(로그가 정본)."""
    logger.error("[UNIVERSE-ALERT] %s — %s", subject, body)
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        recipient = getattr(settings, "OPS_ALERT_EMAIL", None) or getattr(
            settings, "DEFAULT_FROM_EMAIL", None
        )
        if recipient:
            send_mail(
                subject=f"[stock-vis] {subject}",
                message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient],
                fail_silently=True,
            )
    except Exception as e:  # noqa: BLE001 — 메일 실패 격리
        logger.warning("[UNIVERSE-ALERT] 메일 발송 실패(격리): %s", e)


@shared_task(
    name="chainsight-refresh-sp500-universe",
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def refresh_sp500_universe_task(self):
    """
    주 1회 유니버스 갱신 (Wikipedia → 가드 → 비파괴 sync). 가드 위반·예외 → 알림.
    멱등(같은 응답 2회 = 무변화). 성공 시 updated_at 신선 → universe_stale 자연 해제.
    """
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from packages.shared.stocks.services.sp500_service import SP500Service

    try:
        result = SP500Service().sync_constituents()
    except Exception as exc:  # noqa: BLE001
        _alert("유니버스 갱신 실패(예외)", f"{type(exc).__name__}: {exc}")
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    if result.get("guard_violation"):
        _alert("유니버스 갱신 가드 위반 — DB 무접촉",
               f"reason={result['guard_violation']} total={result.get('total')}")
        return result

    logger.info("유니버스 갱신 완료: %s", result)
    return result


@shared_task(
    name="chainsight-monitor-universe-staleness",
    bind=True,
    max_retries=1,
    soft_time_limit=120,
)
def monitor_universe_staleness_task(self):
    """주간 유니버스 신선도 감시 — >7일 경고 알림, >30일 stale(결정8)."""
    from django import db

    db.connections.close_all()

    from apps.chain_sight.services.universe_refresh import universe_staleness_status

    status = universe_staleness_status(timezone.now().date())
    if status["warn"]:
        level = "STALE(>30d)" if status["stale"] else "WARN(>7d)"
        _alert(
            f"유니버스 신선도 {level}",
            f"last_updated={status['last_updated']} days_since={status['days_since']} "
            f"— 갱신 소스 점검 필요(chainsight-refresh-sp500-universe).",
        )
    else:
        logger.info("유니버스 신선도 정상: %s", status)
    return status
