"""Metrics Celery tasks.

- send_daily_report_task: 매일 아침 KST 07:00 발송
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="metrics.tasks.send_daily_report_task",
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=300,
    time_limit=360,
)
def send_daily_report_task(self):
    """Daily report 생성 + 메일 발송. 매일 KST 07:00."""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils import timezone

    from metrics.services.daily_report import build_report_payload

    today = timezone.localtime().date()
    logger.info(f"send_daily_report_task: building for {today}")

    try:
        payload = build_report_payload(today)

        html_body = render_to_string("email/daily_report.html", {"payload": payload})

        red = sum(1 for s in payload["suggestions"] if "🔴" in s["severity"])
        yel = sum(1 for s in payload["suggestions"] if "🟡" in s["severity"])
        grn = sum(1 for s in payload["suggestions"] if "🟢" in s["severity"])

        text_body = (
            f"Stock-Vis Daily Report — {today}\n"
            f"{'='*50}\n\n"
            f"노드: {payload['graph']['total_nodes']}, 관계: {payload['graph']['total_relations']}\n"
            f"24h 뉴스: {payload['news']['today_new']} (LLM 분석률 {payload['news']['today_llm_analyzed_pct']}%)\n\n"
            f"개선방향: 🔴 {red} / 🟡 {yel} / 🟢 {grn}\n\n"
            f"HTML 본문에서 전체 내용 확인.\n"
        )

        recipient = getattr(settings, "REPORT_RECIPIENT_EMAIL", "") or settings.EMAIL_HOST_USER
        if not recipient:
            logger.error("REPORT_RECIPIENT_EMAIL 미설정")
            return {"status": "skipped", "reason": "no_recipient"}

        subject = (
            f"[Stock-Vis] {today} 일일 리포트 — "
            f"노드 {payload['graph']['total_nodes']:,} / 24h 뉴스 {payload['news']['today_new']}"
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

        logger.info(f"daily report sent → {recipient}")
        return {
            "status": "sent",
            "recipient": recipient,
            "nodes": payload["graph"]["total_nodes"],
            "relations": payload["graph"]["total_relations"],
            "suggestions": {"red": red, "yel": yel, "grn": grn},
        }
    except Exception as exc:
        logger.exception(f"send_daily_report_task failed: {exc}")
        raise self.retry(exc=exc)
