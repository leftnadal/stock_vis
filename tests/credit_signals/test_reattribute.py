"""P2a-1c — reattribute_etf_nav 마이그레이션 command (dry-run/execute·재귀속·신설·hold)."""
import datetime as dt
import json
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from apps.credit_signals.models import EtfNavHistory

_D = lambda x: Decimal(str(x))
_ET = ZoneInfo("America/New_York")


def _fake_client(eod_map):
    fc = mock.MagicMock()
    fc.get_historical_price.side_effect = (
        lambda symbol, from_date=None, to_date=None: eod_map.get(symbol, [])
    )
    return fc


def _run(*args, eod_map=None):
    out = StringIO()
    with mock.patch(
        "packages.shared.api_request.providers.fmp.client.FMPClient",
        return_value=_fake_client(eod_map or {}),
    ):
        call_command("reattribute_etf_nav", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestReattribute:
    def _mixed_0806(self):
        EtfNavHistory.objects.create(
            symbol="HYG", date=date(2026, 8, 6), nav=_D("79.37"), price=_D("79.46"),
            nav_updated_at=dt.datetime(2026, 8, 6, 17, 11, tzinfo=_ET),
        )

    def test_dry_run_no_db_change(self):
        self._mixed_0806()
        out = _run(eod_map={"HYG": [{"date": "2026-08-05", "close": 79.52}]})
        assert "MOVE" in out and "DRY-RUN" in out
        # 무변경: 08-06 그대로, 08-05 미생성
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 6)).exists()
        assert not EtfNavHistory.objects.filter(date=date(2026, 8, 5)).exists()

    def test_execute_moves_and_repairs_price(self):
        self._mixed_0806()
        _run("--execute", eod_map={"HYG": [{"date": "2026-08-05", "close": 79.52}]})
        assert not EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 6)).exists()
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 8, 5))
        assert row.nav == _D("79.37") and row.price == _D("79.52")
        assert row.revised_at is not None

    def test_hold_when_nav_updated_at_null(self):
        # nav_updated_at 없음 → 재귀속 근거 불가, hold(이동 안 함)
        EtfNavHistory.objects.create(
            symbol="HYG", date=date(2026, 7, 20), nav=_D("79.6"), price=_D("79.6"),
        )
        out = _run("--execute", eod_map={"HYG": [{"date": "2026-07-17", "close": 79.0}]})
        assert "HOLD" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 7, 20)).exists()

    def test_hold_when_eod_unavailable(self):
        self._mixed_0806()
        out = _run("--execute", eod_map={"HYG": []})  # EOD 미확보
        assert "HOLD" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 6)).exists()  # 이동 안 됨

    def test_create_new_row_from_json(self, tmp_path):
        seed = tmp_path / "seed.json"
        seed.write_text(json.dumps({"2026-08-04": {"HYG": "79.40"}}))
        _run("--execute", "--nav-json", str(seed),
             eod_map={"HYG": [{"date": "2026-08-04", "close": 79.55}]})
        row = EtfNavHistory.objects.get(symbol="HYG", date=date(2026, 8, 4))
        assert row.nav == _D("79.40") and row.price == _D("79.55")
        assert row.nav_updated_at is None  # 소급 주입은 게시 시각 불명

    def test_new_row_skip_if_exists(self, tmp_path):
        EtfNavHistory.objects.create(
            symbol="HYG", date=date(2026, 8, 4), nav=_D("79.40"), price=_D("79.55"),
        )
        seed = tmp_path / "seed.json"
        seed.write_text(json.dumps({"2026-08-04": {"HYG": "79.40"}}))
        out = _run("--execute", "--nav-json", str(seed),
                   eod_map={"HYG": [{"date": "2026-08-04", "close": 79.55}]})
        assert "SKIP" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 4)).count() == 1


