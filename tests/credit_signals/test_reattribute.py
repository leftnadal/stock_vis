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
