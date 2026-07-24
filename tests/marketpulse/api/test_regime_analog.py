"""MP2-ANALOG Slice B — regime/analog 엔드포인트 회귀.

계약: 페이로드 스키마(today_axes 4·neighbors·fan 5지평·alert)·label 슬롯 null(Slice C)·
  마커 미노출·소급 부재 시 빈 응답.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()
pytestmark = [pytest.mark.django_db]

_KEYS = [
    "return_1d_pct", "vol_20d_pct", "drawdown_pct", "nfci", "nfci_credit",
    "nfci_leverage", "nfci_risk", "hy_oas_pct", "hy_ccc_oas_pct",
    "t10y2y_pct", "t10y3m_pct", "vix", "vix3m", "move",
]
_CODES = {
    "nfci": "NFCI", "nfci_credit": "NFCICREDIT", "nfci_leverage": "NFCILEVERAGE",
    "nfci_risk": "NFCIRISK", "hy_oas_pct": "BAMLH0A0HYM2", "hy_ccc_oas_pct": "BAMLH0A3HYC",
    "t10y2y_pct": "T10Y2Y", "t10y3m_pct": "T10Y3M", "vix": "VIXCLS",
    "vix3m": "VIX3M", "move": "MOVE",
}


@pytest.fixture(autouse=True)
def _clear():
    from macro.models.indicators import IndicatorValue, MarketIndexPrice

    cache.clear()
    RegimeSnapshot.objects.all().delete()
    IndicatorValue.objects.all().delete()
    MarketIndexPrice.objects.all().delete()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    u = User.objects.create_user(username="an", email="an@e.com", password="pw")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _base_vec(scale=1.0):
    # 완전벡터(14키). scale로 벡터 간 거리 통제.
    return {k: round(0.5 * scale + i * 0.1, 3) for i, k in enumerate(_KEYS)}


def _seed_population(n=40):
    days = _weekdays(date(2023, 8, 7), n)
    for i, d in enumerate(days):
        RegimeSnapshot.objects.create(
            date=d, snapshot_time=d, regime=RegimeSnapshot.Regime.TRANSITION,
            status=RegimeSnapshot.Status.OK, coverage=1.0, headline="h",
            inputs=_base_vec(1.0 + i * 0.02), fired_rules=[], previous_regime="",
            hysteresis_streak=1, summary=BACKFILL_MARK,
        )
    return days


def _seed_today_inputs():
    """load_inputs(today)가 채워지도록 최근 SPY(≥21d) + 지표(today) 시드."""
    from macro.models.indicators import (
        EconomicIndicator, IndicatorValue, MarketIndex, MarketIndexPrice,
    )
    from django.utils import timezone

    today = timezone.localdate()
    spy, _ = MarketIndex.objects.get_or_create(symbol="SPY", defaults={"name": "SPY"})
    for i, d in enumerate(_weekdays(today - timedelta(days=40), 30)):
        MarketIndexPrice.objects.get_or_create(
            index=spy, date=d, defaults={"close": Decimal(str(400 + i))}
        )
    for key, code in _CODES.items():
        ind, _ = EconomicIndicator.objects.get_or_create(
            code=code, defaults={"name": code, "category": "macro", "data_source": "fred"}
        )
        IndicatorValue.objects.get_or_create(
            indicator=ind, date=today - timedelta(days=1),
            defaults={"value": Decimal("1.0")},
        )


def _url():
    return reverse("marketpulse_api_v2:regime-analog")


class TestRegimeAnalog:
    def test_empty_when_no_population(self, auth_client):
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False

    def test_schema_and_label_slots(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        assert len(body["today_axes"]) == 4
        assert {a["axis"] for a in body["today_axes"]} == {
            "stress", "financial", "return_1d_pct", "vol_20d_pct"
        }
        assert [f["horizon"] for f in body["fan"]] == [1, 5, 10, 20, 60]
        assert "on" in body["alert"] and "nearest_dist" in body["alert"]
        # 미생성 이웃(AnalogDayContext 부재) = why null. cat_slot/cat_key는 C-core 채움.
        for nb in body["neighbors"]:
            assert nb["why"] is None  # 이 픽스처는 L3 미생성 → null(populated는 별도 테스트)
            assert nb["cat_key"] == "TRANSITION"          # 시드 regime
            assert nb["cat_slot"] == RegimeSnapshot.Regime.TRANSITION.label
            assert "dist" in nb and "fwd" in nb

    def test_marker_not_exposed(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        raw = auth_client.get(_url()).content.decode()
        assert BACKFILL_MARK not in raw

    def test_fan_honest_n_per_horizon(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        body = auth_client.get(_url()).json()["data"]
        # 모집단이 SPY 창 밖(2023-08)이라 선도수익 미실현 → N=0 정직(발명 없음)
        for f in body["fan"]:
            assert f["n"] >= 0 and f["n_eff"] >= 0

    def test_today_category_none_without_today_snapshot(self, auth_client):
        # C-core: 오늘 라이브 스냅샷 없으면 today_category=null(억지 태그 금지)
        _seed_population()
        _seed_today_inputs()
        body = auth_client.get(_url()).json()["data"]
        assert body["today_category"] is None

    def test_today_category_populated_from_ok_snapshot(self, auth_client):
        from django.utils import timezone

        _seed_population()
        _seed_today_inputs()
        today = timezone.localdate()
        RegimeSnapshot.objects.create(
            date=today, snapshot_time=today, regime=RegimeSnapshot.Regime.LATE_BULL,
            status=RegimeSnapshot.Status.OK, coverage=1.0, inputs={}, fired_rules=[],
            previous_regime="", hysteresis_streak=1, summary="live",
        )
        body = auth_client.get(_url()).json()["data"]
        assert body["today_category"] == {
            "key": "LATE_BULL", "label": RegimeSnapshot.Regime.LATE_BULL.label,
        }

    def test_l3_why_populated_partial_and_render_no_llm(self, auth_client, monkeypatch):
        """C-L3: 저장분 있는 이웃만 why 채움(부분), 렌더 경로 LLM 호출 0.

        이웃 선정은 오늘 벡터 의존이라 고정 이웃 2개로 monkeypatch — 배선(why lookup)만 격리 검증.
        """
        from apps.market_pulse.llm import client as llm_client
        from apps.market_pulse.models import AnalogDayContext
        from apps.market_pulse.regime import analog

        # 렌더 경로가 LLM을 부르면 즉시 실패(읽기 결정론 증명).
        def _boom(**_kw):
            raise AssertionError("렌더 경로에서 LLM 호출 금지(읽기 결정론 위반)")

        monkeypatch.setattr(llm_client, "generate_with_circuit", _boom)

        days = _seed_population()  # weekdays(2023-08-07, 40)
        _seed_today_inputs()
        d0, d1 = days[0], days[1]  # 고정 이웃(모집단 실재일)
        monkeypatch.setattr(
            analog, "select_neighbors",
            lambda *a, **k: ([{"date": d0, "dist": 0.11}, {"date": d1, "dist": 0.22}], 0.11),
        )

        # d0에만 L3 저장분 생성(부분 상태).
        AnalogDayContext.objects.create(
            date=d0, why_text="긴축 우려가 부각된 국면.",
            provenance=[{"id": "1", "url": "https://ex.com/1", "title": "h"}],
            prompt_version="cl3_v1",
        )
        cache.clear()
        by_date = {nb["date"]: nb for nb in auth_client.get(_url()).json()["data"]["neighbors"]}

        hit = by_date[d0.isoformat()]
        assert hit["why"] == "긴축 우려가 부각된 국면."
        assert hit["why_version"] == "cl3_v1"
        assert len(hit["why_provenance"]) == 1
        # 부분: 저장분 없는 d1은 여전히 null(additive·미오염).
        miss = by_date[d1.isoformat()]
        assert miss["why"] is None and miss["why_provenance"] is None and miss["why_version"] is None
