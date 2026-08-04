"""⑳-3 REVIEW-P2 S1 — apply_review_verdicts 로더 파서·반영 규칙 테스트."""

import pytest

from apps.chain_sight.management.commands.apply_review_verdicts import (
    VerdictParseError,
    apply_plan,
    build_plan,
    parse_verdict,
    status_targets,
)
from apps.chain_sight.models import RelationConfidence


def _row(pair, rtype, verdict):
    return {"symbol_pair": pair, "relation_type": rtype, "human_verdict": verdict}


def _rc(a, b, rtype):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, relation_category="truth",
    )


# ── 파서 단위 (어휘 5종 + 미인지 거부) ──
class TestParseVerdict:
    def test_simple_ok_drop_hold(self):
        assert parse_verdict("OK") == ("OK", None)
        assert parse_verdict("DROP") == ("DROP", None)
        assert parse_verdict("HOLD") == ("HOLD", None)

    def test_change_with_type(self):
        assert parse_verdict("CHANGE:COMPETES_WITH") == ("CHANGE", "COMPETES_WITH")

    def test_change_rev_precedence_over_change(self):
        # 'CHANGE_REV:'가 'CHANGE'를 문자열로 포함 — 접두사 우선순위가 정확해야 함
        assert parse_verdict("CHANGE_REV:SUPPLIES_TO") == ("CHANGE_REV", "SUPPLIES_TO")

    def test_whitespace_stripped(self):
        assert parse_verdict("  OK ") == ("OK", None)
        assert parse_verdict("CHANGE: COMPETES_WITH ") == ("CHANGE", "COMPETES_WITH")

    @pytest.mark.parametrize("bad", ["MAYBE", "", "CHANGE", "change:x", "DROP2", "OKAY"])
    def test_unrecognized_raises(self, bad):
        with pytest.raises(VerdictParseError):
            parse_verdict(bad)


# ── 반영 규칙 (소형 fixture) ──
@pytest.mark.django_db
class TestReflection:
    def test_ok_drop_hold_status_mapping(self):
        _rc("AAA", "BBB", "PEER_OF")
        _rc("CCC", "DDD", "PEER_OF")
        _rc("EEE", "FFF", "PEER_OF")
        rows = [
            _row("AAA↔BBB", "PEER_OF", "OK"),
            _row("CCC↔DDD", "PEER_OF", "DROP"),
            _row("EEE↔FFF", "PEER_OF", "HOLD"),
        ]
        p = build_plan(rows)
        assert p["unrecognized"] == [] and p["unmatched"] == []
        assert status_targets(p["plan"]) == {"approved": 1, "rejected": 1, "pending": 1}
        apply_plan(p["plan"])
        assert RelationConfidence.objects.get(symbol_a="AAA").domain_review_status == "approved"
        assert RelationConfidence.objects.get(symbol_a="CCC").domain_review_status == "rejected"
        assert RelationConfidence.objects.get(symbol_a="EEE").domain_review_status == "pending"

    def test_change_type_and_approved(self):
        _rc("INCY", "REGN", "PARTNER_WITH")
        rows = [_row("INCY↔REGN", "PARTNER_WITH", "CHANGE:COMPETES_WITH")]
        p = build_plan(rows)
        assert p["unrecognized"] == [] and p["unmatched"] == []
        res = apply_plan(p["plan"])
        assert res["change"] == 1
        obj = RelationConfidence.objects.get(symbol_a="INCY", symbol_b="REGN")
        assert obj.relation_type == "COMPETES_WITH"
        assert obj.domain_review_status == "approved"
        assert obj.neo4j_dirty is True

    def test_change_rev_skipped_in_s1(self):
        rc = _rc("ANET", "AVGO", "COMPETES_WITH")
        rows = [_row("ANET↔AVGO", "COMPETES_WITH", "CHANGE_REV:SUPPLIES_TO")]
        p = build_plan(rows)
        # 계획엔 포함되나 apply에서 상태 미변경(S2 위임)
        assert any(x[0] == "CHANGE_REV" for x in p["plan"])
        assert status_targets(p["plan"]) == {"approved": 0, "rejected": 0, "pending": 0}
        apply_plan(p["plan"])
        rc.refresh_from_db()
        assert rc.relation_type == "COMPETES_WITH"  # 불변
        assert rc.domain_review_status is None       # S1 미반영

    def test_forward_exact_matching_no_reverse(self):
        # DB엔 (SNDK→WDC)만 존재. CSV가 'WDC↔SNDK'면 forward 0건 → unmatched
        _rc("SNDK", "WDC", "DEPENDS_ON")
        rows = [_row("WDC↔SNDK", "DEPENDS_ON", "OK")]
        p = build_plan(rows)
        assert p["unmatched"] == [("WDC↔SNDK", "DEPENDS_ON", 0)]
        assert p["plan"] == []

    def test_missing_record_is_unmatched(self):
        rows = [_row("NOPE↔NADA", "PEER_OF", "OK")]
        p = build_plan(rows)
        assert p["unmatched"] == [("NOPE↔NADA", "PEER_OF", 0)]

    def test_invalid_change_type_is_unrecognized(self):
        _rc("AAA", "BBB", "PEER_OF")
        rows = [_row("AAA↔BBB", "PEER_OF", "CHANGE:NOT_A_REAL_TYPE")]
        p = build_plan(rows)
        assert len(p["unrecognized"]) == 1
        assert p["plan"] == []

    def test_idempotent_reapply(self):
        _rc("AAA", "BBB", "PEER_OF")
        rows = [_row("AAA↔BBB", "PEER_OF", "OK")]
        plan = build_plan(rows)["plan"]
        apply_plan(plan)
        first = RelationConfidence.objects.get(symbol_a="AAA").domain_review_status
        # 재실행 — 동일 결과
        plan2 = build_plan(rows)["plan"]
        apply_plan(plan2)
        second = RelationConfidence.objects.get(symbol_a="AAA").domain_review_status
        assert first == second == "approved"

    def test_change_rerun_detects_already_applied(self):
        # CHANGE 반영 후 원 키(PARTNER_WITH)가 사라짐 → 재실행 시 unmatched(H-C) 대신 already_applied
        _rc("INCY", "REGN", "PARTNER_WITH")
        rows = [_row("INCY↔REGN", "PARTNER_WITH", "CHANGE:COMPETES_WITH")]
        apply_plan(build_plan(rows)["plan"])  # 1차: 타입 교체
        p2 = build_plan(rows)                  # 2차: 원 키 소멸
        assert p2["unmatched"] == []
        assert p2["already_applied"] == [("INCY↔REGN", "COMPETES_WITH")]
        assert not any(x[0] == "CHANGE" for x in p2["plan"])

    def test_verdict_counts_tallied(self):
        _rc("AAA", "BBB", "PEER_OF")
        _rc("CCC", "DDD", "PEER_OF")
        rows = [
            _row("AAA↔BBB", "PEER_OF", "OK"),
            _row("CCC↔DDD", "PEER_OF", "DROP"),
            _row("XXX↔YYY", "PEER_OF", "BOGUS"),  # 미인지 — 카운트 제외
        ]
        p = build_plan(rows)
        assert p["verdict_counts"]["OK"] == 1
        assert p["verdict_counts"]["DROP"] == 1
        assert len(p["unrecognized"]) == 1
