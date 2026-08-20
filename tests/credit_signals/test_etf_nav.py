"""P2a-1 — EtfNavHistory upsert 멱등성 · 디스카운트 compute-on-read · 부호 규약 ·
콜드스타트 · 원장 누적 · resolve 괴리 skip · 기존 8키 무영향(회귀)."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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
    """C″ 테스트용: quote·info·eod(historical) 주입."""
    def __init__(self, quote=None, info=None, eod=None):
        self._quote = quote or {}
        self._info = info or {}
        self._eod = eod or []

    def get_quote(self, symbol):
        return self._quote

    def get_etf_info(self, symbol):
        return self._info

    def get_historical_price(self, symbol, from_date=None, to_date=None):
        return self._eod


@pytest.mark.django_db
class TestUpsertNavUpdatedAt:
    """A — nav_updated_at(FMP strike 시각) 원장 병기 (upsert 직접, C″ 무관)."""

    def test_upsert_stores_nav_updated_at(self):
        dt = datetime(2026, 7, 27, 16, 30, tzinfo=ZoneInfo("America/New_York"))
        upsert_etf_nav("HYG", date(2026, 7, 27), _D("79.19"), _D("79.27"), nav_updated_at=dt)
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 7, 27))
        assert row.nav_updated_at == dt

    def test_upsert_nav_updated_at_defaults_null(self):
        upsert_etf_nav("HYG", date(2026, 7, 27), _D("79.19"), _D("79.27"))
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 7, 27))
        assert row.nav_updated_at is None

    def test_revise_updates_nav_updated_at(self):
        dt1 = datetime(2026, 7, 27, 16, 30, tzinfo=ZoneInfo("America/New_York"))
        dt2 = datetime(2026, 7, 28, 6, 0, tzinfo=ZoneInfo("America/New_York"))
        upsert_etf_nav("HYG", date(2026, 7, 27), _D("79.19"), _D("79.27"), nav_updated_at=dt1)
        assert upsert_etf_nav(
            "HYG", date(2026, 7, 27), _D("79.30"), _D("79.28"), nav_updated_at=dt2
        ) == "updated"
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 7, 27))
        assert row.nav_updated_at == dt2


@pytest.mark.django_db
class TestAttributionEdgeCases:
    """P2a-1e T-0 — 당일 귀속 + EOD 페어링 + 정체 게이트 + mismatch (엣지케이스).

    (구 TestCPrimePrimeAttribution: T-1 귀속. T-0 전환으로 개명·당일화. 기본 당일
    create/revise/멱등은 TestT0Attribution E1~E5, 여기는 DST·정체·price·mismatch·
    주말/휴장 무소급 회귀방지.)
    """

    def _client(self, upd, nav, eod, prev_close=None):
        q = {"symbol": "HYG"}
        if prev_close is not None:
            q["previousClose"] = prev_close
        return _FakeClient(quote=q, info={"symbol": "HYG", "nav": nav, "updatedAt": upd}, eod=eod)

    def test_monday_pub_attributes_same_day_not_friday(self):
        """회귀방지(T-0): 월요일 게시 → 당일(월) 귀속, 주말 소급 없음. pub 08-03(월)→08-03."""
        c = self._client("2026-08-03T17:55:00Z", 79.26, [{"date": "2026-08-03", "close": 79.48}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 3))
        assert r["result"] == "created" and r["trade_date"] == "2026-08-03"

    def test_post_holiday_pub_attributes_same_day_not_prior_friday(self):
        """회귀방지(T-0): MLK(01-19 월) 다음날 화 01-20 게시 → 당일 01-20 귀속, 휴장 소급 없음."""
        c = self._client("2026-01-20T22:00:00Z", 79.0, [{"date": "2026-01-20", "close": 79.1}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 1, 20))
        assert r["result"] == "created" and r["trade_date"] == "2026-01-20"

    def test_dst_winter_attribution(self):
        """겨울 EST: 화 01-06 09:00 EST 게시 → 당일 01-06 귀속(ET 날짜 추출 DST 정상)."""
        c = self._client("2026-01-06T14:00:00Z", 79.0, [{"date": "2026-01-06", "close": 79.1}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 1, 6))
        assert r["trade_date"] == "2026-01-06"

    def test_nav_stale_skip(self):
        """게시 08-03, 오늘 08-05 → 2거래일 정체 → skip nav_stale, 원장 미기록."""
        c = self._client("2026-08-03T17:55:00Z", 79.26, [{"date": "2026-07-31", "close": 79.48}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 5))
        assert r["result"] == "skipped" and r["reason"] == "nav_stale"
        assert not EtfNavHistory.objects.filter(symbol="HYG").exists()

    def test_one_day_lag_not_stale(self):
        """게시 08-05, 오늘 08-06 → 1거래일 → 정상 당일 귀속(08-05)."""
        c = self._client("2026-08-05T15:32:00Z", 79.40, [{"date": "2026-08-05", "close": 79.55}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 6))
        assert r["result"] == "created" and r["trade_date"] == "2026-08-05"

    def test_price_unavailable_skip(self):
        """EOD 종가 미확보 → skip price_unavailable."""
        c = self._client("2026-08-06T21:11:00Z", 79.37, [])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["result"] == "skipped" and r["reason"] == "price_unavailable"
        assert not EtfNavHistory.objects.filter(symbol="HYG").exists()

    def test_price_mismatch_flag(self):
        """previousClose vs 당일 EOD 종가 불일치(>tol) → created + price_mismatch(ⓑ 우선)."""
        c = self._client("2026-08-06T21:11:00Z", 79.37,
                         [{"date": "2026-08-06", "close": 79.52}], prev_close=79.20)
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["result"] == "created" and r["price_mismatch"] is True
        assert EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 8, 6)).price == _D("79.52")

    def test_price_mismatch_within_tol_no_flag(self):
        """오차 내(≤tol) → mismatch 아님."""
        c = self._client("2026-08-06T21:11:00Z", 79.37,
                         [{"date": "2026-08-06", "close": 79.52}], prev_close=79.54)
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["price_mismatch"] is False

    def test_price_from_eod_not_quote(self):
        """price는 EOD 종가지 quote.price가 아니다."""
        c = _FakeClient(
            quote={"symbol": "HYG", "price": 999, "previousClose": 79.52},
            info={"symbol": "HYG", "nav": 79.37, "updatedAt": "2026-08-06T21:11:00Z"},
            eod=[{"date": "2026-08-06", "close": 79.52}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["price"] == 79.52

    def test_missing_nav_skip(self):
        c = self._client("2026-08-06T21:11:00Z", None, [{"date": "2026-08-05", "close": 79.52}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["result"] == "skipped" and r["reason"] == "missing_or_invalid"

    def test_resolve_populates_nav_updated_at(self):
        """귀속 행에 nav_updated_at(게시 시각) 저장 유지."""
        c = self._client("2026-08-06T21:11:00Z", 79.37, [{"date": "2026-08-06", "close": 79.52}])
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 7))
        assert r["result"] == "created"
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 8, 6))
        assert row.nav_updated_at.astimezone(ZoneInfo("America/New_York")).hour == 17


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


@pytest.mark.django_db
class TestNonTradingDayPubGuard:
    """P2a-1d — 비거래일(주말·미국 휴장일) 게시 가드.

    FMP가 비거래일에 게시하는 잔존값 이월분은 새 strike가 아니므로 create·revise를
    원천 차단한다(기존행 무접촉). 가드 키 = 게시일(updatedAt의 ET 날짜)이지 발화일이
    아니다 — 거래일 게시의 클린 create/revise 경로는 그대로 보존(08-16 오귀속 재발 방지).
    """

    def _client(self, upd, nav, eod, prev_close=None):
        q = {"symbol": "HYG"}
        if prev_close is not None:
            q["previousClose"] = prev_close
        return _FakeClient(
            quote=q, info={"symbol": "HYG", "nav": nav, "updatedAt": upd}, eod=eod
        )

    def test_saturday_pub_blocks_create(self, caplog):
        """T1 — pub=토(08-15) → create 시도 차단 + skip 로그 (08-16 오귀속 재현).

        가드 없으면 prev_trading_day(08-15)=금 08-14 행이 create된다. 가드가 봉쇄.
        """
        c = self._client(
            "2026-08-15T20:14:30-04:00", 79.63,
            [{"date": "2026-08-14", "close": 79.71}],
        )
        with caplog.at_level("WARNING"):
            r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 15))
        assert r["result"] == "skipped" and r["reason"] == "non_trading_day_pub"
        assert not EtfNavHistory.objects.exists()  # create 원천 차단
        assert "비거래일 게시" in caplog.text

    def test_sunday_pub_blocks_create(self):
        """T2 — pub=일(08-16) → 동일 차단 (08-17 재현)."""
        c = self._client(
            "2026-08-16T20:57:10-04:00", 79.63,
            [{"date": "2026-08-14", "close": 79.71}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 16))
        assert r["result"] == "skipped" and r["reason"] == "non_trading_day_pub"
        assert not EtfNavHistory.objects.exists()

    def test_friday_pub_allows_create(self):
        """T3 — pub=금(08-14, 거래일) + 신규 → 당일 08-14 create 허용 (게시일 키·T-0).

        발화일 키였다면 이 클린 create까지 오차단됐을 것 — 게시일 키가 정답임을 증명.
        """
        c = self._client(
            "2026-08-14T20:24:40-04:00", 79.63,
            [{"date": "2026-08-14", "close": 79.79}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 14))
        assert r["result"] == "created" and r["trade_date"] == "2026-08-14"
        assert EtfNavHistory.objects.get(
            symbol="HYG", date=date(2026, 8, 14)
        ).nav == _D("79.63")

    def test_monday_pub_allows_revise(self):
        """T4 — pub=월(08-17, 거래일) + 기존 당일행 값 상이 → revise 허용 (T-0)."""
        # 기존 08-17 당일행(구값 79.63)을 seed → 월 게시가 79.57로 교정.
        upsert_etf_nav("HYG", date(2026, 8, 17), _D("79.63"), _D("79.71"))
        c = self._client(
            "2026-08-17T20:53:20-04:00", 79.57,
            [{"date": "2026-08-17", "close": 79.71}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 17))
        assert r["result"] == "updated" and r["trade_date"] == "2026-08-17"
        assert EtfNavHistory.objects.get(
            symbol="HYG", date=date(2026, 8, 17)
        ).nav == _D("79.57")

    def test_holiday_pub_blocks_create(self):
        """T5 — pub=미국 휴장일(Labor Day 2026-09-07 월) → 차단."""
        c = self._client(
            "2026-09-07T20:00:00-04:00", 79.50,
            [{"date": "2026-09-04", "close": 79.60}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 9, 7))
        assert r["result"] == "skipped" and r["reason"] == "non_trading_day_pub"
        assert not EtfNavHistory.objects.exists()

    def test_trading_day_pub_same_value_already_ok(self):
        """T6 — pub=거래일(08-14) + 동일값 당일행 → no-change(멱등) 불변, 가드 무간섭 (T-0).

        정면 재작성: seed·pub·eod 모두 당일(08-14)로 정렬 → upsert가 진짜 no-change로
        skip하는 경로를 검증(구판은 08-13 seed로 price_unavailable 우연통과였음).
        """
        upsert_etf_nav("HYG", date(2026, 8, 14), _D("79.63"), _D("79.79"))
        c = self._client(
            "2026-08-14T20:24:40-04:00", 79.63,
            [{"date": "2026-08-14", "close": 79.79}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 14))
        assert r["result"] == "skipped" and r["trade_date"] == "2026-08-14"
        assert "reason" not in r  # no-change 정상 경로(price_unavailable 등 아님)
        assert EtfNavHistory.objects.get(
            symbol="HYG", date=date(2026, 8, 14)
        ).revised_at is None  # 불변


@pytest.mark.django_db
class TestT0Attribution:
    """P2a-1e — 귀속 규칙 T-0 전환.

    fix(08-14) 이후 FMP 저녁 스윕(20:1x~20:5x ET)이 당일 확정 NAV를 게시(iShares
    공식치 양 ETF 교차검증) → nav_trade_date = 게시일 당일(D-1 제거). 비거래일 pub은
    가드(P2a-1d)가 선차단하므로 T-0에 도달하는 것은 거래일 pub뿐. price 페어링이
    '당일 nav vs 당일 EOD'로 정렬되어 mismatch 게이트 판별력 회복.
    """

    def _client(self, upd, nav, eod, prev_close=None):
        q = {"symbol": "HYG"}
        if prev_close is not None:
            q["previousClose"] = prev_close
        return _FakeClient(
            quote=q, info={"symbol": "HYG", "nav": nav, "updatedAt": upd}, eod=eod
        )

    def test_e1_trading_day_pub_attributes_same_day(self):
        """E1 — pub=거래일(화 08-18 저녁) → 당일 08-18 귀속 create (D-1 아님)."""
        c = self._client(
            "2026-08-18T20:18:10-04:00", 79.43,
            [{"date": "2026-08-18", "close": 79.61}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 18))
        assert r["result"] == "created" and r["trade_date"] == "2026-08-18"
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 8, 18))
        assert row.nav == _D("79.43") and row.price == _D("79.61")

    def test_e2_same_day_value_differs_revises(self):
        """E2 — pub=거래일 + 기존 당일행 값 상이 → revise."""
        upsert_etf_nav("HYG", date(2026, 8, 18), _D("79.00"), _D("79.61"))
        c = self._client(
            "2026-08-18T20:18:10-04:00", 79.43,
            [{"date": "2026-08-18", "close": 79.61}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 18))
        assert r["result"] == "updated" and r["trade_date"] == "2026-08-18"
        assert EtfNavHistory.objects.get(
            symbol="HYG", date=date(2026, 8, 18)
        ).nav == _D("79.43")

    def test_e3_same_day_same_value_idempotent(self):
        """E3 — pub=거래일 + 동일값 → no-change 멱등(already_ok)."""
        upsert_etf_nav("HYG", date(2026, 8, 18), _D("79.43"), _D("79.61"))
        c = self._client(
            "2026-08-18T20:18:10-04:00", 79.43,
            [{"date": "2026-08-18", "close": 79.61}],
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 18))
        assert r["result"] == "skipped" and r["trade_date"] == "2026-08-18"
        assert "reason" not in r  # no-change(정상 경로), price_unavailable 등 아님

    def test_e4_guard_regression_non_trading_pub_blocked(self):
        """E4 — 가드 회귀: 토·일·휴장일 pub → 차단 불변(T-0 전환 후에도)."""
        for upd, label in [
            ("2026-08-15T20:14:30-04:00", "토"),
            ("2026-08-16T20:57:10-04:00", "일"),
            ("2026-09-07T20:00:00-04:00", "LaborDay"),
        ]:
            c = self._client(upd, 79.50, [{"date": "2026-08-14", "close": 79.71}])
            r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 18))
            assert r["result"] == "skipped" and r["reason"] == "non_trading_day_pub", label
        assert not EtfNavHistory.objects.exists()

    def test_e5_mismatch_pairs_same_day_nav_and_eod(self):
        """E5 — mismatch: 당일 nav vs 당일 EOD close 페어링(price=당일 EOD)."""
        c = self._client(
            "2026-08-18T20:18:10-04:00", 79.43,
            [{"date": "2026-08-18", "close": 79.61}], prev_close=79.40,
        )
        r = resolve_and_upsert_one(c, "HYG", today_et=date(2026, 8, 18))
        assert r["result"] == "created" and r["price_mismatch"] is True
        # price는 당일(08-18) EOD 종가여야 한다.
        assert r["price"] == 79.61
        assert EtfNavHistory.objects.get(
            symbol="HYG", date=date(2026, 8, 18)
        ).price == _D("79.61")
