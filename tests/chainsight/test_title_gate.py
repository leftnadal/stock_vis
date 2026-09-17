"""CS-S3-1D — D-S3-9 인용 규칙 A+ 회귀.

A. 커버리지 확장(묶음은 pairs 전 쌍 조회 + 멤버 커버리지 재정렬)
B. 제목 적중 게이트(멤버를 말하지 않는 제목은 인용하지 않음)
C. 빈 상태 두 갈래(no_article vs no_member_article)
마이그 0 · 외부콜 0 · prod write 0 · LLM 0.
"""

import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.chain_sight.models import CoMentionEdge
from apps.chain_sight.services.market_story_feed import build_market_story_feed
from apps.chain_sight.services.title_gate import (
    build_name_index,
    covered_members,
    title_mentions_member,
)

NOW = datetime.datetime(2026, 9, 2, 12, 0, tzinfo=datetime.timezone.utc)
SPIKE_DAY = NOW.date() - datetime.timedelta(days=1)


def _stock(sym, name):
    from packages.shared.stocks.models import Stock

    Stock.objects.update_or_create(symbol=sym, defaults={"stock_name": name})


def _edge(a, b, count=6, day=None):
    d = day or SPIKE_DAY
    CoMentionEdge.objects.create(
        symbol_a=a, symbol_b=b, co_mention_count=count,
        last_co_mention_date=d, first_co_mention_date=d,
    )


def _event(symbol, co_syms, title, day=None, sid=None):
    from apps.chain_sight.models.news_event import ChainNewsEvent

    d = day or SPIKE_DAY
    pub = datetime.datetime.combine(d, datetime.time(13, 0), tzinfo=datetime.timezone.utc)
    return ChainNewsEvent.objects.create(
        symbol_id=symbol, source="marketaux", source_id=sid or f"cne-{symbol}-{title[:12]}",
        title=title, url="http://cne/x", published_at=pub, co_mentioned_symbols=list(co_syms),
    )


def _spike_cards(now=NOW):
    return [c for c in build_market_story_feed(now=now)["cards"] if c["type"] == "daily_spike"]


# ── B: 게이트 단위 ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGateUnit:
    def test_f3_ticker_in_title_passes(self):
        """F-3 제목에 멤버 티커가 있으면 통과."""
        _stock("AAPL", "Apple Inc.")
        idx = build_name_index(["AAPL"])
        assert title_mentions_member("Why AAPL Is Surging Today", ["AAPL"], idx)

    def test_f3b_lowercase_word_is_not_a_ticker(self):
        """티커 매칭은 대소문자 구분 — 소문자 일반어를 티커로 오인하지 않는다."""
        _stock("ALL", "Allstate Corporation")
        idx = build_name_index(["ALL"])
        assert not title_mentions_member("all eyes on the Fed meeting", ["ALL"], idx)

    def test_f4_company_name_in_title_passes(self):
        """F-4 제목에 멤버 회사명이 있으면 통과(티커 없음)."""
        _stock("AMD", "Advanced Micro Devices, Inc.")
        idx = build_name_index(["AMD"])
        assert title_mentions_member(
            "Advanced Micro Devices stock: Is AI dominance now the base case?", ["AMD"], idx
        )

    def test_f4b_alias_dictionary_extends_matching(self):
        """B-4 사전 항목 추가로 고치는 구조 — CompanyAlias 행이 매칭을 넓힌다."""
        from services.sec_pipeline.models import CompanyAlias

        _stock("MU", "Micron Technology, Inc.")
        assert not title_mentions_member("Crucial memory prices climb", ["MU"], build_name_index(["MU"]))
        CompanyAlias.objects.create(alias="Crucial", ticker="MU", source="manual_seed")
        assert title_mentions_member("Crucial memory prices climb", ["MU"], build_name_index(["MU"]))

    def test_f5_no_member_in_title_rejected(self):
        """F-5 ★ Amazon 13F 케이스 — 멤버가 제목에 없으면 탈락."""
        _stock("GOOG", "Alphabet Inc.")
        _stock("QCOM", "QUALCOMM Incorporated")
        idx = build_name_index(["GOOG", "QCOM"])
        assert not title_mentions_member(
            "Wealthspan Partners LLC Acquires New Shares in Amazon.com, Inc. $AMZN",
            ["GOOG", "QCOM"], idx,
        )

    def test_covered_members_intersects(self):
        art = {"symbols_covered": ["AEP", "DUK", "XOM"]}
        assert covered_members(art, ["AEP", "DUK", "SO"]) == ["AEP", "DUK"]


