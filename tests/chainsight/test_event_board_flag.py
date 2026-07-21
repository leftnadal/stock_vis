"""
이벤트 보드 그룹 소스 플래그 배선 테스트 (M2 v1.1 보드 전환 — Slice A+B).

검증:
- OFF(기본): theme_tags 그룹핑·드릴다운 = 오늘과 IDENTICAL, name 키 없음.
- ON: EventGroup(kept만·slug 키·n3 표시명) + 드릴다운 eg:{slug} leadership(재계산 없음).
- 게이팅: gated 그룹 보드/드릴다운 미노출.
"""

from datetime import date

import pytest
from django.test import override_settings

from apps.chain_sight.models import CompanyChainProfile, StockAttentionScore
from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from apps.chain_sight.models.leadership import StockLeadershipScore
from apps.chain_sight.serializers.event_board import EventBoardItemSerializer
from apps.chain_sight.services.attention_service import get_event_board, get_event_ranking
from apps.chain_sight.services.leadership_eventgroup import (
    attach_leadership_eg,
    eg_theme_key,
)
from packages.shared.stocks.models import Stock

AS_OF = date(2026, 6, 26)

OFF = dict(CHAINSIGHT_GROUP_SOURCE="theme_tags")
ON = dict(CHAINSIGHT_GROUP_SOURCE="event_group")


def _stock(sym):
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Tech"}
    )[0]


def _score(sym, score, ret=0.01):
    _stock(sym)
    StockAttentionScore.objects.create(
        symbol_id=sym, date=AS_OF, score=score, volume_z=0.0,
        volatility_pct=0.5, return_pct=0.5, raw_return=ret, is_low_liquidity=False,
    )


def _profile(sym, tags):
    CompanyChainProfile.objects.update_or_create(symbol_id=sym, defaults={"theme_tags": tags})


def _eg(slug, name, members, is_hidden=False):
    """members=[(sym, role)]."""
    eg = EventGroup.objects.create(
        name=name, slug=slug, source="news_jaccard", confidence=0.5, cohesion=0.5,
        member_count=len(members), core_count=sum(1 for _, r in members if r == "core"),
        is_hidden=is_hidden,
    )
    for sym, role in members:
        GroupMembership.objects.create(group=eg, symbol_id=sym, role=role)
    return eg


def _eg_lead(slug, sym, window, beta, kind):
    StockLeadershipScore.objects.create(
        stock_id=sym, theme=eg_theme_key(slug), window=window, as_of_date=AS_OF,
        theme_beta=beta, trend_quality=0.5, benchmark_kind=kind, obs_count=20,
    )


@pytest.fixture
def world(db):
    # 종목 + attention
    for sym, sc in [("AMD", 80), ("INTC", 60), ("NVDA", 90), ("MU", 40), ("AAPL", 30)]:
        _score(sym, sc)
    # OFF용 theme_tags
    for sym in ["AMD", "INTC", "NVDA"]:
        _profile(sym, ["Semiconductors"])
    _profile("MU", ["Semiconductors"])
    _profile("AAPL", ["Tech Hardware"])
    # ON용 kept EventGroup: 코어 AMD/INTC/NVDA + 위성 MU/AAPL
    _eg("news-amd-1", "intel devices semiconductor",
        [("AMD", "core"), ("INTC", "core"), ("NVDA", "core"), ("MU", "satellite"), ("AAPL", "satellite")])
    # gated 그룹(숨김)
    _stock("XYZ"); _score("XYZ", 50)
    _eg("news-x-9", "hidden group", [("XYZ", "core")], is_hidden=True)
    # eg leadership(드릴다운, 재계산 없음 — 사전 적재 모사)
    for sym in ["AMD", "INTC", "NVDA"]:
        _eg_lead("news-amd-1", sym, 20, 1.1, "core_loo")
    for sym in ["MU", "AAPL"]:
        _eg_lead("news-amd-1", sym, 20, 0.2, "sat_coremean")


class TestBoardOFF:
    @override_settings(**OFF)
    def test_off_uses_theme_tags(self, world):
        board = get_event_board(AS_OF)
        themes = {b["theme"] for b in board}
        assert "Semiconductors" in themes  # 섹터명 그룹핑
        assert "news-amd-1" not in themes  # slug 아님

    @override_settings(**OFF)
    def test_off_no_name_key(self, world):
        board = get_event_board(AS_OF)
        assert all("name" not in b for b in board)  # OFF엔 name 없음(IDENTICAL)

    @override_settings(**OFF)
    def test_off_serializer_omits_name(self, world):
        board = get_event_board(AS_OF)
        data = EventBoardItemSerializer(board, many=True).data
        assert all("name" not in row for row in data)  # 응답 스키마 IDENTICAL


