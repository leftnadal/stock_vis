"""Django SMTP 설정을 재사용하는 메일 발송 (야간 에이전트 공통).

dogfood의 `report_mail.send`를 그대로 옮긴 것. healthcheck가 같은 코드를 복제하는
대신 여기서 가져다 쓴다(복제 = drift).
"""

from __future__ import annotations

import os

DEFAULT_TO = os.getenv("AGENT_MAIL_TO", "jinie545@gmail.com")


def send(subject: str, body: str, to: str = DEFAULT_TO) -> int:
    """Django SMTP 설정 재사용. 값은 절대 출력하지 않는다."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from django.conf import settings
    from django.core.mail import send_mail

    return send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )
