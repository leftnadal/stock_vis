"""
EventGroup 리더 어댑터 단위 테스트 (M2 v1.1 reader 전환 — Slice A).

검증:
- 게이팅 중앙집중: kept(is_hidden=False)만 반환, gated 숨김.
- n3 이름(EventGroup.name) + core/satellite 멤버 + cohesion 노출.
- 단일 그룹 조회: kept만, gated/부재는 None.
- N+1 없음(prefetch).
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from apps.chain_sight.services import event_group_reader as reader
from packages.shared.stocks.models import Stock


def _mk_stock(sym):
    return Stock.objects.create(symbol=sym, stock_name=f"{sym} Inc.", sector="Technology")


def _mk_group(slug, name, cohesion, is_hidden, members):
    """members = [(symbol, role, edge_confidence, anchor_symbol)]."""
    eg = EventGroup.objects.create(
        name=name,
        slug=slug,
        source="news_jaccard",
        confidence=0.5,
        cohesion=cohesion,
        name_candidates={"n2": name, "n3": name, "terms": name.split()},
        member_count=len(members),
        core_count=sum(1 for m in members if m[1] == "core"),
        is_hidden=is_hidden,
    )
    for sym, role, ec, anchor in members:
        GroupMembership.objects.create(
            group=eg, symbol_id=sym, role=role,
            edge_confidence=ec, anchor_symbol=anchor,
        )
    return eg


@pytest.fixture
def shadow(db):
    for s in ["A", "B", "C", "D", "E", "F", "G", "X", "Y", "Z"]:
        _mk_stock(s)
    # kept 1: cohesion 0.8, 코어 A,B + 위성 C
    _mk_group("grp-a", "alpha beta gamma", 0.8, False, [
        ("A", "core", 0.9, ""), ("B", "core", 0.7, ""), ("C", "satellite", 0.3, "A"),
    ])
    # kept 2: cohesion 0.5, 코어 D,E
    _mk_group("grp-d", "delta epsilon", 0.5, False, [
        ("D", "core", 0.6, ""), ("E", "core", 0.6, ""),
    ])
    # gated (is_hidden=True): cohesion 0.1 — 어댑터가 숨겨야 함
    _mk_group("grp-x", "xray yankee zulu", 0.1, True, [
        ("X", "core", 0.4, ""), ("Y", "core", 0.4, ""), ("Z", "satellite", 0.2, "X"),
    ])


class TestKeptOnly:
    def test_excludes_gated(self, shadow):
        groups = reader.get_kept_event_groups()
        slugs = {g["slug"] for g in groups}
        assert slugs == {"grp-a", "grp-d"}
        assert "grp-x" not in slugs  # gated 숨김

    def test_count_matches_kept(self, shadow):
        assert len(reader.get_kept_event_groups()) == 2


class TestShape:
    def test_n3_name_and_cohesion(self, shadow):
        g = next(g for g in reader.get_kept_event_groups() if g["slug"] == "grp-a")
        assert g["name"] == "alpha beta gamma"  # n3 이름(EventGroup.name)
        assert g["cohesion"] == 0.8
        assert g["core_count"] == 2
        assert g["member_count"] == 3

    def test_core_satellite_members(self, shadow):
        g = next(g for g in reader.get_kept_event_groups() if g["slug"] == "grp-a")
        roles = {m["symbol"]: m["role"] for m in g["members"]}
        assert roles == {"A": "core", "B": "core", "C": "satellite"}

    def test_core_listed_before_satellite(self, shadow):
        g = next(g for g in reader.get_kept_event_groups() if g["slug"] == "grp-a")
        first_sat = next(i for i, m in enumerate(g["members"]) if m["role"] == "satellite")
        last_core = max(i for i, m in enumerate(g["members"]) if m["role"] == "core")
        assert last_core < first_sat  # 코어 먼저


class TestSort:
    def test_cohesion_desc(self, shadow):
        groups = reader.get_kept_event_groups()
        cohesions = [g["cohesion"] for g in groups]
        assert cohesions == sorted(cohesions, reverse=True)


class TestSingle:
    def test_get_kept_group(self, shadow):
        g = reader.get_event_group("grp-a")
        assert g is not None
        assert g["name"] == "alpha beta gamma"

    def test_get_gated_returns_none(self, shadow):
        assert reader.get_event_group("grp-x") is None  # gated → None

    def test_get_missing_returns_none(self, shadow):
        assert reader.get_event_group("nope") is None


class TestNoNPlusOne:
    def test_bounded_queries(self, shadow):
        # 그룹 수와 무관하게 쿼리 수 일정(prefetch). 2 그룹 → ≤3 쿼리.
        with CaptureQueriesContext(connection) as ctx:
            groups = reader.get_kept_event_groups()
            _ = [m["symbol"] for g in groups for m in g["members"]]
        assert len(ctx) <= 3, f"N+1 의심: {len(ctx)} 쿼리"
