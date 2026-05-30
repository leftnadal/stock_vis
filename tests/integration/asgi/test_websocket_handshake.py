"""C-3 영구 ASGI 회귀 게이트.

Django 5.2 LTS 위에서 channels consumer가 정상 핸드셰이크함을 회귀가
자동으로 보증. channels/daphne 버전을 그대로 유지한다는 C-3 결정 ②의
영구 게이트.

내용:
1. StockPriceConsumer: 무인증, ws/stock/<symbol>/ 핸드셰이크 + ping/pong
   round-trip + 정상 disconnect.
2. PortfolioConsumer: 인증 필요. 익명 사용자 접속 시 close 확정.

테스트 격리:
- CHANNEL_LAYERS를 InMemoryChannelLayer로 override (운영 RedisChannelLayer는
  테스트 환경에서 미가동).
- StockPriceConsumer.send_current_price는 Stock 모델 조회 결과 None 시 송신
  스킵 — 핸드셰이크 자체는 영향 없음.
"""
from __future__ import annotations

import json

import pytest
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from config.asgi import application

_INMEMORY_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=_INMEMORY_LAYERS)
async def test_stock_consumer_handshake_and_ping_pong():
    """StockPriceConsumer: 핸드셰이크 + ping/pong round-trip + disconnect.

    채널 그룹 등록(group_add)이 InMemoryChannelLayer에서 정상 동작해야
    accept()가 반환된다. accept 이후 send_current_price가 호출되지만
    Stock 모델 미존재 시 None 분기로 송신 스킵.
    """
    communicator = WebsocketCommunicator(application, "/ws/stock/TESTSYM/")
    connected, _subprotocol = await communicator.connect()
    try:
        assert connected is True, "stock consumer handshake should succeed"

        # ping → pong round-trip
        await communicator.send_to(
            text_data=json.dumps({"type": "ping", "timestamp": 1234567890})
        )
        response = await communicator.receive_from(timeout=5)
        payload = json.loads(response)
        # 핸드셰이크 직후 current_price를 먼저 보낼 수도 있으므로 pong만 도달할 때까지 1회 추가 수신 허용.
        if payload.get("type") != "pong":
            response = await communicator.receive_from(timeout=5)
            payload = json.loads(response)
        assert payload.get("type") == "pong"
        assert payload.get("timestamp") == 1234567890
    finally:
        await communicator.disconnect()


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=_INMEMORY_LAYERS)
async def test_portfolio_consumer_rejects_anonymous():
    """PortfolioConsumer: 익명 사용자는 connect 즉시 close.

    `self.user.is_authenticated`가 False이면 consumer가 self.close()를 호출.
    WebsocketCommunicator.connect()는 (False, close_code)를 반환.
    """
    communicator = WebsocketCommunicator(application, "/ws/portfolio/")
    connected, _ = await communicator.connect()
    try:
        assert connected is False, "portfolio consumer must reject anonymous user"
    finally:
        await communicator.disconnect()
