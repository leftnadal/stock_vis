"""⑳-3 S2-B 도메인 태깅 코어 테스트 — 기계검증·게이트·하드룰(타입 비자동)."""

import pytest
from django.test import override_settings

from apps.chain_sight.services import domain_tagging as dt


# ── JSON 파싱 ──
def test_parse_strips_markdown_fence():
    out = dt.parse_llm_json('```json\n{"domain_tags": ["메모리·HBM"], "confidence": 0.9}\n```')
    assert out["domain_tags"] == ["메모리·HBM"]


def test_parse_malformed_returns_none():
    assert dt.parse_llm_json("이건 JSON이 아님") is None
    assert dt.parse_llm_json("") is None


def test_parse_extracts_object_amid_prose():
    out = dt.parse_llm_json('설명... {"confidence": 0.5} 끝')
    assert out == {"confidence": 0.5}


# ── 기계검증 ──
def _mc(relation_type, basis, llm_out, target="MU", target_name="Micron Technology"):
    return dt.machine_check(
        symbol_a="NVDA", symbol_b=target, center="NVDA",
        relation_type=relation_type, basis=basis,
        target_name=target_name, llm_out=llm_out,
    )


def test_target_in_basis_by_symbol_and_name():
    mc = _mc("SUPPLIES_TO", "SEC 10-K: We purchase from Micron and MU.", {"confidence": 0.9, "type_match": {"match": True}})
    assert mc["target_in_basis"] is True


def test_target_absent_fails():
    mc = _mc("SUPPLIES_TO", "SEC 10-K: unrelated text about revenue.", {"confidence": 0.9, "type_match": {"match": True}})
    assert mc["target_in_basis"] is False


def test_compete_vocab_in_noncompete_type_fails_signature():
    # DEPENDS_ON인데 문장은 경쟁 어휘 → 시그니처 불일치
    mc = _mc("DEPENDS_ON", "SEC 10-K: our competitors include Micron.", {"confidence": 0.9, "type_match": {"match": True}})
    assert mc["type_signature_ok"] is False


def test_compete_vocab_in_compete_type_ok():
    mc = _mc("COMPETES_WITH", "SEC 10-K: we compete directly with Micron.", {"confidence": 0.9, "type_match": {"match": True}})
    assert mc["type_signature_ok"] is True


@override_settings(DOMAIN_CONFIDENCE_THRESHOLD=0.75)
def test_confidence_threshold():
    hi = _mc("SUPPLIES_TO", "SEC 10-K: purchase from Micron MU.", {"confidence": 0.8, "type_match": {"match": True}})
    lo = _mc("SUPPLIES_TO", "SEC 10-K: purchase from Micron MU.", {"confidence": 0.6, "type_match": {"match": True}})
    assert hi["confidence_ok"] is True
    assert lo["confidence_ok"] is False


# ── 게이트 + 하드룰 ──
@override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
def test_hard_rule_type_change_never_auto_even_with_high_conf():
    """★하드룰: LLM이 타입 변경 제안하면 confidence·검증 무관 pending(auto 금지)."""
    mc = _mc("DEPENDS_ON", "SEC 10-K: purchase memory from Micron MU.",
             {"confidence": 0.99, "type_match": {"match": False, "suggested_type": "SUPPLIES_TO"}})
    gate_class, status = dt.decide_gate(mc)
    assert gate_class == "pending"
    assert status == "pending"  # AUTO_APPROVE=True여도 타입변경은 절대 auto 아님


@override_settings(DOMAIN_AUTO_APPROVE=True, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
def test_auto_candidate_becomes_auto_when_switch_on():
    mc = _mc("SUPPLIES_TO", "SEC 10-K: We purchase memory from Micron MU.",
             {"confidence": 0.9, "type_match": {"match": True}})
    gate_class, status = dt.decide_gate(mc)
    assert gate_class == "auto_candidate"
    assert status == "auto"


@override_settings(DOMAIN_AUTO_APPROVE=False, DOMAIN_CONFIDENCE_THRESHOLD=0.75)
def test_auto_candidate_stays_pending_when_switch_off():
    """캘리브레이션 전(DOMAIN_AUTO_APPROVE=False): auto 후보도 status=pending(반영 보류)."""
    mc = _mc("SUPPLIES_TO", "SEC 10-K: We purchase memory from Micron MU.",
             {"confidence": 0.9, "type_match": {"match": True}})
    gate_class, status = dt.decide_gate(mc)
    assert gate_class == "auto_candidate"
    assert status == "pending"


# ── tag_one 통합(코어, mock LLM) ──
def test_tag_one_json_fail_marks_not_ok():
    out = dt.tag_one(
        symbol_a="NVDA", symbol_b="MU", center="NVDA", relation_type="SUPPLIES_TO",
        basis="SEC 10-K: purchase memory from Micron MU.", target_name="Micron",
        llm_call=lambda s, c: "not json at all",
    )
    assert out["ok"] is False
    assert out["review_status"] == "pending"
    assert out["draft"] is None


@override_settings(DOMAIN_AUTO_APPROVE=False)
def test_tag_one_draft_no_approved_write():
    """코어는 draft만 산출 — 승인본은 반환 구조에 없음(relation_domain 미기록 보장)."""
    out = dt.tag_one(
        symbol_a="NVDA", symbol_b="MU", center="NVDA", relation_type="SUPPLIES_TO",
        basis="SEC 10-K: We purchase memory from Micron MU.", target_name="Micron",
        llm_call=lambda s, c: '{"domain_tags": ["메모리·HBM"], "type_match": {"match": true}, "confidence": 0.9}',
    )
    assert out["ok"] is True
    assert out["draft"] == "메모리·HBM"
    assert out["review_status"] == "pending"  # 스위치 off
    assert "relation_domain" not in out  # 승인본 키 자체가 없음
