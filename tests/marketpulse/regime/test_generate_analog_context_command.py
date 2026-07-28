"""C-L3 generate_analog_context 커맨드 테스트 — dry-run·commit·멱등·동결(LLM monkeypatch)."""

from __future__ import annotations

import datetime
from io import StringIO

import pytest
from django.core.management import call_command

from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models import AnalogDayContext, RegimeSnapshot
from apps.market_pulse.regime import context_generator as gen

DAY = datetime.date(2024, 5, 6)


@pytest.fixture
def _seeded(db):
    """모집단일 1(BACKFILL_MARK·coverage=1.0) + 그날 헤드라인 2건."""
    from services.news.models import NewsArticle

    RegimeSnapshot.objects.create(
        date=DAY, snapshot_time=datetime.datetime(2024, 5, 6, 20, 0, tzinfo=datetime.timezone.utc),
        regime="TRANSITION", coverage=1.0, summary=BACKFILL_MARK,
    )
    ts = datetime.datetime(2024, 5, 6, 12, 0, tzinfo=datetime.timezone.utc)
    for i in range(2):
        NewsArticle.objects.create(url=f"https://ex.com/{i}", title=f"h{i}", source=f"S{i}",
                                   published_at=ts, sentiment_score=0.4)


def _run(*args):
    out = StringIO()
    call_command("generate_analog_context", *args, stdout=out)
    return out.getvalue()


def test_dry_run_writes_nothing(_seeded, monkeypatch):
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "규제 우려 국면.")
    text = _run()  # --commit 없음 = dry-run
    assert AnalogDayContext.objects.count() == 0
    assert "DRY-RUN" in text
    assert "헤드라인 있는 일수 : 1" in text


def test_commit_creates_context(_seeded, monkeypatch):
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "규제 우려가 부각된 국면.")
    _run("--commit")
    obj = AnalogDayContext.objects.get(date=DAY)
    assert obj.why_text == "규제 우려가 부각된 국면."
    assert obj.prompt_version == "cl3_v1"
    assert len(obj.provenance) == 2


def test_idempotent_skip(_seeded, monkeypatch):
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "규제 우려 국면.")
    _run("--commit")
    # 2회차: 기존분 skip → LLM 재호출 없이 대상 0
    calls = {"n": 0}
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: calls.__setitem__("n", calls["n"] + 1) or "다른 문장.")
    text = _run("--commit")
    assert calls["n"] == 0
    assert AnalogDayContext.objects.get(date=DAY).why_text == "규제 우려 국면."  # 동결(불변)
    assert "이번 대상 0" in text


def test_regenerate_overwrites_with_version(_seeded, monkeypatch):
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "구버전 문장.")
    _run("--commit")
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "신버전 문장.")
    _run("--commit", "--regenerate", "--prompt-version", "cl3_v2")
    obj = AnalogDayContext.objects.get(date=DAY)
    assert obj.why_text == "신버전 문장."
    assert obj.prompt_version == "cl3_v2"
    assert AnalogDayContext.objects.count() == 1  # 덮어쓰기(신규 행 아님)


def test_empty_day_keeps_null(db, monkeypatch):
    """모집단일이나 그날 헤드라인 0건 → 행 미생성(why=null)."""
    RegimeSnapshot.objects.create(
        date=datetime.date(2020, 1, 1),
        snapshot_time=datetime.datetime(2020, 1, 1, 20, 0, tzinfo=datetime.timezone.utc),
        regime="TRANSITION", coverage=1.0, summary=BACKFILL_MARK,
    )
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "안 불림.")
    _run("--commit")
    assert AnalogDayContext.objects.count() == 0
