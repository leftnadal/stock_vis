"""SECB-V2-ROLLOUT — v2 필터 정합·v1 보존·sanity 경고·verbatim 매칭 입증.

D-SECB-V2-LEN=C(캡 제거·2000 sanity 경고·절단 금지) + D-SECB-V2-COEXIST=B
(v1 보존·소비측 .current() v2 필터).
"""

import logging
from datetime import date

import pytest

from packages.shared.stocks.models import Stock
from services.sec_pipeline.grounding import STATUS_VERIFIED, ground_evidence_g16
from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
from services.sec_pipeline.validator_track_a import save_supply_chain_evidences


def _doc(stock, acc):
    return RawDocumentStore.objects.create(
        symbol=stock,
        accession_no=acc,
        filing_date=date(2023, 11, 3),
        fiscal_year=2023,
        final_link="https://sec.gov/t",
    )


@pytest.mark.django_db
def test_current_returns_only_v2_and_preserves_v1():
    """소비 기본 .current()=v2만. v1은 원장에 보존(삭제 안 됨)."""
    stock = Stock.objects.create(symbol="AAPL", stock_name="Apple")
    doc = _doc(stock, "acc-v2-001")
    v1 = SupplyChainEvidence.objects.create(
        source_document=doc, source_company=stock, target_company_name="TSMC",
        relationship_type="SUPPLIES_TO", evidence_text="v1 text",
        system_confidence=0.8, prompt_version="v1",
    )
    v2 = SupplyChainEvidence.objects.create(
        source_document=doc, source_company=stock, target_company_name="TSMC",
        relationship_type="SUPPLIES_TO", evidence_text="v2 text",
        system_confidence=0.9, prompt_version="v2",
    )
    assert list(SupplyChainEvidence.objects.current()) == [v2]
    # v1 무접촉 보존
    assert SupplyChainEvidence.objects.count() == 2
    assert SupplyChainEvidence.objects.filter(pk=v1.pk).exists()


@pytest.mark.django_db
def test_supersession_v1_only_filing_kept():
    """(b) v2 없는 filing → v1 유지(배포~롤아웃 창 회귀 방지)."""
    stock = Stock.objects.create(symbol="INTC", stock_name="Intel")
    doc = _doc(stock, "acc-suprsn-b")
    v1 = SupplyChainEvidence.objects.create(
        source_document=doc, source_company=stock, target_company_name="ASML",
        relationship_type="DEPENDS_ON", evidence_text="v1 only",
        system_confidence=0.7, prompt_version="v1",
    )
    assert list(SupplyChainEvidence.objects.current()) == [v1]


@pytest.mark.django_db
def test_supersession_mixed_filings():
    """(c) 혼재: X(v1+v2)→v2 대체, Y(v1-only)→v1 유지. filing 단위 정확."""
    stock = Stock.objects.create(symbol="AVGO", stock_name="Broadcom")
    doc_x = _doc(stock, "acc-suprsn-cx")
    doc_y = _doc(stock, "acc-suprsn-cy")
    x_v1 = SupplyChainEvidence.objects.create(
        source_document=doc_x, source_company=stock, target_company_name="Apple",
        relationship_type="CUSTOMER_OF", evidence_text="x v1",
        system_confidence=0.6, prompt_version="v1",
    )
    x_v2 = SupplyChainEvidence.objects.create(
        source_document=doc_x, source_company=stock, target_company_name="Apple",
        relationship_type="CUSTOMER_OF", evidence_text="x v2",
        system_confidence=0.9, prompt_version="v2",
    )
    y_v1 = SupplyChainEvidence.objects.create(
        source_document=doc_y, source_company=stock, target_company_name="Google",
        relationship_type="CUSTOMER_OF", evidence_text="y v1",
        system_confidence=0.6, prompt_version="v1",
    )
    cur = set(SupplyChainEvidence.objects.current().values_list("pk", flat=True))
    assert cur == {x_v2.pk, y_v1.pk}  # X=v2(대체)·Y=v1(유지)
    assert x_v1.pk not in cur  # X의 v1은 배제(supersession)


