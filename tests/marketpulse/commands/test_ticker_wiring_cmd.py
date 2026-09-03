"""A-3(HUB-V02-S1): fix_commodity_ticker_wiring 커맨드 — dry-run 무쓰기 / --commit 교정."""
from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from macro.models.indicators import MarketIndex

pytestmark = pytest.mark.django_db


def _mi(symbol, sg):
    obj, _ = MarketIndex.objects.update_or_create(
        symbol=symbol, defaults={"name": symbol, "category": "commodity", "sector_group": sg}
    )
    return obj


def test_dry_run_no_write():
    _mi("GCUSD", "COMMUNICATION")  # non-benchmark(스트립 제외 상태 대용 — 모델 non-null 준수)
    _mi("GLD", "BENCHMARK")
    out = StringIO()
    call_command("fix_commodity_ticker_wiring", stdout=out)
    # dry-run: 값 불변
    assert MarketIndex.objects.get(symbol="GCUSD").sector_group == "COMMUNICATION"
    assert MarketIndex.objects.get(symbol="GLD").sector_group == "BENCHMARK"
    assert "DRY-RUN" in out.getvalue()


def test_commit_adds_commodity_to_benchmark():
    _mi("GCUSD", "COMMUNICATION")
    _mi("SIUSD", "COMMUNICATION")
    _mi("GLD", "BENCHMARK")  # 빈 심볼 — 커맨드는 쓰기 안 함(코드가 스킵)
    call_command("fix_commodity_ticker_wiring", "--commit")
    assert MarketIndex.objects.get(symbol="GCUSD").sector_group == "BENCHMARK"
    assert MarketIndex.objects.get(symbol="SIUSD").sector_group == "BENCHMARK"
    # GLD는 커맨드가 손대지 않음(sector_group 불변)
    assert MarketIndex.objects.get(symbol="GLD").sector_group == "BENCHMARK"


def test_commit_idempotent():
    _mi("GCUSD", "BENCHMARK")  # 이미 목표값
    call_command("fix_commodity_ticker_wiring", "--commit")
    assert MarketIndex.objects.get(symbol="GCUSD").sector_group == "BENCHMARK"
