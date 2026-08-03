"""⑳-3 S3-MINDMAP S0 — backfill_review_domains 적재 규칙·보호 가드 테스트."""

import pytest

from apps.chain_sight.management.commands.backfill_review_domains import (
    apply_backfill,
    build_backfill_plan,
)
from apps.chain_sight.models import RelationConfidence


def _row(pair, rtype, verdict, ntag="", draft=""):
    return {
        "symbol_pair": pair, "relation_type": rtype, "human_verdict": verdict,
        "normalized_tag": ntag, "draft_domain": draft,
    }


def _rc(a, b, rtype, status=None):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, relation_category="truth",
        domain_review_status=status,
    )


@pytest.mark.django_db
class TestBackfillReviewDomains:
    def test_approved_ok_row_tagged(self):
        _rc("AAA", "BBB", "PEER_OF", status="approved")
        rows = [_row("AAA↔BBB", "PEER_OF", "OK", ntag="반도체·메모리", draft="HBM")]
        p = build_backfill_plan(rows)
        assert len(p["plan"]) == 1 and p["skipped"] == []
        apply_backfill(p["plan"])
        obj = RelationConfidence.objects.get(symbol_a="AAA")
        assert obj.relation_domain == "반도체·메모리"       # 승인본=normalized_tag
        assert obj.relation_domain_draft == "HBM"           # 초안=draft_domain

    def test_non_approved_skipped_protection(self):
        # pending 관계엔 태그를 쓰지 않는다(보호 가드)
        _rc("CCC", "DDD", "PEER_OF", status="pending")
        rows = [_row("CCC↔DDD", "PEER_OF", "OK", ntag="금융·결제")]
        p = build_backfill_plan(rows)
        assert p["plan"] == []
        assert p["skipped"] == [("CCC↔DDD", "PEER_OF", "비approved(pending)")]

    def test_no_tag_excluded(self):
        _rc("EEE", "FFF", "PEER_OF", status="approved")
        rows = [_row("EEE↔FFF", "PEER_OF", "OK", ntag="")]  # 태그 없음
        p = build_backfill_plan(rows)
        assert p["plan"] == [] and p["skipped"] == []  # 조용히 제외(폴백 대상)

    def test_drop_hold_excluded(self):
        _rc("GGG", "HHH", "PEER_OF", status="rejected")
        rows = [_row("GGG↔HHH", "PEER_OF", "DROP", ntag="무시됨")]
        p = build_backfill_plan(rows)
        assert p["plan"] == []

    def test_draft_empty_becomes_null(self):
        _rc("III", "JJJ", "PEER_OF", status="approved")
        rows = [_row("III↔JJJ", "PEER_OF", "OK", ntag="통신·네트워크", draft="")]
        apply_backfill(build_backfill_plan(rows)["plan"])
        obj = RelationConfidence.objects.get(symbol_a="III")
        assert obj.relation_domain == "통신·네트워크"
        assert obj.relation_domain_draft is None

    def test_idempotent(self):
        _rc("AAA", "BBB", "PEER_OF", status="approved")
        rows = [_row("AAA↔BBB", "PEER_OF", "OK", ntag="반도체·메모리", draft="HBM")]
        apply_backfill(build_backfill_plan(rows)["plan"])
        apply_backfill(build_backfill_plan(rows)["plan"])  # 재실행
        obj = RelationConfidence.objects.get(symbol_a="AAA")
        assert obj.relation_domain == "반도체·메모리"
