"""⑳-3 S3-MINDMAP S1 — L1 자동화 스위치 + 검수 verdict 270 보호 가드."""

import pytest
from django.test import override_settings

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services import domain_tagging as dt


def _rc(a, b, rtype="SUPPLIES_TO", status=None, mc=None, basis=""):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype, relation_category="truth",
        domain_review_status=status, domain_machine_check=mc,
        relation_basis_summary=basis,
    )


@pytest.mark.django_db
class TestHumanReviewedGuard:
    def test_verdict_holder_is_human_reviewed(self):
        # review_status 있음 + machine_check 없음 = 검수 산출(보호)
        rc = _rc("AAA", "BBB", status="approved", mc=None)
        assert dt.is_human_reviewed(rc) is True

    def test_fresh_relation_not_reviewed(self):
        rc = _rc("CCC", "DDD", status=None, mc=None)
        assert dt.is_human_reviewed(rc) is False

    def test_pipeline_tagged_not_reviewed(self):
        # 파이프라인이 태깅하면 machine_check가 채워짐 → 보호 대상 아님(재처리 가능)
        rc = _rc("EEE", "FFF", status="pending", mc={"json_parse": True})
        assert dt.is_human_reviewed(rc) is False

    def test_exclude_human_reviewed_queryset(self):
        v = _rc("AAA", "BBB", status="approved", mc=None)     # 보호
        p = _rc("CCC", "DDD", status="pending", mc={"x": 1})   # 파이프라인
        fresh = _rc("EEE", "FFF", status=None, mc=None)        # 신규
        qs = dt.exclude_human_reviewed(RelationConfidence.objects.all())
        ids = set(qs.values_list("id", flat=True))
        assert v.id not in ids           # verdict 보유 제외
        assert p.id in ids and fresh.id in ids


def _mc(**over):
    base = {
        "target_in_basis": True, "type_signature_ok": True, "confidence_ok": True,
        "confidence": 0.9, "type_match_ok": True, "suggested_type": None,
        "self_contradiction": False,
    }
    base.update(over)
    return base


class TestGateAudit:
    """S3 — 게이트 감사 추적(행위보존: audit 경로 ↔ decide_gate 판정 일치)."""

    def test_schema_has_rules_values_path(self):
        a = dt.build_gate_audit(_mc(), "SUPPLIES_TO")
        assert set(a) == {"decision_path", "fired_rules", "values"}
        assert a["values"]["relation_type"] == "SUPPLIES_TO"
        assert a["values"]["confidence"] == 0.9
        assert "confidence_threshold" in a["values"]

    @override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
    def test_audit_path_matches_decide_gate(self):
        cases = [
            _mc(self_contradiction=True),                       # self_contradiction
            _mc(type_match_ok=False, suggested_type="PARTNER_WITH"),  # type_change
            _mc(),                                              # all_checks→auto
            _mc(target_in_basis=False),                        # checks_fail
        ]
        for mc in cases:
            gate_class, status = dt.decide_gate(mc)
            audit = dt.build_gate_audit(mc, "SUPPLIES_TO")
            # 감사 경로가 decide_gate 판정과 정합(행위보존 증명)
            if mc["self_contradiction"]:
                assert audit["decision_path"] == "self_contradiction→pending"
                assert status == "pending"
            elif not mc["type_match_ok"] or mc["suggested_type"]:
                assert audit["decision_path"] == "type_change→pending"
                assert status == "pending"
            elif mc["target_in_basis"] and mc["type_signature_ok"] and mc["confidence_ok"]:
                assert audit["decision_path"] == "all_checks→auto_candidate"
                assert status == "auto"  # 스위치 ON
            else:
                assert audit["decision_path"] == "checks_fail→pending"

    def test_fired_rules_recorded(self):
        a = dt.build_gate_audit(_mc(target_in_basis=False, confidence_ok=False), "PEER_OF")
        assert "target_in_basis_fail" in a["fired_rules"]
        assert "confidence_ok_fail" in a["fired_rules"]


class TestExtractRationale:
    def test_valid_rationale(self):
        out = dt.extract_rationale({"rationale": {
            "claim": "공급 관계", "claim_type": "inference",
            "basis_hint": "10-K", "counter_signal": "경쟁 신호",
        }})
        assert out["claim"] == "공급 관계"
        assert out["claim_type"] == "inference"
        assert out["counter_signal"] == "경쟁 신호"

    def test_unknown_claim_type_defaults_uncertain(self):
        out = dt.extract_rationale({"rationale": {"claim": "x", "claim_type": "bogus"}})
        assert out["claim_type"] == "uncertain"

    def test_missing_rationale_returns_none(self):
        assert dt.extract_rationale({"domain_tags": ["x"]}) is None
        assert dt.extract_rationale({"rationale": "not a dict"}) is None
        assert dt.extract_rationale({"rationale": {"claim": ""}}) is None  # 빈 claim


