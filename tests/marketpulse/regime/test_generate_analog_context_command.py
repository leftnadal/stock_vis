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


# ── REGEN-V2: --select-version v2 ──

@pytest.fixture
def _seeded_macro(db):
    """모집단일 1 + 그날 macro 헤드라인 1건(v2 STRONG) + 개별기업 노이즈 1건."""
    from services.news.models import NewsArticle

    RegimeSnapshot.objects.create(
        date=DAY, snapshot_time=datetime.datetime(2024, 5, 6, 20, 0, tzinfo=datetime.timezone.utc),
        regime="TRANSITION", coverage=1.0, summary=BACKFILL_MARK,
    )
    ts = datetime.datetime(2024, 5, 6, 12, 0, tzinfo=datetime.timezone.utc)
    NewsArticle.objects.create(url="https://ex.com/macro", title="Fed signals rate cut as inflation eases",
                               source="Reuters", published_at=ts, sentiment_score=0.1)
    NewsArticle.objects.create(url="https://ex.com/noise", title="Acme soars on blowout earnings",
                               source="Yahoo Finance", published_at=ts, sentiment_score=0.95)


def test_v2_commit_tags_cl3_v2(_seeded_macro, monkeypatch):
    """--select-version v2 → prompt 자동 cl3_v2 태그 + macro provenance."""
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "긴축 완화 기대가 부각된 국면.")
    text = _run("--select-version", "v2", "--commit")
    obj = AnalogDayContext.objects.get(date=DAY)
    assert obj.prompt_version == "cl3_v2"
    assert "select=v2" in text
    assert any("Fed" in p["title"] for p in obj.provenance)      # macro 선별
    assert all("Acme" not in p["title"] for p in obj.provenance)  # 노이즈 탈락


def test_v2_regenerate_upgrades_v1_then_idempotent(_seeded_macro, monkeypatch):
    """v1 생성분(cl3_v1) → v2 --regenerate 업그레이드(cl3_v2) → 재실행 멱등 skip."""
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "구버전 문장.")
    _run("--commit")  # v1 → cl3_v1
    assert AnalogDayContext.objects.get(date=DAY).prompt_version == "cl3_v1"

    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "긴축 완화 기대가 부각된 국면.")
    _run("--select-version", "v2", "--regenerate", "--commit")  # 업그레이드 → cl3_v2
    obj = AnalogDayContext.objects.get(date=DAY)
    assert obj.prompt_version == "cl3_v2"
    assert AnalogDayContext.objects.count() == 1  # 덮어쓰기(신규 행 아님)

    # 재실행(같은 v2) → 이미 cl3_v2 → skip(멱등)
    calls = {"n": 0}
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: calls.__setitem__("n", calls["n"] + 1) or "다른 문장.")
    text = _run("--select-version", "v2", "--regenerate", "--commit")
    assert calls["n"] == 0
    assert "이번 대상 0" in text


def test_v2_empty_macro_signal_keeps_null(_seeded, monkeypatch):
    """v2: 개별기업만(_seeded=h0/h1, macro 없음) → 빈 선별 → 행 미생성(why=null)."""
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "안 불림.")
    _run("--select-version", "v2", "--commit")
    assert AnalogDayContext.objects.count() == 0


def test_v2_dry_run_macro_signal_reported(_seeded_macro, monkeypatch):
    """v2 dry-run: 실제 선별기로 macro 신호 있는 날 실측, 쓰기 0."""
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "안 불림.")
    text = _run("--select-version", "v2")
    assert AnalogDayContext.objects.count() == 0
    assert "select=v2" in text
    assert "헤드라인 있는 일수 : 1" in text


def test_dates_flag_targets_population_intersection(db, monkeypatch):
    """--dates: 콤마 목록 ∩ 모집단만 대상(모집단 밖·비존재일 자동 제외). 재시도 게이트용."""
    for day in (datetime.date(2024, 3, 1), datetime.date(2024, 3, 4)):
        RegimeSnapshot.objects.create(
            date=day,
            snapshot_time=datetime.datetime(day.year, day.month, day.day, 20, 0, tzinfo=datetime.timezone.utc),
            regime="TRANSITION", coverage=1.0, summary=BACKFILL_MARK,
        )
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "안 불림.")
    text = _run("--dates", "2024-03-01,2024-03-04", "--select-version", "v2")
    assert "모집단 2일" in text  # 둘 다 모집단
    text2 = _run("--dates", "2024-03-01,2099-01-01", "--select-version", "v2")
    assert "모집단 1일" in text2  # 모집단 밖(2099)은 제외
