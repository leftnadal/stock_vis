"""⑳-3 REVIEW-P2 Part Q — a≠b 앱 레벨 자기루프 가드.

MIG-BUNDLE-1 A-1: 상류 배치 skip+로그 헬퍼(skip_self_loop) 커버리지 추가.
"""

import datetime

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.chain_sight.models import (
    CoMentionEdge,
    RelationConfidence,
    RelationPairSnapshot,
)
from apps.chain_sight.models.relation_discovery import SelfLoopError
from apps.chain_sight.utils import skip_self_loop


@pytest.mark.django_db
class TestSelfLoopGuard:
    def test_new_self_loop_rejected_on_create(self):
        with pytest.raises(SelfLoopError):
            RelationConfidence.objects.create(
                symbol_a="AAA", symbol_b="AAA", relation_type="PEER_OF",
                relation_category="truth",
            )

    def test_new_self_loop_rejected_via_update_or_create(self):
        # ORM create 경로(update_or_create)도 save()를 거치므로 가드가 잡는다
        with pytest.raises(SelfLoopError):
            RelationConfidence.objects.update_or_create(
                symbol_a="BBB", symbol_b="BBB", relation_type="SUPPLIES_TO",
                defaults={"relation_category": "truth"},
            )

    def test_non_self_loop_allowed(self):
        obj = RelationConfidence.objects.create(
            symbol_a="AAA", symbol_b="BBB", relation_type="PEER_OF",
            relation_category="truth",
        )
        assert obj.pk is not None

    # NOTE: A-4(SELFLOOP-DBCONSTRAINT) 이후 "레거시 self-loop 갱신 가능" 전제는 소멸.
    # 정제(A-2)로 기존 행 제거 + DB CheckConstraint 로 bulk_create 우회까지 차단되어
    # 자기루프 행 자체가 존재 불가. 아래 TestSelfLoopDBConstraint 가 그 불변식을 검증.


@pytest.mark.django_db
class TestSelfLoopDBConstraint:
    """A-4: symbol_a≠symbol_b / canonical_a≠canonical_b DB CheckConstraint.

    모델 save() 가드(SelfLoopError)는 ORM create 경로만 막는다. bulk_create·raw 는
    save() 를 우회하므로 DB 제약이 최종 방어선. 마이그 0034_selfloop_db_constraints.
    """

    def test_comentionedge_self_loop_rejected_by_db(self):
        # CoMentionEdge 는 save() 가드 없음 → create 도 DB 제약에 직행.
        with pytest.raises(IntegrityError):
            CoMentionEdge.objects.create(symbol_a="XXX", symbol_b="XXX")

    def test_relationconfidence_bulk_create_self_loop_rejected_by_db(self):
        # bulk_create 는 save() 가드 우회 → DB 제약이 잡는다.
        with pytest.raises(IntegrityError):
            RelationConfidence.objects.bulk_create([
                RelationConfidence(
                    symbol_a="DLR", symbol_b="DLR",
                    relation_type="DEPENDS_ON", relation_category="truth",
                )
            ])

    def test_relationpairsnapshot_self_loop_rejected_by_db(self):
        with pytest.raises(IntegrityError):
            RelationPairSnapshot.objects.create(
                canonical_a="ZZZ", canonical_b="ZZZ",
                period=datetime.date(2026, 1, 1),
                truth_max=0.0, market_max=0.0,
                relevance_opp=0.0, relevance_risk=0.0,
                last_observed_at=timezone.now(),
            )

    def test_distinct_pair_allowed_all_three(self):
        # 서로 다른 심볼 쌍은 3모델 모두 정상 저장.
        CoMentionEdge.objects.create(symbol_a="AAA", symbol_b="BBB")
        RelationPairSnapshot.objects.create(
            canonical_a="AAA", canonical_b="BBB",
            period=datetime.date(2026, 1, 1),
            truth_max=0.0, market_max=0.0,
            relevance_opp=0.0, relevance_risk=0.0,
            last_observed_at=timezone.now(),
        )
        assert CoMentionEdge.objects.filter(symbol_a="AAA").exists()
        assert RelationPairSnapshot.objects.filter(canonical_a="AAA").exists()


class TestSkipSelfLoopHelper:
    """A-1: 상류 배치 가드 — raise 대신 skip+구조화 로그."""

    def test_returns_true_and_logs_on_self_loop(self, caplog):
        with caplog.at_level("WARNING", logger="apps.chain_sight.utils"):
            skipped = skip_self_loop(
                "DLR", "DLR", relation_type="DEPENDS_ON", source="sec_8k"
            )
        assert skipped is True
        assert "self_loop_skipped" in caplog.text
        assert "source=sec_8k" in caplog.text
        assert "symbol=DLR" in caplog.text
        assert "relation_type=DEPENDS_ON" in caplog.text

    def test_returns_false_for_distinct_pair(self, caplog):
        with caplog.at_level("WARNING", logger="apps.chain_sight.utils"):
            skipped = skip_self_loop("DLR", "EXR", source="sec_8k")
        assert skipped is False
        assert "self_loop_skipped" not in caplog.text

    def test_custom_logger_receives_record(self, caplog):
        import logging

        custom = logging.getLogger("test.custom.selfloop")
        with caplog.at_level("WARNING", logger="test.custom.selfloop"):
            assert skip_self_loop("X", "X", source="unit", logger=custom) is True
        assert "self_loop_skipped" in caplog.text
