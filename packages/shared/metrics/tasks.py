"""Metrics Celery tasks.

- send_daily_report_task: 매일 아침 KST 07:00 발송 (통합 daily report)
- send_agent_report_task: Phase 1 (2026-05-22) — 도메인별 4통 분리 발송
    @data 06:00 / @backend 06:15 / @qa 06:30 / @design 06:45 KST
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

    from packages.shared.metrics.services.daily_report import build_report_payload

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
            f"{'=' * 50}\n\n"
            f"노드: {payload['graph']['total_nodes']}, 관계: {payload['graph']['total_relations']}\n"
            f"24h 뉴스 퍼널: N{payload['news']['funnel']['n_today_new']}"
            f"→M{payload['news']['funnel']['m_score_recorded']}"
            f"→K{payload['news']['funnel']['k_tier_a_pass']}"
            f"→J{payload['news']['funnel']['j_deep_analyzed']}"
            f" (실행 건강 "
            f"{payload['news']['funnel']['execution_health_pct'] if payload['news']['funnel']['execution_health_pct'] is not None else 'N/A'}"
            f"{'%' if payload['news']['funnel']['execution_health_pct'] is not None else ''})\n\n"
            f"개선방향: 🔴 {red} / 🟡 {yel} / 🟢 {grn}\n\n"
            f"HTML 본문에서 전체 내용 확인.\n"
        )

        recipient = (
            getattr(settings, "REPORT_RECIPIENT_EMAIL", "") or settings.EMAIL_HOST_USER
        )
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

        # Archive 사본 — 메일 발송과 독립(best-effort). 실패해도 메일 영향 없음.
        try:
            from packages.shared.metrics.services.daily_report import save_mail_archive

            archive_path = save_mail_archive(payload)
            logger.info(f"daily report archived → {archive_path}")
        except Exception as arch_exc:
            logger.warning(f"daily report archive failed (메일 발송은 성공): {arch_exc}")
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


# ─── Phase 1: Agent별 도메인 분리 보고서 ────────────────────────────────

AGENT_DOMAINS = ("data", "backend", "qa", "design")


@shared_task(
    bind=True,
    name="metrics.tasks.send_agent_report_task",
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=300,
    time_limit=360,
)
def send_agent_report_task(self, domain: str):
    """도메인별 일일 보고서 발송. domain ∈ {data, backend, qa, design}."""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils import timezone

    from packages.shared.metrics.services.agent_reports import BUILDERS

    if domain not in BUILDERS:
        logger.error(f"send_agent_report_task: unknown domain={domain}")
        return {"status": "error", "reason": "unknown_domain", "domain": domain}

    today = timezone.localtime().date()
    logger.info(f"send_agent_report_task[{domain}]: building for {today}")

    try:
        payload = BUILDERS[domain](today)
        html_body = render_to_string("email/agent_report.html", {"payload": payload})

        # 텍스트 본문 — TL;DR 위주
        tldr_text = "\n".join(f"- {line}" for line in payload.get("tldr", []))
        text_body = (
            f"Stock-Vis {payload['domain_label']} — {today}\n"
            f"{'=' * 50}\n\n"
            f"{tldr_text}\n\n"
            f"HTML 본문에서 전체 audit 내용 확인.\n"
        )

        recipient = (
            getattr(settings, "REPORT_RECIPIENT_EMAIL", "") or settings.EMAIL_HOST_USER
        )
        if not recipient:
            logger.error("REPORT_RECIPIENT_EMAIL 미설정")
            return {"status": "skipped", "reason": "no_recipient"}

        subject = f"[Stock-Vis {payload['domain_label']}] {today} 도메인 보고서"

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

        logger.info(f"agent report[{domain}] sent → {recipient}")
        return {
            "status": "sent",
            "domain": domain,
            "recipient": recipient,
            "tldr_count": len(payload.get("tldr", [])),
        }
    except Exception as exc:
        logger.exception(f"send_agent_report_task[{domain}] failed: {exc}")
        raise self.retry(exc=exc)
