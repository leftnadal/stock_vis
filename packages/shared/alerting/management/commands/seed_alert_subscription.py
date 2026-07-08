"""알림 구독 시드 커맨드(병진 수동 실행용).

수신 주소는 코드·지시서에 박지 않는다 — `--email` 인자로만 주입.
멱등: 동일 (source_app, event_type, channel, destination) 재실행 시 중복 생성 없음.

Usage:
    python manage.py seed_alert_subscription --email you@example.com
    python manage.py seed_alert_subscription --email you@example.com \
        --source-app market_pulse --event-type regime_transition
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from packages.shared.alerting.models import AlertSubscription


class Command(BaseCommand):
    help = "알림 구독 1건 시드(멱등). 수신 주소는 --email로만 주입."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True, help="수신 이메일 주소")
        parser.add_argument("--source-app", default="market_pulse")
        parser.add_argument("--event-type", default="regime_transition")
        parser.add_argument("--channel", default="email")

    def handle(self, *args, **opts) -> None:
        sub, created = AlertSubscription.objects.get_or_create(
            source_app=opts["source_app"],
            event_type=opts["event_type"],
            channel=opts["channel"],
            destination=opts["email"],
            defaults={"enabled": True},
        )
        verb = "생성" if created else "이미 존재"
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ 구독 {verb}: {sub.source_app}:{sub.event_type} "
                f"→ {sub.channel} (id={sub.pk}, enabled={sub.enabled})"
            )
        )
