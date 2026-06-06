"""
MarketpulseConfig — 앱 부트 + shared VIX 포트 구현체 등록(BOUNDARY-3).

소속: apps/market_pulse (app 레이어 root, AppConfig).
역할:
  - app label='marketpulse' (PR4 monorepo 이동에도 reverse url 등 호환 위해 불변).
  - ready()에서 `register_vix_provider(MacroVIXProvider())` — packages/shared의 VIX
    포트(`vix_provider.py`)에 구체 구현체를 주입.
왜(BOUNDARY-3 의존 역전): shared가 macro·apps를 거꾸로 import하면 단방향 경계
  위반. shared는 포트(VIXProvider)만 알고, 구현체는 app 쪽에서 등록 패턴으로 채운다 —
  그래야 shared 코드가 market_pulse를 아예 모르는 채로(import도 안 한 채로) VIX를
  쓸 수 있다. 모델 이동·마이그레이션 없이 의존 방향만 뒤집은 청소.
주의: ready()는 Django app 로딩 1회만 실행. register는 idempotent하나 ready 다중 호출
  환경에서도 마지막 구현체가 active.
"""
from django.apps import AppConfig


class MarketpulseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.market_pulse"
    label = "marketpulse"
    verbose_name = "Market Pulse v2"

    def ready(self) -> None:
        from apps.market_pulse.services.macro_vix_provider import MacroVIXProvider
        from packages.shared.stocks.services.vix_provider import (
            register_vix_provider,
        )

        register_vix_provider(MacroVIXProvider())
