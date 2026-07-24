"""C-L3 생성기 테스트 — 그라운딩·톤가드·재시도(LLM은 _invoke_llm monkeypatch로 결정론화)."""

from __future__ import annotations

import datetime

import pytest

from apps.market_pulse.regime import context_generator as gen


def _seed_day(day: datetime.date, n: int = 3):
    from services.news.models import NewsArticle

    ts = datetime.datetime(day.year, day.month, day.day, 12, 0, tzinfo=datetime.timezone.utc)
    for i in range(n):
        NewsArticle.objects.create(
            url=f"https://ex.com/{day}-{i}", title=f"headline {i}", source=f"S{i}",
            published_at=ts, sentiment_score=0.5 - i * 0.1,
        )


@pytest.mark.django_db
def test_generate_success(monkeypatch):
    day = datetime.date(2024, 5, 6)
    _seed_day(day, 3)
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "규제 우려가 부각된 국면.")

    out = gen.generate_for_date(day)
    assert out is not None
    assert out["why_text"] == "규제 우려가 부각된 국면."
    assert out["prompt_version"] == "cl3_v1"
    assert len(out["provenance"]) == 3
    assert all({"id", "url", "title"} <= set(p) for p in out["provenance"])


@pytest.mark.django_db
def test_generate_empty_day_returns_none(monkeypatch):
    """그날 헤드라인 0건 → None(억지 생성 금지). LLM 호출조차 하지 않음."""
    called = {"n": 0}
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: called.__setitem__("n", called["n"] + 1) or "x")
    out = gen.generate_for_date(datetime.date(2020, 1, 1))
    assert out is None
    assert called["n"] == 0


@pytest.mark.django_db
def test_generate_tone_retry_then_success(monkeypatch):
    """1차 톤가드 실패 → 재생성 → 통과 시 저장 가능."""
    day = datetime.date(2024, 5, 6)
    _seed_day(day, 2)
    outs = iter(["금리 때문에 하락했다.", "긴축 우려가 부각된 국면."])  # 1차 위반 → 2차 정상
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: next(outs))

    out = gen.generate_for_date(day)
    assert out is not None
    assert out["why_text"] == "긴축 우려가 부각된 국면."


@pytest.mark.django_db
def test_generate_tone_retry_fails_returns_none(monkeypatch):
    """재생성도 톤가드 실패 → None(why=null 유지)."""
    day = datetime.date(2024, 5, 6)
    _seed_day(day, 2)
    monkeypatch.setattr(gen, "_invoke_llm", lambda h: "지금 매수해야 한다.")  # 매번 조언 어투

    out = gen.generate_for_date(day)
    assert out is None
