"""P2a-1 — EtfNavHistory upsert 멱등성 · 디스카운트 compute-on-read · 부호 규약 ·
콜드스타트 · 원장 누적 · resolve 괴리 skip · 기존 8키 무영향(회귀)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.credit_signals.constants import (
    DERIVED_SIGNAL_MAP,
    ETF_DISCOUNT_MAP,
    SIGNAL_SERIES_MAP,
)
from apps.credit_signals.models import CreditSignalState, EtfNavHistory, MacroSeriesHistory
from apps.credit_signals.services.etf_nav_service import (
    resolve_and_upsert_one,
    upsert_etf_nav,
)
from apps.credit_signals.services.signal_service import (
    compute_all_signals,
    compute_etf_discount_signal,
)

_D = lambda x: Decimal(str(x))


def _seed_nav(symbol, discounts, start=date(2026, 1, 1)):
    """discount d → nav=100, price=100−d (discount=(nav−price)/nav×100)."""
    for i, d in enumerate(discounts):
        EtfNavHistory.objects.create(
            symbol=symbol, date=start + timedelta(days=i),
            nav=_D("100.0000"), price=(_D("100") - _D(d)).quantize(_D("0.0001")),
        )


# 60관측 MAD>floor 보장 베이스라인(0.0/0.2 교대) 59개.
_BASE59 = ([0.0, 0.2] * 30)[:59]


@pytest.mark.django_db
class TestUpsertEtfNav:
    def test_insert_then_idempotent(self):
        assert upsert_etf_nav("HYG", date(2026, 7, 17), _D("79.63"), _D("79.65")) == "created"
        # 동일 값 재수집 → no-op
        assert upsert_etf_nav("HYG", date(2026, 7, 17), _D("79.63"), _D("79.65")) == "skipped"
        assert EtfNavHistory.objects.filter(symbol="HYG").count() == 1

    def test_revise_updates_and_stamps(self):
        upsert_etf_nav("HYG", date(2026, 7, 17), _D("79.63"), _D("79.65"))
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 7, 17))
        assert row.revised_at is None
        original_ingested = row.ingested_at
        assert upsert_etf_nav("HYG", date(2026, 7, 17), _D("79.70"), _D("79.68")) == "updated"
        row.refresh_from_db()
        assert row.nav == _D("79.70") and row.price == _D("79.68")
        assert row.revised_at is not None
        assert row.ingested_at == original_ingested  # 유지


@pytest.mark.django_db
class TestComputeEtfDiscount:
    def test_value_formula_and_as_of(self):
        """단일 관측: value=(nav−price)/nav×100(4dp), as_of=최신일, 콜드스타트 gray."""
        EtfNavHistory.objects.create(
            symbol="HYG", date=date(2026, 7, 17), nav=_D("79.63"), price=_D("79.65")
        )
        state = compute_etf_discount_signal("HYG_NAV_DISCOUNT")
        assert state is not None
        assert state.as_of == date(2026, 7, 17)
        # (79.63−79.65)/79.63×100 = −0.0251…  → 4dp
        assert state.value == _D("-0.0251")
        assert state.z_score is None and state.grade == "gray"  # 1관측 = 콜드스타트

    def test_discount_stress_escalates_positive_z(self):
        """디스카운트(price<nav) 이상치 → 양의 z → 상향(부호 규약 B)."""
        _seed_nav("HYG", _BASE59 + [5.0])  # 마지막 = 큰 디스카운트
        state = compute_etf_discount_signal("HYG_NAV_DISCOUNT")
        assert float(state.z_score) > 2.0
        assert state.grade == "orange"
        assert state.value == _D("5.0000")

    def test_premium_does_not_escalate_negative_z(self):
        """프리미엄(price>nav = 음의 디스카운트) 이상치 → 음의 z → gray(미상향)."""
        _seed_nav("HYG", _BASE59 + [-5.0])  # 마지막 = 큰 프리미엄
        state = compute_etf_discount_signal("HYG_NAV_DISCOUNT")
        assert float(state.z_score) < -2.0
        assert state.grade == "gray"

    def test_cold_start_gray(self):
        """60관측 미만 → z=null, grade=gray (기존 계약 재사용)."""
        _seed_nav("LQD", [0.1] * 30)
        state = compute_etf_discount_signal("LQD_NAV_DISCOUNT")
        assert state.z_score is None and state.grade == "gray"

    def test_none_when_ledger_empty(self):
        assert compute_etf_discount_signal("HYG_NAV_DISCOUNT") is None
        assert not CreditSignalState.objects.filter(signal_key="HYG_NAV_DISCOUNT").exists()

    def test_ledger_accumulates_and_recomputes(self):
        """3거래일 누적 → 원장 3행, as_of=최신, 값 재현."""
        for i, (d, day) in enumerate([("0.10", 1), ("0.20", 2), ("0.30", 3)]):
            upsert_etf_nav("HYG", date(2026, 7, day), _D("100"), _D("100") - _D(d))
        assert EtfNavHistory.objects.filter(symbol="HYG").count() == 3
        state = compute_etf_discount_signal("HYG_NAV_DISCOUNT")
        assert state.as_of == date(2026, 7, 3)
        assert state.value == _D("0.3000")  # 최신 디스카운트
        assert state.detail["n_obs"] == 3


class _FakeClient:
    def __init__(self, quote, info):
        self._quote, self._info = quote, info

    def get_quote(self, symbol):
        return self._quote

    def get_etf_info(self, symbol):
        return self._info


# 2026-07-17 16:00 ET(금 종가) epoch.
_TS_FRI_0717 = 1784318400


@pytest.mark.django_db
class TestResolveAndUpsert:
    def test_accept_within_lag(self):
        """정본 거래일(금 07-17) vs nav updatedAt(일 07-19, 1영업일) → upsert."""
        client = _FakeClient(
            quote={"symbol": "HYG", "price": 79.65, "timestamp": _TS_FRI_0717},
            info={"symbol": "HYG", "nav": 79.63, "updatedAt": "2026-07-20T02:16:00Z"},
        )
        r = resolve_and_upsert_one(client, "HYG")
        assert r["result"] == "created"
        assert r["trading_day"] == "2026-07-17"
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 7, 17)).exists()

    def test_skip_when_nav_lag_exceeds(self):
        """nav updatedAt이 정본 거래일과 1영업일 초과 괴리 → skip + 원장 미기록."""
        client = _FakeClient(
            quote={"symbol": "HYG", "price": 79.65, "timestamp": _TS_FRI_0717},
            info={"symbol": "HYG", "nav": 79.63, "updatedAt": "2026-07-10T20:00:00Z"},
        )
        r = resolve_and_upsert_one(client, "HYG")
        assert r["result"] == "skipped"
        assert r["reason"].startswith("nav_lag_")
        assert not EtfNavHistory.objects.filter(symbol="HYG").exists()

    def test_skip_missing_nav(self):
        client = _FakeClient(
            quote={"symbol": "HYG", "price": 79.65, "timestamp": _TS_FRI_0717},
            info={"symbol": "HYG", "nav": None, "updatedAt": "2026-07-17T20:00:00Z"},
        )
        r = resolve_and_upsert_one(client, "HYG")
        assert r["result"] == "skipped"
        assert not EtfNavHistory.objects.filter(symbol="HYG").exists()


@pytest.mark.django_db
class TestNoImpactRegression:
    def test_signal_key_namespaces_disjoint(self):
        """ETF 디스카운트 키는 기존 raw·파생 키와 겹치지 않는다."""
        etf = set(ETF_DISCOUNT_MAP)
        assert etf.isdisjoint(SIGNAL_SERIES_MAP)
        assert etf.isdisjoint(DERIVED_SIGNAL_MAP)

    def test_strip_api_excludes_etf_keys(self):
        """strip API 응답에 ETF 디스카운트 키가 노출되지 않는다(UI 미노출)."""
        # raw 1키 + ETF 상태 동시 존재시켜도 strip은 raw/파생만 반환.
        MacroSeriesHistory.objects.create(
            series_id="BAMLH0A0HYM2", date=date(2026, 7, 17), value=_D("2.71")
        )
        CreditSignalState.objects.create(
            signal_key="HY_OAS", as_of=date(2026, 7, 17), value=_D("2.71"),
            z_score=_D("0.4"), grade="gray", detail={},
        )
        CreditSignalState.objects.create(
            signal_key="HYG_NAV_DISCOUNT", as_of=date(2026, 7, 17), value=_D("-0.0251"),
            z_score=None, grade="gray", detail={},
        )
        user = get_user_model().objects.create_user(username="p2a_tester", password="x")
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get("/api/credit-signals/strip/")
        assert resp.status_code == 200
        keys = {s["key"] for s in resp.json()["signals"]}
        assert "HY_OAS" in keys
        assert "HYG_NAV_DISCOUNT" not in keys
        assert "LQD_NAV_DISCOUNT" not in keys

    def test_compute_all_includes_etf_keys(self):
        """compute_all_signals가 ETF 키를 포함(데이터 있을 때만 상태 생성)."""
        _seed_nav("HYG", [0.1] * 5)  # 콜드스타트지만 상태는 생성
        results = compute_all_signals()
        assert "HYG_NAV_DISCOUNT" in results
        assert "LQD_NAV_DISCOUNT" in results
        # LQD 원장 없음 → None(상태 미생성)
        assert results["LQD_NAV_DISCOUNT"] is None
