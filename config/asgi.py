"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django ASGI application을 먼저 초기화
django_asgi_app = get_asgi_application()

# Channels imports
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import stocks.routing

# ASGI application 설정
application = ProtocolTypeRouter({
    # HTTP 요청은 Django로 처리
    "http": django_asgi_app,

    # WebSocket 요청 처리
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                stocks.routing.websocket_urlpatterns
            )
        )
    ),
})