# ── e2e 훅: mock LLM ──
_GOOD_JSON = (
    '{"domain_tags": ["메모리·HBM"], "type_match": {"match": true, "suggested_type": null}, '
    '"refined_basis": "", "confidence": 0.92}'
)


class _Resp:
    def __init__(self, text):
        self.text = text


@pytest.mark.django_db
class TestAutoTaggingE2E:
    @override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
    def test_fresh_sec_relation_auto_tagged(self, monkeypatch):
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol="MU", stock_name="Micron Technology")
        rc = _rc("NVDA", "MU", "SUPPLIES_TO",
                 basis="SEC 10-K: We purchase memory from Micron (MU).")
        monkeypatch.setattr(
            "packages.shared.llm.legacy_gemini.generate_with_circuit",
            lambda **kw: _Resp(_GOOD_JSON),
        )
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        res = tag_relation_domain_task(rc.id)
        rc.refresh_from_db()
        assert res["review_status"] == "auto"          # 스위치 ON → auto
        assert rc.relation_domain_draft == "메모리·HBM"
        assert rc.domain_machine_check is not None
        assert rc.relation_domain is None              # 승인본은 하드룰상 미기록

    @override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
    def test_rationale_recorded_in_machine_check(self, monkeypatch):
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol="MU2", stock_name="Micron")
        rc = _rc("NVDA", "MU2", "SUPPLIES_TO",
                 basis="SEC 10-K: We purchase memory from Micron (MU2).")
        good = (
            '{"domain_tags": ["메모리·HBM"], "type_match": {"match": true, "suggested_type": null}, '
            '"confidence": 0.92, "rationale": {"claim": "메모리 공급 관계", '
            '"claim_type": "known_fact", "basis_hint": "10-K 구매 문장", "counter_signal": ""}}'
        )
        monkeypatch.setattr(
            "packages.shared.llm.legacy_gemini.generate_with_circuit",
            lambda **kw: _Resp(good),
        )
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        tag_relation_domain_task(rc.id)
        rc.refresh_from_db()
        rat = rc.domain_machine_check.get("llm_rationale")
        assert rat is not None
        assert rat["claim"] == "메모리 공급 관계"
        assert rat["claim_type"] == "known_fact"

    @override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
    def test_malformed_rationale_does_not_block_tagging(self, monkeypatch):
        # rationale 누락(부속 실패)이어도 태깅(본체)은 성공, llm_rationale만 null
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol="MU3", stock_name="Micron")
        rc = _rc("NVDA", "MU3", "SUPPLIES_TO",
                 basis="SEC 10-K: We purchase memory from Micron (MU3).")
        no_rationale = (
            '{"domain_tags": ["메모리·HBM"], "type_match": {"match": true}, "confidence": 0.9}'
        )
        monkeypatch.setattr(
            "packages.shared.llm.legacy_gemini.generate_with_circuit",
            lambda **kw: _Resp(no_rationale),
        )
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        res = tag_relation_domain_task(rc.id)
        rc.refresh_from_db()
        assert res["review_status"] == "auto"                 # 태깅 성공(블록 안 됨)
        assert rc.relation_domain_draft == "메모리·HBM"
        assert rc.domain_machine_check.get("llm_rationale") is None  # 근거만 null

    @override_settings(DOMAIN_AUTO_APPROVE=True)
    def test_verdict_holder_skipped_by_hook(self, monkeypatch):
        # 검수 승인된 관계는 훅이 건드리지 않는다(덮어쓰기 금지)
        rc = _rc("INCY", "REGN", "COMPETES_WITH", status="approved", mc=None,
                 basis="SEC 10-K: compete with Regeneron (REGN).")
        called = {"n": 0}

        def _spy(**kw):
            called["n"] += 1
            return _Resp(_GOOD_JSON)

        monkeypatch.setattr("packages.shared.llm.legacy_gemini.generate_with_circuit", _spy)
        from apps.chain_sight.tasks.domain_tasks import tag_relation_domain_task
        res = tag_relation_domain_task(rc.id)
        assert res == {"skipped": "human-reviewed", "rc_id": rc.id}
        assert called["n"] == 0                        # LLM 호출조차 안 함
        rc.refresh_from_db()
        assert rc.relation_domain_draft is None        # 무접촉