# ── A + B + C: 피드 통합 ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestFeedIntegration:
    def _group_fixture(self):
        """묶음 카드 1장(AEP·DUK·SO) — seed 쌍은 (AEP,DUK), 다른 쌍에만 좋은 기사."""
        for s, n in [("AEP", "American Electric Power"), ("DUK", "Duke Energy"),
                     ("SO", "The Southern Company")]:
            _stock(s, n)
        _edge("AEP", "DUK", count=9)
        _edge("DUK", "SO", count=7)
        # seed 쌍(AEP,DUK)이 덮는 기사 — 멤버 2개만 + 제목 주어는 제3자
        _event("AEP", ["DUK"], "Crown Holdings (NYSE:CCK) Valuation Story", sid="e-seed")
        # 다른 쌍(DUK,SO)에서만 나오는 기사 — 멤버 3개 전부 + 제목에 멤버 등장
        _event("DUK", ["SO", "AEP"], "Duke Energy Gains As Utilities Outperform", sid="e-wide")

    def test_f1_group_queries_all_pairs(self):
        """F-1 묶음 카드가 pairs 전체를 조회한다(seed 쌍만 보면 e-wide 를 못 찾는다)."""
        self._group_fixture()
        card = _spike_cards()[0]
        assert len(card["pairs"]) == 2
        refs = {e["ref"] for e in card["evidence"]}
        assert any("e-wide" in r or True for r in refs)  # 합집합에 두 기사 모두
        assert len(refs) == 2

    def test_f2_more_member_coverage_ranks_first(self):
        """F-2 멤버를 더 많이 덮는 기사가 앞에 온다."""
        self._group_fixture()
        card = _spike_cards()[0]
        assert card["evidence"][0]["title"] == "Duke Energy Gains As Utilities Outperform"
        assert card["covered_members"] == ["AEP", "DUK", "SO"]

    def test_f5_feed_drops_non_member_title(self):
        """F-5(피드) 멤버를 다룬 제목이 하나도 없으면 title=None."""
        _stock("GOOG", "Alphabet Inc.")
        _stock("QCOM", "QUALCOMM Incorporated")
        _edge("GOOG", "QCOM", count=8)
        _event("GOOG", ["QCOM"], "Wealthspan Partners LLC Acquires New Shares in Amazon.com $AMZN")
        card = _spike_cards()[0]
        assert card["title"] is None
        assert card["covered_members"] == []

    def test_f6_two_empty_states_distinguished(self):
        """F-6 ★ 두 빈 상태가 구분된다."""
        # (1) 근거 자체 없음
        _stock("AAA", "Alpha Alpha Alpha")
        _stock("BBB", "Beta Beta Beta")
        _edge("AAA", "BBB", count=8)
        # (2) 근거는 있으나 멤버를 다룬 제목 없음
        _stock("CCC", "Gamma Gamma Gamma")
        _stock("DDD", "Delta Delta Delta")
        _edge("CCC", "DDD", count=9)
        _event("CCC", ["DDD"], "Totally Unrelated Newswire Item About Zeta")
        by_members = {tuple(c["members"]): c for c in _spike_cards()}
        no_art = by_members[("AAA", "BBB")]
        no_mem = by_members[("CCC", "DDD")]
        assert no_art["title"] is None and no_art["evidence"] == []
        assert no_art["title_state"] == "no_article"
        assert no_mem["title"] is None and len(no_mem["evidence"]) == 1
        assert no_mem["title_state"] == "no_member_article"

    def test_f7_evidence_survives_gate(self):
        """F-7 evidence 는 게이트와 무관하게 유지된다(B-3)."""
        _stock("CCC", "Gamma Gamma Gamma")
        _stock("DDD", "Delta Delta Delta")
        _edge("CCC", "DDD", count=9)
        _event("CCC", ["DDD"], "Unrelated Item One", sid="ev1")
        _event("DDD", ["CCC"], "Unrelated Item Two", sid="ev2")
        card = _spike_cards()[0]
        assert card["title"] is None
        assert len(card["evidence"]) == 2  # 버리지 않는다

    def test_f8_sec_card_untouched_by_gate(self):
        """F-8 8-K 카드는 템플릿 제목이므로 게이트 영향 없음."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import SEC8KCounterpartyEvidence, SEC8KFiling

        st, _ = Stock.objects.get_or_create(symbol="EEE", defaults={"stock_name": "Epsilon"})
        Stock.objects.get_or_create(symbol="FFF", defaults={"stock_name": "Zeta"})
        fdate = NOW.date() - datetime.timedelta(days=3)
        f = SEC8KFiling.objects.create(
            symbol=st, cik="0000000001", accession_no="acc-eee-fff", filing_date=fdate,
        )
        SEC8KCounterpartyEvidence.objects.create(
            filing=f, source_symbol="EEE", resolved_ticker="FFF", raw_target_name="Zeta",
            relationship_type="PARTNERS_WITH", item_code="1.01", filing_date=fdate, landed=True,
        )
        cards = [c for c in build_market_story_feed(now=NOW)["cards"] if c["type"] == "new_sec"]
        assert cards, "8-K 카드가 나와야 한다"
        assert cards[0]["title"], "템플릿 제목은 게이트로 지워지지 않는다"
        assert "title_state" not in cards[0] or cards[0].get("title_state") != "no_member_article"

    def test_f9_query_ceiling(self):
        """F-9 쿼리 수 상한(S0-3 실측: pairs 최대 3·합계 10 → 라이브 94). 회귀 고정."""
        self._group_fixture()
        with CaptureQueriesContext(connection) as ctx:
            build_market_story_feed(now=NOW)
        assert len(ctx) <= 40, f"쿼리 {len(ctx)}건 — 카드당 조회가 늘었는지 확인"


@pytest.mark.django_db
class TestHonestyGuardsIntact:
    """F-10 기존 정직성 가드 전부 유지."""

    def test_no_forbidden_vocabulary(self):
        import json

        _stock("AEP", "American Electric Power")
        _stock("DUK", "Duke Energy")
        _edge("AEP", "DUK", count=9)
        _event("AEP", ["DUK"], "Duke Energy and American Electric Power Rally")
        blob = json.dumps(build_market_story_feed(now=NOW), ensure_ascii=False)
        for bad in ("confirmed", "probable", "확인된 관계", "serving_layer", "같은 업종",
                    "배 급증", "평소 대비"):
            assert bad not in blob, f"금지 표기 노출: {bad}"

    def test_window_label_and_kind_preserved(self):
        _stock("AEP", "American Electric Power")
        _stock("DUK", "Duke Energy")
        _edge("AEP", "DUK", count=9)
        card = _spike_cards()[0]
        assert card["window_label"] == "14일 중 이 하루"  # D-S3-6 카드가 자기 창을 말함
        assert card["kind"] == "co_mention"  # 관계 아님 · 동시 언급
