"""Phase 1.5 Translation Layer S4 — overview translations envelope 직렬화 검증.

검증:
  - 정상(senses 4키) → translations.senses 4키 + 메타
  - 부분(일부 키) → 있는 키만, 누락 카드는 빠짐
  - 행 없음 → translations null(미생성)
  - cards 블록 불변(회귀 가드 — translations 추가가 cards를 건드리지 않음)
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.briefing import BriefingLog
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)
from apps.market_pulse.models.translation import TranslationLog
from macro.models.indicators import MarketIndex, MarketIndexPrice

User = get_user_model()

_FULL_SENSES = {
    "regime": "강세장 후반부, 경계가 필요한 국면이에요.",
    "breadth": "오르는 종목이 더 많아 참여가 폭넓습니다.",
    "sector": "기술이 앞서고 유틸리티는 뒤처져 있어요.",
    "concentration": "상위 종목 쏠림이 다소 높은 편입니다.",
}


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="tr", email="tr@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def populated(db):
    # 카드 직렬화가 localdate() 기준 당일 행을 읽으므로 today=localdate()로 채운다.
    today = timezone.localdate()
    now = timezone.now()
    spy, _ = MarketIndex.objects.update_or_create(
        symbol="SPY",
        defaults={"name": "SPY", "sector_group": "BENCHMARK", "category": "us_equity"},
    )
    MarketIndexPrice.objects.update_or_create(
        index=spy, date=today, defaults={"close": Decimal("500"), "volume": 1000}
    )
    MarketIndexPrice.objects.update_or_create(
        index=spy, date=today - timedelta(days=1),
        defaults={"close": Decimal("490"), "volume": 1000},
    )
    xlk, _ = MarketIndex.objects.update_or_create(
        symbol="XLK",
        defaults={"name": "XLK", "sector_group": "TECH", "category": "sector"},
    )
    RegimeSnapshot.objects.create(
        date=today, snapshot_time=now, regime=RegimeSnapshot.Regime.BULL_EXPANSION,
        status=RegimeSnapshot.Status.OK, coverage=0.9, headline="strong",
        fired_rules=[], previous_regime="", hysteresis_streak=1,
    )
    BreadthSnapshot.objects.create(
        date=today, snapshot_time=now, universe="SPY",
        advance_count=320, decline_count=180, unchanged_count=3, total_count=503,
        new_high_52w=20, new_low_52w=5, ad_line=140, ad_line_change=140,
    )
    ConcentrationSnapshot.objects.create(
        date=today, snapshot_time=now, universe="SPY",
        top5_weight=Decimal("0.27"), top10_weight=Decimal("0.38"), hhi=Decimal("0.018"),
        top_holdings=[{"symbol": "NVDA", "weight": 0.07}],
    )
    SectorFlowSnapshot.objects.create(
        date=today, snapshot_time=now, market_index=xlk,
        rel_strength=Decimal("2.0"), momentum_1d=Decimal("1.0"),
        cross_dispersion=Decimal("0.8"), rotation_index=Decimal("1.5"), rank_in_universe=1,
    )
    BriefingLog.objects.create(
        date=today, model_version="gemini-2.5-flash",
        status=BriefingLog.Status.OK, headline="headline", body="content " * 30,
    )
    return today


def _get(auth_client):
    return auth_client.get(reverse("marketpulse_api_v2:overview")).json()


@pytest.mark.django_db
class TestTranslationsEnvelope:
    def test_full_senses(self, auth_client):
        TranslationLog.objects.create(
            date=date_cls(2026, 4, 27), model_version="gemini-2.5-flash",
            status=TranslationLog.Status.OK, senses=_FULL_SENSES,
            prompt_tokens=1000, completion_tokens=120,
        )
        data = _get(auth_client)
        tr = data["translations"]
        assert tr is not None
        assert set(tr["senses"].keys()) == {"regime", "breadth", "sector", "concentration"}
        assert tr["senses"]["regime"].startswith("강세장")
        assert tr["status"] == "OK"
        assert tr["model_version"] == "gemini-2.5-flash"
        assert tr["generated_at"]

    def test_partial_senses(self, auth_client):
        TranslationLog.objects.create(
            date=date_cls(2026, 4, 27), model_version="gemini-2.5-flash",
            status=TranslationLog.Status.OK,
            senses={"regime": _FULL_SENSES["regime"], "breadth": _FULL_SENSES["breadth"]},
        )
        tr = _get(auth_client)["translations"]
        assert set(tr["senses"].keys()) == {"regime", "breadth"}
        assert "sector" not in tr["senses"]

    def test_no_row_is_null(self, auth_client):
        """TranslationLog 미생성 → translations null(빈 dict 아님)."""
        data = _get(auth_client)
        assert data["translations"] is None

    def test_empty_senses_distinct_from_null(self, auth_client):
        """생성됐으나 0키(REFUSED) → 블록 존재 + senses={} (null과 구분)."""
        TranslationLog.objects.create(
            date=date_cls(2026, 4, 27), model_version="gemini-2.5-flash",
            status=TranslationLog.Status.REFUSED, senses={},
        )
        tr = _get(auth_client)["translations"]
        assert tr is not None
        assert tr["senses"] == {}
        assert tr["status"] == "REFUSED"


@pytest.mark.django_db
class TestCardsUnchangedGuard:
    """회귀 가드 — translations 추가가 cards 블록을 건드리지 않음."""

    def test_cards_block_intact_with_translations(self, auth_client, populated):
        TranslationLog.objects.create(
            date=populated, model_version="gemini-2.5-flash",
            status=TranslationLog.Status.OK, senses=_FULL_SENSES,
        )
        data = _get(auth_client)
        cards = data["cards"]
        assert set(cards.keys()) == {"regime", "breadth", "sector", "concentration", "brief"}
        assert cards["regime"]["regime"] == "BULL_EXPANSION"
        assert cards["breadth"]["advance"] == 320
        assert cards["concentration"]["top10_weight"] == pytest.approx(0.38)
        # translations는 cards 밖 동렬 블록.
        assert "translations" in data
        assert data["translations"]["senses"]["regime"]
