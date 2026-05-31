"""
quality_checks.py 추가 단위 테스트.

기존 test_quality_checks.py에서 누락된 영역:
- 평균 confidence 미만 알림
- Ticker 매칭률 미달 알림
- Track B unknown 비율 알림
- Neo4j dirty 적체 알림
- get_dashboard_stats: 매칭 큐 status 분류, BM grade 분류

DB 접근 필요 — @pytest.mark.django_db.
"""

from datetime import date

import pytest


@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock
    return Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')


@pytest.fixture
def doc(stock):
    from services.sec_pipeline.models import RawDocumentStore
    return RawDocumentStore.objects.create(
        symbol=stock,
        accession_no='acc-qca-001',
        filing_date=date(2023, 11, 1),
        fiscal_year=2023,
        final_link='https://sec.gov/qca',
        status='success',
    )


@pytest.mark.django_db
class TestAdditionalAlerts:
    def test_low_confidence_alert(self, stock, doc):
        """평균 system_confidence < 0.5 → 알림."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 매칭률은 충분히 높이고 confidence만 낮춤
        for i in range(5):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=stock,  # matched
                target_company_name=f'Co {i}',
                relationship_type='SUPPLIES_TO',
                evidence_text='ev',
                system_confidence=0.2,  # 평균 0.2 < 0.5
            )

        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('confidence' in a for a in alerts)

    def test_low_match_rate_alert(self, stock, doc):
        """매칭률 < 30% → 알림."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 1 matched / 9 unmatched → 10% 매칭률
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company=stock,
            target_company_name='Matched',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev', system_confidence=0.9,
        )
        for i in range(9):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=None,
                target_company_name=f'Unmatched {i}',
                relationship_type='SUPPLIES_TO',
                evidence_text='ev', system_confidence=0.9,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('매칭률' in a for a in alerts)

    def test_track_b_unknown_alert(self, stock, doc):
        """Track B unknown 비율 > 30% → 알림."""
        from services.sec_pipeline.models import BusinessModelSnapshot
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 2 스냅샷 × 5 필드 = 10. 모두 unknown이면 100%
        for i in range(2):
            BusinessModelSnapshot.objects.create(
                symbol=stock, source_document=doc,
                as_of_date=date(2023, 11, 1),
                # 모든 필드 default 'unknown'
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('unknown' in a for a in alerts)

    def test_neo4j_dirty_backlog_alert(self, stock, doc):
        """neo4j_dirty=True & matched > 50건 → 알림."""
        from services.sec_pipeline.models import SupplyChainEvidence
        from services.sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(51):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=stock,
                target_company_name=f'X {i}',
                relationship_type='SUPPLIES_TO',
                evidence_text='ev',
                system_confidence=0.8,
                neo4j_dirty=True,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert any('Neo4j dirty' in a for a in alerts)


@pytest.mark.django_db
class TestDashboardStatsAdvanced:
    def test_bm_grade_breakdown(self, stock, doc):
        from services.sec_pipeline.models import BusinessModelSnapshot
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2023, 1, 1),
            confidence_grade='high',
        )
        BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2023, 2, 1),
            confidence_grade='medium',
        )
        BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2023, 3, 1),
            confidence_grade='low',
        )
        result = get_dashboard_stats()
        assert result['track_b']['total_snapshots'] == 3
        assert result['track_b']['high_grade'] == 1
        assert result['track_b']['medium_grade'] == 1
        assert result['track_b']['low_grade'] == 1

    def test_collection_status_breakdown(self, stock):
        from services.sec_pipeline.models import RawDocumentStore
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        RawDocumentStore.objects.create(
            symbol=stock, accession_no='ds-1',
            filing_date=date(2023, 1, 1), fiscal_year=2022,
            final_link='https://sec.gov/1', status='success',
        )
        RawDocumentStore.objects.create(
            symbol=stock, accession_no='ds-2',
            filing_date=date(2023, 2, 1), fiscal_year=2022,
            final_link='https://sec.gov/2', status='partial',
        )
        RawDocumentStore.objects.create(
            symbol=stock, accession_no='ds-3',
            filing_date=date(2023, 3, 1), fiscal_year=2022,
            final_link='https://sec.gov/3', status='failed',
        )
        result = get_dashboard_stats()
        assert result['collection']['total'] == 3
        assert result['collection']['success'] == 1
        assert result['collection']['partial'] == 1
        assert result['collection']['failed'] == 1

    def test_queue_status_breakdown(self):
        from services.sec_pipeline.models import UnmatchedCompanyQueue
        from services.sec_pipeline.quality_checks import get_dashboard_stats

        UnmatchedCompanyQueue.objects.create(
            raw_company_name='A', source_symbol='X', status='pending',
        )
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='B', source_symbol='X', status='matched',
        )
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='C', source_symbol='X', status='not_public',
        )
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='D', source_symbol='X', status='person',
        )
        result = get_dashboard_stats()
        assert result['matching']['queue_total'] == 4
        assert result['matching']['queue_pending'] == 1
        assert result['matching']['queue_matched'] == 1
        assert result['matching']['queue_not_public'] == 1
        assert result['matching']['queue_person'] == 1