@pytest.mark.django_db
def test_save_records_prompt_version_v2():
    stock = Stock.objects.create(symbol="MSFT", stock_name="Microsoft")
    doc = _doc(stock, "acc-v2-002")
    validated = [{
        "target_company_name": "OpenAI", "relationship_type": "PARTNER_WITH",
        "evidence_text": "MSFT partners with OpenAI.",
        "system_confidence": 0.9, "confidence_grade": "high",
    }]
    created = save_supply_chain_evidences(validated, doc, "MSFT")
    assert len(created) == 1
    assert created[0].prompt_version == "v2"


@pytest.mark.django_db
def test_sanity_warning_no_truncation(caplog):
    """>2000자 = 경고 로그만. 절단·거부 없음(verbatim 전량 저장)."""
    stock = Stock.objects.create(symbol="NVDA", stock_name="Nvidia")
    doc = _doc(stock, "acc-v2-003")
    long_text = "A" * 2500
    validated = [{
        "target_company_name": "TSMC", "relationship_type": "DEPENDS_ON",
        "evidence_text": long_text,
        "system_confidence": 0.8, "confidence_grade": "medium",
    }]
    with caplog.at_level(logging.WARNING, logger="services.sec_pipeline.validator_track_a"):
        created = save_supply_chain_evidences(validated, doc, "NVDA")
    # 절단 없음 — verbatim 전량 저장
    assert len(created[0].evidence_text) == 2500
    # 경고 발생
    assert any("SECB_V2_SANITY" in r.getMessage() for r in caplog.records)


@pytest.mark.django_db
def test_rematch_scope_preserves_v1():
    """rematch unmatched 쿼리=.current().filter(target isnull) → v1 제외(delete 보호)."""
    stock = Stock.objects.create(symbol="AMD", stock_name="AMD")
    doc = _doc(stock, "acc-v2-004")
    v1u = SupplyChainEvidence.objects.create(
        source_document=doc, source_company=stock, target_company=None,
        target_company_name="customers", relationship_type="CUSTOMER_OF",
        evidence_text="v1", system_confidence=0.5, prompt_version="v1",
    )
    v2u = SupplyChainEvidence.objects.create(
        source_document=doc, source_company=stock, target_company=None,
        target_company_name="customers", relationship_type="CUSTOMER_OF",
        evidence_text="v2", system_confidence=0.5, prompt_version="v2",
    )
    scoped = SupplyChainEvidence.objects.current().filter(target_company__isnull=True)
    assert list(scoped) == [v2u]
    assert v1u not in list(scoped)


def test_validate_no_truncation_over_300():
    """D-SECB-V2-LEN=C: validate가 >300 evidence를 절단하지 않고 '...' 미부착(verbatim)."""
    from services.sec_pipeline.validator_track_a import validate_supply_chain_result

    long_ev = (
        "The Company depends on Supplier X for critical components, and this "
        "dependency spans multiple product lines across several fiscal years, "
        "creating a concentration risk that management actively monitors on a "
        "continuous basis and discloses in detail within its annual report to "
        "shareholders, lenders, and regulators in every jurisdiction worldwide."
    )
    assert len(long_ev) > 300
    raw = {"relationships": [{
        "target_company_name": "Supplier X", "relationship_type": "DEPENDS_ON",
        "evidence_text": long_ev, "confidence": 0.9, "direction": "inbound",
    }]}
    result = validate_supply_chain_result(raw, "AAPL")
    assert len(result) == 1
    assert result[0]["evidence_text"] == long_ev  # 원문 그대로
    assert not result[0]["evidence_text"].endswith("...")
    assert len(result[0]["evidence_text"]) > 300  # 절단 안 됨


def test_grounding_verbatim_long_evidence_verified():
    """캡 제거 방향 실증: >300자 완결 인용이 원문 verbatim 부분문자열이면 VERIFIED."""
    sentence = (
        "The Company depends on Taiwan Semiconductor Manufacturing Company for the "
        "fabrication of substantially all of its advanced logic chips, and any "
        "prolonged disruption in that critical supply relationship could materially "
        "and adversely affect the Company's ability to manufacture, assemble, and "
        "deliver its products to its customers on a timely and cost-effective basis."
    )
    assert len(sentence) > 300
    source = "Some preamble. " + sentence + " Additional filing boilerplate follows."
    res = ground_evidence_g16(sentence, source)
    assert res.status == STATUS_VERIFIED
