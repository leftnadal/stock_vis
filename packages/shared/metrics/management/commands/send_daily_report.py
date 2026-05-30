"""
Daily Report Email — 매일 아침 메트릭 리포트 발송.

Usage:
    python manage.py send_daily_report
    python manage.py send_daily_report --dry-run   # 메일 안 보내고 콘솔 출력만
    python manage.py send_daily_report --to email@example.com  # 수신자 override
"""

import logging
from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from packages.shared.metrics.services.daily_report import build_report_payload

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Stock-Vis 일일 리포트 생성 + 이메일 발송"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="발송하지 않고 HTML/요약만 출력"
        )
        parser.add_argument(
            "--to",
            type=str,
            default=None,
            help="수신자 override (기본: REPORT_RECIPIENT_EMAIL)",
        )
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="리포트 기준 날짜 (YYYY-MM-DD, 기본: 오늘 KST)",
        )

    def handle(self, *args, **options):
        # KST 기준 today
        now_local = timezone.localtime()
        if options["date"]:
            from datetime import datetime as dt

            today = dt.strptime(options["date"], "%Y-%m-%d").date()
        else:
            today = now_local.date()

        self.stdout.write(self.style.NOTICE(f"📊 Daily report 생성: {today}"))
        payload = build_report_payload(today)

        self.stdout.write(
            f"  ─ Graph: nodes={payload['graph']['total_nodes']}, rels={payload['graph']['total_relations']}"
        )
        self.stdout.write(
            f"  ─ News: today_new={payload['news']['today_new']}, llm_pct={payload['news']['today_llm_analyzed_pct']}%"
        )
        self.stdout.write(f"  ─ Suggestions: {len(payload['suggestions'])}건")
        self.stdout.write(
            f"  ─ Health: worker={'OK' if payload['health']['celery_worker_alive'] else 'DOWN'}, "
            f"neo4j={'OK' if payload['health']['neo4j_alive'] else 'DOWN'}"
        )

        # HTML 렌더링
        html_body = render_to_string("email/daily_report.html", {"payload": payload})

        # 텍스트 fallback
        red_count = sum(1 for s in payload["suggestions"] if "🔴" in s["severity"])
        yel_count = sum(1 for s in payload["suggestions"] if "🟡" in s["severity"])
        grn_count = sum(1 for s in payload["suggestions"] if "🟢" in s["severity"])

        text_body = (
            f"Stock-Vis Daily Report — {today}\n"
            f"{'=' * 50}\n\n"
            f"노드: {payload['graph']['total_nodes']}, 관계: {payload['graph']['total_relations']}\n"
            f"24h 뉴스 신규: {payload['news']['today_new']} (LLM 분석률 {payload['news']['today_llm_analyzed_pct']}%)\n\n"
            f"개선방향: 🔴 {red_count} / 🟡 {yel_count} / 🟢 {grn_count}\n\n"
            f"전체 내용은 HTML 본문 참조 (Gmail/Apple Mail에서 자동 렌더링).\n"
        )

        recipient = (
            options["to"]
            or getattr(settings, "REPORT_RECIPIENT_EMAIL", None)
            or settings.EMAIL_HOST_USER
        )
        if not recipient:
            self.stderr.write(
                self.style.ERROR("수신자 미설정 (REPORT_RECIPIENT_EMAIL or --to)")
            )
            return

        subject = f"[Stock-Vis] {today} 일일 리포트 — 노드 {payload['graph']['total_nodes']:,} / 24h 뉴스 {payload['news']['today_new']}"

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"--dry-run 모드: 메일 발송 안 함"))
            self.stdout.write(f"수신자: {recipient}")
            self.stdout.write(f"제목: {subject}")
            self.stdout.write(f"HTML 길이: {len(html_body)} bytes")
            # 첫 500자 미리보기
            self.stdout.write(f"\n--- HTML preview (앞 500자) ---")
            self.stdout.write(html_body[:500])
            return

        # 발송
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html_body, "text/html")

        try:
            msg.send(fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f"✓ 메일 발송 완료 → {recipient}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"발송 실패: {type(e).__name__}: {e}"))
            raise
