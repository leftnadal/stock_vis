"""C-L3 그라운딩 선별 테스트 — 결정론 랭킹 + is_archived 무필터 회귀(함정 잠금)."""

from __future__ import annotations

import datetime

import pytest

from apps.market_pulse.regime.grounding import (
    GROUNDING_SOURCE_CAP,
    fetch_day_candidates,
    rank_headlines,
    select_grounding,
)


def _c(cid, *, sent=None, ec=0, source="S", pub="2024-05-06T12:00:00"):
    return {
        "id": cid,
        "title": f"headline {cid}",
        "url": f"https://ex.com/{cid}",
        "source": source,
        "sentiment_score": sent,
        "entity_count": ec,
        "published_at": datetime.datetime.fromisoformat(pub),
    }


# ── 순수 랭킹(LLM·DB 무의존) ──

def test_rank_by_sentiment_strength_desc():
    """감성 강도(절대값) 큰 것이 앞. 부호 무관(-0.9가 +0.1보다 앞)."""
    got = rank_headlines([_c("a", sent=0.1), _c("b", sent=-0.9), _c("c", sent=0.3)])
    assert [c["id"] for c in got] == ["b", "c", "a"]


def test_rank_entity_count_tiebreak():
    """감성 강도 동률 → entity_count 많은 것이 앞."""
    got = rank_headlines([_c("a", sent=0.5, ec=2), _c("b", sent=0.5, ec=9), _c("c", sent=0.5, ec=5)])
    assert [c["id"] for c in got] == ["b", "c", "a"]


def test_rank_none_sentiment_treated_as_zero():
    """sentiment None은 강도 0(최하). 발명 금지."""
    got = rank_headlines([_c("a", sent=None, ec=99), _c("b", sent=0.01, ec=0)])
    assert [c["id"] for c in got] == ["b", "a"]


def test_rank_source_cap_diversity():
    """동일 소스는 source_cap개까지만 — 편중 소스 독점 방지."""
    cands = [_c(f"x{i}", sent=0.9 - i * 0.01, source="PRN") for i in range(10)]
    cands += [_c("other", sent=0.2, source="Reuters")]
    got = rank_headlines(cands, n=12, source_cap=GROUNDING_SOURCE_CAP)
    prn = [c for c in got if c["source"] == "PRN"]
    assert len(prn) == GROUNDING_SOURCE_CAP  # cap 초과 컷
    assert any(c["source"] == "Reuters" for c in got)  # 다양성 확보


def test_rank_top_n_limit():
    got = rank_headlines([_c(f"n{i}", sent=0.5, source=f"src{i}") for i in range(30)], n=12)
    assert len(got) == 12


def test_rank_empty_input():
    assert rank_headlines([]) == []


def test_rank_fully_deterministic():
    """완전 tie(감성·ec·pub 동일) → str(id) 안정 정렬. 재실행 동일."""
    cands = [_c("b", sent=0.5, source="A"), _c("a", sent=0.5, source="B"), _c("c", sent=0.5, source="C")]
    r1 = [c["id"] for c in rank_headlines(cands)]
    r2 = [c["id"] for c in rank_headlines(list(reversed(cands)))]
    assert r1 == r2 == ["c", "b", "a"]  # str(id) desc


# ── DB 페치(is_archived 무필터 함정 회귀) ──


@pytest.mark.django_db
def test_fetch_includes_archived_articles():
    """★함정 회귀: is_archived=True 과거 기사도 그라운딩 후보에 포함되어야 한다.

    archive_old_articles가 6개월+ 과거분을 soft delete 처리해도 이웃일 맥락이 벙어리가 되면 안 됨.
    """
    from services.news.models import NewsArticle

    day = datetime.date(2024, 5, 6)
    ts = datetime.datetime(2024, 5, 6, 12, 0, tzinfo=datetime.timezone.utc)
    NewsArticle.objects.create(url="https://ex.com/active", title="active", source="R",
                               published_at=ts, is_archived=False, sentiment_score=0.5)
    NewsArticle.objects.create(url="https://ex.com/archived", title="archived", source="B",
                               published_at=ts, is_archived=True, sentiment_score=0.9)

    got = fetch_day_candidates(day)
    urls = {c["url"] for c in got}
    assert "https://ex.com/active" in urls
    assert "https://ex.com/archived" in urls, "is_archived=True 기사가 그라운딩에서 누락됨(함정 재발)"


@pytest.mark.django_db
def test_select_grounding_empty_day_returns_empty():
    """그날 헤드라인 0건 → 빈 리스트(억지 생성 금지 신호)."""
    assert select_grounding(datetime.date(2020, 1, 1)) == []


@pytest.mark.django_db
def test_fetch_window_is_calendar_day():
    """창 = published_at__date == T (DB TZ 캘린더일). 인접일은 제외."""
    from services.news.models import NewsArticle

    day = datetime.date(2024, 5, 6)
    NewsArticle.objects.create(url="https://ex.com/onday", title="onday", source="R",
                               published_at=datetime.datetime(2024, 5, 6, 9, 0, tzinfo=datetime.timezone.utc),
                               sentiment_score=0.4)
    NewsArticle.objects.create(url="https://ex.com/nextday", title="nextday", source="R",
                               published_at=datetime.datetime(2024, 5, 8, 9, 0, tzinfo=datetime.timezone.utc),
                               sentiment_score=0.4)
    urls = {c["url"] for c in fetch_day_candidates(day)}
    assert "https://ex.com/onday" in urls
    assert "https://ex.com/nextday" not in urls
