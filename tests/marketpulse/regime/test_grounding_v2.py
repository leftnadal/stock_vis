"""SELECT-V2 grounding_v2 결정론 선별 단위 테스트 (순수함수, DB 무의존).

핵심 회귀 고정: macro 어휘 점수·티커노이즈 가드·품질 하한(빈 결과)·near-dup 접기·
source_cap·완전 결정론·provenance/버전 태그. v1 대비 개선(고감정 개별기업 < macro)의 못.
"""
import uuid
from datetime import datetime, timezone

import pytest

from apps.market_pulse.regime.grounding_v2 import (
    SELECT_VERSION,
    macro_score,
    rank_headlines_v2,
    select_grounding_v2,
)


def _c(title, *, summary="", source="Reuters", sentiment=0.0, ec=0, ts="2024-05-16T12:00:00+00:00", id=None):
    return {
        "id": id or uuid.uuid4(),
        "title": title,
        "summary": summary,
        "url": f"https://ex.com/{abs(hash(title)) % 10**8}",
        "source": source,
        "sentiment_score": sentiment,
        "entity_count": ec,
        "published_at": datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
    }


# ── macro_score (순수) ──
def test_score_strong_title_high():
    s, hits = macro_score("Fed holds interest rate decision as inflation cools", "")
    assert s >= 3.0 and any("inflation" in h or "interest rate decision" in h for h in hits)


def test_score_empty_when_no_macro():
    s, hits = macro_score("Acme Corp announces new CEO appointment", "Leadership change at Acme.")
    assert s == 0.0 and hits == []


def test_score_summary_weighted_lower_than_title():
    s_title, _ = macro_score("inflation surges", "")
    s_summ, _ = macro_score("Acme earnings beat", "analysts cite inflation pressure")
    assert s_title > s_summ > 0


def test_ticker_noise_penalizes_index_name_falsepositive():
    # "S&P 500 ETF" 티커/펀드명 오매치 → 페널티로 중화
    clean, _ = macro_score("S&P 500 hits record as bull market accelerates", "")
    noisy, _ = macro_score("ProShares S&P 500 High Income ETF NYSEARCA:ISPY", "")
    assert clean > noisy  # 같은 s&p 500 매치라도 ETF 보일러플레이트는 감점


def test_score_deterministic():
    a = macro_score("Fed rate cut and CPI report", "treasury yield falls")
    b = macro_score("Fed rate cut and CPI report", "treasury yield falls")
    assert a == b


# ── rank_headlines_v2 ──
def test_macro_outranks_high_sentiment_company_news():
    """v2 핵심 개선: 고감정 개별기업(v1 상위) < macro 헤드라인."""
    cands = [
        _c("Acme soars on blowout earnings", sentiment=0.95, ec=8, source="Yahoo Finance"),
        _c("Fed signals rate cut as inflation eases", sentiment=0.1, ec=1, source="Reuters"),
    ]
    out = rank_headlines_v2(cands, n=6)
    assert out[0]["title"].startswith("Fed signals")  # macro가 1위
    assert "Acme" not in out[0]["title"]


def test_below_threshold_excluded_empty_ok():
    """품질 하한: macro 신호 없는 날 → 빈 결과(억지 채움 금지)."""
    cands = [_c("Acme names new CFO"), _c("Beta Inc opens factory")]
    assert rank_headlines_v2(cands) == []


def test_near_dup_titles_collapsed_keep_highest():
    """신디케이션 near-dup 접기 — 정규화 동일 제목 1건만(최고점)."""
    cands = [
        _c("Fed cuts interest rate by 25 bps!", source="PR Newswire"),      # 감점 소스
        _c("Fed cuts interest rate by 25 bps.", source="Reuters"),          # 가점 소스 → 유지
    ]
    out = rank_headlines_v2(cands, n=6)
    assert len(out) == 1 and out[0]["source"] == "Reuters"


def test_source_cap_enforced():
    cands = [
        _c(f"Fed inflation update {i}", source="PR Newswire", id=uuid.UUID(int=i))
        for i in range(5)
    ]
    out = rank_headlines_v2(cands, n=6, source_cap=3, min_score=0.5)
    assert sum(1 for o in out if o["source"] == "PR Newswire") <= 3


def test_provenance_and_version_tag():
    cands = [_c("Treasury yield curve inverts amid recession fears", ec=2)]
    out = rank_headlines_v2(cands, n=6)
    assert len(out) == 1
    o = out[0]
    for k in ("id", "url", "title", "source", "sentiment_score", "entity_count", "published_at"):
        assert k in o                       # v1 호환 키 보존(REGEN-V2 provenance)
    assert o["select_version"] == SELECT_VERSION
    assert o["rank"] == 1 and o["score"] > 0 and isinstance(o["hits"], list)
    assert "summary" not in o               # 랭킹 재료였을 뿐 반환 스키마 제외


def test_full_determinism_same_order():
    cands = [
        _c("CPI report shows inflation cooling", ec=1, id=uuid.UUID(int=1)),
        _c("Jobs report beats as labor market tightens", ec=1, id=uuid.UUID(int=2)),
        _c("Oil prices spike on geopolitical risk", ec=1, id=uuid.UUID(int=3)),
    ]
    r1 = [o["id"] for o in rank_headlines_v2(cands, n=6)]
    r2 = [o["id"] for o in rank_headlines_v2(list(reversed(cands)), n=6)]
    assert r1 == r2  # 입력 순서 무관 결정론


def test_n_cap_respected():
    cands = [_c(f"Fed inflation note {i}", source=f"src{i}", id=uuid.UUID(int=i)) for i in range(10)]
    out = rank_headlines_v2(cands, n=3, min_score=0.5)
    assert len(out) == 3
    assert [o["rank"] for o in out] == [1, 2, 3]


# ── select_grounding_v2 (DB 페치 경로) — 빈 날 방어 ──
@pytest.mark.django_db
def test_select_grounding_v2_empty_day_returns_list():
    import datetime as dt
    assert select_grounding_v2(dt.date(2099, 1, 1)) == []