class TestBoardON:
    @override_settings(**ON)
    def test_on_uses_event_group_slug_and_name(self, world):
        board = get_event_board(AS_OF)
        assert len(board) == 1  # kept 1그룹(gated 제외)
        item = board[0]
        assert item["theme"] == "news-amd-1"  # 키=slug
        assert item["name"] == "intel devices semiconductor"  # 표시명=n3
        assert item["member_count"] == 5

    @override_settings(**ON)
    def test_on_gated_hidden(self, world):
        board = get_event_board(AS_OF)
        assert all(b["theme"] != "news-x-9" for b in board)  # gated 미노출

    @override_settings(**ON)
    def test_on_serializer_includes_name(self, world):
        board = get_event_board(AS_OF)
        data = EventBoardItemSerializer(board, many=True).data
        assert data[0]["name"] == "intel devices semiconductor"


class TestRankingFlag:
    @override_settings(**OFF)
    def test_off_ranking_by_theme_tags(self, world):
        r = get_event_ranking("Semiconductors", AS_OF)
        syms = {x["symbol"] for x in r}
        assert syms == {"AMD", "INTC", "NVDA", "MU"}  # theme_tags 멤버

    @override_settings(**ON)
    def test_on_ranking_by_event_group_slug(self, world):
        r = get_event_ranking("news-amd-1", AS_OF)
        syms = {x["symbol"] for x in r}
        assert syms == {"AMD", "INTC", "NVDA", "MU", "AAPL"}  # EventGroup 멤버(core+sat)

    @override_settings(**ON)
    def test_on_ranking_gated_empty(self, world):
        assert get_event_ranking("news-x-9", AS_OF) == []  # gated slug → 빈 결과


class TestAttachLeadershipEg:
    @override_settings(**ON)
    def test_eg_leadership_read_only_core_sat(self, world):
        r = get_event_ranking("news-amd-1", AS_OF)
        r = attach_leadership_eg(r, "news-amd-1", AS_OF, 20)
        by = {x["symbol"]: x for x in r}
        assert by["AMD"]["theme_beta"] == 1.1   # core_loo 행 읽음
        assert by["MU"]["theme_beta"] == 0.2     # sat_coremean 행 읽음
        assert by["AMD"]["trend_quality"] == 0.5

    @override_settings(**ON)
    def test_eg_leadership_missing_symbol_null(self, world):
        # eg 행 없는 종목 → 지표 None(키 노출)
        r = [{"symbol": "GHOST"}]
        r = attach_leadership_eg(r, "news-amd-1", AS_OF, 20)
        assert r[0]["theme_beta"] is None
        assert r[0]["is_fallback"] is False

    def test_legacy_leadership_rows_untouched(self, world):
        # attach_leadership_eg는 eg: 행만 읽고 레거시(theme=섹터명) 행 생성/변경 안 함
        before = StockLeadershipScore.objects.exclude(theme__startswith="eg:").count()
        attach_leadership_eg([{"symbol": "AMD"}], "news-amd-1", AS_OF, 20)
        assert StockLeadershipScore.objects.exclude(theme__startswith="eg:").count() == before


class TestBoardMembers:
    """⑳-2 S4(additive): 구성 티커 목록 — 카드 제목 티커 병기용."""

    @override_settings(**ON)
    def test_on_includes_members(self, world):
        board = get_event_board(AS_OF)
        item = board[0]  # news-amd-1
        assert "members" in item
        assert set(item["members"]) == {"AMD", "INTC", "NVDA", "MU", "AAPL"}
        assert len(item["members"]) == item["member_count"]

    @override_settings(**ON)
    def test_serializer_includes_members(self, world):
        board = get_event_board(AS_OF)
        data = EventBoardItemSerializer(board, many=True).data
        assert set(data[0]["members"]) == {"AMD", "INTC", "NVDA", "MU", "AAPL"}

    @override_settings(**OFF)
    def test_off_includes_members(self, world):
        board = get_event_board(AS_OF)
        semi = next(b for b in board if b["theme"] == "Semiconductors")
        assert "members" in semi
        assert set(semi["members"]) == {"AMD", "INTC", "NVDA", "MU"}
