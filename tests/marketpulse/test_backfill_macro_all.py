"""
MP-OPS-FRED-ENTRYPOINT (P1-close) — backfill_macro_all thin wrapper 테스트.

대상: apps/market_pulse/management/commands/backfill_macro_all.py
검증: 기존 backfill_v2_a1을 call_command로 조합(신규 fetch 0). 하위 호출 인자 전파 +
      기본목록 밖 EXTRA_FRED_SERIES(VIXCLS·T10Y2Y) 개별 분기. 실 FRED 무네트워크(call_command mock).
"""
from __future__ import annotations

from unittest.mock import patch

from django.core.management import call_command

from apps.market_pulse.management.commands import backfill_macro_all as cmd


class TestBackfillMacroAllWrapper:
    def test_invokes_base_then_extra_series(self):
        # backfill_macro_all → backfill_v2_a1 (기본 + VIXCLS + T10Y2Y) 3회 호출
        with patch.object(cmd, "call_command") as cc:
            call_command(
                "backfill_macro_all", **{"from": "2025-06-01", "to": "2026-06-23"}
            )

        # 총 3회 (기본 1 + EXTRA_FRED_SERIES 2)
        assert cc.call_count == 1 + len(cmd.EXTRA_FRED_SERIES)
        # 전부 backfill_v2_a1 위임 (신규 fetch 로직 없음 = 다른 커맨드 호출 안 함)
        assert all(c.args[0] == "backfill_v2_a1" for c in cc.call_args_list)

    def test_first_call_is_base_list_no_series_id(self):
        with patch.object(cmd, "call_command") as cc:
            call_command("backfill_macro_all")
        first = cc.call_args_list[0]
        # 기본 목록 호출은 series_id 미지정 (전체 NEW_ECONOMIC_SERIES + NEW_MARKET_SYMBOLS)
        assert "series_id" not in first.kwargs

    def test_extra_series_passed_individually(self):
        with patch.object(cmd, "call_command") as cc:
            call_command("backfill_macro_all")
        extra_ids = [
            c.kwargs.get("series_id")
            for c in cc.call_args_list
            if "series_id" in c.kwargs
        ]
        assert extra_ids == list(cmd.EXTRA_FRED_SERIES)
        assert "VIXCLS" in extra_ids and "T10Y2Y" in extra_ids

    def test_extra_calls_use_econ_only_to_skip_market(self):
        # market(XL*) 중복 재백필 방지: EXTRA series 호출은 econ_only=True
        with patch.object(cmd, "call_command") as cc:
            call_command("backfill_macro_all")
        for c in cc.call_args_list:
            if "series_id" in c.kwargs:
                assert c.kwargs.get("econ_only") is True
        # 기본 목록 호출은 econ_only 미설정 (market 포함)
        first = cc.call_args_list[0]
        assert not first.kwargs.get("econ_only")

    def test_date_range_and_dry_run_propagated(self):
        with patch.object(cmd, "call_command") as cc:
            call_command(
                "backfill_macro_all",
                **{"from": "2025-01-01", "to": "2025-12-31", "dry_run": True},
            )
        for c in cc.call_args_list:
            assert c.kwargs["from_date"] == "2025-01-01"
            assert c.kwargs["to_date"] == "2025-12-31"
            assert c.kwargs["dry_run"] is True

    def test_extra_fred_series_are_outside_base_list(self):
        # 전제 가드: VIXCLS·T10Y2Y가 backfill_v2_a1 기본목록 밖이어야 wrapper가 의미 있음
        from apps.market_pulse.management.commands.backfill_v2_a1 import (
            NEW_ECONOMIC_SERIES,
        )

        for s in cmd.EXTRA_FRED_SERIES:
            assert s not in NEW_ECONOMIC_SERIES