@pytest.mark.django_db
class TestReattributeT0Cutover:
    """P2a-1f — cutover 경계(FMP fix 08-14) 재귀속.

    pre-fix(pub<08-14)=T-1 유지(역사 보존) / post-fix(pub>=08-14)=T-0 당일.
    post-fix 비거래일 pub=무이동(HOLD). cascade(연쇄 이동)는 역순+vacating 인지로
    dry-run 예측과 execute 결과 일치.
    """

    def _seed(self, symbol, d, pub, nav="79.5", price="79.6"):
        EtfNavHistory.objects.create(
            symbol=symbol, date=d, nav=_D(nav), price=_D(price),
            nav_updated_at=dt.datetime(pub.year, pub.month, pub.day, 20, 0, tzinfo=_ET),
        )

    def test_f1_pre_cutover_pub_keeps_t1(self):
        """F1 — pub=08-13(경계 전날) → new_td=08-12(T-1 유지)."""
        self._seed("HYG", date(2026, 8, 13), date(2026, 8, 13))
        _run("--execute", eod_map={"HYG": [{"date": "2026-08-12", "close": 79.55}]})
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 12)).exists()

    def test_f2_cutover_day_pub_applies_t0(self):
        """F2 — pub=08-14(경계 당일) → new_td=08-14(T-0)."""
        self._seed("HYG", date(2026, 8, 13), date(2026, 8, 14))
        _run("--execute", eod_map={"HYG": [{"date": "2026-08-14", "close": 79.71}]})
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 14)).exists()
        assert not EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 13)).exists()

    def test_f3_pre_fix_aligned_already_ok(self):
        """F3 — pre-fix 정합 행(08-12행, pub=08-13) → already_ok 무이동."""
        self._seed("HYG", date(2026, 8, 12), date(2026, 8, 13))
        out = _run("--execute", eod_map={"HYG": [{"date": "2026-08-12", "close": 79.6}]})
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 12)).count() == 1
        assert "MOVE" not in out

    def test_f4_post_fix_misattributed_moves(self):
        """F4 — post-fix 오귀속 행(08-13행, pub=08-14) → MOVE 08-14."""
        self._seed("HYG", date(2026, 8, 13), date(2026, 8, 14))
        out = _run(eod_map={"HYG": [{"date": "2026-08-14", "close": 79.71}]})  # dry-run
        assert "MOVE" in out and "2026-08-14" in out

    def test_f5_post_fix_aligned_already_ok(self):
        """F5 — post-fix T-0 정위치 행(08-20행, pub=08-20) → already_ok(08-19로 안 감)."""
        self._seed("HYG", date(2026, 8, 20), date(2026, 8, 20))
        # 08-19 eod도 제공 → cutover 전이면 08-19로 오이동(RED), cutover 후 already_ok(GREEN)
        _run("--execute", eod_map={"HYG": [
            {"date": "2026-08-20", "close": 79.56}, {"date": "2026-08-19", "close": 79.40},
        ]})
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 20)).exists()
        assert not EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 19)).exists()

    def test_f6_null_holds(self):
        """F6 — NULL nav_updated_at → HOLD 불변."""
        EtfNavHistory.objects.create(
            symbol="HYG", date=date(2026, 8, 4), nav=_D("79.4"), price=_D("79.5"),
        )
        out = _run("--execute", eod_map={"HYG": []})
        assert "HOLD" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 4)).exists()

    def test_f7_conflict_holds(self):
        """F7 — 이동 목적지에 비이동 행 존재 → 충돌 검출·HOLD (회귀)."""
        self._seed("HYG", date(2026, 8, 20), date(2026, 8, 20))  # already_ok, 비이동 점유자
        self._seed("HYG", date(2026, 8, 19), date(2026, 8, 20))  # → 08-20 목표, 충돌
        out = _run("--execute", eod_map={"HYG": [{"date": "2026-08-20", "close": 79.56}]})
        assert "HOLD" in out and "충돌" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 19)).exists()

    def test_f8_post_fix_non_trading_pub_holds(self):
        """F8 — post-fix + 비거래일 pub(토 08-15) → 무이동 처리(HOLD)."""
        self._seed("HYG", date(2026, 8, 16), date(2026, 8, 15))  # 08-15=토, post-fix
        out = _run("--execute", eod_map={"HYG": [{"date": "2026-08-14", "close": 79.71}]})
        assert "HOLD" in out
        assert EtfNavHistory.objects.filter(symbol="HYG", date=date(2026, 8, 16)).exists()

    def test_f9_cascade_three_moves(self):
        """F9 — cascade 08-13→08-14→08-17→08-18(역순 안전). dry-run 예측=execute 결과."""
        self._seed("HYG", date(2026, 8, 13), date(2026, 8, 14), nav="79.63")
        self._seed("HYG", date(2026, 8, 14), date(2026, 8, 17), nav="79.57")
        self._seed("HYG", date(2026, 8, 17), date(2026, 8, 18), nav="79.43")
        eod = {"HYG": [
            {"date": "2026-08-14", "close": 79.71},
            {"date": "2026-08-17", "close": 79.71},
            {"date": "2026-08-18", "close": 79.61},
        ]}
        out = _run(eod_map=eod)  # dry-run
        assert out.count("MOVE") >= 3  # cascade 3연쇄 예측
        _run("--execute", eod_map=eod)
        dates = set(EtfNavHistory.objects.filter(symbol="HYG").values_list("date", flat=True))
        assert dates == {date(2026, 8, 14), date(2026, 8, 17), date(2026, 8, 18)}
