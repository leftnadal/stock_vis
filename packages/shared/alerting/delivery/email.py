"""EmailProvider — 이메일 전달 구현체.

metrics daily report 선례 동형(EmailMultiAlternatives + DEFAULT_FROM_EMAIL). 발송은
with_circuit로 감싸 named CB(`alert_email`)로 보호(연속 실패 시 open → 폭주 차단).
EMAIL_BACKEND 스마트 스위치(settings)라 dev는 console, prod는 smtp(값 무관).
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from packages.shared.alerting.delivery.base import DeliveryProvider
from packages.shared.llm.policy.circuit import with_circuit


class EmailProvider(DeliveryProvider):
    def deliver(
        self, *, subject: str, text_body: str, html_body: str, destination: str
    ) -> None:
        def _send() -> int:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destination],
            )
            if html_body:
                msg.attach_alternative(html_body, "text/html")
            return msg.send(fail_silently=False)

        with_circuit(_send, name="alert_email")
