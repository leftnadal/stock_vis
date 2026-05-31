"""
quality_checks.py 단위 테스트.

run_post_batch_quality_checks, get_dashboard_stats 검증.
DB 접근 필요 — @pytest.mark.django_db.

Note: quality_checks.py는 local import를 사용하므로 실제 DB 레코드로 테스트.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock
    return Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')


@pytest.fixture
def doc(stock):
    from services.sec_pipeline.models import RawDocumentStore
    return RawDocumentStore.objects.create(
        symbol=stock,
        accession_no='acc-qc-001',
        filing_date=date(2023, 11, 1),
        fiscal_year=2023,
        final_link='https://sec.gov/test',
        status='success',
    )


# ---------------------------------------------------------------------------
# Tests: run_post_batch_quality_checks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunPostBatchQualityChecks:
    def test_no_data_returns_empty(self):
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert alerts == []

    def test_high_failure_rate_alert(self, stock):
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 5 failed out of 6 total (83% > 20%)
        for i in range(5):
            RawDocumentStore.objects.create(
                symbol=stock,
                accession_no=f'acc-fail-{i}',
                filing_date=date(2023, 11, 1),
                fiscal_year=2023,
                final_link=f'https://sec.gov/fail{i}',
                status='failed',
            )
        RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-ok-1',
            filing_date=date(2023, 11, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/ok',
            status='success',
        )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('실패율' in a for a in alerts)

    def test_queue_backlog_alert(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 101 pending entries (> 100 threshold)
        for i in range(101):
            UnmatchedCompanyQueue.objects.create(
                raw_company_name=f'Company {i}',
                source_symbol='AAPL',
                status='pending',
            )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('적체' in a and '미매칭' in a for a in alerts)

    def test_section_fail_alert(self):
        from services.sec_pipeline.models import FilingProcessLog
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        FilingProcessLog.objects.create(
            symbol='AAPL',
            stage='section_extract',
            status='failed',
            detail='FAIL: item_1 heading not found',
        )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('섹션 검증 실패' in a for a in alerts)


# ---------------------------------------------------------------------------
# Tests: get_dashboard_stats
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetDashboardStats:
    def test_empty_stats_structure(self):
        from services.sec_pipeline.quality_checks import get_dashboard_stats
        result = get_dashboard_stats()

        assert 'collection' in result
        assert 'track_a' in result
        assert 'track_b' in result
        assert 'matching' in result
        assert result['collection']['total'] == 0
        assert result['track_a']['total_evidences'] == 0

    def test_with_data(self, stock, doc):
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        SupplyChainEvidence.objects.create(
            source_document=doc,
            source_company=stock,
            target_company=stock,
            target_company_name='Apple',
            relationship_type='SUPPLIES_TO',
            evidence_text='test',
            system_confidence=0.8,
            neo4j_dirty=False,
        )

        result = get_dashboard_stats()
        assert result['collection']['total'] == 1
        assert result['track_a']['total_evidences'] == 1
        assert result['track_a']['matched'] == 1
        assert result['track_a']['neo4j_synced'] == 1
