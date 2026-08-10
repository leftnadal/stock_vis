"""purge_analog_v1_residual 테스트 — 이중 조건(date∩cl3_v1)·dry-run·멱등."""

from __future__ import annotations

import datetime
from io import StringIO

import pytest
from django.core.management import call_command

from apps.market_pulse.management.commands.purge_analog_v1_residual import RESIDUAL_DATES
from apps.market_pulse.models import AnalogDayContext


def _mk(date, version, why="x"):
    AnalogDayContext.objects.create(
        date=date, why_text=why, provenance=[{"id": "1", "url": "u", "title": "t"}],
        prompt_version=version,
    )


def _run(*args):
    out = StringIO()
    call_command("purge_analog_v1_residual", *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def _seeded(db):
    # 대상 12일 중 2일을 cl3_v1로, 1일을 cl3_v2로(같은 목록 날짜여도 버전 다르면 보존) 시드.
    _mk(RESIDUAL_DATES[0], "cl3_v1")
    _mk(RESIDUAL_DATES[1], "cl3_v1")
    _mk(RESIDUAL_DATES[2], "cl3_v2")  # 목록 날짜지만 v2 → 이중 조건으로 보존
    # 목록 밖 cl3_v2 1일(무관 보존)
    _mk(datetime.date(2024, 7, 1), "cl3_v2")


def test_dry_run_deletes_nothing(_seeded):
    text = _run()  # --commit 없음
    assert AnalogDayContext.objects.count() == 4
    assert "DRY-RUN" in text


def test_commit_deletes_only_v1_residual(_seeded):
    _run("--commit")
    # cl3_v1 2행만 삭제, cl3_v2(목록 내 1 + 목록 밖 1)는 보존
    assert AnalogDayContext.objects.filter(prompt_version="cl3_v1").count() == 0
    assert AnalogDayContext.objects.filter(prompt_version="cl3_v2").count() == 2
    assert AnalogDayContext.objects.count() == 2


def test_list_date_but_v2_preserved(_seeded):
    """목록 날짜여도 prompt_version=cl3_v2면 이중 조건으로 보존(구조적 차단)."""
    _run("--commit")
    assert AnalogDayContext.objects.filter(date=RESIDUAL_DATES[2]).exists()


def test_idempotent_rerun(_seeded):
    _run("--commit")
    text = _run("--commit")  # 재실행 = 0행
    assert "0행" in text or "대상(date∩cl3_v1) 0행" in text
