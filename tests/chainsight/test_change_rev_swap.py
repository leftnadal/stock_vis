"""⑳-3 REVIEW-P2 S2 — CHANGE_REV 방향 스왑 게이트·반영 테스트."""

import pytest

from apps.chain_sight.management.commands.apply_review_verdicts import (
    apply_change_rev,
    build_plan,
    change_rev_gates,
)
from apps.chain_sight.models import RelationConfidence


def _row(pair, rtype, verdict):
    return {"symbol_pair": pair, "relation_type": rtype, "human_verdict": verdict}


def _rc(a, b, rtype, **kw):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, relation_category="truth", **kw
    )


@pytest.mark.django_db
class TestChangeRevSwap:
    def test_gates_pass_and_swap_applied(self):
        rc = _rc("ANET", "AVGO", "COMPETES_WITH")
        rc.relation_basis_summary = "SEC 10-K: Broadcom has acquired VMware."
        rc.save(update_fields=["relation_basis_summary"])
        rows = [_row("ANET↔AVGO", "COMPETES_WITH", "CHANGE_REV:SUPPLIES_TO")]
        plan = build_plan(rows)["plan"]

        ok, failures = change_rev_gates(plan[0][2], "SUPPLIES_TO")
        assert ok and failures == []

        res = apply_change_rev(plan)
        assert len(res["swapped"]) == 1 and res["held"] == []
        rc.refresh_from_db()
        assert rc.symbol_a == "AVGO" and rc.symbol_b == "ANET"  # 방향 스왑
        assert rc.relation_type == "SUPPLIES_TO"
        assert rc.canonical_direction == "a→b"
        assert rc.domain_review_status == "approved"
        assert rc.neo4j_dirty is True
        # 기반 텍스트 원문 보존(감사추적)
        assert rc.relation_basis_summary == "SEC 10-K: Broadcom has acquired VMware."

    def test_gate_fail_when_swap_target_exists_holds(self):
        # 스왑 결과 (AVGO→ANET SUPPLIES_TO)가 이미 존재 → G1/G3 실패 → HOLD
        rc = _rc("ANET", "AVGO", "COMPETES_WITH")
        _rc("AVGO", "ANET", "SUPPLIES_TO")  # 충돌 엣지 선존재
        rows = [_row("ANET↔AVGO", "COMPETES_WITH", "CHANGE_REV:SUPPLIES_TO")]
        plan = build_plan(rows)["plan"]

        ok, failures = change_rev_gates(plan[0][2], "SUPPLIES_TO")
        assert not ok
        assert any("G1" in f for f in failures) and any("G3" in f for f in failures)

        res = apply_change_rev(plan)
        assert res["swapped"] == [] and len(res["held"]) == 1
        rc.refresh_from_db()
        assert rc.relation_type == "COMPETES_WITH"  # 스왑 미실행
        assert rc.symbol_a == "ANET" and rc.symbol_b == "AVGO"
        assert rc.domain_review_status == "pending"  # HOLD 전환

    def test_idempotent_rerun_detects_already_swapped(self):
        rc = _rc("ANET", "AVGO", "COMPETES_WITH")
        rows = [_row("ANET↔AVGO", "COMPETES_WITH", "CHANGE_REV:SUPPLIES_TO")]
        apply_change_rev(build_plan(rows)["plan"])  # 1차 스왑

        # 2차: 원 키 소멸 → already_swapped 감지, unmatched 아님
        p2 = build_plan(rows)
        assert p2["unmatched"] == []
        assert p2["already_swapped"] == [("ANET↔AVGO", "SUPPLIES_TO")]
        assert not any(x[0] == "CHANGE_REV" for x in p2["plan"])
        res2 = apply_change_rev(p2["plan"])
        assert res2["swapped"] == [] and res2["held"] == []  # no-op
