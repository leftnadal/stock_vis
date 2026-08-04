"""L2-ADOPT — Peer 도메인 태깅 코어 e2e (목킹, LLM 무호출).

경로: LLM 초안 → 접지 판정 → 거부권(0.2) → 채택/기각 폴백 → 추정 라벨.
"""

import json

import pytest

from apps.chain_sight.services.peer_domain_tagging import (
    TAG_SOURCE,
    build_peer_prompt,
    is_estimate_cell,
    tag_peer_one,
)

DCT = {
    "반도체": ["semiconductor"],
    "메모리": ["memory"],
    "결제": ["payment"],
}


def _llm_returning(obj):
    """(system, contents) -> raw JSON 텍스트 콜러블 목킹."""
    def _call(system, contents):
        return json.dumps(obj, ensure_ascii=False)
    return _call


class TestBuildPeerPrompt:
    def test_variant_yi_format_with_name_industry(self):
        system, contents = build_peer_prompt(
            "AAA", "BBB", "Alpha Inc", "Beta Corp", "Semiconductors", "Software"
        )
        user = contents[0]
        # ㉯: 심볼+회사명+industry 포함
        assert "AAA (Alpha Inc, Semiconductors)" in user
        assert "BBB (Beta Corp, Software)" in user

    def test_claim_english_instruction(self):
        system, _ = build_peer_prompt("AAA", "BBB")
        assert "ENGLISH" in system  # claim 영어 강제
        assert "domain_tag" in system


class TestIsEstimateCell:
    def test_low_diff_is_estimate(self):
        assert is_estimate_cell("하", False) is True  # 하·상이

    def test_low_same_not_estimate(self):
        assert is_estimate_cell("하", True) is False

    def test_high_diff_not_estimate(self):
        assert is_estimate_cell("상", False) is False

    def test_none_industry_not_estimate(self):
        # industry_same 결측(None)은 상이로 취급 안 함(보수적).
        assert is_estimate_cell("하", None) is False


class TestTagPeerOneAdopt:
    def test_grounded_tag_adopted(self):
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A designs semiconductor and memory products.",
            desc_b="B manufactures memory chips.",
            mcap_tercile="상", industry_same=True, dct=DCT,
            llm_call=_llm_returning({
                "domain_tag": "반도체·메모리",
                "confidence": 0.9,
                "rationale": {
                    "claim": "Both design semiconductor and memory products.",
                    "claim_type": "known_fact", "basis_hint": "desc", "counter_signal": "",
                },
            }),
        )
        assert out["ok"] is True
        assert out["veto"] is False
        assert out["adopted_tag"] == "반도체·메모리"
        assert out["draft"] == "반도체·메모리"
        assert out["review_status"] == "auto"
        assert out["machine_check"]["source"] == TAG_SOURCE
        assert out["machine_check"]["bucket_fallback"] is False
        assert out["machine_check"]["grounded_ratio"] > 0.2


class TestTagPeerOneVeto:
    def test_ungrounded_tag_vetoed_to_bucket(self):
        # claim이 desc와 무관(payment banking) → grounded ≤ 0.2 → 거부권.
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A is a semiconductor foundry.",
            desc_b="B makes memory chips.",
            mcap_tercile="하", industry_same=True, dct=DCT,
            llm_call=_llm_returning({
                "domain_tag": "결제 인프라",
                "confidence": 0.8,
                "rationale": {
                    "claim": "Both provide payment and banking rails.",
                    "claim_type": "known_fact", "basis_hint": "x", "counter_signal": "",
                },
            }),
        )
        assert out["ok"] is True
        assert out["veto"] is True
        assert out["adopted_tag"] is None          # 기각 → 채택 없음
        assert out["draft"] == "결제 인프라"        # 원 태그는 감사 보존
        assert out["review_status"] == "pending"  # 거부권→pending(버킷 폴백, soft-drop 아님)
        assert out["machine_check"]["bucket_fallback"] is True
        assert out["machine_check"]["veto_reason"] == "low_grounding"

    def test_estimate_label_recorded(self):
        # 하·상이 구획 → 추정 라벨.
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A designs semiconductor and memory products.",
            desc_b="B manufactures memory chips.",
            mcap_tercile="하", industry_same=False, dct=DCT,
            llm_call=_llm_returning({
                "domain_tag": "반도체·메모리",
                "confidence": 0.7,
                "rationale": {
                    "claim": "Both design semiconductor and memory products.",
                    "claim_type": "inference", "basis_hint": "x", "counter_signal": "y",
                },
            }),
        )
        assert out["is_estimate"] is True
        assert out["machine_check"]["is_estimate"] is True


