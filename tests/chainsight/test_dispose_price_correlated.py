"""D-RC-PC-DISPOSE (RC-A-1 PART 3) — PRICE_CORRELATED 처분 커맨드 회귀.

dry-run 안전(무삭제)·아카이브 정확·--apply 가드(아카이브 필수)·삭제 후 검증(PEER_OF 불변).
Neo4j 프로브는 mock(테스트 격리).
"""

import json
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.chain_sight.models import RelationConfidence

NEO4J_PROBE = (
    "apps.chain_sight.management.commands."
    "dispose_price_correlated.Command._probe_neo4j_pc_edges"
)


def _seed():
    # PC 3행 + PEER_OF 2행(무접촉 대상) + CO_MENTIONED 1행
    for i, sb in enumerate(["P1", "P2", "P3"]):
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b=sb, relation_type="PRICE_CORRELATED",
            relation_category="market", market_score=0.60, truth_score=0.0,
        )
    for sb in ["Q1", "Q2"]:
        RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b=sb, relation_type="PEER_OF",
            relation_category="truth", truth_score=0.85,
        )
    RelationConfidence.objects.create(
        symbol_a="AAA", symbol_b="C1", relation_type="CO_MENTIONED",
        relation_category="market", market_score=0.35,
    )


@pytest.mark.django_db
def test_dry_run_does_not_delete():
    _seed()
    with mock.patch(NEO4J_PROBE):
        call_command("dispose_price_correlated")
    assert RelationConfidence.objects.filter(relation_type="PRICE_CORRELATED").count() == 3


@pytest.mark.django_db
def test_archive_dumps_all_rows(tmp_path):
    _seed()
    arch = tmp_path / "pc.jsonl"
    with mock.patch(NEO4J_PROBE):
        call_command("dispose_price_correlated", archive=str(arch))
    lines = arch.read_text().strip().splitlines()
    assert len(lines) == 3
    row = json.loads(lines[0])
    assert row["relation_type"] == "PRICE_CORRELATED"
    assert "market_score" in row and "symbol_a" in row
    # dry-run이므로 여전히 미삭제
    assert RelationConfidence.objects.filter(relation_type="PRICE_CORRELATED").count() == 3


@pytest.mark.django_db
def test_apply_without_archive_errors():
    _seed()
    with mock.patch(NEO4J_PROBE), pytest.raises(CommandError):
        call_command("dispose_price_correlated", apply=True)
    # 삭제 안 됨
    assert RelationConfidence.objects.filter(relation_type="PRICE_CORRELATED").count() == 3


@pytest.mark.django_db
def test_apply_with_archive_deletes_and_preserves_peer(tmp_path):
    _seed()
    arch = tmp_path / "pc.jsonl"
    with mock.patch(NEO4J_PROBE):
        call_command("dispose_price_correlated", archive=str(arch), apply=True)
    assert RelationConfidence.objects.filter(relation_type="PRICE_CORRELATED").count() == 0
    # PEER_OF·CO_MENTIONED 무접촉
    assert RelationConfidence.objects.filter(relation_type="PEER_OF").count() == 2
    assert RelationConfidence.objects.filter(relation_type="CO_MENTIONED").count() == 1
