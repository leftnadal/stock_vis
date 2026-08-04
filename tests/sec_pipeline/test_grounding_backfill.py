"""SEC β G1 — grounding 백필 태스크(dry-run 분포 + 실기록) 테스트.

dry-run 필수(쓰기 0건 확인). 판정 4종 분포 집계. select_related로 N+1 방어.
"""
import datetime

import pytest

from packages.shared.stocks.models import Stock
from services.sec_pipeline.grounding import GROUNDING_METHOD
from services.sec_pipeline.grounding_backfill import run_grounding_backfill
from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence


def _doc(symbol_stock, acc, *, item_1="", item_1a="", item_7=""):
    return RawDocumentStore.objects.create(
        symbol=symbol_stock,
        accession_no=acc,
        filing_date=datetime.date(2026, 4, 1),
        fiscal_year=2025,
        item_1_text=item_1,
        item_1a_text=item_1a,
        item_7_text=item_7,
    )


def _ev(doc, src, text):
    return SupplyChainEvidence.objects.create(
        source_document=doc,
        source_company=src,
        target_company_name="Target Co",
        relationship_type="supplier",
        evidence_text=text,
    )


@pytest.fixture
def cohort(db):
    src = Stock.objects.create(symbol="SRC", stock_name="Src Inc.")
    full = _doc(
        src, "ACC-FULL",
        item_1="ACME relies on SRC for critical components.",
        item_1a='We signed a “long-term” supply agreement with SRC.',
    )
    empty = _doc(src, "ACC-EMPTY")  # 전 item 빈 문자열 = missing_source
    ev_verified = _ev(full, src, "ACME relies on SRC for critical components.")
    ev_normalized = _ev(full, src, 'We signed a "long-term" supply agreement with SRC.')
    ev_not_found = _ev(full, src, "SRC divested its entire semiconductor division.")
    ev_missing = _ev(empty, src, "Any sentence at all.")
    return {
        "verified": ev_verified,
        "normalized_match": ev_normalized,
        "not_found": ev_not_found,
        "missing_source": ev_missing,
    }


def test_dry_run_distribution_and_no_writes(cohort):
    result = run_grounding_backfill(dry_run=True)

    assert result["dry_run"] is True
    assert result["total"] == 4
    assert result["distribution"] == {
        "verified": 1,
        "normalized_match": 1,
        "partial_match": 0,  # G1.6: 이 cohort의 not_found 는 접두<70% → partial 승격 없음
        "not_found": 1,
        "missing_source": 1,
    }
    # 쓰기 0건: 전 행 grounding_status 여전히 NULL
    for ev in cohort.values():
        ev.refresh_from_db()
        assert ev.grounding_status is None
        assert ev.grounded_at is None


def test_write_mode_records_status(cohort):
    result = run_grounding_backfill(dry_run=False)

    assert result["dry_run"] is False
    assert result["distribution"]["verified"] == 1
    for expected_status, ev in cohort.items():
        ev.refresh_from_db()
        assert ev.grounding_status == expected_status
        assert ev.grounding_method == GROUNDING_METHOD
        assert ev.grounded_at is not None


def test_backfill_skips_already_grounded(cohort):
    # 이미 검증된 행(grounding_status IS NOT NULL)은 재순회 대상 아님
    run_grounding_backfill(dry_run=False)
    result = run_grounding_backfill(dry_run=True)
    assert result["total"] == 0  # 전건 이미 grounded → NULL 대상 0