class TestTagPeerOneJsonFail:
    def test_parse_failure_vetoed(self):
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB",
            desc_a="x", desc_b="y",
            mcap_tercile="중", industry_same=True, dct=DCT,
            llm_call=lambda s, c: "not json at all <<<",
        )
        assert out["ok"] is False
        assert out["veto"] is True
        assert out["adopted_tag"] is None
        assert out["review_status"] == "pending"  # 거부권→pending(버킷 폴백, soft-drop 아님)
        assert out["machine_check"]["json_parse"] is False
        assert out["machine_check"]["veto_reason"] == "json_fail"

    def test_no_claim_vetoed(self):
        # 태그는 있으나 rationale.claim 없음 → 접지 불가 → 거부권.
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB",
            desc_a="A semiconductor.", desc_b="B memory.",
            mcap_tercile="상", industry_same=True, dct=DCT,
            llm_call=_llm_returning({"domain_tag": "반도체", "confidence": 0.9}),
        )
        assert out["veto"] is True
        assert out["machine_check"]["veto_reason"] == "no_claim"
        assert out["adopted_tag"] is None


class TestNeverWritesApproved:
    """하드 룰 회귀: 코어 반환에 relation_domain(승인본) 키 없음 — draft만."""

    def test_no_approved_key_in_output(self):
        out = tag_peer_one(
            symbol_a="AAA", symbol_b="BBB", desc_a="A semiconductor.", desc_b="B memory.",
            mcap_tercile="상", industry_same=True, dct=DCT,
            llm_call=_llm_returning({
                "domain_tag": "반도체", "confidence": 0.9,
                "rationale": {"claim": "semiconductor memory", "claim_type": "known_fact",
                              "basis_hint": "", "counter_signal": ""},
            }),
        )
        assert "relation_domain" not in out           # 승인본 키 부재
        assert "draft" in out and "adopted_tag" in out


@pytest.mark.django_db
class TestHookL2Path:
    """L2 훅(tag_peer_domain_task) — 스코프/임포트 회귀 + skip 가드(LLM 무호출)."""

    def _mk(self):
        from apps.chain_sight.models import RelationConfidence
        from packages.shared.stocks.models import Stock
        Stock.objects.create(symbol="AAA", stock_name="Alpha", industry="Semiconductors",
                             description="A semiconductor company.", market_capitalization=10_000_000_000)
        Stock.objects.create(symbol="BBB", stock_name="Beta", industry="Semiconductors",
                             description="B memory chips.", market_capitalization=20_000_000_000)
        Stock.objects.create(symbol="CCC", stock_name="Gamma", industry="Software",
                             description="C software.", market_capitalization=5_000_000_000)
        RelationConfidence.objects.create(symbol_a="AAA", symbol_b="BBB", relation_type="PEER_OF", truth_score=0.5)
        RelationConfidence.objects.create(symbol_a="AAA", symbol_b="CCC", relation_type="PEER_OF", truth_score=0.5)

    def test_peer_terciles_computes_no_nameerror(self):
        # 회귀: _peer_terciles가 Stock 미임포트로 NameError 나지 않는지(스코프 버그).
        self._mk()
        from apps.chain_sight.tasks.domain_tasks import _peer_terciles
        result = _peer_terciles()  # NameError 없이 실행되면 통과(스코프 회귀 핵심)
        assert isinstance(result, tuple) and len(result) == 2  # (t1,t2)

    def test_hook_skips_already_tagged(self):
        # 이미 L2-ADOPT machine_check 있는 쌍 → LLM 무호출 skip(idempotent).
        self._mk()
        from apps.chain_sight.models import RelationConfidence
        from apps.chain_sight.tasks.domain_tasks import tag_peer_domain_task
        rc = RelationConfidence.objects.get(symbol_a="AAA", symbol_b="BBB")
        rc.domain_machine_check = {"source": TAG_SOURCE}
        rc.domain_review_status = "auto"
        rc.save()
        r = tag_peer_domain_task(rc.id)
        assert r["skipped"] == "already-tagged"

    def test_hook_skips_non_peer(self):
        from apps.chain_sight.tasks.domain_tasks import tag_peer_domain_task
        r = tag_peer_domain_task(999999)  # 미존재
        assert r["skipped"] == "not-peer-or-missing"
