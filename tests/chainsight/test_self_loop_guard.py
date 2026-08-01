"""⑳-3 REVIEW-P2 Part Q — a≠b 앱 레벨 자기루프 가드."""

import pytest

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.models.relation_discovery import SelfLoopError


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

    def test_existing_self_loop_can_be_updated(self):
        # 기존 self-loop(레거시)은 소급 삭제/차단 아님 — 갱신·soft-drop은 통과.
        # bulk_create로 save() 가드 우회하여 레거시 self-loop 조성.
        RelationConfidence.objects.bulk_create([
            RelationConfidence(
                symbol_a="DLR", symbol_b="DLR", relation_type="DEPENDS_ON",
                relation_category="truth",
            )
        ])
        obj = RelationConfidence.objects.get(symbol_a="DLR", symbol_b="DLR")
        obj.domain_review_status = "rejected"  # soft-drop 갱신
        obj.save(update_fields=["domain_review_status"])  # adding=False → 통과
        obj.refresh_from_db()
        assert obj.domain_review_status == "rejected"
